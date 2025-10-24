# app_core/insights.py
from __future__ import annotations
from dataclasses import dataclass
import math
import pandas as pd

@dataclass
class Insight:
    title: str
    text: str
    severity: str = "info"  # info|good|warn|bad

def _fmt_money(x: float) -> str:
    try:
        v = float(x)
        if math.isnan(v):
            v = 0.0
    except Exception:
        v = 0.0
    return f"£{v:,.2f}"

def generate_insights(df: pd.DataFrame, ts: pd.DataFrame, cats: pd.DataFrame) -> list[Insight]:
    """
    df: transactions with 'date','signed_amount','category'
    ts: timeseries with 'date','inflow','outflow','net'
    cats: by_category with 'category','amount' (abs values)
    """
    insights: list[Insight] = []

    if df.empty:
        return [Insight("No data yet", "Upload a CSV/XLSX to see insights.", "info")]

    period_start = df["date"].min()
    period_end   = df["date"].max()

    inflow = float(df.loc[df["signed_amount"] > 0, "signed_amount"].sum() or 0.0)
    outflow = float(-df.loc[df["signed_amount"] < 0, "signed_amount"].sum() or 0.0)
    net = inflow - outflow

    insights.append(
        Insight(
            "Period summary",
            f"{period_start} to {period_end}: Inflow {_fmt_money(inflow)}, "
            f"Outflow {_fmt_money(outflow)}, Net {_fmt_money(net)}.",
            "info" if net >= 0 else "warn",
        )
    )

    # Top expense categories
    if not cats.empty:
        top = cats.sort_values("amount", ascending=False).head(2)
        parts = [f"{row['category']} {_fmt_money(float(row['amount']))}" for _, row in top.iterrows()]
        insights.append(
            Insight(
                "Top spending categories",
                " • " + " • ".join(parts),
                "warn" if float(top.iloc[0]['amount']) > 0 else "info",
            )
        )

    # Best revenue day & highest spend day
    if not ts.empty:
        best_rev = ts.loc[ts["inflow"].idxmax()] if ts["inflow"].sum() != 0 else None
        worst_spend = ts.loc[ts["outflow"].idxmax()] if ts["outflow"].sum() != 0 else None

        if best_rev is not None:
            insights.append(
                Insight("Best revenue day",
                        f"{best_rev['date']}: {_fmt_money(float(best_rev['inflow']))}.",
                        "good")
            )
        if worst_spend is not None:
            insights.append(
                Insight("Highest spend day",
                        f"{worst_spend['date']}: {_fmt_money(float(worst_spend['outflow']))}.",
                        "warn")
            )

        # Notable spike: net deviates > 2 std from mean
        if ts["net"].count() >= 3:
            mean = float(ts["net"].mean())
            std = float(ts["net"].std() or 0.0)
            if std > 0:
                spikes = ts[(ts["net"] - mean).abs() > 2 * std].copy()
                if not spikes.empty:
                    d = spikes.iloc[0]
                    direction = "increase" if float(d["net"]) > mean else "drop"
                    insights.append(
                        Insight("Notable variance",
                                f"{d['date']}: Net {_fmt_money(float(d['net']))} "
                                f"({direction} vs typical {_fmt_money(mean)}).",
                                "warn")
                    )

    return insights
