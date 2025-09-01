import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timezone
from dateutil import parser

# =============================
# Mock Data (Replace with real API pull)
# =============================
btc_data = {
    "name": ["MicroStrategy", "MARA Holdings", "XXI", "Bitcoin Treasury", "Bullish"],
    "symbol": ["MSTR.US", "MARA.US", "CEP.US", "CEPO.US", "BLSH.US"],
    "country": ["US", "US", "US", "US", "US"],
    "total_holdings": [632457, 50639, 43514, 30021, 24000],
    "total_entry_value_usd": [46502665839, 0, 0, 0, 0],
    "total_current_value_usd": [68570008266.73, 5490201940.39, 4717720476.99, 3254830317.60, 2602042824.10],
}

eth_data = {
    "name": ["Company A", "Company B", "Company C"],
    "symbol": ["CMPA", "CMPB", "CMPC"],
    "country": ["US", "UK", "SG"],
    "total_holdings": [150000, 82000, 65000],
    "total_entry_value_usd": [200000000, 110000000, 80000000],
    "total_current_value_usd": [350000000, 200000000, 150000000],
}

df_btc = pd.DataFrame(btc_data)
df_eth = pd.DataFrame(eth_data)

# Ensure numeric columns
for df in [df_btc, df_eth]:
    df["total_holdings"] = pd.to_numeric(df["total_holdings"], errors="coerce").fillna(0)
    df["total_entry_value_usd"] = pd.to_numeric(df["total_entry_value_usd"], errors="coerce").fillna(0)
    df["total_current_value_usd"] = pd.to_numeric(df["total_current_value_usd"], errors="coerce").fillna(0)

# =============================
# Streamlit Page Config
# =============================
st.set_page_config(page_title="Crypto Treasury Dashboard", layout="wide")

# =============================
# Heading
# =============================
st.markdown(
    "<h2 style='text-align: center; margin-bottom: 10px;'>📊 Public Companies Crypto Treasury Tracker</h2>",
    unsafe_allow_html=True
)

# =============================
# Snapshot Timestamp (Friendly)
# =============================
snapshot_raw = "2025-08-31T12:33:03.015764Z"
snapshot_dt = parser.isoparse(snapshot_raw)
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
    snapshot_display = snapshot_dt.strftime("%d %b %Y")

st.markdown(
    f"<p style='text-align: center; font-size:16px;'>Latest snapshot: <b>{snapshot_display}</b></p>",
    unsafe_allow_html=True
)

st.markdown("---")

# =============================
# Tabs for BTC & ETH
# =============================
tab1, tab2 = st.tabs(["₿ Bitcoin", "Ξ Ethereum"])

# =============================
# Helper Function for Dashboard
# =============================
def render_dashboard(df, asset_name, total_supply):
    # KPIs
    total_holdings = df["total_holdings"].sum()
    total_value = df["total_current_value_usd"].sum()
    avg_holding = df["total_holdings"].mean()
    num_companies = df.shape[0]

    # KPI Cards with border
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div style="border:2px solid #4CAF50; border-radius:10px; padding:15px; text-align:center;">
            <h4 style="margin:0;">Total {asset_name} Held</h4>
            <p style="font-size:20px; font-weight:bold;">{total_holdings:,.0f}</p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div style="border:2px solid #2196F3; border-radius:10px; padding:15px; text-align:center;">
            <h4 style="margin:0;">Total Value (USD)</h4>
            <p style="font-size:20px; font-weight:bold;">${total_value:,.0f}</p>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div style="border:2px solid #FF9800; border-radius:10px; padding:15px; text-align:center;">
            <h4 style="margin:0;">Avg {asset_name} / Company</h4>
            <p style="font-size:20px; font-weight:bold;">{avg_holding:,.0f}</p>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div style="border:2px solid #9C27B0; border-radius:10px; padding:15px; text-align:center;">
            <h4 style="margin:0;">Companies Tracked</h4>
            <p style="font-size:20px; font-weight:bold;">{num_companies}</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Pie Chart: Companies vs Others
    company_holdings = total_holdings
    other_holdings = total_supply - company_holdings
    pie_data = pd.DataFrame({
        "holder": ["Public Companies", "Others"],
        "holdings": [company_holdings, other_holdings]
    })
    fig_pie = px.pie(
        pie_data,
        names="holder",
        values="holdings",
        title=f"Share of {asset_name} Supply (Companies vs Others)",
        hole=0.4,
        color_discrete_sequence=px.colors.sequential.RdBu
    )

    # Bar Chart: Top Companies
    df_sorted = df.sort_values("total_holdings", ascending=False)
    fig_bar = px.bar(
        df_sorted,
        x="name",
        y="total_holdings",
        title=f"Top Public Companies Holding {asset_name}",
        text="total_holdings",
        color="total_holdings",
        color_continuous_scale="Blues"
    )
    fig_bar.update_traces(texttemplate="%{text:,.0f}", textposition="outside")

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(fig_pie, use_container_width=True)
    with col2:
        st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("---")

    # Data Table
    st.subheader(f"{asset_name} Company Breakdown")
    st.dataframe(df, use_container_width=True)

# =============================
# Render Both Dashboards
# =============================
with tab1:
    render_dashboard(df_btc, "BTC", 21000000)

with tab2:
    render_dashboard(df_eth, "ETH", 120000000)  # supply ≈ 120m
