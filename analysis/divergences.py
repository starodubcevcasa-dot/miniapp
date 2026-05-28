import pandas as pd
import numpy as np
from scipy.signal import argrelextrema


def find_pivots(series: pd.Series, order: int = 3):
    high_idx = argrelextrema(series.values, np.greater, order=order)[0]
    low_idx = argrelextrema(series.values, np.less, order=order)[0]
    return high_idx, low_idx


def find_divergences(df: pd.DataFrame, lookback: int = 20):
    results = []
    price = df["close"]
    rsi_vals = df["rsi"]
    n = len(df)

    high_idx, low_idx = find_pivots(price, order=3)
    rsi_high_idx, rsi_low_idx = find_pivots(rsi_vals, order=3)

    high_set = set(high_idx)
    rsi_high_set = set(rsi_high_idx)
    common_high = sorted(high_set & rsi_high_set)

    for i in range(len(common_high)):
        for j in range(i + 1, len(common_high)):
            p1, p2 = common_high[i], common_high[j]
            if p2 - p1 > lookback:
                continue
            if p2 - p1 < 3:
                continue

            price_higher = price.iloc[p2] > price.iloc[p1]
            rsi_lower = rsi_vals.iloc[p2] < rsi_vals.iloc[p1]

            if price_higher and rsi_lower:
                results.append({
                    "type": "bearish",
                    "strength": "regular",
                    "from_idx": int(p1),
                    "to_idx": int(p2),
                    "from_price": float(price.iloc[p1]),
                    "to_price": float(price.iloc[p2]),
                    "from_rsi": float(rsi_vals.iloc[p1]),
                    "to_rsi": float(rsi_vals.iloc[p2]),
                    "time_from": str(df.index[p1]),
                    "time_to": str(df.index[p2]),
                })

    low_set = set(low_idx)
    rsi_low_set = set(rsi_low_idx)
    common_low = sorted(low_set & rsi_low_set)

    for i in range(len(common_low)):
        for j in range(i + 1, len(common_low)):
            p1, p2 = common_low[i], common_low[j]
            if p2 - p1 > lookback:
                continue
            if p2 - p1 < 3:
                continue

            price_lower = price.iloc[p2] < price.iloc[p1]
            rsi_higher = rsi_vals.iloc[p2] > rsi_vals.iloc[p1]

            if price_lower and rsi_higher:
                results.append({
                    "type": "bullish",
                    "strength": "regular",
                    "from_idx": int(p1),
                    "to_idx": int(p2),
                    "from_price": float(price.iloc[p1]),
                    "to_price": float(price.iloc[p2]),
                    "from_rsi": float(rsi_vals.iloc[p1]),
                    "to_rsi": float(rsi_vals.iloc[p2]),
                    "time_from": str(df.index[p1]),
                    "time_to": str(df.index[p2]),
                })

    return results


def check_rsi_conditions(df: pd.DataFrame):
    last = df.iloc[-1]
    prev = df.iloc[-2]
    conditions = []

    if last["rsi"] < 30:
        conditions.append(f"RSI oversold: {last['rsi']:.1f}")
    elif last["rsi"] > 70:
        conditions.append(f"RSI overbought: {last['rsi']:.1f}")

    if last["rsi"] < 30 and last["rsi"] > prev["rsi"]:
        conditions.append("RSI turning up from oversold")
    elif last["rsi"] > 70 and last["rsi"] < prev["rsi"]:
        conditions.append("RSI turning down from overbought")

    return conditions
