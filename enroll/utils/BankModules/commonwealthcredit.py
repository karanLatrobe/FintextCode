import pdfplumber
import pandas as pd
import re
from datetime import datetime

# ==========================================================
# 1. CAN_HANDLE → detect if PDF belongs to Commonwealth Credit Card
# ==========================================================
def can_handle(pdf_path, first_page_text):
    """
    Identify if this PDF belongs to Commonwealth Ultimate Awards Credit Card.
    STRUCTURE SAME AS BENDIGO can_handle()
    """

    main_keyword = "Ultimate Awards Credit Card"

    other_keywords = [
        "Available credit",
        "Minimum payment",
        "Total amount owing",
        "transactions and charges",
        "Payment Received"
    ]

    text = first_page_text.lower()

    if main_keyword.lower() in text:
        return True

    if any(k.lower() in text for k in other_keywords):
        return True

    return False



# ==========================================================
# 2. PROCESS_PDF → Extract transactions (RETURN DataFrame)
# ==========================================================
def process_pdf(pdf_path):
    """
    Extracts Commonwealth Credit Card transactions and returns DataFrame.
    STRUCTURE SAME AS BENDIGO'S process_pdf()
    """

    date_pattern = re.compile(r"^\s*\d{1,2}\s*[A-Za-z]{3}")

    def is_amount(value):
        """Check if last token is a valid numeric amount."""
        value = value.replace(",", "").replace("-", "")
        return value.replace('.', '', 1).isdigit()

    # =====================================================
    # A. RAW LINE EXTRACTION — (100% same logic you used)
    # =====================================================
    raw_rows = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue

            for line in text.split("\n"):
                line = line.strip()

                if not date_pattern.match(line):
                    continue

                parts = line.split()

                raw_amount = parts[-1]

                if not is_amount(raw_amount.replace("$", "")):
                    continue

                clean_amt = raw_amount.replace("$", "").replace(",", "")
                amount = -float(clean_amt[:-1]) if clean_amt.endswith("-") else float(clean_amt)

                date = parts[0] + " " + parts[1]
                desc = " ".join(parts[2:-1]).strip()

                raw_rows.append([date, desc, amount])

    # =====================================================
    # B. YEAR DETECTION
    # =====================================================
    year = None
    for _, desc, _ in raw_rows:
        yr = re.search(r"20\d{2}", desc)
        if yr:
            year = yr.group()
            break
    if not year:
        year = "2023"

    # =====================================================
    # C. CONVERT DATE → dd-mm-yyyy
    # =====================================================
    month_map = {
        "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04", "May": "05", "Jun": "06",
        "Jul": "07", "Aug": "08", "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12"
    }

    converted = []
    for dt, desc, amt in raw_rows:
        d, m = dt.split()
        dd = d.zfill(2)
        mm = month_map.get(m, "01")
        new_date = f"{dd}-{mm}-{year}"
        converted.append([new_date, desc, amt])

    # =====================================================
    # D. REMOVE ONLY TIME-PERIOD GARBAGE LINES
    # =====================================================
    bad_keywords = [
        "2023- 15 Sep", "2023-", "15 Sep",
        "Available credit", "minimum payment",
        "Total amount owing", "saving", "balance", "Tot", "years"
    ]

    cleaned = []
    for date, desc, amt in converted:
        if any(b.lower() in desc.lower() for b in bad_keywords):
            continue
        cleaned.append([date, desc, amt])

    # =====================================================
    # E. CONVERT TO DATAFRAME
    # =====================================================
    df = pd.DataFrame(cleaned, columns=["Date", "Particular", "Amount"])

    # =====================================================
    # F. CREATE DEBIT, CREDIT, BALANCE (Running)
    # =====================================================
    balances = []
    debit = []
    credit = []

    running_balance = 0

    for _, row in df.iterrows():
        amt = row["Amount"]
        running_balance += amt

        balances.append(running_balance)
        debit.append(amt if amt > 0 else None)
        credit.append(abs(amt) if amt < 0 else None)

    df["Debit"] = debit
    df["Credit"] = credit
    df["Balance"] = balances

    df = df[["Date", "Particular", "Debit", "Credit", "Balance"]]

    print("\n🎉 Clean extraction complete for Commonwealth Credit Card")
    print(df.head(10))

    return df
