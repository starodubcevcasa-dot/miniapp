import json
import os
from datetime import datetime, date


RISK_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "risk_log.json")


def calculate_position_size(account_balance: float, risk_percent: float,
                            entry_price: float, stop_loss: float) -> dict:
    risk_amount = account_balance * (risk_percent / 100)
    price_risk = abs(entry_price - stop_loss)
    if price_risk == 0:
        return {"error": "Stop loss equals entry price"}

    position_size = risk_amount / price_risk
    position_value = position_size * entry_price

    return {
        "account_balance": account_balance,
        "risk_percent": risk_percent,
        "risk_amount": round(risk_amount, 2),
        "entry_price": entry_price,
        "stop_loss": stop_loss,
        "position_size": round(position_size, 6),
        "position_value": round(position_value, 2),
        "risk_reward_1": round(price_risk, 5),
    }


def log_trade(symbol: str, side: str, entry: float, sl: float, tp: float,
              size: float, reason: str):
    trade = {
        "date": str(datetime.now()),
        "symbol": symbol,
        "side": side,
        "entry": entry,
        "stop_loss": sl,
        "take_profit": tp,
        "size": size,
        "reason": reason,
    }
    trades = []
    if os.path.exists(RISK_FILE):
        with open(RISK_FILE) as f:
            trades = json.load(f)
    trades.append(trade)
    if len(trades) > 500:
        trades = trades[-500:]
    with open(RISK_FILE, "w") as f:
        json.dump(trades, f, indent=2)


def check_daily_loss(max_loss: float = 100) -> bool:
    if not os.path.exists(RISK_FILE):
        return True
    with open(RISK_FILE) as f:
        trades = json.load(f)
    today = str(date.today())
    daily_loss = sum(
        abs(t.get("entry", 0))
        for t in trades
        if t.get("date", "").startswith(today) and t.get("side") in ("sell", "short")
    )
    return daily_loss < max_loss
