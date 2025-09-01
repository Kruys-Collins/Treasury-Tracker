# %% [markdown]
# \
# # Treasury Tracker — BTC & ETH (Step‑by‑Step)
# 
# This notebook is a guided, runnable step‑by‑step implementation for a **Treasury Tracker** that fetches public companies' BTC and ETH holdings (CoinGecko Pro), computes USD values and PnL, supports FX conversion, provides what‑if scenarios, and **persists snapshots using `joblib`**.
# 
# **How to use:**
# 1. Create a Python virtual environment and install the dependencies (instructions below).
# 2. Rename `.env.example` to `.env` and add your `COINGECKO_API_KEY`.
# 3. Run the notebook cells in order.
# 
# This notebook includes a demo mode so you can follow the full flow without an API key.
# 

# %% [markdown]
# \
# ## 0 — Quick checklist
# 
# - Python 3.10+ recommended
# - VSCode or Jupyter environment (JupyterLab recommended)
# - CoinGecko **Pro** API key (put into `.env`)
# - We'll persist snapshots with `joblib` to `data/treasury_snapshots.pkl`
# 
# **Packages used:** `pandas`, `requests`, `python-dotenv`, `joblib`, `altair`, `streamlit` (optional).
# 

# %%
\
# 1) Install dependencies (run this cell if you need to install packages)
!pip install pandas requests python-dotenv joblib altair streamlit jupyterlab
print('If you need packages, uncomment the pip line and run this cell.')


# %% [markdown]
# ## 3 — CoinGecko client (API wrappers)
# 
# Define a small client to access the Public Companies endpoint and simple/price.

# %%
\
import os
import requests
from dotenv import load_dotenv
load_dotenv()
API_KEY = os.getenv('COINGECKO_API_KEY','')
PRO_BASE = 'https://pro-api.coingecko.com/api/v3'

class CoinGeckoClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or API_KEY
        self.headers = {'accept': 'application/json'}
        if self.api_key:
            self.headers['x-cg-pro-api-key'] = self.api_key

    def get_companies_treasury(self, coin_id: str) -> dict:
        url = f"{PRO_BASE}/companies/public_treasury/{coin_id}"
        r = requests.get(url, headers=self.headers, timeout=30)
        r.raise_for_status()
        return r.json()

    def get_simple_price(self, ids, vs) -> dict:
        ids_str = ','.join(ids) if isinstance(ids, (list,tuple)) else ids
        vs_str = ','.join(vs) if isinstance(vs, (list,tuple)) else vs
        url = f"{PRO_BASE}/simple/price?ids={ids_str}&vs_currencies={vs_str}"
        r = requests.get(url, headers=self.headers, timeout=30)
        r.raise_for_status()
        return r.json()

print('CoinGecko client defined. API_KEY present:', bool(API_KEY))


# %% [markdown]
# ## 4 — Data transformation helpers
# 
# Normalization, USD valuation, FX application and PnL computation.

# %%
\
import pandas as pd

def normalize_companies_payload(payload):
    if isinstance(payload, dict):
        for key in ['companies','data','items','treasury']:
            if key in payload and isinstance(payload[key], list):
                return pd.json_normalize(payload[key])
    if isinstance(payload, list):
        return pd.json_normalize(payload)
    return pd.DataFrame([payload])

def add_values_fx(df, coin_price_usd, fiat_rates=None, fiat='usd'):
    out = df.copy()
    candidates = ['total_holdings','holdings','amount','quantity','total_btc_holdings','total_eth_holdings']
    amount_col = None
    for c in candidates:
        if c in out.columns:
            amount_col = c
            break
    if amount_col is None:
        numeric_cols = [c for c in out.columns if pd.api.types.is_numeric_dtype(out[c])]
        amount_col = numeric_cols[0] if numeric_cols else None
    if amount_col is None:
        out['coins'] = 0.0
    else:
        out['coins'] = pd.to_numeric(out[amount_col], errors='coerce').fillna(0.0)
    out['value_usd'] = out['coins'] * float(coin_price_usd)
    if fiat.lower() != 'usd' and fiat_rates and fiat.lower() in fiat_rates:
        rate = float(fiat_rates[fiat.lower()])
        out[f'value_{fiat.lower()}'] = out['value_usd'] * rate
    return out

def compute_pnl(df, assumed_cost_per_coin_usd=None, coins_col='coins'):
    out = df.copy()
    if not assumed_cost_per_coin_usd:
        out['cost_basis_usd'] = None
        out['pnl_usd'] = None
        out['pnl_pct'] = None
        return out
    out['cost_basis_usd'] = out[coins_col].astype(float) * float(assumed_cost_per_coin_usd)
    out['pnl_usd'] = out.get('value_usd',0.0) - out['cost_basis_usd']
    out['pnl_pct'] = (out['pnl_usd'] / out['cost_basis_usd']).replace([float('inf'), -float('inf')], None)
    return out

print('Transform helpers ready')


# %% [markdown]
# ## 5 — Persist snapshots using joblib
# 
# Snapshots are stored at `data/treasury_snapshots.pkl`. Each snapshot is a dict: `{'timestamp', 'coin', 'data'}`.

# %%
\
import joblib, os
from datetime import datetime
from pathlib import Path
DATA_DIR = Path('data')
SNAP_PATH = DATA_DIR / 'treasury_snapshots.pkl'
DATA_DIR.mkdir(exist_ok=True)

def save_snapshot(df, coin):
    rec = {'timestamp': datetime.utcnow().isoformat() + 'Z', 'coin': coin, 'data': df}
    if SNAP_PATH.exists():
        snaps = joblib.load(SNAP_PATH)
    else:
        snaps = []
    snaps.append(rec)
    joblib.dump(snaps, SNAP_PATH)
    print(f"Saved snapshot. Total snapshots: {len(snaps)}")

def load_snapshots():
    if SNAP_PATH.exists():
        return joblib.load(SNAP_PATH)
    return []

def latest_snapshot(coin=None):
    snaps = load_snapshots()
    if not snaps:
        return None
    if coin is None:
        return snaps[-1]
    for rec in reversed(snaps):
        if rec.get('coin') == coin:
            return rec
    return None

print('Joblib helpers ready. Snap file at:', SNAP_PATH)


# %% [markdown]
# ## Fetch Data
# 
# This cell will fetch live data if `COINGECKO_API_KEY` is set. Otherwise it runs in demo mode using synthetic data so you can continue following the flow.

# %%
# User settings
coins_to_fetch = ["bitcoin", "ethereum"]
fiat = "usd"
assumed_cost_per_coin_usd = 0.0

cg = CoinGeckoClient()

import pandas as pd

for coin_id in coins_to_fetch:
    print("Fetching live data for", coin_id)
    raw_payload = cg.get_companies_treasury(coin_id)
    price_resp = cg.get_simple_price([coin_id], ["usd", fiat])
    price_usd = price_resp.get(coin_id, {}).get("usd", 0.0)
    fiat_rates = {"usd": 1.0}
    if fiat != "usd":
        fiat_val = price_resp.get(coin_id, {}).get(fiat)
        if fiat_val:
            fiat_rates[fiat] = fiat_val / price_usd

    df = normalize_companies_payload(raw_payload)
    if df.empty:
        print(f"Normalized payload empty for {coin_id}")
    else:
        df_val = add_values_fx(df, coin_price_usd=price_usd, fiat_rates=fiat_rates, fiat=fiat)
        df_val = compute_pnl(df_val, assumed_cost_per_coin_usd=assumed_cost_per_coin_usd)
        save_snapshot(df_val, coin_id)   # <-- saves BTC and ETH snapshots separately
        print(f"✅ Snapshot saved for {coin_id}")


# %%
# --- Fetch BTC and ETH data live ---
btc_payload = cg.get_companies_treasury("bitcoin")
eth_payload = cg.get_companies_treasury("ethereum")

btc_price_resp = cg.get_simple_price(["bitcoin"], ["usd"])
eth_price_resp = cg.get_simple_price(["ethereum"], ["usd"])

btc_price_usd = btc_price_resp.get("bitcoin", {}).get("usd", 0.0)
eth_price_usd = eth_price_resp.get("ethereum", {}).get("usd", 0.0)

# --- Normalize ---
btc_df = normalize_companies_payload(btc_payload)
eth_df = normalize_companies_payload(eth_payload)

# --- Enrich with values ---
btc_df = add_values_fx(btc_df, coin_price_usd=btc_price_usd, fiat_rates={'usd': 1}, fiat="usd")
eth_df = add_values_fx(eth_df, coin_price_usd=eth_price_usd, fiat_rates={'usd': 1}, fiat="usd")

# --- Merge BTC + ETH ---
merged_df = pd.merge(
    btc_df[['name', 'total_holdings', 'value_usd']],
    eth_df[['name', 'total_holdings', 'value_usd']],
    on="name",
    how="outer",
    suffixes=("_BTC", "_ETH")
).fillna(0)

# Compute combined USD value
merged_df["Total Value (USD)"] = merged_df["value_usd_BTC"] + merged_df["value_usd_ETH"]

# Rename columns nicely
merged_df = merged_df.rename(columns={
    "total_holdings_BTC": "BTC Holdings",
    "value_usd_BTC": "BTC Value (USD)",
    "total_holdings_ETH": "ETH Holdings",
    "value_usd_ETH": "ETH Value (USD)"
})

# --- Save snapshot ---
save_snapshot(merged_df, "btc_eth_merged")

# --- Display formatted table ---
display(
    merged_df.style.format({
        "BTC Holdings": "{:,.4f}",
        "ETH Holdings": "{:,.4f}",
        "BTC Value (USD)": "${:,.2f}",
        "ETH Value (USD)": "${:,.2f}",
        "Total Value (USD)": "${:,.2f}"
    })
)

print("✅ Live BTC + ETH snapshot saved and merged!")


# %% [markdown]
# ## 7 — Visualize a snapshot (Altair)
# 
# Run after creating a snapshot. Shows top holders by coins.

# %%
# --- Visualization ---
import altair as alt

df_long = merged_df.melt(
    id_vars="name",
    value_vars=["BTC Value (USD)", "ETH Value (USD)"],
    var_name="Asset",
    value_name="Value (USD)"
)

top_n = 10  # show top 10 by total value
top_companies = merged_df.sort_values("Total Value (USD)", ascending=False).head(top_n)["name"]
df_long = df_long[df_long["name"].isin(top_companies)]

chart = alt.Chart(df_long).mark_bar().encode(
    x=alt.X("Value (USD):Q", axis=alt.Axis(format="~s")),
    y=alt.Y("name:N", sort="-x", title="Company"),
    color="Asset:N",
    tooltip=[
        alt.Tooltip("name", title="Company"),
        alt.Tooltip("Asset", title="Asset"),
        alt.Tooltip("Value (USD):Q", format=",.2f")
    ]
).properties(
    height=400,
    title="Top 10 Companies Holding BTC & ETH"
)

chart

# %% [markdown]
# ## 8 — What‑if quick simulation
# 
# Set `proj_change_pct` and re-run the cell.

# %%
proj_change_pct = 1.10  # 10% up
coins_to_check = ["bitcoin", "ethereum"]

for coin in coins_to_check:
    snap = latest_snapshot(coin)
    if not snap:
        print(f"Run fetch cell first for {coin}")
        continue

    print(f"\n=== {coin.upper()} ===")
    df_snap = snap["data"].copy()
    
    # Current vs projected price
    current_price = df_snap["value_usd"].sum() / (
        df_snap["coins"].sum() if df_snap["coins"].sum() else 1
    )
    projected_price = current_price * proj_change_pct
    df_snap["proj_value_usd"] = df_snap["coins"] * projected_price

    # Totals
    total_now = df_snap["value_usd"].sum()
    total_proj = df_snap["proj_value_usd"].sum()

    print(f"Current total value (USD): ${total_now:,.0f}")
    print(f"Projected (x{proj_change_pct}) total value (USD): ${total_proj:,.0f}")

    # Add TOTAL row at the bottom
    totals_row = pd.DataFrame([{
        "name": "TOTAL",
        "coins": df_snap["coins"].sum(),
        "value_usd": total_now,
        "proj_value_usd": total_proj
    }])
    df_out = pd.concat([df_snap[["name", "coins", "value_usd", "proj_value_usd"]], totals_row], ignore_index=True)

    # Nicely formatted DataFrame
    display(
        df_out.style.format({
            "coins": "{:,.4f}",          # 4 decimals for coin amounts
            "value_usd": "${:,.2f}",     # $ + 2 decimals
            "proj_value_usd": "${:,.2f}"
        })
    )


# %% [markdown]
# ## 9 — Export a Streamlit app (optional)
# 
# This will write `app.py` that reads joblib snapshots and provides a simple Streamlit UI. After creating `app.py`, run:
# 
# ```
# streamlit run app.py
# ```
# 

# %%
app_code = r'''import os
from datetime import datetime
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
import joblib
from pathlib import Path

load_dotenv()
DATA_DIR = Path('data')
SNAP_PATH = DATA_DIR / 'treasury_snapshots.pkl'

st.set_page_config(page_title='Treasury Tracker', layout='wide')
st.title('📊 Public Companies Crypto Treasury Tracker (Demo)')

coin = st.sidebar.selectbox('Coin', ['bitcoin','ethereum'])
fiat = st.sidebar.selectbox('Display currency', ['usd','eur','jpy','gbp','ngn'])
assumed_cost = st.sidebar.number_input('Assumed cost per coin (USD)', min_value=0.0, value=0.0)
fetch_now = st.sidebar.button('Fetch latest now')

def load_snapshots():
    if SNAP_PATH.exists():
        return joblib.load(SNAP_PATH)
    return []

def save_snapshot(df, coin):
    DATA_DIR.mkdir(exist_ok=True)
    rec = {'timestamp': datetime.utcnow().isoformat() + 'Z', 'coin': coin, 'data': df}
    snaps = load_snapshots()
    snaps.append(rec)
    joblib.dump(snaps, SNAP_PATH)

if fetch_now:
    st.info('Fetch requested — make sure COINGECKO_API_KEY is set in .env')
    try:
        from src.api import CoinGeckoClient
        from src.transform import normalize_companies_payload, add_values_fx, compute_pnl
        cg = CoinGeckoClient()
        payload = cg.get_companies_treasury(coin)
        price_resp = cg.get_simple_price([coin], ['usd'])
        price_usd = price_resp.get(coin, {}).get('usd', 0.0)
        df = normalize_companies_payload(payload)
        df = add_values_fx(df, coin_price_usd=price_usd, fiat_rates={'usd':1.0}, fiat='usd')
        df = compute_pnl(df, assumed_cost_per_coin_usd=(assumed_cost if assumed_cost>0 else None))
        save_snapshot(df, coin)
        st.success('Fetched and saved snapshot')
    except Exception as e:
        st.error(f'Failed to fetch: {e}')

snaps = load_snapshots()
if not snaps:
    st.info('No snapshots yet. Use Fetch Latest Now to create one.')
else:
    latests = [s for s in snaps if s['coin']==coin]
    if not latests:
        st.info('No snapshots for selected coin yet.')
    else:
        latest = latests[-1]
        df = latest['data']
        st.subheader(f"Latest snapshot for {coin} @ {latest['timestamp']}")
        st.dataframe(df, use_container_width=True)
        if 'coins' in df.columns:
            st.bar_chart(df.sort_values('coins', ascending=False).set_index('name')['coins'].head(10))
'''

# --- Write the string above into app.py ---
with open('app.py','w',encoding='utf-8') as f:
    f.write(app_code)

print('✅ Wrote app.py. Now run: streamlit run app.py')


# %% [markdown]
# ## 10 — Next steps
# 
# - Automate fetches with cron or GitHub Actions.
# - Add historical aggregation and charts.
# - Consider migrating to SQLite/Postgres for larger histories.
# 
# ---
# 
# Download the notebook and run it in Jupyter or VSCode. If you'd like, I can now bundle this notebook plus a `src/` folder and `app.py` into a ZIP for you.


