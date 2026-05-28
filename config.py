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
    "1h": "1h",
    "4h": "4h",
    "1d": "1d",
}

RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
DIVERGENCE_LOOKBACK = 20

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

DATA_DIR = os.path.join(os.path.dirname(__file__), "data_cache")

LOG_FILE = os.path.join(os.path.dirname(__file__), "signals.json")
