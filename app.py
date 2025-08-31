import os
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
