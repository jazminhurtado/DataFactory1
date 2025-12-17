import streamlit as st
import pandas as pd
import plotly.express as px

# Cargar datos
@st.cache_data
def cargar_datos():
    eventos = pd.read_csv('log_eventos_con_hora.csv', parse_dates=['inicio_actividad', 'fin_actividad'])
    eventos['duracion_horas'] = ((eventos['fin_actividad'] - eventos['inicio_actividad']).dt.total_seconds() / 3600).fillna(0).round(2)
    variantes = pd.read_csv('variantes_proceso_con_hora.csv')
    variantes.columns = variantes.columns.str.lower()
    if 'tickets' in variantes.columns:
        variantes['tickets'] = variantes['tickets'].fillna('')
    return eventos, variantes

# Cargar los datos
log_eventos, variantes = cargar_datos()

# Sidebar
st.sidebar.header("🏦 Filtros")
ticket_id = st.sidebar.selectbox("Ticket específico", options=["Todos"] + sorted(log_eventos['id_ticket'].unique().tolist()))

# KPIs Generales
st.markdown("## 🔹 KPIs Generales")
total_tickets = log_eventos['id_ticket'].nunique()
total_actividades = log_eventos['actividad'].nunique()
promedio_duracion = log_eventos.groupby('id_ticket')['duracion_horas'].sum().mean().round(2)
col1, col2, col3 = st.columns(3)
col1.metric("📅 Tickets únicos", total_tickets)
col2.metric("🌈 Actividades distintas", total_actividades)
col3.metric("⏱️ Promedio duración total (horas)", promedio_duracion)

# Log de Eventos
st.markdown("## 📄 Log de Eventos por Actividad")
if ticket_id != "Todos":
    df_log = log_eventos[log_eventos['id_ticket'] == ticket_id]
else:
    df_log = log_eventos
st.dataframe(df_log.sort_values(by=['id_ticket', 'inicio_actividad']), use_container_width=True)

# Variantes del Proceso
st.markdown("## 🔹 Variantes del Proceso")
top_n = st.slider("Mostrar top N variantes", 1, 20, 5)

# Si el ticket está seleccionado, identificar su secuencia
ticket_secuencia = ""
ticket_en_top = False
if ticket_id != "Todos":
    secuencia_ticket = log_eventos[log_eventos['id_ticket'] == ticket_id].sort_values('inicio_actividad')['actividad'].tolist()
    ticket_secuencia = " ➔ ".join(secuencia_ticket)
    if 'secuencia' in variantes.columns:
        variantes['es_ticket'] = variantes['secuencia'].apply(lambda x: 1 if x == ticket_secuencia else 0)
        ticket_en_top = ticket_secuencia in variantes['secuencia'].head(top_n).values

# Mostrar tabla de variantes
columnas_mostrar = ['secuencia', 'cantidad']
if 'tickets' in variantes.columns:
    columnas_mostrar.append('tickets')
if 'es_ticket' in variantes.columns:
    columnas_mostrar.append('es_ticket')

st.dataframe(variantes.head(top_n)[columnas_mostrar], use_container_width=True)
if ticket_id != "Todos" and not ticket_en_top:
    st.warning("⚠️ La secuencia de este ticket no está entre las top N variantes mostradas.")

# Duración por ticket
st.markdown("## ⏳ Duraciones reales por Ticket")
df_duracion = log_eventos.groupby('id_ticket')['duracion_horas'].sum().reset_index()
df_duracion.columns = ['id_ticket', 'duracion_total_horas']
st.dataframe(df_duracion.sort_values(by='duracion_total_horas', ascending=False), use_container_width=True)

# Gráfico de barras
fig = px.bar(df_duracion.sort_values(by='duracion_total_horas', ascending=False).head(10),
             x='id_ticket', y='duracion_total_horas',
             title='Top 10 Tickets por duración total (horas)',
             labels={'duracion_total_horas': 'Duración (h)', 'id_ticket': 'Ticket'})
st.plotly_chart(fig, use_container_width=True)
