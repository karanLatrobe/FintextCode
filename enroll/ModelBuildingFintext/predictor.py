import os
import torch
import pandas as pd
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

# ============================================================
# PATHS
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_NAME = "karan8920/FIINTEXT-Model" # trained model folder

# if not os.path.isdir(MODEL_FOLDER):
#     raise FileNotFoundError(f"Model folder not found: {MODEL_FOLDER}")

# ============================================================
# LOAD MODEL + TOKENIZER ONCE
# ============================================================
device = "cuda" if torch.cuda.is_available() else "cpu"

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME)
model = model.to(device)
model.eval()

# ============================================================
# SINGLE PREDICTION FUNCTION
# ============================================================
def _predict_single(text):
    prompt = (
        "You are an expert financial transaction categorization AI.\n"
        "Read the transaction carefully.\n"
        "Predict the correct category learned from training.\n"
        "Return ONLY the category name.\n\n"
        f"Transaction:\n{text}\n\n"
        "Category:"
    )

    inp = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
    inp = {k: v.to(device) for k, v in inp.items()}

    with torch.no_grad():
        out = model.generate(
            **inp,
            max_new_tokens=20,
            output_scores=True,
            return_dict_in_generate=True,
            do_sample=False
        )

    pred = tokenizer.decode(out.sequences[0], skip_special_tokens=True).strip()

    last_logits = out.scores[-1]
    last_token_id = out.sequences[0][-1].item()

    probs = F.softmax(last_logits, dim=-1)
    conf = probs[0][last_token_id].item()

    return pred, conf

# ============================================================
# AUTO-DETECT COLUMNS
# ============================================================
def _detect_columns(df):
    txn_keys = {"transaction", "particular", "description", "narration", "details", "particulars"}
    debit_keys = {"debit", "debit amount", "dr", "withdrawal"}
    credit_keys = {"credit", "credit amount", "cr", "deposit"}

    cols = list(df.columns)

    def find(keys):
        for c in cols:
            if c.strip().lower() in keys:
                return c
        for c in cols:
            if any(k in c.lower() for k in keys):
                return c
        return None

    txn = find(txn_keys)
    debit = find(debit_keys)
    credit = find(credit_keys)

    if txn is None:
        for c in cols:
            if df[c].dtype == object:
                txn = c
                break

    return txn, debit, credit

# ============================================================
# PUBLIC FUNCTION – PROCESS WHOLE DATAFRAME
# ============================================================
def predict_for_dataframe(df, verbose=False):
    df = df.copy()
    txn_col, debit_col, credit_col = _detect_columns(df)

    if txn_col is None:
        raise ValueError("❌ No transaction-like column found.")

    preds = []
    confs = []

    total = len(df)

    for i, row in df.iterrows():
        text = str(row.get(txn_col, ""))

        if debit_col:
            text += f"\nDebit: {row.get(debit_col)}"
        if credit_col:
            text += f"\nCredit: {row.get(credit_col)}"

        try:
            p, c = _predict_single(text)
        except:
            p, c = "Prediction Error", 0.0

        preds.append(p)
        confs.append(round(c * 100, 2))

        if verbose and (i+1) % 50 == 0:
            print(f"Processed {i+1}/{total}")

    df["Predicted_Category"] = preds
    df["Confidence(%)"] = confs
    return df
