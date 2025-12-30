import os
import pickle
import pandas as pd
import requests
import numpy as np

from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import LabelEncoder

# ============================================================
# BASE DIR
# ============================================================
def get_base_dir():
    try:
        from django.conf import settings
        if settings.configured:
            return settings.BASE_DIR
    except Exception:
        pass
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BASE_DIR = get_base_dir()

# ============================================================
# PATHS
# ============================================================
TRAINING_DIR = os.path.join(BASE_DIR, "TrainingFile")
MODEL_DIR = os.path.join(BASE_DIR, "models")

TRAINING_CSV = os.path.join(TRAINING_DIR, "TrainingFile.csv")

SVM_MODEL_PATH = os.path.join(MODEL_DIR, "svm_model.pkl")
LE_PATH = os.path.join(MODEL_DIR, "label_encoder.pkl")

os.makedirs(TRAINING_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)

# ============================================================
# OLLAMA CONFIG (TRAINING ONLY)
# ============================================================
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma:7b"

def call_ollama(prompt):
    try:
        r = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.2}
            },
            timeout=120
        )
        return r.json().get("response", "").strip()
    except:
        return ""

def build_prompt(txn, known_labels):
    return f"""
You are a financial transaction categorization expert.

Rules:
- Choose ONLY from Known Labels.
- Do NOT invent new categories.
- Output ONLY the category name.

Known Labels:
{known_labels}

Transaction:
"{txn}"
"""

# ============================================================
# LOAD DATA
# ============================================================
if not os.path.exists(TRAINING_CSV):
    raise FileNotFoundError("TrainingFile.csv not found")

df = pd.read_csv(TRAINING_CSV)
df["Transaction_clean"] = df["Transaction_clean"].astype(str)
df["Account"] = df["Account"].astype(str)

# ============================================================
# INITIAL SVM (FOR CONFIDENCE ESTIMATION)
# ============================================================
le_temp = LabelEncoder()
y_temp = le_temp.fit_transform(df["Account"])

temp_pipeline = Pipeline([
    ("tfidf", TfidfVectorizer(stop_words="english")),
    ("svm", LinearSVC(class_weight="balanced"))
])

temp_pipeline.fit(df["Transaction_clean"], y_temp)

# ============================================================
# LOW CONFIDENCE ROWS → OLLAMA
# ============================================================
scores = temp_pipeline.decision_function(df["Transaction_clean"])
margins = np.max(np.abs(scores), axis=1)

LOW_CONF_THRESHOLD = 0.6
known_labels = "\n".join(sorted(df["Account"].unique()))

print("🤖 Refining low-confidence rows using Ollama...")

for i, margin in enumerate(margins):
    if margin < LOW_CONF_THRESHOLD:
        txn = df.at[i, "Transaction_clean"]

        prompt = build_prompt(txn, known_labels)
        suggested = call_ollama(prompt)

        if suggested and suggested in known_labels:
            df.at[i, "Account"] = suggested

# ============================================================
# FINAL TRAINING (FAST SVM)
# ============================================================
le = LabelEncoder()
y = le.fit_transform(df["Account"])

pipeline = Pipeline([
    ("tfidf", TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        max_features=7000,
        min_df=2
    )),
    ("svm", LinearSVC(
        C=1.0,
        class_weight="balanced",
        random_state=42
    ))
])

print("🚀 Training final SVM model...")
pipeline.fit(df["Transaction_clean"], y)

# ============================================================
# SAVE
# ============================================================
with open(SVM_MODEL_PATH, "wb") as f:
    pickle.dump(pipeline, f)

with open(LE_PATH, "wb") as f:
    pickle.dump(le, f)

print("✅ Training completed with Ollama enrichment")
print("📁 Saved:")
print(" - models/svm_model.pkl")
print(" - models/label_encoder.pkl")
