import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

CHARTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "charts")


def ensure_dir():
    os.makedirs(CHARTS_DIR, exist_ok=True)


def find_levels(df, lookback=60):
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

    return {
        "resistance": sorted(cluster(highs), reverse=True)[:3],
        "support": sorted(cluster(lows))[:3],
    }


def generate_chart(symbol, tf, df, div=None, entry=None):
    ensure_dir()
    name = symbol.replace("=X", "").replace("-USD", "")
    filename = f"{name}_{tf}_{pd.Timestamp.now().strftime('%H%M%S')}.png"
    filepath = os.path.join(CHARTS_DIR, filename)

    n = 120
    plot = df.iloc[-n:].copy()
    plot.index = pd.to_datetime(plot.index)
    x = np.arange(n)

    bg, txt, grid = "#131722", "#d1d4dc", "#2a2e39"

    fig = plt.figure(figsize=(32, 12), facecolor=bg)
    gs = fig.add_gridspec(5, 1, height_ratios=[5, 0.5, 1, 0.7, 0.5], hspace=0.02)

    ax = fig.add_subplot(gs[0, 0], facecolor=bg)
    ax_vol = fig.add_subplot(gs[1, 0], facecolor=bg, sharex=ax)
    ax_macd = fig.add_subplot(gs[2, 0], facecolor=bg, sharex=ax)
    ax_rsi = fig.add_subplot(gs[3, 0], facecolor=bg, sharex=ax)
    ax_stoch = fig.add_subplot(gs[4, 0], facecolor=bg, sharex=ax)

    fig.suptitle(f"{name} ({tf}) — {pd.Timestamp.now().strftime('%d.%m %H:%M')}",
                 color=txt, fontsize=18, fontweight="bold", y=0.97)

    for a in [ax, ax_vol, ax_macd, ax_rsi, ax_stoch]:
        a.set_facecolor(bg)
        a.tick_params(colors=txt, labelsize=9)
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
    body_h = np.maximum(np.abs(closes - opens), 1e-10)

    for i in range(n):
        ax.plot([i, i], [lows[i], highs[i]],
                color="#a6b1c9" if up[i] else "#ef5350",
                linewidth=1.2, zorder=1, solid_capstyle="round")

    ax.bar(x[up], body_h[up], bottom=body_bot[up], width=0.7,
           color="#26a69a", edgecolor="#26a69a", linewidth=0.3, zorder=3)
    ax.bar(x[down], body_h[down], bottom=body_bot[down], width=0.7,
           color="#ef5350", edgecolor="#ef5350", linewidth=0.3, zorder=3)

    if "sma_20" in plot.columns:
        ax.plot(x, plot["sma_20"].values, color="#1e88e5", linewidth=1.5, alpha=0.85, label="SMA20")
    if "sma_50" in plot.columns:
        ax.plot(x, plot["sma_50"].values, color="#ffa726", linewidth=1.5, alpha=0.85, label="SMA50")
    ax.legend(loc="upper left", fontsize=11, facecolor=bg, labelcolor=txt, edgecolor=grid)

    levels = find_levels(df)
    for s in levels["support"]:
        ax.axhline(y=s, color="#4caf50", linewidth=1.2, linestyle="--", alpha=0.5)
        ax.text(n - 1, s, f"  S {s:.5f}", color="#4caf50", fontsize=10, weight="bold",
                ha="left", va="bottom",
                bbox=dict(fc=bg, ec="#4caf50", alpha=0.85, boxstyle="round,pad=0.15"))
    for r in levels["resistance"]:
        ax.axhline(y=r, color="#f44336", linewidth=1.2, linestyle="--", alpha=0.5)
        ax.text(n - 1, r, f"  R {r:.5f}", color="#f44336", fontsize=10, weight="bold",
                ha="left", va="bottom",
                bbox=dict(fc=bg, ec="#f44336", alpha=0.85, boxstyle="round,pad=0.15"))

    if "volume" in plot.columns:
        vol = plot["volume"].values
        vol_norm = vol / vol.max() if vol.max() > 0 else vol
        colors_vol = np.where(up, "#26a69a", "#ef5350")
        ax_vol.bar(x, vol_norm, color=colors_vol, width=0.8, alpha=0.5)
        ax_vol.set_ylim(bottom=0)
        ax_vol.set_ylabel("VOL", color=txt, fontsize=8, alpha=0.5)

    if all(c in plot.columns for c in ["macd", "macd_signal", "macd_hist"]):
        macd_val = plot["macd"].values
        signal = plot["macd_signal"].values
        hist = plot["macd_hist"].values
        ax_macd.plot(x, macd_val, color="#42a5f5", linewidth=1.2, label="MACD")
        ax_macd.plot(x, signal, color="#ffa726", linewidth=1.2, label="Signal")
        bar_colors = np.where(hist >= 0, "#26a69a", "#ef5350")
        ax_macd.bar(x, hist, color=bar_colors, width=0.8, alpha=0.5)
        ax_macd.axhline(y=0, color="#555", linestyle=":", alpha=0.2)
        ax_macd.legend(loc="upper left", fontsize=9, facecolor=bg, labelcolor=txt, edgecolor=grid)
        ax_macd.set_ylabel("MACD", color=txt, fontsize=8, alpha=0.5)

    if "rsi" in plot.columns:
        rsi_vals = plot["rsi"].values
        ax_rsi.plot(x, rsi_vals, color="#ce93d8", linewidth=1.5, label="RSI")
        ax_rsi.axhline(y=70, color="#ef5350", linestyle="--", alpha=0.3, linewidth=1)
        ax_rsi.axhline(y=30, color="#4caf50", linestyle="--", alpha=0.3, linewidth=1)
        ax_rsi.axhline(y=50, color="#555", linestyle=":", alpha=0.15, linewidth=0.6)
        ax_rsi.set_ylim(0, 100)
        ax_rsi.fill_between(x, 30, 70, alpha=0.03, color="#fff")
        ax_rsi.legend(loc="upper left", fontsize=9, facecolor=bg, labelcolor=txt, edgecolor=grid)
        ax_rsi.set_ylabel("RSI", color=txt, fontsize=8, alpha=0.5)

    if "stoch_k" in plot.columns:
        stoch_k = plot["stoch_k"].values
        stoch_d = plot["stoch_d"].values
        ax_stoch.plot(x, stoch_k, color="#42a5f5", linewidth=1.2, label="%K")
        ax_stoch.plot(x, stoch_d, color="#ffa726", linewidth=1.2, linestyle="--", label="%D")
        ax_stoch.axhline(y=80, color="#ef5350", linestyle="--", alpha=0.2, linewidth=0.6)
        ax_stoch.axhline(y=20, color="#4caf50", linestyle="--", alpha=0.2, linewidth=0.6)
        ax_stoch.set_ylim(0, 100)
        ax_stoch.legend(loc="upper left", fontsize=9, facecolor=bg, labelcolor=txt, edgecolor=grid)
        ax_stoch.set_ylabel("Stoch", color=txt, fontsize=8, alpha=0.5)
        ax_stoch.fill_between(x, 20, 80, alpha=0.03, color="#fff")

    if div:
        fi = max(0, div["from_idx"] - len(df) + n)
        ti = max(0, div["to_idx"] - len(df) + n)
        if fi < n and ti < n:
            p1, p2 = div["from_price"], div["to_price"]
            c = "#4caf50" if div["type"] == "bullish" else "#ef5350"
            m = "^" if div["type"] == "bullish" else "v"

            ax.scatter([fi, ti], [p1, p2], color=c, s=300, zorder=10, marker=m,
                       edgecolors="white", linewidth=2)
            ax.plot([fi, ti], [p1, p2], color=c, linewidth=2, linestyle=":", alpha=0.8)

            label = f"{'БЫЧЬЯ' if div['type'] == 'bullish' else 'МЕДВЕЖЬЯ'} ДИВЕРГЕНЦИЯ"
            off = (-30, -40) if div["type"] == "bullish" else (30, 40)
            ax.annotate(label, xy=(ti, p2), xytext=off, textcoords="offset points",
                        fontsize=12, weight="bold", color=c,
                        arrowprops=dict(arrowstyle="->", color=c, lw=2),
                        bbox=dict(boxstyle="round,pad=0.3", facecolor=bg, edgecolor=c, alpha=0.85))

            if "rsi" in plot.columns:
                ax_rsi.scatter([fi, ti], [div["from_rsi"], div["to_rsi"]],
                               color=c, s=200, zorder=10, marker=m,
                               edgecolors="white", linewidth=1.5)
                ax_rsi.plot([fi, ti], [div["from_rsi"], div["to_rsi"]],
                            color=c, linewidth=1.5, linestyle=":", alpha=0.8)

            if "stoch_k" in plot.columns:
                ax_stoch.scatter([fi, ti], [div.get("from_stoch", 50), div.get("to_stoch", 50)],
                                 color=c, s=150, zorder=10, marker=m,
                                 edgecolors="white", linewidth=1.5)
                ax_stoch.plot([fi, ti], [div.get("from_stoch", 50), div.get("to_stoch", 50)],
                              color=c, linewidth=1.5, linestyle=":", alpha=0.8)

    if entry:
        ep, sl, tp = entry["entry"], entry["stop_loss"], entry["take_profit"]
        xm, xl = n - 10, n - 1
        c = "#4caf50" if entry["action"] == "BUY" else "#ef5350"
        act = "ПОКУПКА" if entry["action"] == "BUY" else "ПРОДАЖА"

        ax.axhline(y=ep, color="#ffffff", linewidth=1.5, alpha=0.5, linestyle="-", zorder=5)
        ax.annotate(f"{act}\n{ep:.5f}", xy=(xl, ep), xytext=(12, -28),
                    textcoords="offset points", fontsize=14, weight="bold", color="#fff",
                    bbox=dict(boxstyle="round,pad=0.4", facecolor=c, alpha=0.95, edgecolor="white"))

        ax.axhline(y=sl, color="#ef5350", linewidth=1.5, linestyle="--", alpha=0.6, zorder=5)
        ax.annotate(f"SL {sl:.5f}", xy=(xm, sl), xytext=(5, -18),
                    textcoords="offset points", fontsize=12, color="#fff", weight="bold",
                    bbox=dict(boxstyle="round,pad=0.25", facecolor="#ef5350", alpha=0.9, edgecolor="white"))

        rr = entry.get("risk_reward", "?")
        ax.axhline(y=tp, color="#4caf50", linewidth=1.5, linestyle="--", alpha=0.6, zorder=5)
        ax.annotate(f"TP {tp:.5f} (1:{rr})", xy=(xm, tp), xytext=(5, 5),
                    textcoords="offset points", fontsize=12, color="#fff", weight="bold",
                    bbox=dict(boxstyle="round,pad=0.25", facecolor="#4caf50", alpha=0.9, edgecolor="white"))

    ax.set_xlim(-1, n + 1)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.5f}"))
    ax.tick_params(labelbottom=False)

    fmt = "%H:%M" if tf in ("5m", "15m") else "%m/%d"
    step = max(1, n // 14)
    tick_pos = list(range(0, n, step))
    tick_lbl = [plot.index[i].strftime(fmt) for i in tick_pos]
    ax_stoch.set_xticks(tick_pos)
    ax_stoch.set_xticklabels(tick_lbl, rotation=20, ha="right", color=txt, fontsize=8)

    plt.savefig(filepath, dpi=200, bbox_inches="tight", facecolor=bg)
    plt.close(fig)
    return filepath
