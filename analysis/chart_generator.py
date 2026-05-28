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


def find_levels(df, lookback=80):
    recent = df.iloc[-lookback:]
    highs, lows = recent["high"].values, recent["low"].values

    def cluster(values, threshold=0.0005):
        vals = sorted(set(values))
        if not vals:
            return []
        result = [vals[0]]
        for v in vals[1:]:
            if abs(v - result[-1]) / max(abs(result[-1]), 0.0001) > threshold:
                result.append(v)
        return result

    res = sorted(cluster(highs), reverse=True)[:3]
    sup = sorted(cluster(lows))[:3]
    return {"resistance": [r for r in res if r], "support": [s for s in sup if s]}


def generate_chart(symbol, tf, df, div=None, entry=None):
    ensure_dir()
    name = symbol.replace("=X", "").replace("-USD", "")
    filename = f"{name}_{tf}_{pd.Timestamp.now().strftime('%H%M%S')}.png"
    filepath = os.path.join(CHARTS_DIR, filename)

    n = 250
    plot = df.iloc[-n:].copy()
    plot.index = pd.to_datetime(plot.index)
    x = np.arange(len(plot))
    n_actual = len(plot)

    bg, txt, grid = "#131722", "#d1d4dc", "#2a2e39"

    fig = plt.figure(figsize=(36, 14), facecolor=bg)
    gs = fig.add_gridspec(4, 1, height_ratios=[5, 0.4, 0.8, 0.8], hspace=0.02)

    ax = fig.add_subplot(gs[0, 0], facecolor=bg)
    ax_vol = fig.add_subplot(gs[1, 0], facecolor=bg, sharex=ax)
    ax_macd = fig.add_subplot(gs[2, 0], facecolor=bg, sharex=ax)
    ax_rsi = fig.add_subplot(gs[3, 0], facecolor=bg, sharex=ax)

    fig.suptitle(f"{name} ({tf}) — {pd.Timestamp.now().strftime('%d.%m %H:%M')}",
                 color=txt, fontsize=16, fontweight="bold", y=0.96)

    for a in [ax, ax_vol, ax_macd, ax_rsi]:
        a.set_facecolor(bg)
        a.tick_params(colors=txt, labelsize=9)
        a.grid(True, alpha=0.06, color=grid)
        for s in ["top", "right", "bottom", "left"]:
            a.spines[s].set_visible(False)

    opens = plot["open"].values
    highs = plot["high"].values
    lows = plot["low"].values
    closes = plot["close"].values
    up = closes >= opens
    down = ~up

    body_bot = np.where(up, opens, closes)
    body_h = np.maximum(np.abs(closes - opens), 1e-10)

    for i in range(n_actual):
        ax.plot([i, i], [lows[i], highs[i]],
                color="#787b86" if up[i] else "#787b86",
                linewidth=0.8, zorder=1, solid_capstyle="round")

    ax.bar(x[up], body_h[up], bottom=body_bot[up], width=0.55,
           color="#089981", edgecolor="#089981", linewidth=0.1, zorder=3)
    ax.bar(x[down], body_h[down], bottom=body_bot[down], width=0.55,
           color="#f23645", edgecolor="#f23645", linewidth=0.1, zorder=3)

    if "sma_20" in plot.columns:
        ax.plot(x, plot["sma_20"].values, color="#2962ff", linewidth=1.2, alpha=0.8, label="SMA20")
    if "sma_50" in plot.columns:
        ax.plot(x, plot["sma_50"].values, color="#ff9800", linewidth=1.2, alpha=0.8, label="SMA50")
    ax.legend(loc="upper left", fontsize=10, facecolor=bg, labelcolor=txt, edgecolor=grid)

    levels = find_levels(df)
    for s in levels["support"]:
        ax.axhline(y=s, color="#089981", linewidth=1, linestyle="--", alpha=0.35)
        ax.text(n_actual - 1, s, f"  S {s:.5f}", color="#089981", fontsize=9, weight="bold",
                ha="left", va="bottom",
                bbox=dict(fc=bg, ec="#089981", alpha=0.8, boxstyle="round,pad=0.1"))
    for r in levels["resistance"]:
        ax.axhline(y=r, color="#f23645", linewidth=1, linestyle="--", alpha=0.35)
        ax.text(n_actual - 1, r, f"  R {r:.5f}", color="#f23645", fontsize=9, weight="bold",
                ha="left", va="bottom",
                bbox=dict(fc=bg, ec="#f23645", alpha=0.8, boxstyle="round,pad=0.1"))

    if "volume" in plot.columns:
        vol = plot["volume"].values
        vol_norm = vol / vol.max() if vol.max() > 0 else vol
        colors_vol = np.where(up, "#089981", "#f23645")
        ax_vol.bar(x, vol_norm, color=colors_vol, width=0.7, alpha=0.4)
        ax_vol.set_ylim(bottom=0)
        ax_vol.set_ylabel("VOL", color=txt, fontsize=8, alpha=0.4)

    if all(c in plot.columns for c in ["macd", "macd_signal", "macd_hist"]):
        macd_val = plot["macd"].values
        signal = plot["macd_signal"].values
        hist = plot["macd_hist"].values
        ax_macd.plot(x, macd_val, color="#2962ff", linewidth=1, label="MACD")
        ax_macd.plot(x, signal, color="#ff9800", linewidth=1, label="Signal")
        bar_colors = np.where(hist >= 0, "#089981", "#f23645")
        ax_macd.bar(x, hist, color=bar_colors, width=0.7, alpha=0.4)
        ax_macd.axhline(y=0, color="#555", linestyle=":", alpha=0.15)
        ax_macd.legend(loc="upper left", fontsize=8, facecolor=bg, labelcolor=txt, edgecolor=grid, ncol=2)

    if "rsi" in plot.columns:
        rsi_vals = plot["rsi"].values
        ax_rsi.plot(x, rsi_vals, color="#787b86", linewidth=1.2, label="RSI")
        ax_rsi.axhline(y=70, color="#f23645", linestyle="--", alpha=0.25, linewidth=0.8)
        ax_rsi.axhline(y=30, color="#089981", linestyle="--", alpha=0.25, linewidth=0.8)
        ax_rsi.axhline(y=50, color="#555", linestyle=":", alpha=0.1, linewidth=0.5)
        ax_rsi.set_ylim(0, 100)
        ax_rsi.legend(loc="upper left", fontsize=8, facecolor=bg, labelcolor=txt, edgecolor=grid)

    if div:
        fi = max(0, div["from_idx"] - len(df) + n_actual)
        ti = max(0, div["to_idx"] - len(df) + n_actual)
        if fi < n_actual and ti < n_actual:
            p1, p2 = div["from_price"], div["to_price"]
            c = "#089981" if div["type"] == "bullish" else "#f23645"
            m = "^" if div["type"] == "bullish" else "v"

            ax.scatter([fi, ti], [p1, p2], color=c, s=200, zorder=10, marker=m,
                       edgecolors="white", linewidth=1.5)
            ax.plot([fi, ti], [p1, p2], color=c, linewidth=1.5, linestyle=":", alpha=0.7)

            label = f"{'БЫЧЬЯ' if div['type'] == 'bullish' else 'МЕДВЕЖЬЯ'} ДИВЕРГЕНЦИЯ"
            off = (-20, -30) if div["type"] == "bullish" else (20, 30)
            ax.annotate(label, xy=(ti, p2), xytext=off, textcoords="offset points",
                        fontsize=10, weight="bold", color=c,
                        arrowprops=dict(arrowstyle="->", color=c, lw=1.5),
                        bbox=dict(boxstyle="round,pad=0.25", facecolor=bg, edgecolor=c, alpha=0.85))

            if "rsi" in plot.columns:
                ax_rsi.scatter([fi, ti], [div["from_rsi"], div["to_rsi"]],
                               color=c, s=150, zorder=10, marker=m,
                               edgecolors="white", linewidth=1.5)
                ax_rsi.plot([fi, ti], [div["from_rsi"], div["to_rsi"]],
                            color=c, linewidth=1.5, linestyle=":", alpha=0.7)

    if entry:
        ep, sl, tp = entry["entry"], entry["stop_loss"], entry["take_profit"]
        x_label = n_actual - 1
        c = "#089981" if entry["action"] == "BUY" else "#f23645"
        act = "ПОКУПКА" if entry["action"] == "BUY" else "ПРОДАЖА"

        ax.axhline(y=ep, color="#ffffff", linewidth=1.2, alpha=0.4, linestyle="-", zorder=5)
        ax.annotate(f"{act}\n{ep:.5f}", xy=(x_label, ep), xytext=(10, -25),
                    textcoords="offset points", fontsize=12, weight="bold", color="#fff",
                    bbox=dict(boxstyle="round,pad=0.35", facecolor=c, alpha=0.95, edgecolor="white"))

        ax.axhline(y=sl, color="#f23645", linewidth=1.2, linestyle="--", alpha=0.5, zorder=5)
        ax.annotate(f"SL {sl:.5f}", xy=(x_label, sl), xytext=(10, -15),
                    textcoords="offset points", fontsize=10, color="#fff", weight="bold",
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="#f23645", alpha=0.9, edgecolor="white"))

        rr = entry.get("risk_reward", "?")
        ax.axhline(y=tp, color="#089981", linewidth=1.2, linestyle="--", alpha=0.5, zorder=5)
        ax.annotate(f"TP {tp:.5f} (1:{rr})", xy=(x_label, tp), xytext=(10, 5),
                    textcoords="offset points", fontsize=10, color="#fff", weight="bold",
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="#089981", alpha=0.9, edgecolor="white"))

    ax.set_xlim(-1, n_actual + 1)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:.5f}"))
    ax.yaxis.tick_right()
    ax.tick_params(labelbottom=False)

    fmt = "%d.%m" if n_actual > 50 else "%H:%M"
    step = max(1, n_actual // 12)
    tick_pos = list(range(0, n_actual, step))
    tick_lbl = [plot.index[i].strftime(fmt) for i in tick_pos]
    ax_rsi.set_xticks(tick_pos)
    ax_rsi.set_xticklabels(tick_lbl, rotation=15, ha="right", color=txt, fontsize=7)

    plt.savefig(filepath, dpi=200, bbox_inches="tight", facecolor=bg)
    plt.close(fig)
    return filepath
