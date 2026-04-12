import requests
import time
import yfinance as yf

_CIK_CACHE: dict[str, str] = {}


def _get_cik(ticker: str) -> str | None:
    if ticker in _CIK_CACHE:
        return _CIK_CACHE[ticker]
    try:
        r = requests.get(
            "https://efts.sec.gov/LATEST/search-index?q=%22" + ticker + "%22&dateRange=custom&startdt=2020-01-01&forms=10-K",
            headers={"User-Agent": "AlphaBot research@alphabot.ai"},
            timeout=10,
        )
        data = requests.get(
            "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&ticker=" + ticker + "&type=10-K&dateb=&owner=include&count=1&search_text=&output=atom",
            headers={"User-Agent": "AlphaBot research@alphabot.ai"},
            timeout=10,
        ).text
        import re
        match = re.search(r"CIK=(\d+)", data)
        if match:
            cik = match.group(1).zfill(10)
            _CIK_CACHE[ticker] = cik
            return cik
    except Exception:
        pass
    return None


def _get_edgar_facts(cik: str) -> dict:
    try:
        r = requests.get(
            f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json",
            headers={"User-Agent": "AlphaBot research@alphabot.ai"},
            timeout=15,
        )
        time.sleep(0.2)
        return r.json().get("facts", {}).get("us-gaap", {}) if r.status_code == 200 else {}
    except Exception:
        return {}


def _extract_quarterly_eps(facts: dict) -> list[float]:
    for tag in ["EarningsPerShareDiluted", "EarningsPerShareBasic"]:
        data = facts.get(tag, {}).get("units", {}).get("USD/shares", [])
        quarterly = [d for d in data if d.get("form") == "10-Q"]
        if len(quarterly) >= 8:
            quarterly.sort(key=lambda x: x["end"])
            return [d["val"] for d in quarterly[-8:]]
    return []


def get_eps_growth(ticker: str) -> dict:
    cik = _get_cik(ticker)
    if cik:
        facts = _get_edgar_facts(cik)
        eps_series = _extract_quarterly_eps(facts)
        if len(eps_series) >= 8:
            current_q = eps_series[-1]
            year_ago_q = eps_series[-5]
            if year_ago_q and year_ago_q != 0:
                growth = round(((current_q - year_ago_q) / abs(year_ago_q)) * 100, 1)
                return {"quarterly_yoy_pct": growth, "source": "SEC EDGAR"}

    try:
        info = yf.Ticker(ticker).info
        eq = info.get("earningsGrowth")
        if eq is not None:
            return {"quarterly_yoy_pct": round(eq * 100, 1), "source": "yfinance"}
    except Exception:
        pass

    return {"quarterly_yoy_pct": None, "source": None}


def get_fundamentals(ticker: str) -> dict:
    try:
        info = yf.Ticker(ticker).info
    except Exception:
        info = {}

    eps_data = get_eps_growth(ticker)

    pe_trailing = info.get("trailingPE")
    pe_forward = info.get("forwardPE")
    roe = info.get("returnOnEquity")
    revenue_growth = info.get("revenueGrowth")

    canslim_c = (
        eps_data["quarterly_yoy_pct"] is not None
        and eps_data["quarterly_yoy_pct"] >= 25
    )
    canslim_a = bool(info.get("earningsGrowth") and info.get("earningsGrowth") > 0.25)

    fundamental_score = 50.0
    if eps_data["quarterly_yoy_pct"] is not None:
        g = eps_data["quarterly_yoy_pct"]
        fundamental_score += 20 if g >= 50 else 10 if g >= 25 else 0 if g >= 0 else -15

    if roe is not None:
        fundamental_score += 10 if roe >= 0.17 else 0 if roe >= 0 else -10

    if revenue_growth is not None:
        fundamental_score += 10 if revenue_growth >= 0.20 else 5 if revenue_growth >= 0.10 else 0

    return {
        "eps_growth_qoq_yoy_pct": eps_data["quarterly_yoy_pct"],
        "eps_source": eps_data["source"],
        "revenue_growth_pct": round(revenue_growth * 100, 1) if revenue_growth else None,
        "roe_pct": round(roe * 100, 1) if roe else None,
        "pe_trailing": round(pe_trailing, 1) if pe_trailing else None,
        "pe_forward": round(pe_forward, 1) if pe_forward else None,
        "canslim_c": canslim_c,
        "canslim_a": canslim_a,
        "fundamental_score": round(min(max(fundamental_score, 0), 100), 1),
    }
