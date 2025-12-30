import pdfplumber
import pandas as pd
import re
from datetime import datetime


def can_handle(pdf_path, first_page_text):
    keywords = ["ANZ", "Australia and New Zealand Banking Group", "ANZ Plus"]
    return any(k.lower() in first_page_text.lower() for k in keywords)


def process_pdf(pdf_path):
    rows = []
    current_date = None
    current_desc = ""
    current_amt1 = None
    current_amt2 = None

    date_pattern = re.compile(r"^\d{1,2} [A-Za-z]{3}$")
    amount_pattern = re.compile(r"\$[0-9,]+\.\d{2}")

    year = datetime.now().year  # fallback default

    # ---------- Extract Year From Page 1 ----------
    with pdfplumber.open(pdf_path) as pdf:
        first_page_text = pdf.pages[0].extract_text()
        match = re.search(r"\d{1,2} [A-Za-z]+ (\d{4})", first_page_text)
        if match:
            year = int(match.group(1))

    def fix_date(d):
        parsed = datetime.strptime(d, "%d %b")
        parsed = parsed.replace(year=year)
        return parsed.strftime("%d-%m-%Y")

    # ---------- Process Transactions ----------
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue

            lines = [line.strip() for line in text.split("\n") if line.strip()]

            if "Date Description Credit Debit Balance" in lines:
                lines = lines[lines.index("Date Description Credit Debit Balance") + 1:]

            for line in lines:

                if "Australia and New Zealand Banking Group" in line or "Page " in line:
                    break

                parts = line.split()
                possible_date = " ".join(parts[:2])

                if date_pattern.match(possible_date):
                    if current_date and current_amt1 and current_amt2:

                        if any(w in current_desc.upper() for w in ["FROM", "DEPOSIT", "REFUND"]):
                            credit = current_amt1
                            debit = None
                        else:
                            debit = current_amt1
                            credit = None

                        desc_clean = re.sub(r"\$[0-9,]+\.\d{2}", "", current_desc)
                        desc_clean = re.sub(r"Please check.*", "", desc_clean, flags=re.IGNORECASE)
                        desc_clean = " ".join(desc_clean.split()).strip()

                        rows.append([
                            fix_date(current_date),
                            desc_clean,
                            float(credit) if credit else None,
                            float(debit) if debit else None,
                            float(current_amt2)
                        ])

                    current_date = possible_date
                    current_desc = " ".join(parts[2:])
                    current_amt1 = None
                    current_amt2 = None

                else:
                    if not amount_pattern.search(line):
                        current_desc += " " + line

                amounts = amount_pattern.findall(line)
                if len(amounts) == 2:
                    current_amt1 = amounts[0].replace("$", "").replace(",", "")
                    current_amt2 = amounts[1].replace("$", "").replace(",", "")

        # Save last transaction
        if current_date and current_amt1 and current_amt2:
            if any(w in current_desc.upper() for w in ["FROM", "DEPOSIT", "REFUND"]):
                credit = current_amt1
                debit = None
            else:
                debit = current_amt1
                credit = None

            desc_clean = re.sub(r"\$[0-9,]+\.\d{2}", "", current_desc)
            desc_clean = re.sub(r"Please check.*", "", desc_clean, flags=re.IGNORECASE)
            desc_clean = " ".join(desc_clean.split()).strip()

            rows.append([
                fix_date(current_date),
                desc_clean,
                float(credit) if credit else None,
                float(debit) if debit else None,
                float(current_amt2)
            ])

    df = pd.DataFrame(rows, columns=["Date", "Description", "Credit", "Debit", "Balance"])
    return df
