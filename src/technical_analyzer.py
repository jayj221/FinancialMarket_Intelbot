import pandas as pd
import pandas_ta as ta
import numpy as np


def calc_rsi(df: pd.DataFrame, period: int = 14) -> float | None:
    rsi = ta.rsi(df["close"], length=period)
    return round(float(rsi.iloc[-1]), 2) if rsi is not None and not rsi.empty else None


def calc_macd(df: pd.DataFrame) -> dict | None:
    macd = ta.macd(df["close"])
    if macd is None or macd.empty:
        return None
    hist_col = [c for c in macd.columns if "MACDh" in c][0]
    macd_col = [c for c in macd.columns if "MACD_" in c and "h" not in c and "s" not in c][0]
    sig_col = [c for c in macd.columns if "MACDs" in c][0]
    return {
        "macd": round(float(macd[macd_col].iloc[-1]), 4),
        "signal": round(float(macd[sig_col].iloc[-1]), 4),
        "histogram": round(float(macd[hist_col].iloc[-1]), 4),
        "momentum": "Bullish" if float(macd[hist_col].iloc[-1]) > 0 else "Bearish",
    }


def calc_bollinger(df: pd.DataFrame, period: int = 20) -> dict | None:
    bb = ta.bbands(df["close"], length=period)
    if bb is None or bb.empty:
        return None
    upper = float(bb[[c for c in bb.columns if "BBU" in c][0]].iloc[-1])
    lower = float(bb[[c for c in bb.columns if "BBL" in c][0]].iloc[-1])
    price = float(df["close"].iloc[-1])
    band_width = upper - lower
    position = (price - lower) / band_width if band_width > 0 else 0.5
    return {
        "upper": round(upper, 2),
        "lower": round(lower, 2),
        "position_pct": round(position * 100, 1),
    }


def calc_ema_cross(df: pd.DataFrame, short: int = 9, long: int = 21) -> dict | None:
    ema_short = ta.ema(df["close"], length=short)
    ema_long = ta.ema(df["close"], length=long)
    if ema_short is None or ema_long is None:
        return None
    s, l = float(ema_short.iloc[-1]), float(ema_long.iloc[-1])
    prev_s, prev_l = float(ema_short.iloc[-2]), float(ema_long.iloc[-2])
    crossed_up = prev_s <= prev_l and s > l
    crossed_down = prev_s >= prev_l and s < l
    status = "Golden Cross" if crossed_up else "Death Cross" if crossed_down else ("Bullish" if s > l else "Bearish")
    return {"ema9": round(s, 2), "ema21": round(l, 2), "status": status}


def calc_volume_ratio(df: pd.DataFrame, period: int = 20) -> float | None:
    avg = df["volume"].rolling(period).mean().iloc[-1]
    cur = df["volume"].iloc[-1]
    return round(float(cur / avg), 2) if avg > 0 else None


def minervini_trend_template(df: pd.DataFrame) -> dict:
    close = df["close"]
    volume = df["volume"]

    sma50 = close.rolling(50).mean()
    sma150 = close.rolling(150).mean()
    sma200 = close.rolling(200).mean()

    c = float(close.iloc[-1])
    s50 = float(sma50.iloc[-1])
    s150 = float(sma150.iloc[-1])
    s200 = float(sma200.iloc[-1])
    s200_21ago = float(sma200.iloc[-22]) if len(sma200.dropna()) >= 22 else s200

    high52 = float(close.rolling(252).max().iloc[-1])
    low52 = float(close.rolling(252).min().iloc[-1])

    criteria = {
        "above_150_200": c > s150 and c > s200,
        "sma150_above_200": s150 > s200,
        "sma200_trending_up": s200 > s200_21ago,
        "sma50_above_150_200": s50 > s150 and s50 > s200,
        "above_sma50": c > s50,
        "above_52wk_low_30pct": c >= low52 * 1.30,
        "within_25pct_of_52wk_high": c >= high52 * 0.75,
    }

    passes = sum(criteria.values())
    return {"score": passes, "max": 7, "criteria": criteria}


def get_technicals(df: pd.DataFrame) -> dict:
    return {
        "rsi": calc_rsi(df),
        "macd": calc_macd(df),
        "bollinger": calc_bollinger(df),
        "ema_cross": calc_ema_cross(df),
        "volume_ratio": calc_volume_ratio(df),
        "trend_template": minervini_trend_template(df),
    }


def technical_score(technicals: dict) -> float:
    score = 50.0

    rsi = technicals.get("rsi")
    if rsi is not None:
        if 40 <= rsi <= 60:
            score += 10
        elif rsi < 30:
            score += 15
        elif rsi > 70:
            score -= 15
        elif rsi > 65:
            score -= 5

    macd = technicals.get("macd")
    if macd:
        score += 10 if macd["momentum"] == "Bullish" else -10

    bb = technicals.get("bollinger")
    if bb:
        pos = bb["position_pct"]
        if pos < 20:
            score += 10
        elif pos > 80:
            score -= 10

    ema = technicals.get("ema_cross")
    if ema:
        if "Golden" in ema["status"] or ema["status"] == "Bullish":
            score += 10
        elif "Death" in ema["status"] or ema["status"] == "Bearish":
            score -= 10

    tt = technicals.get("trend_template", {})
    tt_score = tt.get("score", 0)
    score += (tt_score / 7) * 15

    return round(min(max(score, 0), 100), 1)
