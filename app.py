import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timezone
from dateutil import parser, relativedelta

# =============================
# Load data (replace with your real source)
# =============================
# Example DataFrame
data = {
    "name": ["Strategy", "MARA Holdings", "XXI", "Bitcoin Standard Treasury Company", "Bullish"],
    "symbol": ["MSTR.US", "MARA.US", "CEP.US", "CEPO.US", "BLSH.US"],
    "country": ["US", "US", "US", "US", "US"],
    "total_holdings": [632457, 50639, 43514, 30021, 24000],
    "total_entry_value_usd": [46502665839, 0, 0, 0, 0],
    "total_current_value_usd": [68570008266.73, 5490201940.39, 4717720476.99, 3254830317.60, 2602042824.10],
}
df = pd.DataFrame(data)

# Ensure numeric columns
df["total_holdings"] = pd.to_numeric(df["total_holdings"], errors="coerce").fillna(0)
df["total_entry_value_usd"] = pd.to_numeric(df["total_entry_value_usd"], errors="coerce").fillna(0)
df["total_current_value_usd"] = pd.to_numeric(df["total_current_value_usd"], errors="coerce").fillna(0)

# =============================
# Streamlit Page Config
# =============================
st.set_page_config(page_title="Crypto Treasury Tracker", layout="wide")

# =============================
# Heading
# =============================
st.markdown(
    "<h2 style='text-align: center;'>📊 Public Companies Crypto Treasury Tracker (Demo)</h2>",
    unsafe_allow_html=True
)

# =============================
# Snapshot Timestamp (friendly)
# =============================
# Replace with your API snapshot timestamp
snapshot_raw = "2025-08-31T12:33:03.015764Z"
snapshot_dt = parser.isoparse(snapshot_raw)

# Convert to relative / friendly date
now = datetime.now(timezone.utc)
delta = now - snapshot_dt

if delta.days == 0:
    if delta.seconds < 3600:
        snapshot_display = f"{delta.seconds // 60} minutes ago"
    else:
        snapshot_display = f"{delta.seconds // 3600} hours ago"
elif delta.days == 1:
    snapshot_display = "yesterday"
elif delta.days < 7:
    snapshot_display = f"{delta.days} days ago"
else:
    snapshot_display = snapshot_dt.strftime("%d %b %Y")  # e.g. 31 Aug 2025

st.markdown(
    f"<p style='text-align: center; font-size:16px;'>Latest snapshot for <b>bitcoin</b>: {snapshot_display}</p>",
    unsafe_allow_html=True
)

# =============================
# KPIs
# =============================
total_holdings = df["total_holdings"].sum()
total_value = df["total_current_value_usd"].sum()
avg_holding = df["total_holdings"].mean()
num_companies = df.shape[0]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total BTC Held", f"{total_holdings:,.0f}")
col2.metric("Total Value (USD)", f"${total_value:,.0f}")
col3.metric("Avg BTC per Company", f"{avg_holding:,.0f}")
col4.metric("Companies Tracked", f"{num_companies}")

st.markdown("---")

# =============================
# Pie Chart
# =============================
btc_total_supply = 21000000
company_holdings = total_holdings
other_holdings = btc_total_supply - company_holdings

pie_data = pd.DataFrame({
    "holder": ["Public Companies", "Others"],
    "holdings": [company_holdings, other_holdings]
})

fig_pie = px.pie(
    pie_data,
    names="holder",
    values="holdings",
    title="Share of Bitcoin Supply (Public Companies vs Others)",
    hole=0.4,
    color_discrete_sequence=px.colors.sequential.RdBu
)
st.plotly_chart(fig_pie, use_container_width=True)

# =============================
# Data Table
# =============================
st.subheader("Company Breakdown")
st.dataframe(df, use_container_width=True)
