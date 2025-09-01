import os
from datetime import datetime
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
import joblib
from pathlib import Path
import plotly.express as px

# Load environment variables
load_dotenv()

DATA_DIR = Path("data")
SNAP_PATH = DATA_DIR / "treasury_snapshots.pkl"

# Streamlit config
st.set_page_config(page_title="Treasury Tracker", layout="wide")
st.title("📊 Public Companies Crypto Treasury Tracker (Demo)")

# Sidebar
coin = st.sidebar.selectbox("Coin", ["bitcoin", "ethereum"])
fiat = st.sidebar.selectbox("Display currency", ["usd", "eur", "jpy", "gbp", "ngn"])
assumed_cost = st.sidebar.number_input(
    "Assumed cost per coin (USD)", min_value=0.0, value=0.0
)
fetch_now = st.sidebar.button("Fetch latest now")

# --- Helper functions ---
def load_snapshots():
    if SNAP_PATH.exists():
        return joblib.load(SNAP_PATH)
    return []

def save_snapshot(df, coin):
    DATA_DIR.mkdir(exist_ok=True)
    rec = {"timestamp": datetime.utcnow().isoformat() + "Z", "coin": coin, "data": df}
    snaps = load_snapshots()
    snaps.append(rec)
    joblib.dump(snaps, SNAP_PATH)

# --- Fetch new snapshot if requested ---
if fetch_now:
    st.info("Fetch requested — make sure COINGECKO_API_KEY is set in .env")
    try:
        from src.api import CoinGeckoClient
        from src.transform import normalize_companies_payload, add_values_fx, compute_pnl

        cg = CoinGeckoClient()
        payload = cg.get_companies_treasury(coin)
        price_resp = cg.get_simple_price([coin], ["usd"])
        price_usd = price_resp.get(coin, {}).get("usd", 0.0)

        df = normalize_companies_payload(payload)
        df = add_values_fx(df, coin_price_usd=price_usd, fiat_rates={"usd": 1.0}, fiat="usd")
        df = compute_pnl(df, assumed_cost_per_coin_usd=(assumed_cost if assumed_cost > 0 else None))

        save_snapshot(df, coin)
        st.success("Fetched and saved snapshot ✅")
    except Exception as e:
        st.error(f"Failed to fetch: {e}")

# --- Load latest snapshot ---
snaps = load_snapshots()
if not snaps:
    st.info("No snapshots yet. Use Fetch Latest Now to create one.")
else:
    latests = [s for s in snaps if s["coin"] == coin]
    if not latests:
        st.info("No snapshots for selected coin yet.")
    else:
        latest = latests[-1]
        df = latest["data"]

        st.subheader(f"Latest snapshot for {coin} @ {latest['timestamp']}")

        # --- KPI Cards ---
        total_coins = df["coins"].sum()
        total_value = df["value_usd"].sum()
        pct_supply = df.get("pct_supply", pd.Series([0])).sum()
        total_pnl = df.get("pnl_usd", pd.Series([0])).sum()

        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Total Coins Held", f"{total_coins:,.0f}")
        kpi2.metric("Total Value (USD)", f"${total_value:,.0f}")
        kpi3.metric("% of Supply", f"{pct_supply:.2f}%")
        kpi4.metric("Total PnL (USD)", f"${total_pnl:,.0f}")

        # --- Dataframe display ---
        st.dataframe(df, use_container_width=True)

        # --- Pie Chart: Companies vs Rest ---
        if "pct_supply" in df.columns and df["pct_supply"].sum() > 0:
            st.markdown("### 🥧 Companies vs Rest of Supply")
            companies_pct = df["pct_supply"].sum()
            rest_pct = max(0, 100 - companies_pct)
            pie_df = pd.DataFrame({
                "Category": ["Companies", "Rest of Supply"],
                "Share": [companies_pct, rest_pct]
            })
            fig1 = px.pie(pie_df, names="Category", values="Share", color="Category",
                          color_discrete_map={"Companies": "blue", "Rest of Supply": "gray"})
            st.plotly_chart(fig1, use_container_width=True)

        # --- Line Chart: Historical Accumulation (Yearly) ---
        st.markdown("### 📈 Yearly Accumulation")
        history = pd.DataFrame()
        for snap in latests:
            snap_df = snap["data"].copy()
            snap_df["timestamp"] = snap["timestamp"]
            history = pd.concat([history, snap_df])

        if not history.empty:
            history["timestamp"] = pd.to_datetime(history["timestamp"])
            yearly = history.groupby([pd.Grouper(key="timestamp", freq="Y"), "name"])["coins"].sum().reset_index()
            fig2 = px.line(yearly, x="timestamp", y="coins", color="name", title="Yearly Accumulation")
            st.plotly_chart(fig2, use_container_width=True)

# --- Custom CSS ---
st.markdown(
    """
    <style>
    .stMetric {background: #f8f9fa; padding: 15px; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);}
    </style>
    """,
    unsafe_allow_html=True,
)
