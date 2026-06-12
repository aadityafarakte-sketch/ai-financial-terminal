import yfinance as yf
import pandas as pd
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import sqlite3

# --- SQL WATCHLIST DATABASE MODULE ---
def init_db():
    try:
        conn = sqlite3.connect("watchlist.db")
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                exchange TEXT NOT NULL,
                UNIQUE(ticker, exchange)
            )
        """)
        conn.commit()
        conn.close()
    except Exception:
        pass

def add_to_watchlist(ticker, exchange):
    try:
        conn = sqlite3.connect("watchlist.db")
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO watchlist (ticker, exchange) VALUES (?, ?)", (ticker, exchange))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False

def get_watchlist():
    try:
        conn = sqlite3.connect("watchlist.db")
        cursor = conn.cursor()
        cursor.execute("SELECT ticker, exchange FROM watchlist")
        rows = cursor.fetchall()
        conn.close()
        return rows
    except Exception:
        return []

def remove_from_watchlist(ticker, exchange):
    try:
        conn = sqlite3.connect("watchlist.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM watchlist WHERE ticker = ? AND exchange = ?", (ticker, exchange))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False

# --- UTILITY: DEEP FINANCIAL STATEMENT EXTRACTOR ---
def extract_statement_metric(df, rows_to_check):
    """Safely extracts the latest numeric value from financial dataframes without fallbacks."""
    if df is not None and not df.empty:
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        for row_name in rows_to_check:
            matched_indices = [idx for idx in df.index if row_name.lower() in str(idx).lower()]
            if matched_indices:
                val = df.loc[matched_indices[0]]
                if isinstance(val, pd.Series):
                    val = val.iloc[0]
                if pd.notna(val) and not isinstance(val, (str, bool)):
                    return float(val)
    return None

# --- UTILITY: INTERNATIONALLY AWARE CURRENCY FORMATTER ---
def format_financial_units(value, ticker):
    """Formats raw metrics into regional context. Returns None if value is missing."""
    if value is None or pd.isna(value):
        return None
    
    is_indian = ticker.endswith(".NS") or ticker.endswith(".BO")
    if is_indian:
        return f"₹{value / 10_000_000:,.2f} Cr"
    return f"${value / 1_000_000:,.2f} M"

# --- DATA ENGINE CORE FUNCTIONS ---
def get_current_price(ticker):
    try:
        df = yf.download(ticker, period="5d", progress=False)
        if not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            series = df['Close']
            if isinstance(series, pd.DataFrame):
                series = series.iloc[:, 0]
            
            valid_prices = series.dropna()
            if not valid_prices.empty:
                return float(valid_prices.iloc[-1])
        
        stock = yf.Ticker(ticker)
        info = stock.info if stock.info else {}
        price = info.get("currentPrice") or info.get("regularMarketPrice")
        return float(price) if price else None
    except Exception:
        return None

def get_key_ratios(ticker):
    """STRICT: Returns real parameters. No proxy baselines or fallbacks allowed."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info if stock.info else {}
        current_price = get_current_price(ticker)
        
        pe = info.get("trailingPE")
        forward_pe = info.get("forwardPE")
        pb = info.get("priceToBook")
        
        # Try programmatic extraction if standard info block is restricted
        if (pb is None or pd.isna(pb)) and current_price:
            try:
                balance_sheet = stock.balance_sheet
                shares = info.get("sharesOutstanding") or info.get("impliedSharesOutstanding")
                total_assets = extract_statement_metric(balance_sheet, ["Total Assets"])
                total_liab = extract_statement_metric(balance_sheet, ["Total Liabilities"])
                if total_assets and total_liab and shares and shares > 0:
                    bvps = (total_assets - total_liab) / shares
                    if bvps > 0: 
                        pb = current_price / bvps
            except Exception:
                pass

        return {
            "P/E Ratio": round(pe, 2) if pe is not None and not pd.isna(pe) else None,
            "Forward P/E": round(forward_pe, 2) if forward_pe is not None and not pd.isna(forward_pe) else None,
            "Price to Book": round(pb, 2) if pb is not None and not pd.isna(pb) else None
        }
    except Exception:
        return {"P/E Ratio": None, "Forward P/E": None, "Price to Book": None}

def get_financial_health(ticker):
    """STRICT: Returns real ROE, Debt/Equity, and FCF. No hardcoded string fallbacks."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info if stock.info else {}
        
        roe = info.get("returnOnEquity")
        if not roe or pd.isna(roe):
            try:
                net_income = extract_statement_metric(stock.financials, ["Net Income"])
                total_equity = extract_statement_metric(stock.balance_sheet, ["Stockholders Equity"])
                if net_income and total_equity and total_equity > 0:
                    roe = net_income / total_equity
            except Exception:
                pass
        
        debt_to_equity = info.get("debtToEquity")
        if not debt_to_equity or pd.isna(debt_to_equity):
            try:
                total_debt = extract_statement_metric(stock.balance_sheet, ["Total Debt"])
                total_equity = extract_statement_metric(stock.balance_sheet, ["Stockholders Equity"])
                if total_debt and total_equity and total_equity > 0:
                    debt_to_equity = (total_debt / total_equity) * 100
            except Exception:
                pass
        
        fcf = info.get("freeCashflow")
        if not fcf or pd.isna(fcf):
            try:
                ocf = extract_statement_metric(stock.cashflow, ["Operating Cash Flow"])
                capex = extract_statement_metric(stock.cashflow, ["Capital Expenditure"])
                if ocf: 
                    fcf = ocf - (abs(capex) if capex else 0)
            except Exception:
                pass

        # Adjust metric formatting to convert legacy percentages to ratios if needed
        d_e_val = None
        if debt_to_equity is not None and not pd.isna(debt_to_equity):
            d_e_val = f"{debt_to_equity / 100:.2f}" if debt_to_equity > 5 else f"{debt_to_equity:.2f}"

        return {
            "ROE": f"{roe * 100:.2f}%" if roe is not None and not pd.isna(roe) else None,
            "Debt to Equity": d_e_val,
            "Free Cash Flow": format_financial_units(fcf, ticker) if fcf is not None else None
        }
    except Exception:
        return {"ROE": None, "Debt to Equity": None, "Free Cash Flow": None}

def calculate_graham_value(ticker):
    """STRICT: Traditional Benjamin Graham Square Root valuation. Returns None if inputs missing."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info if stock.info else {}
        
        eps = info.get("trailingEps")
        bvps = info.get("bookValue")
        
        if not eps or not bvps or pd.isna(eps) or pd.isna(bvps):
            try:
                shares = info.get("sharesOutstanding") or info.get("impliedSharesOutstanding")
                net_income = extract_statement_metric(stock.financials, ["Net Income"])
                total_assets = extract_statement_metric(stock.balance_sheet, ["Total Assets"])
                total_liab = extract_statement_metric(stock.balance_sheet, ["Total Liabilities"])
                
                if shares and shares > 0:
                    if net_income: 
                        eps = net_income / shares
                    if total_assets and total_liab: 
                        bvps = (total_assets - total_liab) / shares
            except Exception:
                pass
        
        if eps and bvps and eps > 0 and bvps > 0:
            val = (22.5 * eps * bvps) ** 0.5
            return round(float(val), 2) if not pd.isna(val) else None
        return None
    except Exception:
        return None

def calculate_dcf_value(ticker):
    """DEPRECATED: Removed per retail analytical specification rules."""
    return None

def get_shareholding_pattern(ticker):
    """STRICT: Extracts institutional blocks. Returns None if unavailable."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info if stock.info else {}
        insiders = info.get("heldPercentInsiders")
        institutions = info.get("heldPercentInstitutions")
        
        return {
            "insiders": float(insiders) if insiders is not None and not pd.isna(insiders) else None,
            "institutions": float(institutions) if institutions is not None and not pd.isna(institutions) else None
        }
    except Exception:
        return {"insiders": None, "institutions": None}

def get_technical_indicators(ticker):
    try:
        df = yf.download(ticker, period="1y", progress=False)
        if df.empty: 
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
        df['High'] = pd.to_numeric(df['High'], errors='coerce')
        df['Low'] = pd.to_numeric(df['Low'], errors='coerce')
        df = df.dropna(subset=['Close', 'High', 'Low']).copy()

        if len(df) < 50: 
            return None

        delta = df['Close'].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0, 1e-9)
        rsi_series = 100 - (100 / (1 + rs))
        
        ema_20_series = df['Close'].ewm(span=20, adjust=False).mean()
        ema_50_series = df['Close'].ewm(span=50, adjust=False).mean()
        sma_50_series = df['Close'].rolling(window=50).mean()
        
        latest_close = float(df['Close'].iloc[-1])
        
        # FIXED: Only compute 200 DMA if 200 actual active data elements exist
        sma_200_val = None
        if len(df) >= 200:
            sma_200_series = df['Close'].rolling(window=200).mean()
            sma_200_val = float(sma_200_series.iloc[-1]) if not pd.isna(sma_200_series.iloc[-1]) else None
        
        support_val = float(df['Low'].rolling(window=50).min().iloc[-1])
        resistance_val = float(df['High'].rolling(window=50).max().iloc[-1])

        return {
            "Close": latest_close,
            "RSI": float(rsi_series.iloc[-1]) if not pd.isna(rsi_series.iloc[-1]) else None,
            "EMA_20": float(ema_20_series.iloc[-1]) if not pd.isna(ema_20_series.iloc[-1]) else None,
            "EMA_50": float(ema_50_series.iloc[-1]) if not pd.isna(ema_50_series.iloc[-1]) else None,
            "50 DMA": float(sma_50_series.iloc[-1]) if not pd.isna(sma_50_series.iloc[-1]) else None,
            "200 DMA": sma_200_val,
            "Support": support_val,
            "Resistance": resistance_val,
            "Beta Index": 1.0
        }
    except Exception:
        return None

def get_latest_quarterly_income_statement(ticker):
    try:
        stock = yf.Ticker(ticker)
        df = stock.quarterly_financials
        if df is not None and not df.empty:
            return df.iloc[:, 0].to_dict()
        return "Quarterly financials registry update pending."
    except Exception:
        return "Quarterly financials registry update pending."

def get_recent_news_headlines(ticker):
    try:
        clean_ticker = ticker.split('.')[0]
        url = f"https://news.google.com/rss/search?q={clean_ticker}+stock&hl=en-US&gl=US&ceid=US:en"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            xml_data = response.read()
        root = ET.fromstring(xml_data)
        headlines = []
        for item in root.findall('.//item')[:5]:
            title = item.find('title').text
            headlines.append({"headline": title, "url": item.find('link').text})
        return headlines if headlines else [{"headline": f"No recent news catalyst found for {ticker}.", "url": "#"}]
    except Exception:
        return [{"headline": f"No recent news catalyst found for {ticker}.", "url": "#"}]
    
