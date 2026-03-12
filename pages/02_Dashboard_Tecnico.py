import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

st.set_page_config(page_title="Dashboard Técnico de Sectores", layout="wide")

st.title("📊 Módulo 2: Análisis de Tendencia y RS Normalizado")

# --- REUTILIZAMOS TU LÓGICA DE DATOS ---
@st.cache_data
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
