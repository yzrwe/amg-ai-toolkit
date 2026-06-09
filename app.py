"""AMG Portfolio Monitor — Streamlit dashboard for a multi-asset pension plan.

Positioning vs. target, performance by asset class, NAV trend, and the
month's reconciliation status — the daily glance an Asset Management Group
operations/investments team wants in one screen.

Run:  streamlit run app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
from recon.reconcile_performance import reconcile  # noqa: E402

st.set_page_config(page_title="AMG Portfolio Monitor", page_icon="🏦", layout="wide")


@st.cache_data(ttl=3600)
def load() -> pd.DataFrame:
    df = pd.read_csv(ROOT / "data" / "portfolio_monthly.csv")
    return df.drop_duplicates(subset=["manager", "month"], keep="first")


df = load()
months = sorted(df["month"].unique())

st.title("🏦 AMG Portfolio Monitor")
st.caption("Synthetic multi-asset pension dataset (14 external managers, "
           "$12B illustrative plan). All data generated — no real funds.")

month = st.sidebar.selectbox("As-of month", months, index=len(months) - 1)
cur = df[df["month"] == month].copy()

# ---- KPI row ---------------------------------------------------------------
total_nav = cur["nav_usd_m"].sum()
cur["actual_weight_pct"] = cur["nav_usd_m"] / total_nav * 100
cur["drift_pct"] = cur["actual_weight_pct"] - cur["target_weight_pct"]
wavg_ret = (cur["custodian_return_pct"] * cur["nav_usd_m"]).sum() / total_nav

recon_month = reconcile(df, month)
breaks = (recon_month["status"] == "BREAK").sum()
missing = (recon_month["status"] == "MISSING DATA").sum()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Plan NAV", f"${total_nav / 1000:,.2f}B")
c2.metric("Month return (wtd)", f"{wavg_ret:+.2f}%")
c3.metric("Max weight drift", f"{cur['drift_pct'].abs().max():.2f} pts")
c4.metric("Recon exceptions", f"{breaks + missing}",
          "clean" if breaks + missing == 0 else "investigate", delta_color="inverse")

# ---- Charts ----------------------------------------------------------------
left, right = st.columns(2)

with left:
    alloc = cur.groupby("asset_class")[["nav_usd_m"]].sum().reset_index()
    alloc["target"] = cur.groupby("asset_class")["target_weight_pct"].sum().values
    alloc["actual"] = alloc["nav_usd_m"] / total_nav * 100
    fig = go.Figure()
    fig.add_bar(x=alloc["asset_class"], y=alloc["target"], name="Target %",
                marker_color="#9FC5E8")
    fig.add_bar(x=alloc["asset_class"], y=alloc["actual"], name="Actual %",
                marker_color="#0B5394")
    fig.update_layout(title=f"Allocation vs target — {month}", barmode="group",
                      height=400, yaxis_title="% of plan")
    st.plotly_chart(fig, width="stretch")

with right:
    nav_trend = df.groupby("month")["nav_usd_m"].sum().reset_index()
    fig2 = px.area(nav_trend, x="month", y="nav_usd_m", title="Total plan NAV ($M)")
    fig2.update_traces(line_color="#0B5394")
    fig2.update_layout(height=400, yaxis_title="$M")
    st.plotly_chart(fig2, width="stretch")

# ---- Drift table -----------------------------------------------------------
st.subheader(f"Manager positioning — {month}")
table = cur[["manager", "asset_class", "sub_class", "nav_usd_m",
             "target_weight_pct", "actual_weight_pct", "drift_pct",
             "custodian_return_pct"]].sort_values("drift_pct", key=abs,
                                                  ascending=False)
st.dataframe(
    table, hide_index=True, width="stretch",
    column_config={
        "manager": "Manager", "asset_class": "Asset class", "sub_class": "Strategy",
        "nav_usd_m": st.column_config.NumberColumn("NAV ($M)", format="%.0f"),
        "target_weight_pct": st.column_config.NumberColumn("Target %", format="%.1f"),
        "actual_weight_pct": st.column_config.NumberColumn("Actual %", format="%.2f"),
        "drift_pct": st.column_config.NumberColumn("Drift (pts)", format="%.2f"),
        "custodian_return_pct": st.column_config.NumberColumn("Mo. return %", format="%.2f"),
    },
)

# ---- Recon status ----------------------------------------------------------
st.subheader(f"Reconciliation status — {month}")
exceptions = recon_month[recon_month["status"] != "MATCH"]
if exceptions.empty:
    st.success("Clean reconciliation — all managers within 5 bps of custodian.")
else:
    st.warning(f"{len(exceptions)} exception(s) require follow-up.")
    st.dataframe(exceptions, hide_index=True, width="stretch")

st.caption("Private markets report on a 1–3 month lag (flagged in source data); "
           "returns shown as received, per standard alternatives reporting practice.")
