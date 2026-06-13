import streamlit as st
import plotly.graph_objects as go
import json
import time
import logging
import re
import yfinance as yf
import pandas as pd

import finance_tools
import ai_engine

# --- STRUCTURED LOGGING FRAMEWORK ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
logger = logging.getLogger(__name__)

# --- SAFE SESSION STATE INITIALIZATION ---
st.session_state.setdefault("active_ticker", None)
st.session_state.setdefault("active_exchange", None)

# Initialize background relational tracking tables
try:
    finance_tools.init_db()
except Exception as db_err:
    logger.error(f"Database infrastructure initialization failure: {type(db_err).__name__}")

# --- STREAMLIT PAGE ARCHITECTURE CONFIGURATION ---
st.set_page_config(
    page_title="AI Financial Terminal",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject Custom Dark CSS Theme Core Styling
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

# --- SIDEBAR DESK: RISK PARAMS & WATCHLIST CONTROL ---
st.sidebar.header("💼 Quantitative Risk Desk")
total_capital = st.sidebar.number_input("Total Trading Capital", min_value=1000.0, value=100000.0, step=5000.0)
risk_pct = st.sidebar.slider("Risk Tolerance per Trade (%)", min_value=0.1, max_value=5.0, value=1.0, step=0.1)
risk_amount = total_capital * (risk_pct / 100.0)

max_share_cap = st.sidebar.number_input("Maximum Allowed Position Shares", min_value=1000, value=50000000, step=50000)

st.sidebar.markdown("---")
st.sidebar.header("⭐ Asset Watchlist")
try:
    watchlist_items = finance_tools.get_watchlist()
except Exception as wl_err:
    logger.error(f"Failed to query watchlist schema: {type(wl_err).__name__}")
    watchlist_items = []

if watchlist_items:
    for ticker_item, exchange_item in watchlist_items:
        cols = st.sidebar.columns([3, 1])
        cols[0].write(f"**{ticker_item}** ({exchange_item})")
        if cols[1].button("❌", key=f"del_{ticker_item}_{exchange_item}"):
            try:
                finance_tools.remove_from_watchlist(ticker_item, exchange_item)
                st.toast(f"Removed {ticker_item} from tracker.")
                st.rerun()
            except Exception as wl_del_err:
                logger.error(f"Failed to delete watchlist row element: {type(wl_del_err).__name__}")
else:
    st.sidebar.info("Watchlist is empty. Search an asset to track it.")

# --- MAIN CONTROLLER PANEL: TICKER PROCESSING & ROUTING ---
c1, c2 = st.columns([3, 1])
target_input = c1.text_input(
    "Enter Asset Ticker (e.g., RELIANCE.NS, TCS.NS, AAPL, NVDA)", 
    value=st.session_state.active_ticker if st.session_state.active_ticker else ""
).upper().strip()

exchange_select = c2.selectbox(
    "Market Exchange", 
    ["NSE", "BSE", "NASDAQ", "NYSE"], 
    index=["NSE", "BSE", "NASDAQ", "NYSE"].index(st.session_state.active_exchange) if st.session_state.active_exchange else 0
)

is_valid_input = True
if target_input:
    if not re.match(r'^[A-Z0-9.-]{1,15}$', target_input):
        st.error("Malformed Ticker Symbol: Please verify characters and regional syntax format.")
        is_valid_input = False

if st.button("🔍 Run Terminal Analytics Engine", use_container_width=True) and is_valid_input:
    if not target_input:
        st.error("Empty Input: Please specify a valid market ticker identifier before running analytics.")
    else:
        st.session_state.active_ticker = target_input
        st.session_state.active_exchange = exchange_select
        st.rerun()

# --- CENTRALIZED USER PERFORMANCE DATA FETCH PIPELINE ---
@st.cache_data(ttl=300)
def get_unified_terminal_data(ticker_symbol):
    logger.info(f"Initiating network data extraction pipeline for asset: {ticker_symbol}")
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            hist_df = yf.download(ticker_symbol, period="1y", progress=False)
            if hist_df.empty:
                raise ValueError("The downloaded financial dataframe returned empty metrics from the network channel.")
            
            if isinstance(hist_df.columns, pd.MultiIndex):
                hist_df.columns = hist_df.columns.get_level_values(0)
            
            hist_df = hist_df.reset_index()
            
            if 'Date' not in hist_df.columns:
                date_candidates = [col for col in hist_df.columns if 'date' in str(col).lower()]
                if date_candidates:
                    hist_df.rename(columns={date_candidates[0]: 'Date'}, inplace=True)
                else:
                    hist_df['Date'] = hist_df.index

            # FIXED: Issue #1 & #3 - Swapped multiple arguments for a single string parameter and removed unused stock_obj
            current_price = finance_tools.get_current_price(ticker_symbol)
            tech_indicators = finance_tools.get_technical_indicators(ticker_symbol)
            key_ratios = finance_tools.get_key_ratios(ticker_symbol)
            financial_health = finance_tools.get_financial_health(ticker_symbol)
            graham_value = finance_tools.calculate_graham_value(ticker_symbol)
            shareholding = finance_tools.get_shareholding_pattern(ticker_symbol)
            news_headlines = finance_tools.get_recent_news_headlines(ticker_symbol)
            
            return {
                "current_price": current_price,
                "tech_indicators": tech_indicators,
                "key_ratios": key_ratios,
                "financial_health": financial_health,
                "graham_value": graham_value,
                "shareholding": shareholding,
                "news_headlines": news_headlines,
                "hist_df": hist_df  
            }
        except Exception as exc:
            # FIXED: Issue #2 - Corrected indentation parameters inside the diagnostic error block
            st.error(f"🚨 DEBUG ERROR: {type(exc).__name__}: {str(exc)}")
            logger.exception(exc)
            raise exc
            
    return None

# --- RUN RENDER ROUTINE ---
if st.session_state.active_ticker:
    ticker = st.session_state.active_ticker
    exchange = st.session_state.active_exchange
    
    is_indian = ticker.endswith(".NS") or ticker.endswith(".BO")
    currency_symbol = "₹" if is_indian else "$"
    
    with st.spinner(f"Extracting serverless data metrics for {ticker}..."):
        data_payload = get_unified_terminal_data(ticker)
        
    # FIXED: Issue #4 - Relaxed checking constraints to isolate structural breaks to missing current price components only
    if not data_payload or data_payload["current_price"] is None:
        st.error(f"Pipeline Connection Refused: Unable to extract complete structural data profiles for {ticker}. Verify network channels or exchange formatting suffix.")
    else:
        current_price = data_payload["current_price"]
        tech_indicators = data_payload["tech_indicators"] or {}
        key_ratios = data_payload["key_ratios"] or {}
        financial_health = data_payload["financial_health"] or {}
        graham_value = data_payload["graham_value"]
        shareholding = data_payload["shareholding"] or {}
        news_headlines = data_payload["news_headlines"] or []
        hist_df = data_payload["hist_df"] 
        
        # User Action Layout
        col_actions = st.columns(2)
        if col_actions[0].button("➕ Add Asset to Core Watchlist Tracker", use_container_width=True):
            try:
                finance_tools.add_to_watchlist(ticker, exchange)
                st.toast(f"Successfully pinned {ticker} to Watchlist!")
                st.rerun()
            except Exception as wl_add_err:
                logger.error(f"Watchlist insertion failure: {type(wl_add_err).__name__}")
                st.error("Failed to append asset target row data onto watch database tables.")
            
        # True Data Completeness Calculation Loop Matrix
        completeness_vector = [
            key_ratios.get("P/E Ratio"),
            key_ratios.get("Forward P/E"),
            key_ratios.get("Price to Book"),
            financial_health.get("ROE"),
            financial_health.get("Debt to Equity"),
            financial_health.get("Free Cash Flow"),
            tech_indicators.get("RSI"),
            tech_indicators.get("Support"),
            tech_indicators.get("Resistance"),
            graham_value
        ]
        
        def run_valid_check(metric_element):
            if metric_element is None: return False
            if isinstance(metric_element, str) and metric_element.strip().upper() in ["N/A", "NONE", "NULL", "NAN"]: return False
            return True
            
        valid_metrics_sum = sum(1 for item in completeness_vector if run_valid_check(item))
        quality_score = round((valid_metrics_sum / len(completeness_vector)) * 100)
        
        # TECHNICAL BOUNDARY RISK ENGINE TRIGGER
        support_floor = tech_indicators.get("Support", 0.0)
        if support_floor and current_price < support_floor:
            st.markdown(f"""
                <div style='background-color:#4d0000; padding:15px; border-radius:8px; border-left:6px solid #ff3333; margin-bottom:15px;'>
                    <h3 style='margin:0; color:#ffcccc;'>⚠️ CRITICAL STRUCTURAL RISK ALERT</h3>
                    <p style='margin:5px 0 0 0; color:#ffffff;'>Asset price has broken beneath its technical support floor boundary of <b>{currency_symbol}{support_floor:,.2f}</b>.</p>
                </div>
            """, unsafe_allow_html=True)

        # Core Numeric Metrics Display Containers
        st.subheader("📊 Institutional Core Data Grid")
        st.caption(f"Strict Pipeline Integration Integrity Quality Score: {quality_score}%")
        
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        m_col1.metric("Live Market Price", f"{currency_symbol}{current_price:,.2f}")
        m_col2.metric("Relative Strength Index (RSI 14)", f"{tech_indicators.get('RSI'):.2f}" if tech_indicators.get('RSI') else "N/A")
        m_col3.metric("EMA 20 Vector Floor", f"{currency_symbol}{tech_indicators.get('EMA_20'):,.2f}" if tech_indicators.get('EMA_20') else "N/A")
        m_col4.metric("EMA 50 Vector Floor", f"{currency_symbol}{tech_indicators.get('EMA_50'):,.2f}" if tech_indicators.get('EMA_50') else "N/A")
        
        m_col5, m_col6, m_col7, m_col8 = st.columns(4)
        m_col5.metric("50 Day Moving Average", f"{currency_symbol}{tech_indicators.get('50 DMA'):,.2f}" if tech_indicators.get('50 DMA') else "N/A")
        m_col6.metric("200 Day Moving Average", f"{currency_symbol}{tech_indicators.get('200 DMA'):,.2f}" if tech_indicators.get('200 DMA') else "N/A")
        m_col7.metric("Support Floor Baseline", f"{currency_symbol}{support_floor:,.2f}" if support_floor else "N/A")
        m_col8.metric("Resistance Ceiling Wall", f"{currency_symbol}{tech_indicators.get('Resistance'):,.2f}" if tech_indicators.get('Resistance') else "N/A")

        st.markdown("---")
        
        # Fundamental Parameters Statement Sections
        f_col1, f_col2 = st.columns(2)
        with f_col1:
            st.markdown("### 📈 Core Financial Valuation Ratios")
            st.write(f"**Trailing P/E Ratio:** {key_ratios.get('P/E Ratio') if key_ratios.get('P/E Ratio') is not None else 'N/A'}")
            st.write(f"**Forward P/E Prediction:** {key_ratios.get('Forward P/E') if key_ratios.get('Forward P/E') is not None else 'N/A'}")
            st.write(f"**Price to Book Value (P/B):** {key_ratios.get('Price to Book') if key_ratios.get('Price to Book') is not None else 'N/A'}")
            
        with f_col2:
            st.markdown("### 🏥 Corporate Financial Health & Scales")
            st.write(f"**Return on Equity (ROE):** {financial_health.get('ROE') if financial_health.get('ROE') is not None else 'N/A'}")
            st.write(f"**Debt to Equity Leverage Ratio:** {financial_health.get('Debt to Equity') if financial_health.get('Debt to Equity') is not None else 'N/A'}")
            st.write(f"**Calculated Free Cash Flow:** {financial_health.get('Free Cash Flow') if financial_health.get('Free Cash Flow') is not None else 'N/A'}")

        st.markdown("---")

        # --- POSITION DESK & VALUATION MATRIX CONTROL CENTERS ---
        v_left, v_right = st.columns(2)
        with v_left:
            st.markdown("### 🎯 Quantitative Capital Position Allocations")
            
            default_stop_value = float(support_floor) if (support_floor and support_floor < current_price and support_floor > 0) else float(current_price * 0.95)
            
            stop_loss = st.number_input(
                f"Define Execution Stop Loss ({currency_symbol})", 
                min_value=0.0, 
                max_value=float(current_price * 2.0), 
                value=default_stop_value, 
                step=1.0
            )
            
            min_allowable_gap = current_price * 0.002 
            per_share_risk = abs(current_price - stop_loss)
            
            if stop_loss <= 0:
                st.error("Invalid Configuration Parameter: Stop loss threshold values must strictly sit above zero.")
                max_shares_to_buy, total_trade_value = 0, 0.0
            elif per_share_risk < min_allowable_gap:
                st.warning(f"Stop Loss gap configuration limits are near zero (Minimum variance: {currency_symbol}{min_allowable_gap:,.2f}). Position calculator locked out to prevent division overflows.")
                max_shares_to_buy, total_trade_value = 0, 0.0
            else:
                risk_based_shares = int(risk_amount / per_share_risk)
                capital_based_shares = int(total_capital / current_price)
                max_shares_to_buy = min(risk_based_shares, capital_based_shares)
                
                if max_shares_to_buy > max_share_cap:
                    max_shares_to_buy = max_share_cap
                    
                total_trade_value = max_shares_to_buy * current_price
            
            st.info(f"**Max Financial Risk Allocation Budget:** {currency_symbol} {risk_amount:,.2f}")
            st.write(f"**Calculated Position Purchasing Cap:** {max_shares_to_buy:,} Shares")
            st.write(f"**Net Position Capital Allocation Cost:** {currency_symbol} {total_trade_value:,.2f}")

        with v_right:
            st.markdown("### 💎 Asset Intrinsic Valuation Matrix")
            cols_val = st.columns(2)
            
            if graham_value is not None:
                margin_of_safety = ((graham_value - current_price) / graham_value) * 100
                cols_val[0].metric("Benjamin Graham Value", f"{currency_symbol}{graham_value:,.2f}")
                if margin_of_safety > 0:
                    cols_val[0].success(f"Undervalued: {margin_of_safety:.1f}% MOS")
                else:
                    cols_val[0].error(f"Overvalued: {abs(margin_of_safety):.1f}% Premium")
            else:
                cols_val[0].info("Graham Value: N/A")
                
            cols_val[1].warning("DCF Disabled. Public market data reporting layers are insufficient for reliable retail cash calculations.")

        st.markdown("---")

        # --- STRUCTURAL PLOTLY GRAPHING MODULES ---
        g1, g2 = st.columns([2, 1])
        with g1:
            st.markdown("### 📊 6-Month Historical Close Vector Candlestick")
            if hist_df is not None and not hist_df.empty and 'Date' in hist_df.columns:
                try:
                    hist_df['Date'] = pd.to_datetime(hist_df['Date'])
                    six_months_cutoff = hist_df['Date'].max() - pd.Timedelta(days=180)
                    filtered_chart_df = hist_df[hist_df['Date'] >= six_months_cutoff]
                    
                    fig = go.Figure(data=[go.Candlestick(
                        x=filtered_chart_df['Date'], open=filtered_chart_df['Open'], high=filtered_chart_df['High'],
                        low=filtered_chart_df['Low'], close=filtered_chart_df['Close'], name=ticker
                    )])
                    fig.update_layout(template="plotly_dark", margin=dict(l=20, r=20, t=20, b=20), height=380)
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as chart_err:
                    logger.error(f"Plotly candlestick vector map rendering exception: {type(chart_err).__name__}")
                    st.info("Graphic tracking metrics interrupted by browser rendering threads.")
            else:
                st.info("Historical tracking graphics stream unavailable.")

        with g2:
            st.markdown("### 🥧 Corporate Equity Allocation Pattern")
            insiders = shareholding.get("insiders")
            institutions = shareholding.get("institutions")
            
            insiders_pct = insiders * 100 if insiders is not None else 0.0
            inst_pct = institutions * 100 if institutions is not None else 0.0
            public_pct = max(0.0, 100.0 - (insiders_pct + inst_pct))
            
            label_insider = 'Promoter / Insider' if is_indian else 'Insider Holdings'
            label_inst = 'Institutional (FII/DII)' if is_indian else 'Institutional Holdings'
            
            labels = [label_insider, label_inst, 'Public & Retail']
            values = [insiders_pct, inst_pct, public_pct]
            
            if sum(values) > 0:
                fig_pie = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.4)])
                fig_pie.update_layout(template="plotly_dark", margin=dict(l=10, r=10, t=10, b=10), height=380, showlegend=True)
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("Shareholding structural parameters missing on regional reporting feeds.")

        st.markdown("---")

        # --- SPECIALIZED AI EQUITY RESEARCH INTELLIGENCE ENGINE ---
        st.subheader("🤖 Generative AI Research Analyst Engine")
        user_query = st.text_input(
            "Issue Query or Analysis Commands to the Financial Analyst Agent:", 
            value=f"Provide a comprehensive equity research brief and target risk assessment profile for {ticker} based on the real-time data grid."
        )

        if st.button("🧠 Execute High-Conviction AI Inference Run"):
            with st.spinner("Processing deep quantitative neural vector loops..."):
                try:
                    financial_context_dict = {
                        "Ticker Symbol": ticker,
                        "Current Market Price Value": current_price,
                        "Technical Indicator Baseline Vector Summary": tech_indicators,
                        "Core Financial Multipliers and Valuation Metrics": key_ratios,
                        "Corporate Accounting Health and Statements Scale": financial_health,
                        "Computed Intrinsic Benjamin Graham Value Floor": graham_value,
                        "Recent Corporate Media Catalysts Framework": news_headlines
                    }
                    
                    serialized_financial_context = json.dumps(financial_context_dict, indent=2, default=str)
                    ai_report = ai_engine.generate_financial_analysis(ticker, user_query, serialized_financial_context)
                    
                    if isinstance(ai_report, dict) and not ai_report.get("success"):
                        logger.error(f"Structured error payload captured: {ai_report.get('error')}")
                        st.error(f"The AI Research Engine turned up an error: {ai_report.get('error_msg', 'Service Limit Reached')}")
                    elif "exception" in str(ai_report).lower() or "error" in str(ai_report).lower() or "unauthorized" in str(ai_report).lower():
                        logger.error("API call execution bottleneck caught in processing logs.")
                        st.error("The AI Research Engine encountered an API connection block or quota limit hurdle. Please verify configuration keys.")
                    else:
                        st.markdown("### 📋 Institutional Equity Research Brief")
                        st.markdown(ai_report)
                except Exception as ai_run_err:
                    logger.error(f"Generative AI execution pipeline failure: {type(ai_run_err).__name__}")
                    st.error("An unexpected service interruption occurred while building research reports via the cloud intelligence engine.")
else:
    st.info("🔍 Terminal Onboarding Check Complete. Enter an asset ticker symbol up top and hit 'Run Terminal Analytics Engine' to stream real-time quantitative records.")

# --- COMPLIANCE REGULATORY DISCLAIMER FOOTER ---
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #555555; font-size: 0.8rem;'>"
    "⚠️ <b>Legal Disclaimer:</b> This terminal is built exclusively for educational, instructional, and research-tracking demonstrations. "
    "It does not constitute official financial advice, capital management allocation structures, or equity purchasing recommendations. "
    "All computational math model metrics are pulled from public tracking infrastructure."
    "</div>", 
    unsafe_allow_html=True
)
