# AI Investment Co-Pilot HTTP Servers

Developer-focused overview of the MCP (Model Context Protocol) HTTP servers that expose stock, macroeconomic, and web-search tools over FastAPI.

## Repository layout
- `mcp_http_server/`: Python source, Docker assets, and dependency pins for the HTTP servers.
- `mcp_http_server/mcp_http_server_project/`: Primary application code (YFinance-backed MCP server, Alpha Vantage MCP server, Docker assets).

## Architecture and code flow
### YFinance MCP HTTP server
- `mcp_stock_server_http_yfinance.py` wraps a `FastMCP` instance to register many `@mcp.tool` functions and exposes them through `app = mcp.http_app()` so Uvicorn can serve them over HTTP.【F:mcp_http_server/mcp_http_server_project/mcp_stock_server_http_yfinance.py†L122-L219】【F:mcp_http_server/mcp_http_server_project/mcp_stock_server_http_yfinance.py†L1768-L1790】
- A `CacheWithStats` decorator wraps a 30-minute TTL cache to memoize tool responses and track hit/miss ratios; cache introspection tools (`get_cache_stats`, `view_cache_records`, `reset_cache`) are also exposed via MCP.【F:mcp_http_server/mcp_http_server_project/mcp_stock_server_http_yfinance.py†L33-L102】【F:mcp_http_server/mcp_http_server_project/mcp_stock_server_http_yfinance.py†L1680-L1764】
- Core tool categories include:
  - **Company fundamentals**: `fetch_stock_info` assembles company metadata, valuation metrics, and market data from `yfinance.Ticker` APIs.【F:mcp_http_server/mcp_http_server_project/mcp_stock_server_http_yfinance.py†L129-L219】
  - **Financial statements**: `fetch_quarterly_financials` and `fetch_annual_financials` join income, balance sheet, and cashflow data and compute ratios/growth metrics for each period.【F:mcp_http_server/mcp_http_server_project/mcp_stock_server_http_yfinance.py†L231-L332】【F:mcp_http_server/mcp_http_server_project/mcp_stock_server_http_yfinance.py†L335-L420】
  - **Events and payouts**: tools fetch dividends, corporate actions, earnings history, and corporate calendar information for scheduling-aware clients.【F:mcp_http_server/mcp_http_server_project/mcp_stock_server_http_yfinance.py†L803-L858】【F:mcp_http_server/mcp_http_server_project/mcp_stock_server_http_yfinance.py†L1156-L1185】
  - **Market data and indicators**: price quotes, history, technical indicators, and ARIMA-based forecasts operate on YFinance price series (see `get_stock_price`, `get_stock_history`, `fetch_technical_indicators`, `forecast_stock`, etc.).【F:mcp_http_server/mcp_http_server_project/mcp_stock_server_http_yfinance.py†L445-L716】
  - **Search and macro data**: `crawl_web_page` integrates the Tavily API, while `get_fred_macro_data` and `get_international_macro_data` fetch macroeconomic series from FRED and other sources using API keys read from the environment.【F:mcp_http_server/mcp_http_server_project/mcp_stock_server_http_yfinance.py†L1431-L1508】
- A custom `/health` route is registered for uptime checks, mirroring the Uvicorn entrypoint at port 8001 by default.【F:mcp_http_server/mcp_http_server_project/mcp_stock_server_http_yfinance.py†L1768-L1790】

### Alpha Vantage MCP HTTP server
- `mcp_http_stock_server_alphavantage.py` provides an alternate MCP server that proxies Alpha Vantage endpoints for equities, FX, crypto, and technical indicators, again exposing `app = mcp.http_app()` for HTTP serving.【F:mcp_http_server/mcp_http_server_project/mcp_http_stock_server_alphavantage.py†L1-L160】【F:mcp_http_server/mcp_http_server_project/mcp_http_stock_server_alphavantage.py†L200-L260】【F:mcp_http_server/mcp_http_server_project/mcp_http_stock_server_alphavantage.py†L595-L623】
- Tools enforce timeouts and structured error handling around Alpha Vantage responses and share the same `/health` check pattern as the YFinance server.【F:mcp_http_server/mcp_http_server_project/mcp_http_stock_server_alphavantage.py†L40-L160】【F:mcp_http_server/mcp_http_server_project/mcp_http_stock_server_alphavantage.py†L599-L623】

## Environment and dependencies
- Python 3.10+ with dependencies in `mcp_http_server_project/requirements.txt` (FastAPI, FastMCP, yfinance, statsmodels, cachetools, LangChain community integrations, etc.).【F:mcp_http_server/mcp_http_server_project/requirements.txt†L1-L61】
- Required environment variables for full functionality:
  - `ALPHA_VANTAGE_API_KEY` for Alpha Vantage tools.【F:mcp_http_server/mcp_http_server_project/mcp_http_stock_server_alphavantage.py†L33-L64】
  - `TAVILY_API_KEY` for web search; the code falls back to a hardcoded dev key but recommends setting your own.【F:mcp_http_server/mcp_http_server_project/mcp_stock_server_http_yfinance.py†L1453-L1476】
  - `FRED_API_KEY` for FRED macroeconomic data access.【F:mcp_http_server/mcp_http_server_project/mcp_stock_server_http_yfinance.py†L1483-L1505】

## Running locally
1. Create a virtual environment and install dependencies:
   ```bash
   cd mcp_http_server/mcp_http_server_project
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Export any needed API keys (see above) in your shell or a `.env` file.
3. Start the YFinance HTTP MCP server (port 8001 by default):
   ```bash
   uvicorn mcp_stock_server_http_yfinance:app --host 0.0.0.0 --port 8001 --log-level debug
   ```
4. Start the Alpha Vantage HTTP MCP server (port 8002 by default):
   ```bash
   uvicorn mcp_http_stock_server_alphavantage:app --host 0.0.0.0 --port 8002 --log-level debug
   ```

Each server exposes its MCP tools via the HTTP interface provided by FastMCP; a quick health probe is available at `/health` on the corresponding port.

## Docker usage
- The project includes a Dockerfile that installs dependencies and runs the YFinance server on port 8001.【F:mcp_http_server/mcp_http_server_project/Dockerfile†L1-L24】
- `docker-compose.yml` builds the same image and maps container ports, but currently targets port 8000 in the health check and port mapping; adjust to `8001:8001` if you keep the default Uvicorn port from the Dockerfile.【F:mcp_http_server/mcp_http_server_project/docker-compose.yml†L1-L26】【F:mcp_http_server/mcp_http_server_project/Dockerfile†L18-L24】

## Development tips
- Use the cache tooling (`get_cache_stats`, `view_cache_records`, `reset_cache`) to observe or flush the TTL cache during iterative testing.【F:mcp_http_server/mcp_http_server_project/mcp_stock_server_http_yfinance.py†L1680-L1764】
- When adding new tools, decorate async/sync functions with `@mcp.tool()` and rely on the shared `tracked_cache` if responses benefit from memoization.【F:mcp_http_server/mcp_http_server_project/mcp_stock_server_http_yfinance.py†L33-L219】【F:mcp_http_server/mcp_http_server_project/mcp_stock_server_http_yfinance.py†L1680-L1764】
- Keep API keys out of the codebase by relying on environment variables or a `.env` file consumed by `python-dotenv` at import time.【F:mcp_http_server/mcp_http_server_project/mcp_stock_server_http_yfinance.py†L20-L33】【F:mcp_http_server/mcp_http_server_project/mcp_http_stock_server_alphavantage.py†L1-L34】
