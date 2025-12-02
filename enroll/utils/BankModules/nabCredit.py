import pdfplumber
import pandas as pd
import re
from datetime import datetime


# ------------------------------------------------------
# 1. CHECK IF PDF IS NAB CREDIT CARD STATEMENT
# ------------------------------------------------------
def can_handle(pdf_path, first_page_text):
    """
    Detect whether the PDF belongs to NAB Credit Card.
    Detection based on table headers.
    """
    headers = [
        "Date", "Amount$", "Details", "Explanation",
        "Amount NOT", "Amount subject to GST",
        "GST component", "Reference"
    ]

    text_lower = first_page_text.lower()
    return all(h.lower() in text_lower for h in ["date", "amount$", "details"])


# ------------------------------------------------------
# 2. MAIN PROCESS FUNCTION (same structure as Bendigo)
# ------------------------------------------------------
def process_pdf(pdf_path):

    # --- Helper: Clean Amount (Same name as Bendigo) ---
    def clean_amount(value):
        if value is None:
            return 0.0

        s = re.sub(r"[^0-9.\-]", "", str(value))
        if s in ["", "-", ".", "-."]:
            return 0.0

        try:
            return float(s)
        except:
            return 0.0

    # --- Helper: Detect Date (renamed same as Bendigo) ---
    def is_date(text):
        """
        NAB date format: 17Dec2024 → detect pattern ddMMMyyyy
        """
        return bool(re.match(r"^\d{1,2}[A-Za-z]{3}\d{4}$", text.strip()))

    # --- Helper: Convert Date ---
    def convert_date(date_str):
        """
        Convert 17Dec2024 → 17-12-2024
        """
        try:
            d = datetime.strptime(date_str, "%d%b%Y")
            return d.strftime("%d-%m-%Y")
        except:
            return date_str

    # --- (Not used in NAB but needed for uniform structure) ---
    def extract_amounts(line):
        return []  # not required for NAB table extraction

    # --- Clean Particular Text (same name as Bendigo) ---
    def clean_particular_text(text):
        text = re.sub(r"\s+", " ", str(text)).strip(" .,-")
        return text

    # ------------------------------------------------------
    # EXTRACT TABLE DATA
    # ------------------------------------------------------
    records = []

    with pdfplumber.open(pdf_path) as pdf:

        # Read first page text to validate the file
        first_page_text = pdf.pages[0].extract_text() or ""
        if not can_handle(pdf_path, first_page_text):
            raise ValueError("❌ This PDF does NOT seem to be NAB Credit Card Statement.")

        for page in pdf.pages:
            tables = page.extract_tables()
            if not tables:
                continue

            table = tables[0]

            # Skip header row
            for row in table[1:]:
                raw_date = row[0]
                raw_amount = row[1]
                raw_details = row[2]

                if not raw_date:
                    continue

                # Clean date & amount
                if is_date(raw_date):
                    date_clean = convert_date(raw_date)
                else:
                    date_clean = raw_date

                amount_clean = clean_amount(raw_amount)
                details_clean = clean_particular_text(raw_details)

                # Append a record
                records.append([
                    date_clean,
                    details_clean,
                    amount_clean
                ])

    # ------------------------------------------------------
    # CREATE FINAL DATAFRAME (Same layout as Bendigo)
    # ------------------------------------------------------
    df = pd.DataFrame(records, columns=["Date", "Particular", "Balance"])
    df["Debit"] = ""
    df["Credit"] = ""

    df = df[["Date", "Particular", "Debit", "Credit", "Balance"]]

    return df
