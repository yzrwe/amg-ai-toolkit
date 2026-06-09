"""Generate a synthetic multi-asset pension portfolio dataset.

Models a defined-benefit plan structured like a large corporate pension:
public equities, fixed income, hedge funds, and private markets, managed by
external managers and reported through a custodian. Returns are seeded and
reproducible. A handful of custodian-vs-manager breaks are injected
deliberately so the reconciliation module has something real to catch.

Usage:
    python data/generate_dataset.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

RNG = np.random.default_rng(42)
OUT = Path(__file__).parent
MONTHS = pd.period_range("2024-07", "2026-06", freq="M").astype(str).tolist()

# manager, asset_class, sub_class, target_weight_pct, annual_mu, annual_vol, reporting_lag_m
MANAGERS = [
    ("Northbrook Capital",      "Public Equity",  "US Large Cap",        14.0, 0.08, 0.16, 0),
    ("Halverson Global",        "Public Equity",  "International Dev",    8.0, 0.07, 0.17, 0),
    ("Meridian EM Partners",    "Public Equity",  "Emerging Markets",     4.0, 0.08, 0.22, 0),
    ("Ironclad Index Co",       "Public Equity",  "US Small Cap",         4.0, 0.08, 0.20, 0),
    ("Bluestem Fixed Income",   "Fixed Income",   "Long Duration Govt",  16.0, 0.045, 0.09, 0),
    ("Carraway Credit",         "Fixed Income",   "IG Credit",           12.0, 0.05, 0.07, 0),
    ("Tallgrass High Yield",    "Fixed Income",   "High Yield",           4.0, 0.06, 0.09, 0),
    ("Foxglove Macro Fund",     "Hedge Funds",    "Global Macro",         4.0, 0.06, 0.08, 1),
    ("Quarry Relative Value",   "Hedge Funds",    "Relative Value",       4.0, 0.055, 0.05, 1),
    ("Stonebridge Equity LS",   "Hedge Funds",    "Equity Long/Short",    3.0, 0.06, 0.09, 1),
    ("Alder Grove Partners VII","Private Markets","Private Equity",      10.0, 0.11, 0.12, 3),
    ("Kestrel Ventures III",    "Private Markets","Venture Capital",      3.0, 0.12, 0.20, 3),
    ("Millbrook Private Credit","Private Markets","Private Credit",       8.0, 0.085, 0.06, 3),
    ("Granite Real Assets",     "Private Markets","Real Assets",          6.0, 0.07, 0.08, 3),
]

PLAN_AUM_M = 12_000.0  # $12B North America DB plan (illustrative)


def main() -> None:
    rows, nav = [], {}
    for mgr, ac, sub, w, mu, vol, lag in MANAGERS:
        nav[mgr] = PLAN_AUM_M * w / 100
        m_mu, m_vol = mu / 12, vol / np.sqrt(12)
        for month in MONTHS:
            r = RNG.normal(m_mu, m_vol)
            mgr_r = r + RNG.normal(0, 0.0002)  # tiny methodology noise
            nav[mgr] *= 1 + r
            rows.append({
                "month": month, "manager": mgr, "asset_class": ac,
                "sub_class": sub, "target_weight_pct": w,
                "custodian_return_pct": round(r * 100, 4),
                "manager_return_pct": round(mgr_r * 100, 4),
                "nav_usd_m": round(nav[mgr], 2),
                "reporting_lag_months": lag,
            })

    df = pd.DataFrame(rows)

    # ---- Inject known issues for QA / recon to catch ----------------------
    ix = df[(df.manager == "Tallgrass High Yield") & (df.month == "2026-03")].index
    df.loc[ix, "manager_return_pct"] = df.loc[ix, "custodian_return_pct"] + 0.85  # recon break
    ix = df[(df.manager == "Foxglove Macro Fund") & (df.month == "2026-02")].index
    df.loc[ix, "custodian_return_pct"] = np.nan                                   # missing data
    ix = df[(df.manager == "Kestrel Ventures III") & (df.month == "2026-01")].index
    df.loc[ix, "nav_usd_m"] = -df.loc[ix, "nav_usd_m"]                            # impossible NAV
    dup = df[(df.manager == "Carraway Credit") & (df.month == "2025-11")]
    df = pd.concat([df, dup], ignore_index=True)                                  # duplicate row

    df.to_csv(OUT / "portfolio_monthly.csv", index=False)
    print(f"✓ wrote {len(df)} rows -> portfolio_monthly.csv "
          f"({len(MANAGERS)} managers x {len(MONTHS)} months + injected issues)")


if __name__ == "__main__":
    main()
