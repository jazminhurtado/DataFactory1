import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import random

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Minería de Procesos", layout="wide")

# --- CARGA DE DATOS ---
@st.cache_data
def cargar_datos():
    log = pd.read_csv(
        "data/log_eventos_con_hora.csv",
        parse_dates=['inicio_actividad', 'fin_actividad']
    )
    variantes = pd.read_csv("data/variantes_proceso_con_hora.csv")
    duracion = pd.read_csv("data/duracion_real_por_ticket.csv")
    return log, variantes, duracion

log, variantes, duracion = cargar_datos()

# --- CÁLCULO DURACIÓN HORAS ---
log['duracion_horas'] = (
    log['fin_actividad'] - log['inicio_actividad']
).dt.total_seconds() / 3600

log['duracion_horas'] = log['duracion_horas'].round(2)
duracion["duracion_proceso_horas"] = duracion["duracion_proceso_horas"].round(2)

# --- CLASIFICACIÓN DE ALERTA ---
def clasificar_ticket(duracion):
    if duracion <= 1500:
        return "✅ OK"
    elif duracion <= 3000:
        return "⚠️ Medio"
    else:
        return "🔥 Crítico"

duracion["nivel_alerta"] = duracion["duracion_proceso_horas"].apply(clasificar_ticket)

# --- ENCABEZADO ---
st.title("📊 Análisis del Proceso Generación de Tickets")
st.markdown("Visualización del flujo real de requerimientos según registros de eventos.")

# --- KPIs ---
#st.subheader("🔢 KPIs Generales")
col1, col2, col3 = st.columns(3)

col1.metric("🎫 Tickets únicos", log['id_ticket'].nunique())
col2.metric("⚙️ Actividades distintas", log['actividad'].nunique())
col3.metric(
    "⏱️ Promedio duración total (horas)",
    int(duracion["duracion_proceso_horas"].mean())
)

# --- TABLA LOG ---
st.subheader("📋 Log de Eventos por Actividad")
st.dataframe(log, use_container_width=True)

# --- FILTRO ---
st.sidebar.header("🎛️ Filtros")
ticket_sel = st.sidebar.selectbox(
    "Ticket específico",
    ["Todos"] + sorted(log['id_ticket'].unique())
)

# =========================================================
# 🔁 VARIANTES DEL PROCESO (CON TICKETS REALES)
# =========================================================

st.subheader("🔁 Variantes del Proceso")

# 1️⃣ Secuencia por ticket
secuencia_por_ticket = (
    log.sort_values(by=["id_ticket", "inicio_actividad"])
    .groupby("id_ticket")["actividad"]
    .apply(lambda x: " ➔ ".join(x))
    .reset_index(name="secuencia")
)

# 2️⃣ Tabla de variantes reales
variantes_reales = (
    secuencia_por_ticket
    .groupby("secuencia")
    .agg(
        cantidad=("id_ticket", "count"),
        tickets=("id_ticket", list)
    )
    .reset_index()
    .sort_values(by="cantidad", ascending=False)
)

# 3️⃣ Selectbox para seleccionar variante
opciones_variantes = variantes_reales["secuencia"].tolist()
variante_sel = st.selectbox("Selecciona una variante específica", opciones_variantes)

# 4️⃣ Filtrar la tabla para mostrar solo la variante seleccionada
tabla_filtrada = variantes_reales[variantes_reales["secuencia"] == variante_sel]

# 5️⃣ Mostrar tabla con tickets como string
tabla_filtrada = tabla_filtrada.copy()
tabla_filtrada["tickets"] = tabla_filtrada["tickets"].apply(lambda x: ", ".join(x))

st.dataframe(tabla_filtrada, use_container_width=True)




# --- EVENTOS DEL TICKET SELECCIONADO ---
if ticket_sel != "Todos":
    st.subheader(f"🔎 Eventos del Ticket: {ticket_sel}")

    # Ordenar por fecha de inicio
    eventos_ticket = log[log['id_ticket'] == ticket_sel].sort_values(by="inicio_actividad")
    st.dataframe(eventos_ticket, use_container_width=True)

    # --- COMPARAR DURACIONES ---
    total_duracion_actividades = eventos_ticket["duracion_horas"].sum()
    duracion_ticket = duracion[duracion["id_ticket"] == ticket_sel]

    if not duracion_ticket.empty:
        total_duracion_proceso = duracion_ticket["duracion_proceso_horas"].values[0]
        
        suma_actividades = int(round(total_duracion_actividades, 0))
        duracion_total = int(round(total_duracion_proceso, 0))
        tiempo_espera = duracion_total - suma_actividades
        
        st.info(f"🧮 **Suma de actividades:** {suma_actividades} horas")
        st.info(f"📦 **Duración total del proceso:** {duracion_total} horas")
        st.info(f"⏱️ **Tiempo en espera/inactividad:** {tiempo_espera} horas")     
      
    else:
        st.warning("⚠️ No se encontró la duración total del ticket en la tabla de duración.")






# --- DURACIONES ---
st.subheader("⏳ Duraciones reales por Ticket")
if ticket_sel != "Todos":
    st.dataframe(
        duracion[duracion['id_ticket'] == ticket_sel],
        use_container_width=True
    )
else:
    st.dataframe(duracion, use_container_width=True)

# --- ANÁLISIS DE ACTIVIDADES POR TICKET ---
if ticket_sel != "Todos":
    st.subheader("📈 Análisis de Actividades del Ticket Seleccionado")

    actividades_ticket = log[log["id_ticket"] == ticket_sel]

    if not actividades_ticket.empty:
        duraciones_actividad = actividades_ticket["duracion_horas"].dropna()

        # 1️⃣ Promedio y Mediana por ticket
        promedio_actividad = int(round(duraciones_actividad.mean(), 0))
        mediana_actividad = int(round(duraciones_actividad.median(), 0))

        col1, col2 = st.columns(2)
        col1.metric("📊 Promedio de duración por actividad", promedio_actividad)
        col2.metric("📏 Mediana por actividad", mediana_actividad)

        # 2️⃣ Outliers internos (actividades del ticket)
        #q1_a = duraciones_actividad.quantile(0.25)
        #q3_a = duraciones_actividad.quantile(0.75)
        #iqr_a = q3_a - q1_a
        #limite_outlier = q3_a + 1.5 * iqr_a

        #outliers_act = actividades_ticket[actividades_ticket["duracion_horas"] > limite_outlier]

        st.markdown(f"🔍 Se detectaron **{len(outliers_act)} actividades** como _outliers_ (>{int(limite_outlier)} horas)")
        st.dataframe(outliers_act, use_container_width=True)

        # 3️⃣ Boxplot actividades del ticket
        st.markdown("### 📦 Boxplot de duración por actividad")
        fig_box_actividad = px.box(
            actividades_ticket,
            y="duracion_horas",
            points="all",
            title=f"Distribución de Duración por Actividad - {ticket_sel}"
        )
        st.plotly_chart(fig_box_actividad, use_container_width=True)

        # 4️⃣ Histograma por ticket
        st.markdown("### 📊 Histograma de duración de actividades")
        fig_hist_actividad = px.histogram(
            actividades_ticket,
            x="duracion_horas",
            nbins=10,
            title=f"Histograma de Duración de Actividades - {ticket_sel}",
            labels={"duracion_horas": "Duración (horas)"}
        )
        st.plotly_chart(fig_hist_actividad, use_container_width=True)







# --- BARRAS DURACIÓN ---
st.subheader("📊 Duración Total del Proceso por Ticket")

if ticket_sel != "Todos":
    df_top = duracion[duracion['id_ticket'] == ticket_sel]
    titulo = f"Duración del Ticket {ticket_sel}"
else:
    n = st.slider("Top N tickets más largos", 5, 50, 10)
    df_top = duracion.sort_values(
        by="duracion_proceso_horas",
        ascending=False
    ).head(n)
    titulo = "Duración Total del Proceso"

fig = px.bar(
    df_top,
    x="id_ticket",
    y="duracion_proceso_horas",
    title=titulo,
    labels={"id_ticket": "Ticket", "duracion_proceso_horas": "Horas"},
    color="duracion_proceso_horas",
    color_continuous_scale="Blues"
)

st.plotly_chart(fig, use_container_width=True)

# --- SANKEY ---
st.subheader("🔄 Flujo Real de Actividades (Sankey)")

log_filtrado = log if ticket_sel == "Todos" else log[log["id_ticket"] == ticket_sel]

log_ord = log_filtrado.sort_values(by=["id_ticket", "inicio_actividad"])
log_ord["actividad_siguiente"] = log_ord.groupby("id_ticket")["actividad"].shift(-1)

pares = log_ord.dropna(subset=["actividad_siguiente"])

flujo = pares.groupby(
    ["actividad", "actividad_siguiente"]
).agg(
    cantidad=('id_ticket', 'count'),
    duracion_promedio=('duracion_horas', 'mean')
).reset_index()

nodos = list(set(flujo["actividad"]) | set(flujo["actividad_siguiente"]))
idx = {n: i for i, n in enumerate(nodos)}

flujo["source"] = flujo["actividad"].map(idx)
flujo["target"] = flujo["actividad_siguiente"].map(idx)

colores = [f"hsl({random.randint(0,360)},70%,50%)" for _ in nodos]

fig_sankey = go.Figure(go.Sankey(
    node=dict(label=nodos, color=colores),
    link=dict(
        source=flujo["source"],
        target=flujo["target"],
        value=flujo["cantidad"]
    )
))

st.plotly_chart(fig_sankey, use_container_width=True)
