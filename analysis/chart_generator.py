import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import mplfinance as mpf
from matplotlib import style as mpl_style

CHARTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "charts")


def ensure_dir():
    os.makedirs(CHARTS_DIR, exist_ok=True)


def find_levels(df: pd.DataFrame, lookback: int = 40) -> dict:
    recent = df.iloc[-lookback:]
    highs = recent["high"].values
    lows = recent["low"].values

    def cluster(values, threshold=0.0008):
        vals = sorted(set(values))
        if not vals:
            return []
        result = [vals[0]]
        for v in vals[1:]:
            if abs(v - result[-1]) / max(abs(result[-1]), 0.0001) > threshold:
                result.append(v)
        return result

    return {
        "resistance": sorted(cluster(highs), reverse=True)[:2],
        "support": sorted(cluster(lows))[:2],
    }


def generate_chart(symbol: str, tf: str, df: pd.DataFrame, div: dict = None,
                   entry: dict = None) -> str:
    ensure_dir()
    name = symbol.replace("=X", "").replace("-USD", "")
    filename = f"{name}_{tf}_{pd.Timestamp.now().strftime('%H%M%S')}.png"
    filepath = os.path.join(CHARTS_DIR, filename)

    candle_count = 35 if tf in ("1m", "5m") else 35
    plot_data = df.iloc[-candle_count:].copy()
    plot_data.index = pd.to_datetime(plot_data.index)

    cols = {"open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"}
    plot_renamed = plot_data.rename(columns=cols)

    bg_color = "#1a1a2e"
    text_color = "#e0e0e0"
    grid_color = "#2a2a3e"

    mpl_style.use("dark_background")
    plt.rcParams.update({
        "figure.facecolor": bg_color,
        "axes.facecolor": bg_color,
        "axes.edgecolor": grid_color,
        "axes.labelcolor": text_color,
        "text.color": text_color,
        "xtick.color": text_color,
        "ytick.color": text_color,
        "grid.color": grid_color,
        "font.size": 13,
        "axes.titlesize": 16,
    })

    custom_style = mpf.make_mpf_style(
        base_mpf_style="charles",
        rc={
            "font.size": 13,
            "figure.facecolor": bg_color,
            "axes.facecolor": bg_color,
            "axes.edgecolor": grid_color,
            "axes.labelcolor": text_color,
            "text.color": text_color,
            "xtick.color": text_color,
            "ytick.color": text_color,
            "grid.color": grid_color,
            "grid.alpha": 0.2,
        },
        marketcolors=mpf.make_marketcolors(
            up="#00e676",
            down="#ff1744",
            edge="#00e676",
            wick="#00e676",
            volume="inherit",
        ),
    )

    ap_data = []
    rsi_series = plot_data["rsi"] if "rsi" in plot_data.columns else None
    if rsi_series is not None:
        ap_data.append(mpf.make_addplot(
            rsi_series, panel=2, color="#bb86fc", width=2, ylabel="RSI"
        ))
        ap_data.append(mpf.make_addplot(
            pd.Series(70, index=plot_data.index), panel=2,
            color="#ff1744", linestyle="--", alpha=0.35, width=1,
        ))
        ap_data.append(mpf.make_addplot(
            pd.Series(30, index=plot_data.index), panel=2,
            color="#00e676", linestyle="--", alpha=0.35, width=1,
        ))
        ap_data.append(mpf.make_addplot(
            pd.Series(50, index=plot_data.index), panel=2,
            color="#888888", linestyle=":", alpha=0.2, width=0.8,
        ))

    fig, axes = mpf.plot(
        plot_renamed, type="candle", style=custom_style,
        addplot=ap_data if ap_data else None,
        volume=True,
        returnfig=True,
        figsize=(22, 14),
        title=f"\n{name} ({tf}) — {pd.Timestamp.now().strftime('%d.%m %H:%M')}",
        panel_ratios=(5, 0.8, 1.5),
        tight_layout=True,
        xrotation=0,
    )

    ax1 = axes[0]
    ax1.grid(True, alpha=0.15, color=grid_color)
    ax1.tick_params(axis="both", labelsize=12)

    levels = find_levels(df)
    for s in levels["support"]:
        ax1.axhline(y=s, color="#00e676", linewidth=1.5, linestyle="--", alpha=0.6)
        ax1.text(0.98, s, f"S {s:.5f}", color="#00e676", fontsize=12, weight="bold",
                 transform=ax1.get_yaxis_transform(), ha="right", va="bottom",
                 bbox=dict(fc="#1a1a2e", ec="#00e676", alpha=0.7, boxstyle="round,pad=0.2"))
    for r in levels["resistance"]:
        ax1.axhline(y=r, color="#ff1744", linewidth=1.5, linestyle="--", alpha=0.6)
        ax1.text(0.98, r, f"R {r:.5f}", color="#ff1744", fontsize=12, weight="bold",
                 transform=ax1.get_yaxis_transform(), ha="right", va="bottom",
                 bbox=dict(fc="#1a1a2e", ec="#ff1744", alpha=0.7, boxstyle="round,pad=0.2"))

    if div:
        from_idx = max(0, div["from_idx"] - len(df) + len(plot_data))
        to_idx = max(0, div["to_idx"] - len(df) + len(plot_data))
        if from_idx < len(plot_data) and to_idx < len(plot_data):
            p1_price = div["from_price"]
            p2_price = div["to_price"]
            t1 = mdates.date2num(plot_data.index[from_idx])
            t2 = mdates.date2num(plot_data.index[to_idx])
            color = "#00e676" if div["type"] == "bullish" else "#ff1744"
            marker = "^" if div["type"] == "bullish" else "v"

            ax1.scatter([t1, t2], [p1_price, p2_price],
                        color=color, s=200, zorder=10, marker=marker,
                        edgecolors="white", linewidth=2)
            ax1.plot([t1, t2], [p1_price, p2_price],
                     color=color, linewidth=2, linestyle=":", alpha=0.9)

            label = f"{'БЫЧЬЯ' if div['type'] == 'bullish' else 'МЕДВЕЖЬЯ'} ДИВЕРГЕНЦИЯ"
            xy_off = (-80, -80) if div["type"] == "bullish" else (80, 80)
            ax1.annotate(label, xy=(t2, p2_price), xytext=xy_off,
                         textcoords="offset points", fontsize=13, weight="bold",
                         color=color,
                         arrowprops=dict(arrowstyle="->", color=color, lw=2.5),
                         bbox=dict(boxstyle="round,pad=0.4", facecolor=bg_color,
                                   edgecolor=color, alpha=0.85))

            ax2 = axes[2]
            ax2.grid(True, alpha=0.15, color=grid_color)
            rsi_from = div["from_rsi"]
            rsi_to = div["to_rsi"]
            r1 = plot_data.index[from_idx]
            r2 = plot_data.index[to_idx]
            ax2.scatter([mdates.date2num(r1), mdates.date2num(r2)],
                        [rsi_from, rsi_to], color=color, s=150, zorder=10, marker=marker,
                        edgecolors="white", linewidth=2)
            ax2.plot([mdates.date2num(r1), mdates.date2num(r2)],
                     [rsi_from, rsi_to], color=color, linewidth=2, linestyle=":", alpha=0.9)

    if entry:
        entry_price = entry["entry"]
        sl_price = entry["stop_loss"]
        tp_price = entry["take_profit"]
        x_last = mdates.date2num(plot_data.index[-1])
        x_mid = mdates.date2num(plot_data.index[-6])

        color = "#00e676" if entry["action"] == "BUY" else "#ff1744"
        action = "ПОКУПКА" if entry["action"] == "BUY" else "ПРОДАЖА"

        ax1.axhline(y=entry_price, color="#ffffff", linewidth=2.5, alpha=0.8)
        ax1.annotate(f"{action}\n{entry_price}",
                     xy=(x_last, entry_price), xytext=(20, -20),
                     textcoords="offset points", fontsize=14, weight="bold",
                     color="#ffffff",
                     bbox=dict(boxstyle="round,pad=0.5", facecolor=color, alpha=0.9))

        ax1.axhline(y=sl_price, color="#ff1744", linewidth=2, linestyle="--", alpha=0.8)
        ax1.annotate(f"SL {sl_price}", xy=(x_mid, sl_price),
                     xytext=(5, -18), textcoords="offset points", fontsize=12,
                     color="#ffffff", weight="bold",
                     bbox=dict(boxstyle="round,pad=0.2", facecolor="#ff1744", alpha=0.8))

        rr = entry.get("risk_reward", "?")
        tp_label = f"TP {tp_price} (R:R 1:{rr})"
        ax1.axhline(y=tp_price, color="#00e676", linewidth=2, linestyle="--", alpha=0.8)
        ax1.annotate(tp_label, xy=(x_mid, tp_price),
                     xytext=(5, 5), textcoords="offset points", fontsize=12,
                     color="#ffffff", weight="bold",
                     bbox=dict(boxstyle="round,pad=0.2", facecolor="#00e676", alpha=0.8))

    plt.savefig(filepath, dpi=180, bbox_inches="tight", facecolor=bg_color)
    plt.close(fig)
    return filepath
