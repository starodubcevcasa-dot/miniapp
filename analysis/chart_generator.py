import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle

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


def draw_candle(ax, x, o, h, l, c, width=0.6, up_color="#00e676", down_color="#ff1744"):
    color = up_color if c >= o else down_color
    ax.plot([x, x], [l, h], color=color, linewidth=1.5, solid_capstyle="round")
    rect = Rectangle((x - width / 2, min(o, c)), width, abs(c - o),
                     facecolor=color, edgecolor=color, linewidth=0.5)
    ax.add_patch(rect)


def generate_chart(symbol: str, tf: str, df: pd.DataFrame, div: dict = None,
                   entry: dict = None) -> str:
    ensure_dir()
    name = symbol.replace("=X", "").replace("-USD", "")
    filename = f"{name}_{tf}_{pd.Timestamp.now().strftime('%H%M%S')}.png"
    filepath = os.path.join(CHARTS_DIR, filename)

    candle_count = 35
    plot_data = df.iloc[-candle_count:].copy()
    plot_data.index = pd.to_datetime(plot_data.index)

    bg = "#131722"
    text_c = "#d1d4dc"
    grid_c = "#2a2e39"

    fig = plt.figure(figsize=(20, 12), facecolor=bg)
    gs = fig.add_gridspec(4, 1, height_ratios=[4, 0.8, 1.2, 0.8], hspace=0.08)

    ax1 = fig.add_subplot(gs[0, 0], facecolor=bg)
    ax_vol = fig.add_subplot(gs[1, 0], facecolor=bg, sharex=ax1)
    ax_rsi = fig.add_subplot(gs[2, 0], facecolor=bg, sharex=ax1)

    fig.suptitle(f"{name} ({tf}) — {pd.Timestamp.now().strftime('%d.%m %H:%M')}",
                 color=text_c, fontsize=18, fontweight="bold", y=0.98)

    for ax in [ax1, ax_vol, ax_rsi]:
        ax.set_facecolor(bg)
        ax.tick_params(colors=text_c, labelsize=11)
        ax.grid(True, alpha=0.12, color=grid_c)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["bottom"].set_color(grid_c)
        ax.spines["left"].set_color(grid_c)

    dates_num = mdates.date2num(plot_data.index.to_pydatetime())
    x_range = range(len(plot_data))

    for i in range(len(plot_data)):
        row = plot_data.iloc[i]
        draw_candle(ax1, i, row["open"], row["high"], row["low"], row["close"],
                    width=0.7, up_color="#00e676", down_color="#ff1744")

    sma20 = plot_data["sma_20"] if "sma_20" in plot_data.columns else None
    sma50 = plot_data["sma_50"] if "sma_50" in plot_data.columns else None
    if sma20 is not None:
        ax1.plot(x_range, sma20.values, color="#2196f3", linewidth=1.5, alpha=0.8, label="SMA20")
    if sma50 is not None:
        ax1.plot(x_range, sma50.values, color="#ff9800", linewidth=1.5, alpha=0.8, label="SMA50")
    ax1.legend(loc="upper left", fontsize=11, facecolor=bg, labelcolor=text_c, edgecolor=grid_c)

    ax1.set_ylabel("Price", color=text_c, fontsize=12)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.5f}"))

    levels = find_levels(df)
    for s in levels["support"]:
        ax1.axhline(y=s, color="#00e676", linewidth=1.5, linestyle="--", alpha=0.6)
        ax1.text(len(plot_data) - 1, s, f"S {s:.5f}", color="#00e676", fontsize=12,
                 weight="bold", ha="right", va="bottom",
                 bbox=dict(fc=bg, ec="#00e676", alpha=0.8, boxstyle="round,pad=0.2"))
    for r in levels["resistance"]:
        ax1.axhline(y=r, color="#ff1744", linewidth=1.5, linestyle="--", alpha=0.6)
        ax1.text(len(plot_data) - 1, r, f"R {r:.5f}", color="#ff1744", fontsize=12,
                 weight="bold", ha="right", va="bottom",
                 bbox=dict(fc=bg, ec="#ff1744", alpha=0.8, boxstyle="round,pad=0.2"))

    if "volume" in plot_data.columns:
        vol = plot_data["volume"].values
        colors_vol = ["#00e676" if plot_data["close"].iloc[i] >= plot_data["open"].iloc[i]
                      else "#ff1744" for i in range(len(plot_data))]
        ax_vol.bar(x_range, vol, color=colors_vol, width=0.8, alpha=0.7)
        ax_vol.set_ylabel("Vol", color=text_c, fontsize=11)
        ax_vol.set_ylim(bottom=0)

    rsi_vals = plot_data["rsi"].values if "rsi" in plot_data.columns else None
    if rsi_vals is not None:
        ax_rsi.plot(x_range, rsi_vals, color="#bb86fc", linewidth=2, label="RSI")
        ax_rsi.axhline(y=70, color="#ff1744", linestyle="--", alpha=0.35, linewidth=1)
        ax_rsi.axhline(y=30, color="#00e676", linestyle="--", alpha=0.35, linewidth=1)
        ax_rsi.axhline(y=50, color="#888888", linestyle=":", alpha=0.2, linewidth=0.8)
        ax_rsi.set_ylabel("RSI", color=text_c, fontsize=11)
        ax_rsi.set_ylim(0, 100)
        ax_rsi.legend(loc="upper left", fontsize=11, facecolor=bg, labelcolor=text_c, edgecolor=grid_c)

    if div:
        from_idx = max(0, div["from_idx"] - len(df) + len(plot_data))
        to_idx = max(0, div["to_idx"] - len(df) + len(plot_data))
        if from_idx < len(plot_data) and to_idx < len(plot_data):
            p1_price = div["from_price"]
            p2_price = div["to_price"]
            color = "#00e676" if div["type"] == "bullish" else "#ff1744"
            marker = "^" if div["type"] == "bullish" else "v"

            ax1.scatter([from_idx, to_idx], [p1_price, p2_price],
                        color=color, s=250, zorder=10, marker=marker,
                        edgecolors="white", linewidth=2.5)
            ax1.plot([from_idx, to_idx], [p1_price, p2_price],
                     color=color, linewidth=2.5, linestyle=":", alpha=0.9)

            label = f"{'БЫЧЬЯ' if div['type'] == 'bullish' else 'МЕДВЕЖЬЯ'} ДИВЕРГЕНЦИЯ"
            xy_off = (-30, -60) if div["type"] == "bullish" else (30, 60)
            ax1.annotate(label, xy=(to_idx, p2_price), xytext=xy_off,
                         textcoords="offset points", fontsize=13, weight="bold",
                         color=color,
                         arrowprops=dict(arrowstyle="->", color=color, lw=2.5),
                         bbox=dict(boxstyle="round,pad=0.4", facecolor=bg,
                                   edgecolor=color, alpha=0.85))

            if rsi_vals is not None:
                rsi_from = div["from_rsi"]
                rsi_to = div["to_rsi"]
                ax_rsi.scatter([from_idx, to_idx], [rsi_from, rsi_to],
                               color=color, s=180, zorder=10, marker=marker,
                               edgecolors="white", linewidth=2)
                ax_rsi.plot([from_idx, to_idx], [rsi_from, rsi_to],
                            color=color, linewidth=2, linestyle=":", alpha=0.9)

    if entry:
        entry_price = entry["entry"]
        sl_price = entry["stop_loss"]
        tp_price = entry["take_profit"]
        x_mid = len(plot_data) - 6
        x_last = len(plot_data) - 1

        color = "#00e676" if entry["action"] == "BUY" else "#ff1744"
        action = "ПОКУПКА" if entry["action"] == "BUY" else "ПРОДАЖА"

        ax1.axhline(y=entry_price, color="#ffffff", linewidth=2.5, alpha=0.8)
        ax1.annotate(f"{action}\n{entry_price}",
                     xy=(x_last, entry_price), xytext=(15, -25),
                     textcoords="offset points", fontsize=14, weight="bold",
                     color="#ffffff",
                     bbox=dict(boxstyle="round,pad=0.5", facecolor=color, alpha=0.9))

        ax1.axhline(y=sl_price, color="#ff1744", linewidth=2, linestyle="--", alpha=0.8)
        ax1.annotate(f"SL {sl_price}", xy=(x_mid, sl_price),
                     xytext=(5, -18), textcoords="offset points", fontsize=12,
                     color="#ffffff", weight="bold",
                     bbox=dict(boxstyle="round,pad=0.2", facecolor="#ff1744", alpha=0.85))

        rr = entry.get("risk_reward", "?")
        tp_label = f"TP {tp_price} (1:{rr})"
        ax1.axhline(y=tp_price, color="#00e676", linewidth=2, linestyle="--", alpha=0.8)
        ax1.annotate(tp_label, xy=(x_mid, tp_price),
                     xytext=(5, 5), textcoords="offset points", fontsize=12,
                     color="#ffffff", weight="bold",
                     bbox=dict(boxstyle="round,pad=0.2", facecolor="#00e676", alpha=0.85))

    ax1.set_xlim(-0.5, len(plot_data) - 0.5)

    time_fmt = "%H:%M" if tf in ("1m", "5m", "15m") else "%m/%d"
    tick_step = max(1, len(plot_data) // 8)
    tick_positions = list(range(0, len(plot_data), tick_step))
    tick_labels = [plot_data.index[i].strftime(time_fmt) for i in tick_positions]
    ax_rsi.set_xticks(tick_positions)
    ax_rsi.set_xticklabels(tick_labels, rotation=25, ha="right", color=text_c, fontsize=10)

    plt.savefig(filepath, dpi=180, bbox_inches="tight", facecolor=bg)
    plt.close(fig)
    return filepath
