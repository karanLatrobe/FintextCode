import pdfplumber
import pandas as pd
import re


def process_pdf(pdf_path):
    """
    Extracts transactions from a Westpac BusinessOne statement PDF.
    Returns a pandas DataFrame.
    """

    date_re = re.compile(r"^\s*(\d{2}/\d{2}/\d{2,4})\b")

    def is_valid_amount(s):
        s = s.strip().replace(',', '')
        if re.match(r"^\d{1,5}(\.\d{2})?$", s):
            return True
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

    def extract_transactions(text):
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        start = find_table_start(lines)
        if start is None:
            return []

        data_lines = []
        for L in lines[start:]:
            if is_footer(L):
                break
            data_lines.append(L)

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

            big_nums = re.findall(r"\d{1,3}(?:,\d{3})*(?:\.\d{2})", rest)

            if len(big_nums) == 2 and "Deposit" in rest:
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

            all_nums = re.findall(r"[\d,]+(?:\.\d{2})?", rest)
            valid_nums = [n for n in all_nums if is_valid_amount(n)]
            if not valid_nums:
                continue

            balance = clean_num(valid_nums[-1])
            desc = rest
            for n in reversed(valid_nums):
                idx = desc.rfind(n)
                if idx != -1:
                    desc = desc[:idx] + desc[idx + len(n):]
            desc = re.sub(r"\s+", " ", desc).strip(" -")

            debit = credit = None
            if len(valid_nums) >= 3:
                debit = clean_num(valid_nums[-3])
                credit = clean_num(valid_nums[-2])
            elif len(valid_nums) == 2:
                candidate = clean_num(valid_nums[0])
                if any(x in desc.lower() for x in ["withdraw", "payment", "bpay"]):
                    debit = candidate
                else:
                    credit = candidate

            txs.append({
                "Date": date,
                "Particular": desc,
                "Debit": debit,
                "Credit": credit,
                "Balance": balance
            })

        return txs

    all_txs = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()
            txs = extract_transactions(text)
            if txs:
                print(f"✅ Page {i}: {len(txs)} transactions extracted")
                all_txs.extend(txs)

    df = pd.DataFrame(all_txs, columns=["Date", "Particular", "Debit", "Credit", "Balance"])

    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce").dt.strftime("%d-%m-%Y")

    print(f"💾 Extraction complete for Westpac Business PDF ({len(df)} rows)")
    return df
