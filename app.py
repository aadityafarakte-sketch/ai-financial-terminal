import streamlit as st
import plotly.graph_objects as go
import json
import time
import yfinance as yf
import pandas as pd  # FIXED: Issue #1 - Added missing pandas dependency to prevent NameErrors

import finance_tools
import ai_engine

# --- INITIALIZATION ENGINE ---
# FIXED: Issue #10 - Use clean, standardized setdefault initialization for state safety
st.session_state.setdefault("active_ticker", "RELIANCE.NS")
st.session_state.setdefault("active_exchange", "NSE")

# Initialize relational tracking schemas at boot
finance_tools.init_db()

# --- STREAMLIT UI LAYOUT DESIGN ---
st.set_page_config(page_title="AI Financial Terminal", layout="wide", initial_sidebar_state="expanded")

# Inject Custom Dark CSS Theme Core Elements
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    div[data-testid="stMetricValue"] { font-size: 1.8rem; color: #00ffcc; }
    .stButton>button { background-color: #262730; color: white; border-radius: 6px; }
    </style>
""", unsafe_allow_html=True)

st.title("📈 Advanced AI Institutional Financial Terminal")
st.caption("Production-Grade Real-Time Data Pipeline, Optimized Caching Framework & Risk Sizing Engine")
st.markdown("---")

# --- SIDEBAR CONTROLS: CAPITAL DESK & PORTFOLIO TRACKER ---
st.sidebar.header("💼 Quantitative Risk Desk")
total_capital = st.sidebar.number_input("Total Trading Capital", min_value=1000.0, value=100000.0, step=5000.0)
risk_pct = st.sidebar.slider("Risk Tolerance per Trade (%)", min_value=0.1, max_value=5.0, value=1.0, step=0.1)
risk_amount = total_capital * (risk_pct / 100.0)

st.sidebar.markdown("---")
st.sidebar.header("⭐ Asset Watchlist")
watchlist_items = finance_tools.get_watchlist()

if watchlist_items:
    for ticker_item, exchange_item in watchlist_items:
        cols = st.sidebar.columns([3, 1])
        cols[0].write(f"**{ticker_item}** ({exchange_item})")
        if cols[1].button("❌", key=f"del_{ticker_item}_{exchange_item}"):
            finance_tools.remove_from_watchlist(ticker_item, exchange_item)
            st.rerun()
else:
    st.sidebar.info("Watchlist is empty. Search an asset to track it.")

# --- MAIN DASHBOARD INTERFACE INPUTS ---
c1, c2 = st.columns([3, 1])
target_input = c1.text_input("Enter Asset Ticker (e.g., RELIANCE.NS, TCS.NS, AAPL, NVDA)", value=st.session_state.active_ticker).upper().strip()
exchange_select = c2.selectbox("Market Exchange", ["NSE", "BSE", "NASDAQ", "NYSE"], index=["NSE", "BSE", "NASDAQ", "NYSE"].index(st.session_state.active_exchange))

# FIXED: Issue #5 - Dynamic International Localization and Currency Metric Flag Assignment
is_indian = target_input.endswith(".NS") or target_input.endswith(".BO")
currency_symbol = "₹" if is_indian else "$"

if st.button("🔍 Run Terminal Analytics Engine", use_container_width=True):
    st.session_state.active_ticker = target_input
    st.session_state.active_exchange = exchange_select

# --- FIXED: Issue #2, #3, #6, #7 - HIGH PERFORMANCE CENTRALIZED DATA FETCH PIPELINE ---
@st.cache_data(ttl=300) # FIXED: Issue #3 - Implemented 5-minute data retention cache layer
def get_unified_terminal_data(ticker):
    """
    Orchestrates data fetching. Instantiates yf.Ticker ONCE (Issue #2),
    reuses the historical dataframe for indicators and graphing (Issue #7),
    and wraps the network pipeline in an exponential backoff retry loop (Issue #6).
    """
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Fetch unified 1-year history vector at runtime
            hist_df = yf.download(ticker, period="1y", progress=False)
            if hist_df.empty:
                raise ValueError("Downloaded data frame returned empty metrics from network channel.")
            
            # Instantiate single core ticker structure
            stock_obj = yf.Ticker(ticker)
            
            # Route shared instantiated dependencies directly down to computation filters
            current_price = finance_tools.get_current_price(ticker, hist_df)
            tech_indicators = finance_tools.get_technical_indicators(ticker, hist_df)
            key_ratios = finance_tools.get_key_ratios(stock_obj, current_price)
            financial_health = finance_tools.get_financial_health(stock_obj)
            graham_value = finance_tools.calculate_graham_value(stock_obj, current_price)
            shareholding = finance_tools.get_shareholding_pattern(stock_obj)
            news_headlines = finance_tools.get_recent_news_headlines(ticker)
            
            return {
                "current_price": current_price,
                "tech_indicators": tech_indicators,
                "key_ratios": key_ratios,
                "financial_health": financial_health,
                "graham_value": graham_value,
                "shareholding": shareholding,
                "news_headlines": news_headlines,
                "hist_df_json": hist_df.reset_index().to_json() # Safe JSON serialization for cache storage
            }
        except Exception as e:
            if attempt == max_retries - 1:
                return None
            time.sleep(2 ** attempt) # Exponential backoff safety multiplier
    return None

# Execute primary user pipeline rendering loop
if st.session_state.active_ticker:
    ticker = st.session_state.active_ticker
    exchange = st.session_state.active_exchange
    
    with st.spinner(f"Extracting serverless data metrics for {ticker}..."):
        data_payload = get_unified_terminal_data(ticker)
        
    if not data_payload or data_payload["current_price"] is None:
        st.error(f"Network Connection Interrupted: Failed to extract data for {ticker}. Verify ticker format or retry.")
    else:
        # Deconstruct verified data components out of cached structure
        current_price = data_payload["current_price"]
        tech_indicators = data_payload["tech_indicators"]
        key_ratios = data_payload["key_ratios"]
        financial_
