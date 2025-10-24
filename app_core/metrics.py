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

def timeseries(df: pd.DataFrame, freq: str = "D") -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["date","inflow","outflow","net"])

    d = df.copy()
    d["date"] = pd.to_datetime(d["date"])
    d.set_index("date", inplace=True)

    inflow  = d.loc[d["signed_amount"] > 0, "signed_amount"].resample(freq).sum()
    outflow = -d.loc[d["signed_amount"] < 0, "signed_amount"].resample(freq).sum()
    net     = d["signed_amount"].resample(freq).sum()

    # Coerce to float and fill gaps
    inflow = pd.to_numeric(inflow, errors="coerce").fillna(0.0).astype(float)
    outflow = pd.to_numeric(outflow, errors="coerce").fillna(0.0).astype(float)
    net = pd.to_numeric(net, errors="coerce").fillna(0.0).astype(float)

    out = pd.DataFrame({"inflow": inflow, "outflow": outflow, "net": net}).reset_index()
    out = out.sort_values("date")  # ensure order
    out["date"] = out["date"].dt.date
    return out


def by_category(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["category","amount"])
    cat = df.groupby(df["category"].fillna("Uncategorised"))["signed_amount"].sum()
    cat = pd.to_numeric(cat, errors="coerce").fillna(0.0).abs().astype(float)
    return cat.sort_values(ascending=False).reset_index().rename(columns={"signed_amount":"amount"})
