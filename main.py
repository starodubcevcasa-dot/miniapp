import time
import json
from datetime import datetime
from config import SYMBOLS, TIMEFRAMES, DIVERGENCE_LOOKBACK
from data.provider import fetch_all
from analysis.indicators import compute_all
from analysis.divergences import find_divergences, check_rsi_conditions
from bot.telegram import send_message, format_signal, format_market_overview


def analyze_symbol(symbol: str, tf: str, df):
    df = compute_all(df)
    divergences = find_divergences(df, lookback=DIVERGENCE_LOOKBACK)
    conditions = check_rsi_conditions(df)

    signals = []
    for div in divergences[-3:]:
        signal = format_signal(symbol, tf, div, conditions)
        signals.append({"signal": signal, "div": div, "conditions": conditions})

    return signals, float(df["close"].iloc[-1])


def run_once():
    print(f"[{datetime.now().isoformat()}] Fetching data...")
    data = fetch_all()
    all_signals = []
    market_overview = []

    for (symbol, tf), df in data.items():
        signals, price = analyze_symbol(symbol, tf, df)
        all_signals.extend(signals)
        for s in signals:
            market_overview.append({
                "symbol": symbol,
                "tf": tf,
                "type": s["div"]["type"],
                "price": price,
            })

    for s in all_signals:
        send_message(s["signal"])
        time.sleep(0.5)

    if market_overview:
        overview = format_market_overview(market_overview)
        send_message(overview)

    return all_signals


def run_loop(interval_minutes: int = 60):
    print(f"Starting forex bot, scanning every {interval_minutes} minutes")
    while True:
        try:
            run_once()
        except Exception as e:
            print(f"Error in loop: {e}")
        time.sleep(interval_minutes * 60)


if __name__ == "__main__":
    import sys
    if "--once" in sys.argv:
        run_once()
    else:
        interval = 60
        for arg in sys.argv[1:]:
            if arg.isdigit():
                interval = int(arg)
                break
        run_loop(interval)
