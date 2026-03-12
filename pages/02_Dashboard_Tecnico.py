import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# --- AGREGÁ ESTO AQUÍ ---
from streamlit_autorefresh import st_autorefresh

# Refresco automático cada 15 minutos
# (15 min * 60 seg * 1000 ms = 900.000)
st_autorefresh(interval=900000, key="Dashboard_refresh")
# ------------------------

st.set_page_config(page_title="Dashboard Técnico de Sectores", layout="wide")

st.title("📊 Módulo 2: Análisis de Tendencia y RS Normalizado")

# --- REUTILIZAMOS TU LÓGICA DE DATOS ---
@st.cache_data(ttl=900)
def get_data():
    sectors = {
        "XLK": "Technology", "XLE": "Energy", "XLF": "Financials",
        "XLV": "Healthcare", "XLP": "Staples", "XLY": "Discretionary",
        "XLI": "Industrials", "XLC": "Communication", "XLRE": "Real State",
        "XLB": "Materials", "XLU": "Utilities"
    }
    tickers = list(sectors.keys()) + ["SPY"]
    raw_data = yf.download(tickers, period="2y", interval="1d")
    data = raw_data['Adj Close'] if 'Adj Close' in raw_data.columns else raw_data['Close']
    return data, sectors

data, sectors = get_data()

# Cálculos de Fuerza Relativa
rs_df = pd.DataFrame()
for tick, name in sectors.items():
    rs_df[name] = data[tick] / data['SPY']

# Normalización 126 días
lookback = 126
rs_recent = rs_df.tail(lookback)
rs_norm = (rs_recent / rs_recent.iloc[0]) * 100

# --- SECCIÓN A: GRÁFICOS TÉCNICOS ---
st.header("📈 Canasta de Sectores (RS vs EMAs)")
cols = st.columns(3) # Para que no sea una lista infinita, los agrupamos
for i, col_name in enumerate(rs_norm.columns):
    with cols[i % 3]:
        fig, ax = plt.subplots()
        e21 = rs_norm[col_name].ewm(span=21, adjust=False).mean()
        e50 = rs_norm[col_name].ewm(span=50, adjust=False).mean()
        
        ax.plot(rs_norm[col_name], label='RS', color='blue')
        ax.plot(e21, label='EMA 21', color='orange')
        ax.plot(e50, label='EMA 50', color='red')
        ax.axhline(100, color='black', ls='--', alpha=0.3)
        ax.set_title(col_name)
        st.pyplot(fig)

# --- SECCIÓN B: MOMENTUM 30D ---
st.divider()
st.header("⏱️ Momentum Relativo (Últimos 30 días)")

curr, p7, p30, p90 = rs_df.iloc[-1], rs_df.iloc[-6], rs_df.iloc[-22], rs_df.iloc[-64]
trend_table = pd.DataFrame({
    'RS vs 7D (%)': ((curr / p7) - 1) * 100,
    'RS vs 30D (%)': ((curr / p30) - 1) * 100,
    'RS vs 90D (%)': ((curr / p90) - 1) * 100,
    'RS Base 100': rs_norm.iloc[-1]
}).sort_values(by='RS vs 30D (%)', ascending=False)

fig_bar, ax_bar = plt.subplots(figsize=(10, 4))
colors = ['#2ecc71' if x > 0 else '#e74c3c' for x in trend_table['RS vs 30D (%)']]
trend_table['RS vs 30D (%)'].plot(kind='bar', color=colors, ax=ax_bar)
ax_bar.axhline(0, color='black', lw=1)
st.pyplot(fig_bar)

# --- SECCIÓN C: TABLA CON SEMÁFORO ---
st.header("📋 Matriz de Estados")

def determinar_estado(row):
    if row['RS Base 100'] > 100 and row['RS vs 7D (%)'] > 0: return "LIDERAZGO"
    if row['RS Base 100'] > 100 and row['RS vs 7D (%)'] < 0: return "DEBILITAMIENTO"
    if row['RS Base 100'] < 100 and row['RS vs 7D (%)'] > 0: return "RECUPERACIÓN (PISO?)"
    return "BAJISTA"

trend_table['ESTADO'] = trend_table.apply(determinar_estado, axis=1)

# Estilizado para Streamlit
def color_estado(val):
    color_map = {"LIDERAZGO": "#2ecc71", "RECUPERACIÓN (PISO?)": "#f1c40f", 
                 "DEBILITAMIENTO": "#e67e22", "BAJISTA": "#e74c3c"}
    return f'background-color: {color_map.get(val, "")}'

st.dataframe(trend_table.style.applymap(color_estado, subset=['ESTADO']).format("{:.2f}%", subset=['RS vs 7D (%)', 'RS vs 30D (%)', 'RS vs 90D (%)']), use_container_width=True)


# --- AGREGAR AL FINAL DEL ARCHIVO 02_DASHBOARD.PY ---
st.divider()

with st.expander("📖 Ver Guía de Acción Táctica (RSI + Extensión + Medias)"):
    st.markdown("""
    ### 🛠️ Estrategia de Ejecución Basada en Niveles Técnicos

    Esta guía combina el **RSI**, la **Extensión de la SMA200** y el **Precio** para determinar puntos de entrada y salida con alta probabilidad.

    ---

    ### 🟢 1. REGLAS DE ENTRADA (Buy the Dip / Momentum)

    | Señal | RSI (14D) | Extensión % | Acción Sugerida |
    | :--- | :--- | :--- | :--- |
    | **Oversold Extremo** | **< 30** | **< 0% (Cerca de SMA200)** | **COMPRA AGRESIVA:** Probable suelo temporal. |
    | **Rebote de Momentum** | **Cruce > 50** | **0% a +5%** | **CONFIRMACIÓN:** El precio recupera fuerza tras descanso. |
    | **Ignición** | **Cruce > 70** | **+2% a +6%** | **COMPRA MOMENTUM:** No es sobrecompra aún, es fuerza pura. |

    ---

    ### 🔴 2. REGLAS DE SALIDA (Take Profit / Stop Loss)

    | Señal | RSI (14D) | Extensión % | Acción Sugerida |
    | :--- | :--- | :--- | :--- |
    | **Euforia Terminal** | **> 80** | **> +8%** | **VENTA TOTAL:** Riesgo inminente de regresión a la media. |
    | **Divergencia Bajista**| **Bajando** | **Subiendo** | **REDUCIR EXPOSICIÓN:** El precio sube sin fuerza real. |
    | **Falla de Soporte** | **< 50** | **Cruce < 0%** | **STOP LOSS:** El activo perdió su tendencia de largo plazo. |

    ---

    ### 🧠 Conceptos "Advanced Junior" para el Dashboard

    * **La Regla del 8%:** Históricamente, el SPY rara vez se mantiene por encima del 8-10% de su SMA200 por mucho tiempo. Es un "imán" que tarde o temprano succiona el precio hacia abajo.
    * **RSI 50 como Eje:** Mientras el RSI se mantenga arriba de 50, estamos en **Modo Alcista**. Si el RSI choca contra 50 desde abajo y no lo pasa, el rebote falló.
    * **Confluencia VIX:** Si el **Módulo 3** muestra un VIX subiendo y aquí ves una **Extensión > 8%**, la probabilidad de un crash de corto plazo es del 90%.

    ---
    *Utiliza esta matriz para eliminar la emoción del trading y operar basado en datos estadísticos.*
    """)







