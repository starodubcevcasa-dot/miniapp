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

    n = 80
    plot = df.iloc[-n:].copy()
    plot.index = pd.to_datetime(plot.index)
    x = np.arange(len(plot))
    n_actual = len(plot)

    bg = "#131722"
    txt = "#d1d4dc"
    grid = "#2a2e39"
    up_c = "#089981"
    down_c = "#f23645"

    fig = plt.figure(figsize=(36, 14), facecolor=bg)
    gs = fig.add_gridspec(2, 1, height_ratios=[5, 1], hspace=0.03)

    ax = fig.add_subplot(gs[0, 0], facecolor=bg)
    ax_rsi = fig.add_subplot(gs[1, 0], facecolor=bg, sharex=ax)

    fig.suptitle(f"{name} ({tf}) — {pd.Timestamp.now().strftime('%d.%m %H:%M')}",
                 color=txt, fontsize=16, fontweight="bold", y=0.97)

    for a in [ax, ax_rsi]:
        a.set_facecolor(bg)
        a.tick_params(colors=txt, labelsize=10)
        a.grid(True, alpha=0.08, color=grid)
        for s in ["top", "right", "bottom", "left"]:
            a.spines[s].set_visible(False)

    opens = plot["open"].values
    highs = plot["high"].values
    lows = plot["low"].values
    closes = plot["close"].values
    up = closes >= opens
    down = ~up

    body_bot = np.where(up, opens, closes)
    body_top = np.where(up, closes, opens)
    body_h = body_top - body_bot
    is_doji = body_h == 0

    candle_w = 0.7
    for i in range(n_actual):
        wc = up_c if up[i] else down_c
        ax.plot([i, i], [lows[i], highs[i]], color=wc, linewidth=0.8, zorder=1)

    up_idx = np.where(up & ~is_doji)[0]
    down_idx = np.where(down & ~is_doji)[0]
    doji_idx = np.where(is_doji)[0]

    if len(up_idx) > 0:
        ax.bar(x[up_idx], body_h[up_idx], bottom=body_bot[up_idx], width=candle_w,
               color=up_c, edgecolor=up_c, linewidth=0.3, zorder=3)
    if len(down_idx) > 0:
        ax.bar(x[down_idx], body_h[down_idx], bottom=body_bot[down_idx], width=candle_w,
               color=down_c, edgecolor=down_c, linewidth=0.3, zorder=3)
    for i in doji_idx:
        ax.plot([i - candle_w / 2, i + candle_w / 2], [closes[i], closes[i]],
                color=up_c if up[i] else down_c, linewidth=1.5, zorder=3)

    price_max = highs.max()
    price_min = lows.min()
    price_range = price_max - price_min
    pad = price_range * 0.05 if price_range > 0 else 0.001
    ax.set_ylim(price_min - pad, price_max + pad)

    if "sma_20" in plot.columns:
        ax.plot(x, plot["sma_20"].values, color="#2962ff", linewidth=1.2, alpha=0.8, label="SMA20")
    if "sma_50" in plot.columns:
        ax.plot(x, plot["sma_50"].values, color="#ff9800", linewidth=1.2, alpha=0.8, label="SMA50")
    ax.legend(loc="upper left", fontsize=11, facecolor=bg, labelcolor=txt, edgecolor=grid)

    levels = find_levels(df)
    for s in levels["support"]:
        ax.axhline(y=s, color=up_c, linewidth=1, linestyle="--", alpha=0.35)
        ax.text(n_actual - 1, s, f"  S {s:.5f}", color=up_c, fontsize=10, weight="bold",
                ha="left", va="bottom", bbox=dict(fc=bg, ec=up_c, alpha=0.8, boxstyle="round,pad=0.1"))
    for r in levels["resistance"]:
        ax.axhline(y=r, color=down_c, linewidth=1, linestyle="--", alpha=0.35)
        ax.text(n_actual - 1, r, f"  R {r:.5f}", color=down_c, fontsize=10, weight="bold",
                ha="left", va="bottom", bbox=dict(fc=bg, ec=down_c, alpha=0.8, boxstyle="round,pad=0.1"))

    if "rsi" in plot.columns:
        rsi_vals = plot["rsi"].values
        ax_rsi.plot(x, rsi_vals, color="#787b86", linewidth=1.5, label="RSI")
        ax_rsi.axhline(y=70, color=down_c, linestyle="--", alpha=0.3, linewidth=0.8)
        ax_rsi.axhline(y=30, color=up_c, linestyle="--", alpha=0.3, linewidth=0.8)
        ax_rsi.axhline(y=50, color="#555", linestyle=":", alpha=0.1, linewidth=0.5)
        ax_rsi.set_ylim(0, 100)
        ax_rsi.fill_between(x, 30, 70, alpha=0.03, color="#fff")
        ax_rsi.legend(loc="upper left", fontsize=10, facecolor=bg, labelcolor=txt, edgecolor=grid)

    if div:
        fi = max(0, div["from_idx"] - len(df) + n_actual)
        ti = max(0, div["to_idx"] - len(df) + n_actual)
        if fi < n_actual and ti < n_actual:
            p1, p2 = div["from_price"], div["to_price"]
            dc = up_c if div["type"] == "bullish" else down_c
            m = "^" if div["type"] == "bullish" else "v"

            ax.scatter([fi, ti], [p1, p2], color=dc, s=200, zorder=10, marker=m,
                       edgecolors="white", linewidth=1.5)
            ax.plot([fi, ti], [p1, p2], color=dc, linewidth=1.5, linestyle=":", alpha=0.7)

            lbl = f"{'БЫЧЬЯ' if div['type'] == 'bullish' else 'МЕДВЕЖЬЯ'} ДИВЕРГЕНЦИЯ"
            off = (-20, -30) if div["type"] == "bullish" else (20, 30)
            ax.annotate(lbl, xy=(ti, p2), xytext=off, textcoords="offset points",
                        fontsize=10, weight="bold", color=dc,
                        arrowprops=dict(arrowstyle="->", color=dc, lw=1.5),
                        bbox=dict(boxstyle="round,pad=0.25", facecolor=bg, edgecolor=dc, alpha=0.85))

            if "rsi" in plot.columns:
                ax_rsi.scatter([fi, ti], [div["from_rsi"], div["to_rsi"]],
                               color=dc, s=150, zorder=10, marker=m,
                               edgecolors="white", linewidth=1.5)
                ax_rsi.plot([fi, ti], [div["from_rsi"], div["to_rsi"]],
                            color=dc, linewidth=1.5, linestyle=":", alpha=0.7)

    if entry:
        ep, sl, tp = entry["entry"], entry["stop_loss"], entry["take_profit"]
        dc = up_c if entry["action"] == "BUY" else down_c
        act = "ПОКУПКА" if entry["action"] == "BUY" else "ПРОДАЖА"
        rr = entry.get("risk_reward", "?")

        ax.axhline(y=ep, color="#ffffff", linewidth=1, alpha=0.4, linestyle="-", zorder=5)
        ax.axhline(y=sl, color=down_c, linewidth=1, linestyle="--", alpha=0.4, zorder=5)
        ax.axhline(y=tp, color=up_c, linewidth=1, linestyle="--", alpha=0.4, zorder=5)

        info_text = f"{act} {ep:.5f} | SL {sl:.5f} | TP {tp:.5f} (1:{rr})"
        ax.annotate(info_text, xy=(0.5, 1), xytext=(0, 0),
                    textcoords="axes fraction", fontsize=14, weight="bold", color="#fff",
                    ha="center", va="top",
                    bbox=dict(boxstyle="round,pad=0.35", facecolor=dc, alpha=0.85, edgecolor="white"))

    ax.set_xlim(-1, n_actual + 1)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:.5f}"))
    ax.yaxis.tick_right()
    ax.tick_params(labelbottom=False)
    ax.tick_params(axis="y", labelsize=11)

    fmt = "%d.%m %H:%M"
    step = max(1, n_actual // 10)
    tick_pos = list(range(0, n_actual, step))
    tick_lbl = [plot.index[i].strftime(fmt) for i in tick_pos]
    ax_rsi.set_xticks(tick_pos)
    ax_rsi.set_xticklabels(tick_lbl, rotation=15, ha="right", color=txt, fontsize=9)

    plt.savefig(filepath, dpi=200, bbox_inches="tight", facecolor=bg)
    plt.close(fig)
    return filepath
