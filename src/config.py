import os

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")

WATCHLIST = {
    "stocks": ["AAPL", "TSLA", "NVDA", "MSFT", "SPY", "AMZN"],
    "crypto": ["BINANCE:BTCUSDT", "BINANCE:ETHUSDT"],
}

REPORT_DIR = "reports"

# Sentiment thresholds
BULLISH_THRESHOLD = 0.15
BEARISH_THRESHOLD = -0.15

# Max news articles to fetch per asset
NEWS_LIMIT = 10
