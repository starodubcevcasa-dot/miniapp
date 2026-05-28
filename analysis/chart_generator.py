import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mplfinance as mpf

CHARTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "charts")


def ensure_dir():
    os.makedirs(CHARTS_DIR, exist_ok=True)


def find_levels(df, lookback=40):
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
    return _render(symbol, {tf: df}, {tf: {"div": div, "entry": entry}}, (tf, entry, 0) if entry else None)


def generate_interactive(symbol, all_data, results, best_entry):
    return _render(symbol, all_data, results, best_entry)


def _render(symbol, all_data, results, best_entry):
    ensure_dir()
    name = symbol.replace("=X", "").replace("-USD", "")
    filename = f"{name}_{pd.Timestamp.now().strftime('%H%M%S')}.png"
    filepath = os.path.join(CHARTS_DIR, filename)

    all_tfs = sorted(all_data.keys(),
                     key=lambda x: ["5m", "15m", "1h", "4h", "1d"].index(x) if x in ["5m", "15m", "1h", "4h", "1d"] else 99)
    default_tf = best_entry[0] if best_entry else all_tfs[0]

    df = all_data[default_tf].iloc[-55:].copy()
    df.index = pd.to_datetime(df.index)
    result = results.get(default_tf, {}) or {}

    mc = mpf.make_marketcolors(
        up="#089981", down="#f23645",
        wick={"up": "#089981", "down": "#f23645"},
        edge={"up": "#089981", "down": "#f23645"},
        volume={"up": "#089981", "down": "#f23645"},
    )
    style = mpf.make_mpf_style(
        base_mpf_style="charles",
        marketcolors=mc,
        facecolor="#131722",
        figcolor="#131722",
        gridcolor="#2a2e39",
        gridaxis="both",
        rc={
            "font.size": 10,
            "axes.labelcolor": "#d1d4dc",
            "xtick.color": "#d1d4dc",
            "ytick.color": "#d1d4dc",
        },
    )

    ap = []

    if "sma_20" in df.columns:
        ap.append(mpf.make_addplot(df["sma_20"], color="#2962ff", width=1.2))
    if "sma_50" in df.columns:
        ap.append(mpf.make_addplot(df["sma_50"], color="#ff9800", width=1.2))

    div = result.get("div")
    if div:
        fi = max(0, div["from_idx"] - len(all_data[default_tf]) + len(df))
        ti = max(0, div["to_idx"] - len(all_data[default_tf]) + len(df))
        if fi < len(df) and ti < len(df):
            dc = "#089981" if div["type"] == "bullish" else "#f23645"
            marker = "^" if div["type"] == "bullish" else "v"
            div_vals = pd.Series(np.nan, index=df.index)
            div_vals.iloc[fi] = div["from_price"]
            div_vals.iloc[ti] = div["to_price"]
            ap.append(mpf.make_addplot(
                div_vals, type="scatter", marker=marker,
                color=dc, markersize=200, edgecolors="white",
            ))

    if result.get("entry"):
        ep = result["entry"]["entry"]
        sl = result["entry"]["stop_loss"]
        tp = result["entry"]["take_profit"]

    rsi_ap = None
    if "rsi" in df.columns:
        rsi_ap = mpf.make_addplot(df["rsi"], panel="lower", color="#787b86", width=1.5, ylabel="RSI")
        ap.append(rsi_ap)

    fig, axes = mpf.plot(
        df, type="candle", style=style,
        title=f"{name} ({default_tf})",
        addplot=ap,
        returnfig=True,
        figsize=(20, 11),
        figscale=1.0,
        volume=False,
        tight_layout=True,
    )

    ax_main = axes[0]
    ax_main.yaxis.tick_right()
    ax_main.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.5f}"))

    for line in ax_main.lines:
        line.set_linewidth(1.0)

    levels = find_levels(df)
    for s in levels["support"]:
        ax_main.axhline(y=s, color="#089981", linewidth=1.2, linestyle="--", alpha=0.6)
        ax_main.text(len(df) - 1, s, f"  S {s:.5f}", color="#089981", fontsize=9, weight="bold",
                     ha="left", va="bottom",
                     bbox=dict(fc="#131722", ec="#089981", alpha=0.8, boxstyle="round,pad=0.1"))
    for r in levels["resistance"]:
        ax_main.axhline(y=r, color="#f23645", linewidth=1.2, linestyle="--", alpha=0.6)
        ax_main.text(len(df) - 1, r, f"  R {r:.5f}", color="#f23645", fontsize=9, weight="bold",
                     ha="left", va="bottom",
                     bbox=dict(fc="#131722", ec="#f23645", alpha=0.8, boxstyle="round,pad=0.1"))

    if result.get("entry"):
        ep = result["entry"]["entry"]
        sl = result["entry"]["stop_loss"]
        tp = result["entry"]["take_profit"]
        rr = result["entry"].get("risk_reward", "?")
        act = "ПОКУПКА" if result["entry"]["action"] == "BUY" else "ПРОДАЖА"
        dc = "#089981" if result["entry"]["action"] == "BUY" else "#f23645"
        ec = "#f23645" if result["entry"]["action"] == "BUY" else "#089981"

        sig_idx = result["entry"].get("signal_idx")
        if sig_idx is not None:
            local_sig = max(0, sig_idx - len(all_data[default_tf]) + len(df))
            if 0 <= local_sig < len(df):
                sig_high = df["high"].iloc[local_sig]
                sig_low = df["low"].iloc[local_sig]
                sig_mid = (sig_high + sig_low) / 2

                ax_main.annotate("",
                                 xy=(local_sig, sig_high), xytext=(local_sig, sig_high + (df["high"].max() - df["low"].min()) * 0.15),
                                 fontsize=20, weight="bold",
                                 arrowprops=dict(arrowstyle="->", color=dc, lw=3))

                ax_main.scatter(local_sig, sig_mid, marker="o", s=300, color=dc,
                                edgecolors="white", linewidth=2, zorder=10, alpha=0.5)

        ax_main.axhline(y=ep, color="#ffffff", linewidth=2, linestyle="-", alpha=0.8, zorder=5)
        ax_main.axhline(y=sl, color="#f23645", linewidth=2, linestyle="--", alpha=0.7, zorder=5)
        ax_main.axhline(y=tp, color="#089981", linewidth=2, linestyle="--", alpha=0.7, zorder=5)

        ax_main.fill_between(range(len(df)), ep, sl, color=ec, alpha=0.08, zorder=1)

        ax_main.annotate(f"{act}\n{ep:.5f}", xy=(len(df) - 0.5, ep), xytext=(15, -30),
                         textcoords="offset points", fontsize=15, weight="bold", color="#fff",
                         bbox=dict(boxstyle="round,pad=0.4", facecolor=dc, alpha=0.95, edgecolor="white"))
        ax_main.annotate(f"SL {sl:.5f}", xy=(len(df) - 0.5, sl), xytext=(15, -18),
                         textcoords="offset points", fontsize=13, color="#fff", weight="bold",
                         bbox=dict(boxstyle="round,pad=0.25", facecolor="#f23645", alpha=0.95, edgecolor="white"))
        ax_main.annotate(f"TP {tp:.5f} (1:{rr})", xy=(len(df) - 0.5, tp), xytext=(15, 5),
                         textcoords="offset points", fontsize=13, color="#fff", weight="bold",
                         bbox=dict(boxstyle="round,pad=0.25", facecolor="#089981", alpha=0.95, edgecolor="white"))

    fig.savefig(filepath, dpi=200, bbox_inches="tight", facecolor="#131722")
    plt.close(fig)
    return filepath
