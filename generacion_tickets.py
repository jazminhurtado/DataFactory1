import streamlit as st
import pandas as pd
import plotly.express as px

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Minería de Procesos", layout="wide")

# --- CARGA DE DATOS ---
st.cache_data.clear()  # Forzar limpieza de caché
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


# --- GRÁFICO DE BARRAS: Duración total del proceso por ticket ---


st.subheader("📊 Duración Total del Proceso por Ticket")

# Elegir cuántos tickets mostrar
top_n_tickets = st.slider("Mostrar top N tickets con mayor duración", min_value=5, max_value=50, value=10)

# Ordenar por duración descendente
df_top_duracion = duracion.sort_values(by="duracion_proceso_horas", ascending=False).head(top_n_tickets)

# Crear gráfico con Plotly
fig = px.bar(
    df_top_duracion,
    x="id_ticket",
    y="duracion_proceso_horas",
    labels={"id_ticket": "Ticket", "duracion_proceso_horas": "Duración (horas)"},
    title="Duración Total del Proceso por Ticket",
    color="duracion_proceso_horas",
    color_continuous_scale="Blues"
)

st.plotly_chart(fig, use_container_width=True)



st.subheader("📊 Comparativo por Fases del Proceso")

# Reordenar columnas para gráfica
df_fases = duracion[["id_ticket", "duracion_fase_horas", "duracion_qa_horas", "duracion_post_resolucion_horas"]]

# Convertir a formato largo para gráfico apilado
df_melt = df_fases.melt(id_vars="id_ticket", var_name="fase", value_name="horas")

# Crear gráfico apilado
fig_fases = px.bar(df_melt, x="id_ticket", y="horas", color="fase",
                   title="Duraciones por Fases del Proceso (Barras Apiladas)",
                   labels={"id_ticket": "Ticket", "horas": "Duración (hrs)", "fase": "Fase"},
                   color_discrete_sequence=px.colors.qualitative.Set3)

st.plotly_chart(fig_fases, use_container_width=True)



st.subheader("🚨 Tickets con posibles Cuellos de Botella")

# Cuello = si alguna fase dura más de 1500 horas
umbral_fase = 1500

cuellos = duracion[
    (duracion['duracion_fase_horas'] > umbral_fase) |
    (duracion['duracion_qa_horas'] > umbral_fase) |
    (duracion['duracion_post_resolucion_horas'] > umbral_fase)
]

st.dataframe(cuellos, use_container_width=True)




st.dataframe(cuellos, use_container_width=True)


st.subheader("🚦 Tickets con Código de Color (Semáforo)")

def color_semáforo(valor):
    if valor < 2000:
        return 'background-color: #D4EDDA'  # verde claro
    elif valor < 3500:
        return 'background-color: #FFF3CD'  # amarillo
    else:
        return 'background-color: #F8D7DA'  # rojo claro

styled = duracion.style.applymap(color_semáforo, subset=['duracion_proceso_horas'])
st.dataframe(styled, use_container_width=True)
             

