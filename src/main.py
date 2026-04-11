"""
AI Market Intelligence — Daily Signal Report
Fetches prices and news from Finnhub, scores sentiment with VADER,
and commits a markdown report to the repository.
"""
import sys
import datetime

import data_fetcher as df
import sentiment_analyzer as sa
import report_generator as rg
from config import WATCHLIST, FINNHUB_API_KEY


def run():
    if not FINNHUB_API_KEY:
        print("ERROR: FINNHUB_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    today = datetime.date.today()
    print(f"[main] Starting analysis for {today}")

    results = []

    # --- Stocks ---
    for symbol in WATCHLIST["stocks"]:
        print(f"[main] Processing {symbol}...")

        quote = df.get_quote(symbol)
        if quote is None:
            print(f"[main] Skipping {symbol} — no quote data.")
            continue

        articles = df.get_stock_news(symbol)
        scored_articles = sa.score_articles(articles)
        headlines = [a["headline"] for a in articles]
        sentiment_score = sa.score_headlines(headlines)
        signal = sa.classify(sentiment_score)

        results.append({
            "symbol": symbol,
            "price": quote["price"],
            "change_pct": quote["change_pct"],
            "sentiment_score": sentiment_score,
            "signal": signal,
            "top_articles": scored_articles[:5],
        })

    # --- Crypto ---
    for symbol in WATCHLIST["crypto"]:
        print(f"[main] Processing {symbol}...")

        quote = df.get_quote(symbol)
        if quote is None:
            print(f"[main] Skipping {symbol} — no quote data.")
            continue

        # Finnhub doesn't support company_news for crypto; use market news sentiment proxy
        results.append({
            "symbol": symbol,
            "price": quote["price"],
            "change_pct": quote["change_pct"],
            "sentiment_score": 0.0,  # updated below with market news
            "signal": "Neutral",
            "top_articles": [],
        })

    # --- Market news (used for crypto sentiment and report section) ---
    print("[main] Fetching market news...")
    market_articles = df.get_market_news()
    scored_market = sa.score_articles(market_articles)

    # Apply market-wide sentiment to crypto entries (no per-asset news available)
    market_sentiment = sa.score_headlines([a["headline"] for a in market_articles])
    for r in results:
        if "USDT" in r["symbol"] or ":" in r["symbol"]:
            r["sentiment_score"] = market_sentiment
            r["signal"] = sa.classify(market_sentiment)

    if not results:
        print("[main] No data collected — exiting without writing report.", file=sys.stderr)
        sys.exit(1)

    # --- Generate and save report ---
    print("[main] Generating report...")
    report_content = rg.build_report(results, scored_market, date=today)
    path = rg.save_report(report_content, date=today)
    print(f"[main] Report saved to {path}")


if __name__ == "__main__":
    run()
