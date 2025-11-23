FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY .env .env

COPY . .

# Add healthcheck directly in Dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/tools/health_check || exit 1

# Use a shell form to ensure proper signal handling
#mcp_stock_server_http_yfinance name of file without .py
CMD uvicorn mcp_stock_server_http_yfinance:app --host 0.0.0.0 --port 8001 --log-level debug
