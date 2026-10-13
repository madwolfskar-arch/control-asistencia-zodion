import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
from datetime import datetime
import textwrap

# Configuración de la página
st.set_page_config(page_title="Control de Asistencia - Zodion", page_icon="📲", layout="centered")

# ID de la carpeta principal compartida en Google Drive para las evidencias
CARPETA_RAIZ_ID = "1nx8rVRoA0r8SDOZP0zZdlh-D4Gnp8Acs"

# Inicializar el estado de la sesión para mantener el acceso abierto
if "admin_autenticado" not in st.session_state:
    st.session_state["admin_autenticado"] = False

# Función para conectar a Google Sheets y Google Drive con manejo seguro de credenciales
@st.cache_resource
def conectar_google():
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
        sheet_name = st.secrets["sheets"]["sheet_name"]
        sheet = client.open(sheet_name).sheet1
        
        drive_service = build('drive', 'v3', credentials=creds)
        
        return sheet, drive_service
    except Exception as e:
        st.error(f"Error de conexión con Google: {e}")
        return None, None

sheet, drive_service = conectar_google()

# Función para obtener o crear la subcarpeta del establecimiento
def obtener_o_crear_carpeta_drive(drive_svc, nombre_establecimiento, parent_id):
    try:
        query = f"mimeType='application/vnd.google-apps.folder' and name='{nombre_establecimiento}' and '{parent_id}' in parents and trashed=false"
        results = drive_svc.files().list(q=query, spaces='drive', fields="files(id, name)").execute()
        folders = results.get('files', [])
        
        if folders:
            return folders[0]['id']
        else:
            file_metadata = {
                'name': nombre_establecimiento,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_id]
            }
            folder = drive_svc.files().create(body=file_metadata, fields='id').execute()
            return folder.get('id')
    except Exception as e:
        st.error(f"Error gestionando carpeta en Drive: {e}")
        return None

# Interfaz de Usuario - Cabecera
st.title("📲 Control de Asistencia - Zodion")
st.markdown("Sistema de registro de control de personal y evidencias.")

# --- CONTROL DE SESIÓN POR PIN (SEGURIDAD DESDE SECRETS) ---
if not st.session_state["admin_autenticado"]:
    st.markdown("---")
    st.subheader("🔐 Acceso Administrativo")
    pin_ingresado = st.text_input("Ingrese el PIN de seguridad para iniciar sesión:", type="password")
    
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("Ingresar", type="primary"):
            # Leer de forma segura el PIN desde los Secrets
            pin_correcto = st.secrets["admin"]["pin"]
            if pin_ingresado == pin_correcto:
                st.session_state["admin_autenticado"] = True
                st.rerun()
            else:
                st.error("PIN incorrecto.")
    st.stop()

# Si ya está autenticado, muestra el panel lateral para cerrar sesión si se requiere
with st.sidebar:
    st.markdown("### Panel de Control")
    if st.button("Cerrar Sesión Administrador"):
        st.session_state["admin_autenticado"] = False
        st.rerun()

st.markdown("---")

# Opciones base de establecimientos
establecimientos_base = [
    "Seleccione...",
    "Establecimiento A - La Canasta",
    "Establecimiento B - La Espiga",
    "Establecimiento C - Javeriano",
    "Establecimiento D - El Vergel",
    "Establecimiento E - Prado Verde",
    "➕ Otro (Nuevo Establecimiento)"
]

selected_option = st.selectbox("Seleccione el Establecimiento / Empresa *", establecimientos_base)

establecimiento_final = ""
if selected_option == "➕ Otro (Nuevo Establecimiento)":
    nuevo_est = st.text_input("Escriba el nombre del nuevo establecimiento *")
    if nuevo_est:
        establecimiento_final = nuevo_est.strip()
elif selected_option != "Seleccione...":
    establecimiento_final = selected_option

cedula = st.text_input("Cédula / ID del Trabajador *")
nombre = st.text_input("Nombre Completo *")
cargo = st.text_input("Cargo o Rol (Ej. Operario, Mesero, Auxiliar) *")

tipo_evento = st.radio(
    "Tipo de Evento:",
    [
        "🟢 ENTRADA TURNO",
        "🟡 SALIDA A DESCANSO",
        "🔵 REGRESO DE DESCANSO",
        "🔴 SALIDA TURNO"
    ]
)

st.markdown("### 📸 Fotografía de Confirmación")
foto_capturada = st.camera_input("Tomar Foto de Evidencia")

if st.button("Registrar Asistencia", type="primary"):
    if not establecimiento_final or not cedula or not nombre or not cargo or not foto_capturada:
        st.warning("Por favor complete todos los campos obligatorios y tome la fotografía de evidencia.")
    elif not sheet or not drive_service:
        st.error("No hay conexión activa con Google Sheets o Drive. Verifique los Secrets.")
    else:
        with st.spinner("Subiendo evidencia y registrando asistencia..."):
            try:
                folder_id = obtener_o_crear_carpeta_drive(drive_service, establecimiento_final, CARPETA_RAIZ_ID)
                
                if folder_id:
                    timestamp_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                    file_name = f"{cedula}_{timestamp_str}.jpg"
                    
                    file_metadata = {
                        'name': file_name,
                        'parents': [folder_id]
                    }
                    
                    media = MediaIoBaseUpload(
                        io.BytesIO(foto_capturada.getvalue()),
                        mimetype='image/jpeg',
                        resumable=True
                    )
                    
                    file = drive_service.files().create(
                        body=file_metadata,
                        media_body=media,
                        fields='id, webViewLink'
                    ).execute()
                    
                    link_foto = file.get('webViewLink', '')
                    
                    fecha_actual = datetime.now().strftime("%Y-%m-%d")
                    hora_actual = datetime.now().strftime("%H:%M:%S")
                    timestamp_completo = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    fila = [
                        establecimiento_final,
                        cedula,
                        nombre,
                        cargo,
                        tipo_evento,
                        fecha_actual,
                        hora_actual,
                        timestamp_completo,
                        link_foto
                    ]
                    
                    sheet.append_row(fila)
                    st.success("¡Asistencia registrada y foto guardada con éxito en Google Drive!")
                    st.balloons()
                else:
                    st.error("No se pudo crear o acceder a la carpeta de destino en Google Drive.")
            except Exception as e:
                st.error(f"Error al procesar el registro: {e}")
                
