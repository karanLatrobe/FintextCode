import pdfplumber
import pandas as pd
import re
from datetime import datetime


def can_handle(pdf_path, first_page_text):
    """
    Identify if this PDF belongs to Bendigo Bank.
    """
    keywords = ["BENDIGO BANK", "bendigobank.com", "Bendigo and Adelaide Bank"]
    return any(k.lower() in first_page_text.lower() for k in keywords)


def process_pdf(pdf_path):
    """
    Extracts Bendigo Bank transactions and returns a cleaned DataFrame.
    """

    def clean_amount(value):
        if value is None:
            return None
        s = str(value).replace(",", "").replace("$", "").strip()
        if not s:
            return None
        try:
            return float(s)
        except:
            return None

    # Checks if text matches transaction date format e.g. "09 Apr 25"
    def is_date(text):
        return bool(re.match(r"^\d{1,2}\s+\w+\s+\d{2}$", str(text).strip()))

    # Convert "09 Apr 25" → "09-04-2025"
    def convert_date(date_str):
        try:
            d = datetime.strptime(date_str, "%d %b %y")
            return d.strftime("%d-%m-%Y")
        except:
            return date_str

    def extract_amounts(line):
        return re.findall(r"\d{1,3}(?:,\d{3})*\.\d{2}", line)

    records = []
    opening_balance_value = None

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text(x_tolerance=2, y_tolerance=3)
            if not text:
                continue

            m = re.search(r"Opening\s+balance\s+\$?([\d,]+\.\d{2})", text, flags=re.IGNORECASE)
            if m:
                opening_balance_value = clean_amount(m.group(1))

            lines = text.split("\n")
            inside_table = False
            current_date, particulars, amount_parsed, balance_parsed = None, "", None, None

            for line in lines:
                line = line.strip()
                if "Date Transaction Withdrawals Deposits Balance" in line:
                    inside_table = True
                    continue
                if not inside_table or not line:
                    continue

                if any(x in line.lower() for x in [
                    "transaction totals", "opening balance", "continued",
                    "bendigobank.com", "bendigoadelaide", "statement number"
                ]):
                    continue

                parts = line.split()
                date_candidate = " ".join(parts[:3]) if len(parts) >= 3 else ""

                if is_date(date_candidate):

                    if current_date and particulars:
                        records.append([current_date, particulars.strip(), amount_parsed, balance_parsed])

                    current_date = convert_date(date_candidate)  # ← Date now converted here
                    particulars = " ".join(parts[3:])

                    nums = extract_amounts(line)
                    if nums:
                        balance_parsed = clean_amount(nums[-1])
                        if len(nums) >= 2:
                            amount_parsed = clean_amount(nums[-2])
                        else:
                            amount_parsed = None
                    else:
                        amount_parsed, balance_parsed = None, None

                else:
                    particulars += " " + line

            if current_date and particulars:
                records.append([current_date, particulars.strip(), amount_parsed, balance_parsed])


    df = pd.DataFrame(records, columns=["Date", "Particular", "Amount_parsed", "Balance"])
    df.dropna(subset=["Balance"], inplace=True)
    df["Balance"] = df["Balance"].astype(float)
    df["Amount_parsed"] = df["Amount_parsed"].astype(float)
    df.reset_index(drop=True, inplace=True)

    def clean_particular_text(text):
        text = re.sub(r"\d{1,3}(?:,\d{3})*\.\d{2}", "", text)
        text = re.sub(r"\s+", " ", text).strip(" .,-")
        return text

    df["Particular"] = df["Particular"].apply(clean_particular_text)
    df["Prev_Balance"] = df["Balance"].shift(1)

    if opening_balance_value:
        df.loc[0, "Prev_Balance"] = opening_balance_value

    debit, credit = [], []
    for _, row in df.iterrows():
        prev_bal, curr_bal, amount = row["Prev_Balance"], row["Balance"], row["Amount_parsed"]

        if pd.isna(prev_bal) or pd.isna(curr_bal):
            debit.append(None)
            credit.append(None)
        elif curr_bal < prev_bal:
            debit.append(amount)
            credit.append(None)
        elif curr_bal > prev_bal:
            debit.append(None)
            credit.append(amount)
        else:
            if amount == 0:
                debit.append(None)
                credit.append(0)
            else:
                debit.append(None)
                credit.append(None)

    df["Debit"] = debit
    df["Credit"] = credit
    df = df[["Date", "Particular", "Debit", "Credit", "Balance"]]

    if opening_balance_value:
        opening_row = pd.DataFrame(
            [[None, "Opening Balance", None, None, opening_balance_value]], columns=df.columns
        )
        df = pd.concat([opening_row, df], ignore_index=True)

    closing_row = pd.DataFrame(
        [[None, "Closing Balance", None, None, df["Balance"].iloc[-1]]], columns=df.columns
    )
    df = pd.concat([df, closing_row], ignore_index=True)

    print("\n🎉 Clean extraction complete with formatted Date (dd-mm-yyyy)")
    print(df.head(10))

    return df
