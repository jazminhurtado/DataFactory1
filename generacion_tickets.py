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
    log = pd.read_csv("data/log_eventos_con_hora.csv", parse_dates=['inicio_actividad', 'fin_actividad'])
    variantes = pd.read_csv("data/variantes_proceso_con_hora.csv")
    duracion = pd.read_csv("data/duracion_real_por_ticket.csv")

    # Recalcular duracion_horas si es necesario
    log['duracion_horas'] = (log['fin_actividad'] - log['inicio_actividad']).dt.total_seconds() / 3600
    log['duracion_horas'] = log['duracion_horas'].round(2)

    return log, variantes, duracion

log, variantes, duracion = cargar_datos()

# --- PASO 1: Clasificar tickets por nivel de alerta ---
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

# --- KPIs GENERALES ---
st.subheader("📉 KPIs Generales")
total_tickets = log['id_ticket'].nunique()
total_actividades = log['actividad'].nunique()
prom_duracion_real = duracion["duracion_proceso_horas"].mean()

col1, col2, col3 = st.columns(3)
col1.metric("🎫 Tickets únicos", total_tickets)
col2.metric("⚙️ Actividades distintas", total_actividades)
col3.metric("⏱️ Promedio duración total (horas)", round(prom_duracion_real))

# --- FILTRO POR TICKET ---
st.sidebar.header("🎛️ Filtros")
ticket_sel = st.sidebar.selectbox("Ticket específico", ["Todos"] + sorted(log['id_ticket'].unique()))

# --- TABLA PRINCIPAL ---
st.subheader("📋 Log de Eventos por Actividad")
if ticket_sel != "Todos":
    log_filtrado = log[log['id_ticket'] == ticket_sel]
else:
    log_filtrado = log.copy()
st.dataframe(log_filtrado, use_container_width=True)

# --- VARIANTES DE PROCESO ---
st.subheader("🔁 Variantes del Proceso")
top_n = st.slider("Mostrar top N variantes", min_value=1, max_value=20, value=5)

# Identificar la secuencia seguida por el ticket seleccionado
secuencia_ticket = None
if ticket_sel != "Todos":
    actividades_ticket = log[log['id_ticket'] == ticket_sel].sort_values(by='inicio_actividad')['actividad']
    secuencia_ticket = ' ➔ '.join(actividades_ticket)

# Preparar dataframe de variantes
variantes['es_ticket'] = variantes['secuencia_actividades'].apply(lambda x: 1 if x == secuencia_ticket else 0)
variantes['tickets'] = variantes['tickets'].fillna('')

# Mostrar top N variantes
top_variantes = variantes.copy()
top_variantes['cantidad'] = top_variantes['tickets'].apply(lambda x: len(str(x).split(',')) if x else 0)
top_variantes = top_variantes.sort_values(by='cantidad', ascending=False).head(top_n)
top_variantes = top_variantes[['secuencia_actividades', 'cantidad', 'tickets', 'es_ticket']]
top_variantes.columns = ['secuencia', 'cantidad', 'tickets', 'es_ticket']
st.dataframe(top_variantes, use_container_width=True)

# Mensaje si el ticket seleccionado no está en las top N variantes
if ticket_sel != "Todos" and secuencia_ticket not in top_variantes['secuencia'].values:
    st.warning("⚠️ La secuencia de este ticket no está entre las top N variantes mostradas.")

# --- TABLA DE DURACIONES REALES ---
st.subheader("⏳ Duraciones reales por Ticket")
if ticket_sel != "Todos":
    duracion_filtrada = duracion[duracion['id_ticket'] == ticket_sel]
    st.dataframe(duracion_filtrada, use_container_width=True)
else:
    st.dataframe(duracion, use_container_width=True)

# --- GRAFICO: Duración por Ticket ---
st.subheader("📊 Duración Total del Proceso por Ticket")
if ticket_sel != "Todos":
    df_top_duracion = duracion[duracion['id_ticket'] == ticket_sel]
    titulo = f"Duración del Ticket: {ticket_sel}"
else:
    top_n_tickets = st.slider("Mostrar top N tickets con mayor duración", min_value=5, max_value=50, value=10)
    df_top_duracion = duracion.sort_values(by="duracion_proceso_horas", ascending=False).head(top_n_tickets)
    titulo = "Duración Total del Proceso por Ticket"

fig = px.bar(df_top_duracion, x="id_ticket", y="duracion_proceso_horas",
             labels={"id_ticket": "Ticket", "duracion_proceso_horas": "Duración (horas)"},
             title=titulo, color="duracion_proceso_horas", color_continuous_scale="Blues")
st.plotly_chart(fig, use_container_width=True)

# --- SEMÁFORO POR FASE ---
st.subheader("🚦 Semáforo por Fase del Proceso")
if ticket_sel != "Todos":
    df_semaforo_filtrado = duracion[duracion["id_ticket"] == ticket_sel]
    titulo_semaforo = f"Duración por Fase - Ticket {ticket_sel}"
else:
    df_semaforo_filtrado = duracion.copy()
    titulo_semaforo = "Duración por Fase del Proceso (Todos los Tickets)"

df_melted = df_semaforo_filtrado.melt(
    id_vars="id_ticket",
    value_vars=["duracion_fase_horas", "duracion_qa_horas", "duracion_post_resolucion_horas"],
    var_name="fase",
    value_name="duracion"
)
df_melted["color"] = pd.cut(df_melted["duracion"], bins=[-1, 500, 2000, float("inf")],
                              labels=["🟢 Bajo", "🟡 Medio", "🔴 Alto"])
fig2 = px.bar(df_melted, x="fase", y="duracion", color="color", barmode="group",
              color_discrete_map={"🟢 Bajo": "green", "🟡 Medio": "orange", "🔴 Alto": "red"},
              title=titulo_semaforo)
st.plotly_chart(fig2, use_container_width=True)

# --- GRAFICO SANKEY: Flujo Real de Actividades ---
st.subheader("🔄 Flujo Real de Actividades (Gráfico Sankey)")
if ticket_sel != "Todos":
    log_sankey = log[log["id_ticket"] == ticket_sel]
else:
    log_sankey = log.copy()
log_sankey = log_sankey.sort_values(by=["id_ticket", "inicio_actividad"])
log_sankey["actividad_siguiente"] = log_sankey.groupby("id_ticket")["actividad"].shift(-1)
pares = log_sankey.dropna(subset=["actividad_siguiente"])
flujo = pares.groupby(["actividad", "actividad_siguiente"]).agg(
    cantidad=('id_ticket', 'count'),
    duracion_promedio=('duracion_horas', 'mean')
).reset_index()

nodos = list(set(flujo["actividad"].tolist() + flujo["actividad_siguiente"].tolist()))
indices = {k: v for v, k in enumerate(nodos)}
flujo["source"] = flujo["actividad"].map(indices)
flujo["target"] = flujo["actividad_siguiente"].map(indices)
colores_nodos = ['hsl({},70%,50%)'.format(random.randint(0, 360)) for _ in nodos]
flujo["porcentaje"] = (flujo["cantidad"] / flujo["cantidad"].sum()) * 100
hover_textos = flujo.apply(
    lambda row: f"{row['actividad']} → {row['actividad_siguiente']}<br>Cantidad: {row['cantidad']}<br>Duración prom.: {row['duracion_promedio']:.2f} h<br>Participación: {row['porcentaje']:.1f}%",
    axis=1)

fig_sankey = go.Figure(data=[go.Sankey(
    node=dict(pad=15, thickness=20, line=dict(color="black", width=0.5), label=nodos, color=colores_nodos),
    link=dict(source=flujo["source"], target=flujo["target"], value=flujo["cantidad"], hovertemplate=hover_textos)
)])
st.plotly_chart(fig_sankey, use_container_width=True)
