import pdfplumber
import pandas as pd
import re


def process_pdf(pdf_path):
    """
    Extracts transactions from a Westpac BusinessOne statement PDF.
    Returns a cleaned, reconciled pandas DataFrame.
    """

    # ---- REGEX & HELPERS (same style as before) ----
    date_re = re.compile(r"^\s*(\d{2}/\d{2}/\d{2,4})\b")

    def is_valid_amount(s):
        s = s.strip().replace(',', '')
        # 1–5 digits + 2 decimals
        if re.match(r"^\d{1,5}(\.\d{2})?$", s):
            return True
        # commas allowed
        if ',' in s and re.match(r"^[\d,]+(\.\d{2})?$", s):
            return True
        return False

    def clean_num(s):
        if not s:
            return None
        s = s.replace(',', '').strip()
        try:
            return float(s)
        except:
            return None

    def find_table_start(lines):
        for i, L in enumerate(lines):
            if "DATE TRANSACTION DESCRIPTION DEBIT CREDIT BALANCE" in L.upper():
                return i + 1
        return None

    def is_footer(line):
        keys = ["WESTPAC", "STATEMENT NO", "PAGE", "PLEASE CHECK", "ABN", "AFSL"]
        return any(k in line.upper() for k in keys)

    # ---- MAIN EXTRACTION (first-book logic) ----
    def extract_transactions(text):
        # remove blank lines
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        start = find_table_start(lines)
        if start is None:
            return []

        # collect only table body, stop at footer
        data_lines = []
        for L in lines[start:]:
            if is_footer(L):
                break
            data_lines.append(L)

        # merge multiline rows: new row starts with a date
        merged = []
        for L in data_lines:
            if date_re.match(L):
                merged.append(L)
            elif merged:
                merged[-1] += " " + L

        txs = []
        for L in merged:
            m = date_re.match(L)
            if not m:
                continue

            date = m.group(1)
            rest = L[m.end():].strip()

            # detect 2-large-number pattern (like “126,000.00 133,592.63” for Deposit)
            big_nums = re.findall(r"\d{1,3}(?:,\d{3})*(?:\.\d{2})", rest)
            if len(big_nums) == 2 and "deposit" in rest.lower():
                desc = re.sub(
                    r"\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})",
                    "",
                    rest
                ).strip()

                credit = clean_num(big_nums[0])
                balance = clean_num(big_nums[1])

                txs.append({
                    "Date": date,
                    "Particular": desc,
                    "Debit": None,
                    "Credit": credit,
                    "Balance": balance
                })
                continue

            # general numeric extraction
            all_nums = re.findall(r"[\d,]+(?:\.\d{2})?", rest)
            valid_nums = [n for n in all_nums if is_valid_amount(n)]
            if not valid_nums:
                continue

            # last valid number is balance
            balance = clean_num(valid_nums[-1])

            # description = rest minus all numeric chunks
            desc = rest
            for n in reversed(valid_nums):
                idx = desc.rfind(n)
                if idx != -1:
                    desc = desc[:idx] + desc[idx + len(n):]
            desc = re.sub(r"\s+", " ", desc).strip(" -")

            debit = credit = None

            # if we have at least 3 numbers → [debit, credit, balance]
            if len(valid_nums) >= 3:
                debit = clean_num(valid_nums[-3])
                credit = clean_num(valid_nums[-2])

            # if exactly 2 numbers → [amount, balance]
            elif len(valid_nums) == 2:
                candidate = clean_num(valid_nums[0])
                # heuristic: guess debit vs credit by text
                if any(x in desc.lower() for x in ["withdraw", "payment", "bpay"]):
                    debit = candidate
                else:
                    credit = candidate

            # if only 1 number → just balance, no amount
            elif len(valid_nums) == 1:
                debit = credit = None

            txs.append({
                "Date": date,
                "Particular": desc,
                "Debit": debit,
                "Credit": credit,
                "Balance": balance
            })

        return txs

    # ---- EXTRACT FROM ALL PAGES ----
    all_txs = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()
            txs = extract_transactions(text)
            if txs:
                print(f"✅ Page {i}: {len(txs)} transactions extracted")
                all_txs.extend(txs)

    df = pd.DataFrame(all_txs, columns=["Date", "Particular", "Debit", "Credit", "Balance"])

    # ---- RECONCILE BY BALANCE DIFFERENCE (first-book logic) ----
    for i in range(1, len(df)):
        prev_bal = df.loc[i - 1, "Balance"]
        curr_bal = df.loc[i, "Balance"]
        if pd.notna(prev_bal) and pd.notna(curr_bal):
            diff = round(curr_bal - prev_bal, 2)
            if diff > 0:
                df.loc[i, "Credit"] = abs(diff)
                df.loc[i, "Debit"] = None
            elif diff < 0:
                df.loc[i, "Debit"] = abs(diff)
                df.loc[i, "Credit"] = None

    # ---- REMOVE “ORPHAN” NUMERIC ROWS (no balance change but amount present) ----
    df["bal_diff"] = df["Balance"].diff().round(2)
    df = df[~((df["bal_diff"] == 0) & (df["Debit"].notna() | df["Credit"].notna()))]
    df.drop(columns=["bal_diff"], inplace=True)

    # ---- FINAL CLEANUP: DROP < ₹50 NOISE ----
    df["Debit"] = df["Debit"].apply(lambda x: x if pd.isna(x) or x > 50 else None)
    df["Credit"] = df["Credit"].apply(lambda x: x if pd.isna(x) or x > 50 else None)

    # ---- DATE FORMAT (second-book requirement) ----
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce").dt.strftime("%d-%m-%Y")

    print(f"💾 Extraction complete for Westpac Business PDF ({len(df)} rows)")
    return df
