import pdfplumber
import pandas as pd
import re


# ----------------------------------------------------
# 1. CHECK IF THIS PDF BELONGS TO ANZ BUSINESS ACCOUNT
# ----------------------------------------------------
def can_handle(pdf_path, first_page_text):
    return "ANZ BUSINESS ESSENTIALS STATEMENT" in first_page_text


# ----------------------------------------------------
# 2. MAIN PROCESSOR FUNCTION (FULL LOGIC INSIDE)
# ----------------------------------------------------
def process_pdf(pdf_path):

    # -------- Extract first page for YEAR -----------
    with pdfplumber.open(pdf_path) as pdf_check:
        first_page = pdf_check.pages[0].extract_text()

    year_match = re.search(r"\b(20\d{2})\b", first_page)
    YEAR = year_match.group(1)

    month_map = {
        "JAN":"01","FEB":"02","MAR":"03","APR":"04","MAY":"05","JUN":"06",
        "JUL":"07","AUG":"08","SEP":"09","OCT":"10","NOV":"11","DEC":"12"
    }

    # -------- date converter --------
    def convert_date(d):
        day, mon = d.split()
        return f"{day}-{month_map[mon]}-{YEAR}"

    # -------- float converter --------
    def to_float(x):
        if not x or x == "blank": return 0.0
        return float(x.replace(",", ""))

    # -------- description cleaner --------
    def clean_desc(text):
        text = re.sub(r"Withdrawals \(\$\).*", "", text)
        text = re.sub(r"XPRCAP\d+-\d+", "", text)
        text = re.sub(r"RTBSP\d+", "", text)
        text = re.sub(r"\b\d{1,3}(?:,\d{3})*(?:\.\d{1,2})\b", "", text)
        text = text.replace("blank", "")
        return " ".join(text.split()).strip()

    # ----- VARIABLES FOR PARSING -----
    transactions = []
    current_date = None
    details = []
    withdrawal = deposit = balance = ""

    # ----------------------------------------------------
    #      PARSING LOGIC (unchanged — exact copy)
    # ----------------------------------------------------
    with pdfplumber.open(pdf_path) as pdf:
        for pg in pdf.pages:
            txt = pg.extract_text()
            if "Date Transaction Details" not in txt:
                continue

            lines = txt.split("\n")
            reading = False

            for line in lines:
                line = line.strip()

                if "Date Transaction Details" in line:
                    reading = True
                    continue

                if not reading or not line or line == "2024":
                    continue

                if ("TOTALS AT END" in line) or line.startswith("Page"):
                    continue

                if "Withdrawals ($)" in line and "Deposits ($)" in line:
                    continue

                date_match = re.match(r"^(\d{2} \w{3})", line)
                if date_match:

                    if current_date and details:
                        merged = " ".join(details)

                        if "OPENING BALANCE" in merged.upper():
                            amt = re.search(r"([\d,]+\.\d{2})", merged)
                            if amt:
                                balance = amt.group(1)

                        desc = clean_desc(merged)

                        transactions.append({
                            "Date": convert_date(current_date),
                            "Transaction Details": desc,
                            "Withdrawals": to_float(withdrawal),
                            "Deposits": to_float(deposit),
                            "Balance": to_float(balance)
                        })

                    current_date = date_match.group(1)
                    details = []
                    withdrawal = deposit = balance = ""
                    line = line.replace(current_date, "").strip()

                m = re.search(
                    r"([\d.,]+|blank)\s+([\d.,]+|blank)\s+([\d.,]+)$",
                    line
                )
                if m:
                    withdrawal = m.group(1)
                    deposit = m.group(2)
                    balance = m.group(3)

                    left = line[:line.rfind(m.group(3))].strip()
                    if left:
                        details.append(left)
                else:
                    details.append(line)

    # ---- SAVE LAST ROW ----
    if current_date and details:
        merged = " ".join(details)

        if "OPENING BALANCE" in merged.upper():
            amt = re.search(r"([\d,]+\.\d{2})", merged)
            if amt:
                balance = amt.group(1)

        desc = clean_desc(merged)

        transactions.append({
            "Date": convert_date(current_date),
            "Transaction Details": desc,
            "Withdrawals": to_float(withdrawal),
            "Deposits": to_float(deposit),
            "Balance": to_float(balance)
        })

    # ----------------------------------------------------
    #      FINAL CLEANING + RENAMING (unchanged)
    # ----------------------------------------------------
    df = pd.DataFrame(transactions)

    df = df.rename(columns={
        "Date": "Date",
        "Transaction Details": "Particular",
        "Withdrawals": "Debit",
        "Deposits": "Credit",
        "Balance": "Balance"
    })

    print("\n🎉 ANZ extraction complete!")
    print(df.head(10))

    return df
