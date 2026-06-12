import yfinance as yf
import pandas as pd
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import sqlite3
import logging
from cachetools import TTLCache  # FIXED: Issue #2 - Swapped raw dicts with self-cleaning TTL structures

# --- MODULE-LEVEL STRUCTURED LOGGING ENGINE ---
logger = logging.getLogger(__name__)

# --- RUNTIME CACHE MEMOIZATION DESK ---
# FIXED: Issue #2 - Set absolute maximum bounds (512 objects) and 5-minute expirations to eliminate memory leaks
_ticker_cache = TTLCache(maxsize=512, ttl=300)
_download_cache = TTLCache(maxsize=512, ttl=300)

def _get_cached_ticker(ticker):
    if ticker not in _ticker_cache:
        _ticker_cache[ticker] = yf.Ticker(ticker)
    return _ticker_cache[ticker]

def _get_cached_download(ticker, period="1y"):
    cache_key = (ticker, period)
    if cache_key not in _download_cache:
        logger.info(f"Downloading historical timeline vector for ticker: {ticker} (Period: {period})")
        df = yf.download(ticker, period=period, progress=False)
        _download_cache[cache_key] = df
    return _download_cache[cache_key]

# --- SQL WATCHLIST DATABASE MODULE ---
def init_db():
    conn = sqlite3.connect("watchlist.db")
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS watchlist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    exchange TEXT NOT NULL,
                    UNIQUE(ticker, exchange)
                )
            """)
            
            # FIXED: Issue #4 - Live Schema Migration. Detects and alters legacy tracking matrices safely
            cursor.execute("PRAGMA table_info(watchlist)")
            existing_columns = [column_row[1] for column_row in cursor.fetchall()]
            
            if "created_at" not in existing_columns:
                logger.info("Legacy watchlist layout detected. Migrating database tables...")
                cursor.execute("ALTER TABLE watchlist ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                logger.info("Watchlist table schema successfully updated with 'created_at' index parameters.")
    except sqlite3.Error as err:
        # FIXED: Issue #5 - Switched noisy stack traces to concise warnings for expected storage anomalies
        logger.warning(f"Database configuration step bypassed or uninitialized: {type(err).__name__}")
    finally:
        conn.close()

def add_to_watchlist(ticker, exchange):
    conn = sqlite3.connect("watchlist.db")
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO watchlist (ticker, exchange) VALUES (?, ?)", (ticker, exchange))
        return True
    except sqlite3.Error as err:
        logger.warning(f"Failed to append asset row track element onto database: {type(err).__name__}")
        return False
    finally:
        conn.close()

def get_watchlist():
    conn = sqlite3.connect("watchlist.db")
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT ticker, exchange FROM watchlist ORDER BY created_at DESC")
        rows = cursor.fetchall()
        return rows
    except sqlite3.Error as err:
        logger.warning(f"Watchlist database structural query failed: {type(err).__name__}")
        return []
    finally:
        conn.close()

def remove_from_watchlist(ticker, exchange):
    conn = sqlite3.connect("watchlist.db")
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM watchlist WHERE ticker = ? AND exchange = ?", (ticker, exchange))
        return True
    except sqlite3.Error as err:
        logger.warning(f"Failed to clear selected track element row: {type(err).__name__}")
        return False
    finally:
        conn.close()

# --- UTILITY: DEEP FINANCIAL STATEMENT EXTRACTOR ---
def extract_statement_metric(df, rows_to_check):
    """Safely extracts the latest numeric value from financial dataframes using high-performance vectorized string scanning."""
    try:
        if df is None or df.empty:
            return None
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        # FIXED: Issue #7 - Eliminated nested loops. Using clean vectorized pandas pandas-series lookups instead
        index_series = pd.Series(df.index, index=df.index).astype(str).str.lower()
        
        for row_name in rows_to_check:
            target_string = row_name.lower()
            matched_rows = index_series[index_series.str.contains(target_string, na=False)]
            
            if not matched_rows.empty:
                val = df.loc[matched_rows.index[0]]
                if isinstance(val, pd.Series):
                    val = val.iloc[0]
                if pd.notna(val) and not isinstance(val, (str, bool)):
                    return float(val)
    except Exception as exc:
        logger.debug(f"Dataframe row extraction sequence bypassed: {type(exc).__name__}")
    return None

# --- UTILITY: INTERNATIONALLY AWARE CURRENCY FORMATTER ---
def format_financial_units(value, ticker):
    if value is None or pd.isna(value):
        return None
    is_indian = ticker.endswith(".NS") or ticker.endswith(".BO")
    if is_indian:
        return f"₹{value / 10_000_000:,.2f} Cr"
    return f"${value / 1_000_000:,.2f} M"

# --- DATA ENGINE CORE FUNCTIONS ---
def get_current_price(ticker):
    try:
        stock = _get_cached_ticker(ticker)
        
        # FIXED: Issue #3 - Intercept and utilize fast_info layers first to capture real-time market action instantly
        try:
            if hasattr(stock, 'fast_info'):
                live_price = stock.fast_info.get('lastPrice') or stock.fast_info.get('last_price')
                if live_price is not None:
                    return float(live_price)
        except Exception:
            pass
            
        info = stock.info if stock.info else {}
        price = info.get("currentPrice") or info.get("regularMarketPrice")
        if price:
            return float(price)
        
        # Last resort history array calculation check
        df = _get_cached_download(ticker, period="1y")
        if not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            series = df['Close']
            if isinstance(series, pd.DataFrame):
                series = series.iloc[:, 0]
            valid_prices = series.dropna()
            if not valid_prices.empty:
                return float(valid_prices.iloc[-1])
    except Exception as exc:
        logger.warning(f"Unable to extract real-time price updates for {ticker}: {type(exc).__name__}")
    return None

def get_key_ratios(ticker):
    try:
        stock = _get_cached_ticker(ticker)
        info = stock.info if stock.info else {}
        current_price = get_current_price(ticker)
        
        pe = info.get("trailingPE")
        forward_pe = info.get("forwardPE")
        pb = info.get("priceToBook")
        
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
            except Exception as inner_exc:
                logger.debug(f"Book value substitution extraction pass: {type(inner_exc).__name__}")

        return {
            "P/E Ratio": round(pe, 2) if pe is not None and not pd.isna(pe) else None,
            "Forward P/E": round(forward_pe, 2) if forward_pe is not None and not pd.isna(forward_pe) else None,
            "Price to Book": round(pb, 2) if pb is not None and not pd.isna(pb) else None
        }
    except Exception as exc:
        logger.warning(f"Valuation metrics extraction failed on ticker target {ticker}: {type(exc).__name__}")
        return {"P/E Ratio": None, "Forward P/E": None, "Price to Book": None}

def get_financial_health(ticker):
    try:
        stock = _get_cached_ticker(ticker)
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

        d_e_val = None
        if debt_to_equity is not None and not pd.isna(debt_to_equity):
            d_e_val = f"{debt_to_equity / 100:.2f}" if debt_to_equity > 5 else f"{debt_to_equity:.2f}"

        return {
            "ROE": f"{roe * 100:.2f}%" if roe is not None and not pd.isna(roe) else None,
            "Debt to Equity": d_e_val,
            "Free Cash Flow": format_financial_units(fcf, ticker) if fcf is not None else None
        }
    except Exception as exc:
        logger.warning(f"Financial safety calculations skipped on target {ticker}: {type(exc).__name__}")
        return {"ROE": None, "Debt to Equity": None, "Free Cash Flow": None}

def calculate_graham_value(ticker):
    try:
        stock = _get_cached_ticker(ticker)
        info = stock.info if stock.info else {}
        
        eps = info.get("trailingEps")
        bvps = info.get("bookValue")
        
        if not eps or not bvps or pd.isna(eps) or pd.isna(bvps):
            try:
                shares = info.get("sharesOutstanding") or info.get("impliedSharesOutstanding")
                net_income = extract_statement_metric(stock.financials, ["Net Income"])
                total_assets = extract_statement_metric(stock.balance_sheet, ["Total Assets"])
                # FIXED: Bug #1 - Corrected tracking reference scope from balance_sheet to stock.balance_sheet
                total_liab = extract_statement_metric(stock.balance_sheet, ["Total Liabilities"])
                
                if shares and shares > 0:
                    if net_income: eps = net_income / shares
                    if total_assets and total_liab: bvps = (total_assets - total_liab) / shares
            except Exception:
                pass
        
        if eps and bvps and eps > 0 and bvps > 0:
            val = (22.5 * eps * bvps) ** 0.5
            return round(float(val), 2) if not pd.isna(val) else None
        return None
    except Exception as exc:
        logger.warning(f"Traditional Graham analysis step bypassed for {ticker}: {type(exc).__name__}")
        return None

def calculate_dcf_value(ticker):
    return None

def get_shareholding_pattern(ticker):
    try:
        stock = _get_cached_ticker(ticker)
        info = stock.info if stock.info else {}
        insiders = info.get("heldPercentInsiders")
        institutions = info.get("heldPercentInstitutions")
        
        return {
            "insiders": float(insiders) if insiders is not None and not pd.isna(insiders) else None,
            "institutions": float(institutions) if institutions is not None and not pd.isna(institutions) else None
        }
    except Exception as exc:
        logger.warning(f"Shareholding data tracking unavailable on target {ticker}: {type(exc).__name__}")
        return {"insiders": None, "institutions": None}

def get_technical_indicators(ticker):
    try:
        df_raw = _get_cached_download(ticker, period="1y")
        if df_raw.empty: 
            return None
            
        df = df_raw.copy()
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
        
        sma_200_val = None
        if len(df) >= 200:
            sma_200_series = df['Close'].rolling(window=200).mean()
            sma_200_val = float(sma_200_series.iloc[-1]) if not pd.isna(sma_200_series.iloc[-1]) else None
        
        support_val = float(df['Low'].rolling(window=50).min().iloc[-1])
        resistance_val = float(df['High'].rolling(window=50).max().iloc[-1])

        stock = _get_cached_ticker(ticker)
        beta_val = None
        try:
            if stock.info:
                beta_val = stock.info.get("beta")
                if beta_val is not None:
                    beta_val = float(beta_val)
        except Exception:
            pass

        return {
            "Close": latest_close,
            "RSI": float(rsi_series.iloc[-1]) if not pd.isna(rsi_series.iloc[-1]) else None,
            "EMA_20": float(ema_20_series.iloc[-1]) if not pd.isna(ema_20_series.iloc[-1]) else None,
            "EMA_50": float(ema_50_series.iloc[-1]) if not pd.isna(ema_50_series.iloc[-1]) else None,
            "50 DMA": float(sma_50_series.iloc[-1]) if not pd.isna(sma_50_series.iloc[-1]) else None,
            "200 DMA": sma_200_val,
            "Support": support_val,
            "Resistance": resistance_val,
            "Beta Index": beta_val
        }
    except Exception as exc:
        logger.warning(f"Technical series rendering exception on ticker {ticker}: {type(exc).__name__}")
        return None

def get_latest_quarterly_income_statement(ticker):
    try:
        stock = _get_cached_ticker(ticker)
        df = stock.quarterly_financials
        if df is not None and not df.empty:
            return df.iloc[:, 0].to_dict()
        return {}
    except Exception as exc:
        logger.warning(f"Quarterly financials tracking retrieval failure on {ticker}: {type(exc).__name__}")
        return {}

def get_recent_news_headlines(ticker):
    try:
        clean_ticker = ticker.split('.')[0]
        # FIXED: Issue #8 - Enhanced query configuration using long company identifiers to filter out ambient market noise
        search_query = f"{clean_ticker} stock"
        try:
            stock = _get_cached_ticker(ticker)
            if stock.info and stock.info.get("longName"):
                cleaned_name = stock.info.get("longName").split()[0].replace(",", "").replace(".", "")
                search_query = f"{cleaned_name} share news"
        except Exception:
            pass
            
        encoded_query = urllib.parse.quote_with_plus(search_query)
        url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
        
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            xml_data = response.read()
            
        root = ET.fromstring(xml_data)
        headlines = []
        for item in root.findall('.//item')[:5]:
            title_node = item.find('title')
            link_node = item.find('link')
            if title_node is not None and title_node.text:
                headlines.append({
                    "headline": title_node.text, 
                    "url": link_node.text if link_node is not None else "#"
                })
        return headlines if headlines else [{"headline": f"No recent news catalyst found for {ticker}.", "url": "#"}]
    except Exception as exc:
        logger.warning(f"RSS news aggregator timeline exception on asset {ticker}: {type(exc).__name__}")
        return [{"headline": f"No recent news catalyst found for {ticker}.", "url": "#"}]
