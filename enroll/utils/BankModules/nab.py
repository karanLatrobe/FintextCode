import pdfplumber
import pandas as pd
from dateutil import parser as dateparser
import re
from pathlib import Path

# ================================================================
# This extractor dynamically detects tabular transaction layouts
# and works for general/unidentified bank statement formats.
# ================================================================

HEADER_ALIASES = {
    "date": {"date", "txn date", "value date","Date"},
    "transaction": {
        "transaction", "particulars", "description",
        "transaction description", "narration", "details","Particulars"
    },
    "debit": {"debit", "withdrawal", "debits", "amount withdrawn", "debit amt","Withdrawals"},
    "credit": {"credit", "deposit", "credits", "amount deposited", "credit amt","Deposits"},
    "balance": {"balance", "closing balance", "running balance","Balance"},
}

AMOUNT_RE = re.compile(r"[-]?\$?\s*\(?\d[\d,]*\.\d{2}\)?")

def can_handle(pdf_path, first_page_text):
    """
    Default fallback extractor — used when no specific bank match found.
    """
    return True  # acts as a universal handler


def process_pdf(pdf_path):
    """
    Extracts transactions generically using header detection and column bucketing.
    Returns a cleaned pandas DataFrame.
    """

    def normalize_header(token: str) -> str:
        t = token.strip().lower()
        for std, names in HEADER_ALIASES.items():
            if any(t == n or t.replace(" ", "") == n.replace(" ", "") for n in names):
                return std
        return ""

    def amount_to_float(s: str | None) -> float | None:
        if not s:
            return None
        s = s.replace("$", "").replace(",", "").strip()
        neg = s.startswith("-") or s.endswith("-") or s.startswith("(") or s.endswith(")")
        s = s.replace("(", "").replace(")", "").replace("-", "")
        try:
            v = float(s)
            return -v if neg else v
        except:
            return None

    def clean_balance_text(s: str | None) -> str | None:
        if not s:
            return None
        s = s.replace("CR", "").replace("DR", "").replace("$", "").strip()
        return s

    def parse_date_safe(s: str | None):
        if not s:
            return None
        s = s.strip()
        try:
            return dateparser.parse(s, dayfirst=True, fuzzy=True).date()
        except:
            return None

    def row_is_header(words_line):
        joined = " ".join(w["text"] for w in words_line).lower()
        hits = 0
        for names in HEADER_ALIASES.values():
            if any(n in joined for n in names):
                hits += 1
        return hits >= 3

    def build_column_boundaries(words_line):
        tagged = []
        for w in words_line:
            std = normalize_header(w["text"])
            if std:
                x_center = (w["x0"] + w["x1"]) / 2
                tagged.append((std, x_center))
        dedup = {}
        for std, xc in sorted(tagged, key=lambda t: t[1]):
            dedup.setdefault(std, xc)
        order = []
        for key in ["date", "transaction", "debit", "credit", "balance"]:
            if key in dedup:
                order.append((key, dedup[key]))
        if len(order) < 3:
            return [], []
        centers = [xc for _, xc in order]
        splits = [(a + b) / 2.0 for a, b in zip(centers[:-1], centers[1:])]
        return order, splits

    def bucket_by_columns(words_line, order, splits):
        cols = {name: [] for name, _ in order}
        for w in words_line:
            x_center = (w["x0"] + w["x1"]) / 2.0
            idx = 0
            while idx < len(splits) and x_center > splits[idx]:
                idx += 1
            name = order[min(idx, len(order) - 1)][0]
            cols[name].append(w["text"])
        return {k: " ".join(v).strip() for k, v in cols.items()}

    def merge_continuation_rows(rows):
        merged = []
        for r in rows:
            if merged and not r.get("Date"):
                if r.get("Transaction"):
                    merged[-1]["Transaction"] = (
                        merged[-1]["Transaction"] + " " + r["Transaction"]
                    ).strip()
                if r.get("Debit"):
                    merged[-1]["Debit"] = r["Debit"]
                if r.get("Credit"):
                    merged[-1]["Credit"] = r["Credit"]
                if r.get("Balance") and not merged[-1].get("Balance"):
                    merged[-1]["Balance"] = r["Balance"]
            else:
                merged.append(r)
        return merged
    
    def extract_transactions_from_page(page):
        words = page.extract_words(use_text_flow=True, keep_blank_chars=False)
        if not words:
            return []
        lines, current, prev_mid = [], [], None
        tol = 3.0
        for w in words:
            mid = (w["top"] + w["bottom"]) / 2.0
            if prev_mid is None or abs(mid - prev_mid) <= tol:
                current.append(w)
                prev_mid = mid if prev_mid is None else (prev_mid + mid) / 2.0
            else:
                lines.append(current)
                current = [w]
                prev_mid = mid
        if current:
            lines.append(current)
        header_idx = None
        for i, line in enumerate(lines):
            if row_is_header(line):
                header_idx = i
                break
        if header_idx is None:
            return []
        order, splits = build_column_boundaries(lines[header_idx])
        if not order:
            return []
        rows = []
        for line in lines[header_idx + 1:]:
            buckets = bucket_by_columns(line, order, splits)
            out = {
                "Date": buckets.get("date", "") or "",
                "Transaction": buckets.get("transaction", "") or "",
                "Debit": buckets.get("debit", "") or "",
                "Credit": buckets.get("credit", "") or "",
                "Balance": buckets.get("balance", "") or "",
            }
            if not any(out.values()):
                continue
            rows.append(out)
        return rows

    # Main logic
    all_rows = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            rows = extract_transactions_from_page(page)
            all_rows.extend(rows)

    if not all_rows:
        raise RuntimeError("No tabular data detected in PDF.")

    merged = merge_continuation_rows(all_rows)

    cleaned_rows = []
    for r in merged:
        d = parse_date_safe(r.get("Date"))
        bal_txt = clean_balance_text(r.get("Balance") or "")
        debit_txt = r.get("Debit") or ""
        credit_txt = r.get("Credit") or ""

        def last_amount(text):
            if not text:
                return None
            m = AMOUNT_RE.findall(str(text))
            return m[-1] if m else None

        debit_val = amount_to_float(last_amount(debit_txt))
        credit_val = amount_to_float(last_amount(credit_txt))
        balance_val = amount_to_float(last_amount(bal_txt))

        cleaned_rows.append({
            "Date": d,
            "Transaction": (r.get("Transaction") or "").strip(),
            "Debit": debit_val,
            "Credit": credit_val,
            "Balance": balance_val
        })

    def looks_like_noise(txn: str) -> bool:
        t = txn.lower()
        return any(key in t for key in [
            "opening balance", "closing balance", "total", "page", "statement", "interest charged"
        ]) and not AMOUNT_RE.search(txn)

    final_rows = [
        r for r in cleaned_rows
        if any([r["Date"], r["Transaction"], r["Debit"], r["Credit"]])
        and not looks_like_noise(r["Transaction"])
    ]

    df = pd.DataFrame(final_rows, columns=["Date", "Transaction", "Debit", "Credit", "Balance"])
    df["Date"] = df["Date"].ffill()
    df = df[(df["Date"].notna()) & (df[["Debit", "Credit", "Balance"]].notna().any(axis=1))]

    print(f"✅ Generic extractor processed {len(df)} transactions.")
    print(df.head(15))

    return df
