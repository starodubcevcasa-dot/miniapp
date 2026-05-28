import time
import sys
from datetime import datetime
from config import SYMBOLS, TIMEFRAMES, DIVERGENCE_LOOKBACK
from data.provider import fetch_custom, normalize_symbol
from analysis.indicators import compute_all
from analysis.divergences import find_divergences, check_rsi_conditions, generate_entry
from bot.telegram import send_message, format_signal


def analyze_symbol(symbol: str, tf: str, df):
    df = compute_all(df)
    lookback = DIVERGENCE_LOOKBACK.get(tf, 20)
    pivot_order = 5 if tf == "1m" else 3
    divergences = find_divergences(df, lookback=lookback, pivot_order=pivot_order)
    conditions = check_rsi_conditions(df)

    for div in divergences[-1:]:
        entry = generate_entry(df, div) if tf == "1m" else None
        signal = format_signal(symbol, tf, div, conditions, entry)
        yield {"signal": signal, "div": div, "conditions": conditions, "entry": entry, "price": float(df["close"].iloc[-1])}


def print_entry(s):
    e = s.get("entry")
    if e:
        print(f"\n>>> {e['action']} {s['symbol']} {s['tf']} @ {e['entry']} "
              f"SL:{e['stop_loss']} TP:{e['take_profit']} R:R 1:{e['risk_reward']}")


def analyze(symbols: list[str], timeframes: list[str]):
    data = fetch_custom(symbols, timeframes)
    for (symbol, tf), df in data.items():
        for s in analyze_symbol(symbol, tf, df):
            s["symbol"] = symbol
            s["tf"] = tf
            print_entry(s)
            send_message(s["signal"])
            yield s


def run_once(symbols=None, timeframes=None):
    if symbols is None:
        symbols = SYMBOLS
    if timeframes is None:
        timeframes = list(TIMEFRAMES.keys())

    print(f"[{datetime.now().isoformat()}] Scanning {symbols} on {timeframes}")
    list(analyze(symbols, timeframes))


def run_loop(interval_minutes=60, symbols=None, timeframes=None):
    print(f"Starting loop every {interval_minutes}m for {symbols or SYMBOLS}")
    while True:
        try:
            run_once(symbols, timeframes)
        except Exception as e:
            print(f"Error: {e}")
        time.sleep(interval_minutes * 60)


def parse_args():
    args = sys.argv[1:]
    symbols = []
    tf = "1m"
    rest = []

    i = 0
    while i < len(args):
        if args[i] == "--tf" and i + 1 < len(args):
            tf = args[i + 1]
            i += 2
        elif args[i] == "--once":
            i += 1
        elif args[i].isdigit():
            i += 1
        elif args[i] in ("-h", "--help"):
            print("Usage: python3 main.py [--once] [--tf 1m|1h|4h|1d] [SYMBOLS...]")
            print("       python3 main.py [interval_minutes] [--tf ...] [SYMBOLS...]")
            print("Examples:")
            print("  python3 main.py --once EURUSD GBPUSD BTC")
            print("  python3 main.py --once --tf 1h EURUSD USDJPY")
            print("  python3 main.py 30 EURUSD GBPUSD AUDUSD USDCAD")
            sys.exit(0)
        else:
            rest.append(args[i])
            i += 1

    for arg in rest:
        if arg.isdigit():
            continue
        symbols.append(normalize_symbol(arg))

    return tf, symbols


if __name__ == "__main__":
    tf, custom_symbols = parse_args()
    timeframes = [tf]
    once = "--once" in sys.argv

    if custom_symbols:
        symbols = custom_symbols
    else:
        symbols = SYMBOLS
        if tf == "1m":
            timeframes = ["1m"]
        else:
            timeframes = list(TIMEFRAMES.keys())

    if once:
        run_once(symbols, timeframes)
    else:
        interval = 60
        for arg in sys.argv[1:]:
            if arg.isdigit():
                interval = int(arg)
                break
        run_loop(interval, symbols, timeframes)
