import time
import sys
from datetime import datetime
from config import SYMBOLS, TIMEFRAMES, DIVERGENCE_LOOKBACK, PIVOT_ORDER, ENTRY_TIMEFRAMES
from data.provider import fetch_custom, normalize_symbol
from analysis.indicators import compute_all, trend_direction, market_structure
from analysis.divergences import find_divergences, check_rsi_conditions, generate_entry, confidence_score
from bot.telegram import send_message, format_mtf_signal


def analyze_tf(symbol: str, tf: str, df):
    df = compute_all(df)
    lookback = DIVERGENCE_LOOKBACK.get(tf, 20)
    pivot_order = PIVOT_ORDER.get(tf, 3)
    divergences = find_divergences(df, lookback=lookback, pivot_order=pivot_order)
    conditions = check_rsi_conditions(df)
    trend = trend_direction(df)
    struct = market_structure(df)

    best = None
    for div in reversed(divergences):
        confidence = confidence_score(div, conditions, trend, struct)
        if best is None or confidence > best["confidence"]:
            best = {
                "div": div,
                "conditions": conditions,
                "trend": trend,
                "structure": struct,
                "confidence": confidence,
                "price": float(df["close"].iloc[-1]),
            }

    if best:
        best["entry"] = generate_entry(df, best["div"]) if tf in ENTRY_TIMEFRAMES else None
    return best


def print_mtf(symbol: str, results: dict):
    tfs_sorted = ["1m", "5m", "15m", "1h", "4h", "1d"]
    name = symbol.replace("=X", "").replace("-USD", "")

    lines = [f"\n{'='*50}", f"  {name}  ${results.get(tfs_sorted[0], {}).get('price', 0):.5f}", f"{'='*50}"]
    lines.append(f"  {'TF':<5} {'Dir':<8} {'Div':<10} {'Conf':<6} {'Trend':<14} {'Entry/SL/TP'}")

    for tf in tfs_sorted:
        r = results.get(tf)
        if not r or not r.get("div"):
            continue
        d = r["div"]
        direction = d["type"]
        strength = d["strength"]
        conf = r["confidence"]
        trend = r["trend"]
        arrow = "🟢" if direction == "bullish" else "🔴"

        div_label = f"{strength[:3]} {direction[:3]}".upper()
        trend_short = trend.replace("_", " ")[:12]

        rest = f"{arrow}  {div_label:<10} {conf}%  {trend_short:<14}"

        e = r.get("entry")
        if e:
            rest += f" {e['entry']} / SL:{e['stop_loss']} / TP:{e['take_profit']} (R:R 1:{e['risk_reward']})"

        lines.append(f"  {tf:<5} {rest}")

    return "\n".join(lines)


def analyze_full(symbols: list[str], timeframes: list[str]):
    data = fetch_custom(symbols, timeframes)
    grouped = {}

    for (symbol, tf), df in data.items():
        result = analyze_tf(symbol, tf, df)
        if result:
            grouped.setdefault(symbol, {})[tf] = result

    for symbol in symbols:
        if symbol in grouped:
            text = print_mtf(symbol, grouped[symbol])
            send_message(text)
            time.sleep(0.5)

    return grouped


def run_once(symbols=None, timeframes=None):
    if symbols is None:
        symbols = SYMBOLS
    if timeframes is None:
        timeframes = list(TIMEFRAMES.keys())

    print(f"[{datetime.now().isoformat()}] Scanning {[s.replace('=X','').replace('-USD','') for s in symbols]} on {timeframes}")
    analyze_full(symbols, timeframes)


def run_loop(interval_minutes=60, symbols=None, timeframes=None):
    print(f"Starting every {interval_minutes}m for {symbols or SYMBOLS}")
    while True:
        try:
            run_once(symbols, timeframes)
        except Exception as e:
            print(f"Error: {e}")
        time.sleep(interval_minutes * 60)


def parse_args():
    args = sys.argv[1:]
    symbols = []
    tf = None
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
            print("  python3 main.py --once --tf 1m EURUSD")
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
    once = "--once" in sys.argv

    if custom_symbols:
        symbols = custom_symbols
    else:
        symbols = SYMBOLS

    if tf:
        timeframes = [tf]
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
