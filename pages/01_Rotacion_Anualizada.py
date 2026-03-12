import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

import streamlit as st
import yfinance as yf
# ... otros imports ...

# --- AGREGÁ ESTO AQUÍ ---
from streamlit_autorefresh import st_autorefresh

# Refresco automático cada 15 minutos
# (15 min * 60 seg * 1000 ms = 900.000)
st_autorefresh(interval=900000, key="rotacion_refresh")
# ------------------------

st.set_page_config(page_title="Radar de Rotación Pro", layout="wide")

st.title("🚀 Radar de Aceleración y Rotación Sectorial")
st.markdown("Comparativa de Tasas Anualizadas de Fuerza Relativa vs SPY")

@st.cache_data (ttl=900)
def get_data(p):
    sectors = {
        "XLK": "Tech", "XLE": "Energy", "XLF": "Financials",
        "XLV": "Health", "XLP": "Staples", "XLY": "Discretionary",
        "XLI": "Industrials", "XLC": "Comm", "XLRE": "RealEstate",
        "XLB": "Materials", "XLU": "Utilities"
    }
    tickers = list(sectors.keys()) + ["SPY"]
    raw_data = yf.download(tickers, period=p, interval="1d")
    data = raw_data['Adj Close'] if 'Adj Close' in raw_data.columns else raw_data['Close']
    return data, sectors

periodo = st.sidebar.selectbox("Historial de datos", ["1y", "2y", "5y"], index=1)

try:
    data, sectors = get_data(periodo)
    rs_df = pd.DataFrame()
    for tick, name in sectors.items():
        rs_df[name] = data[tick] / data['SPY']

    # Cálculo de Tasas Anualizadas
    periods = {'90D': 63, '30D': 21, '7D': 5}
    ann_data = {}
    for label, days in periods.items():
        curr = rs_df.iloc[-1]
        past = rs_df.iloc[-(days + 1)]
        ret = (curr / past) - 1
        ann_data[label] = ((1 + ret)**(252/days) - 1) * 100

    df_ann = pd.DataFrame(ann_data)
    
    # Cálculo de la Aceleración (Slope)
    df_ann['Aceleración'] = df_ann.apply(lambda row: np.polyfit([0, 1, 2], [row['90D'], row['30D'], row['7D']], 1)[0], axis=1)
    df_ann = df_ann.sort_values(by='Aceleración', ascending=False)

    # --- GRÁFICO MEJORADO ---
    fig, ax = plt.subplots(figsize=(14, 8))
    labels = df_ann.index
    x = np.arange(len(labels))
    width = 0.25

    rects1 = ax.bar(x - width, df_ann['90D'], width, label='90D Anual', color='#34495e', alpha=0.3)
    rects2 = ax.bar(x, df_ann['30D'], width, label='30D Anual', color='#3498db', alpha=0.5)
    rects3 = ax.bar(x + width, df_ann['7D'], width, label='7D Anual', color='#2ecc71', alpha=0.8)

    # Función para poner etiquetas de porcentaje en las barras
    def autolabel(rects):
        for rect in rects:
            height = rect.get_height()
            ax.annotate(f'{height:.1f}%',
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3 if height > 0 else -12),
                        textcoords="offset points",
                        ha='center', va='bottom' if height > 0 else 'top',
                        fontsize=8, fontweight='bold')

    autolabel(rects1)
    autolabel(rects2)
    autolabel(rects3)

    # Etiquetas de Aceleración y flechas
    for i in range(len(labels)):
        acc = df_ann['Aceleración'].iloc[i]
        color = 'green' if acc > 0 else 'red'
        icon = "▲" if acc > 0 else "▼"
        y_max = max(df_ann.iloc[i, :3])
        y_min = min(df_ann.iloc[i, :3])
        pos_y = y_max + 15 if y_max > 0 else y_min - 25
        
        ax.text(x[i], pos_y, f"{icon}\n{acc:+.1f}", ha='center', va='center', 
                color=color, fontweight='bold', bbox=dict(facecolor='white', alpha=0.6, edgecolor=color))

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, fontweight='bold')
    ax.set_ylabel("Tasa Anualizada (%)")
    ax.axhline(0, color='black', lw=1)
    ax.legend(loc='upper right')
    
    st.pyplot(fig)

    # --- TABLA FORMATEADA ---
    st.subheader("Matriz de Rendimientos Relativos Anualizados")
    
    # Formateo de 2 decimales y símbolo de porcentaje
    styled_df = df_ann.style.format("{:.2f}%").background_gradient(
        cmap='RdYlGn', subset=['7D', 'Aceleración']
    )
    
    st.dataframe(styled_df, use_container_width=True)

except Exception as e:
    st.error(f"Hubo un problema al procesar los datos: {e}")
