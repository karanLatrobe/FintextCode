import pdfplumber
import re
import pandas as pd


def can_handle(pdf_path, first_page_text):
    """
    Identify if this PDF belongs to Suncorp Bank.
    """
    keywords = ["SUNCORP", "Suncorp Bank", "suncorpbank.com"]
    return any(k.lower() in first_page_text.lower() for k in keywords)


def process_pdf(pdf_path):
    """
    Extracts and cleans Suncorp Bank transactions from a PDF statement.
    Returns a pandas DataFrame.
    """

    transactions = []
    header = "Date Transaction Details Withdrawal Deposit Balance"

    FOOTER_KEYWORDS = [
        "Statement No:", "Details are continued", "Suncorp Bank",
        "Norfina", "GPO Box", "Brisbane", "AFSL", "Page",
        "contact us", "complaint", "Important information",
        "Protecting your property", "Sun Logo", "Summary of Interest"
    ]

    def clean_footer_text(text):
        clean_lines = []
        for line in text.splitlines():
            if any(k.lower() in line.lower() for k in FOOTER_KEYWORDS):
                break
            clean_lines.append(line)
        return "\n".join(clean_lines)

    def extract_amounts(line):
        return re.findall(r"[\d,]+\.\d{2}", line)

    def normalize_amount(val):
        try:
            return float(val.replace(",", ""))
        except:
            return None

    with pdfplumber.open(pdf_path) as pdf:
        print("✅ Total Pages:", len(pdf.pages))
        prev_balance = None
        carried_line = None

        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()
            if not text or header not in text:
                print(f"⚠️ Header not found on page {page_num}")
                continue

            text = text.split(header, 1)[1].strip()
            text = clean_footer_text(text)
            if "CLOSING BALANCE" in text.upper():
                text = text.split("CLOSING BALANCE")[0] + "CLOSING BALANCE"

            lines = [l.strip() for l in text.splitlines() if l.strip()]
            current = None
            page_transactions = []

            for line in lines:
                upper_line = line.upper()

                # Handle forward/brought lines
                if "BALANCE CARRIED FORWARD" in upper_line:
                    carried_line = ["", line.strip(), "", "", extract_amounts(line)[-1]]
                    continue
                if "BALANCE BROUGHT FORWARD" in upper_line:
                    transactions.append(["", line.strip(), "", "", extract_amounts(line)[-1]])
                    continue

                # Handle balance-only lines
                if any(k in upper_line for k in ["OPENING BALANCE", "CLOSING BALANCE"]) and extract_amounts(line):
                    amt = extract_amounts(line)[-1]
                    page_transactions.append(["", line.strip(), "", "", amt])
                    prev_balance = normalize_amount(amt)
                    continue

                # Detect dated transaction lines
                date_match = re.match(r"^(\d{1,2}\s\w+\s\d{4})\s+(.*)", line)
                if date_match:
                    if current:
                        page_transactions.append(current)

                    date = date_match.group(1)
                    rest = date_match.group(2)
                    amts = extract_amounts(rest)
                    particulars = re.sub(r"[\d,]+\.\d{2}", "", rest).strip()

                    debit, credit, balance = "", "", ""
                    if len(amts) == 2:
                        first_val = normalize_amount(amts[0])
                        last_val = normalize_amount(amts[1])
                        if prev_balance is not None and last_val is not None:
                            if last_val < prev_balance:
                                debit = amts[0]
                            else:
                                credit = amts[0]
                        else:
                            credit = amts[0]
                        balance = amts[1]
                        prev_balance = last_val
                    elif len(amts) == 1:
                        balance = amts[0]
                        prev_balance = normalize_amount(balance)

                    current = [date, particulars, debit, credit, balance]
                else:
                    if current:
                        current[1] += " " + line.strip()

            if current:
                page_transactions.append(current)

            # Add carried forward line at the end of the page
            if carried_line:
                page_transactions.append(carried_line)
                carried_line = None

            transactions.extend(page_transactions)

    # Build and clean DataFrame
    df = pd.DataFrame(transactions, columns=["Date", "Particulars", "Debit", "Credit", "Balance"])

    df["Date"] = df["Date"].fillna("").str.strip()
    df["Particulars"] = df["Particulars"].fillna("").str.replace(r"\s+", " ", regex=True)
    df["Debit"] = df["Debit"].fillna("").str.replace(",", "")
    df["Credit"] = df["Credit"].fillna("").str.replace(",", "")
    df["Balance"] = df["Balance"].fillna("").str.replace(",", "")

    # Remove footer junk
    df = df[~df["Particulars"].str.contains("Statement No|Suncorp|Page|GPO|complaint", case=False, na=False)]

    print(f"\n🎉 Suncorp Bank extraction complete — {len(df)} transactions extracted.")
    print(df.head(15))


    df = df[~df["Particulars"].str.contains("Statement No|Suncorp|Page|GPO|complaint", case=False, na=False)]

    # Convert date to dd-mm-yyyy format
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.strftime("%d-%m-%Y")

    print(f"\n🎉 Suncorp Bank extraction complete — {len(df)} transactions extracted.")
    print(df.head(15))

    return df
