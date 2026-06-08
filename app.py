import requests
import pandas as pd
from datetime import datetime, timedelta

from dash import Dash, dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import dash

# ============================================================
# FUNCIONES PARA DESCARGAR DATOS
# ============================================================

def get_candles(granularity):
    """Descarga velas OHLC desde Coinbase."""
    try:
        url = f"https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity={granularity}"
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


# ============================================================
# DASH APP
# ============================================================

app = Dash(__name__)
app.title = "Bitcoin Monitor"

app.layout = html.Div([

    html.H1("Bitcoin Monitor en Tiempo Real", style={"textAlign": "center"}),

    # Guarda el offset de la gráfica de 5 minutos
    dcc.Store(id="offset_5m", data=0),

    # Botón para refrescar todo
    html.Button("Refrescar Datos", id="refresh_btn", n_clicks=0,
                style={"margin": "20px", "padding": "10px", "fontSize": "18px"}),

    # ============================
    # GRÁFICA 1 — 1 AÑO
    # ============================
    dcc.Graph(id="fig_1y"),

    # ============================
    # GRÁFICA 2 — 24 HORAS
    # ============================
    dcc.Graph(id="fig_24h"),

    # ============================
    # GRÁFICA 3 Y 4 EN COLUMNAS
    # ============================
    html.Div([
        html.Div([
            dcc.Graph(id="fig_1h")
        ], style={"width": "48%", "display": "inline-block"}),

        html.Div([
            dcc.Graph(id="fig_5m"),

            dcc.Markdown(id="indicators_box",
                         style={
                             "backgroundColor": "#222",
                             "color": "white",
                             "padding": "15px",
                             "marginTop": "10px",
                             "borderRadius": "8px",
                             "fontSize": "18px",
                             "whiteSpace": "pre-line"
                         }),

            html.Div([
                html.Button("-1 min", id="minus_btn", n_clicks=0,
                            style={"margin": "5px", "padding": "10px"}),
                html.Button("+1 min", id="plus_btn", n_clicks=0,
                            style={"margin": "5px", "padding": "10px"}),
            ], style={"textAlign": "center"})
        ], style={"width": "48%", "display": "inline-block", "verticalAlign": "top"})
    ])
])


# ============================================================
# CALLBACK PARA AJUSTAR OFFSET DE 5 MINUTOS
# ============================================================

@app.callback(
    Output("offset_5m", "data"),
    [Input("minus_btn", "n_clicks"),
     Input("plus_btn", "n_clicks"),
     Input("refresh_btn", "n_clicks")],
    [State("offset_5m", "data")]
)
def update_offset(minus_clicks, plus_clicks, refresh_clicks, offset):
    ctx = dash.callback_context

    if not ctx.triggered:
        return offset

    trigger = ctx.triggered[0]["prop_id"].split(".")[0]

    if trigger == "minus_btn":
        return offset - 1
    elif trigger == "plus_btn":
        return offset + 1
    elif trigger == "refresh_btn":
        return 0  # reset offset

    return offset


# ============================================================
# CALLBACK PRINCIPAL PARA ACTUALIZAR TODAS LAS GRÁFICAS
# ============================================================

@app.callback(
    [Output("fig_1y", "figure"),
     Output("fig_24h", "figure"),
     Output("fig_1h", "figure"),
     Output("fig_5m", "figure"),
     Output("indicators_box", "children")],
    [Input("refresh_btn", "n_clicks"),
     Input("offset_5m", "data")]
)
def update_all(n, offset):

    # --------------------------
    # 1 AÑO (granularity = 1 día)
    # --------------------------
    df_1y = get_candles(86400)
    fig1 = go.Figure()
    if df_1y is not None:
        fig1.add_trace(go.Candlestick(
            x=df_1y["time"],
            open=df_1y["open"],
            high=df_1y["high"],
            low=df_1y["low"],
            close=df_1y["close"]
        ))
    fig1.update_layout(title="Histórico de precios de 1 Año", template="plotly_dark", height=400)

    # --------------------------
    # 24 HORAS (granularity = 1 min)
    # --------------------------
    df_24h = get_candles(60)
    fig2 = go.Figure()
    if df_24h is not None:
        df_24h = df_24h.tail(1440)
        fig2.add_trace(go.Candlestick(
            x=df_24h["time"],
            open=df_24h["open"],
            high=df_24h["high"],
            low=df_24h["low"],
            close=df_24h["close"]
        ))
    fig2.update_layout(title="Histórico de precios de 24 horas", template="plotly_dark", height=400)

    # --------------------------
    # 1 HORA (granularity = 1 min)
    # --------------------------
    fig3 = go.Figure()
    if df_24h is not None:
        df_1h = df_24h.tail(60)
        fig3.add_trace(go.Candlestick(
            x=df_1h["time"],
            open=df_1h["open"],
            high=df_1h["high"],
            low=df_1h["low"],
            close=df_1h["close"]
        ))
    fig3.update_layout(title="Histórico de precios de 1 hora", template="plotly_dark", height=400)

    # --------------------------
    # 5 MINUTOS + OFFSET (solo mueve el límite izquierdo)
    # --------------------------
    fig4 = go.Figure()
    indicator_text = ""

    if df_24h is not None:

        # Último timestamp disponible
        end_real = df_24h["time"].max()

        # Ventana base de 5 minutos
        start_base = end_real - pd.Timedelta(minutes=5)

        # Aplicar offset SOLO al inicio
        start_time = start_base + pd.Timedelta(minutes=offset)
        end_time   = start_time + pd.Timedelta(minutes=5)

        # Filtrar datos dentro de la ventana desplazada
        df_5m = df_24h[(df_24h["time"] >= start_time) & (df_24h["time"] <= end_time)]

        # Dibujar velas
        fig4.add_trace(go.Candlestick(
            x=df_5m["time"],
            open=df_5m["open"],
            high=df_5m["high"],
            low=df_5m["low"],
            close=df_5m["close"]
        ))

        # ============================================================
        # INDICADORES (EMA3, EMA15, RSI) — usando últimos 15 minutos
        # ============================================================

        if len(df_24h) >= 15:

            df_15m = df_24h.tail(15).copy()

            # --------------------------
            # EMA 3 y EMA 15
            # --------------------------
            df_15m["EMA3"] = df_15m["close"].ewm(span=3).mean()
            df_15m["EMA15"] = df_15m["close"].ewm(span=15).mean()

            ema3 = df_15m["EMA3"].iloc[-1]
            ema15 = df_15m["EMA15"].iloc[-1]

            if ema3 > ema15:
                ema_signal = "EMA3 > EMA15 → Momentum ALZA"
            elif ema3 < ema15:
                ema_signal = "EMA3 < EMA15 → Momentum BAJA"
            else:
                ema_signal = "EMA3 = EMA15 → Momentum NEUTRO"

            # --------------------------
            # RSI 15m
            # --------------------------
            delta = df_15m["close"].diff()
            gain = delta.clip(lower=0)
            loss = -delta.clip(upper=0)

            avg_gain = gain.rolling(14).mean().iloc[-1]
            avg_loss = loss.rolling(14).mean().iloc[-1]

            if avg_loss == 0:
                rsi = 100
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))

            if rsi < 30:
                rsi_signal = f"RSI {rsi:.1f} → Sobreventa (posible rebote)"
            elif rsi > 70:
                rsi_signal = f"RSI {rsi:.1f} → Sobrecompra (posible caída)"
            else:
                rsi_signal = f"RSI {rsi:.1f} → Neutral"

            indicator_text = f"**{ema_signal}**\n\n**{rsi_signal}**"

    fig4.update_layout(
        title="Histórico de precios de 5 minutos",
        template="plotly_dark",
        height=400
    )

    return fig1, fig2, fig3, fig4, indicator_text


# ============================================================
# EJECUTAR SERVIDOR
# ============================================================

if __name__ == "__main__":
    app.run(debug=False)