import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# Configuración de la página
st.set_page_config(page_title="Quant Screener Pro", layout="wide")

# Autorefresh cada 15 minutos (900.000 milisegundos)
st_autorefresh(interval=15 * 60 * 1000, key="data_refresh")

st.title("📊 Terminal Quant: S&P 500 Screener")
st.write(f"Última actualización: {datetime.now().strftime('%H:%M:%S')}")

# Lista de tickers (reducida para velocidad, puedes usar la de Wikipedia si prefieres)
TICKERS = [
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "BRK-B", "TSLA", "AVGO", "LLY",
    "UNH", "V", "MA", "JPM", "HD", "PG", "COST", "JNJ", "ABBV", "ADBE",
    "CRM", "WMT", "BAC", "NFLX", "AMD", "PEP", "TMO", "KO", "XOM", "ORCL",
    "LIN", "ACN", "DIS", "INTC", "CSCO", "CVX", "ABT", "TMUS", "VZ"
]

@st.cache_data(ttl=900) # Caché interna de 15 min para no saturar yfinance
def run_full_pro_screener(tickers_list):
    data = yf.download(tickers_list, period="2y", group_by='ticker', threads=True, progress=False)
    results = []
    
    for ticker in tickers_list:
        try:
            df_t = data[ticker].dropna()
            if len(df_t) < 50: continue
            
            close = df_t['Close']
            high = df_t['High']
            low = df_t['Low']
            vol = df_t['Volume']
            last_price = float(close.iloc[-1])
            
            # --- 1. ADX (Puro Pandas/Numpy) ---
            plus_dm = high.diff().clip(lower=0)
            minus_dm = (-low.diff()).clip(lower=0)
            tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
            atr_14 = tr.rolling(14).mean()
            plus_di = 100 * (plus_dm.rolling(14).mean() / atr_14)
            minus_di = 100 * (minus_dm.rolling(14).mean() / atr_14)
            dx = 100 * (abs(plus_di - minus_di) / (plus_di + minus_di))
            adx_val = float(dx.rolling(14).mean().iloc[-1])
            
            # --- 2. VR y ATR ---
            vr_val = float(vol.iloc[-1] / vol.rolling(20).mean().iloc[-1])
            current_atr = float(atr_14.iloc[-1])
            
            # --- 3. TÉCNICOS ---
            ema21 = close.ewm(span=21, adjust=False).mean().iloc[-1]
            ema200 = close.ewm(span=200, adjust=False).mean().iloc[-1]
            dist_ema21 = ((last_price - ema21)/ema21)*100
            dist_ema200 = ((last_price - ema200)/ema200)*100
            
            # RSI Puro Pandas
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rsi_val = float(100 - (100 / (1 + (gain/loss))).iloc[-1])
            
            # MACD Puro Pandas
            macd_series = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
            signal_series = macd_series.ewm(span=9, adjust=False).mean()
            m_line = float(macd_series.iloc[-1])
            s_line = float(signal_series.iloc[-1])
            m_hist = m_line - s_line

            # --- 4. FUNDAMENTALES ---
            # En Streamlit, yf.info puede ser lento. Usamos manejo de errores.
            ticker_obj = yf.Ticker(ticker)
            info = ticker_obj.info
            pe = info.get('trailingPE', np.nan)
            target = info.get('targetMeanPrice', np.nan)
            upside_val = float(((target - last_price) / last_price * 100)) if target else 0.0

            # --- LÓGICA DE SCORE (0 a 6) ---
            score = 0
            if -1.0 <= dist_ema21 <= 1.0: score += 1
            if 0.0 <= dist_ema200 <= 2.0: score += 1
            if m_line < 0 and s_line < 0 and -0.5 <= m_hist <= 0.5: score += 1
            if adx_val > 22: score += 1
            if vr_val >= 1.2: score += 1
            if upside_val >= 25.0: score += 1
            
            results.append({
                'Ticker': ticker, 'Price': last_price, 'Score': score, 'RSI': rsi_val,
                'Dist_EMA21_%': dist_ema21, 'Dist_EMA200_%': dist_ema200,
                'MACD_Line': m_line, 'MACD_Signal': s_line, 'MACD_Hist': m_hist,
                'ADX': adx_val, 'ATR': current_atr, 'VR': vr_val,
                'P/E': pe, 'Target': target, 'Upside_%': upside_val,
                'Stoploss': last_price - (2 * current_atr)
            })
        except:
            continue
            
    return pd.DataFrame(results)

# Interfaz de Streamlit
with st.spinner("Calculando métricas..."):
    df_final = run_full_pro_screener(TICKERS)

if not df_final.empty:
    # Aplicar estilos
    df_sorted = df_final.sort_values(by='Score', ascending=False)
    
    styled_df = df_sorted.style \
        .background_gradient(subset=['Score'], cmap='RdYlGn') \
        .background_gradient(subset=['Upside_%'], cmap='YlGn') \
        .map(lambda x: 'color: red; font-weight: bold' if x <= 35 else '', subset=['RSI']) \
        .format({
            'Price': '${:.2f}', 'RSI': '{:.1f}', 'Dist_EMA21_%': '{:.2f}%', 
            'Dist_EMA200_%': '{:.2f}%', 'ADX': '{:.1f}', 'ATR': '{:.2f}', 
            'VR': '{:.2f}x', 'Upside_%': '{:.2f}%', 'Stoploss': '${:.2f}', 'Target': '${:.2f}'
        }, na_rep="-")
    
    st.dataframe(styled_df, use_container_width=True, height=800)
else:
    st.error("No se pudieron cargar los datos.")
