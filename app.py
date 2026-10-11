import streamlit as st
import pandas as pd
from datetime import datetime
from PIL import Image
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# --- Configuración de la página ---
st.set_page_config(
    page_title="Control de Asistencia - Zodion",
    page_icon="⏱️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- Estilos CSS personalizados para mejorar la vista en Celulares ---
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3em;
        font-weight: bold;
    }
    h1 {
        color: #1b4332;
        text-align: center;
        font-size: 1.8rem;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d8f3dc;
        color: #081c15;
        text-align: center;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# --- Conexión con Google Sheets usando los Secretos de Streamlit ---
@st.cache_resource
def init_connection():
    try:
        # Lee las credenciales desde los secretos seguros de Streamlit Cloud
        secret_dict = dict(st.secrets["gcp_service_account"])
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(secret_dict, scope)
        client = gspread.authorize(creds)
        
        # Abre la hoja de cálculo por su nombre exacto en Google Drive
        sheet_name = st.secrets["sheets"]["sheet_name"]
        sheet = client.open(sheet_name).sheet1
        return sheet
    except Exception as e:
        st.error(f"Error al conectar con Google Sheets. Verifica tus secretos en Streamlit: {e}")
        return None

sheet = init_connection()

# --- Navegación Superior ---
menu = st.sidebar.selectbox("Menú de Navegación", ["Móvil: Registrar Marcación", "Panel Administrativo (Admin)"])

# ==========================================
# MÓDULO 1: REGISTRO DE ASISTENCIA (EMPLEADOS)
# ==========================================
if menu == "Móvil: Registrar Marcación":
    st.markdown("<h1>📲 Control de Asistencia</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #555;'>Ingresa tus datos y toma tu foto para registrar tu marcación.</p>", unsafe_allow_html=True)
    
    with st.form("form_marcacion"):
        # Identificación del trabajador
        col1, col2 = st.columns(2)
        with col1:
            emp_id = st.text_input("Cédula / ID del Trabajador *").strip()
        with col2:
            emp_nombre = st.text_input("Nombre Completo *").strip()
            
        tipo_marcacion = st.radio("Tipo de Marcación:", ["🟢 ENTRADA", "🔴 SALIDA"], horizontal=True)
        
        st.markdown("---")
        st.markdown("### 📸 Fotografía de Confirmación")
        st.info("Por favor, habilita tu cámara y toma una foto clara de tu llegada o salida.")
        
        # Componente de cámara nativo para móviles
        foto_capturada = st.camera_input("Tomar Foto")
        
        submitted = st.form_submit_button("Registrar Marcación")
        
        if submitted:
            if not emp_id or not emp_nombre:
                st.warning("⚠️ Por favor completa tu ID y Nombre completo.")
            elif not foto_capturada:
                st.warning("⚠️ Es obligatorio tomar la fotografía para validar la marcación.")
            else:
                try:
                    # Fecha y hora exacta local (o ajustada)
                    now = datetime.now()
                    fecha_str = now.strftime("%Y-%m-%d")
                    hora_str = now.strftime("%H:%M:%S")
                    timestamp_completo = now.strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Optimización y compresión de imagen para evitar saturar memoria
                    img = Image.open(foto_capturada)
                    img.thumbnail((600, 600)) # Redimensiona manteniendo proporción
                    
                    # Registrar en Google Sheets
                    if sheet:
                        # Columnas: ID, Nombre, Tipo, Fecha, Hora, Timestamp
                        fila_nueva = [emp_id, emp_nombre, tipo_marcacion, fecha_str, hora_str, timestamp_completo]
                        sheet.append_row(fila_nueva)
                        
                        st.markdown(f"""
                            <div class="success-box">
                                ✅ ¡Marcación registrada con éxito!<br>
                                Empleado: {emp_nombre} ({emp_id})<br>
                                Evento: {tipo_marcacion}<br>
                                Hora: {hora_str} ({fecha_str})
                            </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.error("No hay conexión activa con la base de datos de Google Sheets.")
                        
                except Exception as e:
                    st.error(f"Ocurrió un error al procesar el registro: {e}")

# ==========================================
# MÓDULO 2: PANEL ADMINISTRATIVO
# ==========================================
elif menu == "Panel Administrativo (Admin)":
    st.markdown("<h1>🔒 Panel de Administración</h1>", unsafe_allow_html=True)
    
    # Sistema básico de seguridad por PIN
    admin_pin = st.text_input("Ingrese PIN de Administrador:", type="password")
    
    # Puedes definir tu PIN secreto directamente aquí o en secrets
    PIN_CORRECTO = "2026" # Cambia este PIN por seguridad
    
    if admin_pin == PIN_CORRECTO:
        st.success("Acceso concedido.")
        
        if sheet:
            with st.spinner("Cargando registros desde Google Sheets..."):
                try:
                    data = sheet.get_all_records()
                    if data:
                        df = pd.DataFrame(data)
                        
                        st.markdown("### 📊 Historial Completo de Marcaciones")
                        st.dataframe(df, use_container_width=True)
                        
                        st.markdown("---")
                        st.markdown("### 🧮 Resumen y Cálculo de Horas")
                        
                        # Filtro básico por ID o nombre si se desea
                        trabajadores_unicos = df["ID"].unique() if "ID" in df.columns else []
                        selected_worker = st.selectbox("Filtrar por ID de Trabajador", ["Todos"] + list(trabajadores_unicos))
                        
                        if selected_worker != "Todos":
                            df_filtered = df[df["ID"] == selected_worker]
                        else:
                            df_filtered = df
                            
                        st.dataframe(df_filtered, use_container_width=True)
                        
                        # Botón para descargar reporte localmente en Excel si lo requiere el admin
                        csv_data = df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Descargar Reporte en formato CSV/Excel",
                            data=csv_data,
                            file_name=f"reporte_asistencia_{datetime.now().strftime('%Y-%m-%d')}.csv",
                            mime="text/csv"
                        )
                        
                    else:
                        st.info("Aún no hay registros guardados en la hoja de cálculo.")
                except Exception as e:
                    st.error(f"Error al leer los datos de Google Sheets: {e}")
        else:
            st.error("Google Sheets no está configurado correctamente.")
            
    elif admin_pin != "":
        st.error("PIN incorrecto. Intente nuevamente.")
        


