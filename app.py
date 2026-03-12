import streamlit as st

st.set_page_config(page_title="Trading OS - Dashboard", layout="wide")

st.title("🖥️ Trading OS: Sistema de Evaluaciòn y seleccion de activos")

st.markdown("""
### Bienvenido al Centro de Comando de Mercado
Este sistema está diseñado para analizar el flujo de capital institucional y el régimen de mercado en tiempo real.

**Usa el menú de la izquierda para navegar por los módulos:**

1.  **🚀 Rotación Anualizada:** Análisis de momentum y fuerza relativa (RS) ajustada por tiempo.
2.  **📊 Dashboard Técnico:** RS normalizado vs medias móviles (EMA 21/50).
3.  **⚖️ Market Regime:** (Próximamente) Análisis de volatilidad y estructura del SPY.

---

""")

st.sidebar.info("Seleccioná un módulo arriba para comenzar.")
