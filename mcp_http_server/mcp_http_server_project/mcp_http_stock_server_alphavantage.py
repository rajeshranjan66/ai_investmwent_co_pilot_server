from typing import Dict
import aiohttp
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastmcp import FastMCP
import requests
from requests.exceptions import Timeout, RequestException
from pydantic import BaseModel, Field
import uvicorn
import logging
import os
load_dotenv()

# Initialize logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize FastAPI app
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize FastMCP
mcp = FastMCP(name="AlphaVantageHTTPMCPServer",)

API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY')
BASE_URL = 'https://www.alphavantage.co/query'

class StockResponse(BaseModel):
    symbol: str
    data: Dict

@mcp.tool()
async def get_stock_data(symbol: str) -> dict:
    """
    Fetch stock data from Alpha Vantage API with timeout handling.

    :param symbol: Stock symbol (e.g., 'AAPL' for Apple)
    :return: JSON response containing stock data
    """


    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    #
    # API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY')
    # BASE_URL = 'https://www.alphavantage.co/query'

    # Set reasonable timeout values
    CONNECT_TIMEOUT = 5  # seconds for initial connection
    READ_TIMEOUT = 15  # seconds for reading response

    params = {
        'function': 'TIME_SERIES_DAILY',  # Adjusted daily time series
        'symbol': symbol,
        'apikey': API_KEY
    }

    try:
        # Add timeout parameters to the request
        response = requests.get(
            BASE_URL,
            params=params,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT)
        )

        logger.debug(f"Request URL: {response.url}")
        logger.debug(f"Response status code: {response.status_code}")
        logger.debug(f"Raw response: {response.text[:200]}...")  # Log first 200 chars

        response.raise_for_status()
        return response.json()

    except Timeout:
        logger.error("Request timed out while accessing Alpha Vantage API")
        return {
            "error": "Request timed out",
            "details": "The API request took too long to complete"
        }

    except RequestException as e:
        logger.error(f"Request failed: {str(e)}")
        return {
            "error": "Request failed",
            "details": str(e)
        }

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {
            "error": "Unexpected error",
            "details": str(e)
        }

@mcp.tool()
async def get_latest_stock_price(symbol: str) -> dict:
        """
        Fetch stock data from Alpha Vantage API with timeout handling.

        :param symbol: Stock symbol (e.g., 'AAPL' for Apple)
        :return: JSON response containing stock data
        """

        logging.basicConfig(level=logging.DEBUG)
        logger = logging.getLogger(__name__)
        #
        # API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY')
        # BASE_URL = 'https://www.alphavantage.co/query'

        # Set reasonable timeout values
        CONNECT_TIMEOUT = 5  # seconds for initial connection
        READ_TIMEOUT = 15  # seconds for reading response

        params = {
            'function': 'GLOBAL_QUOTE',  # Adjusted daily time series
            'symbol': symbol,
            'apikey': API_KEY
        }

        try:
            # Add timeout parameters to the request
            response = requests.get(
                BASE_URL,
                params=params,
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT)
            )

            logger.debug(f"Request URL: {response.url}")
            logger.debug(f"Response status code: {response.status_code}")
            logger.debug(f"Raw response: {response.text[:200]}...")  # Log first 200 chars

            response.raise_for_status()
            return response.json()

        except Timeout:
            logger.error("Request timed out while accessing Alpha Vantage API")
            return {
                "error": "Request timed out",
                "details": "The API request took too long to complete"
            }

        except RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            return {
                "error": "Request failed",
                "details": str(e)
            }

        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return {
                "error": "Unexpected error",
                "details": str(e)
            }

@mcp.tool()
async def get_forex_data(request: dict) -> StockResponse:
    """
    Fetch forex (currency exchange) data from Alpha Vantage.
    Args:
        request: Dictionary containing:
            from_currency: From Currency Symbol (e.g., 'USD')
            to_currency: To Currency Symbol (e.g., 'EUR')
            function: Optional - Type of forex data (default: FX_DAILY)
    Returns:
        StockResponse containing forex data
    Example:
        {
            "from_currency": "USD",
            "to_currency": "EUR",
            "function": "FX_DAILY"
        }
    """
    params = {
        "function": "FX_DAILY",  # Fixed function for daily forex data
        "from_symbol": request["from_currency"],
        "to_symbol": request["to_currency"],
        "apikey": API_KEY
    }

    logging.debug(f"Request params: {params}")

    async with aiohttp.ClientSession() as session:
        async with session.get(BASE_URL, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return StockResponse(symbol=f"{request['from_currency']}/{request['to_currency']}", data=data)
            raise Exception(f"API request failed with status {response.status}")


@mcp.tool()
async def get_crypto_data(request: dict) -> StockResponse:
    """
    Fetch cryptocurrency data from Alpha Vantage.
    Args:
        request: Dictionary containing:
            symbol: Crypto Symbol (e.g., 'BTC')
            market: Market Currency (e.g., 'USD')
            function: Optional - Type of crypto data (default: DIGITAL_CURRENCY_DAILY)
    Returns:
        StockResponse containing crypto data
    Example:
        {
            "symbol": "BTC",
            "market": "USD",
            "function": "DIGITAL_CURRENCY_DAILY"
        }
    """
    params = {
        "function": request.get("function", "DIGITAL_CURRENCY_DAILY"),
        "symbol": request["symbol"],
        "market": request["market"],
        "apikey": API_KEY
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(BASE_URL, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return StockResponse(symbol=f"{request['symbol']}/{request['market']}", data=data)
            raise Exception(f"API request failed with status {response.status}")


@mcp.tool()
async def get_technical_indicator(request: dict) -> StockResponse:
    """
    Fetch technical indicators for a symbol from Alpha Vantage.
    Args:
        request: Dictionary containing:
            symbol: Stock Symbol (e.g., 'AAPL')
            function: Technical Indicator (e.g., 'SMA', 'EMA', 'RSI')
            interval: Time interval (e.g., 'daily', '60min', '15min')
            time_period: Number of data points (e.g., 60, 200)
            series_type: Price type (e.g., 'close', 'open', 'high', 'low')
    Returns:
        StockResponse containing technical indicator data
    Example:
        {
            "symbol": "AAPL",
            "function": "SMA",
            "interval": "daily",
            "time_period": 60,
            "series_type": "close"
        }
    """
    params = {
        "function": request["function"],
        "symbol": request["symbol"],
        "interval": request["interval"],
        "time_period": request["time_period"],
        "series_type": request["series_type"],
        "apikey": API_KEY
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(BASE_URL, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return StockResponse(symbol=request["symbol"], data=data)
            raise Exception(f"API request failed with status {response.status}")


@mcp.tool()
async def get_company_overview(symbol: str) -> StockResponse:
    """
    Fetch company overview data from Alpha Vantage.
    Args:
        symbol: Stock Symbol (e.g., 'AAPL')
    Returns:
        StockResponse containing company overview data
    Example:
        "AAPL"
    """
    params = {
        "function": "OVERVIEW",
        "symbol": symbol,
        "apikey": API_KEY
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(BASE_URL, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return StockResponse(symbol=symbol, data=data)
            raise Exception(f"API request failed with status {response.status}")


@mcp.tool()
async def get_earnings(symbol: str) -> StockResponse:
    """
    Fetch company earnings data from Alpha Vantage.
    Args:
        symbol: Stock Symbol (e.g., 'AAPL')
    Returns:
        StockResponse containing earnings data
    Example:
        "AAPL"
    """
    params = {
        "function": "EARNINGS",
        "symbol": symbol,
        "apikey": API_KEY
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(BASE_URL, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return StockResponse(symbol=symbol, data=data)
            raise Exception(f"API request failed with status {response.status}")


@mcp.tool()
async def search_symbols(keywords: str) -> StockResponse:
    """
    Search for symbols using keywords.
    Args:
        keywords: Search keywords (e.g., 'apple')
    Returns:
        StockResponse containing search results
    Example:
        "apple"
    """
    params = {
        "function": "SYMBOL_SEARCH",
        "keywords": keywords,
        "apikey": API_KEY
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(BASE_URL, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return StockResponse(symbol=keywords, data=data)
            raise Exception(f"API request failed with status {response.status}")


class NewsRequestModel(BaseModel):
    tickers: str = Field(default="AAPL", description="Comma-separated stock symbols")
    topics: str = Field(default="earnings", description="Comma-separated topics")

@mcp.tool()
async def get_news_sentiment(request: dict) -> StockResponse:
        """Use this tool to get news and sentiment analysis for stocks.
        Parameters:
        - tickers: Comma-separated stock symbols (e.g., 'AAPL,MSFT')
        - topics: Comma-separated topics (e.g., 'earnings,technology')""",
        params = {
            "function": "NEWS_SENTIMENT",
            "apikey": API_KEY,
            "tickers": request.tickers,
            "topics": request.topics
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(BASE_URL, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return StockResponse(symbol="NEWS", data=data)
                raise Exception(f"API request failed with status {response.status}")


# async def get_news_sentiment(request: dict) -> StockResponse:
#     """Use this tool to get news and sentiment analysis for stocks.
#         You MUST provide a dictionary with at least one of these parameters:
#         - 'tickers': a string of comma-separated stock symbols (e.g., 'AAPL,MSFT')
#         - 'topics': a string of comma-separated topics (e.g., 'earnings,technology')
#         Example: {'tickers': 'AAPL,MSFT'} or {'topics': 'earnings'} or {'tickers': 'AAPL', 'topics': 'earnings'}"""
#     params = {
#         "function": "NEWS_SENTIMENT",
#         "apikey": API_KEY
#     }
#
#     if "tickers" in request:
#         params["tickers"] = request["tickers"]
#     if "topics" in request:
#         params["topics"] = request["topics"]
#
#     async with aiohttp.ClientSession() as session:
#         async with session.get(BASE_URL, params=params) as response:
#             if response.status == 200:
#                 data = await response.json()
#                 return StockResponse(symbol="NEWS", data=data)
#             raise Exception(f"API request failed with status {response.status}")

@mcp.tool()
async def get_macd(request: dict) -> StockResponse:
    """
    Fetch MACD (Moving Average Convergence/Divergence) indicator.
    Args:
        request: Dictionary containing:
            symbol: Stock Symbol (e.g., 'AAPL')
            interval: Time interval (e.g., 'daily', '60min', '15min')
            series_type: Price type (e.g., 'close', 'open')
    Returns:
        StockResponse containing MACD data
    Example:
        {
            "symbol": "AAPL",
            "interval": "daily",
            "series_type": "close"
        }
    """
    params = {
        "function": "MACD",
        "symbol": request["symbol"],
        "interval": request["interval"],
        "series_type": request["series_type"],
        "apikey": API_KEY
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(BASE_URL, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return StockResponse(symbol=request["symbol"], data=data)
            raise Exception(f"API request failed with status {response.status}")


@mcp.tool()
async def get_bbands(request: dict) -> StockResponse:
    """
    Fetch Bollinger Bands indicator.
    Args:
        request: Dictionary containing:
            symbol: Stock Symbol (e.g., 'AAPL')
            interval: Time interval (e.g., 'daily', '60min')
            time_period: Number of data points (default: 20)
            series_type: Price type (e.g., 'close', 'open')
    Returns:
        StockResponse containing Bollinger Bands data
    Example:
        {
            "symbol": "AAPL",
            "interval": "daily",
            "time_period": 20,
            "series_type": "close"
        }
    """
    params = {
        "function": "BBANDS",
        "symbol": request["symbol"],
        "interval": request["interval"],
        "time_period": request.get("time_period", 20),
        "series_type": request["series_type"],
        "apikey": API_KEY
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(BASE_URL, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return StockResponse(symbol=request["symbol"], data=data)
            raise Exception(f"API request failed with status {response.status}")


@mcp.tool()
async def get_income_statement(symbol: str) -> StockResponse:
    """
    Fetch company income statement from Alpha Vantage.
    Args:
        symbol: Stock Symbol (e.g., 'AAPL')
    Returns:
        StockResponse containing income statement data
    Example:
        "AAPL"
    """
    params = {
        "function": "INCOME_STATEMENT",
        "symbol": symbol,
        "apikey": API_KEY
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(BASE_URL, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return StockResponse(symbol=symbol, data=data)
            raise Exception(f"API request failed with status {response.status}")


@mcp.tool()
async def get_balance_sheet(symbol: str) -> StockResponse:
    """
    Fetch company balance sheet from Alpha Vantage.
    Args:
        symbol: Stock Symbol (e.g., 'AAPL')
    Returns:
        StockResponse containing balance sheet data
    Example:
        "AAPL"
    """
    params = {
        "function": "BALANCE_SHEET",
        "symbol": symbol,
        "apikey": API_KEY
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(BASE_URL, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return StockResponse(symbol=symbol, data=data)
            raise Exception(f"API request failed with status {response.status}")


@mcp.tool()
async def get_cash_flow(symbol: str) -> StockResponse:
    """
    Fetch company cash flow statement from Alpha Vantage.
    Args:
        symbol: Stock Symbol (e.g., 'AAPL')
    Returns:
        StockResponse containing cash flow data
    Example:
        "AAPL"
    """
    params = {
        "function": "CASH_FLOW",
        "symbol": symbol,
        "apikey": API_KEY
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(BASE_URL, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return StockResponse(symbol=symbol, data=data)
            raise Exception(f"API request failed with status {response.status}")


@mcp.tool()
async def get_gdp(request: dict) -> StockResponse:
    """
    Fetch real GDP data from Alpha Vantage.
    Args:
        request: Dictionary containing:
            interval: 'annual' or 'quarterly'
    Returns:
        StockResponse containing GDP data
    Example:
        {
            "interval": "quarterly"
        }
    """
    params = {
        "function": "REAL_GDP",
        "interval": request.get("interval", "quarterly"),
        "apikey": API_KEY
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(BASE_URL, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return StockResponse(symbol=f"GDP_{request.get('interval')}", data=data)
            raise Exception(f"API request failed with status {response.status}")


@mcp.tool()
async def get_inflation(request: dict) -> StockResponse:
    """
    Fetch inflation data from Alpha Vantage.
    Args:
        request: Dictionary containing:
            datatype: Optional - 'json' or 'csv' (default: json)
    Returns:
        StockResponse containing inflation data
    Example:
        {
            "datatype": "json"
        }
    """
    params = {
        "function": "INFLATION",
        "datatype": request.get("datatype", "json"),
        "apikey": API_KEY
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(BASE_URL, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return StockResponse(symbol="INFLATION", data=data)
            raise Exception(f"API request failed with status {response.status}")


from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import PlainTextResponse

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
        port=8002,
        log_level="debug"  # Set log level to DEBUG for detailed output
    )
