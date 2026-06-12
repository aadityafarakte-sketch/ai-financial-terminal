import yfinance as yf
import pandas_ta as ta
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

def get_current_price(ticker):
    try:
        stock = yf.Ticker(ticker)
        price = stock.info.get("currentPrice")
        if price is not None:
            return float(price)
        # Fallback to historical data if currentPrice is missing
        df = stock.history(period="1d")
        if not df.empty:
            return float(df['Close'].iloc[-1])
        return None
    except Exception:
        return None

def get_key_ratios(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        beta = info.get("beta")
        
        # Calculate domestic Beta for Indian stocks against Nifty 50
        if ticker.endswith(".NS") or ticker.endswith(".BO"):
            try:
                stock_df = yf.download(ticker, period="1y", progress=False)
                nifty_df = yf.download("^NSEI", period="1y", progress=False)
                
                if not stock_df.empty and not nifty_df.empty:
                    stock_returns = stock_df['Close'].squeeze().pct_change().dropna()
                    nifty_returns = nifty_df['Close'].squeeze().pct_change().dropna()
                    
                    aligned_stock, aligned_nifty = stock_returns.align(nifty_returns, join='inner')
                    
                    if len(aligned_nifty) > 1:
                        variance = aligned_nifty.var()
                        if variance != 0:
                            covariance = aligned_stock.cov(aligned_nifty)
                            beta = round(covariance / variance, 2)
            except Exception:
                pass  # Fall back to yfinance beta

        return {
            "P/E Ratio": info.get("trailingPE"),
            "EPS": info.get("trailingEps"),
            "Forward P/E": info.get("forwardPE"),
            "Beta": beta
        }
    except Exception:
        return {"P/E Ratio": None, "EPS": None, "Forward P/E": None, "Beta": None}

def get_technical_indicators(ticker):
    try:
        import pandas as pd
        # Fetch 1 year of daily historical data
        df = yf.download(ticker, period="1y", progress=False)
        if df.empty:
            return None
        
        # Fix Yahoo Finance's multi-level tracking header bug
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        # Clean data structures explicitly to prevent calculation crashes
        df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
        df['High'] = pd.to_numeric(df['High'], errors='coerce')
        df['Low'] = pd.to_numeric(df['Low'], errors='coerce')
        df = df.dropna(subset=['Close', 'High', 'Low']).copy()  # Added .copy() to prevent warnings
        df = df.dropna(subset=['Close', 'High', 'Low']).copy()

        if len(df) < 200:
            return None

        # Calculate pure pandas-ta math sequences cleanly
        rsi_series = df.ta.rsi(length=14)
        ema_20_series = df.ta.ema(length=20)
        ema_50_series = df.ta.ema(length=50)
        sma_50_series = df.ta.sma(length=50)
        sma_200_series = df.ta.sma(length=200)
        # --- NATIVE PANDAS CORE INDICATOR MATH (Replaces pandas-ta package) ---
        # 1. RSI (14) using Wilder's Smoothing Exponential Moving Average
        delta = df['Close'].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0, 1e-9)  # Protect against division by zero
        rsi_series = 100 - (100 / (1 + rs))
        
        # 2. Moving Averages
        ema_20_series = df['Close'].ewm(span=20, adjust=False).mean()
        ema_50_series = df['Close'].ewm(span=50, adjust=False).mean()
        sma_50_series = df['Close'].rolling(window=50).mean()
        sma_200_series = df['Close'].rolling(window=200).mean()
        
        # Calculate trailing 50-day support/resistance floors and ceilings
        support_val = df['Low'].rolling(window=50).min().iloc[-1]
        resistance_val = df['High'].rolling(window=50).max().iloc[-1]
        
        # Pull the exact latest execution data arrays
        latest_close = df['Close'].iloc[-1]
        latest_rsi = rsi_series.iloc[-1] if rsi_series is not None else None
        latest_ema20 = ema_20_series.iloc[-1] if ema_20_series is not None else None
        latest_ema50 = ema_50_series.iloc[-1] if ema_50_series is not None else None
        latest_sma50 = sma_50_series.iloc[-1] if sma_50_series is not None else None
        latest_sma200 = sma_200_series.iloc[-1] if sma_200_series is not None else None
        latest_rsi = rsi_series.iloc[-1]
        latest_ema20 = ema_20_series.iloc[-1]
        latest_ema50 = ema_50_series.iloc[-1]
        latest_sma50 = sma_50_series.iloc[-1]
        latest_sma200 = sma_200_series.iloc[-1]

        # Custom Regional Benchmark Beta Calculator (Nifty 50 vs US Indices)
        beta_val = 1.0
        if ticker.endswith(".NS") or ticker.endswith(".BO"):
            try:
                nifty_df = yf.download("^NSEI", period="1y", progress=False)
                if isinstance(nifty_df.columns, pd.MultiIndex):
                    nifty_df.columns = nifty_df.columns.get_level_values(0)
                df['Returns'] = df['Close'].pct_change()
                nifty_df['Returns'] = nifty_df['Close'].pct_change()
                combined = pd.DataFrame({'Stock': df['Returns'], 'Nifty': nifty_df['Returns']}).dropna()
                covariance = combined['Stock'].cov(combined['Nifty'])
                variance = combined['Nifty'].var()
                if variance > 0:
                    beta_val = covariance / variance
            except Exception:
                pass
        else:
            try:
                stock_obj = yf.Ticker(ticker)
                beta_val = stock_obj.info.get("beta", 1.0)
            except Exception:
                beta_val = 1.0

        return {
            "Close": float(latest_close),
            "RSI": float(latest_rsi) if latest_rsi is not None else None,
            "EMA_20": float(latest_ema20) if latest_ema20 is not None else None,
            "EMA_50": float(latest_ema50) if latest_ema50 is not None else None,
            "50 DMA": float(latest_sma50) if latest_sma50 is not None else None,
            "200 DMA": float(latest_sma200) if latest_sma200 is not None else None,
            "Support": float(support_val) if support_val is not None else None,
            "Resistance": float(resistance_val) if resistance_val is not None else None,
            "RSI": float(latest_rsi) if not pd.isna(latest_rsi) else None,
            "EMA_20": float(latest_ema20) if not pd.isna(latest_ema20) else None,
            "EMA_50": float(latest_ema50) if not pd.isna(latest_ema50) else None,
            "50 DMA": float(latest_sma50) if not pd.isna(latest_sma50) else None,
            "200 DMA": float(latest_sma200) if not pd.isna(latest_sma200) else None,
            "Support": float(support_val) if not pd.isna(support_val) else None,
            "Resistance": float(resistance_val) if not pd.isna(resistance_val) else None,
            "Beta Index": float(beta_val)
        }
    except Exception:
        return None

def calculate_graham_value(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        eps = info.get("trailingEps", 0)
        book_value = info.get("bookValue", 0)
        if eps and book_value and eps > 0 and book_value > 0:
            return round((22.5 * eps * book_value) ** 0.5, 2)
        return None
    except Exception:
        return None

def get_financial_health(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        roe = info.get("returnOnEquity")
        roe_formatted = f"{round(roe * 100, 2)}%" if roe is not None else "N/A"
        
        debt_to_equity = info.get("debtToEquity")
        debt_formatted = round(debt_to_equity / 100, 2) if debt_to_equity is not None else "N/A"
        
        fcf = info.get("freeCashFlow")
        
        # If the fast-lookup is blank, read from the cash flow statement
        if fcf is None or fcf == "N/A":
            try:
                cashflow = stock.cashflow
                if not cashflow.empty:
                    opf = cashflow.loc['Operating Cash Flow'].iloc[0] if 'Operating Cash Flow' in cashflow.index else 0
                    capex = cashflow.loc['Capital Expenditure'].iloc[0] if 'Capital Expenditure' in cashflow.index else 0
                    calculated_fcf = opf + capex if capex < 0 else opf - capex
                    if calculated_fcf != 0:
                        fcf = calculated_fcf
            except Exception:
                pass

        fcf_formatted = f"₹{int(fcf):,}" if (fcf is not None and fcf != "N/A") else "N/A"

        return {
            "ROE": roe_formatted,
            "Debt to Equity": debt_formatted,
            "Free Cash Flow": fcf_formatted
        }
    except Exception:
        return {"ROE": "N/A", "Debt to Equity": "N/A", "Free Cash Flow": "N/A"}

def calculate_dcf_value(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        shares = info.get("sharesOutstanding")
        
        fcf = info.get("freeCashFlow")
        if fcf is None:
            try:
                cashflow = stock.cashflow
                if not cashflow.empty:
                    opf = cashflow.loc['Operating Cash Flow'].iloc[0] if 'Operating Cash Flow' in cashflow.index else 0
                    capex = cashflow.loc['Capital Expenditure'].iloc[0] if 'Capital Expenditure' in cashflow.index else 0
                    fcf = opf + capex if capex < 0 else opf - capex
            except Exception:
                fcf = None

        if fcf and shares and fcf > 0 and shares > 0:
            growth_rate = 0.10  
            discount_rate = 0.12  
            temp_fcf = fcf
            projected_fcf = 0
            
            for _ in range(5):
                temp_fcf *= (1 + growth_rate)
                projected_fcf += temp_fcf / ((1 + discount_rate) ** (_ + 1))
                
            terminal_value = (temp_fcf * (1 + 0.03)) / (discount_rate - 0.03)
            projected_fcf += terminal_value / ((1 + discount_rate) ** 5)
            
            return round(projected_fcf / shares, 2)
        return None
    except Exception:
        return None

def get_latest_quarterly_income_statement(ticker):
    try:
        stock = yf.Ticker(ticker)
        financials = stock.quarterly_financials
        if not financials.empty:
            return financials.iloc[:, :2].to_string()
        return "Financial statements not available."
    except Exception:
        return "Error loading financial statements."

def get_recent_news_headlines(ticker):
    try:
        search_keyword = ticker.replace(".NS", "").replace(".BO", "") + " stock"
        encoded_keyword = urllib.parse.quote(search_keyword)
        rss_url = f"https://news.google.com/rss/search?q={encoded_keyword}&hl=en-IN&gl=IN&ceid=IN:en"
        
        req = urllib.request.Request(rss_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            xml_data = response.read()
            
        root = ET.fromstring(xml_data)
        headlines = []
        
        for item in root.findall('.//item')[:5]:
            title_text = item.find('title').text if item.find('title') is not None else ""
            if title_text:
                if " - " in title_text:
                    title_text = title_text.rsplit(" - ", 1)[0]
                headlines.append(f"• {title_text}")
                
        if headlines:
            return "\n".join(headlines)
        return "No recent news headlines found."
    except Exception:
        return "Financial news stream temporarily unavailable."

def get_shareholding_pattern(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        insiders = info.get("heldPercentInsiders")
        institutions = info.get("heldPercentInstitutions")
        
        if insiders is None and institutions is None:
            return None
            
        return {
            "insiders": float(insiders) if insiders is not None else 0.0,
            "institutions": float(institutions) if institutions is not None else 0.0
        }
    except Exception:
        return None

import sqlite3

def init_db():
    """Initializes the SQLite database and creates the watchlist table structure if missing."""
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
    """Inserts a confirmed stock ticker and its market exchange rule into the database."""
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
    """Retrieves all permanently saved investment rows from the local registry database."""
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
    """Deletes a selected stock index row completely out of the local tracking database."""
    try:
        conn = sqlite3.connect("watchlist.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM watchlist WHERE ticker = ? AND exchange = ?", (ticker, exchange))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False