import os
import pickle
import pandas as pd

# ============================================================
# BASE DIR RESOLUTION (Django + Standalone)
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
MODEL_DIR = os.path.join(BASE_DIR, "models")
TRAINING_EXCEL = os.path.join(BASE_DIR, "TrainingFile", "LatestTraining.xlsx")

SVM_MODEL_PATH = os.path.join(MODEL_DIR, "svm_model.pkl")
LE_PATH = os.path.join(MODEL_DIR, "label_encoder.pkl")

# ============================================================
# LOAD MODEL
# ============================================================
if not os.path.exists(SVM_MODEL_PATH):
    raise FileNotFoundError(f"Missing model: {SVM_MODEL_PATH}")

if not os.path.exists(LE_PATH):
    raise FileNotFoundError(f"Missing encoder: {LE_PATH}")

with open(SVM_MODEL_PATH, "rb") as f:
    SVM_PIPELINE = pickle.load(f)

with open(LE_PATH, "rb") as f:
    LABEL_ENCODER = pickle.load(f)

print("⚡ FAST SVM model loaded successfully")

# ============================================================
# FAST PREDICTION FUNCTION
# ============================================================
def fast_predict_latest_excel():
    if not os.path.exists(TRAINING_EXCEL):
        print(f"⚠ File not found: {TRAINING_EXCEL}")
        return

    df = pd.read_excel(TRAINING_EXCEL)

    if df.shape[1] < 2:
        print("⚠ Invalid Excel format (Transaction column missing)")
        return

    # 🔥 RULE: transaction text ALWAYS second column
    texts = df.iloc[:, 1].fillna("").astype(str)

    preds = SVM_PIPELINE.predict(texts)
    df["Account Type"] = LABEL_ENCODER.inverse_transform(preds)

    df.to_excel(TRAINING_EXCEL, index=False)
    print("✅ Prediction completed FAST")

# ============================================================
# STANDALONE RUN
# ============================================================
if __name__ == "__main__":
    fast_predict_latest_excel()
