import time
import sys
from datetime import datetime
from config import SYMBOLS, TIMEFRAMES, DIVERGENCE_LOOKBACK, PIVOT_ORDER, ENTRY_TIMEFRAMES
from data.provider import fetch_custom, normalize_symbol
from analysis.indicators import compute_all, trend_direction, market_structure
from analysis.divergences import find_divergences, check_rsi_conditions, generate_entry, confidence_score
from analysis.chart_generator import generate_chart
from bot.telegram import send_message

CONFIDENCE_MIN = 65
TF_ORDER = ["1m", "5m", "15m", "1h", "4h", "1d"]


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
        confidence = confidence_score(div, conditions, trend, struct, df)
        if best is None or confidence > best["confidence"]:
            best = {
                "div": div,
                "conditions": conditions,
                "trend": trend,
                "structure": struct,
                "confidence": confidence,
                "price": float(df["close"].iloc[-1]),
                "df": df,
            }

    if best and tf in ENTRY_TIMEFRAMES:
        best["entry"] = generate_entry(df, best["div"])
    elif best:
        best["entry"] = None
    return best


def mtf_alignment(results: dict, tf: str) -> str:
    idx = TF_ORDER.index(tf)
    r = results.get(tf)
    if not r or not r.get("div"):
        return "neutral"
    direction = r["div"]["type"]

    align_score = 0
    for higher_tf in TF_ORDER[idx + 1:]:
        h = results.get(higher_tf)
        if h and h.get("div"):
            if h["div"]["type"] == direction:
                align_score += 1
            else:
                align_score -= 1

    if align_score >= 2:
        return "strong"
    elif align_score >= 1:
        return "align"
    elif align_score <= -1:
        return "conflict"
    return "neutral"


TREND_RU = {
    "uptrend": "восход",
    "downtrend": "нисход",
    "bullish_bias": "бычий",
    "bearish_bias": "медвеж",
    "neutral": "нейтр",
}
DIR_RU = {"bullish": "БЫЧЬЯ", "bearish": "МЕДВ"}
STRENGTH_RU = {"regular": "ОБЫЧ", "hidden": "СКРЫТ"}
ACTION_RU = {"BUY": "ПОКУПКА", "SELL": "ПРОДАЖА"}
ALIGN_RU = {"strong": "✅", "align": "↑", "conflict": "⚠", "neutral": "—"}


def format_mtf(symbol: str, results: dict):
    name = symbol.replace("=X", "").replace("-USD", "")
    price = 0
    for tf in TF_ORDER:
        r = results.get(tf)
        if r and r.get("price", 0) > 0:
            price = r["price"]
            break
    lines = [f"\n{'='*50}", f"  {name}  ${price:.5f}", f"{'='*50}"]
    lines.append(f"  {'ТФ':<5} {'Напр':<7} {'Сигнал':<11} {'Увер':<6} {'Согл':<8} {'Тренд':<14} {'Вход/SL/TP'}")

    entry_tf = None
    entry_data = None

    for tf in TF_ORDER:
        r = results.get(tf)
        if not r or not r.get("div"):
            continue
        d = r["div"]
        conf = r["confidence"]
        if conf < CONFIDENCE_MIN:
            continue

        align = mtf_alignment(results, tf)
        arrow = "🟢" if d["type"] == "bullish" else "🔴"
        div_label = f"{STRENGTH_RU.get(d['strength'], d['strength'][:3])} {DIR_RU.get(d['type'], d['type'][:3])}"
        trend_short = TREND_RU.get(r["trend"], r["trend"][:8])
        align_short = ALIGN_RU.get(align, "—")

        rest = f"{arrow}  {div_label:<11} {conf}%  {align_short:<8} {trend_short:<14}"
        e = r.get("entry")
        if e and tf in ENTRY_TIMEFRAMES and conf >= CONFIDENCE_MIN:
            rest += f" {e['entry']} / SL:{e['stop_loss']} / TP:{e['take_profit']} (1:{e['risk_reward']})"
            if not entry_data or r.get("confidence", 0) > entry_data[1]:
                entry_tf, entry_data = tf, (e, r["confidence"])

        lines.append(f"  {tf:<5} {rest}")

    chart_path = None
    if entry_data:
        e, conf = entry_data
        arrow = "🟢" if e["action"] == "BUY" else "🔴"
        action = ACTION_RU.get(e["action"], e["action"])
        lines.append(f"\n  РЕКОМЕНДАЦИЯ: {arrow} {action} {name} @ {e['entry']}"
                     f"  SL: {e['stop_loss']}  TP: {e['take_profit']}  R:R 1:{e['risk_reward']}  ({entry_tf}, {conf}%)")

        best_result = results.get(entry_tf)
        if best_result and best_result.get("div") and best_result.get("df") is not None:
            chart_path = generate_chart(
                symbol, entry_tf, best_result["df"],
                best_result["div"], e
            )

    if chart_path:
        lines.append(f"  📷 {chart_path}")

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
            text = format_mtf(symbol, grouped[symbol])
            print(text)
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
