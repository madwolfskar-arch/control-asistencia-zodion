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

# --- Conexión con Google Sheets (Soporte multihoja: Asistencia y Empleados) ---
@st.cache_resource
def init_connection():
    try:
        secret_dict = dict(st.secrets["gcp_service_account"])
        
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
        spreadsheet = client.open(spreadsheet_name)
        
        sheet_asistencia = spreadsheet.worksheet("Asistencia")
        sheet_empleados = spreadsheet.worksheet("Empleados")
        
        return spreadsheet, sheet_asistencia, sheet_empleados
    except Exception as e:
        st.error(f"Error al conectar con Google Sheets. Verifica tus secretos o nombres de pestañas: {e}")
        return None, None, None

spreadsheet, sheet_asistencia, sheet_empleados = init_connection()

# --- Navegación Superior ---
menu = st.sidebar.selectbox("Menú de Navegación", [
    "Móvil: Registrar Marcación", 
    "Inscribir / Gestionar Empleados", 
    "Panel Administrativo (Admin)"
])

# ==========================================
# MÓDULO 1: REGISTRO DE ASISTENCIA (EMPLEADOS)
# ==========================================
if menu == "Móvil: Registrar Marcación":
    st.markdown("<h1>📲 Control de Asistencia</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #555;'>Selecciona tu perfil, tipo de evento y toma tu foto.</p>", unsafe_allow_html=True)
    
    empleados_lista = []
    df_emp = pd.DataFrame()
    if sheet_empleados:
        try:
            data_emp = sheet_empleados.get_all_records()
            if data_emp:
                df_emp = pd.DataFrame(data_emp)
        except Exception:
            pass

    if df_emp.empty or "ID" not in df_emp.columns:
        st.warning("⚠️ No hay empleados inscritos todavía. Por favor ve al menú 'Inscribir / Gestionar Empleados' para dar de alta al personal primero.")
    else:
        df_emp["Display"] = df_emp["Nombre"] + " (ID: " + df_emp["ID"].astype(str) + " - " + df_emp["Cargo"] + ")"
        seleccion_empleado = st.selectbox("Selecciona tu Trabajador *", options=df_emp["Display"].tolist())
        
        emp_seleccionado = df_emp[df_emp["Display"] == seleccion_empleado].iloc[0]
        emp_id = str(emp_seleccionado["ID"])
        emp_nombre = emp_seleccionado["Nombre"]
        emp_cargo = emp_seleccionado["Cargo"]

        st.info(f"👤 **Cargo actual:** {emp_cargo}")

        with st.form("form_marcacion"):
            tipo_marcacion = st.radio("Tipo de Marcación:", ["🟢 ENTRADA", "🔴 SALIDA"], horizontal=True)
            
            st.markdown("---")
            st.markdown("### 📸 Fotografía de Confirmación")
            st.info("Por favor, habilita tu cámara y toma una foto clara de tu llegada o salida.")
            
            foto_capturada = st.camera_input("Tomar Foto")
            
            submitted = st.form_submit_button("Registrar Marcación")
            
            if submitted:
                if not foto_capturada:
                    st.warning("⚠️ Es obligatorio tomar la fotografía para validar la marcación.")
                else:
                    try:
                        now = datetime.now()
                        fecha_str = now.strftime("%Y-%m-%d")
                        hora_str = now.strftime("%H:%M:%S")
                        timestamp_completo = now.strftime("%Y-%m-%d %H:%M:%S")
                        
                        img = Image.open(foto_capturada)
                        img.thumbnail((600, 600))
                        
                        if sheet_asistencia:
                            # Estructura con Cargo al final (Columna G)
                            fila_nueva = [emp_id, emp_nombre, tipo_marcacion, fecha_str, hora_str, timestamp_completo, emp_cargo]
                            sheet_asistencia.append_row(fila_nueva)
                            
                            st.markdown(f"""
                                <div class="success-box">
                                    ✅ ¡Marcación registrada con éxito!<br>
                                    Empleado: {emp_nombre} ({emp_cargo})<br>
                                    Evento: {tipo_marcacion}<br>
                                    Hora: {hora_str} ({fecha_str})
                                </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.error("No hay conexión activa con la hoja de Asistencia.")
                            
                    except Exception as e:
                        st.error(f"Ocurrió un error al procesar el registro: {e}")

# ==========================================
# MÓDULO 2: INSCRIPCIÓN / GESTIÓN DE EMPLEADOS
# ==========================================
elif menu == "Inscribir / Gestionar Empleados":
    st.markdown("<h1>👥 Registro de Personal</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #555;'>Inscribe aquí al personal para que aparezca automáticamente en el control móvil.</p>", unsafe_allow_html=True)
    
    with st.form("form_nuevo_empleado"):
        nuevo_id = st.text_input("Cédula / ID del Trabajador *").strip()
        nuevo_nombre = st.text_input("Nombre Completo *").strip()
        nuevo_cargo = st.text_input("Cargo o Rol (Ej. Biólogo, Operario, Consultor) *").strip()
        
        btn_guardar_emp = st.form_submit_button("Guardar / Inscribir Empleado")
        
        if btn_guardar_emp:
            if not nuevo_id or not nuevo_nombre or not nuevo_cargo:
                st.warning("⚠️ Todos los campos son obligatorios para la inscripción.")
            else:
                try:
                    if sheet_empleados:
                        existing_records = sheet_empleados.get_all_records()
                        ids_existentes = [str(r.get("ID")) for r in existing_records]
                        
                        if nuevo_id in ids_existentes:
                            st.error(f"⚠️ Ya existe un empleado registrado con la cédula {nuevo_id}.")
                        else:
                            sheet_empleados.append_row([nuevo_id, nuevo_nombre, nuevo_cargo])
                            st.success(f"🎉 ¡Empleado {nuevo_nombre} inscrito correctamente!")
                    else:
                        st.error("No hay conexión con la base de datos de empleados.")
                except Exception as e:
                    st.error(f"Error al registrar al empleado: {e}")

    st.markdown("---")
    st.markdown("### 📋 Personal Actualmente Inscrito")
    if sheet_empleados:
        try:
            data_emp = sheet_empleados.get_all_records()
            if data_emp:
                st.dataframe(pd.DataFrame(data_emp), use_container_width=True)
            else:
                st.info("Aún no hay personal registrado en el sistema.")
        except Exception as e:
            st.error(f"Error al cargar la lista de empleados: {e}")

# ==========================================
# MÓDULO 3: PANEL ADMINISTRATIVO
# ==========================================
elif menu == "Panel Administrativo (Admin)":
    st.markdown("<h1>🔒 Panel de Administración</h1>", unsafe_allow_html=True)
    
    admin_pin = st.text_input("Ingrese PIN de Administrador:", type="password")
    PIN_CORRECTO = "2026"
    
    if admin_pin == PIN_CORRECTO:
        st.success("Acceso concedido.")
        
        if sheet_asistencia:
            with st.spinner("Cargando registros de asistencia..."):
                try:
                    data = sheet_asistencia.get_all_records()
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
                        st.info("Aún no hay registros guardados en la hoja de asistencia.")
                except Exception as e:
                    st.error(f"Error al leer los datos: {e}")
        else:
            st.error("Google Sheets no está configurado correctamente.")
            
    elif admin_pin != "":
        st.error("PIN incorrecto. Intente nuevamente.")
        
