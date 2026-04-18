import sys
import datetime
import yfinance as yf
import pandas as pd

import data_fetcher as df
import sentiment_analyzer as sa
import technical_analyzer as ta
import fundamentals as fund
import macro_analyzer as macro
import report_generator as rg
from config import WATCHLIST, FINNHUB_API_KEY, FRED_API_KEY


def classify_market_direction() -> dict:
    spy = yf.Ticker("SPY").history(period="6mo")
    if spy.empty:
        return {"classification": "UNKNOWN", "dist_count": 0, "above_sma50": False, "above_sma200": False}
    if hasattr(spy.index, "tz") and spy.index.tz is not None:
        spy.index = spy.index.tz_convert(None)
    close = spy["Close"]
    volume = spy["Volume"]

    sma50 = close.rolling(50).mean()
    sma200 = close.rolling(200).mean()

    dist_day = (close.pct_change() <= -0.002) & (volume > volume.shift(1))
    dist_count = int(dist_day.rolling(25).sum().iloc[-1])

    spy_above_sma50 = float(close.iloc[-1]) > float(sma50.iloc[-1])
    spy_above_sma200 = float(close.iloc[-1]) > float(sma200.iloc[-1])

    ftd = False
    if not spy_above_sma50:
        recent = close.pct_change().tail(10)
        ftd = any(recent > 0.0125)

    if spy_above_sma50 and dist_count <= 3:
        classification = "CONFIRMED UPTREND"
    elif spy_above_sma50 and dist_count <= 5:
        classification = "UPTREND UNDER PRESSURE"
    else:
        classification = "MARKET IN CORRECTION"

    return {
        "classification": classification,
        "spy_above_sma50": spy_above_sma50,
        "spy_above_sma200": spy_above_sma200,
        "distribution_days": dist_count,
        "ftd": ftd,
    }


def run():
    if not FINNHUB_API_KEY:
        print("ERROR: FINNHUB_API_KEY not set", file=sys.stderr)
        sys.exit(1)
    if not FRED_API_KEY:
        print("ERROR: FRED_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    today = datetime.date.today()
    print(f"[main] Starting deep analysis — {today}")

    print("[main] Fetching macro data...")
    macro_data = macro.get_macro_summary()

    print("[main] Classifying market direction...")
    market_dir = classify_market_direction()
    print(f"[main] Market: {market_dir['classification']}")

    results = []

    for symbol in WATCHLIST:
        print(f"[main] Processing {symbol}...")

        quote = df.get_quote(symbol)
        if quote is None:
            print(f"[main] Skipping {symbol} — no quote")
            continue

        ohlcv = df.get_ohlcv(symbol)
        news = df.get_stock_news(symbol)
        analyst_data = df.get_analyst_data(symbol)

        scored_articles = sa.score_articles(news) if news else []
        sentiment_score = sa.aggregate_score(scored_articles)
        sentiment_signal = sa.classify(sentiment_score)

        technicals = ta.get_technicals(ohlcv) if ohlcv is not None else {}
        tech_score = ta.technical_score(technicals) if technicals else 50.0

        fund_data = fund.get_fundamentals(symbol)
        fund_score = fund_data.get("fundamental_score", 50.0)

        composite = rg.compute_composite(
            sentiment_score, tech_score, fund_score, macro_data["macro_score"]
        )
        grade = rg._grade(composite)

        results.append({
            "symbol": symbol,
            "price": quote["price"],
            "change_pct": quote["change_pct"],
            "sentiment_score": sentiment_score,
            "sentiment_signal": sentiment_signal,
            "top_articles": scored_articles[:5],
            "analyst_data": analyst_data,
            "technicals": technicals,
            "technical_score": tech_score,
            "fundamentals": fund_data,
            "fundamental_score": fund_score,
            "composite_score": composite,
            "grade": grade,
        })

    if not results:
        print("[main] No results — exiting", file=sys.stderr)
        sys.exit(1)

    print("[main] Building report...")
    content = rg.build_report(results, macro_data, market_dir, date=today)
    path = rg.save_report(content, date=today)
    print(f"[main] Report saved → {path}")


if __name__ == "__main__":
    run()
