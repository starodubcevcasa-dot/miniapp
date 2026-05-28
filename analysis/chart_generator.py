import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

CHARTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "charts")


def ensure_dir():
    os.makedirs(CHARTS_DIR, exist_ok=True)


def find_levels(df, lookback=40):
    recent = df.iloc[-lookback:]
    highs, lows = recent["high"].values, recent["low"].values

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


def generate_chart(symbol, tf, df, div=None, entry=None):
    ensure_dir()
    name = symbol.replace("=X", "").replace("-USD", "")
    filename = f"{name}_{tf}_{pd.Timestamp.now().strftime('%H%M%S')}.png"
    filepath = os.path.join(CHARTS_DIR, filename)

    n = 35
    plot = df.iloc[-n:].copy()
    plot.index = pd.to_datetime(plot.index)
    x = np.arange(n)

    bg, txt, grid = "#131722", "#d1d4dc", "#2a2e39"

    fig = plt.figure(figsize=(20, 12), facecolor=bg)
    gs = fig.add_gridspec(4, 1, height_ratios=[4, 0.8, 1.2, 0.6], hspace=0.05)

    ax = fig.add_subplot(gs[0, 0], facecolor=bg)
    ax_v = fig.add_subplot(gs[1, 0], facecolor=bg, sharex=ax)
    ax_r = fig.add_subplot(gs[2, 0], facecolor=bg, sharex=ax)

    fig.suptitle(f"{name} ({tf}) — {pd.Timestamp.now().strftime('%d.%m %H:%M')}",
                 color=txt, fontsize=18, fontweight="bold", y=0.98)

    for a in [ax, ax_v, ax_r]:
        a.set_facecolor(bg)
        a.tick_params(colors=txt, labelsize=11)
        a.grid(True, alpha=0.1, color=grid)
        for s in ["top", "right", "bottom", "left"]:
            a.spines[s].set_visible(False)

    opens, highs, lows, closes = plot["open"].values, plot["high"].values, plot["low"].values, plot["close"].values
    up = closes >= opens
    down = ~up

    # Candles: wicks
    for i in range(n):
        ax.plot([i, i], [lows[i], highs[i]], color="#a6b1c9" if up[i] else "#ef5350", linewidth=1.2, zorder=1)

    # Candles: bodies
    ax.bar(x[up], closes[up] - opens[up], bottom=opens[up], width=0.7, color="#00e676", edgecolor="#00e676", linewidth=0.5, zorder=2)
    ax.bar(x[down], closes[down] - opens[down], bottom=opens[down], width=0.7, color="#ff1744", edgecolor="#ff1744", linewidth=0.5, zorder=2)

    # SMA
    if "sma_20" in plot.columns:
        ax.plot(x, plot["sma_20"].values, color="#2196f3", linewidth=1.5, alpha=0.8, label="SMA20")
    if "sma_50" in plot.columns:
        ax.plot(x, plot["sma_50"].values, color="#ff9800", linewidth=1.5, alpha=0.8, label="SMA50")
    ax.legend(loc="upper left", fontsize=11, facecolor=bg, labelcolor=txt, edgecolor=grid)

    # S/R
    levels = find_levels(df)
    for s in levels["support"]:
        ax.axhline(y=s, color="#00e676", linewidth=1.5, linestyle="--", alpha=0.6)
        ax.text(n - 1, s, f"S {s:.5f}", color="#00e676", fontsize=12, weight="bold",
                ha="right", va="bottom",
                bbox=dict(fc=bg, ec="#00e676", alpha=0.8, boxstyle="round,pad=0.2"))
    for r in levels["resistance"]:
        ax.axhline(y=r, color="#ff1744", linewidth=1.5, linestyle="--", alpha=0.6)
        ax.text(n - 1, r, f"R {r:.5f}", color="#ff1744", fontsize=12, weight="bold",
                ha="right", va="bottom",
                bbox=dict(fc=bg, ec="#ff1744", alpha=0.8, boxstyle="round,pad=0.2"))

    # Volume
    if "volume" in plot.columns:
        vol = plot["volume"].values
        colors_v = np.where(up, "#00e676", "#ff1744")
        ax_v.bar(x, vol, color=colors_v, width=0.8, alpha=0.6)
        ax_v.set_ylim(bottom=0)

    # RSI
    if "rsi" in plot.columns:
        rsi_vals = plot["rsi"].values
        ax_r.plot(x, rsi_vals, color="#bb86fc", linewidth=2, label="RSI")
        ax_r.axhline(y=70, color="#ff1744", linestyle="--", alpha=0.3, linewidth=1)
        ax_r.axhline(y=30, color="#00e676", linestyle="--", alpha=0.3, linewidth=1)
        ax_r.axhline(y=50, color="#555", linestyle=":", alpha=0.2, linewidth=0.8)
        ax_r.set_ylim(0, 100)
        ax_r.legend(loc="upper left", fontsize=11, facecolor=bg, labelcolor=txt, edgecolor=grid)

    # Divergence
    if div:
        fi = max(0, div["from_idx"] - len(df) + n)
        ti = max(0, div["to_idx"] - len(df) + n)
        if fi < n and ti < n:
            p1, p2 = div["from_price"], div["to_price"]
            c = "#00e676" if div["type"] == "bullish" else "#ff1744"
            m = "^" if div["type"] == "bullish" else "v"

            ax.scatter([fi, ti], [p1, p2], color=c, s=250, zorder=10, marker=m,
                       edgecolors="white", linewidth=2.5)
            ax.plot([fi, ti], [p1, p2], color=c, linewidth=2.5, linestyle=":", alpha=0.9)

            label = f"{'БЫЧЬЯ' if div['type'] == 'bullish' else 'МЕДВЕЖЬЯ'} ДИВЕРГЕНЦИЯ"
            off = (-30, -60) if div["type"] == "bullish" else (30, 60)
            ax.annotate(label, xy=(ti, p2), xytext=off, textcoords="offset points",
                        fontsize=13, weight="bold", color=c,
                        arrowprops=dict(arrowstyle="->", color=c, lw=2.5),
                        bbox=dict(boxstyle="round,pad=0.4", facecolor=bg, edgecolor=c, alpha=0.85))

            if "rsi" in plot.columns:
                ax_r.scatter([fi, ti], [div["from_rsi"], div["to_rsi"]],
                             color=c, s=180, zorder=10, marker=m,
                             edgecolors="white", linewidth=2)
                ax_r.plot([fi, ti], [div["from_rsi"], div["to_rsi"]],
                          color=c, linewidth=2, linestyle=":", alpha=0.9)

    # Entry
    if entry:
        ep, sl, tp = entry["entry"], entry["stop_loss"], entry["take_profit"]
        xm, xl = n - 6, n - 1
        c = "#00e676" if entry["action"] == "BUY" else "#ff1744"
        act = "ПОКУПКА" if entry["action"] == "BUY" else "ПРОДАЖА"

        ax.axhline(y=ep, color="#fff", linewidth=2.5, alpha=0.8)
        ax.annotate(f"{act}\n{ep}", xy=(xl, ep), xytext=(15, -25),
                    textcoords="offset points", fontsize=14, weight="bold", color="#fff",
                    bbox=dict(boxstyle="round,pad=0.5", facecolor=c, alpha=0.9))

        ax.axhline(y=sl, color="#ff1744", linewidth=2, linestyle="--", alpha=0.8)
        ax.annotate(f"SL {sl}", xy=(xm, sl), xytext=(5, -18),
                    textcoords="offset points", fontsize=12, color="#fff", weight="bold",
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="#ff1744", alpha=0.85))

        rr = entry.get("risk_reward", "?")
        ax.axhline(y=tp, color="#00e676", linewidth=2, linestyle="--", alpha=0.8)
        ax.annotate(f"TP {tp} (1:{rr})", xy=(xm, tp), xytext=(5, 5),
                    textcoords="offset points", fontsize=12, color="#fff", weight="bold",
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="#00e676", alpha=0.85))

    ax.set_xlim(-0.5, n - 0.5)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.5f}"))

    fmt = "%H:%M" if tf in ("1m", "5m", "15m") else "%m/%d"
    step = max(1, n // 8)
    tick_pos = list(range(0, n, step))
    tick_lbl = [plot.index[i].strftime(fmt) for i in tick_pos]
    ax_r.set_xticks(tick_pos)
    ax_r.set_xticklabels(tick_lbl, rotation=25, ha="right", color=txt, fontsize=10)

    plt.savefig(filepath, dpi=180, bbox_inches="tight", facecolor=bg)
    plt.close(fig)
    return filepath
