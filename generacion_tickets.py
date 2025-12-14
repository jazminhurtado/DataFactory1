import streamlit as st
import pandas as pd

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Minería de Procesos", layout="wide")

# --- CARGA DE DATOS ---
@st.cache_data
def cargar_datos():
    log = pd.read_csv("data/log_eventos.csv", parse_dates=['inicio_actividad', 'fin_actividad'])
    variantes = pd.read_csv("data/variantes_proceso.csv")
    return log, variantes

log, variantes = cargar_datos()

# --- ENCABEZADO ---
st.title("📊 Análisis de Proceso de Tickets")
st.markdown("Visualización del flujo real de requerimientos según registros de eventos.")

# --- KPIs ---
st.subheader("🔢 KPIs Generales")
total_tickets = log['id_ticket'].nunique()
total_actividades = log['actividad'].nunique()
duracion_total = log.groupby('id_ticket')['duracion_horas'].sum().mean()

col1, col2, col3 = st.columns(3)
col1.metric("🎫 Tickets únicos", total_tickets)
col2.metric("⚙️ Actividades distintas", total_actividades)
col3.metric("⏱️ Promedio duración total (horas)", round(duracion_total, 2))

# --- TABLA PRINCIPAL ---
st.subheader("📋 Log de Eventos por Actividad")
st.dataframe(log, use_container_width=True)

# --- VARIANTES ---
st.subheader("🔁 Variantes del Proceso")
top_n = st.slider("Mostrar top N variantes", min_value=1, max_value=20, value=5)
top_variantes = variantes['secuencia_actividades'].value_counts().head(top_n).reset_index()
top_variantes.columns = ['secuencia', 'cantidad']
st.dataframe(top_variantes)

# --- FILTROS (Extra) ---
st.sidebar.header("🎛️ Filtros")
ticket_sel = st.sidebar.selectbox("Ticket específico", ["Todos"] + list(log['id_ticket'].unique()))
if ticket_sel != "Todos":
    st.subheader(f"🔎 Eventos del Ticket: {ticket_sel}")
    st.dataframe(log[log['id_ticket'] == ticket_sel])
