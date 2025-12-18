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
st.title("📊 Análisis de Proceso de Tickets")
st.markdown("Visualización del flujo real de requerimientos según registros de eventos.")

# --- KPIs ---
st.subheader("🔢 KPIs Generales")
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
    st.dataframe(
        log[log['id_ticket'] == ticket_sel],
        use_container_width=True
    )

# --- DURACIONES ---
st.subheader("⏳ Duraciones reales por Ticket")
if ticket_sel != "Todos":
    st.dataframe(
        duracion[duracion['id_ticket'] == ticket_sel],
        use_container_width=True
    )
else:
    st.dataframe(duracion, use_container_width=True)

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
