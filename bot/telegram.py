import json
import os
import requests
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, LOG_FILE


def send_message(text: str) -> bool:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        log_signal(text)
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


def format_mtf_signal(symbol: str, tf: str, div: dict, conditions: list,
                      entry: dict | None = None, trend: str = "",
                      confidence: int = 0) -> str:
    emoji = "🐻" if div["type"] == "bearish" else "🐂"
    lines = [
        f"{emoji} <b>{symbol} {tf}</b>  ({confidence}%)",
        f"{div['strength'].upper()} {div['type'].upper()}  |  {trend}",
    ]
    if conditions:
        lines.append(f"{' | '.join(conditions)}")
    if entry:
        arrow = "🟢" if entry["action"] == "BUY" else "🔴"
        lines.append(
            f"{arrow} {entry['action']} {entry['entry']} "
            f"SL:{entry['stop_loss']} TP:{entry['take_profit']} 1:{entry['risk_reward']}"
        )
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
