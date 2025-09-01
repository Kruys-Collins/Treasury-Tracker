import streamlit as st
import pandas as pd
import joblib
from pathlib import Path
import plotly.express as px
from datetime import datetime, timezone
from dateutil import parser

# =============================
# Load Snapshots from joblib
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

def latest_merged():
    snaps = load_snapshots()
    snaps_merged = [s for s in snaps if s.get("coin") == "btc_eth_merged"]
    if not snaps_merged:
        return None
    return snaps_merged[-1]

# =============================
# Formatting helpers
# =============================
def fmt_usd(x):
    try:
        return f"${float(x):,.0f}"
    except Exception:
        return x

def fmt_num(x):
    try:
        return f"{float(x):,.0f}"
    except Exception:
        return x

# Choose the correct USD-value column in a DataFrame
def detect_usd_col(df, hint=None):
    candidates = []
    if hint:
        candidates.append(hint)
    candidates += [
        "total_current_value_usd",  # notebook single-coin
        "value_usd",                # some steps use this
        "Total Value (USD)",        # merged view
        "BTC Value (USD)",          # per-asset in merged
        "ETH Value (USD)",
    ]
    # Fallback: any column that looks like a USD value
    candidates += [c for c in df.columns if "usd" in c.lower() or "value" in c.lower()]
    for c in candidates:
        if c in df.columns:
            return c
    return None  # graceful handling in the UI

# Ensure a "total_holdings" column exists for KPIs/charts
def ensure_total_holdings(df):
    df = df.copy()
    if "total_holdings" in df.columns:
        return df
    if "coins" in df.columns:
        df["total_holdings"] = pd.to_numeric(df["coins"], errors="coerce").fillna(0.0)
        return df
    # merged snapshot may have split holdings
    btc_col = "BTC Holdings" if "BTC Holdings" in df.columns else None
    eth_col = "ETH Holdings" if "ETH Holdings" in df.columns else None
    if btc_col or eth_col:
        df["total_holdings"] = 0.0
        if btc_col:
            df["total_holdings"] = df["total_holdings"] + pd.to_numeric(df[btc_col], errors="coerce").fillna(0.0)
        if eth_col:
            df["total_holdings"] = df["total_holdings"] + pd.to_numeric(df[eth_col], errors="coerce").fillna(0.0)
        return df
    # last resort: try the first numeric column
    num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if num_cols:
        df["total_holdings"] = pd.to_numeric(df[num_cols[0]], errors="coerce").fillna(0.0)
    else:
        df["total_holdings"] = 0.0
    return df

# Format all number columns in a copy for display (tables),
# without touching the numeric df used for charts.
def format_table(df):
    df_fmt = df.copy()
    cols_usd_strict = {"BTC Value (USD)", "ETH Value (USD)", "Total Value (USD)", "value_usd", "total_current_value_usd"}
    usd_like = [c for c in df_fmt.columns if ("usd" in c.lower()) or (c in cols_usd_strict)]
    hold_like = [c for c in df_fmt.columns if ("holdings" in c.lower()) or (c.lower() in {"coins"})]

    for c in usd_like:
        df_fmt[c] = df_fmt[c].apply(fmt_usd)
    for c in hold_like:
        df_fmt[c] = df_fmt[c].apply(fmt_num)
    return df_fmt

# =============================
# Streamlit Page Config & Heading
# =============================
st.set_page_config(page_title="Crypto Treasury Dashboard", layout="wide")
st.markdown(
    "<h2 style='text-align: center; margin-bottom: 10px;'>📊 Public Companies Crypto Treasury Tracker</h2>",
    unsafe_allow_html=True
)

# Friendly timestamp from any latest snapshot
latest_any = latest_snapshot("bitcoin") or latest_snapshot("ethereum") or latest_merged()
if latest_any:
    snapshot_raw = latest_any.get("timestamp")
    try:
        snapshot_dt = parser.isoparse(snapshot_raw)
        now = datetime.now(timezone.utc)
        delta = now - snapshot_dt
        if delta.days == 0:
            snapshot_display = f"{delta.seconds // 60} minutes ago" if delta.seconds < 3600 else f"{delta.seconds // 3600} hours ago"
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
    except Exception:
        pass

st.markdown("---")

# =============================
# Tabs (Design unchanged)
# =============================
tab1, tab2, tab3 = st.tabs(["₿ Bitcoin", "Ξ Ethereum", "₿+Ξ Combined"])

# =============================
# Core renderer (cards → pie → bar → table)
# =============================
def render_dashboard(df, asset_name, total_supply=None, usd_hint=None):
    if df is None or df.empty:
        st.warning(f"No data available for {asset_name}")
        return

    # Ensure required columns exist
    df = ensure_total_holdings(df)
    usd_col = detect_usd_col(df, hint=usd_hint)

    # Coerce numerics (for charts/KPIs)
    for c in df.columns:
        if c == "name":
            continue
        # don't coerce already formatted strings like "$1,234"
        if pd.api.types.is_numeric_dtype(df[c]):
            continue
        # try convert; keep original if fails
        converted = pd.to_numeric(df[c], errors="coerce")
        if converted.notna().any():
            df[c] = converted.fillna(0)

    total_holdings = df["total_holdings"].sum() if "total_holdings" in df.columns else 0.0
    total_value = df[usd_col].sum() if usd_col and usd_col in df.columns else 0.0
    avg_holding = df["total_holdings"].mean() if "total_holdings" in df.columns else 0.0
    num_companies = df.shape[0]

    # KPI cards (same design)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
        <div style="border:2px solid #4CAF50; border-radius:10px; padding:15px; text-align:center;">
            <h4 style="margin:0;">Total {asset_name} Held</h4>
            <p style="font-size:20px; font-weight:bold;">{fmt_num(total_holdings)}</p>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div style="border:2px solid #2196F3; border-radius:10px; padding:15px; text-align:center;">
            <h4 style="margin:0;">Total Value (USD)</h4>
            <p style="font-size:20px; font-weight:bold;">{fmt_usd(total_value)}</p>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div style="border:2px solid #FF9800; border-radius:10px; padding:15px; text-align:center;">
            <h4 style="margin:0;">Avg {asset_name} / Company</h4>
            <p style="font-size:20px; font-weight:bold;">{fmt_num(avg_holding)}</p>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div style="border:2px solid #9C27B0; border-radius:10px; padding:15px; text-align:center;">
            <h4 style="margin:0;">Companies Tracked</h4>
            <p style="font-size:20px; font-weight:bold;">{num_companies}</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Pie chart
    if total_supply and asset_name in {"BTC", "ETH"}:
        company_holdings = float(total_holdings)
        other_holdings = max(float(total_supply) - company_holdings, 0)
        pie_df = pd.DataFrame({"holder": ["Public Companies", "Others"], "holdings": [company_holdings, other_holdings]})
        fig_pie = px.pie(pie_df, names="holder", values="holdings",
                         title=f"Share of {asset_name} Supply (Companies vs Others)",
                         hole=0.4, color_discrete_sequence=px.colors.sequential.RdBu)
        fig_pie.update_traces(textinfo="label+percent")
    else:
        # For combined tab, show company breakdown by USD value
        if not usd_col:
            st.warning("No USD value column detected for pie chart.")
            fig_pie = None
        else:
            pie_df = df.groupby("name")[usd_col].sum().reset_index()
            fig_pie = px.pie(pie_df, names="name", values=usd_col,
                             title=f"{asset_name} Breakdown by Company (USD Value)",
                             hole=0.4)

    # Bar chart (by USD)
    fig_bar = None
    if usd_col and usd_col in df.columns:
        df_sorted = df.sort_values(usd_col, ascending=False).head(25)
        fig_bar = px.bar(
            df_sorted,
            x="name",
            y=usd_col,
            title=f"Top Public Companies Holding {asset_name}",
            text=usd_col,
            color=usd_col,
            color_continuous_scale="Blues"
        )
        fig_bar.update_traces(
            texttemplate="%{text:,.0f}",
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>$%{y:,.2f}<extra></extra>"
        )
        fig_bar.update_yaxes(tickformat="~s", tickprefix="$")

    c1, c2 = st.columns(2)
    with c1:
        if fig_pie:
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Pie chart unavailable for this view.")
    with c2:
        if fig_bar:
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("Bar chart unavailable for this view.")

    st.markdown("---")

    # Table with formatting on ALL relevant columns
    st.subheader(f"{asset_name} Company Breakdown")
    st.dataframe(format_table(df), use_container_width=True)

# =============================
# Render Tabs (using your snapshots)
# =============================
with tab1:
    snap_btc = latest_snapshot("bitcoin")
    if snap_btc:
        render_dashboard(snap_btc["data"], "BTC", total_supply=21_000_000, usd_hint="value_usd")
    else:
        st.info("No BTC snapshot found. Run your notebook fetch first.")

with tab2:
    snap_eth = latest_snapshot("ethereum")
    if snap_eth:
        render_dashboard(snap_eth["data"], "ETH", total_supply=120_000_000, usd_hint="value_usd")
    else:
        st.info("No ETH snapshot found. Run your notebook fetch first.")

with tab3:
    snap_merged = latest_merged()
    if snap_merged:
        # merged has 'Total Value (USD)' plus per-asset columns
        render_dashboard(snap_merged["data"], "BTC+ETH", total_supply=None, usd_hint="Total Value (USD)")
    else:
        st.info("No merged snapshot found. Run the merge cell in your notebook.")
