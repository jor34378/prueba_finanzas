import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import io
import requests
import re
import matplotlib.pyplot as plt

st.set_page_config(page_title="Market Breadth 500", layout="wide")

st.title("🧬 Módulo 3: Market Breadth & Global Regime")
st.markdown("Análisis de salud interna del S&P 500 y confluencia de activos de riesgo.")

# --- FUNCIÓN DE CARGA DE DATOS (Optimizada con Cache) ---
@st.cache_data(ttl=3600) # Se actualiza cada 1 hora
def get_breadth_data():
    # 1. Tickers de Wikipedia
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    df_wiki = pd.read_html(io.StringIO(resp.text))[0]
    all_tickers = [re.sub(r'\.', '-', t) for t in df_wiki['Symbol'].tolist()]
    
    global_assets = ["SPY", "^VIX", "HYG", "TLT"]
    
    # 2. Descarga
    with st.spinner("Escaneando 500 activos... esto puede tardar 20-30 segundos"):
        data_raw = yf.download(all_tickers + global_assets, period="2y", interval="1d", auto_adjust=True, progress=False)
        data = data_raw['Close'] if 'Close' in data_raw.columns else data_raw
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
    return data, all_tickers

try:
    data, all_tickers = get_breadth_data()
    
    # 3. Cálculos de Índices
    spy = data['SPY'].dropna()
    vix = data['^VIX'].dropna()
    hyg = data['HYG'].dropna()
    tlt = data['TLT'].dropna()
    
    # Breadth Calculation
    with st.spinner("Calculando indicadores internos..."):
        all_sma200 = data[all_tickers].apply(lambda x: ta.sma(x, length=200))
        breadth = (data[all_tickers] > all_sma200).sum(axis=1) / len(all_tickers) * 100
        
        sma200_spy = ta.sma(spy, length=200)
        dist_pct = ((spy / sma200_spy) - 1) * 100
        b_slope = breadth.diff(5)
        sma_slope = (sma200_spy.diff(5) / sma200_spy.shift(5)) * 100

    # --- UI: MÉTRICAS PRINCIPALES ---
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Breadth (Acciones > SMA200)", f"{breadth.iloc[-1]:.1f}%", f"{b_slope.iloc[-1]:+.1f}")
    m2.metric("VIX (Miedo)", f"{vix.iloc[-1]:.2f}", delta=f"{vix.diff(1).iloc[-1]:+.2f}", delta_color="inverse")
    m3.metric("Extensión SPY/SMA200", f"{dist_pct.iloc[-1]:+.2f}%")
    m4.metric("Inercia SMA200 (Slope)", f"{sma_slope.iloc[-1]:+.4f}%")

    st.divider()

    # --- UI: TABLA HISTÓRICA ---
    st.subheader("📋 Matriz Histórica de Confluencias")
    periods = {'Actual': -1, '7 Días': -7, '30 Días': -30, '90 Días': -90}
    history = []
    for label, idx in periods.items():
        history.append({
            'Periodo': label, 'SPY Price': spy.iloc[idx], 'Ext %': dist_pct.iloc[idx],
            'VIX': vix.iloc[idx], 'HYG (Crédito)': hyg.iloc[idx], 'TLT (Bonos)': tlt.iloc[idx],
            'Breadth %': breadth.iloc[idx], 'B-Slope': b_slope.iloc[idx]
        })
    df_report = pd.DataFrame(history)
    
    # Estilizado
    st.dataframe(df_report.style.format({
        'SPY Price': '{:.2f}', 'Ext %': '{:+.2f}%', 'VIX': '{:.2f}',
        'HYG (Crédito)': '{:.2f}', 'TLT (Bonos)': '{:.2f}',
        'Breadth %': '{:.1f}%', 'B-Slope': '{:+.1f}'
    }).background_gradient(cmap='RdYlGn', subset=['Breadth %', 'HYG (Crédito)'])
      .background_gradient(cmap='RdYlGn_r', subset=['VIX']), use_container_width=True)

    # --- UI: DIAGNÓSTICO FINAL ---
    st.divider()
    actual = df_report.iloc[0]
    
    if actual['Breadth %'] > 60 and actual['VIX'] < 18:
        st.success("🎯 **DIAGNÓSTICO: SALUDABLE** - El mercado interno apoya la subida. Risk-On.")
    elif actual['Breadth %'] < 40:
        st.error("🎯 **DIAGNÓSTICO: PELIGRO** - Menos del 40% de las acciones están en tendencia. Fragilidad extrema.")
    elif actual['B-Slope'] < -5:
        st.warning("🎯 **DIAGNÓSTICO: ALERTA** - La participación está cayendo rápido. Posible corrección.")
    else:
        st.info("🎯 **DIAGNÓSTICO: NEUTRAL** - El mercado busca dirección clara.")

    # --- GRÁFICO DE BREADTH ---
    st.subheader("📈 Gráfico de Participación Total")
    fig, ax = plt.subplots(figsize=(10, 3))
    ax.fill_between(breadth.index, breadth, 50, color='lime' if breadth.iloc[-1] > 50 else 'red', alpha=0.2)
    ax.plot(breadth.index, breadth, color='white', lw=1)
    ax.axhline(60, color='green', ls='--', alpha=0.5)
    ax.axhline(40, color='red', ls='--', alpha=0.5)
    ax.set_facecolor('#0e1117')
    fig.patch.set_facecolor('#0e1117')
    st.pyplot(fig)

except Exception as e:
    st.error(f"Error al procesar el Breadth: {e}")
