import streamlit as st
import yfinance as yf
import pandas as pd
import io
import requests
import re
import matplotlib.pyplot as plt

# --- AGREGÁ ESTO AQUÍ ---
from streamlit_autorefresh import st_autorefresh

# Refresco automático cada 15 minutos
# (15 min * 60 seg * 1000 ms = 900.000)
st_autorefresh(interval=900000, key="breadth_refresh")
# ------------------------

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Market Breadth 500", layout="wide")

# --- FUNCIÓN RSI MANUAL ---
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# --- CARGA DE DATOS ---
@st.cache_data(ttl=3600)
def get_breadth_data():
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    df_wiki = pd.read_html(io.StringIO(resp.text))[0]
    all_tickers = [re.sub(r'\.', '-', t) for t in df_wiki['Symbol'].tolist()]
    
    global_assets = ["SPY", "^VIX", "HYG", "TLT"]
    
    with st.spinner("Descargando datos y calculando métricas..."):
        data_raw = yf.download(all_tickers + global_assets, period="2y", interval="1d", auto_adjust=True, progress=False)
        data = data_raw['Close'] if 'Close' in data_raw.columns else data_raw
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
    return data, all_tickers

try:
    data, all_tickers = get_breadth_data()
    
    spy = data['SPY'].dropna()
    vix = data['^VIX'].dropna()
    hyg = data['HYG'].dropna()
    tlt = data['TLT'].dropna()
    
    # --- CÁLCULOS TÉCNICOS ---
    all_sma200 = data[all_tickers].rolling(window=200).mean()
    breadth = (data[all_tickers] > all_sma200).sum(axis=1) / len(all_tickers) * 100
    
    sma200_spy = spy.rolling(window=200).mean()
    dist_pct = ((spy / sma200_spy) - 1) * 100
    rsi_spy = calculate_rsi(spy)
    
    b_slope = breadth.diff(5)
    sma_slope = (sma200_spy.diff(5) / sma200_spy.shift(5)) * 100

    st.title("🧬 Módulo 3: Market Breadth & Global Regime")
    
    # --- 1. MÉTRICAS PRINCIPALES (Flechitas) ---
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Breadth (> SMA200)", f"{breadth.iloc[-1]:.1f}%", f"{b_slope.iloc[-1]:+.1f}")
    m2.metric("RSI SPY (14d)", f"{rsi_spy.iloc[-1]:.1f}")
    m3.metric("Extensión SPY/SMA200", f"{dist_pct.iloc[-1]:+.2f}%")
    m4.metric("VIX", f"{vix.iloc[-1]:.2f}", delta=f"{vix.diff(1).iloc[-1]:+.2f}", delta_color="inverse")

    st.divider()

    # --- 2. GRÁFICOS TÉCNICOS (RSI y Extensión) ---
    col_g1, col_g2 = st.columns(2)

    with col_g1:
        st.subheader("📈 RSI (Fuerza Relativa)")
        fig_rsi, ax_rsi = plt.subplots(figsize=(10, 4))
        ax_rsi.plot(rsi_spy.index, rsi_spy, color='#00FFAA', lw=1.5)
        ax_rsi.axhline(70, color='red', ls='--', alpha=0.5)
        ax_rsi.axhline(30, color='green', ls='--', alpha=0.5)
        ax_rsi.fill_between(rsi_spy.index, rsi_spy, 70, where=(rsi_spy >= 70), color='red', alpha=0.3)
        ax_rsi.fill_between(rsi_spy.index, rsi_spy, 30, where=(rsi_spy <= 30), color='green', alpha=0.3)
        ax_rsi.set_facecolor('#0e1117')
        fig_rsi.patch.set_facecolor('#0e1117')
        st.pyplot(fig_rsi)

    with col_g2:
        st.subheader("📏 Extensión % vs SMA200")
        fig_ext, ax_ext = plt.subplots(figsize=(10, 4))
        ax_ext.plot(dist_pct.index, dist_pct, color='white', lw=1.5)
        ax_ext.axhline(8, color='orange', ls='-', label="Umbral de Euforia (8%)")
        ax_ext.axhline(0, color='gray', ls='--', alpha=0.5)
        ax_ext.fill_between(dist_pct.index, dist_pct, 8, where=(dist_pct >= 8), color='orange', alpha=0.4)
        ax_ext.set_facecolor('#0e1117')
        fig_ext.patch.set_facecolor('#0e1117')
        st.pyplot(fig_ext)

    # --- 3. TABLA HISTÓRICA (MATRIZ) ---
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
    
    st.dataframe(df_report.style.format({
        'SPY Price': '{:.2f}', 'Ext %': '{:+.2f}%', 'VIX': '{:.2f}',
        'HYG (Crédito)': '{:.2f}', 'TLT (Bonos)': '{:.2f}',
        'Breadth %': '{:.1f}%', 'B-Slope': '{:+.1f}'
    }).background_gradient(cmap='RdYlGn', subset=['Breadth %', 'HYG (Crédito)'])
      .background_gradient(cmap='RdYlGn_r', subset=['VIX']), use_container_width=True)

    # --- 4. GRÁFICO DE BREADTH (EL ORIGINAL) ---
    st.subheader("📊 Participación Total (Acciones > SMA200)")
    fig_b, ax_b = plt.subplots(figsize=(10, 3))
    ax_b.fill_between(breadth.index, breadth, 50, color='lime' if breadth.iloc[-1] > 50 else 'red', alpha=0.2)
    ax_b.plot(breadth.index, breadth, color='white', lw=1)
    ax_b.axhline(60, color='green', ls='--', alpha=0.5)
    ax_b.axhline(40, color='red', ls='--', alpha=0.5)
    ax_b.set_facecolor('#0e1117')
    fig_b.patch.set_facecolor('#0e1117')
    st.pyplot(fig_b)

    # --- 5. TEXTO DE GUÍA TÉCNICA ---
    st.divider()
    st.markdown("""
    # 📉 GUÍA TÉCNICA: DINÁMICA DE VARIABLES Y CONFLUENCIAS
    ---
    ## 🧬 1. LECTURAS INDIVIDUALES (El ADN de cada variable)
    """)
    
    data_guia = [
        ["VIX (Miedo)", "> 22", "Compra de 'seguros' (Puts). Riesgo de caída vertical inminente."],
        ["Breadth %", "< 40%", "Mercado 'hueco'. El índice es sostenido por pocas empresas."],
        ["B-Slope", "< -10", "Capitulación: Ventas por pánico de forma indiscriminada."],
        ["Extensión %", "> +8%", "Euforia: El precio está muy lejos de su media (regresión inminente)."],
        ["HYG (Crédito)", "Bajando", "El 'dinero inteligente' detecta estrés crediticio. Señal líder."],
        ["TLT (Bonos)", "Subiendo", "Flight to Safety: Los fondos huyen del riesgo hacia bonos."],
        ["SMA_S %", "Tendiendo a 0", "Pérdida de inercia: El portaaviones está apagando motores."]
    ]
    df_guia = pd.DataFrame(data_guia, columns=["Variable", "Umbral de Alerta", "Significado Técnico"])
    st.table(df_guia)

    st.markdown("""
    ## ⚡ 2. CONFLUENCIAS CRÍTICAS (Escenarios Combinados)
    
    ### 🔴 **ESCENARIO: La Trampa de los Gigantes (Distribución)**
    * **Variables:** SPY sube/lateral + Breadth cae (< 50%) + VIX subiendo (> 18).
    * **Interpretación:** Las Megacaps (Apple, NVDA) ocultan la caída del resto de las 500 acciones.
    * **Acción:** **Reducir exposición.** Preludio de caída fuerte. No compres "el dip".

    ### 🟢 **ESCENARIO: El Impulso de Despegue (Breadth Thrust)**
    * **Variables:** SPY rompe resistencia + B-Slope muy positivo (> +10) + VIX bajando.
    * **Interpretación:** Entrada masiva de dinero en todos los sectores, no solo tech.
    * **Acción:** **Comprar / Risk-On.** Máxima probabilidad de éxito en largos.

    ### 🟡 **ESCENARIO: El Goteo de Sangre (Bear Market lento)**
    * **Variables:** SMA_S % negativa + HYG cayendo + TLT subiendo.
    * **Interpretación:** El crédito y los bonos confirman daño en la economía real. Rebotes falsos.
    * **Acción:** **Cash es Rey.** Buscar shorts o quedarse fuera.

    ### 🔵 **ESCENARIO: Suelo de Capitulación (El Gran Rebote)**
    * **Variables:** Breadth < 15% + VIX > 30 + B-Slope girando a verde (+).
    * **Interpretación:** Ya no quedan vendedores. El pánico ha limpiado el mercado.
    * **Acción:** **Cargar posiciones.** Punto de máximo beneficio potencial.
    
    ---
    ## 📊 3. MATRIZ DE TOMA DE DECISIÓN TÁCTICA
    """)

    st.markdown("""
    | Si el Semáforo es... | Estado VIX y TLT | Estado Breadth y SMA_S | Acción Recomendada |
    | :--- | :--- | :--- | :--- |
    | **🟢 RISK-ON** | VIX < 18 y TLT bajando | Breadth > 60% y SMA_S subiendo | **Agresivo.** Mantener y buscar nuevas entradas. |
    | **🟡 CAUTELA** | VIX 18-22 y TLT lateral | Breadth 45-55% y SMA_S plana | **Neutral.** Ajustar Stops; no ampliar riesgo. |
    | **🔴 RISK-OFF** | VIX > 22 y TLT subiendo | Breadth < 40% y SMA_S bajando | **Defensivo.** Salir de posiciones y ganar liquidez. |
    
    ---
    ## 🎓 4. CONSEJOS DE NIVEL "ADVANCED JUNIOR"
    * **⚠️ Prioridad de Variables:** Si el **VIX** y el **HYG** muestran peligro, ignora cualquier vela alcista en el precio. La liquidez siempre manda sobre el gráfico.
    * **🔍 El Filtro de los 90 días:** Si el **Breadth** actual es menor al de hace 90 días pero el **SPY** está en un precio mayor, estás en una **Divergencia Terminal**. El agotamiento es total.
    """)

except Exception as e:
    st.error(f"Error en el dashboard: {e}")
