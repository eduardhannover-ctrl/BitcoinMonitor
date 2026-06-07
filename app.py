import requests
import pandas as pd
from datetime import datetime, timedelta

from dash import Dash, dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go

# ---------------------------
# DESCARGA DATOS DE COINBASE
# ---------------------------
def get_btc_data():
    try:
        url = "https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=60"
        r = requests.get(url, timeout=5)

        if r.status_code != 200:
            return None

        data = r.json()
        df = pd.DataFrame(data, columns=["time","low","high","open","close","volume"])
        df["time"] = pd.to_datetime(df["time"], unit="s")
        df = df.sort_values("time")
        df[["open","high","low","close"]] = df[["open","high","low","close"]].astype(float)
        return df

    except:
        return None

# ---------------------------
# DASH APP
# ---------------------------
app = Dash(__name__)
app.title = "Bitcoin Monitor"

app.layout = html.Div([
    html.H1("Bitcoin Monitor en Tiempo Real", style={"textAlign": "center"}),

    dcc.Graph(id="candles"),
    dcc.Graph(id="last5"),

    dcc.Interval(
        id="interval",
        interval=60 * 1000,  # 60 segundos
        n_intervals=0
    )
])

# ---------------------------
# CALLBACK PRINCIPAL
# ---------------------------
@app.callback(
    [Output("candles", "figure"),
     Output("last5", "figure")],
    [Input("interval", "n_intervals")]
)
def update_graph(n):
    df = get_btc_data()
    if df is None:
        return go.Figure(), go.Figure()

    # Tendencia últimos 5 min
    df5 = df.tail(5)
    start = df5["close"].iloc[0]
    end = df5["close"].iloc[-1]
    trend = "ALZA" if end > start else "BAJA" if end < start else "NEUTRA"
    color = "green" if trend == "ALZA" else "red" if trend == "BAJA" else "gold"

    # --- FIGURA 1: VELAS ---
    fig1 = go.Figure(data=[
        go.Candlestick(
            x=df["time"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"]
        )
    ])
    fig1.update_layout(
        title=f"Bitcoin - Velas OHLC (24h) — Tendencia: {trend}",
        template="plotly_dark",
        height=600
    )

    # --- FIGURA 2: ÚLTIMOS 5 MIN ---
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=df5["time"],
        y=df5["close"],
        mode="lines+markers",
        line=dict(color=color, width=4)
    ))
    fig2.update_layout(
        title=f"Últimos 5 minutos — Tendencia: {trend}",
        template="plotly_dark",
        height=300
    )

    return fig1, fig2

# ---------------------------
# EJECUTAR SERVIDOR
# ---------------------------
if __name__ == "__main__":
    app.run(debug=False)
