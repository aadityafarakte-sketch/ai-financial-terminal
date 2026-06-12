import streamlit as st
import plotly.graph_objects as go
import json
import yfinance as yf
import finance_tools
import ai_engine

# Initialize SQLite structures cleanly at application boot
finance_tools.init_db()

# --- STREAMLIT UI DESIGN CONFIGURATION ---
st.set_page_config(page_title="AI Financial Terminal", layout="wide", initial_sidebar_state="expanded")

# Inject Custom Dark CSS UI Theme
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    div[data-testid="stMetricValue"] { font-size: 1.8rem; color: #00ffcc; }
    .stButton>button { background-color: #262730; color: white; border-radius: 6px; }
    </style>
""", unsafe_allow_html=True) # FIX: Changed from unsafe_allowed_html to unsafe_allow_html

st.title("📈 Advanced AI Institutional Financial Terminal")
st.caption("Real-Time Multi-Market Analytics, Quantitative Risk Desk & Deterministic AI Research Intelligence")
st.markdown("---")

# --- SIDEBAR: REVENUE CAP ALLOCATION & POSITION DESK ---
st.sidebar.header("💼 Quantitative Risk Desk")

total_capital = st.sidebar.number_input("Total Trading Capital", min_value=1000.0, value=100000.0, step=5000.0)
risk_pct = st.sidebar.slider("Risk Tolerance per Trade (%)", min_value=0.1, max_value=5.0, value=1.0, step=0.1)
risk_amount = total_capital * (risk_pct / 100.0)

st.sidebar.markdown("---")
st.sidebar.header("⭐ Asset Watchlist")
watchlist_items = finance_tools.get_watchlist()

if watchlist_items:
    for ticker, exchange in watchlist_items:
        cols = st.sidebar.columns([3, 1])
        cols[0].write(f"**{ticker}** ({exchange})")
        if cols[1].button("❌", key=f"del_{ticker}_{exchange}"):
            finance_tools.remove_from_watchlist(ticker, exchange)
            st.rerun()
else:
    st.sidebar.info("Watchlist is empty. Search an asset to track it.")

# --- MAIN CONTROLLER: DATA INTEGRATION PIPELINES ---
c1, c2 = st.columns([3, 1])
target_input = c1.text_input("Enter Asset Ticker (e.g., RELIANCE.NS, TCS.NS, AAPL, NVDA)", value="RELIANCE.NS").upper().strip()
exchange_select = c2.selectbox("Market Exchange", ["NSE", "BSE", "NASDAQ", "NYSE"])

if st.button("🔍 Run Terminal Analytics Engine", use_container_width=True):
    st.session_state['active_ticker'] = target_input
    st.session_state['active_exchange'] = exchange_select

# Execute core rendering if active ticker configuration exists
if 'active_ticker' in st.session_state:
    ticker = st.session_state['active_ticker']
    exchange = st.session_state['active_exchange']
    
    with st.spinner(f"Routing real-time data metrics for {ticker}..."):
        current_price = finance_tools.get_current_price(ticker)
        tech_indicators = finance_tools.get_technical_indicators(ticker)
        key_ratios = finance_tools.get_key_ratios(ticker)
        financial_health = finance_tools.get_financial_health(ticker)
        graham_value = finance_tools.calculate_graham_value(ticker)
        shareholding = finance_tools.get_shareholding_pattern(ticker)
        news_headlines = finance_tools.get_recent_news_headlines(ticker)
        
    if not current_price or not tech_indicators:
        st.error(f"Network Pipeline Error: Unable to extract data for {ticker}. Verify ticker identifier or market routing channels.")
    else:
        # Action Buttons Layer
        col_actions = st.columns(2)
        if col_actions[0].button("➕ Add Asset to Core Watchlist Tracker", use_container_width=True):
            finance_tools.add_to_watchlist(ticker, exchange)
            st.toast(f"Successfully pinned {ticker} to Watchlist!")
            st.rerun()
            
        # Display accurate Data Quality Indicator
        available_metrics = sum(x is not None for x in [graham_value, key_ratios.get("P/E Ratio"), key_ratios.get("Price to Book")])
        quality_score = round((available_metrics / 3) * 100)
        
        # --- CRITICAL SAFETY TRIGGER: RISK ALERT ENGINE ---
        support_floor = tech_indicators.get("Support", 0.0)
        if current_price < support_floor:
            st.markdown(f"""
                <div style='background-color:#4d0000; padding:15px; border-radius:8px; border-left:6px solid #ff3333; margin-bottom:15px;'>
                    <h3 style='margin:0; color:#ffcccc;'>⚠️ CRITICAL STRUCTURAL RISK ALERT</h3>
                    <p style='margin:5px 0 0 0; color:#ffffff;'>Asset has broken below its technical support floor baseline of <b>{support_floor:,.2f}</b>. Risk exposure mitigation frameworks should be activated immediately.</p>
                </div>
            """, unsafe_allow_html=True) # FIX: Changed from unsafe_allowed_html to unsafe_allow_html

        # Core Metrics Display Layout
        st.subheader("📊 Institutional Core Data Grid")
        st.caption(f"Data Source Pipeline Integrity Quality Score: {quality_score}%")
        
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        m_col1.metric("Live Market Price", f"{current_price:,.2f}")
        m_col2.metric("Relative Strength Index (RSI 14)", f"{tech_indicators['RSI']:.2f}" if tech_indicators['RSI'] else "N/A")
        m_col3.metric("EMA 20 Vector Floor", f"{tech_indicators['EMA_20']:,.2f}" if tech_indicators['EMA_20'] else "N/A")
        m_col4.metric("EMA 50 Vector Floor", f"{tech_indicators['EMA_50']:,.2f}" if tech_indicators['EMA_50'] else "N/A")
        
        m_col5, m_col6, m_col7, m_col8 = st.columns(4)
        m_col5.metric("50 Day Moving Average", f"{tech_indicators['50 DMA']:,.2f}" if tech_indicators['50 DMA'] else "N/A")
        m_col6.metric("200 Day Moving Average", f"{tech_indicators['200 DMA']:,.2f}" if tech_indicators['200 DMA'] else "N/A")
        m_col7.metric("Support Floor Baseline", f"{support_floor:,.2f}" if support_floor else "N/A")
        m_col8.metric("Resistance Ceiling Wall", f"{tech_indicators['Resistance']:,.2f}" if tech_indicators['Resistance'] else "N/A")

        st.markdown("---")
        
        # Fundamental Financial Parameters Column Layers
        f_col1, f_col2 = st.columns(2)
        with f_col1:
            st.markdown("### 📈 Core Financial Valuation Ratios")
            st.write(f"**Trailing P/E Ratio:** {key_ratios['P/E Ratio'] if key_ratios['P/E Ratio'] else 'N/A'}")
            st.write(f"**Forward P/E Prediction:** {key_ratios['Forward P/E'] if key_ratios['Forward P/E'] else 'N/A'}")
            st.write(f"**Price to Book Value (P/B):** {key_ratios['Price to Book'] if key_ratios['Price to Book'] else 'N/A'}")
            
        with f_col2:
            st.markdown("### 🏥 Corporate Financial Health & Scales")
            st.write(f"**Return on Equity (ROE):** {financial_health['ROE'] if financial_health['ROE'] else 'N/A'}")
            st.write(f"**Debt to Equity Leverage Ratio:** {financial_health['Debt to Equity'] if financial_health['Debt to Equity'] else 'N/A'}")
            st.write(f"**Calculated Annual Free Cash Flow:** {financial_health['Free Cash Flow'] if financial_health['Free Cash Flow'] else 'N/A'}")

        st.markdown("---")

        # --- POSITION CALCULATOR & VALUATION PARSER CONTROLLERS ---
        v_left, v_right = st.columns(2)
        
        with v_left:
            st.markdown("### 🎯 Quantitative Capital Position Allocations")
            per_share_risk = current_price - support_floor
            
            if per_share_risk > 0:
                risk_based_shares = int(risk_amount / per_share_risk)
                capital_based_shares = int(total_capital / current_price)
                max_shares_to_buy = min(risk_based_shares, capital_based_shares)
            else:
                max_shares_to_buy = int(total_capital / current_price)
                
            total_trade_value = max_shares_to_buy * current_price
            
            st.info(f"**Max Capital Risk Budget Allocated:** {exchange_select} {risk_amount:,.2f}")
            st.write(f"**Calculated Position Purchasing Cap:** {max_shares_to_buy:,} Shares")
            st.write(f"**Net Position Capital Allocation Cost:** {total_trade_value:,.2f}")

        with v_right:
            st.markdown("### 💎 Asset Intrinsic Valuation Matrix")
            cols_val = st.columns(2)
            
            if graham_value:
                margin_of_safety = ((graham_value - current_price) / graham_value) * 100
                cols_val[0].metric("Benjamin Graham Value", f"{graham_value:,.2f}")
                if margin_of_safety > 0:
                    cols_val[0].success(f"Undervalued: {margin_of_safety:.1f}% MOS")
                else:
                    cols_val[0].error(f"Overvalued: {abs(margin_of_safety):.1f}% Premium")
            else:
                cols_val[0].info("Graham Value: N/A")
                
            cols_val[1].warning("DCF disabled. Public market data layers are insufficient for reliable retail projections.")

        st.markdown("---")

        # --- VISUAL GRAPHING VECTOR INTERFACES ---
        g1, g2 = st.columns([2, 1])
        
        with g1:
            st.markdown("### 📊 6-Month Historical Close Vector Candlestick")
            hist_df = yf.download(ticker, period="6m", progress=False)
            if not hist_df.empty:
                if isinstance(hist_df.columns, pd.MultiIndex):
                    hist_df.columns = hist_df.columns.get_level_values(0)
                fig = go.Figure(data=[go.Candlestick(
                    x=hist_df.index, open=hist_df['Open'], high=hist_df['High'],
                    low=hist_df['Low'], close=hist_df['Close'], name=ticker
                )])
                fig.update_layout(template="plotly_dark", margin=dict(l=20, r=20, t=20, b=20), height=380)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Unable to compile interactive structural tracking graphics vectors.")

        with g2:
            st.markdown("### 🥧 Corporate Equity Allocation Pattern")
            
            insiders = shareholding.get("insiders")
            institutions = shareholding.get("institutions")
            
            insiders_pct = insiders * 100 if insiders is not None else 0.0
            inst_pct = institutions * 100 if institutions is not None else 0.0
            public_pct = max(0.0, 100.0 - (insiders_pct + inst_pct))
            
            labels = ['Promoter / Insider', 'Institutional', 'Public & Retail']
            values = [insiders_pct, inst_pct, public_pct]
            
            if sum(values) > 0:
                fig_pie = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.4)])
                fig_pie.update_layout(template="plotly_dark", margin=dict(l=10, r=10, t=10, b=10), height=380, showlegend=True)
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("Shareholding structural matrix records restricted by reporting channels.")

        st.markdown("---")

        # --- SPECIALIZED AI EQUITY RESEARCH INTELLIGENCE ENGINE ---
        st.subheader("🤖 Generative AI Research Analyst Engine")
        user_query = st.text_input("Issue Query or Analysis Commands to the Financial Analyst:", 
                                  value=f"Provide a comprehensive equity research brief and target risk assessment profile for {ticker} based on the real-time data grid.")

        if st.button("🧠 Execute High-Conviction AI Inference Run"):
            with st.spinner("Processing deep quantitative neural vector loops..."):
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
                st.markdown("### 📋 Institutional Equity Research Brief")
                st.markdown(ai_report)
