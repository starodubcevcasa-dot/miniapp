import os
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

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


def make_candle_traces(tf, df, result, is_visible):
    traces = []
    n = len(df)
    dates = df.index.tolist()

    traces.append(go.Candlestick(
        x=dates, open=df["open"], high=df["high"],
        low=df["low"], close=df["close"],
        name=f"{tf}",
        visible=is_visible,
        showlegend=False,
        increasing_line_color="#089981", decreasing_line_color="#f23645",
        line=dict(width=0.8),
    ))

    if "sma_20" in df.columns:
        traces.append(go.Scatter(
            x=dates, y=df["sma_20"],
            name=f"SMA20", visible=is_visible, showlegend=False,
            line=dict(color="#2962ff", width=1.2),
        ))
    if "sma_50" in df.columns:
        traces.append(go.Scatter(
            x=dates, y=df["sma_50"],
            name=f"SMA50", visible=is_visible, showlegend=False,
            line=dict(color="#ff9800", width=1.2),
        ))

    levels = find_levels(df)
    for s in levels["support"]:
        traces.append(go.Scatter(
            x=[dates[0], dates[-1]], y=[s, s],
            name=f"S {s:.5f}", visible=is_visible, showlegend=False,
            mode="lines+text",
            line=dict(color="#089981", width=1, dash="dash"),
            text=[f"S {s:.5f}", ""], textposition="top left",
            textfont=dict(color="#089981", size=10),
        ))
    for r in levels["resistance"]:
        traces.append(go.Scatter(
            x=[dates[0], dates[-1]], y=[r, r],
            name=f"R {r:.5f}", visible=is_visible, showlegend=False,
            mode="lines+text",
            line=dict(color="#f23645", width=1, dash="dash"),
            text=[f"R {r:.5f}", ""], textposition="top left",
            textfont=dict(color="#f23645", size=10),
        ))

    div = result.get("div")
    if div:
        fi = max(0, div["from_idx"] - len(df) + n)
        ti = max(0, div["to_idx"] - len(df) + n)
        if fi < n and ti < n:
            dc = "#089981" if div["type"] == "bullish" else "#f23645"
            marker = "triangle-up" if div["type"] == "bullish" else "triangle-down"
            label = "БЫЧЬЯ ДИВЕРГЕНЦИЯ" if div["type"] == "bullish" else "МЕДВЕЖЬЯ ДИВЕРГЕНЦИЯ"

            traces.append(go.Scatter(
                x=[dates[fi], dates[ti]],
                y=[div["from_price"], div["to_price"]],
                name=label, visible=is_visible, showlegend=False,
                mode="markers+lines",
                marker=dict(size=12, color=dc, symbol=marker, line=dict(color="white", width=1.5)),
                line=dict(color=dc, width=1.5, dash="dot"),
                text=[label], textposition="top center",
                textfont=dict(color=dc, size=10),
            ))

    entry_e = result.get("entry")
    if entry_e:
        ep, sl, tp = entry_e["entry"], entry_e["stop_loss"], entry_e["take_profit"]
        dc = "#089981" if entry_e["action"] == "BUY" else "#f23645"
        rr = entry_e.get("risk_reward", "?")
        act = "ПОКУПКА" if entry_e["action"] == "BUY" else "ПРОДАЖА"

        traces.append(go.Scatter(
            x=[dates[0], dates[-1]], y=[ep, ep],
            name=f"{act} {ep:.5f}", visible=is_visible, showlegend=False,
            mode="lines+text",
            line=dict(color="white", width=1),
            text=[f"{act} {ep:.5f}", ""], textposition="top left",
            textfont=dict(color=dc, size=11),
        ))
        traces.append(go.Scatter(
            x=[dates[0], dates[-1]], y=[sl, sl],
            name=f"SL {sl:.5f}", visible=is_visible, showlegend=False,
            mode="lines+text",
            line=dict(color="#f23645", width=1, dash="dash"),
            text=[f"SL {sl:.5f}", ""], textposition="top left",
            textfont=dict(color="#f23645", size=10),
        ))
        traces.append(go.Scatter(
            x=[dates[0], dates[-1]], y=[tp, tp],
            name=f"TP {tp:.5f} 1:{rr}", visible=is_visible, showlegend=False,
            mode="lines+text",
            line=dict(color="#089981", width=1, dash="dash"),
            text=[f"TP {tp:.5f} 1:{rr}", ""], textposition="top left",
            textfont=dict(color="#089981", size=10),
        ))

    return traces


def make_rsi_traces(tf, df, result, is_visible):
    traces = []
    if "rsi" not in df.columns:
        return traces
    dates = df.index.tolist()

    traces.append(go.Scatter(
        x=dates, y=df["rsi"],
        name=f"RSI", visible=is_visible, showlegend=False,
        line=dict(color="#787b86", width=1.2),
    ))

    for level, color in [(70, "#f23645"), (30, "#089981")]:
        traces.append(go.Scatter(
            x=[dates[0], dates[-1]], y=[level, level],
            name=f"RSI {level}", visible=is_visible, showlegend=False,
            mode="lines",
            line=dict(color=color, width=0.8, dash="dash"),
        ))

    div = result.get("div")
    if div:
        fi = max(0, div["from_idx"] - len(df) + len(df))
        ti = max(0, div["to_idx"] - len(df) + len(df))
        if fi < len(df) and ti < len(df):
            dc = "#089981" if div["type"] == "bullish" else "#f23645"
            marker = "triangle-up" if div["type"] == "bullish" else "triangle-down"
            traces.append(go.Scatter(
                x=[dates[fi], dates[ti]],
                y=[div["from_rsi"], div["to_rsi"]],
                name="RSI div", visible=is_visible, showlegend=False,
                mode="markers+lines",
                marker=dict(size=10, color=dc, symbol=marker, line=dict(color="white", width=1.5)),
                line=dict(color=dc, width=1.5, dash="dot"),
            ))

    return traces


def generate_chart(symbol, tf, df, div=None, entry=None):
    return generate_interactive(symbol, {tf: df}, {tf: {"div": div, "entry": entry}}, (tf, entry, 0) if entry else None)


def generate_interactive(symbol, all_data, results, best_entry):
    ensure_dir()
    name = symbol.replace("=X", "").replace("-USD", "")
    filename = f"{name}_chart_{pd.Timestamp.now().strftime('%H%M%S')}.html"
    filepath = os.path.join(CHARTS_DIR, filename)

    all_tfs = sorted(all_data.keys(),
                     key=lambda x: ["5m", "15m", "1h", "4h", "1d"].index(x) if x in ["5m", "15m", "1h", "4h", "1d"] else 99)

    default_tf = best_entry[0] if best_entry else all_tfs[0]

    fig = make_subplots(
        rows=2, cols=1,
        row_heights=[0.75, 0.25],
        shared_xaxes=True,
        vertical_spacing=0.04,
    )

    all_price_traces = []
    all_rsi_traces = []
    tf_to_indices = {}

    idx = 0
    for tf in all_tfs:
        df = all_data[tf].iloc[-80:].copy()
        df.index = pd.to_datetime(df.index)
        result = results.get(tf, {})
        is_vis = tf == default_tf

        price_tr = make_candle_traces(tf, df, result, is_vis)
        rsi_tr = make_rsi_traces(tf, df, result, is_vis)

        start_idx = idx
        for t in price_tr:
            fig.add_trace(t, row=1, col=1)
            idx += 1
        for t in rsi_tr:
            fig.add_trace(t, row=2, col=1)
            idx += 1
        tf_to_indices[tf] = (start_idx, idx)

    buttons = []
    for tf in all_tfs:
        start, end = tf_to_indices[tf]
        vis = [False] * idx
        for i in range(start, end):
            vis[i] = True
        buttons.append(dict(
            label=tf,
            method="update",
            args=[{"visible": vis}],
        ))

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#131722",
        plot_bgcolor="#131722",
        font=dict(color="#d1d4dc", size=11),
        title=dict(
            text=f"{name} — {pd.Timestamp.now().strftime('%d.%m %H:%M')}",
            font=dict(size=16, color="#d1d4dc"),
            y=0.97,
        ),
        hovermode="x unified",
        dragmode="zoom",
        margin=dict(l=40, r=60, t=50, b=20),
        xaxis=dict(
            showgrid=True, gridcolor="#2a2e39", gridwidth=0.5,
            showspikes=True, spikemode="across", spikesnap="cursor",
            showline=False,
        ),
        xaxis2=dict(
            showgrid=True, gridcolor="#2a2e39", gridwidth=0.5,
            showline=False,
        ),
        yaxis=dict(
            showgrid=True, gridcolor="#2a2e39", gridwidth=0.5,
            side="right",
            tickformat=".5f",
            showline=False,
        ),
        yaxis2=dict(
            showgrid=True, gridcolor="#2a2e39", gridwidth=0.5,
            range=[0, 100],
            showline=False,
        ),
        updatemenus=[dict(
            buttons=buttons,
            direction="down",
            showactive=True,
            x=0, xanchor="left",
            y=1.08, yanchor="top",
            bgcolor="#2a2e39",
            bordercolor="#d1d4dc",
            font=dict(color="#d1d4dc"),
            active=all_tfs.index(default_tf),
        )],
        legend=dict(
            font=dict(size=10),
            bgcolor="rgba(0,0,0,0)",
        ),
    )

    fig.update_xaxes(rangeslider=dict(visible=False))

    fig.write_html(filepath, include_plotlyjs="cdn", full_html=True,
                   config={
                       "scrollZoom": True,
                       "displayModeBar": True,
                       "modeBarButtonsToRemove": ["lasso2d", "select2d"],
                       "displaylogo": False,
                   })
    return filepath
