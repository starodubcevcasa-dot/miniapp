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
    return _render(symbol, {tf: df}, {tf: {"div": div, "entry": entry}}, (tf, entry, 0) if entry else None)


def generate_interactive(symbol, all_data, results, best_entry):
    return _render(symbol, all_data, results, best_entry)


def _render(symbol, all_data, results, best_entry):
    ensure_dir()
    name = symbol.replace("=X", "").replace("-USD", "")
    filename = f"{name}_chart_{pd.Timestamp.now().strftime('%H%M%S')}.png"
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
        ohlc={"up": "#089981", "down": "#f23645"},
    )
    tv_style = mpf.make_mpf_style(
        base_mpf_style="charles",
        marketcolors=mc,
        facecolor="#131722",
        figcolor="#131722",
        edgecolor="#2a2e39",
        gridcolor="#2a2e39",
        gridstyle="-",
        rc={
            "font.size": 11,
            "axes.labelcolor": "#d1d4dc",
            "xtick.color": "#d1d4dc",
            "ytick.color": "#d1d4dc",
            "axes.edgecolor": "#2a2e39",
        },
    )

    ap = []

    if "sma_20" in df.columns:
        ap.append(mpf.make_addplot(df["sma_20"], color="#2962ff", width=1.2))
    if "sma_50" in df.columns:
        ap.append(mpf.make_addplot(df["sma_50"], color="#ff9800", width=1.2))

    levels = find_levels(df)
    for s in levels["support"]:
        ap.append(mpf.make_addplot(pd.Series(s, index=df.index), color="#089981", width=1, linestyle="--", secondary_y=False))
    for r in levels["resistance"]:
        ap.append(mpf.make_addplot(pd.Series(r, index=df.index), color="#f23645", width=1, linestyle="--", secondary_y=False))

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
                color=dc, markersize=150, edgecolors="white",
            ))

    entry_e = result.get("entry")
    if entry_e:
        ep = entry_e["entry"]
        sl = entry_e["stop_loss"]
        tp = entry_e["take_profit"]
        rr = entry_e.get("risk_reward", "?")

        ap.append(mpf.make_addplot(pd.Series(ep, index=df.index), color="white", width=0.8, linestyle="-"))
        ap.append(mpf.make_addplot(pd.Series(sl, index=df.index), color="#f23645", width=0.8, linestyle="--"))
        ap.append(mpf.make_addplot(pd.Series(tp, index=df.index), color="#089981", width=0.8, linestyle="--"))

    rsi_df = None
    if "rsi" in df.columns:
        rsi_df = df["rsi"]
        ap.append(mpf.make_addplot(rsi_df, panel=1, color="#787b86", width=1.5, ylabel="RSI"))

    fig, axes = mpf.plot(
        df,
        type="candle",
        style=tv_style,
        title=f"{name} ({default_tf}) — {pd.Timestamp.now().strftime('%d.%m %H:%M')}",
        ylabel="",
        ylabel_lower="",
        volume=False,
        addplot=ap,
        returnfig=True,
        figsize=(18, 10),
        panel_ratios=(5, 1),
        tight_layout=True,
    )

    for a in axes:
        try:
            a.yaxis.tick_right()
        except Exception:
            pass

    fig.savefig(filepath, dpi=200, bbox_inches="tight", facecolor="#131722")
    plt.close(fig)
    return filepath
