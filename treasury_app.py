import streamlit as st
import pandas as pd
import joblib
from pathlib import Path
import plotly.express as px
from datetime import datetime, timezone
from dateutil import parser

# =============================
# Load Snapshots
# =============================
DATA_DIR = Path("data")
SNAP_PATH = DATA_DIR / "treasury_snapshots.pkl"

def load_snapshots():
    if SNAP_PATH.exists():
        return joblib.load(SNAP_PATH)
    return []

def latest_snapshot(coin):
    snaps = load_snapshots()
    snaps_coin = [s for s in snaps if s.get("coin") == coin]
    if not snaps_coin:
        return None
    return snaps_coin[-1]

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
latest_any = latest_snapshot("bitcoin") or latest_snapshot("ethereum")
if latest_any:
    snapshot_raw = latest_any["timestamp"]
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
    if df is None or df.empty:
        st.warning(f"No data available for {asset_name}")
        return

    # Normalize column names (so it works with your joblib snapshots)
    if "total_holdings" not in df.columns and "coins" in df.columns:
        df = df.rename(columns={"coins": "total_holdings"})
    if "value_usd" in df.columns and "total_current_value_usd" not in df.columns:
        df = df.rename(columns={"value_usd": "total_current_value_usd"})

    # KPIs
    total_holdings = df["total_holdings"].sum()
    total_value = df["total_current_value_usd"].sum()
    avg_holding = df["total_holdings"].mean()
    num_companies = df.shape[0]

    # KPI Cards
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
    other_holdings = max(total_supply - company_holdings, 0)
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
    snap_btc = latest_snapshot("bitcoin")
    if snap_btc:
        render_dashboard(snap_btc["data"], "BTC", 21_000_000)

with tab2:
    snap_eth = latest_snapshot("ethereum")
    if snap_eth:
        render_dashboard(snap_eth["data"], "ETH", 120_000_000)
