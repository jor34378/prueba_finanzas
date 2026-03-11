import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

st.set_page_config(page_title="Radar de Rotación Pro", layout="wide")

st.title("🚀 Radar de Aceleración y Rotación Sectorial")
st.markdown("Esta aplicación analiza la **Fuerza Relativa (RS)** de los sectores contra el SPY.")

@st.cache_data
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

    periods = {'90D': 63, '30D': 21, '7D': 5}
    ann_data = {}
    for label, days in periods.items():
        curr = rs_df.iloc[-1]
        past = rs_df.iloc[-(days + 1)]
        ret = (curr / past) - 1
        ann_data[label] = ((1 + ret)**(252/days) - 1) * 100

    df_ann = pd.DataFrame(ann_data)
    df_ann['Aceleración'] = df_ann.apply(lambda row: np.polyfit([0, 1, 2], [row['90D'], row['30D'], row['7D']], 1)[0], axis=1)
    df_ann = df_ann.sort_values(by='Aceleración', ascending=False)

    fig, ax = plt.subplots(figsize=(12, 7))
    labels = df_ann.index
    x = np.arange(len(labels))
    width = 0.25
    ax.bar(x - width, df_ann['90D'], width, label='90D', color='#34495e', alpha=0.3)
    ax.bar(x, df_ann['30D'], width, label='30D', color='#3498db', alpha=0.5)
    ax.bar(x + width, df_ann['7D'], width, label='7D', color='#2ecc71', alpha=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45)
    ax.legend()
    st.pyplot(fig)
    st.dataframe(df_ann.style.background_gradient(cmap='RdYlGn'))

except Exception as e:
    st.error(f"Error: {e}")
