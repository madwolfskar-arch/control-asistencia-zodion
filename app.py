import streamlit as st
import pandas as pd
from datetime import datetime
from PIL import Image
import gspread
from google.oauth2.service_account import Credentials
import textwrap

# --- Configuración de la página ---
st.set_page_config(
    page_title="Control de Asistencia - Zodion",
    page_icon="⏱️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- Estilos CSS personalizados ---
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

# --- Conexión con Google Sheets (Única pestaña: Asistencia) ---
@st.cache_resource
def init_connection():
    try:
        secret_dict = dict(st.secrets["gcp_service_account"])
        
        # Saneamiento y reconstrucción matemática de la llave PEM
        if "private_key" in secret_dict:
            raw_key = secret_dict["private_key"]
            clean_base64 = raw_key.replace("-----BEGIN PRIVATE KEY-----", "").replace("-----END PRIVATE KEY-----", "")
            clean_base64 = "".join(clean_base64.split())
            wrapped_lines = textwrap.wrap(clean_base64, 64)
            formatted_pem = "-----BEGIN PRIVATE KEY-----\n" + "\n".join(wrapped_lines) + "\n-----END PRIVATE KEY-----\n"
            secret_dict["private_key"] = formatted_pem

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        creds = Credentials.from_service_account_info(secret_dict, scopes=scopes)
        client = gspread.authorize(creds)
        
        spreadsheet_name = st.secrets["sheets"]["sheet_name"]
        sheet = client.open(spreadsheet_name).worksheet("Asistencia")
        return sheet
    except Exception as e:
        st.error(f"Error al conectar con Google Sheets. Verifica tus secretos o nombre de pestaña: {e}")
        return None

sheet = init_connection()

# --- Navegación Superior ---
menu = st.sidebar.selectbox("Menú de Navegación", [
    "Móvil: Registrar Marcación", 
    "Panel Administrativo (Admin)"
])

# ==========================================
# MÓDULO 1: REGISTRO DE ASISTENCIA (MÓVIL)
# ==========================================
if menu == "Móvil: Registrar Marcación":
    st.markdown("<h1>📲 Control de Asistencia</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #555;'>Ingresa tus datos y toma tu foto para registrar tu marcación.</p>", unsafe_allow_html=True)
    
    with st.form("form_marcacion"):
        col1, col2 = st.columns(2)
        with col1:
            emp_id = st.text_input("Cédula / ID del Trabajador *").strip()
        with col2:
            emp_nombre = st.text_input("Nombre Completo *").strip()
            
        emp_cargo = st.text_input("Cargo o Rol (Ej. Biólogo, Operario, CEO) *").strip()
        
        tipo_marcacion = st.radio("Tipo de Marcación:", ["🟢 ENTRADA", "🔴 SALIDA"], horizontal=True)
        
        st.markdown("---")
        st.markdown("### 📸 Fotografía de Confirmación")
        st.info("Por favor, habilita tu cámara y toma una foto clara de tu llegada o salida.")
        
        foto_capturada = st.camera_input("Tomar Foto")
        
        submitted = st.form_submit_button("Registrar Marcación")
        
        if submitted:
            if not emp_id or not emp_nombre or not emp_cargo:
                st.warning("⚠️ Por favor completa tu ID, Nombre completo y Cargo.")
            elif not foto_capturada:
                st.warning("⚠️ Es obligatorio tomar la fotografía para validar la marcación.")
            else:
                try:
                    now = datetime.now()
                    fecha_str = now.strftime("%Y-%m-%d")
                    hora_str = now.strftime("%H:%M:%S")
                    timestamp_completo = now.strftime("%Y-%m-%d %H:%M:%S")
                    
                    img = Image.open(foto_capturada)
                    img.thumbnail((600, 600))
                    
                    if sheet:
                        # Estructura ordenada: [ID, Nombre, Cargo, Tipo, Fecha, Hora, Timestamp]
                        fila_nueva = [emp_id, emp_nombre, emp_cargo, tipo_marcacion, fecha_str, hora_str, timestamp_completo]
                        sheet.append_row(fila_nueva)
                        
                        st.markdown(f"""
                            <div class="success-box">
                                ✅ ¡Marcación registrada con éxito!<br>
                                Empleado: {emp_nombre} ({emp_cargo})<br>
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
    
    admin_pin = st.text_input("Ingrese PIN de Administrador:", type="password")
    PIN_CORRECTO = "2026"
    
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
                        st.markdown("### 🧮 Filtrar por Trabajador")
                        
                        trabajadores_unicos = df["Nombre"].unique() if "Nombre" in df.columns else []
                        selected_worker = st.selectbox("Seleccionar Empleado", ["Todos"] + list(trabajadores_unicos))
                        
                        if selected_worker != "Todos":
                            df_filtered = df[df["Nombre"] == selected_worker]
                        else:
                            df_filtered = df
                            
                        st.dataframe(df_filtered, use_container_width=True)
                        
                        csv_data = df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Descargar Reporte en formato CSV/Excel",
                            data=csv_data,
                            file_name=f"reporte_asistencia_zodion_{datetime.now().strftime('%Y-%m-%d')}.csv",
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
        

