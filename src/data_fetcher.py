import time
import datetime
import finnhub
import yfinance as yf
from config import FINNHUB_API_KEY, NEWS_LOOKBACK_DAYS, NEWS_LIMIT_PER_ASSET

_client = finnhub.Client(api_key=FINNHUB_API_KEY)


def _rl():
    time.sleep(1.1)


def get_quote(symbol: str) -> dict | None:
    try:
        q = _client.quote(symbol)
        _rl()
        if not q or q.get("c", 0) == 0:
            return None
        return {
            "symbol": symbol,
            "price": q["c"],
            "change_pct": round(((q["c"] - q["pc"]) / q["pc"]) * 100, 2) if q["pc"] else 0.0,
            "high": q["h"],
            "low": q["l"],
            "open": q["o"],
            "prev_close": q["pc"],
        }
    except Exception as e:
        print(f"[data_fetcher] quote error {symbol}: {e}")
        return None


def get_ohlcv(symbol: str, days: int = 200) -> "pd.DataFrame | None":
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=f"{days}d")
        if df.empty or len(df) < 50:
            return None
        if hasattr(df.index, "tz") and df.index.tz is not None:
            df.index = df.index.tz_convert(None)
        return df[["Open", "High", "Low", "Close", "Volume"]].rename(
            columns=str.lower
        )
    except Exception as e:
        print(f"[data_fetcher] ohlcv error {symbol}: {e}")
        return None


def get_stock_news(symbol: str) -> list[dict]:
    today = datetime.date.today()
    from_date = today - datetime.timedelta(days=NEWS_LOOKBACK_DAYS)
    try:
        news = _client.company_news(symbol, _from=str(from_date), to=str(today))
        _rl()
        return (news or [])[:NEWS_LIMIT_PER_ASSET]
    except Exception as e:
        print(f"[data_fetcher] news error {symbol}: {e}")
        return []


def get_analyst_data(symbol: str) -> dict:
    out = {"recommendations": [], "price_targets": {}, "insider_sentiment": {}}
    try:
        out["recommendations"] = _client.recommendation_trends(symbol) or []
        _rl()
    except Exception:
        pass
    try:
        out["price_targets"] = _client.price_target(symbol) or {}
        _rl()
    except Exception:
        pass
    try:
        out["insider_sentiment"] = _client.stock_insider_sentiment(symbol, "2024-01-01", str(datetime.date.today())) or {}
        _rl()
    except Exception:
        pass
    return out


def get_ticker_info(symbol: str) -> dict:
    try:
        return yf.Ticker(symbol).info or {}
    except Exception:
        return {}
