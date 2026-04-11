import time
import datetime
import finnhub
from config import FINNHUB_API_KEY, NEWS_LIMIT


client = finnhub.Client(api_key=FINNHUB_API_KEY)


def _rate_limit():
    """Brief pause to stay within Finnhub's 60 req/min free tier."""
    time.sleep(1.1)


def get_quote(symbol: str) -> dict | None:
    """
    Returns price data for a stock or crypto symbol.
    For crypto, symbol should be like 'BINANCE:BTCUSDT'.
    Returns dict with keys: price, change_pct, high, low, open, prev_close
    or None on error.
    """
    try:
        q = client.quote(symbol)
        _rate_limit()
        if q.get("c", 0) == 0:
            return None
        return {
            "symbol": symbol,
            "price": q["c"],
            "change_pct": round(((q["c"] - q["pc"]) / q["pc"]) * 100, 2) if q["pc"] else 0,
            "high": q["h"],
            "low": q["l"],
            "open": q["o"],
            "prev_close": q["pc"],
        }
    except Exception as e:
        print(f"[data_fetcher] Error fetching quote for {symbol}: {e}")
        return None


def get_stock_news(symbol: str) -> list[dict]:
    """
    Returns recent news articles for a stock symbol.
    Each item has: headline, source, url, sentiment_score (if available).
    """
    today = datetime.date.today()
    week_ago = today - datetime.timedelta(days=7)
    try:
        news = client.company_news(symbol, _from=str(week_ago), to=str(today))
        _rate_limit()
        return [
            {
                "headline": a.get("headline", ""),
                "source": a.get("source", ""),
                "url": a.get("url", ""),
            }
            for a in (news or [])[:NEWS_LIMIT]
        ]
    except Exception as e:
        print(f"[data_fetcher] Error fetching news for {symbol}: {e}")
        return []


def get_market_news() -> list[dict]:
    """Returns general market news headlines."""
    try:
        news = client.general_news("general", min_id=0)
        _rate_limit()
        return [
            {
                "headline": a.get("headline", ""),
                "source": a.get("source", ""),
                "url": a.get("url", ""),
            }
            for a in (news or [])[:NEWS_LIMIT]
        ]
    except Exception as e:
        print(f"[data_fetcher] Error fetching market news: {e}")
        return []
