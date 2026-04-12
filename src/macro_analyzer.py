import datetime
from fredapi import Fred
from config import FRED_API_KEY

_fred = None


def _get_fred():
    global _fred
    if _fred is None:
        _fred = Fred(api_key=FRED_API_KEY)
    return _fred


def _latest(series_id: str, periods: int = 30):
    try:
        return _get_fred().get_series(series_id).dropna().tail(periods)
    except Exception as e:
        print(f"[macro] FRED error {series_id}: {e}")
        return None


def get_vix() -> dict:
    series = _latest("VIXCLS", 30)
    if series is None or series.empty:
        return {"current": None, "trend": None, "regime": "Unknown"}
    current = round(float(series.iloc[-1]), 2)
    avg30 = round(float(series.mean()), 2)
    regime = (
        "Complacent" if current < 15
        else "Normal" if current < 20
        else "Elevated" if current < 30
        else "Fear"
    )
    return {"current": current, "avg_30d": avg30, "regime": regime}


def get_yield_curve() -> dict:
    series = _latest("T10Y2Y", 10)
    if series is None or series.empty:
        return {"spread": None, "signal": "Unknown"}
    spread = round(float(series.iloc[-1]), 3)
    signal = (
        "Inverted (Recession Risk)" if spread < 0
        else "Flat (Caution)" if spread < 0.5
        else "Normal"
    )
    return {"spread_10y_2y": spread, "signal": signal}


def get_fed_funds() -> dict:
    series = _latest("FEDFUNDS", 6)
    if series is None or series.empty:
        return {"rate": None, "trend": "Unknown"}
    current = round(float(series.iloc[-1]), 2)
    prev = round(float(series.iloc[-2]), 2) if len(series) > 1 else current
    trend = "Rising" if current > prev else "Falling" if current < prev else "Stable"
    return {"rate": current, "trend": trend}


def get_macro_summary() -> dict:
    vix = get_vix()
    yield_curve = get_yield_curve()
    fed = get_fed_funds()

    score = 50.0
    if vix["current"] is not None:
        if vix["current"] < 15:
            score += 15
        elif vix["current"] < 20:
            score += 5
        elif vix["current"] > 30:
            score -= 20
        else:
            score -= 5

    if yield_curve["spread_10y_2y"] is not None:
        score += 10 if yield_curve["spread_10y_2y"] > 0.5 else (-10 if yield_curve["spread_10y_2y"] < 0 else 0)

    if fed["trend"] == "Falling":
        score += 10
    elif fed["trend"] == "Rising":
        score -= 5

    return {
        "vix": vix,
        "yield_curve": yield_curve,
        "fed_funds": fed,
        "macro_score": round(min(max(score, 0), 100), 1),
    }
