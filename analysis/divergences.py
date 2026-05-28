import pandas as pd
import numpy as np
from scipy.signal import argrelextrema


def find_pivots(series: pd.Series, order: int = 3):
    high_idx = argrelextrema(series.values, np.greater, order=order)[0]
    low_idx = argrelextrema(series.values, np.less, order=order)[0]
    return high_idx, low_idx


DIVERGENCE_MIN_RSI_DIFF = 3.0


def find_divergences(df: pd.DataFrame, lookback: int = 20, pivot_order: int = 3):
    results = []
    price = df["close"]
    rsi_vals = df["rsi"]
    atr_val = float(df["atr"].iloc[-1]) if "atr" in df.columns else 0
    n = len(df)

    high_idx, low_idx = find_pivots(price, order=pivot_order)
    rsi_high_idx, rsi_low_idx = find_pivots(rsi_vals, order=pivot_order)

    def quality_check(p1, p2):
        rsi_diff = abs(rsi_vals.iloc[p2] - rsi_vals.iloc[p1])
        if rsi_diff < DIVERGENCE_MIN_RSI_DIFF:
            return False
        price_diff_pct = abs(price.iloc[p2] - price.iloc[p1]) / price.iloc[p1]
        if price_diff_pct < 0.0005:
            return False
        if atr_val > 0:
            price_diff_atr = abs(price.iloc[p2] - price.iloc[p1]) / atr_val
            if price_diff_atr < 0.3:
                return False
        return True

    high_set = set(high_idx)
    rsi_high_set = set(rsi_high_idx)
    common_high = sorted(high_set & rsi_high_set)

    for i in range(len(common_high)):
        for j in range(i + 1, len(common_high)):
            p1, p2 = common_high[i], common_high[j]
            if p2 - p1 > lookback or p2 - p1 < 3:
                continue
            if not quality_check(p1, p2):
                continue

            ph = price.iloc[p2] > price.iloc[p1]
            rl = rsi_vals.iloc[p2] < rsi_vals.iloc[p1]

            if ph and rl:
                results.append(make_div("bearish", "regular", df, p1, p2))
            elif not ph and rl:
                results.append(make_div("bullish", "hidden", df, p1, p2))

    low_set = set(low_idx)
    rsi_low_set = set(rsi_low_idx)
    common_low = sorted(low_set & rsi_low_set)

    for i in range(len(common_low)):
        for j in range(i + 1, len(common_low)):
            p1, p2 = common_low[i], common_low[j]
            if p2 - p1 > lookback or p2 - p1 < 3:
                continue
            if not quality_check(p1, p2):
                continue

            pl = price.iloc[p2] < price.iloc[p1]
            rh = rsi_vals.iloc[p2] > rsi_vals.iloc[p1]

            if pl and rh:
                results.append(make_div("bullish", "regular", df, p1, p2))
            elif not pl and rh:
                results.append(make_div("bearish", "hidden", df, p1, p2))

    return results


def make_div(direction: str, strength: str, df, p1, p2) -> dict:
    price = df["close"]
    rsi_vals = df["rsi"]
    return {
        "type": direction,
        "strength": strength,
        "from_idx": int(p1),
        "to_idx": int(p2),
        "from_price": float(price.iloc[p1]),
        "to_price": float(price.iloc[p2]),
        "from_rsi": float(rsi_vals.iloc[p1]),
        "to_rsi": float(rsi_vals.iloc[p2]),
        "time_from": str(df.index[p1]),
        "time_to": str(df.index[p2]),
    }


def check_rsi_conditions(df: pd.DataFrame):
    last = df.iloc[-1]
    prev = df.iloc[-2]
    conditions = []

    if last["rsi"] < 30:
        conditions.append(f"Oversold {last['rsi']:.1f}")
    elif last["rsi"] > 70:
        conditions.append(f"Overbought {last['rsi']:.1f}")

    if last["rsi"] < 30 and last["rsi"] > prev["rsi"]:
        conditions.append("RSI up from oversold")
    elif last["rsi"] > 70 and last["rsi"] < prev["rsi"]:
        conditions.append("RSI down from overbought")

    if last["rsi"] > 50:
        conditions.append("RSI>50 bullish")
    elif last["rsi"] < 50:
        conditions.append("RSI<50 bearish")

    return conditions


def generate_entry(df: pd.DataFrame, div: dict, atr_multiplier: float = 1.5) -> dict:
    last = df.iloc[-1]
    atr_val = float(df["atr"].iloc[-1])
    direction = div["type"]
    entry = float(last["close"])

    if direction == "bullish":
        sl = entry - atr_val * atr_multiplier
        tp = entry + atr_val * atr_multiplier * 2
        stop_idx = div["from_idx"]
        recent_low = float(df["low"].iloc[stop_idx:].min())
        sl = max(sl, recent_low - atr_val * 0.3)
    else:
        sl = entry + atr_val * atr_multiplier
        tp = entry - atr_val * atr_multiplier * 2
        stop_idx = div["from_idx"]
        recent_high = float(df["high"].iloc[stop_idx:].max())
        sl = min(sl, recent_high + atr_val * 0.3)

    risk = abs(sl - entry)
    reward = abs(tp - entry)

    return {
        "action": "BUY" if direction == "bullish" else "SELL",
        "entry": round(entry, 5),
        "stop_loss": round(sl, 5),
        "take_profit": round(tp, 5),
        "atr": round(atr_val, 5),
        "risk_reward": round(reward / risk, 2) if risk > 0 else 0,
        "signal_idx": int(div["to_idx"]),
    }


def confidence_score(div: dict, conditions: list, trend: str, struct: str,
                     df: pd.DataFrame | None = None) -> int:
    score = 50

    if div["strength"] == "regular":
        score += 15
    else:
        score += 5

    rsi_diff = abs(div["to_rsi"] - div["from_rsi"])
    score += min(int(rsi_diff * 2), 10)

    direction = div["type"]
    if trend == "uptrend" and direction == "bullish":
        score += 20
    elif trend == "downtrend" and direction == "bearish":
        score += 20
    elif trend in ("bullish_bias",):
        score += 8 if direction == "bullish" else -8
    elif trend in ("bearish_bias",):
        score += 8 if direction == "bearish" else -8

    if struct == "HH_HL" and direction == "bullish":
        score += 10
    elif struct == "LH_LL" and direction == "bearish":
        score += 10

    for c in conditions:
        if "oversold" in c and direction == "bullish":
            score += 5
        elif "overbought" in c and direction == "bearish":
            score += 5
        if "up from oversold" in c:
            score += 5
        elif "down from overbought" in c:
            score += 5

    if df is not None and "volume" in df.columns:
        vol = df["volume"].iloc[-5:]
        avg_vol = vol.mean()
        last_vol = float(df["volume"].iloc[-1])
        if avg_vol > 0 and last_vol > avg_vol * 1.3:
            score += 5

    return max(0, min(100, score))
