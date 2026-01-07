import pdfplumber
import re
import importlib
import pandas as pd
from pathlib import Path


def clean_old_excels(output_dir):
    for f in output_dir.glob("*.xlsx"):
        try:
            f.unlink()   # delete file
        except:
            pass
# ===================================================
# 🏦 1️⃣ PERFECT BANK DETECTION SYSTEM (FINAL)
# ===================================================


def detect_bank_name(pdf_path):
    pdf_path = Path(pdf_path)

    try:
        with pdfplumber.open(pdf_path) as pdf:
            pages_text = ""
            for i in range(min(2, len(pdf.pages))):
                txt = pdf.pages[i].extract_text() or ""
                pages_text += "\n" + txt.lower()
    except:
        return "Unknown"

    # ======================================================
    # 🔥 STRICT NAB CREDIT CARD DETECTION (SAFE)
    # ======================================================
    if "nab qantas business signature" in pages_text:
        return "NAB Credit Card"

    if "nab commercial cards centre" in pages_text:
        return "NAB Credit Card"

    if "transaction record for:" in pages_text and "amount not" in pages_text:
        return "NAB Credit Card"

    if ("amount not" in pages_text and
        "gst component" in pages_text and
        "reference" in pages_text and
        "details" in pages_text and
        "amount $" in pages_text):
        return "NAB Credit Card"

    # ======================================================
    # 🟦 COMMONWEALTH DETECTION
    # ======================================================
    if "Commonwealth" or "commonwealth" in pages_text:
        if "ultimate awards credit card" or "Low Rate Mastercard" or "Low Rate Mastercard ® Credit Card" or "Low Rate" or "Credit Card" or "Commonwealth credit card" in pages_text:
            return "Commonwealth Credit Card"

    if "commonwealth" in pages_text or "commbank" in pages_text:
        return "Commonwealth Bank"

    # ======================================================
    # 🟨 ANZ DETECTION
    # ======================================================
    if "anz business essentials statement" in pages_text:
        return "ANZ Business Essentials"

    if "anz plus" in pages_text:
        return "ANZ Plus"

    # ======================================================
    # 🟪 BENDIGO DETECTION
    # ======================================================
    if "bendigo" in pages_text or "bendigobank" in pages_text:
        return "Bendigo Bank"

    # ======================================================
    # 🟧 SUNCORP DETECTION
    # ======================================================
    if "suncorp" in pages_text:
        return "Suncorp Bank"

    # ======================================================
    # 🟥 WESTPAC DETECTION SYSTEM (FINAL)
    # ======================================================
    if "westpac" in pages_text:

        # -- WESTPAC CREDIT CARD (Altitude Mastercard)
        if ("altitude" in pages_text and "mastercard" in pages_text.replace("®", "")) \
           or ("altitude business platinum" in pages_text) \
           or ("credit card" in pages_text and "closing balance" in pages_text):
            return "Westpac Credit Card"

        # -- WESTPAC BUSINESS ACCOUNT
        if "westpac business one" in pages_text:
            return "Westpac Business One"

        # fallback
        return "Westpac Bank"

    return "Unknown"



# ===================================================
# ⚙️ 2️⃣ BANK → MODULE MAP (UPDATED)
# ===================================================
BANK_MODULES = {
    "ANZ Business Essentials": "enroll.utils.BankModules.ANZBusinessEssentials",
    "ANZ Plus": "enroll.utils.BankModules.ANZBankExtractor",

    "Bendigo Bank": "enroll.utils.BankModules.bendigoExtractor",

    "Commonwealth Bank": "enroll.utils.BankModules.CommonWealthExtractor",
    "Commonwealth Credit Card": "enroll.utils.BankModules.commonwealthcredit",

    "NAB Credit Card": "enroll.utils.BankModules.nabCredit",
    "NAB Bank": "enroll.utils.BankModules.nab",

    "Suncorp Bank": "enroll.utils.BankModules.suncorpExtractor",

    # ⭐⭐ NEW WESTPAC MAPPINGS ⭐⭐
    "Westpac Credit Card": "enroll.utils.BankModules.WestpacCredit",
    "Westpac Business One": "enroll.utils.BankModules.westpacBusinessExtractor",
    "Westpac Bank": "enroll.utils.BankModules.westpacBusinessExtractor",

    "Unknown": None
}



# ===================================================
# 🌟 3️⃣ PROCESS → RETURN EXCEL
# ===================================================
def process_pdf_and_return_output_path(pdf_path):
    pdf_path = Path(pdf_path)

    
    detected_bank = detect_bank_name(pdf_path)
    module_name = BANK_MODULES.get(detected_bank)

    if not module_name:
        raise ValueError(
            f"Unsupported or unknown bank PDF detected: {detected_bank}"
        )

    module = importlib.import_module(module_name)

    if not hasattr(module, "process_pdf"):
        raise ValueError(
            f"Extractor module '{module_name}' has no process_pdf()."
        )

    df = module.process_pdf(str(pdf_path))
    if not isinstance(df, pd.DataFrame):
        raise ValueError("Extractor did not return a valid DataFrame.")

    # Output folder
    output_dir = Path(__file__).resolve().parent / "outputs"
    output_dir.mkdir(exist_ok=True)

    # Numeric cleanup
    for col in ["Debit", "Credit", "Balance"]:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(",", "", regex=False)
                .str.replace("$", "", regex=False)
                .str.strip()
                .replace("-", "")
                .replace("", "")
            )

            df[col] = pd.to_numeric(df[col], errors="coerce")
            df[col] = df[col].where(df[col].notnull(), None)

    clean_old_excels(output_dir)
    clean_bank = detected_bank.replace(" ", "_")
    output_file = output_dir / f"{pdf_path.stem}_{clean_bank}.xlsx"

    df.to_excel(output_file, index=False)

    return str(output_file), df
