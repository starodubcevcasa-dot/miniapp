import pandas as pd
import numpy as np


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def macd(series: pd.Series, fast=12, slow=26, signal=9):
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def trend_direction(df: pd.DataFrame) -> str:
    last = df.iloc[-1]
    price = last["close"]
    sma20 = last.get("sma_20")
    sma50 = last.get("sma_50")
    sma200 = last.get("sma_200")

    if pd.isna(sma200) or pd.isna(sma20):
        return "neutral"

    if price > sma20 > sma50 > sma200 and sma20 > sma50:
        return "uptrend"
    if price < sma20 < sma50 < sma200 and sma20 < sma50:
        return "downtrend"

    if price > sma200:
        return "bullish_bias"
    return "bearish_bias"


def market_structure(df: pd.DataFrame, lookback: int = 10) -> str:
    highs = df["high"].iloc[-lookback:]
    lows = df["low"].iloc[-lookback:]
    hh = highs.is_monotonic_increasing
    ll = lows.is_monotonic_decreasing
    if hh and not ll:
        return "HH_HL"
    if ll and not hh:
        return "LH_LL"
    return "mixed"


def stochastic(df: pd.DataFrame, k_period=14, d_period=3) -> tuple[pd.Series, pd.Series]:
    low_k = df["low"].rolling(k_period).min()
    high_k = df["high"].rolling(k_period).max()
    k = 100 * (df["close"] - low_k) / (high_k - low_k).replace(0, np.nan)
    d = k.rolling(d_period).mean()
    return k, d


def compute_all(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["rsi"] = rsi(df["close"], 14)
    df["sma_20"] = sma(df["close"], 20)
    df["sma_50"] = sma(df["close"], 50)
    df["sma_200"] = sma(df["close"], 200)
    df["macd"], df["macd_signal"], df["macd_hist"] = macd(df["close"])
    df["atr"] = atr(df)
    df["stoch_k"], df["stoch_d"] = stochastic(df)
    return df
