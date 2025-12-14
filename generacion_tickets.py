import streamlit as st
import pandas as pd

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

# --- CALCULAR DURACIÓN A PARTIR DE TIEMPOS (por si la necesitas) ---
log['duracion_horas'] = (log['fin_actividad'] - log['inicio_actividad']).dt.total_seconds() / 3600

# --- ENCABEZADO ---
st.title("📊 Análisis de Proceso de Tickets")
st.markdown("Visualización del flujo real de requerimientos según registros de eventos.")

# --- KPIs GENERALES ---
st.subheader("🔢 KPIs Generales")
total_tickets = log['id_ticket'].nunique()
total_actividades = log['actividad'].nunique()
prom_duracion_real = duracion["duracion_proceso_horas"].mean()

col1, col2, col3 = st.columns(3)
col1.metric("🎫 Tickets únicos", total_tickets)
col2.metric("⚙️ Actividades distintas", total_actividades)
col3.metric("⏱️ Promedio duración total (horas)", round(prom_duracion_real, 2))

# --- TABLA PRINCIPAL ---
st.subheader("📋 Log de Eventos por Actividad")
st.dataframe(log, use_container_width=True)

# --- VARIANTES DE PROCESO ---
st.subheader("🔁 Variantes del Proceso")
top_n = st.slider("Mostrar top N variantes", min_value=1, max_value=20, value=5)
top_variantes = variantes['secuencia_actividades'].value_counts().head(top_n).reset_index()
top_variantes.columns = ['secuencia', 'cantidad']
st.dataframe(top_variantes)

# --- FILTRO POR TICKET ---
st.sidebar.header("🎛️ Filtros")
ticket_sel = st.sidebar.selectbox("Ticket específico", ["Todos"] + list(log['id_ticket'].unique()))

if ticket_sel != "Todos":
    st.subheader(f"🔎 Eventos del Ticket: {ticket_sel}")
    st.dataframe(log[log['id_ticket'] == ticket_sel], use_container_width=True)

# --- TABLA DE DURACIONES REALES ---
st.subheader("⏳ Duraciones reales por Ticket")
st.dataframe(duracion, use_container_width=True)
