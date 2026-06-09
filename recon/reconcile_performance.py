"""Reconcile custodian-reported vs. manager-reported performance.

Classic monthly ops control in an asset management group: the custodian's
official book of record and each manager's self-reported return should match
within tolerance. This module computes the differences, classifies breaks by
severity, and writes an exception report for follow-up.

Tolerance bands (monthly return, in basis points):
    <= 5 bps   MATCH        (methodology noise — ignore)
    <= 25 bps  MINOR        (monitor; likely pricing-source or timing diff)
    >  25 bps  BREAK        (investigate with manager / custodian)

Usage:
    python recon/reconcile_performance.py [--month 2026-03]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

DATA = Path(__file__).parents[1] / "data" / "portfolio_monthly.csv"
OUT = Path(__file__).parent / "exceptions_report.csv"

MATCH_BPS, MINOR_BPS = 5, 25


def classify(diff_bps: float) -> str:
    if pd.isna(diff_bps):
        return "MISSING DATA"
    a = abs(diff_bps)
    if a <= MATCH_BPS:
        return "MATCH"
    if a <= MINOR_BPS:
        return "MINOR"
    return "BREAK"


def reconcile(df: pd.DataFrame, month: str | None = None) -> pd.DataFrame:
    df = df.drop_duplicates(subset=["manager", "month"], keep="first").copy()
    if month:
        df = df[df["month"] == month]
    df["diff_bps"] = (df["manager_return_pct"] - df["custodian_return_pct"]) * 100
    df["status"] = df["diff_bps"].apply(classify)
    df["abs_diff_bps"] = df["diff_bps"].abs()
    cols = ["month", "manager", "asset_class", "custodian_return_pct",
            "manager_return_pct", "diff_bps", "status"]
    return df.sort_values("abs_diff_bps", ascending=False)[cols]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--month", default=None, help="e.g. 2026-03 (default: all)")
    args = parser.parse_args()

    recon = reconcile(pd.read_csv(DATA), args.month)
    exceptions = recon[recon["status"] != "MATCH"]

    scope = args.month or "all months"
    print(f"Performance reconciliation — {scope}")
    print(f"  Rows reconciled: {len(recon)}")
    print(f"  Matches:         {(recon['status'] == 'MATCH').sum()}")
    print(f"  Minor diffs:     {(recon['status'] == 'MINOR').sum()}")
    print(f"  Breaks:          {(recon['status'] == 'BREAK').sum()}")
    print(f"  Missing data:    {(recon['status'] == 'MISSING DATA').sum()}\n")

    if not exceptions.empty:
        print("Exceptions (largest first):")
        print(exceptions.head(10).to_string(index=False))
        exceptions.to_csv(OUT, index=False)
        print(f"\n✓ Exception report written to {OUT.name}")
    else:
        print("✓ No exceptions — clean reconciliation.")


if __name__ == "__main__":
    main()
