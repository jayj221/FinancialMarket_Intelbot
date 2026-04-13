import pandas as pd
import numpy as np


def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def calc_rsi(df: pd.DataFrame, period: int = 14) -> float | None:
    delta = df["close"].diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    r = 100 - (100 / (1 + rs))
    val = r.iloc[-1]
    return round(float(val), 2) if pd.notna(val) else None


def calc_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> dict | None:
    ema_fast = _ema(df["close"], fast)
    ema_slow = _ema(df["close"], slow)
    macd_line = ema_fast - ema_slow
    signal_line = _ema(macd_line, signal)
    hist = macd_line - signal_line
    m, s, h = macd_line.iloc[-1], signal_line.iloc[-1], hist.iloc[-1]
    if any(pd.isna(v) for v in [m, s, h]):
        return None
    return {
        "macd": round(float(m), 4),
        "signal": round(float(s), 4),
        "histogram": round(float(h), 4),
        "momentum": "Bullish" if float(h) > 0 else "Bearish",
    }


def calc_bollinger(df: pd.DataFrame, period: int = 20) -> dict | None:
    close = df["close"]
    mid = close.rolling(period).mean()
    std = close.rolling(period).std()
    upper = mid + 2 * std
    lower = mid - 2 * std
    u, l, price = float(upper.iloc[-1]), float(lower.iloc[-1]), float(close.iloc[-1])
    if any(pd.isna(v) for v in [u, l]):
        return None
    band_width = u - l
    position = (price - l) / band_width if band_width > 0 else 0.5
    return {
        "upper": round(u, 2),
        "lower": round(l, 2),
        "position_pct": round(position * 100, 1),
    }


def calc_ema_cross(df: pd.DataFrame, short: int = 9, long: int = 21) -> dict | None:
    ema_short = _ema(df["close"], short)
    ema_long = _ema(df["close"], long)
    s, l = float(ema_short.iloc[-1]), float(ema_long.iloc[-1])
    prev_s, prev_l = float(ema_short.iloc[-2]), float(ema_long.iloc[-2])
    if any(pd.isna(v) for v in [s, l, prev_s, prev_l]):
        return None
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

    rsi_val = technicals.get("rsi")
    if rsi_val is not None:
        if 40 <= rsi_val <= 60:
            score += 10
        elif rsi_val < 30:
            score += 15
        elif rsi_val > 70:
            score -= 15
        elif rsi_val > 65:
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
