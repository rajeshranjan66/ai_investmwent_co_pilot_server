import math
from datetime import datetime, timedelta
from cachetools import cached, TTLCache
import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import numpy as np
import yfinance as yf
from dotenv import load_dotenv
from fastmcp import FastMCP
from pandas import DataFrame
import logging
from typing import Dict, Any, Optional, List
from statsmodels.tsa.arima.model import ARIMA
import uvicorn
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from langchain_community.tools.tavily_search import TavilySearchResults
from cachetools.keys import hashkey
import functools
import time
from langchain_community.tools.tavily_search import TavilySearchResults
import os
load_dotenv()

# cache 500 records for 30 sec,
#financialdata_cache = TTLCache(maxsize=100, ttl=300)
#pricedata_cache = TTLCache(maxsize=100, ttl=30)
#Stores up to 100 different stock symbols
#Each entry expires after 30 seconds (TTL = Time To Live)
#Automatically removes old entries when full

price_cache = TTLCache(maxsize=100, ttl=1800)
import inspect

class CacheWithStats:
    def __init__(self, cache):
        self._cache = cache
        self.hits = 0
        self.misses = 0
        self._last_reset = time.time()

    def __call__(self, func):
        # Check if the function is async
        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                # Include function name in the cache key
                key = self._generate_key(func.__name__, *args, **kwargs)
                if key in self._cache:
                    self.hits += 1
                    logging.debug(f"Cache HIT for {func.__name__} with key: {key}")
                    return self._cache[key]
                else:
                    self.misses += 1
                    logging.debug(f"Cache MISS for {func.__name__} with key: {key}")
                    result = await func(*args, **kwargs)
                    self._cache[key] = result
                    return result

            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                # Include function name in the cache key
                key = self._generate_key(func.__name__, *args, **kwargs)
                if key in self._cache:
                    self.hits += 1
                    logging.debug(f"Cache HIT for {func.__name__} with key: {key}")
                    return self._cache[key]
                else:
                    self.misses += 1
                    logging.debug(f"Cache MISS for {func.__name__} with key: {key}")
                    result = func(*args, **kwargs)
                    self._cache[key] = result
                    return result

            return sync_wrapper

    @staticmethod
    def _make_hashable(obj):
        if isinstance(obj, dict):
            return tuple(sorted((k, CacheWithStats._make_hashable(v)) for k, v in obj.items()))
        elif isinstance(obj, (list, set)):
            return tuple(CacheWithStats._make_hashable(x) for x in obj)
        return obj

    def _generate_key(self, *args, **kwargs):
        hashable_args = tuple(CacheWithStats._make_hashable(arg) for arg in args)
        hashable_kwargs = tuple(sorted((k, CacheWithStats._make_hashable(v)) for k, v in kwargs.items()))
        return hashkey(*hashable_args, *hashable_kwargs)

    # def _generate_key(self, *args, **kwargs):
    #     """Generate a cache key using cachetools.hashkey."""
    #     return hashkey(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._cache, name)

# Wrap the price_cache for statistics tracking
tracked_cache = CacheWithStats(price_cache)




# Initialize logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')
#mcp = FastMCP("stocksAnalysisMCPServer", "1.0.0", "A server to analyze stock data using yfinance")

# Initialize FastAPI app
#app = FastAPI()

# Add CORS middleware
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# Initialize FastMCP
mcp = FastMCP(name="stocksMCPServerHTTPYFinance",)



#tested

@mcp.tool()
@tracked_cache
async def fetch_stock_info(symbol: str) -> dict:
    """
    Get general company info for a stock symbol.
    Args: symbol (str)
    Returns: dict with company profile and key stats.
    """
    try:
        ticker = yf.Ticker(symbol)

        # fast_info: quick access to common fields
        fast_info = ticker.fast_info if hasattr(ticker, "fast_info") else {}

        # get_info(): more detailed profile (non-deprecated version of .info)
        try:
            full_info = ticker.get_info()

            #logging.info(f"full_info keys for {symbol}: {list(full_info.keys())}")
        except Exception as e:
            #logging.warning(f"Could not fetch detailed info for {symbol}: {e}")
            full_info = {}

        result = {
            "symbol": symbol,
            "company_name": full_info.get("shortName"),
            "market_cap": full_info.get("marketCap"),
            "pe_ratio": full_info.get("trailingPE"),
            "52_week_high": full_info.get("fiftyTwoWeekHigh"),
            "52_week_low": full_info.get("fiftyTwoWeekLow"),
            "company_name": full_info.get("shortName"),
            "long_name": full_info.get("longName"),
            "symbol": full_info.get("symbol"),
            "exchange": full_info.get("exchange"),
            "sector": full_info.get("sector"),
            "industry": full_info.get("industry"),
            "market_cap": full_info.get("marketCap"),
            "enterprise_value": full_info.get("enterpriseValue"),
            "shares_outstanding": full_info.get("sharesOutstanding"),
            "pe_ratio_trailing": full_info.get("trailingPE"),
            "pe_ratio_forward": full_info.get("forwardPE"),
            "peg_ratio": full_info.get("pegRatio"),
            "dividend_rate": full_info.get("dividendRate"),
            "dividend_yield": full_info.get("dividendYield"),
            "ex_dividend_date": full_info.get("exDividendDate"),
            "payout_ratio": full_info.get("payoutRatio"),
            "five_year_avg_dividend_yield": full_info.get("fiveYearAvgDividendYield"),
            "fifty_two_week_high": full_info.get("fiftyTwoWeekHigh"),
            "fifty_two_week_low": full_info.get("fiftyTwoWeekLow"),
            "regular_market_price": full_info.get("regularMarketPrice"),
            "beta": full_info.get("beta"),
            "profit_margins": full_info.get("profitMargins"),
            "gross_margins": full_info.get("grossMargins"),
            "ebitda_margins": full_info.get("ebitdaMargins"),
            "revenue": full_info.get("revenue"),
            "gross_profits": full_info.get("grossProfits"),
            "total_cash": full_info.get("totalCash"),
            "total_debt": full_info.get("totalDebt"),
            "debt_to_equity": full_info.get("debtToEquity"),
            "website": full_info.get("website"),
            "address": full_info.get("address1"),
            "city": full_info.get("city"),
            "state": full_info.get("state"),
            "country": full_info.get("country"),
            "full_time_employees": full_info.get("fullTimeEmployees"),
            "earnings_growth": full_info.get("earningsGrowth"),
            "revenue_growth": full_info.get("revenueGrowth"),
            "operating_margins": full_info.get("operatingMargins"),
            "recommendation_mean": full_info.get("recommendationMean"),
            "recommendation_key": full_info.get("recommendationKey"),
            "logo_url": full_info.get("logo_url"),
            "phone": full_info.get("phone"),
            "summary": full_info.get("summary"),
            "general_info": {},


            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # Merge fast_info + full_info
        result["general_info"].update(fast_info if fast_info else {})
        result["general_info"].update(full_info if full_info else {})

        if not result["general_info"]:
            return {
                "error": f"No stock info available for {symbol}",
                "symbol": symbol,
                "last_updated": result["last_updated"]
            }

        return result

    except Exception as e:
        logging.error(f"Error fetching stock info for {symbol}: {str(e)}")
        return {
            "error": f"Failed to fetch stock info: {str(e)}",
            "symbol": symbol,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }



@mcp.tool()
@tracked_cache
async def fetch_quarterly_financials(symbol: str) -> dict:
    """
        Get quarterly financials and ratios for a stock.
        Args: symbol (str)
        Returns: list of dicts per quarter with metrics.
        """
    ticker = yf.Ticker(symbol)
    income = ticker.quarterly_financials
    balance = ticker.quarterly_balance_sheet
    cashflow = ticker.quarterly_cashflow

    if (income is None or income.empty) and (balance is None or balance.empty) and (cashflow is None or cashflow.empty):
        return {"error": f"No quarterly financial statements available for {symbol}"}

    df_income = income.T if income is not None else pd.DataFrame()
    df_balance = balance.T if balance is not None else pd.DataFrame()
    df_cashflow = cashflow.T if cashflow is not None else pd.DataFrame()

    combined = df_income.join(df_balance, how="outer", lsuffix="_inc", rsuffix="_bal")
    combined = combined.join(df_cashflow, how="outer", rsuffix="_cf")
    combined.sort_index(ascending=False, inplace=True)
    combined = combined.reset_index()

    records = []
    for i, row in combined.iterrows():
        quarter_data = row.to_dict()
        try:
            revenue = row.get("Total Revenue", None)
            net_income = row.get("Net Income", None)
            ebitda = row.get("EBITDA", None)
            operating_income = row.get("Operating Income", None)
            gross_profit = row.get("Gross Profit", None)
            total_assets = row.get("Total Assets", None)
            total_liabilities = row.get("Total Liab", None)
            equity = row.get("Total Stockholder Equity", None)
            free_cash_flow = row.get("Free Cash Flow", None)
            capex = row.get("Capital Expenditures", None)
            current_assets = row.get("Total Current Assets", None)
            current_liabilities = row.get("Total Current Liabilities", None)
            inventory = row.get("Inventory", None)
            receivables = row.get("Net Receivables", None)
            shares_outstanding = row.get("Common Stock", None)
            dividends = row.get("Dividends Paid", None)
            tax_expense = row.get("Income Tax Expense", None)
            interest_expense = row.get("Interest Expense", None)

            eps = net_income / shares_outstanding if net_income and shares_outstanding else None
            roe = net_income / equity if net_income and equity else None
            roa = net_income / total_assets if net_income and total_assets else None
            current_ratio = current_assets / current_liabilities if current_assets and current_liabilities else None
            quick_ratio = (current_assets - inventory) / current_liabilities if current_assets and inventory and current_liabilities else None
            debt_to_equity = total_liabilities / equity if total_liabilities and equity else None
            interest_coverage = operating_income / interest_expense if operating_income and interest_expense else None
            book_value_per_share = equity / shares_outstanding if equity and shares_outstanding else None
            gross_margin = gross_profit / revenue if gross_profit and revenue else None
            operating_margin = operating_income / revenue if operating_income and revenue else None
            net_margin = net_income / revenue if net_income and revenue else None
            dividend_payout_ratio = dividends / net_income if dividends and net_income else None
            effective_tax_rate = tax_expense / pre_tax_income if tax_expense and (pre_tax_income := row.get("Pretax Income", None)) else None
            inventory_turnover = revenue / inventory if revenue and inventory else None
            receivables_turnover = revenue / receivables if revenue and receivables else None

            quarter_data.update({
                "EPS": eps,
                "EBITDA": ebitda,
                "Operating_Income": operating_income,
                "Gross_Profit": gross_profit,
                "Total_Assets": total_assets,
                "Total_Liabilities": total_liabilities,
                "Shareholder_Equity": equity,
                "Free_Cash_Flow": free_cash_flow,
                "Return_on_Equity": roe,
                "Return_on_Assets": roa,
                "Current_Ratio": current_ratio,
                "Quick_Ratio": quick_ratio,
                "Debt_to_Equity": debt_to_equity,
                "Interest_Coverage": interest_coverage,
                "Book_Value_Per_Share": book_value_per_share,
                "Gross_Margin": gross_margin,
                "Operating_Margin": operating_margin,
                "Net_Margin": net_margin,
                "Dividend_Payout_Ratio": dividend_payout_ratio,
                "Effective_Tax_Rate": effective_tax_rate,
                "Capital_Expenditures": capex,
                "Inventory_Turnover": inventory_turnover,
                "Receivables_Turnover": receivables_turnover,
            })

            # Growth rates (QoQ)
            if i < len(combined) - 1:
                prev_row = combined.iloc[i + 1]
                prev_revenue = prev_row.get("Total Revenue", None)
                prev_net_income = prev_row.get("Net Income", None)
                quarter_data["Revenue_Growth_QoQ"] = ((revenue - prev_revenue) / prev_revenue) if revenue and prev_revenue else None
                quarter_data["Net_Income_Growth_QoQ"] = ((net_income - prev_net_income) / prev_net_income) if net_income and prev_net_income else None
        except Exception:
            pass
        records.append(quarter_data)

    return {"quarterly_financials": records}


@mcp.tool()
@tracked_cache
async def fetch_annual_financials(symbol: str) -> dict:

    """
    Get annual financials and ratios for a stock.
    Args: symbol (str)
    Returns: list of dicts per year with metrics.
    """
    ticker = yf.Ticker(symbol)
    income = ticker.financials
    balance = ticker.balance_sheet
    cashflow = ticker.cashflow

    if (income is None or income.empty) and (balance is None or balance.empty) and (cashflow is None or cashflow.empty):
        return {"error": f"No financial statements available for {symbol}"}

    df_income = income.T if income is not None else pd.DataFrame()
    df_balance = balance.T if balance is not None else pd.DataFrame()
    df_cashflow = cashflow.T if cashflow is not None else pd.DataFrame()

    combined = df_income.join(df_balance, how="outer", lsuffix="_inc", rsuffix="_bal")
    combined = combined.join(df_cashflow, how="outer", rsuffix="_cf")
    combined.sort_index(ascending=False, inplace=True)
    combined = combined.reset_index()

    # Calculate additional metrics
    records = []
    for i, row in combined.iterrows():
        year_data = row.to_dict()
        try:
            # Extract values safely
            revenue = row.get("Total Revenue", None)
            net_income = row.get("Net Income", None)
            ebitda = row.get("EBITDA", None)
            operating_income = row.get("Operating Income", None)
            gross_profit = row.get("Gross Profit", None)
            total_assets = row.get("Total Assets", None)
            total_liabilities = row.get("Total Liab", None)
            equity = row.get("Total Stockholder Equity", None)
            free_cash_flow = row.get("Free Cash Flow", None)
            capex = row.get("Capital Expenditures", None)
            current_assets = row.get("Total Current Assets", None)
            current_liabilities = row.get("Total Current Liabilities", None)
            inventory = row.get("Inventory", None)
            receivables = row.get("Net Receivables", None)
            shares_outstanding = row.get("Common Stock", None)
            dividends = row.get("Dividends Paid", None)
            tax_expense = row.get("Income Tax Expense", None)
            interest_expense = row.get("Interest Expense", None)

            # Ratios and growth
            eps = net_income / shares_outstanding if net_income and shares_outstanding else None
            roe = net_income / equity if net_income and equity else None
            roa = net_income / total_assets if net_income and total_assets else None
            current_ratio = current_assets / current_liabilities if current_assets and current_liabilities else None
            quick_ratio = (current_assets - inventory) / current_liabilities if current_assets and inventory and current_liabilities else None
            debt_to_equity = total_liabilities / equity if total_liabilities and equity else None
            interest_coverage = operating_income / interest_expense if operating_income and interest_expense else None
            book_value_per_share = equity / shares_outstanding if equity and shares_outstanding else None
            gross_margin = gross_profit / revenue if gross_profit and revenue else None
            operating_margin = operating_income / revenue if operating_income and revenue else None
            net_margin = net_income / revenue if net_income and revenue else None
            dividend_payout_ratio = dividends / net_income if dividends and net_income else None
            effective_tax_rate = tax_expense / pre_tax_income if tax_expense and (pre_tax_income := row.get("Pretax Income", None)) else None
            inventory_turnover = revenue / inventory if revenue and inventory else None
            receivables_turnover = revenue / receivables if revenue and receivables else None

            # Add to year_data
            year_data.update({
                "EPS": eps,
                "EBITDA": ebitda,
                "Operating_Income": operating_income,
                "Gross_Profit": gross_profit,
                "Total_Assets": total_assets,
                "Total_Liabilities": total_liabilities,
                "Shareholder_Equity": equity,
                "Free_Cash_Flow": free_cash_flow,
                "Return_on_Equity": roe,
                "Return_on_Assets": roa,
                "Current_Ratio": current_ratio,
                "Quick_Ratio": quick_ratio,
                "Debt_to_Equity": debt_to_equity,
                "Interest_Coverage": interest_coverage,
                "Book_Value_Per_Share": book_value_per_share,
                "Gross_Margin": gross_margin,
                "Operating_Margin": operating_margin,
                "Net_Margin": net_margin,
                "Dividend_Payout_Ratio": dividend_payout_ratio,
                "Effective_Tax_Rate": effective_tax_rate,
                "Capital_Expenditures": capex,
                "Inventory_Turnover": inventory_turnover,
                "Receivables_Turnover": receivables_turnover,
            })

            # Growth rates (YoY)
            if i < len(combined) - 1:
                prev_row = combined.iloc[i + 1]
                prev_revenue = prev_row.get("Total Revenue", None)
                prev_net_income = prev_row.get("Net Income", None)
                year_data["Revenue_Growth_YoY"] = ((revenue - prev_revenue) / prev_revenue) if revenue and prev_revenue else None
                year_data["Net_Income_Growth_YoY"] = ((net_income - prev_net_income) / prev_net_income) if net_income and prev_net_income else None
        except Exception:
            pass
        records.append(year_data)

    return {"annual_financials": records[:2]}



# @mcp.tool()
# @tracked_cache
async def get_stock_price(symbol: str) -> Optional[float]:
    """
    Retrieve the latest stock price for a given symbol.

    Args:
        symbol (str): The stock symbol (e.g., "AAPL", "MSFT").

    Returns:
        float: The latest stock price if successful.
        None: If the price data is unavailable or invalid.
    """
    logging.debug(f"**************fetch_stock_info called with: {symbol}")
    logging.debug(f"***************Cache stats - Hits: {tracked_cache.hits}, Misses: {tracked_cache.misses}")
    logging.debug(f"═══════════════════════════════════════════════════")
    logging.debug(f"fetch_stock_info called with: '{symbol}'")
    logging.debug(f"Type of symbol: {type(symbol)}, Value: '{symbol}'")
    logging.debug(f"Cache stats - Hits: {tracked_cache.hits}, Misses: {tracked_cache.misses}")
    logging.debug(f"Current cache size: {len(price_cache)}")
    logging.debug(f"Cache keys: {list(price_cache.keys())}")
    logging.debug(f"═══════════════════════════════════════════════════")
    try:
        ticker = yf.Ticker(symbol)

        # Get data with timeout and validation
        data = ticker.history(
            period="1d",
            interval="1m",  # More frequent data for accuracy
            prepost=False,  # Only regular market hours
            timeout=10  # Fail fast if no response
        )

        if data.empty:
            logging.error(f"No price data for {symbol}")
            return None

        # Validate we have closing price
        if "Close" not in data.columns:
            logging.error(f"Missing Close price for {symbol}")
            return None

        latest_price = data["Close"].iloc[-1]

        # Price sanity check
        if not isinstance(latest_price, (float, int)) or latest_price <= 0:
            logging.error(f"Invalid price {latest_price} for {symbol}")
            return None

       # logging.info(f"Price retrieved for {symbol}: ${latest_price:.2f}")
        return float(latest_price)

    except Exception as e:
        logging.error(f"Failed to get price for {symbol}: {str(e)}")
        return None


@mcp.tool()
@tracked_cache
async def get_stock_history(symbol: str, period: str = "1mo") -> DataFrame:
    """
    Retrieve historical stock price data with technical indicators.

    Args:
        symbol (str): The stock symbol (e.g., "AAPL", "MSFT").
        period (str): The time period for the data (default: "1mo").
                      Valid values: "1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max".

    Returns:
        DataFrame: A DataFrame containing OHLCV data, technical indicators, and metadata.
                   Metadata is stored in the `attrs` attribute of the DataFrame.
    """
    logging.debug(f"**************fetch_stock_info called with: {symbol}")
    logging.debug(f"***************Cache stats - Hits: {tracked_cache.hits}, Misses: {tracked_cache.misses}")
    logging.debug(f"═══════════════════════════════════════════════════")
    logging.debug(f"fetch_stock_info called with: '{symbol}'")
    logging.debug(f"Type of symbol: {type(symbol)}, Value: '{symbol}'")
    logging.debug(f"Cache stats - Hits: {tracked_cache.hits}, Misses: {tracked_cache.misses}")
    logging.debug(f"Current cache size: {len(price_cache)}")
    logging.debug(f"Cache keys: {list(price_cache.keys())}")
    logging.debug(f"═══════════════════════════════════════════════════")
    # Input validation
    valid_periods = ['1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max']
    if period not in valid_periods:
        logging.error(f"Invalid period: {period}. Valid periods: {valid_periods}")
        return DataFrame()

    try:
        ticker = yf.Ticker(symbol)

        # Get historical data with modern API
        history = ticker.history(
            period=period,
            interval="1d",
            actions=True,
            auto_adjust=True,
            prepost=False  # Disable pre/post market data for consistency
        )

        if history.empty:
            logging.warning(f"No data for {symbol} (period: {period})")
            return DataFrame()

        # Validate required columns
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        missing_cols = [col for col in required_cols if col not in history.columns]
        if missing_cols:
            logging.error(f"Missing columns: {missing_cols}")
            return DataFrame()

        # Calculate technical indicators
        def safe_calc(series, window):
            try:
                return series.rolling(window=window).mean()
            except:
                return None

        indicators = {
            'Daily_Return': history['Close'].pct_change(),
            'MA5': safe_calc(history['Close'], 5),
            'MA20': safe_calc(history['Close'], 20),
            'Daily_Range': history['High'] - history['Low'],
            'Volume_MA5': safe_calc(history['Volume'], 5)
        }

        # Add indicators only if calculation succeeded
        for name, values in indicators.items():
            if values is not None:
                history[name] = values.round(4)

        # Add metadata
        metadata = {
            'symbol': symbol,
            'period': period,
            'start_date': history.index[0].strftime('%Y-%m-%d'),
            'end_date': history.index[-1].strftime('%Y-%m-%d'),
            'trading_days': len(history),
            'summary_stats': {
                'start_price': float(history['Open'].iloc[0]),
                'end_price': float(history['Close'].iloc[-1]),
                'period_high': float(history['High'].max()),
                'period_low': float(history['Low'].min()),
                'avg_volume': int(history['Volume'].mean()),
                'total_volume': int(history['Volume'].sum()),
                'price_change': float(history['Close'].iloc[-1] - history['Open'].iloc[0]),
                'price_change_pct': round(float(
                    (history['Close'].iloc[-1] - history['Open'].iloc[0]) /
                    history['Open'].iloc[0] * 100), 2)
            }
        }

        history.attrs.update(metadata)
        return history

    except Exception as e:
        logging.error(f"Error processing {symbol}: {str(e)}", exc_info=True)
        return DataFrame()


@mcp.tool()
@tracked_cache
async def fetch_technical_indicators(symbol: str, period: str = "1mo") -> dict:
    """
    Get daily technical indicators for a stock.
    Args: symbol (str), period (str)
    Returns: dict with indicators per day.
    """
    import pandas as pd
    import yfinance as yf

    def safe_calc(series, window):
        try:
            return series.rolling(window=window).mean()
        except Exception:
            return None

    def calc_atr(df, window=14):
        high_low = df['High'] - df['Low']
        high_close = (df['High'] - df['Close'].shift()).abs()
        low_close = (df['Low'] - df['Close'].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return tr.rolling(window=window).mean()

    def calc_obv(df):
        obv = [0]
        for i in range(1, len(df)):
            if df['Close'].iloc[i] > df['Close'].iloc[i - 1]:
                obv.append(obv[-1] + df['Volume'].iloc[i])
            elif df['Close'].iloc[i] < df['Close'].iloc[i - 1]:
                obv.append(obv[-1] - df['Volume'].iloc[i])
            else:
                obv.append(obv[-1])
        return pd.Series(obv, index=df.index)

    def calc_adx(df, window=14):
        try:
            up = df['High'].diff()
            down = -df['Low'].diff()
            plus_dm = np.where((up > down) & (up > 0), up, 0)
            minus_dm = np.where((down > up) & (down > 0), down, 0)

            # Ensure tr is a Series with a valid index
            tr_series = calc_atr(df, window)
            if not isinstance(tr_series, pd.Series):
                return pd.Series([np.nan] * len(df), index=df.index)

            plus_di = 100 * pd.Series(plus_dm, index=df.index).rolling(window).sum() / tr_series
            minus_di = 100 * pd.Series(minus_dm, index=df.index).rolling(window).sum() / tr_series

            # Handle potential division by zero
            dx_denominator = (plus_di + minus_di)
            dx = 100 * (abs(plus_di - minus_di) / dx_denominator.where(dx_denominator != 0, np.nan))

            adx = dx.rolling(window).mean()
            return adx
        except Exception:
            return pd.Series([np.nan] * len(df), index=df.index)

    try:
        ticker = yf.Ticker(symbol)
        history = ticker.history(period=period, interval="1d", auto_adjust=True, prepost=False)
        if history.empty:
            return {"error": f"No data for {symbol} ({period})"}

        # Indicators
        indicators = {
            "SMA5": safe_calc(history["Close"], 5),
            "SMA10": safe_calc(history["Close"], 10),
            "SMA20": safe_calc(history["Close"], 20),

            "SMA50": safe_calc(history["Close"], 50),
            "EMA12": history["Close"].ewm(span=12, adjust=False).mean(),
            "EMA26": history["Close"].ewm(span=26, adjust=False).mean(),
            "RSI14": 100 - (100 / (
                    1 + history["Close"].pct_change().rolling(14).mean() / history["Close"].pct_change().rolling(
                14).std())),
            "MACD": history["Close"].ewm(span=12, adjust=False).mean() - history["Close"].ewm(span=26,
                                                                                              adjust=False).mean(),
            "Bollinger_Upper": safe_calc(history["Close"], 20) + 2 * history["Close"].rolling(20).std(),
            "Bollinger_Lower": safe_calc(history["Close"], 20) - 2 * history["Close"].rolling(20).std(),
            "Daily_Range": history["High"] - history["Low"],
            "Volume_MA5": safe_calc(history["Volume"], 5),
            "ATR14": calc_atr(history, 14),
            "ADX14": calc_adx(history, 14),
            "OBV": calc_obv(history)
        }

        for name, values in indicators.items():
            if values is not None:
                history[name] = values.round(4)

        # Clean up NaN/NaT values for JSON serialization
        history = history.replace({np.nan: None})

        # Prepare output
        result = history.reset_index().to_dict(orient="records")
        # Convert Timestamp objects in records to strings
        for record in result:
            if 'Date' in record and isinstance(record['Date'], pd.Timestamp):
                record['Date'] = record['Date'].strftime('%Y-%m-%d')

        return {"symbol": symbol, "period": period, "indicators": result}

    except TypeError as te:
        logging.error(f"Serialization error in fetch_technical_indicators for {symbol}: {str(te)}")
        return {"error": f"Could not serialize data. Check for non-standard data types. Details: {str(te)}"}
    except Exception as e:
        logging.error(f"General error in fetch_technical_indicators for {symbol}: {str(e)}")
        return {"error": str(e)}


# @mcp.tool()
# @tracked_cache
# async def fetch_technical_indicators(symbol: str, period: str = "1mo") -> dict:
#     """
#     Get daily technical indicators for a stock.
#     Args: symbol (str), period (str)
#     Returns: dict with indicators per day.
#     """
#     import pandas as pd
#     import yfinance as yf
#
#     def safe_calc(series, window):
#         try:
#             return series.rolling(window=window).mean()
#         except Exception:
#             return None
#
#     def calc_atr(df, window=14):
#         high_low = df['High'] - df['Low']
#         high_close = (df['High'] - df['Close'].shift()).abs()
#         low_close = (df['Low'] - df['Close'].shift()).abs()
#         tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
#         return tr.rolling(window=window).mean()
#
#     def calc_obv(df):
#         obv = [0]
#         for i in range(1, len(df)):
#             if df['Close'].iloc[i] > df['Close'].iloc[i - 1]:
#                 obv.append(obv[-1] + df['Volume'].iloc[i])
#             elif df['Close'].iloc[i] < df['Close'].iloc[i - 1]:
#                 obv.append(obv[-1] - df['Volume'].iloc[i])
#             else:
#                 obv.append(obv[-1])
#         return pd.Series(obv, index=df.index)
#
#     def calc_adx(df, window=14):
#         up = df['High'].diff()
#         down = -df['Low'].diff()
#         plus_dm = np.where((up > down) & (up > 0), up, 0)
#         minus_dm = np.where((down > up) & (down > 0), down, 0)
#         tr = calc_atr(df, window)
#         plus_di = 100 * pd.Series(plus_dm).rolling(window).sum() / tr
#         minus_di = 100 * pd.Series(minus_dm).rolling(window).sum() / tr
#         dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
#         adx = dx.rolling(window).mean()
#         return adx
#
#     try:
#         ticker = yf.Ticker(symbol)
#         history = ticker.history(period=period, interval="1d", auto_adjust=True, prepost=False)
#         if history.empty:
#             return {"error": f"No data for {symbol} ({period})"}
#
#         # Indicators
#         indicators = {
#             "SMA5": safe_calc(history["Close"], 5),
#             "SMA10": safe_calc(history["Close"], 10),
#             "SMA20": safe_calc(history["Close"], 20),
#
#             "SMA50": safe_calc(history["Close"], 50),
#             "EMA12": history["Close"].ewm(span=12, adjust=False).mean(),
#             "EMA26": history["Close"].ewm(span=26, adjust=False).mean(),
#             "RSI14": 100 - (100 / (
#                         1 + history["Close"].pct_change().rolling(14).mean() / history["Close"].pct_change().rolling(
#                     14).std())),
#             "MACD": history["Close"].ewm(span=12, adjust=False).mean() - history["Close"].ewm(span=26,
#                                                                                               adjust=False).mean(),
#             "Bollinger_Upper": safe_calc(history["Close"], 20) + 2 * history["Close"].rolling(20).std(),
#             "Bollinger_Lower": safe_calc(history["Close"], 20) - 2 * history["Close"].rolling(20).std(),
#             "Daily_Range": history["High"] - history["Low"],
#             "Volume_MA5": safe_calc(history["Volume"], 5),
#             "ATR14": calc_atr(history, 14),
#             "ADX14": calc_adx(history, 14),
#             "OBV": calc_obv(history)
#         }
#
#         for name, values in indicators.items():
#             if values is not None:
#                 history[name] = values.round(4)
#
#         # Prepare output
#         result = history.reset_index().to_dict(orient="records")
#         return {"symbol": symbol, "period": period, "indicators": result}
#
#     except Exception as e:
#         return {"error": str(e)}

@mcp.tool()
@tracked_cache
async def fetch_dividends(symbol: str) -> dict:
    """
    Retrieve historical dividend data for a given stock symbol.

    Args:
        symbol (str): The stock symbol of the company (e.g., "AAPL", "TSLA").

    Returns:
        dict: A dictionary containing:
              - `dividend_data` (dict): Historical dividend data and statistics.
              - `dividend_summary` (dict): Summary of dividend-related metrics.
              - `last_updated` (str): Timestamp of the data retrieval.
              - `error` (str, optional): Error message if the data retrieval fails.
    """
    try:
        ticker = yf.Ticker(symbol)

        # Get dividend data
        dividends = ticker.history(period="max")['Dividends']

        # Get additional dividend info from ticker.info
        info = ticker.info

        result = {
            "symbol": symbol,
            "dividend_data": {},
            "dividend_summary": {},
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # Process historical dividends
        if not dividends.empty:
            # Filter out zero dividends and create historical data
            div_history = {}
            for date, amount in dividends[dividends > 0].items():
                div_history[date.strftime("%Y-%m-%d")] = float(amount)

            result["dividend_data"] = {
                "history": div_history,
                "total_dividends_paid": len(div_history),
                "latest_dividend": float(dividends[dividends > 0].iloc[-1]) if len(
                    dividends[dividends > 0]) > 0 else None,
                "latest_dividend_date": dividends[dividends > 0].index[-1].strftime("%Y-%m-%d") if len(
                    dividends[dividends > 0]) > 0 else None
            }

            # Calculate some basic statistics
            if div_history:
                dividend_values = list(div_history.values())
                result["dividend_data"]["statistics"] = {
                    "average_dividend": float(sum(dividend_values) / len(dividend_values)),
                    "minimum_dividend": float(min(dividend_values)),
                    "maximum_dividend": float(max(dividend_values)),
                    "total_dividend_amount": float(sum(dividend_values))
                }

        # Add dividend summary from info
        dividend_summary = {}
        dividend_fields = {
            "dividendRate": "annual_dividend_rate",
            "dividendYield": "dividend_yield",
            "payoutRatio": "payout_ratio",
            "fiveYearAvgDividendYield": "five_year_avg_dividend_yield",
            "trailingAnnualDividendRate": "trailing_annual_dividend_rate",
            "trailingAnnualDividendYield": "trailing_annual_dividend_yield"
        }

        for api_field, result_field in dividend_fields.items():
            if api_field in info and info[api_field] is not None:
                dividend_summary[result_field] = float(info[api_field])

        # Add dividend dates
        date_fields = {
            "dividendDate": "next_dividend_date",
            "exDividendDate": "ex_dividend_date",
            "lastDividendDate": "last_dividend_date"
        }

        for api_field, result_field in date_fields.items():
            if api_field in info and info[api_field] is not None:
                try:
                    date_value = datetime.fromtimestamp(info[api_field])
                    dividend_summary[result_field] = date_value.strftime("%Y-%m-%d")
                except (TypeError, ValueError) as e:
                    logging.warning(f"Could not process {api_field}: {e}")

        if dividend_summary:
            result["dividend_summary"] = dividend_summary

        # Check if we have any dividend data
        if not result["dividend_data"] and not result["dividend_summary"]:
            logging.warning(f"No dividend data found for {symbol}")
            return {
                "error": f"No dividend data available for {symbol}",
                "symbol": symbol,
                "last_updated": result["last_updated"]
            }

        return result

    except Exception as e:
        logging.error(f"Error fetching dividends for {symbol}: {str(e)}")
        return {
            "error": f"Failed to fetch dividends: {str(e)}",
            "symbol": symbol,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }


@mcp.tool()
@tracked_cache
async def fetch_actions(symbol: str) -> dict:
    """
    Retrieve corporate actions (dividends and stock splits) for a given stock symbol.

    Args:
        symbol (str): The stock symbol of the company (e.g., "AAPL", "TSLA").

    Returns:
        dict: A dictionary containing:
              - `actions` (dict): Historical dividend and stock split data.
              - `summary` (dict): Summary statistics for dividends and splits.
              - `last_updated` (str): Timestamp of the data retrieval.
              - `error` (str, optional): Error message if the data retrieval fails.
    """
    try:
        ticker = yf.Ticker(symbol)

        # Get historical data with actions
        history = ticker.history(period="max")

        result = {
            "symbol": symbol,
            "actions": {
                "dividends": {},
                "splits": {}
            },
            "summary": {
                "total_dividends": 0,
                "total_splits": 0,
                "dividend_stats": {},
                "split_stats": {}
            },
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # Process dividends
        if 'Dividends' in history.columns:
            dividends = history['Dividends']
            div_data = {}

            # Filter out zero dividends
            non_zero_dividends = dividends[dividends > 0]

            if not non_zero_dividends.empty:
                for date, amount in non_zero_dividends.items():
                    div_data[date.strftime("%Y-%m-%d")] = float(amount)

                dividend_values = list(div_data.values())
                result["actions"]["dividends"] = div_data
                result["summary"]["dividend_stats"] = {
                    "total_dividends_paid": len(div_data),
                    "first_dividend_date": min(div_data.keys()),
                    "last_dividend_date": max(div_data.keys()),
                    "average_dividend": float(sum(dividend_values) / len(dividend_values)),
                    "minimum_dividend": float(min(dividend_values)),
                    "maximum_dividend": float(max(dividend_values)),
                    "total_dividend_amount": float(sum(dividend_values))
                }
                result["summary"]["total_dividends"] = len(div_data)

        # Process stock splits
        if 'Stock Splits' in history.columns:
            splits = history['Stock Splits']
            split_data = {}

            # Filter out non-split events
            non_zero_splits = splits[splits != 0]

            if not non_zero_splits.empty:
                for date, ratio in non_zero_splits.items():
                    split_data[date.strftime("%Y-%m-%d")] = float(ratio)

                split_values = list(split_data.values())
                result["actions"]["splits"] = split_data
                result["summary"]["split_stats"] = {
                    "total_splits": len(split_data),
                    "first_split_date": min(split_data.keys()),
                    "last_split_date": max(split_data.keys()),
                    "split_ratios": split_data
                }
                result["summary"]["total_splits"] = len(split_data)

        # Add additional info from ticker.info
        try:
            info = ticker.info

            # Add upcoming dividend information if available
            if 'dividendDate' in info and info['dividendDate']:
                next_div_date = datetime.fromtimestamp(info['dividendDate'])
                result["upcoming_dividend"] = {
                    "date": next_div_date.strftime("%Y-%m-%d"),
                    "amount": info.get('dividendRate', None)
                }

            # Add ex-dividend date if available
            if 'exDividendDate' in info and info['exDividendDate']:
                ex_div_date = datetime.fromtimestamp(info['exDividendDate'])
                result["ex_dividend_date"] = ex_div_date.strftime("%Y-%m-%d")

        except Exception as e:
            logging.warning(f"Error processing additional info: {str(e)}")

        # Check if we have any data
        if not result["actions"]["dividends"] and not result["actions"]["splits"]:
            logging.warning(f"No corporate actions found for {symbol}")
            return {
                "error": f"No corporate actions available for {symbol}",
                "symbol": symbol,
                "last_updated": result["last_updated"]
            }

        return result

    except Exception as e:
        logging.error(f"Error fetching actions for {symbol}: {str(e)}")
        return {
            "error": f"Failed to fetch actions: {str(e)}",
            "symbol": symbol,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }


@mcp.tool()
@tracked_cache
async def fetch_calendar(symbol: str) -> dict:
    """
    Retrieve upcoming company events, such as earnings dates, for a given stock symbol.

    Args:
        symbol (str): The stock symbol of the company (e.g., "AAPL", "TSLA").

    Returns:
        dict: A dictionary containing:
              - `events` (dict): Upcoming earnings and other event details.
              - `last_updated` (str): Timestamp of the data retrieval.
              - `error` (str, optional): Error message if the data retrieval fails.
    """
    try:
        ticker = yf.Ticker(symbol)
        calendar = ticker.calendar
        earnings_dates = ticker.earnings_dates

        result = {
            "symbol": symbol,
            "events": {},
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # Process calendar events
        if calendar is not None and not calendar.empty:
            try:
                calendar_dict = {}

                # Process Earnings Date
                if 'Earnings Date' in calendar.index:
                    earnings_date = calendar.loc['Earnings Date'].iloc[0]
                    calendar_dict['earnings_date'] = earnings_date.strftime("%Y-%m-%d") if pd.notnull(
                        earnings_date) else None

                # Process Earnings High/Low
                if 'Earnings High' in calendar.index:
                    calendar_dict['earnings_estimate_high'] = float(
                        calendar.loc['Earnings High'].iloc[0]) if pd.notnull(
                        calendar.loc['Earnings High'].iloc[0]) else None

                if 'Earnings Low' in calendar.index:
                    calendar_dict['earnings_estimate_low'] = float(calendar.loc['Earnings Low'].iloc[0]) if pd.notnull(
                        calendar.loc['Earnings Low'].iloc[0]) else None

                # Process Revenue Forecast
                if 'Revenue Forecast' in calendar.index:
                    calendar_dict['revenue_forecast'] = float(calendar.loc['Revenue Forecast'].iloc[0]) if pd.notnull(
                        calendar.loc['Revenue Forecast'].iloc[0]) else None

                result["events"]["upcoming_earnings"] = calendar_dict

            except Exception as e:
                logging.warning(f"Error processing calendar data: {str(e)}")

        # Process detailed earnings dates
        if earnings_dates is not None and not earnings_dates.empty:
            try:
                earnings_list = []
                for date, row in earnings_dates.iterrows():
                    earnings_event = {
                        "date": date.strftime("%Y-%m-%d"),
                        "estimate": float(row.get('EPS Estimate', None)) if pd.notnull(
                            row.get('EPS Estimate', None)) else None,
                        "actual": float(row.get('Reported EPS', None)) if pd.notnull(
                            row.get('Reported EPS', None)) else None,
                        "surprise": float(row.get('Surprise(%)', None)) if pd.notnull(
                            row.get('Surprise(%)', None)) else None
                    }
                    earnings_list.append(earnings_event)

                result["events"]["earnings_history"] = earnings_list[:4]  # Last 4 earnings dates

            except Exception as e:
                logging.warning(f"Error processing earnings dates: {str(e)}")

        # Add additional company events if available
        try:
            # Get company information
            info = ticker.info

            # Add next dividend date if available
            if 'dividendDate' in info and info['dividendDate'] is not None:
                div_date = datetime.fromtimestamp(info['dividendDate'])
                result["events"]["next_dividend"] = {
                    "date": div_date.strftime("%Y-%m-%d"),
                    "amount": info.get('dividendRate', None)
                }

            # Add ex-dividend date if available
            if 'exDividendDate' in info and info['exDividendDate'] is not None:
                ex_div_date = datetime.fromtimestamp(info['exDividendDate'])
                result["events"]["ex_dividend_date"] = ex_div_date.strftime("%Y-%m-%d")

        except Exception as e:
            logging.warning(f"Error processing additional events: {str(e)}")

        # Check if we have any events
        if not any(result["events"].values()):
            logging.warning(f"No calendar events found for {symbol}")
            return {
                "error": f"No calendar events available for {symbol}",
                "symbol": symbol,
                "last_updated": result["last_updated"]
            }

        return result

    except Exception as e:
        logging.error(f"Error fetching calendar for {symbol}: {str(e)}")
        return {
            "error": f"Failed to fetch calendar: {str(e)}",
            "symbol": symbol,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

@mcp.tool()
@tracked_cache
async def fetch_earnings(symbol: str) -> dict:
    """
    Retrieve annual earnings history for a given stock symbol.

    Args:
        symbol (str): The stock symbol of the company (e.g., "AAPL", "TSLA").

    Returns:
        dict: A dictionary containing:
              - Years as keys and earnings data (revenue and net income) as values.
              - `error` (str, optional): Error message if the data retrieval fails.
    """
    try:
        ticker = yf.Ticker(symbol)

        # Income statement -> Net Income (earnings)
        income_stmt = ticker.income_stmt
        # Financials -> Total Revenue
        financials = ticker.financials

        if income_stmt is None or financials is None:
            return {"message": f"No earnings history found for {symbol}"}

        earnings_dict = {}

        for year in income_stmt.columns:
            revenue_val = financials.loc["Total Revenue"].get(year, float("nan"))
            earnings_val = income_stmt.loc["Net Income"].get(year, float("nan"))

            # Replace NaN with None
            revenue = None if (revenue_val is None or math.isnan(revenue_val)) else int(revenue_val)
            earnings = None if (earnings_val is None or math.isnan(earnings_val)) else int(earnings_val)

            earnings_dict[str(year.year)] = {
                "Revenue": revenue,
                "Earnings": earnings
            }

        return earnings_dict

    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
@tracked_cache
async def fetch_institutional_holders(symbol: str) -> dict:
    """
    Retrieve institutional holders and ownership summary for a given stock symbol.

    Args:
        symbol (str): The stock symbol of the company (e.g., "AAPL", "MSFT").

    Returns:
        dict: A dictionary containing:
              - `institutional_holders` (list): List of institutional holders and their details.
              - `ownership_summary` (dict): Summary of major holders and ownership percentages.
              - `metadata` (dict): Metadata about the data retrieval.
              - `error` (str, optional): Error message if the data retrieval fails.
    """
    result = {
        "institutional_holders": [],
        "ownership_summary": {},
        "metadata": {
            "symbol": symbol,
            "last_updated": datetime.now().isoformat(),
            "data_source": "yfinance"
        }
    }

    try:
        ticker = yf.Ticker(symbol)

        # Get institutional holders (new API method)
        inst_holders = ticker.get_institutional_holders()

        # Process institutional holders
        if inst_holders is not None and not inst_holders.empty:
            holders_list = []
            for _, row in inst_holders.iterrows():
                pct_held = row.get('% Out')
                holder_data = {
                    "holder": str(row.get('Holder', 'N/A')),
                    "shares": int(row.get('Shares', 0)),
                    "date_reported": str(row.get('Date Reported', 'N/A')),
                    "value": float(row.get('Value', 0)),
                    "pct_held": float(pct_held) if pct_held is not None else None
                }
                holders_list.append(holder_data)

            result["institutional_holders"] = holders_list
            result["metadata"]["total_institutions"] = len(holders_list)
            result["metadata"]["total_shares"] = int(inst_holders['Shares'].sum())

        # Get major holders (ownership breakdown)
        major_holders = ticker.get_major_holders()

        # Process ownership summary
        if major_holders is not None and not major_holders.empty:
            ownership = {}
            for _, row in major_holders.iterrows():
                if len(row) >= 2:
                    key = str(row.iloc[0]).strip()
                    val = str(row.iloc[1]).strip()
                    if '%' in val:
                        val = float(val.replace('%', '')) / 100
                    ownership[key] = val
            result["ownership_summary"] = ownership

    except Exception as e:
        result["error"] = f"Failed to fetch data for {symbol}"
        result["details"] = str(e)

    return result

@mcp.tool()
@tracked_cache
async def portfolio_quant_analysis(holdings: dict) -> dict:
    """
    Detailed quantitative research analysis with statistical metrics , risk metrics, narrative about portfolio,Top sector exposure,Annualized volatility
    and optimization suggestions. Best for in-depth quant review.
    Args:
        holdings: {"AAPL": 10, "MSFT": 5, "CASH": 5000}
    Returns:
        Detailed portfolio analytics dictionary.
    """

    tickers = [t for t in holdings.keys() if t != "CASH"]
    data = yf.download(tickers, period="6mo", interval="1d", group_by="ticker", auto_adjust=True, progress=False)

    total_value = holdings.get("CASH", 0.0)
    daily_change_value = 0.0
    portfolio_history = pd.DataFrame()

    sector_exposure = {}
    industry_exposure = {}
    dividends_total = 0.0
    projected_income = 0.0
    top_gainers = []
    top_losers = []

    # Risk calculation prep
    returns_list = []
    weights = []
    betas = []

    for ticker in tickers:
        stock = yf.Ticker(ticker)
        hist = data[ticker]["Close"] if len(tickers) > 1 else data["Close"]

        qty = holdings[ticker]
        latest_price = hist.iloc[-1]
        prev_price = hist.iloc[-2]

        total_value += latest_price * qty
        daily_change_value += (latest_price - prev_price) * qty

        # Portfolio history
        portfolio_history[ticker] = hist.pct_change().dropna()
        returns_list.append(hist.pct_change().dropna())
        weights.append((latest_price * qty) / total_value)

        # Sector & industry mapping
        info = stock.info
        sector_exposure[info.get("sector", "Unknown")] = sector_exposure.get(info.get("sector", "Unknown"), 0) + latest_price * qty
        industry_exposure[info.get("industry", "Unknown")] = industry_exposure.get(info.get("industry", "Unknown"), 0) + latest_price * qty

        # Dividend & income
        divs = stock.dividends
        if not divs.empty:
            annual_div = divs[-4:].sum() if len(divs) >= 4 else divs.sum()
            projected_income += annual_div * qty
            dividends_total += (annual_div / latest_price) * 100  # yield %

    # Normalize exposures
    for sector in sector_exposure:
        sector_exposure[sector] = round((sector_exposure[sector] / total_value) * 100, 2)
    for industry in industry_exposure:
        industry_exposure[industry] = round((industry_exposure[industry] / total_value) * 100, 2)

    # Risk metrics
    portfolio_returns = portfolio_history.mean(axis=1)
    volatility = np.std(portfolio_returns) * np.sqrt(252)
    sharpe = np.mean(portfolio_returns) / np.std(portfolio_returns) * np.sqrt(252) if np.std(portfolio_returns) != 0 else 0
    sortino = np.mean(portfolio_returns) / np.std(portfolio_returns[portfolio_returns < 0]) * np.sqrt(252) if np.std(portfolio_returns[portfolio_returns < 0]) != 0 else 0
    max_drawdown = (portfolio_history.sum(axis=1).cumsum().cummax() - portfolio_history.sum(axis=1).cumsum()).max()

    # Value at Risk (95%)
    var_95 = np.percentile(portfolio_returns, 5) * total_value

    # Narrative
    narrative = f"Your portfolio is worth ${total_value:,.2f}, with a daily change of ${daily_change_value:,.2f}. "
    narrative += f"Top sector exposure: {max(sector_exposure, key=sector_exposure.get)} ({max(sector_exposure.values()):.2f}%). "
    narrative += f"Annualized volatility is {volatility:.2%}, Sharpe ratio {sharpe:.2f}."

    return {
        "total_value": round(total_value, 2),
        "daily_change": round(daily_change_value, 2),
        "sector_exposure": sector_exposure,
        "industry_exposure": industry_exposure,
        "dividend_yield_avg": round(dividends_total / len(tickers), 2) if tickers else 0,
        "projected_annual_income": round(projected_income, 2),
        "risk_metrics": {
            "volatility": round(volatility, 4),
            "sharpe": round(sharpe, 4),
            "sortino": round(sortino, 4),
            "max_drawdown": round(max_drawdown, 4),
            "value_at_risk_95": round(var_95, 2)
        },
        "narrative": narrative
    }

@mcp.tool()
@tracked_cache
async def forecast_stock(symbol: str, forecast_days: int, p: int, d: int, q: int) -> dict:
    """
    Forecast stock prices using ARIMA.

    Args:
        symbol (str): Stock symbol (e.g., "AAPL").
        forecast_days (int): Number of days to forecast.
        p (int): ARIMA parameter for autoregression.
        d (int): ARIMA parameter for differencing.
        q (int): ARIMA parameter for moving average.
        p (AutoRegressive order): The number of lag observations included in the model. It determines how many past values are used to predict the current value.
        d (Differencing order): The number of times the data needs to be differenced to make it stationary. It accounts for trends in the data.
        q (Moving Average order): The size of the moving average window, which determines how many past forecast errors are used to predict the current value.

    Returns:
        dict: Forecasted prices and metadata.
    """
    try:
        # Fetch historical data
        ticker = yf.Ticker(symbol)
        history = ticker.history(period="1y", interval="1d")
        if history.empty:
            return {"error": f"No historical data available for {symbol}"}

        # Use the 'Close' price for forecasting
        data = history['Close'].dropna()

        # Fit ARIMA model
        model = ARIMA(data, order=(p, d, q))
        fitted_model = model.fit()

        # Generate forecasts
        forecast = fitted_model.get_forecast(steps=forecast_days)
        forecast_index = pd.date_range(start=data.index[-1] + pd.Timedelta(days=1), periods=forecast_days)
        forecast_values = forecast.predicted_mean
        conf_int = forecast.conf_int()

        # Prepare results
        result = {
            "symbol": symbol,
            "forecast": {
                "dates": forecast_index.strftime("%Y-%m-%d").tolist(),
                "prices": forecast_values.tolist(),
                "confidence_intervals": conf_int.values.tolist()
            },
            "model_summary": str(fitted_model.summary()),
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        return result

    except Exception as e:
        return {"error": str(e)}

#The freshness_hours parameter in your method specifies how recent the search results should be, in hours. The Tavily API typically supports values like 1, 3, 6, 12, 24, 48, and 168 (up to 7 days).
# You can set freshness_hours to any of these values to control the recency of the results





@mcp.tool()
@tracked_cache
async def crawl_web_page(query: str, freshness_hours: int = 168) -> dict:
    """
    Crawl a web page or perform a search using the Tavily API.
    Args:
        query (str): The search query or URL to crawl.
        The freshness_hours parameter in your method specifies how recent the search results should be, in hours.
        The Tavily API typically supports values like 1, 3, 6, 12, 24, 48, and 168 (up to 7 days).

    Returns:
        dict: The search results or extracted content.
    """
    logging.debug(f"**************crawl_web_page called with: {query}")
    logging.debug(f"***************Cache stats - Hits: {tracked_cache.hits}, Misses: {tracked_cache.misses}")
    logging.debug(f"═══════════════════════════════════════════════════")
    logging.debug(f"crawl_web_page called with: '{query}'")
    logging.debug(f"Type of query: {type(query)}, Value: '{query}'")
    logging.debug(f"Cache stats - Hits: {tracked_cache.hits}, Misses: {tracked_cache.misses}")
    logging.debug(f"Current cache size: {len(price_cache)}")
    logging.debug(f"Cache keys: {list(price_cache.keys())}")

    logging.debug(f"═══════════════════════════════════════════════════")
    try:
        #search = TavilySearchResults(max_results=8)
        tavily_api_key = os.getenv('TAVILY_API_KEY')
        if not tavily_api_key:
            logging.warning("TAVILY_API_KEY not found in environment, using fallback key (NOT RECOMMENDED)")
            tavily_api_key = "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"  #

        print("value of tavily_api_key:", tavily_api_key)
        #logging.debug(f"API keys: ", tavily_api_key)
        search = TavilySearchResults(tavily_api_key=tavily_api_key, max_results=5)
        result = search.invoke({
            "query": query,
            "freshness": f"{freshness_hours}h"
        })
        # Always return a dict
        if isinstance(result, dict):
            return result
        elif isinstance(result, list):
            return {"results": result}
        else:
            return {"error": "Unexpected API response type", "raw_result": str(result)}
    except Exception as e:
        return {"error": str(e)}


import pandas as pd
import requests


@mcp.tool()
@tracked_cache
async def get_fred_macro_data(series_id: str = "GDP", observation_start: str = "2020-01-01") -> dict:
    """
    Get macroeconomic data from FRED API.

    Common series IDs:
    - GDP: 'GDP'
    - Unemployment: 'UNRATE'
    - CPI: 'CPIAUCSL'
    - Interest Rates: 'FEDFUNDS'
    - 10-Year Treasury: 'DGS10'
    - Nonfarm Payrolls: 'PAYEMS'

    Args:
        series_id (str): FRED series identifier (default: 'GDP')
        observation_start (str): Start date in YYYY-MM-DD format (default: '2020-01-01')
    """
    api_key = os.getenv('FRED_API_KEY')
    if not api_key:
        return {
            "error": "FRED_API_KEY not found in environment variables. Get a free key from: https://fred.stlouisfed.org/docs/api/api_key.html"}

    base_url = "https://api.stlouisfed.org/fred/series/observations"

    # Validate series_id
    if not series_id or len(series_id) > 25:
        return {"error": "Invalid series_id. Must be 25 or fewer alphanumeric characters."}

    params = {
        'series_id': series_id,
        'api_key': api_key,
        'file_type': 'json',
        'observation_start': observation_start
    }

    try:
        response = requests.get(base_url, params=params)

        if response.status_code != 200:
            return {
                "error": f"FRED API returned status {response.status_code}",
                "details": response.text
            }

        data = response.json()

        # Check for FRED API errors
        if 'error_code' in data:
            return {
                "error": f"FRED API Error {data.get('error_code')}",
                "message": data.get('error_message')
            }

        # Extract observations
        if 'observations' in data:
            observations = data['observations']
            if not observations:
                return {"error": f"No data found for series_id: {series_id}"}

            # Filter out periods with no data (. values)
            valid_observations = [obs for obs in observations if obs.get('value') != '.']

            if not valid_observations:
                return {"error": f"No valid data points found for series_id: {series_id}"}

            latest_obs = valid_observations[-1]

            return {
                "series_id": series_id,
                "series_name": f"FRED Data for {series_id}",
                "latest_value": float(latest_obs['value']) if latest_obs['value'] else None,
                "latest_date": latest_obs['date'],
                "total_observations": len(valid_observations),
                "data_range": {
                    "start_date": valid_observations[0]['date'],
                    "end_date": latest_obs['date']
                },
                "observations_sample": valid_observations[:3]  # First 3 data points
            }
        else:
            return {"error": "Unexpected response format from FRED API", "raw_response": data}

    except Exception as e:
        return {"error": f"FRED API request failed: {str(e)}"}


# @mcp.tool()
# @tracked_cache
# async def get_international_macro_data(country: str = "US", indicator: str = "GDP") -> dict:
#     """
#     Get macroeconomic data for various countries including India and Singapore.
#
#     Args:
#         country: US, IN (India), SG (Singapore), CN, JP, etc.
#         indicator: GDP, CPI, UNRATE, INTEREST_RATE, etc.
#     """
#
#     # Country to FRED series ID mapping
#     country_series_map = {
#         "US": {
#             "GDP": "GDP",
#             "CPI": "CPIAUCSL",
#             "UNEMPLOYMENT": "UNRATE",
#             "INTEREST_RATE": "FEDFUNDS",
#             "INFLATION": "CPALTT01USM657N"
#         },
#         "IN": {  # India
#             "GDP": "MKTGDPINA646NWDB",  # GDP current USD
#             "CPI": "DDOI12INA156NWDB",  # Consumer Price Index
#             "INTEREST_RATE": "FRINRIDM",  # Interest Rate
#             "INFLATION": "FPCPITOTLZGIND"  # Inflation
#         },
#         "SG": {  # Singapore
#             "GDP": "MKTGDPSGA646NWDB",  # GDP current USD
#             "CPI": "DDOI12SGA156NWDB",  # Consumer Price Index
#             "INTEREST_RATE": "FRINRSDM",  # Interest Rate
#             "INFLATION": "FPCPITOTLZGSGP"  # Inflation
#         }
#     }
#
#     if country not in country_series_map:
#         return {"error": f"Country {country} not supported. Available: {list(country_series_map.keys())}"}
#
#     if indicator not in country_series_map[country]:
#         return {
#             "error": f"Indicator {indicator} not available for {country}. Available: {list(country_series_map[country].keys())}"}
#
#     series_id = country_series_map[country][indicator]
#     return await get_fred_macro_data(series_id)

#world bank API


@mcp.tool()
@tracked_cache
async def get_international_macro_data(country_code: str = "US", indicator: str = "GDP") -> dict:
    """Get international data using World Bank API (more reliable)"""

    country_map = {
        "US": "United States",
        "IN": "India",
        "SG": "Singapore",
        "CN": "China",
        "JP": "Japan"
    }

    indicator_map = {
        "GDP": "NY.GDP.MKTP.CD",  # GDP (current US$)
        "GDP_GROWTH": "NY.GDP.MKTP.KD.ZG",  # GDP growth (annual %)
        "INFLATION": "FP.CPI.TOTL.ZG",  # Inflation, consumer prices
        "CPI": "FP.CPI.TOTL",  # Consumer Price Index
        "UNEMPLOYMENT": "SL.UEM.TOTL.ZS"  # Unemployment rate
    }

    if country_code not in country_map:
        return {"error": f"Country code {country_code} not supported"}

    if indicator not in indicator_map:
        return {"error": f"Indicator {indicator} not supported"}

    indicator_code = indicator_map[indicator]
    url = f"http://api.worldbank.org/v2/country/{country_code}/indicator/{indicator_code}"

    params = {
        'format': 'json',
        'per_page': '10',
        'date': '2010:2024'
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()

        if isinstance(data, list) and len(data) > 1:
            observations = data[1]
            if observations:
                latest_data = next((obs for obs in observations if obs['value'] is not None), None)

                if latest_data:
                    return {
                        "country": country_map[country_code],
                        "indicator": indicator,
                        "latest_value": latest_data['value'],
                        "year": latest_data['date'],
                        "unit": "Various units",
                        "source": "World Bank",
                        "data_points": len([obs for obs in observations if obs['value'] is not None])
                    }

        return {"error": f"No data available for {country_map[country_code]} {indicator}"}

    except Exception as e:
        return {"error": f"World Bank API request failed: {str(e)}"}

# Internal, non-tool function for statistics logic
def _get_cache_statistics_logic() -> Dict[str, Any]:
    """Shared logic for getting cache statistics."""
    total_requests = tracked_cache.hits + tracked_cache.misses
    hit_ratio = tracked_cache.hits / total_requests if total_requests > 0 else 0

    return {
        "hits": tracked_cache.hits,
        "misses": tracked_cache.misses,
        "total_requests": total_requests,
        "hit_ratio": f"{hit_ratio:.2%}",
        "max_size": price_cache.maxsize,
        "current_size": len(price_cache),
        "ttl_seconds": price_cache.ttl,
        "last_reset_seconds_ago": time.time() - tracked_cache._last_reset,
        "performance": "Excellent" if hit_ratio > 0.7 else "Good" if hit_ratio > 0.4 else "Needs improvement"
    }

@mcp.tool()
async def get_cache_stats() -> Dict[str, Any]:
    """Retrieve statistics about the price cache."""
    return _get_cache_statistics_logic()


@mcp.tool()
async def view_cache_records() -> dict:
    """
    Inspect the current records stored in the cache.
    Returns a dictionary of cache keys and their corresponding values,
    along with cache metadata.
    """
    records = []
    try:
        # The `items()` method is delegated to the underlying TTLCache
        for key, value in tracked_cache.items():
            # The key is a tuple from hashkey, e.g., ('function_name', 'arg1', ...)
            tool_name = "unknown"
            if isinstance(key, tuple) and len(key) > 0 and isinstance(key[0], str):
                tool_name = key[0]
                # Represent args/kwargs part of the key as a string
                key_args = str(key[1:])
            else:
                key_args = str(key)

            record_entry = {
                "tool_name": tool_name,
                "cache_key_args": key_args
            }

            # Handle pandas DataFrame serialization
            if isinstance(value, pd.DataFrame):
                record_entry["value_type"] = "DataFrame"
                record_entry["value"] = value.head().to_dict(orient='records')
                record_entry["value_preview"] = f"DataFrame with {len(value)} rows"
            # Handle other basic JSON-serializable types
            elif isinstance(value, (dict, list, str, int, float, bool)) or value is None:
                record_entry["value_type"] = str(type(value).__name__)
                record_entry["value"] = value
            # For any other non-serializable types, provide a string representation
            else:
                record_entry["value_type"] = str(type(value).__name__)
                record_entry["value"] = f"Non-serializable object: {str(value)[:100]}..."

            records.append(record_entry)

        return {
            "cache_records": records,
            "current_size": tracked_cache.currsize,
            "max_size": tracked_cache.maxsize,
            "ttl_seconds": tracked_cache.ttl
        }
    except Exception as e:
        logging.error(f"Error viewing cache records: {e}")
        return {"error": f"Failed to retrieve cache records: {str(e)}"}

@mcp.tool()
async def reset_cache() -> Dict[str, Any]:
    """Clear the price cache and reset statistics"""
    price_cache.clear()
    tracked_cache.hits = 0
    tracked_cache.misses = 0
    tracked_cache._last_reset = time.time()

    return {
        "message": "Cache cleared successfully",
        "new_stats": _get_cache_statistics_logic()
    }



#hit curl http://127.0.0.1:8001/health
#to check health check
@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> PlainTextResponse:
    return PlainTextResponse("OK")

# Create and mount the HTTP app
app = mcp.http_app()  # Use the MCP HTTP app directly instead of mounting


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8001,
        log_level="debug"  # Set log level to DEBUG for detailed output
    )