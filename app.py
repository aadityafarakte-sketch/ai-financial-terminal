import streamlit as st
import finance_tools
import ai_engine
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd

def main():
    st.set_page_config(page_title="AI Financial Advisor", layout="wide")
    st.title("📈 AI Financial Advisor")
    st.write("Get real-time financial data and AI-driven insights for your favorite stocks.")

    # Boot up the SQL structural framework database
    finance_tools.init_db()

    # Sidebar layout configuration panel
    st.sidebar.header("Configuration")

    exchange = st.sidebar.selectbox(
        "Exchange Market",
        options=["NSE (India)", "BSE (India)", "US Market"],
        index=2
    )
    
    if exchange == "BSE (India)":
        st.sidebar.info("Please enter the BSE 6-digit code or script symbol. We will automatically append '.BO'.")

    ticker_input = st.sidebar.text_input("Enter Stock Ticker (e.g., AAPL, MSFT):", value="AAPL")

    st.sidebar.subheader("📐 Position Sizing Calculator")
    total_capital = st.sidebar.number_input("Total Investment Capital", value=100000)
    max_risk_pct = st.sidebar.slider("Max Risk Per Trade (%)", min_value=0.5, max_value=5.0, value=1.0, step=0.5)

    if ticker_input:
        clean_ticker = ticker_input.strip().upper()
        if clean_ticker.endswith(".NS") or clean_ticker.endswith(".BO"):
            clean_ticker = clean_ticker[:-3]
            
        ticker = clean_ticker
        if exchange == "NSE (India)":
            ticker = f"{clean_ticker}.NS"
        elif exchange == "BSE (India)":
            ticker = f"{clean_ticker}.BO"
            
        # --- PERMANENT SQL WATCHLIST MANAGEMENT MODULE ---
        st.sidebar.subheader("⭐ Watchlist Manager")
        saved_list = finance_tools.get_watchlist()
        is_saved = any(item[0] == ticker and item[1] == exchange for item in saved_list)

        if is_saved:
            if st.sidebar.button("❌ Remove from Watchlist", use_container_width=True):
                finance_tools.remove_from_watchlist(ticker, exchange)
                st.sidebar.success(f"{ticker} deleted out of tracking cache.")
                st.rerun()
        else:
            if st.sidebar.button("⭐ Save to Watchlist", use_container_width=True):
                finance_tools.add_to_watchlist(ticker, exchange)
                st.sidebar.success(f"{ticker} permanently pinned to portfolio storage.")
                st.rerun()

        # Render Active Watchlist Summary Table 
        if saved_list:
            st.sidebar.write("**Your Tracked Securities:**")
            df_watchlist = pd.DataFrame(saved_list, columns=["Ticker Symbol", "Market Exchange"])
            st.sidebar.dataframe(df_watchlist, hide_index=True, use_container_width=True)

        # Main Data Processing Operations Engine
        st.header(f"Market Data for {ticker}")
        with st.spinner(f"Fetching data for {ticker}..."):
            current_price = finance_tools.get_current_price(ticker)
            key_ratios = finance_tools.get_key_ratios(ticker)
            tech_indicators = finance_tools.get_technical_indicators(ticker)
            graham_value = finance_tools.calculate_graham_value(ticker)
            fin_health = finance_tools.get_financial_health(ticker)
            dcf_value = finance_tools.calculate_dcf_value(ticker)
            shareholding = finance_tools.get_shareholding_pattern(ticker)

        currency_symbol = "₹" if exchange in ["NSE (India)", "BSE (India)"] else "$"

        if current_price is not None:
            st.subheader(f"Current Price: {currency_symbol}{current_price:,.2f}")
        else:
            st.warning("Could not fetch the current price. The ticker might be invalid.")
# --- PHASE 5: OPTION 3 AUTOMATED RISK TRIGGER ALERTS ---
        if tech_indicators and current_price is not None:
            sup_floor = tech_indicators.get("Support")
            if sup_floor is not None:
                # If current market price crashes down to or below our technical floor
                if current_price <= sup_floor:
                    st.error(
                        f"## 🚨 SYSTEM EMERGENCY: RISK BREACH DETECTED\n"
                        f"**{ticker}** has violated its 50-day support baseline floor of **{currency_symbol}{sup_floor:,.2f}**! "
                        f"The structural market protection boundary has collapsed. High-probability liquidation risk is active. "
                        f"Review your stop-loss execution boundaries immediately."
                    )
        if key_ratios:
            st.subheader("Key Financial Ratios")
            cols = st.columns(len(key_ratios))
            for col, (ratio_name, ratio_value) in zip(cols, key_ratios.items()):
                if ratio_value is not None and isinstance(ratio_value, (int, float)):
                    display_value = f"{ratio_value:,.2f}"
                else:
                    display_value = "N/A"
                col.metric(label=ratio_name, value=display_value)

        if fin_health:
            st.subheader("Financial Health")
            cols_health = st.columns(3)
            cols_health[0].metric(label="ROE", value=fin_health.get("ROE", "N/A"))
            cols_health[1].metric(label="Debt to Equity", value=fin_health.get("Debt to Equity", "N/A"))
            cols_health[2].metric(label="Free Cash Flow", value=fin_health.get("Free Cash Flow", "N/A"))

        # Visual Grid Layout for Institutional Holdings
        st.subheader("🏛️ Institutional Shareholding Pattern")
        if shareholding:
            insiders_pct = shareholding.get("insiders", 0.0) * 100
            inst_pct = shareholding.get("institutions", 0.0) * 100
            public_pct = max(0.0, 100.0 - (insiders_pct + inst_pct))
            
            col_table, col_chart = st.columns([1, 1])
            with col_table:
                sh_data = {
                    "Ownership Class": ["Insider Holdings", "Institutional Holdings", "Public & Retail"],
                    "Allocation": [f"{insiders_pct:.2f}%", f"{inst_pct:.2f}%", f"{public_pct:.2f}%"]
                }
                st.dataframe(pd.DataFrame(sh_data), hide_index=True, use_container_width=True)
                
            with col_chart:
                labels = ['Insiders', 'Institutions', 'Public & Retail']
                values = [insiders_pct, inst_pct, public_pct]
                colors = ['#FF4B4B', '#1C83E1', '#00C0F2']
                
                fig_pie = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.5, marker=dict(colors=colors), textinfo='percent+label', showlegend=False)])
                fig_pie.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=200, template="plotly_dark")
                st.plotly_chart(fig_pie, width="stretch")
        else:
            st.info("Detailed shareholding breakdown registry is currently updating...")

        if tech_indicators:
            st.subheader("Technical Indicators (Latest)")
            cols_row1 = st.columns(4)
            close_val = tech_indicators.get("Close")
            cols_row1[0].metric(label="Close Price", value=f"{currency_symbol}{close_val:,.2f}" if close_val else "N/A")
            rsi_val = tech_indicators.get("RSI")
            cols_row1[1].metric(label="RSI (14)", value=f"{rsi_val:,.2f}" if rsi_val else "N/A")
            ema20 = tech_indicators.get("EMA_20")
            cols_row1[2].metric(label="EMA (20)", value=f"{currency_symbol}{ema20:,.2f}" if ema20 else "N/A")
            ema50 = tech_indicators.get("EMA_50")
            cols_row1[3].metric(label="EMA (50)", value=f"{currency_symbol}{ema50:,.2f}" if ema50 else "N/A")
            
            cols_row2 = st.columns(4)
            sma50 = tech_indicators.get("50 DMA")
            cols_row2[0].metric(label="50 DMA", value=f"{currency_symbol}{sma50:,.2f}" if sma50 else "N/A")
            sma200 = tech_indicators.get("200 DMA")
            cols_row2[1].metric(label="200 DMA", value=f"{currency_symbol}{sma200:,.2f}" if sma200 else "N/A")
            sup_floor = tech_indicators.get("Support")
            cols_row2[2].metric(label="Support (50d)", value=f"{currency_symbol}{sup_floor:,.2f}" if sup_floor else "N/A")
            res_ceil = tech_indicators.get("Resistance")
            cols_row2[3].metric(label="Resistance (50d)", value=f"{currency_symbol}{res_ceil:,.2f}" if res_ceil else "N/A")
            
            if current_price is not None and sup_floor is not None:
                target_stop_loss = sup_floor
                risk_amount = total_capital * (max_risk_pct / 100)
                per_share_risk = current_price - target_stop_loss
                if per_share_risk > 0:
                    max_shares_to_buy = int(risk_amount / per_share_risk)
                    total_trade_value = max_shares_to_buy * current_price
                    st.sidebar.info(
                        f"**Trade Allocation**\n\n"
                        f"• **Shares Allowed:** {max_shares_to_buy:,}\n"
                        f"• **Total Trade Value:** {currency_symbol}{total_trade_value:,.2f}\n"
                        f"• **Stop-Loss Floor:** {currency_symbol}{target_stop_loss:,.2f}"
                    )
                else:
                    st.sidebar.warning("Warning: Safe Stop-Loss structure unaligned with entries.")

        st.subheader("Intrinsic Valuation & Margin of Safety")
        cols_val = st.columns(2)
        
        def calculate_mos(intrinsic_val, price):
            if intrinsic_val is None or intrinsic_val == "N/A": return None
            try:
                if float(intrinsic_val) <= 0: return None
                if price is not None and float(price) > 0:
                    return ((float(intrinsic_val) - float(price)) / float(intrinsic_val)) * 100
            except (ValueError, TypeError): pass
            return None
            
        if graham_value is not None and graham_value != "N/A":
            graham_mos = calculate_mos(graham_value, current_price)
            mos_label = f"{graham_mos:,.2f}% MoS" if graham_mos is not None else None
            cols_val[0].metric(label="Benjamin Graham Value", value=f"{currency_symbol}{graham_value:,.2f}", delta=mos_label)
        else:
            cols_val[0].info("Graham Value N/A")
            
        if dcf_value is not None and dcf_value != "N/A":
            dcf_mos = calculate_mos(dcf_value, current_price)
            mos_label = f"{dcf_mos:,.2f}% MoS" if dcf_mos is not None else None
            cols_val[1].metric(label="DCF Fair Value", value=f"{currency_symbol}{dcf_value:,.2f}", delta=mos_label)
        else:
            cols_val[1].info("DCF Value N/A")

        st.divider()
        st.subheader("6-Month Price History")
        history_df = yf.download(ticker, period="6mo", progress=False)
        if not history_df.empty:
            fig = go.Figure(data=[go.Candlestick(x=history_df.index, open=history_df['Open'].squeeze(), high=history_df['High'].squeeze(), low=history_df['Low'].squeeze(), close=history_df['Close'].squeeze(), name="Price")])
            fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig, width="stretch")

        st.divider()
        st.subheader("Ask the AI Advisor")
        user_query = st.text_input(f"What would you like to know about {ticker}'s financials?")
        
        if st.button("Generate Analysis"):
            if user_query:
                with st.spinner("Analyzing data matrices and mapping vectors..."):
                    financial_context = {
                        "Current Price": current_price, "Key Ratios": key_ratios, "Financial Health": fin_health,
                        "Shareholding Pattern": shareholding, "Technical Indicators": tech_indicators,
                        "Graham Value": graham_value, "DCF Value": dcf_value,
                        "Latest Income Statement": finance_tools.get_latest_quarterly_income_statement(ticker),
                        "Recent News": finance_tools.get_recent_news_headlines(ticker)
                    }
                    try:
                        analysis = ai_engine.generate_financial_analysis(ticker, user_query, financial_context)
                        st.markdown(analysis)
                    except Exception as e:
                        st.error(f"Analysis engine exception: {e}")

if __name__ == "__main__":
    main()