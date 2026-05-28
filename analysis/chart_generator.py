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


def make_price_traces(tf, df, result, is_visible):
    traces = []
    dates = df.index.tolist()
    n = len(df)

    traces.append(go.Candlestick(
        x=dates, open=df["open"], high=df["high"],
        low=df["low"], close=df["close"],
        name=f"{tf}", visible=is_visible,
        showlegend=False,
        increasing=dict(line=dict(color="#089981", width=1.5), fillcolor="#089981"),
        decreasing=dict(line=dict(color="#f23645", width=1.5), fillcolor="#f23645"),
        line=dict(width=1.5),
    ))

    traces.append(go.Scatter(
        x=dates, y=df["close"],
        name=f"close_{tf}", visible=is_visible, showlegend=False,
        line=dict(color="white", width=0.8, dash="dot"),
        opacity=0.4,
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
    last_date = dates[-1]
    for s in levels["support"]:
        traces.append(go.Scatter(
            x=[dates[0], dates[-1]], y=[s, s],
            name=f"S {s:.5f}", visible=is_visible, showlegend=False,
            mode="lines",
            line=dict(color="#089981", width=1, dash="dash"),
        ))
        traces.append(go.Scatter(
            x=[last_date], y=[s],
            name=f"S_label", visible=is_visible, showlegend=False,
            mode="text",
            text=[f"S {s:.5f}"],
            textposition="middle right",
            textfont=dict(color="#089981", size=10, family="monospace"),
        ))
    for r in levels["resistance"]:
        traces.append(go.Scatter(
            x=[dates[0], dates[-1]], y=[r, r],
            name=f"R {r:.5f}", visible=is_visible, showlegend=False,
            mode="lines",
            line=dict(color="#f23645", width=1, dash="dash"),
        ))
        traces.append(go.Scatter(
            x=[last_date], y=[r],
            name=f"R_label", visible=is_visible, showlegend=False,
            mode="text",
            text=[f"R {r:.5f}"],
            textposition="middle right",
            textfont=dict(color="#f23645", size=10, family="monospace"),
        ))

    div = result.get("div")
    if div:
        fi = max(0, div["from_idx"] - len(df) + n)
        ti = max(0, div["to_idx"] - len(df) + n)
        if fi < n and ti < n:
            dc = "#089981" if div["type"] == "bullish" else "#f23645"
            marker = "triangle-up" if div["type"] == "bullish" else "triangle-down"
            label = "БЫЧЬЯ ДИВ" if div["type"] == "bullish" else "МЕДВЕЖЬЯ ДИВ"

            traces.append(go.Scatter(
                x=[dates[fi], dates[ti]],
                y=[div["from_price"], div["to_price"]],
                name=f"div_{tf}", visible=is_visible, showlegend=False,
                mode="markers+lines",
                marker=dict(size=10, color=dc, symbol=marker, line=dict(color="white", width=1.5)),
                line=dict(color=dc, width=1.5, dash="dot"),
            ))
            traces.append(go.Scatter(
                x=[dates[ti]], y=[div["to_price"]],
                name=f"div_label", visible=is_visible, showlegend=False,
                mode="text",
                text=[label],
                textposition="top center" if div["type"] == "bullish" else "bottom center",
                textfont=dict(color=dc, size=11, family="monospace"),
            ))

    entry_e = result.get("entry")
    if entry_e:
        ep, sl, tp = entry_e["entry"], entry_e["stop_loss"], entry_e["take_profit"]
        dc = "#089981" if entry_e["action"] == "BUY" else "#f23645"
        rr = entry_e.get("risk_reward", "?")
        act = "ПОКУПКА" if entry_e["action"] == "BUY" else "ПРОДАЖА"

        traces.append(go.Scatter(
            x=[dates[0], dates[-1]], y=[ep, ep],
            name="entry_line", visible=is_visible, showlegend=False,
            mode="lines",
            line=dict(color="white", width=1.5),
        ))
        traces.append(go.Scatter(
            x=[dates[0], dates[-1]], y=[sl, sl],
            name="sl_line", visible=is_visible, showlegend=False,
            mode="lines",
            line=dict(color="#f23645", width=1.5, dash="dash"),
        ))
        traces.append(go.Scatter(
            x=[dates[0], dates[-1]], y=[tp, tp],
            name="tp_line", visible=is_visible, showlegend=False,
            mode="lines",
            line=dict(color="#089981", width=1.5, dash="dash"),
        ))

    return traces


def make_rsi_traces(tf, df, result, is_visible):
    traces = []
    if "rsi" not in df.columns:
        return traces
    dates = df.index.tolist()

    traces.append(go.Scatter(
        x=dates, y=df["rsi"],
        name=f"RSI_{tf}", visible=is_visible, showlegend=False,
        line=dict(color="#787b86", width=1.5),
    ))

    for level, color in [(70, "#f23645"), (30, "#089981"), (50, "#555")]:
        dash = "dash" if level != 50 else "dot"
        traces.append(go.Scatter(
            x=[dates[0], dates[-1]], y=[level, level],
            name=f"rsi_{level}", visible=is_visible, showlegend=False,
            mode="lines",
            line=dict(color=color, width=0.8, dash=dash),
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
                name=f"rsi_div_{tf}", visible=is_visible, showlegend=False,
                mode="markers+lines",
                marker=dict(size=8, color=dc, symbol=marker, line=dict(color="white", width=1.5)),
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

    n_candles = 60

    fig = make_subplots(
        rows=2, cols=1,
        row_heights=[0.78, 0.22],
        shared_xaxes=True,
        vertical_spacing=0.03,
    )

    all_price_traces = []
    all_rsi_traces = []
    tf_to_indices = {}

    idx = 0
    for tf in all_tfs:
        df = all_data[tf].iloc[-n_candles:].copy()
        df.index = pd.to_datetime(df.index)
        result = results.get(tf, {})
        if not result:
            result = {}
        is_vis = tf == default_tf

        price_tr = make_price_traces(tf, df, result, is_vis)
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
    labels_map = {"5m": "5m", "15m": "15m", "1h": "1h", "4h": "4h", "1d": "1d"}
    for tf in all_tfs:
        start, end = tf_to_indices[tf]
        vis = [False] * idx
        for i in range(start, end):
            vis[i] = True
        buttons.append(dict(
            label=labels_map.get(tf, tf),
            method="update",
            args=[{"visible": vis}],
        ))

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#131722",
        plot_bgcolor="#131722",
        font=dict(color="#d1d4dc", size=12),
        title=dict(
            text=f"{name} — {pd.Timestamp.now().strftime('%d.%m %H:%M')}",
            font=dict(size=18, color="#d1d4dc", family="Arial"),
            y=0.98,
        ),
        hovermode="x unified",
        dragmode="zoom",
        margin=dict(l=30, r=80, t=60, b=20),
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
            fixedrange=False,
        ),
        yaxis2=dict(
            showgrid=True, gridcolor="#2a2e39", gridwidth=0.5,
            range=[0, 100],
            showline=False,
            fixedrange=False,
        ),
        updatemenus=[dict(
            buttons=buttons,
            direction="down",
            showactive=True,
            x=0.01, xanchor="left",
            y=1.12, yanchor="top",
            bgcolor="#1e222d",
            bordercolor="#d1d4dc",
            font=dict(color="#d1d4dc", size=13),
            active=all_tfs.index(default_tf),
            pad=dict(r=5, t=5),
        )],
        legend=dict(font=dict(size=10), bgcolor="rgba(0,0,0,0)", itemclick=False),
        hoverlabel=dict(bgcolor="#1e222d", font=dict(color="#d1d4dc", size=12)),
        separators=".,",
    )

    fig.update_xaxes(rangeslider=dict(visible=True, thickness=0.04, bgcolor="#1e222d"))

    fig.write_html(
        filepath, include_plotlyjs="cdn", full_html=True,
        config={
            "scrollZoom": True,
            "displayModeBar": True,
            "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"],
            "displaylogo": False,
            "responsive": True,
        },
    )
    return filepath
