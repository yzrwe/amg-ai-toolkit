"""Data QA controls for the monthly portfolio dataset.

Runs the checks an asset management operations team applies before any
number reaches a report: completeness, duplicates, impossible values,
stale/missing data, and weight integrity. Exits non-zero if any control
fails, so it can gate a pipeline.

Usage:
    python qa/data_quality_checks.py [path/to/portfolio_monthly.csv]
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

DATA = Path(__file__).parents[1] / "data" / "portfolio_monthly.csv"


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str


def run_checks(df: pd.DataFrame) -> list[CheckResult]:
    results: list[CheckResult] = []

    # 1. Duplicates: one row per manager-month
    dupes = df[df.duplicated(subset=["manager", "month"], keep=False)]
    results.append(CheckResult(
        "No duplicate manager-month rows", dupes.empty,
        "" if dupes.empty else
        f"{len(dupes)} duplicate rows: "
        f"{dupes[['manager', 'month']].drop_duplicates().to_dict('records')}"))

    # 2. Completeness: every manager has every month
    expected = df["month"].nunique()
    counts = df.drop_duplicates(["manager", "month"]).groupby("manager").size()
    short = counts[counts != expected]
    results.append(CheckResult(
        "Every manager reported every month", short.empty,
        "" if short.empty else f"Gaps: {short.to_dict()}"))

    # 3. Missing returns
    miss = df[df["custodian_return_pct"].isna() | df["manager_return_pct"].isna()]
    results.append(CheckResult(
        "No missing returns", miss.empty,
        "" if miss.empty else
        f"{len(miss)} rows missing returns: "
        f"{miss[['manager', 'month']].to_dict('records')}"))

    # 4. Impossible values: negative NAV, return outside ±40%/month
    bad_nav = df[df["nav_usd_m"] <= 0]
    wild = df[df["custodian_return_pct"].abs() > 40]
    ok = bad_nav.empty and wild.empty
    results.append(CheckResult(
        "NAVs positive and returns within sanity bounds", ok,
        "" if ok else
        f"Bad NAV rows: {bad_nav[['manager', 'month', 'nav_usd_m']].to_dict('records')}; "
        f"wild returns: {len(wild)}"))

    # 5. Target weights sum to 100
    weights = (df.drop_duplicates("manager")["target_weight_pct"].sum())
    results.append(CheckResult(
        "Target weights sum to 100%", abs(weights - 100) < 0.01,
        f"Sum = {weights:.2f}%"))

    # 6. Private markets reporting lag flagged, not treated as missing
    lagged = df[(df["reporting_lag_months"] > 0)]
    results.append(CheckResult(
        "Reporting-lag metadata present for alternatives",
        not lagged.empty and lagged["reporting_lag_months"].max() <= 6,
        f"{lagged['manager'].nunique()} managers report on lag (max "
        f"{lagged['reporting_lag_months'].max()}m)"))

    return results


def main(path: Path = DATA) -> int:
    df = pd.read_csv(path)
    results = run_checks(df)
    failures = [r for r in results if not r.passed]

    print(f"Data QA — {path.name}: {len(df)} rows, "
          f"{df['manager'].nunique()} managers, {df['month'].nunique()} months\n")
    for r in results:
        flag = "PASS" if r.passed else "FAIL"
        print(f"  [{flag}] {r.name}" + (f" — {r.detail}" if r.detail else ""))

    print(f"\n{'✓ All controls passed' if not failures else f'✗ {len(failures)} control(s) failed'}")
    return 1 if failures else 0


if __name__ == "__main__":
    arg = Path(sys.argv[1]) if len(sys.argv) > 1 else DATA
    raise SystemExit(main(arg))
