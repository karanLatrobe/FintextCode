import pdfplumber
import re
import pandas as pd
from datetime import datetime

def can_handle(pdf_path, first_page_text):
    """
    Identify if this PDF belongs to Commonwealth Bank.
    """
    keywords = ["COMMONWEALTH BANK", "NetBank", "CommBank", "CBA"]
    return any(k.lower() in first_page_text.lower() for k in keywords)


def process_pdf(pdf_path):
    """
    Extract transactions from Commonwealth Bank PDF Statement
    and return cleaned pandas DataFrame
    """

    header = "Date Transaction Debit Credit Balance"

    # ---------------------------------------------------
    # Read first page - extract statement period years
    # ---------------------------------------------------
    with pdfplumber.open(pdf_path) as pdf:
        first_page = pdf.pages[0].extract_text()

    clean_page = first_page.replace("\n", " ").replace("  ", " ")

    period_match = re.search(
        r"Statement\s*Period\s*([0-9]{1,2}\s+[A-Za-z]{3}\s+[0-9]{4})\s*[-–]\s*([0-9]{1,2}\s+[A-Za-z]{3}\s+[0-9]{4})",
        clean_page
    )

    if not period_match:
        print(clean_page)
        raise ValueError("❌ Statement period not found in PDF")

    period_start = datetime.strptime(period_match.group(1), "%d %b %Y")
    period_end = datetime.strptime(period_match.group(2), "%d %b %Y")

    start_year = period_start.year
    end_year = period_end.year

    print(f"📌 Statement detected for {start_year} -> {end_year}")

    # ---------------------------------------------------
    # Extract text after header
    # ---------------------------------------------------
    text_all = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t and header in t:
                text_all += "\n" + t.split(header, 1)[1]

    if not text_all.strip():
        raise ValueError("Header not found in PDF. Check PDF quality.")

    text = re.sub(r'\s+', ' ', text_all).replace("$ ", "$")
    text = text.replace("CR ", "CR\n").replace("DR ", "DR\n")
    lines = text.split("\n")

    transactions = []
    tmp = ""
    for line in lines:
        tmp += " " + line.strip()
        if "CR" in line or "DR" in line:
            transactions.append(tmp.strip())
            tmp = ""

    money_re = re.compile(r'(\d{1,3}(?:,\d{3})*(?:\.\d{2}))')
    date_re = re.compile(r'(\d{2}\s+[A-Za-z]{3})(?:\s+\d{4})?', re.IGNORECASE)

    rows = []
    for data in transactions:
        s = data.strip()
        dmatch = date_re.search(s)
        raw_date = dmatch.group(1) if dmatch else None

        bal_match = re.search(r'(\d{1,3}(?:,\d{3})*(?:\.\d{2}))\s*(CR|DR)', s)
        if not bal_match:
            continue

        balance = bal_match.group(1)
        balance_type = bal_match.group(2)
        bal_pos = bal_match.start(1)

        amounts = [(m.group(1), m.start(1)) for m in money_re.finditer(s)]
        amounts = [a for a in amounts if not (a[0] == balance and a[1] == bal_pos)]

        candidate_amt = None
        if amounts:
            left = [a for a in amounts if a[1] < bal_pos]
            candidate_amt = max(left, key=lambda x: x[1])[0] if left else amounts[-1][0]

        desc = s
        if raw_date:
            desc = desc.replace(raw_date, "")
        desc = desc.replace(balance, "").replace(balance_type, "")
        if candidate_amt:
            desc = re.sub(r'\$?\s*' + re.escape(candidate_amt), '', desc)
        desc = re.sub(r'\$?\d{1,3}(?:,\d{3})*(?:\.\d{2})', '', desc)
        desc = re.sub(r'[\$\€₹]', '', desc)
        desc = re.sub(r'\s+', ' ', desc).strip()

        # Auto Year Fix
        if raw_date:
            month = datetime.strptime(raw_date, "%d %b").month
            if month in [10, 11, 12]:
                final_date = datetime.strptime(f"{raw_date} {start_year}", "%d %b %Y").strftime("%d-%m-%Y")
            else:
                final_date = datetime.strptime(f"{raw_date} {end_year}", "%d %b %Y").strftime("%d-%m-%Y")
        else:
            final_date = None

        rows.append({
            "raw": s,
            "Date": final_date,
            "Description": desc,
            "CandidateAmount": candidate_amt,
            "AllAmounts": [a[0] for a in amounts],
            "Balance": balance,
            "BalanceType": balance_type
        })

    # Convert to DataFrame
    df = pd.DataFrame(rows)

    def to_num(x):
        if x is None:
            return None
        return float(str(x).replace(',', ''))

    df['Balance_num'] = df['Balance'].apply(lambda x: to_num(x))
    df['Cand_num'] = df['CandidateAmount'].apply(lambda x: to_num(x))

    types = []
    debits = []
    credits = []
    prev_balance = None

    for idx, row in df.iterrows():
        bal = row['Balance_num']
        amt = row['Cand_num']

        chosen_debit = None
        chosen_credit = None
        chosen_type = None

        if pd.isna(amt) and row['AllAmounts']:
            amt = to_num(row['AllAmounts'][-1]) if row['AllAmounts'] else None

        if prev_balance is not None and amt is not None and bal is not None:
            tol = max(0.01, 0.0005 * amt)
            diff_debit_r = round(prev_balance - bal, 2)
            diff_credit_r = round(bal - prev_balance, 2)

            if abs(diff_debit_r - amt) <= tol:
                chosen_debit = amt
                chosen_type = "Debit"
            elif abs(diff_credit_r - amt) <= tol:
                chosen_credit = amt
                chosen_type = "Credit"

        if chosen_type is None:
            s_lower = row['raw'].lower()
            credit_kw = ["transfer from", "direct credit", "fast transfer from", "deposit", "transfer in", "credit"]
            debit_kw = ["transfer to", "direct debit", "wdl", "atm", "fee", "cash out", "purchase", "withdraw", "debit", "pos"]

            if any(k in s_lower for k in credit_kw):
                chosen_credit = amt
                chosen_type = "Credit"
            elif any(k in s_lower for k in debit_kw):
                chosen_debit = amt
                chosen_type = "Debit"
            else:
                if prev_balance is not None and amt is not None and bal is not None:
                    if bal < prev_balance:
                        chosen_debit = amt; chosen_type = "Debit"
                    elif bal > prev_balance:
                        chosen_credit = amt; chosen_type = "Credit"
                else:
                    chosen_debit = amt; chosen_type = "Debit"

        debits.append(chosen_debit)
        credits.append(chosen_credit)
        types.append(chosen_type)
        prev_balance = bal

    df['Debit'] = debits
    df['Credit'] = credits

    # Final Excel Frame
    out = df[['Date', 'Description', 'Debit', 'Credit', 'Balance']].copy()
    out.rename(columns={'Description':'Particulars'}, inplace=True)

    # numeric cleanup
    def clean_numeric(col):
        s = col.astype(str).str.replace(',', '', regex=False)
        s = s.replace({'None': None, 'nan': None, '' : None})
        return pd.to_numeric(s, errors='coerce')

    out['Debit'] = clean_numeric(out['Debit'])
    out['Credit'] = clean_numeric(out['Credit'])
    out['Balance'] = clean_numeric(out['Balance'])

    return out
