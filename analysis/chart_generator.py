import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

CHARTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "charts")


def ensure_dir():
    os.makedirs(CHARTS_DIR, exist_ok=True)


def find_levels(df, lookback=50):
    recent = df.iloc[-lookback:]
    highs, lows = recent["high"].values, recent["low"].values

    def cluster(values, threshold=0.0006):
        vals = sorted(set(values))
        if not vals:
            return []
        result = [vals[0]]
        for v in vals[1:]:
            if abs(v - result[-1]) / max(abs(result[-1]), 0.0001) > threshold:
                result.append(v)
        return result

    res = sorted(cluster(highs), reverse=True)[:2]
    sup = sorted(cluster(lows))[:2]
    return {"resistance": [r for r in res if r], "support": [s for s in sup if s]}


def generate_chart(symbol, tf, df, div=None, entry=None):
    ensure_dir()
    name = symbol.replace("=X", "").replace("-USD", "")
    filename = f"{name}_{tf}_{pd.Timestamp.now().strftime('%H%M%S')}.png"
    filepath = os.path.join(CHARTS_DIR, filename)

    n = 70
    plot = df.iloc[-n:].copy()
    plot.index = pd.to_datetime(plot.index)
    x = np.arange(len(plot))
    n_actual = len(plot)

    bg, txt, grid = "#0d1117", "#e6edf3", "#21262d"

    fig = plt.figure(figsize=(30, 14), facecolor=bg)
    gs = fig.add_gridspec(2, 1, height_ratios=[5, 1], hspace=0.04)

    ax = fig.add_subplot(gs[0, 0], facecolor=bg)
    ax_rsi = fig.add_subplot(gs[1, 0], facecolor=bg, sharex=ax)

    fig.suptitle(f"{name} ({tf}) — {pd.Timestamp.now().strftime('%d.%m %H:%M')}",
                 color=txt, fontsize=22, fontweight="bold", y=0.96)

    for a in [ax, ax_rsi]:
        a.set_facecolor(bg)
        a.tick_params(colors=txt, labelsize=12)
        a.grid(True, alpha=0.15, color=grid)
        for s in ["top", "right", "bottom", "left"]:
            a.spines[s].set_visible(False)

    up_color, down_color = "#3fb950", "#f85149"
    wick_up, wick_down = "#3fb950", "#f85149"

    opens = plot["open"].values
    highs = plot["high"].values
    lows = plot["low"].values
    closes = plot["close"].values
    up = closes >= opens
    down = ~up

    body_bot = np.where(up, opens, closes)
    body_top = np.where(up, closes, opens)
    body_h = np.maximum(body_top - body_bot, 1e-10)

    for i in range(n_actual):
        wc = wick_up if up[i] else wick_down
        ax.plot([i, i], [lows[i], highs[i]],
                color=wc, linewidth=1.2, zorder=1, solid_capstyle="round")

    ax.bar(x[up], body_h[up], bottom=body_bot[up], width=0.8,
           color=up_color, edgecolor=up_color, linewidth=0.5, zorder=3)
    ax.bar(x[down], body_h[down], bottom=body_bot[down], width=0.8,
           color=down_color, edgecolor=down_color, linewidth=0.5, zorder=3)

    price_max = highs.max()
    price_min = lows.min()
    price_range = price_max - price_min
    padding = price_range * 0.08 if price_range > 0 else 0.001
    ax.set_ylim(price_min - padding, price_max + padding)

    if "sma_20" in plot.columns:
        ax.plot(x, plot["sma_20"].values, color="#58a6ff", linewidth=2.5, alpha=0.9, label="SMA20")
    if "sma_50" in plot.columns:
        ax.plot(x, plot["sma_50"].values, color="#d29922", linewidth=2.5, alpha=0.9, label="SMA50")
    ax.legend(loc="upper left", fontsize=14, facecolor=bg, labelcolor=txt, edgecolor=grid)

    levels = find_levels(df)
    for s in levels["support"]:
        ax.axhline(y=s, color="#3fb950", linewidth=2.0, linestyle="--", alpha=0.6)
        ax.text(n_actual - 1, s, f"  S {s:.5f}", color="#3fb950", fontsize=13, weight="bold",
                ha="left", va="bottom",
                bbox=dict(fc=bg, ec="#3fb950", alpha=0.9, boxstyle="round,pad=0.2"))
    for r in levels["resistance"]:
        ax.axhline(y=r, color="#f85149", linewidth=2.0, linestyle="--", alpha=0.6)
        ax.text(n_actual - 1, r, f"  R {r:.5f}", color="#f85149", fontsize=13, weight="bold",
                ha="left", va="bottom",
                bbox=dict(fc=bg, ec="#f85149", alpha=0.9, boxstyle="round,pad=0.2"))

    if "rsi" in plot.columns:
        rsi_vals = plot["rsi"].values
        ax_rsi.plot(x, rsi_vals, color="#bc8cff", linewidth=2.5, label="RSI")
        ax_rsi.axhline(y=70, color="#f85149", linestyle="--", alpha=0.4, linewidth=1.5)
        ax_rsi.axhline(y=30, color="#3fb950", linestyle="--", alpha=0.4, linewidth=1.5)
        ax_rsi.axhline(y=50, color="#555", linestyle=":", alpha=0.15, linewidth=0.8)
        ax_rsi.set_ylim(0, 100)
        ax_rsi.fill_between(x, 30, 70, alpha=0.05, color="#fff")
        ax_rsi.legend(loc="upper left", fontsize=13, facecolor=bg, labelcolor=txt, edgecolor=grid)

    if div:
        fi = max(0, div["from_idx"] - len(df) + n_actual)
        ti = max(0, div["to_idx"] - len(df) + n_actual)
        if fi < n_actual and ti < n_actual:
            p1, p2 = div["from_price"], div["to_price"]
            c = up_color if div["type"] == "bullish" else down_color
            m = "^" if div["type"] == "bullish" else "v"

            ax.scatter([fi, ti], [p1, p2], color=c, s=400, zorder=10, marker=m,
                       edgecolors="white", linewidth=3)
            ax.plot([fi, ti], [p1, p2], color=c, linewidth=3.0, linestyle=":", alpha=0.9)

            label = f"{'БЫЧЬЯ' if div['type'] == 'bullish' else 'МЕДВЕЖЬЯ'} ДИВЕРГЕНЦИЯ"
            off = (-40, -60) if div["type"] == "bullish" else (40, 60)
            ax.annotate(label, xy=(ti, p2), xytext=off, textcoords="offset points",
                        fontsize=14, weight="bold", color=c,
                        arrowprops=dict(arrowstyle="->", color=c, lw=3),
                        bbox=dict(boxstyle="round,pad=0.4", facecolor=bg, edgecolor=c, alpha=0.9))

            if "rsi" in plot.columns:
                ax_rsi.scatter([fi, ti], [div["from_rsi"], div["to_rsi"]],
                               color=c, s=300, zorder=10, marker=m,
                               edgecolors="white", linewidth=2.5)
                ax_rsi.plot([fi, ti], [div["from_rsi"], div["to_rsi"]],
                            color=c, linewidth=2.5, linestyle=":", alpha=0.9)

    if entry:
        ep, sl, tp = entry["entry"], entry["stop_loss"], entry["take_profit"]
        x_label = n_actual - 1
        c = "#3fb950" if entry["action"] == "BUY" else "#f85149"
        act = "ПОКУПКА" if entry["action"] == "BUY" else "ПРОДАЖА"
        rr = entry.get("risk_reward", "?")

        ax.axhline(y=ep, color="#ffffff", linewidth=1.5, alpha=0.5, linestyle="-", zorder=5)
        ax.axhline(y=sl, color="#f85149", linewidth=1.5, linestyle="--", alpha=0.5, zorder=5)
        ax.axhline(y=tp, color="#3fb950", linewidth=1.5, linestyle="--", alpha=0.5, zorder=5)

        info_text = f"{act} {ep:.5f} | SL {sl:.5f} | TP {tp:.5f} (1:{rr})"
        ax.annotate(info_text, xy=(n_actual // 2, 1), xytext=(0, 0),
                    textcoords="axes fraction", fontsize=16, weight="bold", color="#fff",
                    ha="center", va="top",
                    bbox=dict(boxstyle="round,pad=0.4", facecolor=c, alpha=0.85, edgecolor="white"))

    ax.set_xlim(-1, n_actual + 1)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:.5f}"))
    ax.yaxis.tick_right()
    ax.tick_params(labelbottom=False)
    ax.tick_params(axis="y", labelsize=13)

    fmt = "%d.%m %H:%M"
    step = max(1, n_actual // 8)
    tick_pos = list(range(0, n_actual, step))
    tick_lbl = [plot.index[i].strftime(fmt) for i in tick_pos]
    ax_rsi.set_xticks(tick_pos)
    ax_rsi.set_xticklabels(tick_lbl, rotation=20, ha="right", color=txt, fontsize=11)

    plt.savefig(filepath, dpi=220, bbox_inches="tight", facecolor=bg)
    plt.close(fig)
    return filepath
