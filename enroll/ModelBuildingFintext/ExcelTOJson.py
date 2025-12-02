import pandas as pd
import json

df = pd.read_excel("Training.xlsx")

with open("dataset.jsonl", "w", encoding="utf8") as f:
    for idx, row in df.iterrows():
        instr = "Categorize this bank transaction."

        debit = row["Debit"] if not pd.isna(row["Debit"]) else 0
        credit = row["Credit"] if not pd.isna(row["Credit"]) else 0

        input_text = (
            f"Transaction: {row['Transaction']}\n"
            f"Debit: {debit}\n"
            f"Credit: {credit}"
        )

        output_text = row["Account"]

        record = {
            "instruction": instr,
            "input": input_text,
            "output": output_text
        }

        f.write(json.dumps(record, ensure_ascii=False) + "\n")

print("dataset.jsonl generated successfully!")
