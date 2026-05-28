import json
import os
import requests
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, LOG_FILE


def send_message(text: str) -> bool:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        log_signal(text)
        print(f"[Telegram disabled] {text}")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            log_signal(text)
            return True
        print(f"Telegram error: {resp.text}")
        return False
    except Exception as e:
        print(f"Telegram exception: {e}")
        return False


def format_signal(symbol: str, tf: str, div: dict, conditions: list,
                  entry: dict | None = None) -> str:
    emoji = "🐻" if div["type"] == "bearish" else "🐂"
    lines = [
        f"{emoji} <b>{symbol} {tf}</b>",
        f"Type: {div['type'].upper()} divergence ({div['strength']})",
        f"Price: {div['from_price']:.5f} → {div['to_price']:.5f}",
        f"RSI: {div['from_rsi']:.1f} → {div['to_rsi']:.1f}",
    ]
    if conditions:
        lines.append(f"Conditions: {' | '.join(conditions)}")
    if entry:
        arrow = "🟢" if entry["action"] == "BUY" else "🔴"
        lines.extend([
            "",
            f"{arrow} <b>{entry['action']}</b>",
            f"Entry: {entry['entry']}",
            f"SL:    {entry['stop_loss']}",
            f"TP:    {entry['take_profit']}",
            f"R:R  1:{entry['risk_reward']}",
        ])
    return "\n".join(lines)


def format_market_overview(symbol_signals: list) -> str:
    lines = ["<b>📊 Market Overview</b>\n"]
    for s in symbol_signals:
        emoji = "🐻" if s["type"] == "bearish" else "🐂" if s["type"] == "bullish" else "⚪"
        lines.append(f"{emoji} {s['symbol']} {s['tf']} — ${s['price']:.2f} ({s['type']})")
    return "\n".join(lines)


def log_signal(text: str):
    entry = {"text": text}
    try:
        signals = []
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE) as f:
                signals = json.load(f)
        signals.append(entry)
        if len(signals) > 1000:
            signals = signals[-1000:]
        with open(LOG_FILE, "w") as f:
            json.dump(signals, f, indent=2, ensure_ascii=False)
    except Exception:
        pass
