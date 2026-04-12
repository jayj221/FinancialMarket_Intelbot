import os

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
FRED_API_KEY = os.getenv("FRED_API_KEY", "")

WATCHLIST = ["AAPL", "TSLA", "NVDA", "MSFT", "SPY", "AMZN", "META", "GOOGL"]

FINBERT_MODEL = "ProsusAI/finbert"

REPORT_DIR = "reports"

SENTIMENT_RECENT_WEIGHT = 2.0
NEWS_LOOKBACK_DAYS = 2
NEWS_LIMIT_PER_ASSET = 15

COMPOSITE_WEIGHTS = {
    "sentiment": 0.25,
    "fundamentals": 0.30,
    "technical": 0.25,
    "macro": 0.20,
}
