# app_core/ingest.py
from __future__ import annotations
import io
from typing import Tuple, Dict, List, Iterable
import pandas as pd
from decimal import Decimal
from .models import Transaction
import base64

REQUIRED_COLS = {"date", "description", "amount"}
OPTIONAL_COLS = {"direction", "category", "subcategory", "account", "source"}

def _read_any(file_obj, filename: str) -> pd.DataFrame:
    """Read CSV or XLSX into a DataFrame, normalising headers to lower-case."""
    name = filename.lower()
    data = file_obj.read()
    file_obj.seek(0)  # reset pointer for any future reads
    if name.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(data))
    elif name.endswith(".xlsx"):
        df = pd.read_excel(io.BytesIO(data), engine="openpyxl")
    else:
        raise ValueError("Unsupported file type (expected .csv or .xlsx)")
    # normalise headers
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df

def _coerce_types(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """Best-effort coercion of common types; returns df + warnings."""
    warnings: List[str] = []

    # date
    if "date" in df.columns:
        try:
            df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
            if df["date"].isna().any():
                warnings.append("Some rows have invalid dates and were set to NaT.")
        except Exception:
            warnings.append("Could not parse 'date' column.")

    # amount
    if "amount" in df.columns:
        # remove currency symbols/commas if present
        df["amount"] = (
            df["amount"]
            .astype(str)
            .str.replace(",", "", regex=False)
            .str.replace("£", "", regex=False)
            .str.strip()
        )
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
        if df["amount"].isna().any():
            warnings.append("Some rows have invalid amounts and were set to NaN.")

    # direction (infer if missing)
    if "direction" not in df.columns and "amount" in df.columns:
        df["direction"] = df["amount"].apply(lambda x: "inflow" if pd.notna(x) and x >= 0 else "outflow")

    return df, warnings

def validate_and_preview(file_obj, filename: str) -> Dict:
    """
    Reads the file, validates schema, coerces types,
    and returns a dict suitable for rendering in the template.
    """
    # read into df
    df = _read_any(file_obj, filename)

    # missing required columns -> fail fast but return example header
    missing = sorted(list(REQUIRED_COLS - set(df.columns)))
    extras = [c for c in df.columns if c not in REQUIRED_COLS | OPTIONAL_COLS]

    if missing:
        return {
            "ok": False,
            "errors": [f"Missing required columns: {', '.join(missing)}"],
            "warnings": [],
            "preview_html": "",
            "row_count": 0,
            "cols": list(df.columns),
            "example_header": ", ".join(list(df.columns)),
        }

    # coerce types and collect column-level warnings
    df, warnings = _coerce_types(df)

    # detect per-row problems: we'll mark rows as rejected if required values are missing after coercion
    rejection_reasons = {}
    reject_mask = pd.Series([False] * len(df))

    # reason: missing date
    if "date" in df.columns:
        missing_date = df["date"].isna()
        if missing_date.any():
            rej = missing_date
            reject_mask = reject_mask | rej
            rejection_reasons.setdefault("missing_date", 0)
            rejection_reasons["missing_date"] += int(rej.sum())

    # reason: missing/invalid amount
    if "amount" in df.columns:
        missing_amount = df["amount"].isna()
        if missing_amount.any():
            rej = missing_amount
            reject_mask = reject_mask | rej
            rejection_reasons.setdefault("invalid_amount", 0)
            rejection_reasons["invalid_amount"] += int(rej.sum())

    # reason: missing description (empty/na)
    if "description" in df.columns:
        missing_desc = df["description"].isna() | (df["description"].astype(str).str.strip() == "")
        if missing_desc.any():
            rej = missing_desc
            reject_mask = reject_mask | rej
            rejection_reasons.setdefault("missing_description", 0)
            rejection_reasons["missing_description"] += int(rej.sum())

    # build rejected rows CSV if any
    rejected_csv_b64 = None
    rejected_count = int(reject_mask.sum())
    if rejected_count > 0:
        rejected_df = df[reject_mask].copy()
        # include original columns in CSV (stringify dates to ISO)
        if "date" in rejected_df.columns:
            rejected_df["date"] = rejected_df["date"].apply(lambda d: d.isoformat() if pd.notna(d) else "")
        csv_str = rejected_df.to_csv(index=False)
        rejected_csv_b64 = base64.b64encode(csv_str.encode("utf-8")).decode("ascii")

    # small preview (first 20 rows, only relevant cols)
    display_cols = [c for c in ["date", "description", "amount", "direction", "category"] if c in df.columns]
    preview = df[display_cols].head(20).copy()

    # build HTML table (simple & safe for MVP)
    preview_html = preview.to_html(index=False, border=0, classes="preview-table")

    if extras:
        warnings.append(f"Ignored unrecognised columns: {', '.join(extras[:10])}"
                        + (" ..." if len(extras) > 10 else ""))

    # Build a compact rejection summary for the UI (reason -> count)
    rejection_summary = [{"reason": k.replace("_", " "), "count": v} for k, v in rejection_reasons.items()]

    return {
        "ok": True,
        "errors": [],
        "warnings": warnings,
        "preview_html": preview_html,
        "row_count": len(df),
        "cols": list(df.columns),
        "rejected_count": rejected_count,
        "rejection_summary": rejection_summary,
        "rejected_csv_b64": rejected_csv_b64,  # base64 content, data URI produced in template
    }

def dataframe_to_transactions(df, user) -> list[Transaction]:
    """
    Map a validated/cleaned DataFrame into Transaction model instances (unsaved).
    Assumes columns: date, description, amount, direction, category?, subcategory?, account?, source?
    """
    # Ensure required columns exist (caller should have validated already)
    rows = []
    for _, r in df.iterrows():
        # Skip completely invalid rows (NaN amount or date)
        if pd.isna(r.get("amount")) or pd.isna(r.get("date")):
            continue

        amount = Decimal(str(r.get("amount")))
        direction = r.get("direction") or ("inflow" if amount >= 0 else "outflow")
        rows.append(
            Transaction(
                user=user,
                date=r.get("date"),
                description=str(r.get("description") or "")[:512],
                amount=amount.copy_abs(),  # store absolute; use direction for sign
                direction=direction,
                category=(r.get("category") or ""),
                subcategory=(r.get("subcategory") or ""),
                account=(r.get("account") or ""),
                source=(r.get("source") or "csv"),
            )
        )
    return rows
