import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
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

# --- Conexión con Google Sheets y Google Drive ---
@st.cache_resource
def init_connections():
    try:
        secret_dict = dict(st.secrets["gcp_service_account"])
        
        # Saneamiento y reconstrucción de la llave PEM
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
        
        # Servicio de Google Drive para gestionar carpetas e imágenes
        drive_service = build('drive', 'v3', credentials=creds)
        
        return sheet, drive_service
    except Exception as e:
        st.error(f"Error al conectar con Google Services: {e}")
        return None, None

sheet, drive_service = init_connections()

# --- Función para obtener o crear la carpeta del establecimiento en Drive ---
def obtener_o_crear_carpeta_drive(drive_svc, nombre_establecimiento):
    try:
        # Buscar si la carpeta ya existe
        query = f"mimeType='application/vnd.google-apps.folder' and name='{nombre_establecimiento}' and trashed=false"
        results = drive_svc.files().list(q=query, spaces='drive', fields="files(id, name)").execute()
        folders = results.get('files', [])
        
        if folders:
            return folders[0]['id']
        else:
            # Si no existe, crear la carpeta automáticamente
            file_metadata = {
                'name': nombre_establecimiento,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = drive_svc.files().create(body=file_metadata, fields='id').execute()
            return folder.get('id')
    except Exception as e:
        st.error(f"Error gestionando carpeta en Drive: {e}")
        return None

# --- Función para subir la foto a una carpeta específica de Drive ---
def subir_foto_a_drive(drive_svc, folder_id, archivo_foto, nombre_archivo):
    try:
        file_metadata = {
            'name': nombre_archivo,
            'parents': [folder_id]
        }
        
        # Leer los bytes de la foto capturada por Streamlit
        bytes_foto = archivo_foto.getvalue()
        media = MediaIoBaseUpload(io.BytesIO(bytes_foto), mimetype='image/jpeg', resumable=True)
        
        file = drive_svc.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()
        
        return file.get('webViewLink')
    except Exception as e:
        st.error(f"Error subiendo la foto a Drive: {e}")
        return ""

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
    st.markdown("<p style='text-align: center; color: #555;'>Selecciona tu establecimiento, ingresa tus datos, evento y confirma con la foto.</p>", unsafe_allow_html=True)
    
    with st.form("form_marcacion"):
        # Selección de establecimiento (5 iniciales + opción personalizada)
        lista_establecimientos = [
            "Establecimiento A - Restaurante Central",
            "Establecimiento B - Cafetería Norte",
            "Establecimiento C - Bodega Logística Sur",
            "Establecimiento D - Sucursal Comercial",
            "Establecimiento E - Planta Procesadora",
            "Otro (Escribir nombre personalizado)"
        ]
        
        seleccion_est = st.selectbox("Seleccione el Establecimiento / Empresa *", lista_establecimientos)
        
        if seleccion_est == "Otro (Escribir nombre personalizado)":
            est_personalizado = st.text_input("Escriba el nombre del nuevo establecimiento *").strip()
            establecimiento_final = est_personalizado
        else:
            establecimiento_final = seleccion_est
            
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            emp_id = st.text_input("Cédula / ID del Trabajador *").strip()
        with col2:
            emp_nombre = st.text_input("Nombre Completo *").strip()
            
        emp_cargo = st.text_input("Cargo o Rol (Ej. Operario, Mesero, Auxiliar) *").strip()
        
        tipo_marcacion = st.radio(
            "Tipo de Evento:", 
            [
                "🟢 ENTRADA TURNO", 
                "🟡 SALIDA A DESCANSO", 
                "🔵 REGRESO DE DESCANSO", 
                "🔴 SALIDA TURNO"
            ]
        )
        
        st.markdown("---")
        st.markdown("### 📸 Fotografía de Confirmación")
        foto_capturada = st.camera_input("Tomar Foto de Evidencia")
        
        submitted = st.form_submit_button("Registrar Marcación")
        
        if submitted:
            if not establecimiento_final:
                st.warning("⚠️ Por favor especifique el establecimiento.")
            elif not emp_id or not emp_nombre or not emp_cargo:
                st.warning("⚠️ Por favor completa tu ID, Nombre completo y Cargo.")
            elif not foto_capturada:
                st.warning("⚠️ Es obligatorio tomar la fotografía para validar la marcación.")
            else:
                try:
                    now = datetime.now()
                    fecha_str = now.strftime("%Y-%m-%d")
                    hora_str = now.strftime("%H:%M:%S")
                    timestamp_completo = now.strftime("%Y-%m-%d %H:%M:%S")
                    
                    if sheet and drive_service:
                        with st.spinner("Subiendo evidencia y registrando asistencia..."):
                            # 1. Obtener o crear carpeta independiente en Drive para este establecimiento
                            folder_id = obtener_o_crear_carpeta_drive(drive_service, establecimiento_final)
                            
                            # 2. Nombrar archivo de foto con metadatos estructurados
                            nombre_archivo_foto = f"{fecha_str}_{hora_str.replace(':','-')}_{emp_id}_{tipo_marcacion.split()[1]}.jpg"
                            
                            # 3. Subir foto a la carpeta de Drive y obtener el enlace
                            url_foto = subir_foto_a_drive(drive_service, folder_id, foto_capturada, nombre_archivo_foto)
                            
                            # 4. Guardar fila en Google Sheets (Incluyendo Establecimiento y Link de Foto)
                            # Estructura: [Establecimiento, ID, Nombre, Cargo, Tipo, Fecha, Hora, Timestamp, Link_Foto]
                            fila_nueva = [establecimiento_final, emp_id, emp_nombre, emp_cargo, tipo_marcacion, fecha_str, hora_str, timestamp_completo, url_foto]
                            sheet.append_row(fila_nueva)
                        
                        st.markdown(f"""
                            <div class="success-box">
                                ✅ ¡Marcación registrada exitosamente!<br>
                                🏢 <b>{establecimiento_final}</b><br>
                                👤 <b>{emp_nombre}</b> ({emp_cargo})<br>
                                📌 <b>Evento:</b> {tipo_marcacion}<br>
                                🕒 <b>Hora:</b> {hora_str} | 📅 {fecha_str}
                            </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.error("No hay conexión activa con Google Sheets o Google Drive.")
                        
                except Exception as e:
                    st.error(f"Error al procesar el registro: {e}")

# ==========================================
# MÓDULO 2: PANEL ADMINISTRATIVO Y CÁLCULO DE NÓMINA
# ==========================================
elif menu == "Panel Administrativo (Admin)":
    st.markdown("<h1>🔒 Panel de Administración y Nómina</h1>", unsafe_allow_html=True)
    
    admin_pin = st.text_input("Ingrese PIN de Administrador:", type="password")
    PIN_CORRECTO = "2026"
    
    if admin_pin == PIN_CORRECTO:
        st.success("Acceso autorizado.")
        
        if sheet:
            with st.spinner("Cargando registros desde Google Sheets..."):
                try:
                    data = sheet.get_all_records()
                    if data:
                        df = pd.DataFrame(data)
                        df.columns = [c.strip() for c in df.columns]
                        
                        st.markdown("### 🧮 Cálculo Automático de Horas para Nómina")
                        
                        # Filtro por establecimiento si existen datos
                        if "Establecimiento" in df.columns:
                            estab_unicos = ["Todos"] + list(df["Establecimiento"].unique())
                            filtro_estab = st.selectbox("Filtrar por Establecimiento:", estab_unicos)
                            if filtro_estab != "Todos":
                                df = df[df["Establecimiento"] == filtro_estab]
                        
                        df["Datetime"] = pd.to_datetime(df["Timestamp"], errors='coerce')
                        
                        col_f1, col_f2 = st.columns(2)
                        with col_f1:
                            fecha_inicio = st.date_input("Fecha Inicio", value=pd.to_datetime("today").replace(day=1))
                        with col_f2:
                            fecha_fin = st.date_input("Fecha Fin", value=pd.to_datetime("today"))
                        
                        mask = (df["Datetime"].dt.date >= fecha_inicio) & (df["Datetime"].dt.date <= fecha_fin)
                        df_periodo = df.loc[mask].copy()
                        
                        if not df_periodo.empty:
                            resumen_horas = []
                            
                            # Agrupar por Establecimiento, ID, Nombre, Cargo y Fecha
                            grouped = df_periodo.groupby(["Establecimiento", "ID", "Nombre", "Cargo", "Fecha"])
                            
                            for (estab, emp_id, nombre, cargo, fecha), group in grouped:
                                group = group.sort_values("Datetime")
                                
                                entrada_t = group[group["Tipo"].str.contains("ENTRADA TURNO", na=False)]
                                salida_t = group[group["Tipo"].str.contains("SALIDA TURNO", na=False)]
                                salida_d = group[group["Tipo"].str.contains("SALIDA A DESCANSO", na=False)]
                                regreso_d = group[group["Tipo"].str.contains("REGRESO DE DESCANSO", na=False)]
                                
                                hrs_brutas = 0.0
                                hrs_descanso = 0.0
                                
                                if not entrada_t.empty and not salida_t.empty:
                                    t_ent = entrada_t.iloc[0]["Datetime"]
                                    t_sal = salida_t.iloc[-1]["Datetime"]
                                    if t_sal > t_ent:
                                        hrs_brutas = (t_sal - t_ent).total_seconds() / 3600.0
                                
                                if not salida_d.empty and not regreso_d.empty:
                                    t_sdesc = salida_d.iloc[0]["Datetime"]
                                    t_rdesc = regreso_d.iloc[-1]["Datetime"]
                                    if t_rdesc > t_sdesc:
                                        hrs_descanso = (t_rdesc - t_sdesc).total_seconds() / 3600.0
                                
                                hrs_netas = max(0.0, hrs_brutas - hrs_descanso)
                                
                                resumen_horas.append({
                                    "Establecimiento": estab,
                                    "ID": emp_id,
                                    "Nombre": nombre,
                                    "Cargo": cargo,
                                    "Fecha": fecha,
                                    "Horas Brutas": round(hrs_brutas, 2),
                                    "Descanso (h)": round(hrs_descanso, 2),
                                    "Horas Netas": round(hrs_netas, 2)
                                })
                            
                            df_resumen_diario = pd.DataFrame(resumen_horas)
                            
                            consolidado_periodo = df_resumen_diario.groupby(["Establecimiento", "ID", "Nombre", "Cargo"]).agg(
                                Dias_Trabajados=("Fecha", "count"),
                                Total_Horas_Brutas=("Horas Brutas", "sum"),
                                Total_Horas_Descanso=("Descanso (h)", "sum"),
                                Total_Horas_Netas_Pagar=("Horas Netas", "sum")
                            ).reset_index()
                            
                            st.markdown("#### 📊 Consolidado de Nómina por Establecimiento y Empleado")
                            st.dataframe(consolidado_periodo, use_container_width=True)
                            
                            st.markdown("#### 🗓️ Detalle Diario por Jornada")
                            st.dataframe(df_resumen_diario, use_container_width=True)
                            
                            csv_nomina = consolidado_periodo.to_csv(index=False).encode('utf-8')
                            st.download_button(
                                label="📥 Descargar Consolidado de Nómina (CSV/Excel)",
                                data=csv_nomina,
                                file_name=f"reporte_nomina_{fecha_inicio}_al_{fecha_fin}.csv",
                                mime="text/csv"
                            )
                        else:
                            st.info("No existen registros en el rango de fechas seleccionado.")
                        
                        st.markdown("---")
                        st.markdown("### 📋 Historial Completo de Metadatos (Con Enlaces de Fotos en Drive)")
                        st.dataframe(df, use_container_width=True)
                        
                    else:
                        st.info("Aún no hay registros en la base de datos.")
                except Exception as e:
                    st.error(f"Error al leer o procesar los datos: {e}")
        else:
            st.error("Google Sheets o Google Drive no están configurados correctamente.")
            
    elif admin_pin != "":
        st.error("PIN de administración incorrecto.")
        


