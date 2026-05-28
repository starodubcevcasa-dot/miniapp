import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import mplfinance as mpf

CHARTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "charts")


def ensure_dir():
    os.makedirs(CHARTS_DIR, exist_ok=True)


def find_levels(df: pd.DataFrame, lookback: int = 40) -> dict:
    recent = df.iloc[-lookback:]
    highs = recent["high"].values
    lows = recent["low"].values

    def cluster(values, threshold=0.001):
        vals = sorted(set(values))
        result = [vals[0]]
        for v in vals[1:]:
            if abs(v - result[-1]) / max(abs(result[-1]), 0.0001) > threshold:
                result.append(v)
        return result

    return {
        "resistance": sorted(cluster(highs), reverse=True)[:3],
        "support": sorted(cluster(lows))[:3],
    }


def generate_chart(symbol: str, tf: str, df: pd.DataFrame, div: dict = None,
                   entry: dict = None) -> str:
    ensure_dir()
    name = symbol.replace("=X", "").replace("-USD", "")
    filename = f"{name}_{tf}_{pd.Timestamp.now().strftime('%H%M%S')}.png"
    filepath = os.path.join(CHARTS_DIR, filename)

    plot_data = df.iloc[-80:].copy()
    plot_data.index = pd.to_datetime(plot_data.index)

    cols = {"open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"}
    plot_renamed = plot_data.rename(columns=cols)

    ap_data = []
    panels = [2, 2, 2, 2]

    rsi_series = plot_data["rsi"] if "rsi" in plot_data.columns else None
    if rsi_series is not None:
        ap_data.append(mpf.make_addplot(rsi_series, panel=2, color="purple", width=1.5, ylabel="RSI"))
        ap_data.append(mpf.make_addplot(pd.Series(70, index=plot_data.index), panel=2,
                                         color="red", linestyle="--", alpha=0.3))
        ap_data.append(mpf.make_addplot(pd.Series(30, index=plot_data.index), panel=2,
                                         color="green", linestyle="--", alpha=0.3))
        ap_data.append(mpf.make_addplot(pd.Series(50, index=plot_data.index), panel=2,
                                         color="gray", linestyle=":", alpha=0.2))

    style = mpf.make_mpf_style(base_mpf_style="charles", rc={"font.size": 9})

    fig, axes = mpf.plot(
        plot_renamed, type="candle", style=style,
        addplot=ap_data if ap_data else None,
        volume=True,
        returnfig=True,
        figsize=(16, 10),
        title=f"\n{name} ({tf}) — {pd.Timestamp.now().strftime('%d.%m %H:%M')}",
        panel_ratios=(4, 1, 1.5),
        tight_layout=True,
    )

    ax1 = axes[0]

    levels = find_levels(df)
    for s in levels["support"]:
        ax1.axhline(y=s, color="green", linewidth=0.8, linestyle="--", alpha=0.5)
        ax1.text(0.98, s, f"S {s}", color="green", fontsize=9, va="bottom",
                 transform=ax1.get_yaxis_transform(), ha="right")
    for r in levels["resistance"]:
        ax1.axhline(y=r, color="red", linewidth=0.8, linestyle="--", alpha=0.5)
        ax1.text(0.98, r, f"R {r}", color="red", fontsize=9, va="bottom",
                 transform=ax1.get_yaxis_transform(), ha="right")

    if div:
        from_idx = max(0, div["from_idx"] - len(df) + len(plot_data))
        to_idx = max(0, div["to_idx"] - len(df) + len(plot_data))
        if from_idx < len(plot_data) and to_idx < len(plot_data):
            p1_price = div["from_price"]
            p2_price = div["to_price"]
            t1 = mdates.date2num(plot_data.index[from_idx])
            t2 = mdates.date2num(plot_data.index[to_idx])
            color = "#26a69a" if div["type"] == "bullish" else "#ef5350"
            marker = "^" if div["type"] == "bullish" else "v"

            ax1.scatter([t1, t2], [p1_price, p2_price], color=color, s=120, zorder=10, marker=marker, edgecolors="white", linewidth=1)
            ax1.plot([t1, t2], [p1_price, p2_price], color=color, linewidth=1.5, linestyle=":", alpha=0.8)

            label = f"{'БЫЧЬЯ' if div['type'] == 'bullish' else 'МЕДВ'} див. {div['strength']}"
            xy_off = (-60, -60) if div["type"] == "bullish" else (60, 60)
            ax1.annotate(label, xy=(t2, p2_price), xytext=xy_off,
                         textcoords="offset points", fontsize=11, weight="bold",
                         arrowprops=dict(arrowstyle="->", color=color, lw=2),
                         bbox=dict(boxstyle="round,pad=0.3", facecolor=color, alpha=0.2, edgecolor=color))

            if "rsi" in plot_data.columns:
                rsi_from = div["from_rsi"]
                rsi_to = div["to_rsi"]
                r1 = plot_data.index[from_idx]
                r2 = plot_data.index[to_idx]
                axes[2].scatter([mdates.date2num(r1), mdates.date2num(r2)],
                                [rsi_from, rsi_to], color=color, s=80, zorder=10, marker=marker)
                axes[2].plot([mdates.date2num(r1), mdates.date2num(r2)],
                             [rsi_from, rsi_to], color=color, linewidth=1.5, linestyle=":", alpha=0.8)

    if entry:
        entry_price = entry["entry"]
        sl_price = entry["stop_loss"]
        tp_price = entry["take_profit"]
        x_last = mdates.date2num(plot_data.index[-1])
        x_mid = mdates.date2num(plot_data.index[-8])

        color = "#26a69a" if entry["action"] == "BUY" else "#ef5350"
        action = "ПОКУПКА" if entry["action"] == "BUY" else "ПРОДАЖА"

        ax1.axhline(y=entry_price, color="white", linewidth=2, alpha=0.7)
        ax1.annotate(f"{action} {entry_price}", xy=(x_last, entry_price),
                     xytext=(15, 0), textcoords="offset points", fontsize=11, weight="bold",
                     color="white",
                     bbox=dict(boxstyle="round,pad=0.4", facecolor=color, alpha=0.85))

        ax1.axhline(y=sl_price, color="#ef5350", linewidth=1.2, linestyle="--", alpha=0.7)
        ax1.annotate(f"SL {sl_price}", xy=(x_mid, sl_price),
                     xytext=(5, 8), textcoords="offset points", fontsize=9,
                     color="#ef5350", weight="bold")

        ax1.axhline(y=tp_price, color="#26a69a", linewidth=1.2, linestyle="--", alpha=0.7)
        ax1.annotate(f"TP {tp_price}", xy=(x_mid, tp_price),
                     xytext=(5, 8), textcoords="offset points", fontsize=9,
                     color="#26a69a", weight="bold")

    plt.savefig(filepath, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return filepath
