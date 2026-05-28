import os

SYMBOLS = [
    "EURUSD=X",
    "GBPUSD=X",
    "USDJPY=X",
    "AUDUSD=X",
    "USDCAD=X",
    "BTC-USD",
]

TIMEFRAMES = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "1h": "1h",
    "4h": "4h",
    "1d": "1d",
}

FETCH_PERIOD = {
    "1m": "3d",
    "5m": "5d",
    "15m": "10d",
    "1h": "2mo",
    "4h": "3mo",
    "1d": "6mo",
}

RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
DIVERGENCE_LOOKBACK = {
    "1m": 12,
    "5m": 15,
    "15m": 18,
    "1h": 20,
    "4h": 22,
    "1d": 25,
}
PIVOT_ORDER = {
    "1m": 5,
    "5m": 4,
    "15m": 3,
    "1h": 3,
    "4h": 3,
    "1d": 3,
}
ENTRY_TIMEFRAMES = {"1m", "5m", "15m"}

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

DATA_DIR = os.path.join(os.path.dirname(__file__), "data_cache")
LOG_FILE = os.path.join(os.path.dirname(__file__), "signals.json")
