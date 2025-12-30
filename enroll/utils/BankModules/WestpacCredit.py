import pdfplumber
import pandas as pd
import numpy as np
import re
from datetime import datetime


def process_pdf(pdf_path):

    def clean_amount(x):
        if x is None or str(x).strip() == "" or str(x).strip() == "-":
            return np.nan
        x = re.sub(r"[^0-9.\-]", "", str(x))
        try:
            return float(x)
        except:
            return np.nan

    with pdfplumber.open(pdf_path) as pdf:
        tables = pdf.pages[2].extract_tables()

        for table in tables:
            for row in table:

                if (row[0] == 'Date of\nTransaction') and (row[1] == 'Description'):

                    mainRow = table[1]

                    date_list = [d.strip() for d in mainRow[0].split("\n") if d.strip()]
                    particulars_list = [p.strip() for p in mainRow[1].split("\n") if p.strip()]
                    debit_list = [d.strip() for d in mainRow[2].split("\n") if d.strip()]
                    credit_list = [c.strip() for c in mainRow[3].split("\n") if c.strip()]

                    n = len(particulars_list)

                    final_debit = [np.nan] * n
                    final_credit = [np.nan] * n

                    debit_idx = 0
                    credit_idx = 0

                    credit_keywords = ["PAYMENT", "REFUND", "CREDIT", "BPAY", "THANK YOU"]

                    for i, desc in enumerate(particulars_list):

                        desc_upper = desc.upper()

                        if any(k in desc_upper for k in credit_keywords):
                            if credit_idx < len(credit_list):
                                final_credit[i] = credit_list[credit_idx]
                                credit_idx += 1
                            continue

                        if debit_idx < len(debit_list):
                            final_debit[i] = debit_list[debit_idx]
                            debit_idx += 1

                    final_debit = [clean_amount(x) for x in final_debit]

                    cleaned_credit = []
                    for x in final_credit:
                        if pd.isna(x):
                            cleaned_credit.append(np.nan)
                        else:
                            cleaned = re.sub(r"[^0-9.]", "", str(x))
                            cleaned_credit.append(clean_amount(cleaned))

                    final_credit = cleaned_credit

                    balance = []
                    running = 0
                    for d, c in zip(final_debit, final_credit):
                        if not pd.isna(d):
                            running -= d
                        if not pd.isna(c):
                            running += c
                        balance.append(running)

                    df = pd.DataFrame({
                        "Date": date_list,
                        "Particular": particulars_list,
                        "Debit": final_debit,
                        "Credit": final_credit,
                        "Balance": balance
                    })

                    df["Date"] = pd.to_datetime(df["Date"], format="%d %b %y")
                    df["Date"] = df["Date"].dt.strftime("%d-%m-%Y")

                    return df

    return pd.DataFrame()
