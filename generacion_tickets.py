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
    return log, variantes, duracion

log, variantes, duracion = cargar_datos()

# --- ASEGURAMOS COLUMNAS ESPERADAS ---
if 'tickets' not in variantes.columns:
    variantes['tickets'] = ''

# --- CÁLCULO DE DURACIÓN HORAS SI NO EXISTE ---
if 'duracion_horas' not in log.columns:
    log['duracion_horas'] = (log['fin_actividad'] - log['inicio_actividad']).dt.total_seconds() / 3600
    log['duracion_horas'] = log['duracion_horas'].round(2)

# --- CLASIFICACIÓN NIVEL ALERTA ---
def clasificar_ticket(d):
    if d <= 1500:
        return "✅ OK"
    elif d <= 3000:
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
col3.metric("⏱️ Promedio duración total (horas)", round(duracion["duracion_proceso_horas"].mean()))

# --- FILTRO DE TICKETS ---
st.sidebar.header("🎛️ Filtros")
ticket_sel = st.sidebar.selectbox("Ticket específico", ["Todos"] + sorted(log['id_ticket'].unique()))

# --- TABLA LOG ---
st.subheader("📋 Log de Eventos por Actividad")
if ticket_sel != "Todos":
    st.dataframe(log[log['id_ticket'] == ticket_sel], use_container_width=True)
else:
    st.dataframe(log, use_container_width=True)

# --- VARIANTES DE PROCESO ---
st.subheader("📆 Variantes del Proceso")
top_n = st.slider("Mostrar top N variantes", 1, 20, 5)

# Generamos secuencia de actividades por ticket
ticket_secuencias = log.sort_values(by=['id_ticket', 'inicio_actividad']).groupby('id_ticket')['actividad'].apply(lambda x: ' ➔ '.join(x)).reset_index()
ticket_secuencias.columns = ['id_ticket', 'secuencia']

# Conteo de variantes
conteo = ticket_secuencias['secuencia'].value_counts().reset_index()
conteo.columns = ['secuencia', 'cantidad']

# Mapeamos secuencia con sus tickets
conteo['tickets'] = conteo['secuencia'].apply(lambda s: ', '.join(ticket_secuencias[ticket_secuencias['secuencia'] == s]['id_ticket'].values))
conteo['es_ticket'] = conteo['tickets'].apply(lambda t: 1 if ticket_sel in t else 0 if ticket_sel != "Todos" else '')

# Alerta si no está el ticket
if ticket_sel != "Todos" and ticket_sel not in conteo['tickets'].str.split(', ').sum():
    st.warning("⚠️ La secuencia de este ticket no está entre las top N variantes mostradas.")

# Mostrar solo top N
st.dataframe(conteo.head(top_n), use_container_width=True)

# --- DURACIONES REALES POR TICKET ---
st.subheader("⏳ Duraciones reales por Ticket")
if ticket_sel != "Todos":
    st.dataframe(duracion[duracion['id_ticket'] == ticket_sel], use_container_width=True)
else:
    st.dataframe(duracion, use_container_width=True)

# --- BARRAS DE DURACIÓN ---
st.subheader("📊 Duración Total del Proceso por Ticket")
if ticket_sel != "Todos":
    df_duracion = duracion[duracion['id_ticket'] == ticket_sel]
else:
    top_n_tickets = st.slider("Top N tickets con mayor duración", 5, 50, 10)
    df_duracion = duracion.sort_values(by="duracion_proceso_horas", ascending=False).head(top_n_tickets)

fig = px.bar(
    df_duracion,
    x="id_ticket", y="duracion_proceso_horas",
    color="duracion_proceso_horas",
    title="Duración Total del Proceso",
    labels={"id_ticket": "Ticket", "duracion_proceso_horas": "Horas"},
    color_continuous_scale="Blues"
)
st.plotly_chart(fig, use_container_width=True)

# --- SEMÁFORO POR FASE ---
st.subheader("🚦 Semáforo por Fase del Proceso")
df_fase = duracion if ticket_sel == "Todos" else duracion[duracion['id_ticket'] == ticket_sel]
df_melt = df_fase.melt(id_vars='id_ticket',
                       value_vars=['duracion_fase_horas','duracion_qa_horas','duracion_post_resolucion_horas'],
                       var_name='fase', value_name='duracion')

# Colores por rango
bins = [-1, 500, 2000, float('inf')]
labels = ['🟢 Bajo', '🟡 Medio', '🔴 Alto']
df_melt['color'] = pd.cut(df_melt['duracion'], bins=bins, labels=labels)

fig2 = px.bar(df_melt, x='fase', y='duracion', color='color',
              color_discrete_map={'🟢 Bajo':'green','🟡 Medio':'orange','🔴 Alto':'red'},
              title="Duración por Fase")
st.plotly_chart(fig2, use_container_width=True)

# --- GRAFICO SANKEY ---
st.subheader("🔄 Flujo Real de Actividades (Sankey)")
log_sankey = log if ticket_sel == "Todos" else log[log['id_ticket'] == ticket_sel]
log_sankey = log_sankey.sort_values(by=['id_ticket','inicio_actividad'])
log_sankey['actividad_siguiente'] = log_sankey.groupby('id_ticket')['actividad'].shift(-1)
transiciones = log_sankey.dropna(subset=['actividad_siguiente'])

flujo = transiciones.groupby(['actividad','actividad_siguiente']).agg(
    cantidad=('id_ticket','count'),
    duracion_promedio=('duracion_horas','mean')
).reset_index()

nodos = list(set(flujo['actividad'].tolist() + flujo['actividad_siguiente'].tolist()))
indice = {k: i for i, k in enumerate(nodos)}
flujo['source'] = flujo['actividad'].map(indice)
flujo['target'] = flujo['actividad_siguiente'].map(indice)
flujo['porcentaje'] = (flujo['cantidad'] / flujo['cantidad'].sum()) * 100

hover = flujo.apply(lambda row: f"{row['actividad']} → {row['actividad_siguiente']}<br>Cantidad: {row['cantidad']}<br>Duración prom.: {row['duracion_promedio']:.2f} h<br>Participación: {row['porcentaje']:.1f}%", axis=1)

fig_sankey = go.Figure(data=[go.Sankey(
    node=dict(
        pad=15,
        thickness=20,
        line=dict(color="black", width=0.5),
        label=nodos,
        color=['hsl({},70%,50%)'.format(random.randint(0,360)) for _ in nodos]
    ),
    link=dict(
        source=flujo['source'],
        target=flujo['target'],
        value=flujo['cantidad'],
        hovertemplate=hover
    )
)])

st.plotly_chart(fig_sankey, use_container_width=True)
