import os
import pickle
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from config import DATA_DIR, SYMBOLS, FETCH_PERIOD

CACHE_TTL = {"5m": 120, "15m": 300, "1h": 3600, "4h": 7200, "1d": 86400}


def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def cache_path(symbol, tf):
    return os.path.join(DATA_DIR, f"{symbol.replace('=', '')}_{tf}.pkl")


def load_cached(symbol, tf):
    path = cache_path(symbol, tf)
    if os.path.exists(path):
        with open(path, "rb") as f:
            return pickle.load(f)
    return None


def save_cache(symbol, tf, df):
    path = cache_path(symbol, tf)
    with open(path, "wb") as f:
        pickle.dump(df, f)


def has_movement(df) -> bool:
    if df.empty:
        return False
    return (df["high"] != df["low"]).any()


def fetch_ohlcv(symbol: str, tf: str) -> pd.DataFrame:
    period = FETCH_PERIOD.get(tf, "2mo")
    cache_ttl = CACHE_TTL.get(tf, 3600)

    cached = load_cached(symbol, tf)
    if cached is not None and not cached.empty:
        last_time = cached.index[-1]
        now = datetime.now(last_time.tzinfo)
        if now - last_time < timedelta(seconds=cache_ttl):
            return cached

    interval_map = {"5m": "5m", "15m": "15m", "1h": "60m", "4h": "1h", "1d": "1d"}
    interval = interval_map.get(tf, "1h")

    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period, interval=interval)

    if df.empty:
        cached = load_cached(symbol, tf)
        if cached is not None:
            return cached
        return pd.DataFrame()

    df.columns = [c.lower() for c in df.columns]

    if tf == "4h" and interval == "1h":
        df = df.resample("4h").agg({
            "open": "first", "high": "max", "low": "min",
            "close": "last", "volume": "sum",
        }).dropna()

    if has_movement(df):
        save_cache(symbol, tf, df)
    return df


def fetch_all() -> dict:
    return fetch_custom(SYMBOLS, list(FETCH_PERIOD.keys()))


def fetch_custom(symbols: list, timeframes: list[str]) -> dict:
    ensure_data_dir()
    result = {}
    for symbol in symbols:
        for tf in timeframes:
            df = fetch_ohlcv(symbol, tf)
            if not df.empty and has_movement(df):
                result[(symbol, tf)] = df
    return result


def normalize_symbol(raw: str) -> str:
    s = raw.upper().strip()
    if s.endswith("=X") or s.endswith("-USD"):
        return s
    if s == "BTC" or s == "BTCUSD":
        return "BTC-USD"
    if s == "ETH" or s == "ETHUSD":
        return "ETH-USD"
    if len(s) == 6 and s.isalpha():
        return f"{s[:3]}{s[3:]}=X"
    return s
