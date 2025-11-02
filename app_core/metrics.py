# app_core/metrics.py
from __future__ import annotations
import pandas as pd
import numpy as np
from django.db.models import QuerySet
from .models import Transaction

def queryset_to_df(qs: QuerySet[Transaction]) -> pd.DataFrame:
    data = list(qs.values(
        "date", "description", "amount", "direction", "category", "account"
    ))
    if not data:
        return pd.DataFrame(columns=["date","description","amount","direction","category","account","signed_amount"])

    df = pd.DataFrame(data)

    # Ensure proper dtypes
    df["date"] = pd.to_datetime(df["date"]).dt.date
    # Decimal -> float
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0).astype(float)

    # Compute signed amounts as float
    df["signed_amount"] = np.where(df["direction"] == "inflow", df["amount"], -df["amount"]).astype(float)
    return df

def kpis(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"inflow": 0.0, "outflow": 0.0, "net": 0.0, "tx_count": 0}
    inflow = float(df.loc[df["signed_amount"] > 0, "signed_amount"].sum())
    outflow = float(-df.loc[df["signed_amount"] < 0, "signed_amount"].sum())
    net = float(df["signed_amount"].sum())
    return {"inflow": round(inflow,2), "outflow": round(outflow,2), "net": round(net,2), "tx_count": int(len(df))}

def timeseries(df: pd.DataFrame, freq: str = "D", start: object = None, end: object = None) -> pd.DataFrame:
    """
    Produce a time series aggregated by freq ('D','W','M' etc.).
    If start/end are provided (date or parsable string), the returned frame will cover the full inclusive range
    and fill missing periods with zeros so charts span the requested range.
    """
    # Normalize freq code (allow 'D','W','M','Y') to pandas-compatible resample alias
    # Use week frequency that ends on Sunday so weeks are Mon-Sun
    freq_code = (freq or 'D').upper()
    if freq_code == 'W':
        resample_freq = 'W-SUN'
    elif freq_code in {'M', 'Y'}:
        # monthly aggregation for both monthly and yearly charts
        resample_freq = 'M'
    else:
        resample_freq = 'D'

    # If start and end provided, create an index across the range; else return empty frame
    if start is not None:
        try:
            start_ts = pd.to_datetime(start)
        except Exception:
            start_ts = None
    else:
        start_ts = None
    if end is not None:
        try:
            end_ts = pd.to_datetime(end)
        except Exception:
            end_ts = None
    else:
        end_ts = None

    if df.empty:
        # If start and end provided, create an index across the range; else return empty frame
        if start_ts is not None and end_ts is not None:
            try:
                full_idx = pd.date_range(start=start_ts, end=end_ts, freq=resample_freq)
            except Exception:
                # fallback to daily
                full_idx = pd.date_range(start=start_ts, end=end_ts, freq='D')
            out = pd.DataFrame({"inflow": 0.0, "outflow": 0.0, "net": 0.0}, index=full_idx)
            out = out.reset_index().rename(columns={"index": "date"})
            out["date"] = out["date"].dt.date
            return out
        return pd.DataFrame(columns=["date", "inflow", "out"])

    d = df.copy()
    d["date"] = pd.to_datetime(d["date"])  # ensure datetime dtype
    d.set_index("date", inplace=True)

    inflow = d.loc[d["signed_amount"] > 0, "signed_amount"].resample(resample_freq).sum()
    outflow = -d.loc[d["signed_amount"] < 0, "signed_amount"].resample(resample_freq).sum()
    net = d["signed_amount"].resample(resample_freq).sum()

    # Coerce to float and fill gaps
    inflow = pd.to_numeric(inflow, errors="coerce").fillna(0.0).astype(float)
    outflow = pd.to_numeric(outflow, errors="coerce").fillna(0.0).astype(float)
    net = pd.to_numeric(net, errors="coerce").fillna(0.0).astype(float)

    # Determine full index to cover requested start/end (or current series bounds)
    try:
        idx_start = start_ts if start_ts is not None else (inflow.index.min() if not inflow.empty else None)
        idx_end = end_ts if end_ts is not None else (inflow.index.max() if not inflow.empty else None)
        if idx_start is None or idx_end is None:
            full_idx = inflow.index.union(outflow.index).union(net.index).sort_values()
        else:
            try:
                full_idx = pd.date_range(start=idx_start, end=idx_end, freq=resample_freq)
            except Exception:
                full_idx = pd.date_range(start=idx_start, end=idx_end, freq='D')
    except Exception:
        full_idx = inflow.index.union(outflow.index).union(net.index).sort_values()

    # Reindex series to full index so missing periods show zeros
    inflow = inflow.reindex(full_idx, fill_value=0.0)
    outflow = outflow.reindex(full_idx, fill_value=0.0)
    net = net.reindex(full_idx, fill_value=0.0)

    out = pd.DataFrame({"inflow": inflow, "outflow": outflow, "net": net}, index=full_idx)
    out = out.reset_index().rename(columns={"index": "date"})
    out["date"] = out["date"].dt.date
    return out


def by_category(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["category","amount"])
    cat = df.groupby(df["category"].fillna("Uncategorised"))["signed_amount"].sum()
    cat = pd.to_numeric(cat, errors="coerce").fillna(0.0).abs().astype(float)
    return cat.sort_values(ascending=False).reset_index().rename(columns={"signed_amount":"amount"})
