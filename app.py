import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import datetime

# Configuración de la ventana web
st.set_page_config(page_title="Sistema de Análisis Tecno-Fundamental & Gamboa", page_icon="📈", layout="wide")

st.title("📈 Sistema de Análisis: Método V12 vs. Método Diana Gamboa")

# Inicializar Watchlist en la memoria de la sesión
if 'watchlist' not in st.session_state:
    st.session_state['watchlist'] = ["AAPL", "MSFT", "GOOGL", "NVDA"]

# Sidebar con Formulario y Herramientas
st.sidebar.header("Parámetros de Entrada")

with st.sidebar.form(key="ticker_form"):
    ticker_input = st.text_input("Ticker (Presiona Enter para analizar):", value="AAPL").upper()
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("⚙️ Parámetros Método V12 (Fundamental)")
    r_revenue = st.sidebar.number_input("Estimado Crecimiento R (%)", value=15.0, step=1.0, help="Variable R_Revenue de tu script")
    margin_req = st.sidebar.number_input("Margen de Seguridad Exigido (%)", value=15.0, step=1.0, help="Margen requerido para luz verde")

    st.sidebar.markdown("---")
    buscar_alternativas = st.checkbox("💡 Buscar acciones alternativas con menores múltiplos", value=False)
    
    btn_analizar = st.form_submit_button("🔍 Correr Análisis Dual", type="primary")

# Sidebar - Gestión de Watchlist Personal
st.sidebar.markdown("---")
st.sidebar.subheader("⭐ Watchlist Personal")
nuevo_watch = st.sidebar.text_input("Añadir Ticker a Watchlist:").upper()
if st.sidebar.button("➕ Guardar en Watchlist"):
    if nuevo_watch and nuevo_watch not in st.session_state['watchlist']:
        st.session_state['watchlist'].append(nuevo_watch)
        st.sidebar.success(f"¡{nuevo_watch} agregado!")

if st.sidebar.button("🗑️ Limpiar Watchlist"):
    st.session_state['watchlist'] = []
    st.sidebar.info("Watchlist vaciada.")

if st.session_state['watchlist']:
    st.sidebar.write("Tus tickers guardados:")
    st.sidebar.write(", ".join(st.session_state['watchlist']))

SECTORES_CICLICOS = [
    "Consumer Cyclical", "Financial Services", "Industrials", 
    "Basic Materials", "Real Estate", "Energy"
]

def obtener_detalles_empresa(ticker, info):
    nombre = info.get("longName") or info.get("shortName") or ticker
    sector = info.get("sector", "Sector No Especificado")
    industria = info.get("industry", "Industria No Especificada")
    
    quote_type = info.get("quoteType", "EQUITY")
    mapa_tipos = {
        "EQUITY": "Acción Ordinaria (Common Stock)",
        "ETF": "Fondo Cotizado (ETF)",
        "MUTUALFUND": "Fondo de Inversión (Mutual Fund)",
        "INDEX": "Índice Bursátil",
        "CURRENCY": "Divisa / Forex",
        "CRYPTOCURRENCY": "Criptomoneda"
    }
    tipo_activo = mapa_tipos.get(quote_type, f"Instrumento ({quote_type})")
    es_ciclica = "CÍCLICA 🔄" if sector in SECTORES_CICLICOS else "NO CÍCLICA / DEFENSIVA 🛡️"
    
    return {
        "nombre": nombre,
        "sector": sector,
        "industria": industria,
        "tipo_activo": tipo_activo,
        "ciclicidad": es_ciclica
    }

def obtener_descripcion_y_competidores(ticker, info):
    resumen = info.get("longBusinessSummary", "")
    if resumen:
        oraciones = resumen.split(". ")
        descripcion_corta = ". ".join(oraciones[:3]) + "." if len(oraciones) >= 3 else resumen
    else:
        descripcion_corta = "Descripción comercial no disponible actualmente en la fuente de datos."

    sector = info.get("sector", "")
    mapa_competidores = {
        "Technology": ["Microsoft (MSFT)", "Alphabet/Google (GOOGL)", "Apple (AAPL)", "Amazon (AMZN)", "Meta (META)", "NVIDIA (NVDA)"],
        "Consumer Cyclical": ["Amazon (AMZN)", "Tesla (TSLA)", "Home Depot (HD)", "Nike (NKE)", "McDonald's (MCD)"],
        "Financial Services": ["JPMorgan Chase (JPM)", "Bank of America (BAC)", "Visa (V)", "Mastercard (MA)", "Morgan Stanley (MS)"],
        "Healthcare": ["Johnson & Johnson (JNJ)", "Pfizer (PFE)", "Eli Lilly (LLY)", "Abbott (ABT)", "Merck (MRK)"],
        "Communication Services": ["Alphabet (GOOGL)", "Meta (META)", "Netflix (NFLX)", "Disney (DIS)", "Verizon (VZ)"],
        "Industrials": ["Caterpillar (CAT)", "Boeing (BA)", "General Electric (GE)", "Union Pacific (UNP)"],
        "Consumer Defensive": ["Procter & Gamble (PG)", "Walmart (WMT)", "Coca-Cola (KO)", "PepsiCo (PEP)", "Costco (COST)"],
        "Energy": ["ExxonMobil (XOM)", "Chevron (CVX)", "ConocoPhillips (COP)", "Shell (SHEL)"]
    }
    
    lista_comp = mapa_competidores.get(sector, ["Empresas del mismo sector e industria global"])
    competidores_filtrados = [c for c in lista_comp if ticker not in c]
    competidores_str = " | ".join(competidores_filtrados) if competidores_filtrados else "Competidores del sector directo"

    return descripcion_corta, competidores_str

def obtener_datos_reportes_trimestrales(stock):
    info_reporte = {
        "ultimo_reporte_fecha": "N/D",
        "eps_reportado": "N/D",
        "eps_estimado": "N/D",
        "sorpresa_eps": "N/D",
        "proximo_reporte_fecha": "No programada / Pendiente"
    }
    try:
        earnings_dates = stock.get_earnings_dates(limit=8)
        if earnings_dates is not None and not earnings_dates.empty:
            now = pd.Timestamp.now(tz=earnings_dates.index.tz)
            futuros = earnings_dates[earnings_dates.index > now]
            if not futuros.empty:
                info_reporte["proximo_reporte_fecha"] = futuros.index[-1].strftime("%d/%m/%Y")
            
            pasados = earnings_dates[earnings_dates.index <= now]
            if not pasados.empty:
                ultimo = pasados.iloc[0]
                info_reporte["ultimo_reporte_fecha"] = pasados.index[0].strftime("%d/%m/%Y")
                eps_rep = ultimo.get("Reported EPS")
                eps_est = ultimo.get("EPS Estimate")
                sorpresa = ultimo.get("Surprise(%)")
                
                if pd.notnull(eps_rep): info_reporte["eps_reportado"] = f"${eps_rep:.2f}"
                if pd.notnull(eps_est): info_reporte["eps_estimado"] = f"${eps_est:.2f}"
                if pd.notnull(sorpresa):
                    s_val = sorpresa * 100 if sorpresa < 1 else sorpresa
                    info_reporte["sorpresa_eps"] = f"{s_val:+.2f}%"
    except Exception:
        pass
    return info_reporte

def obtener_ubicacion_indices(ticker, info):
    indices_pertenencia = []
    market_cap = info.get("marketCap", 0)
    quote_type = info.get("quoteType", "")
    exchange = info.get("exchange", "")
    DOW_JONES_30 = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "BRK.B", "LLY", "AVGO", "JPM", "TSLA", "UNH", "V", "XOM", "PG", "MA", "JNJ", "HD", "COST", "ABBV", "MRK", "CVX", "CRM", "BAC", "WMT", "ACN", "MCD", "CSCO", "PEP", "TMO"]
    
    if quote_type == "EQUITY":
        if market_cap >= 18_000_000_000: indices_pertenencia.append("S&P 500 🇺🇸")
        elif market_cap >= 3_000_000_000: indices_pertenencia.append("S&P MidCap 400 🇺🇸")
        else: indices_pertenencia.append("Russell 2000 / SmallCap 🇺🇸")
            
        if exchange in ["NASDAQ", "NMS", "NGS"]:
            indices_pertenencia.append("Nasdaq-100 💻" if market_cap >= 25_000_000_000 else "Nasdaq Composite 💻")
                
        if ticker in DOW_JONES_30: indices_pertenencia.append("Dow Jones Industrial Average (DJIA) 🏛️")
            
    if not indices_pertenencia: indices_pertenencia.append("Cotización fuera de índices principales de EE.UU.")
    return " | ".join(indices_pertenencia)

def obtener_analisis_estacional_personalizado(ticker, info):
    mes_num = datetime.datetime.now().month
    meses_nombre = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    mes_actual = meses_nombre[mes_num - 1]
    sector = info.get("sector", "General")
    
    return {
        "mes_actual": mes_actual,
        "fase": f"Fase Estacional Activa para {ticker}",
        "sesgo": "Neutral / Positivo 🟢",
        "ventajas": f"Comportamiento alineado al sector {sector}.",
        "desventajas": "Vigilar reportes de ganancias y volatilidad.",
        "explicacion_riesgo": "Monitorear directrices macroeconómicas y reportes trimestrales.",
        "horizonte_swing": "Trimestral (3 Meses)"
    }

def calcular_indicadores_diana_gamboa(df):
    df['EMA_8'] = df['Close'].ewm(span=8, adjust=False).mean()
    df['EMA_21'] = df['Close'].ewm(span=21, adjust=False).mean()
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    df['SMA_200'] = df['Close'].rolling(window=200).mean()
    df['High_20'] = df['High'].rolling(20).max()

    ema8 = df['EMA_8'].iloc[-1]
    ema21 = df['EMA_21'].iloc[-1]
    sma50 = df['SMA_50'].iloc[-1] if not pd.isna(df['SMA_50'].iloc[-1]) else ema21
    sma200 = df['SMA_200'].iloc[-1] if not pd.isna(df['SMA_200'].iloc[-1]) else sma50
    precio = df['Close'].iloc[-1]

    es_abanico_alcista = (precio > ema8) and (ema8 > ema21) and (ema21 > sma50) and (sma50 > sma200)
    cruce_parceras_alcista = ema8 > ema21
    
    low_14 = df['Low'].rolling(window=14).min()
    high_14 = df['High'].rolling(window=14).max()
    stoch_k = 100 * ((df['Close'] - low_14) / (high_14 - low_14))
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    # Diagnóstico detallado de respiro para Diana Gamboa
    if abs(precio - ema8) / precio < 0.01:
        estado_respiro = "🟢 Respiro Leve en EMA 8 (Impulsiva activa)"
    elif abs(precio - ema21) / precio < 0.015:
        estado_respiro = "🟡 Respiro Sano en EMA 21 (La Parcera - Zona Ideal Buy Limit)"
    elif abs(precio - sma50) / precio < 0.02:
        estado_respiro = "🟠 Respiro Profundo en SMA 50 (Soporte Institucional)"
    elif precio < sma50:
        estado_respiro = "🔴 Precio por debajo de SMA 50 (Pérdida de estructura primaria)"
    else:
        estado_respiro = "🟢 Precio en expansión (Alejado de medias principales)"

    return {
        "ema8": ema8,
        "ema21": ema21,
        "sma50": sma50,
        "sma200": sma200,
        "high20": df['High_20'].iloc[-1],
        "abanico_alcista": es_abanico_alcista,
        "cruce_parceras": cruce_parceras_alcista,
        "estado_respiro": estado_respiro,
        "rsi": rsi.iloc[-1],
        "stoch": stoch_k.rolling(window=3).mean().iloc[-1]
    }

def calcular_valor_custom(eps, pe_ratio, r_rev):
    if eps is None or pe_ratio is None or eps <= 0 or pe_ratio <= 0:
        return None
    return eps * (1 + (r_rev / 100.0)) * pe_ratio

def calcular_ganancias_potenciales(precio_actual, vi_custom, high20):
    ganancia_vi = ((vi_custom - precio_actual) / precio_actual) * 100 if (vi_custom and vi_custom > precio_actual) else 0.0
    ganancia_high20 = ((high20 - precio_actual) / precio_actual) * 100 if high20 > precio_actual else 0.0
    target_3m = max(high20, precio_actual * 1.10)
    ganancia_3m = ((target_3m - precio_actual) / precio_actual) * 100

    return {
        "ganancia_vi": ganancia_vi,
        "ganancia_high20": ganancia_high20,
        "ganancia_3m": ganancia_3m,
        "target_3m": target_3m
    }

# Pestañas principales de navegación en la app
tab_analisis, tab_screener = st.tabs(["📊 Análisis Principal (Dual)", "⚡ Screener Rápido Watchlist"])

with tab_analisis:
    if btn_analizar or ticker_input:
        with st.spinner(f"Analizando {ticker_input} en tiempo real..."):
            stock = yf.Ticker(ticker_input)
            info = stock.info
            df = stock.history(period="1y")

            if df.empty or ("currentPrice" not in info and "regularMarketPrice" not in info):
                st.error("No se encontraron datos para el ticker proporcionado. Verifica que el ticker sea correcto.")
            else:
                precio_actual = info.get("currentPrice") or info.get("regularMarketPrice") or df['Close'].iloc[-1]
                
                detalles_emp = obtener_detalles_empresa(ticker_input, info)
                desc_corta, comp_str = obtener_descripcion_y_competidores(ticker_input, info)
                estacionalidad = obtener_analisis_estacional_personalizado(ticker_input, info)
                datos_reportes = obtener_datos_reportes_trimestrales(stock)
                pertenencia_indices = obtener_ubicacion_indices(ticker_input, info)
                tec = calcular_indicadores_diana_gamboa(df)

                eps_ttm = info.get("trailingEps", 0)
                pe_ttm = info.get('trailingPE', 0)
                forward_pe = info.get('forwardPE', 0)
                price_to_sales = info.get('priceToSalesTrailing12Months', 0)
                
                # Cálculos Método V12
                vi_custom = calcular_valor_custom(eps_ttm, pe_ttm, r_revenue)
                margen_sec_num = ((vi_custom - precio_actual) / vi_custom) * 100 if vi_custom else 0
                margen_sec_str = f"{margen_sec_num:.1f}%" if vi_custom else "N/D"
                cumple_v12 = vi_custom and margen_sec_num >= margin_req

                # Cálculos Método Gamboa
                cumple_gamboa = tec['cruce_parceras'] or tec['abanico_alcista']
                distancia_ema21_pct = ((precio_actual - tec['ema21']) / precio_actual) * 100

                ganancias_potenciales = calcular_ganancias_potenciales(precio_actual, vi_custom, tec['high20'])
                precio_ideal = min(precio_actual, tec['ema21'])

                # ENCABEZADO Y WATCHLIST
                col_title, col_btn = st.columns([4, 1])
                with col_title:
                    st.markdown(f"## 🏢 {detalles_emp['nombre']} ({ticker_input})")
                with col_btn:
                    if st.button("⭐ Guardar Ticker"):
                        if ticker_input not in st.session_state['watchlist']:
                            st.session_state['watchlist'].append(ticker_input)
                            st.success("¡Guardado!")

                st.markdown(f"**📝 Descripción Comercial:** {desc_corta}")
                st.markdown(f"**⚔️ Principales Competidores Directos:** `{comp_str}`")
                st.markdown("")

                c_sec1, c_sec2, c_sec3, c_sec4 = st.columns(4)
                c_sec1.info(f"**Tipo de Activo:**\n\n{detalles_emp['tipo_activo']}")
                c_sec2.info(f"**Sector:**\n\n{detalles_emp['sector']}")
                c_sec3.info(f"**Industria:**\n\n{detalles_emp['industria']}")
                c_sec4.info(f"**Naturaleza:**\n\n{detalles_emp['ciclicidad']}")

                # ==========================================
                # BLOQUE 1: TU MÉTODO TECNO-FUNDAMENTAL (V12)
                # ==========================================
                st.markdown("---")
                st.markdown("### 🧬 Bloque 1: Tu Método Tecno-Fundamental (V12)")
                st.caption("Enfoque de Valor Intrínseco, Múltiplos B|K y Margen de Seguridad.")

                b_v1, b_v2, b_v3, b_v4 = st.columns(4)
                b_v1.metric("Precio Actual", f"${precio_actual:.2f}")
                b_v2.metric("Valor Intrínseco (VI)", f"${vi_custom:.2f}" if vi_custom else "N/D")
                b_v3.metric("Margen de Seguridad", margen_sec_str, f"Exigido: {margin_req:.0f}%")
                
                if cumple_v12:
                    b_v4.success("🟢 **ESTADO V12:** LUZ VERDE (Margen Sólido)")
                else:
                    b_v4.error("🔴 **ESTADO V12:** SIN MARGEN SUFICIENTE")

                st.write(f"• **Múltiplos Base:** EPS TTM (B): `${eps_ttm:.2f}` | P/E Actual (K): `{pe_ttm:.2f}x` | Crecimiento Est. (R): `{r_revenue}%`")

                # ==========================================
                # BLOQUE 2: MÉTODO DIANA GAMBOA (TÉCNICO)
                # ==========================================
                st.markdown("---")
                st.markdown("### 🧘 Bloque 2: Método Diana Gamboa (Estructura Técnica)")
                st.caption("Enfoque de Medias Móviles en Abanico, Respiros y Cruce de Parceras.")

                b_g1, b_g2, b_g3, b_g4 = st.columns(4)
                b_g1.metric("EMA 8 (Impulsiva)", f"${tec['ema8']:.2f}")
                b_g2.metric("EMA 21 (Parcera / Buy Limit)", f"${tec['ema21']:.2f}", f"{distancia_ema21_pct:+.1f}% vs Precio")
                b_g3.metric("SMA 50 (Institucional)", f"${tec['sma50']:.2f}")
                b_g4.metric("SMA 200 (Piso Fuerte)", f"${tec['sma200']:.2f}")

                st.info(f"📌 **Estado de Respiro:** {tec['estado_respiro']}")
                if cumple_gamboa:
                    st.success("🟢 **ESTADO GAMBOA:** Estructura Técnica Favorable (Parceras Alcistas o Abanico Activo)")
                else:
                    st.warning("🟡 **ESTADO GAMBOA:** Estructura Lateral o Bajista (Esperar alineación)")

                # 3. RENDIMIENTOS Y GESTIÓN DE RIESGO
                st.markdown("---")
                st.subheader("📈 Rendimientos Potenciales & Gestión de Riesgo (Swing 3M)")
                
                c_op1, c_op2 = st.columns([1, 1])
                with c_op1:
                    st.markdown("#### 🎯 Proyecciones de Ganancia")
                    g1, g2, g3 = st.columns(3)
                    g1.metric("A Valor Intrínseco", f"+{ganancias_potenciales['ganancia_vi']:.1f}%" if ganancias_potenciales['ganancia_vi'] > 0 else "0.0%")
                    g2.metric("A Máximo 20 Días", f"+{ganancias_potenciales['ganancia_high20']:.1f}%" if ganancias_potenciales['ganancia_high20'] > 0 else "0.0%")
                    g3.metric("Proyección Swing (3M)", f"+{ganancias_potenciales['ganancia_3m']:.1f}%", f"Target: ${ganancias_potenciales['target_3m']:.2f}")

                with c_op2:
                    st.markdown("#### 🛡️ Calculadora de Posición (Stop-Loss en EMA 21)")
                    r_c1, r_c2 = st.columns(2)
                    with r_c1:
                        capital_arriesgar = st.number_input("Capital a Arriesgar ($ USD):", value=200.0, step=50.0)
                    with r_c2:
                        stop_loss_sugerido = st.number_input("Stop-Loss Sugerido:", value=round(tec['ema21'] * 0.98, 2), step=0.10)
                    
                    riesgo_por_accion = precio_actual - stop_loss_sugerido
                    if riesgo_por_accion > 0:
                        num_acciones = int(capital_arriesgar / riesgo_por_accion)
                        inversion_total = num_acciones * precio_actual
                        st.caption(f"**Acciones a Comprar:** `{num_acciones} títulos` | **Inversión Total:** `${inversion_total:,.2f}`")

                # 4. CALENDARIO E ÍNDICES
                st.markdown("---")
                st.subheader("📌 Contexto de Mercado, Índices & Reportes")
                col_ind1, col_ind2 = st.columns([1, 1])
                with col_ind1:
                    st.markdown("**🏛️ Ubicación en Índices Principales:**")
                    st.write(pertenencia_indices)
                    st.caption(f"**Capitalización de Mercado:** ${info.get('marketCap', 0):,}")
                with col_ind2:
                    st.markdown("**📊 Resultados del Último Reporte Trimestral:**")
                    st.write(f"• **Fecha:** {datos_reportes['ultimo_reporte_fecha']}")
                    st.write(f"• **EPS Reportado:** {datos_reportes['eps_reportado']} | **Estimado:** {datos_reportes['eps_estimado']} (Sorpresa: **{datos_reportes['sorpresa_eps']}**)")
                    st.write(f"• **📅 Próximo Reporte Programado:** **{datos_reportes['proximo_reporte_fecha']}**")

                # 5. GRÁFICO INTERACTIVO
                st.markdown("---")
                fig = go.Figure()
                fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Precio"))
                fig.add_trace(go.Scatter(x=df.index, y=df['EMA_8'], line=dict(color='magenta', width=1.5), name="EMA 8"))
                fig.add_trace(go.Scatter(x=df.index, y=df['EMA_21'], line=dict(color='orange', width=1.5), name="EMA 21"))
                fig.add_trace(go.Scatter(x=df.index, y=df['SMA_50'], line=dict(color='cyan', width=2), name="SMA 50"))
                fig.add_trace(go.Scatter(x=df.index, y=df['SMA_200'], line=dict(color='white', width=2), name="SMA 200"))
                
                if vi_custom and vi_custom > 0:
                    fig.add_hline(y=vi_custom, line_dash="solid", line_color="lime", annotation_text=f"VI Custom (V12): ${vi_custom:.2f}")
                fig.add_hline(y=precio_ideal, line_dash="dash", line_color="gold", annotation_text=f"Buy Limit (Gamboa): ${precio_ideal:.2f}")
                
                fig.update_layout(template="plotly_dark", height=450, xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)

with tab_screener:
    st.subheader("⚡ Screener Rápido de tu Watchlist (Análisis Dual)")
    st.write("Compara de un vistazo qué tickers cumplen tu regla fundamental V12 y cuáles cumplen la regla técnica de Diana Gamboa:")

    if not st.session_state['watchlist']:
        st.info("Tu watchlist está vacía. Añade tickers desde la barra lateral o al analizar una acción.")
    else:
        datos_screener = []
        for t_item in st.session_state['watchlist']:
            try:
                stk_s = yf.Ticker(t_item)
                inf_s = stk_s.info
                p_s = inf_s.get("currentPrice") or inf_s.get("regularMarketPrice", 0)
                eps_s = inf_s.get("trailingEps", 0)
                pe_s = inf_s.get("trailingPE", 0)
                vi_s = calcular_valor_custom(eps_s, pe_s, r_revenue)
                marg_s = ((vi_s - p_s) / vi_s) * 100 if vi_s else 0
                
                hist_s = stk_s.history(period="3m")
                if not hist_s.empty:
                    e8_s = hist_s['Close'].ewm(span=8, adjust=False).mean().iloc[-1]
                    e21_s = hist_s['Close'].ewm(span=21, adjust=False).mean().iloc[-1]
                    est_gamboa = "🟢 Alcista" if e8_s > e21_s else "🔴 Lateral/Bajista"
                else:
                    est_gamboa = "N/D"

                estado_v12 = "🟢 Luz Verde" if (vi_s and marg_s >= margin_req) else "🔴 Sin Margen"

                datos_screener.append({
                    "Ticker": t_item,
                    "Precio": f"${p_s:.2f}",
                    "VI Custom": f"${vi_s:.2f}" if vi_s else "N/D",
                    "Margen V12": f"{marg_s:.1f}%",
                    "Bloque V12": estado_v12,
                    "Bloque Gamboa": est_gamboa
                })
            except Exception:
                continue

        if datos_screener:
            df_scr = pd.DataFrame(datos_screener)
            st.dataframe(df_scr, use_container_width=True)
