import datetime
import os
from config import REPORT_DIR, COMPOSITE_WEIGHTS


def _grade(score: float) -> str:
    if score >= 80: return "A"
    if score >= 65: return "B"
    if score >= 50: return "C"
    if score >= 35: return "D"
    return "F"


def _fmt_pct(val, suffix="%") -> str:
    if val is None: return "N/A"
    prefix = "+" if val > 0 else ""
    return f"{prefix}{val:.1f}{suffix}"


def _fmt_float(val, decimals=2) -> str:
    return f"{val:.{decimals}f}" if val is not None else "N/A"


def _macro_section(macro: dict) -> list[str]:
    vix = macro["vix"]
    yc = macro["yield_curve"]
    fed = macro["fed_funds"]
    lines = [
        "## Macro Environment",
        "",
        f"| Indicator | Value | Signal |",
        f"|-----------|-------|--------|",
        f"| VIX | {_fmt_float(vix['current'])} | {vix['regime']} |",
        f"| Yield Curve (10Y-2Y) | {_fmt_float(yc['spread_10y_2y'], 3)} | {yc['signal']} |",
        f"| Fed Funds Rate | {_fmt_float(fed['rate'])}% | {fed['trend']} |",
        f"| Macro Score | {macro['macro_score']}/100 | {_grade(macro['macro_score'])} |",
        "",
    ]
    return lines


def _market_direction_section(direction: dict) -> list[str]:
    return [
        "## Market Direction (O'Neil Method)",
        "",
        f"**Classification:** {direction['classification']}",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| SPY vs SMA50 | {'Above' if direction['spy_above_sma50'] else 'Below'} |",
        f"| SPY vs SMA200 | {'Above' if direction['spy_above_sma200'] else 'Below'} |",
        f"| Distribution Days (25-session) | {direction['distribution_days']} |",
        f"| Follow-Through Day | {'Yes' if direction.get('ftd') else 'No'} |",
        "",
    ]


def _asset_section(results: list[dict]) -> list[str]:
    lines = [
        "## Asset Intelligence",
        "",
        "| Asset | Price | Day Δ | FinBERT | Technicals | Fundamentals | Composite | Grade |",
        "|-------|-------|-------|---------|------------|--------------|-----------|-------|",
    ]
    for r in results:
        lines.append(
            f"| {r['symbol']} | ${r['price']:,.2f} | {_fmt_pct(r['change_pct'])} "
            f"| {r['sentiment_score']:+.2f} ({r['sentiment_signal']}) "
            f"| {r['technical_score']:.0f}/100 "
            f"| {r['fundamental_score']:.0f}/100 "
            f"| {r['composite_score']:.0f}/100 "
            f"| **{r['grade']}** |"
        )
    lines.append("")
    return lines


def _deep_asset_section(results: list[dict]) -> list[str]:
    lines = ["## Deep Asset Analysis", ""]
    for r in results:
        lines += [
            f"### {r['symbol']} — {r['grade']} ({r['composite_score']:.0f}/100)",
            "",
            "**Sentiment (FinBERT)**",
            f"- Score: {r['sentiment_score']:+.4f} | Signal: {r['sentiment_signal']}",
        ]
        for a in r.get("top_articles", [])[:3]:
            lines.append(f"  - `{a['finbert_label'].upper()}` ({a['finbert_confidence']:.2f}): {a['headline'][:90]} — *{a.get('source', '')}*")

        analyst = r.get("analyst_data", {})
        recs = analyst.get("recommendations", [])
        if recs:
            latest = recs[0]
            lines.append(f"- Analyst Consensus: {latest.get('buy', 0)} Buy / {latest.get('hold', 0)} Hold / {latest.get('sell', 0)} Sell")
        pt = analyst.get("price_targets", {})
        if pt.get("targetMean"):
            upside = ((pt["targetMean"] - r["price"]) / r["price"]) * 100
            lines.append(f"- Price Target: ${pt['targetMean']:.2f} (mean) — {_fmt_pct(upside)} upside")

        tech = r.get("technicals", {})
        lines += [
            "",
            "**Technical Analysis**",
            f"- RSI(14): {_fmt_float(tech.get('rsi'))} | MACD: {tech.get('macd', {}).get('momentum', 'N/A')} ({_fmt_float(tech.get('macd', {}).get('histogram'), 4)})",
            f"- Bollinger Position: {_fmt_float(tech.get('bollinger', {}).get('position_pct'))}% of band",
            f"- EMA Cross (9/21): {tech.get('ema_cross', {}).get('status', 'N/A')}",
            f"- Volume Ratio: {_fmt_float(tech.get('volume_ratio'))}x 20-day avg",
            f"- Minervini Trend Template: {tech.get('trend_template', {}).get('score', 0)}/7 criteria",
        ]

        fund = r.get("fundamentals", {})
        lines += [
            "",
            "**Fundamentals**",
            f"- EPS Growth (QoQ YoY): {_fmt_pct(fund.get('eps_growth_qoq_yoy_pct'))} | Revenue Growth: {_fmt_pct(fund.get('revenue_growth_pct'))}",
            f"- ROE: {_fmt_pct(fund.get('roe_pct'))} | P/E Trailing: {_fmt_float(fund.get('pe_trailing'))} | Forward: {_fmt_float(fund.get('pe_forward'))}",
            f"- CAN SLIM — C (EPS≥25%): {'✓' if fund.get('canslim_c') else '✗'} | A (Annual Growth): {'✓' if fund.get('canslim_a') else '✗'}",
        ]

        lines += [
            "",
            f"**Takeaway:** {r.get('takeaway', 'Insufficient data for summary.')}",
            "",
            "---",
            "",
        ]
    return lines


def _build_takeaway(r: dict) -> str:
    grade = r["grade"]
    signal = r["sentiment_signal"]
    tt = r.get("technicals", {}).get("trend_template", {}).get("score", 0)
    eps = r.get("fundamentals", {}).get("eps_growth_qoq_yoy_pct")

    parts = []
    if grade in ("A", "B"):
        parts.append(f"{r['symbol']} shows strong composite strength")
    elif grade in ("D", "F"):
        parts.append(f"{r['symbol']} presents significant headwinds")
    else:
        parts.append(f"{r['symbol']} is mixed")

    if signal == "Bullish":
        parts.append("with positive news sentiment")
    elif signal == "Bearish":
        parts.append("amid negative news flow")

    if tt >= 6:
        parts.append(f"and passes {tt}/7 Minervini trend criteria")
    if eps is not None and eps >= 25:
        parts.append(f"driven by {eps:.0f}% quarterly EPS growth")

    return ". ".join(parts) + "."


def compute_composite(sentiment_score: float, technical_score: float, fundamental_score: float, macro_score: float) -> float:
    sent_normalized = (sentiment_score + 1) / 2 * 100
    return round(
        sent_normalized * COMPOSITE_WEIGHTS["sentiment"]
        + technical_score * COMPOSITE_WEIGHTS["technical"]
        + fundamental_score * COMPOSITE_WEIGHTS["fundamentals"]
        + macro_score * COMPOSITE_WEIGHTS["macro"],
        1,
    )


def build_report(results: list[dict], macro: dict, market_direction: dict, date: datetime.date | None = None) -> str:
    if date is None:
        date = datetime.date.today()

    for r in results:
        r["takeaway"] = _build_takeaway(r)

    lines = [
        f"# AI Market Intelligence — {date}",
        "",
        f"> Deep analysis powered by FinBERT NLP · SEC EDGAR fundamentals · FRED macro · Minervini/CAN SLIM technicals",
        "",
    ]

    lines += _macro_section(macro)
    lines += _market_direction_section(market_direction)
    lines += _asset_section(results)
    lines += _deep_asset_section(results)

    lines += [
        "---",
        f"*Generated: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} | "
        "NLP: [FinBERT](https://huggingface.co/ProsusAI/finbert) | "
        "Data: [Finnhub](https://finnhub.io) · [SEC EDGAR](https://www.sec.gov/developer) · [FRED](https://fred.stlouisfed.org)*",
    ]

    return "\n".join(lines)


def save_report(content: str, date: datetime.date | None = None) -> str:
    if date is None:
        date = datetime.date.today()
    os.makedirs(REPORT_DIR, exist_ok=True)
    path = os.path.join(REPORT_DIR, f"{date}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path
