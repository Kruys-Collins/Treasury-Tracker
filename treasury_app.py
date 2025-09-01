import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timezone
import matplotlib.pyplot as plt

# ---------- Fetch Data from Coingecko ----------
def fetch_treasury_data(coin_id: str):
    url = f"https://api.coingecko.com/api/v3/companies/public_treasury/{coin_id}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        companies = data.get("companies", [])
        df = pd.DataFrame(companies)

        # Add snapshot timestamp
        df["snapshot_time"] = datetime.now(timezone.utc)

        return df
    except Exception as e:
        st.error(f"Error fetching {coin_id} data: {e}")
        return pd.DataFrame()

def format_snapshot_time(timestamp):
    now = datetime.now(timezone.utc)
    diff = now - timestamp

    if diff.days == 0:
        hours = diff.seconds // 3600
        if hours == 0:
            return "just now"
        return f"{hours} hours ago"
    elif diff.days == 1:
        return "yesterday"
    elif diff.days < 7:
        return f"{diff.days} days ago"
    else:
        return timestamp.strftime("%Y-%m-%d")

# ---------- Streamlit Page Config ----------
st.set_page_config(page_title="Crypto Treasury Tracker", layout="wide")

st.markdown(
    "<h2 style='text-align: center; color: #333;'>📊 Crypto Treasury Tracker</h2>",
    unsafe_allow_html=True,
)

# Tabs for Bitcoin & Ethereum
tab1, tab2 = st.tabs(["💰 Bitcoin", "💎 Ethereum"])

for selected_coin, tab in zip(["bitcoin", "ethereum"], [tab1, tab2]):
    with tab:
        df = fetch_treasury_data(selected_coin)

        if not df.empty:
            snapshot_time = df["snapshot_time"].iloc[0]
            st.subheader(f"Latest snapshot for {selected_coin.capitalize()} ({format_snapshot_time(snapshot_time)})")

            # Summary metrics
            total_holdings = df["total_holdings"].sum()
            total_value_usd = df["total_entry_value_usd"].sum()
            perc_supply = df["percentage_of_total_supply"].sum()

            col1, col2, col3 = st.columns(3)
            col1.metric("Total Holdings", f"{total_holdings:,.0f}")
            col2.metric("Total Value (USD)", f"${total_value_usd:,.0f}")
            col3.metric("% of Supply", f"{perc_supply:.2f}%")

            st.markdown("---")

            # Company breakdown table
            st.markdown("### Company Breakdown")
            styled_df = df[["name", "total_holdings", "total_entry_value_usd", "percentage_of_total_supply"]].copy()
            styled_df.columns = ["Company", "Holdings", "Entry Value (USD)", "% of Supply"]
            st.dataframe(
                styled_df.style.format({
                    "Holdings": "{:,.0f}",
                    "Entry Value (USD)": "${:,.0f}",
                    "% of Supply": "{:.2f}%"
                })
            )

            # ---------- Charts ----------
            st.markdown("### Visualizations")

            colA, colB = st.columns(2)

            # Pie chart (Companies vs Others)
            with colA:
                companies_total = df["total_holdings"].sum()
                others = 100 - df["percentage_of_total_supply"].sum()
                labels = ["Tracked Companies", "Others"]
                sizes = [companies_total, others]

                fig1, ax1 = plt.subplots()
                ax1.pie(sizes, labels=labels, autopct="%1.1f%%", startangle=90, colors=["#4CAF50", "#FF9800"])
                ax1.axis("equal")
                st.pyplot(fig1)

            # Bar chart (Top holders)
            with colB:
                top_df = df.sort_values("total_holdings", ascending=False).head(10)
                fig2, ax2 = plt.subplots()
                ax2.barh(top_df["name"], top_df["total_holdings"], color="#2196F3")
                ax2.set_xlabel("Holdings")
                ax2.set_title("Top 10 Holders")
                plt.gca().invert_yaxis()
                st.pyplot(fig2)
