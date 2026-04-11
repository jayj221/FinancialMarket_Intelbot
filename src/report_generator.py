import datetime
import os
from config import REPORT_DIR


def _signal_emoji(signal: str) -> str:
    return {"Bullish": "📈", "Bearish": "📉", "Neutral": "➡️"}.get(signal, "")


def _format_price(symbol: str, price: float) -> str:
    if "USDT" in symbol or "USD" in symbol:
        return f"${price:,.0f}" if price > 1000 else f"${price:,.2f}"
    return f"${price:,.2f}"


def _change_str(change_pct: float) -> str:
    prefix = "+" if change_pct > 0 else ""
    return f"{prefix}{change_pct:.2f}%"


def build_report(results: list[dict], market_news: list[dict], date: datetime.date | None = None) -> str:
    """
    Builds a markdown report string from a list of per-asset result dicts.

    Each result dict must contain:
        symbol, price, change_pct, sentiment_score, signal, top_articles

    market_news is a list of article dicts with headline, source, score.
    """
    if date is None:
        date = datetime.date.today()

    lines = [
        f"# AI Market Intelligence — {date}",
        "",
        "> Auto-generated daily report powered by VADER sentiment analysis on financial news.",
        "",
        "## Signal Summary",
        "",
        "| Asset | Price | Day Δ | Sentiment | AI Signal |",
        "|-------|-------|-------|-----------|-----------|",
    ]

    for r in results:
        symbol = r["symbol"].replace("BINANCE:", "")
        price_str = _format_price(r["symbol"], r["price"])
        change_str = _change_str(r["change_pct"])
        score = r["sentiment_score"]
        signal = r["signal"]
        emoji = _signal_emoji(signal)
        lines.append(
            f"| {symbol} | {price_str} | {change_str} | {score:+.2f} | {signal} {emoji} |"
        )

    # Top bullish stories across all assets
    all_articles = []
    for r in results:
        for a in r.get("top_articles", []):
            all_articles.append({**a, "asset": r["symbol"].replace("BINANCE:", "")})

    bullish = [a for a in all_articles if a["score"] > 0.5]
    bearish = [a for a in all_articles if a["score"] < -0.3]
    bullish.sort(key=lambda x: x["score"], reverse=True)
    bearish.sort(key=lambda x: x["score"])

    if bullish:
        lines += ["", "## Top Bullish Stories", ""]
        for i, a in enumerate(bullish[:3], 1):
            lines.append(f"{i}. **{a['asset']}** ({a['score']:+.2f}): {a['headline']} — *{a['source']}*")

    if bearish:
        lines += ["", "## Top Bearish Stories", ""]
        for i, a in enumerate(bearish[:3], 1):
            lines.append(f"{i}. **{a['asset']}** ({a['score']:+.2f}): {a['headline']} — *{a['source']}*")

    if market_news:
        lines += ["", "## Market Headlines", ""]
        for a in market_news[:5]:
            score_label = f"({a['score']:+.2f})" if "score" in a else ""
            lines.append(f"- {a['headline']} {score_label} — *{a['source']}*")

    lines += [
        "",
        "---",
        f"*Generated: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} | "
        "Sentiment: [VADER](https://github.com/cjhutto/vaderSentiment) | "
        "Data: [Finnhub](https://finnhub.io)*",
    ]

    return "\n".join(lines)


def save_report(content: str, date: datetime.date | None = None) -> str:
    """Writes the report to reports/YYYY-MM-DD.md and returns the file path."""
    if date is None:
        date = datetime.date.today()
    os.makedirs(REPORT_DIR, exist_ok=True)
    path = os.path.join(REPORT_DIR, f"{date}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path
