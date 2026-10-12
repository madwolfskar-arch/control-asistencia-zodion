import streamlit as st
import pandas as pd
from datetime import datetime
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
        st.error(f"Error al conectar con Google Sheets: {e}")
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
    st.markdown("<p style='text-align: center; color: #555;'>Ingresa tus datos, selecciona el evento y confirma con la fotografía.</p>", unsafe_allow_html=True)
    
    with st.form("form_marcacion"):
        col1, col2 = st.columns(2)
        with col1:
            emp_id = st.text_input("Cédula / ID del Trabajador *").strip()
        with col2:
            emp_nombre = st.text_input("Nombre Completo *").strip()
            
        emp_cargo = st.text_input("Cargo o Rol (Ej. Biólogo, Operario, Mesero) *").strip()
        
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
                    
                    if sheet:
                        # Estructura limpia de metadatos: [ID, Nombre, Cargo, Tipo, Fecha, Hora, Timestamp]
                        fila_nueva = [emp_id, emp_nombre, emp_cargo, tipo_marcacion, fecha_str, hora_str, timestamp_completo]
                        sheet.append_row(fila_nueva)
                        
                        st.markdown(f"""
                            <div class="success-box">
                                ✅ ¡Marcación registrada exitosamente!<br>
                                👤 <b>{emp_nombre}</b> ({emp_cargo})<br>
                                📌 <b>Evento:</b> {tipo_marcacion}<br>
                                🕒 <b>Hora:</b> {hora_str} | 📅 {fecha_str}
                            </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.error("No hay conexión activa con Google Sheets.")
                        
                except Exception as e:
                    st.error(f"Error al guardar la marcación: {e}")

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
                        
                        # Limpieza básica de nombres de columnas
                        df.columns = [c.strip() for c in df.columns]
                        
                        st.markdown("### 🧮 Cálculo Automático de Horas para Nómina")
                        
                        # Convertir columna Timestamp a formato fecha/hora real
                        df["Datetime"] = pd.to_datetime(df["Timestamp"], errors='coerce')
                        
                        # Filtro por rango de fechas
                        col_f1, col_f2 = st.columns(2)
                        with col_f1:
                            fecha_inicio = st.date_input("Fecha Inicio", value=pd.to_datetime("today").replace(day=1))
                        with col_f2:
                            fecha_fin = st.date_input("Fecha Fin", value=pd.to_datetime("today"))
                        
                        # Filtrar dataframe por rango seleccionado
                        mask = (df["Datetime"].dt.date >= fecha_inicio) & (df["Datetime"].dt.date <= fecha_fin)
                        df_periodo = df.loc[mask].copy()
                        
                        if not df_periodo.empty:
                            # Procesar horas por empleado y fecha
                            resumen_horas = []
                            
                            grouped = df_periodo.groupby(["ID", "Nombre", "Cargo", "Fecha"])
                            
                            for (emp_id, nombre, cargo, fecha), group in grouped:
                                # Ordenar marcaciones por hora
                                group = group.sort_values("Datetime")
                                
                                entrada_t = group[group["Tipo"].str.contains("ENTRADA TURNO", na=False)]
                                salida_t = group[group["Tipo"].str.contains("SALIDA TURNO", na=False)]
                                salida_d = group[group["Tipo"].str.contains("SALIDA A DESCANSO", na=False)]
                                regreso_d = group[group["Tipo"].str.contains("REGRESO DE DESCANSO", na=False)]
                                
                                hrs_brutas = 0.0
                                hrs_descanso = 0.0
                                
                                # Calcular tiempo bruto de turno (Entrada a Salida)
                                if not entrada_t.empty and not salida_t.empty:
                                    t_ent = entrada_t.iloc[0]["Datetime"]
                                    t_sal = salida_t.iloc[-1]["Datetime"]
                                    if t_sal > t_ent:
                                        hrs_brutas = (t_sal - t_ent).total_seconds() / 3600.0
                                
                                # Calcular tiempo de descanso registrado (Salida Descanso a Regreso)
                                if not salida_d.empty and not regreso_d.empty:
                                    t_sdesc = salida_d.iloc[0]["Datetime"]
                                    t_rdesc = regreso_d.iloc[-1]["Datetime"]
                                    if t_rdesc > t_sdesc:
                                        hrs_descanso = (t_rdesc - t_sdesc).total_seconds() / 3600.0
                                
                                hrs_netas = max(0.0, hrs_brutas - hrs_descanso)
                                
                                resumen_horas.append({
                                    "ID": emp_id,
                                    "Nombre": nombre,
                                    "Cargo": cargo,
                                    "Fecha": fecha,
                                    "Horas Brutas": round(hrs_brutas, 2),
                                    "Descanso (h)": round(hrs_descanso, 2),
                                    "Horas Netas": round(hrs_netas, 2)
                                })
                            
                            df_resumen_diario = pd.DataFrame(resumen_horas)
                            
                            # Consolidado total acumulado por trabajador en el periodo
                            consolidado_periodo = df_resumen_diario.groupby(["ID", "Nombre", "Cargo"]).agg(
                                Dias_Trabajados=("Fecha", "count"),
                                Total_Horas_Brutas=("Horas Brutas", "sum"),
                                Total_Horas_Descanso=("Descanso (h)", "sum"),
                                Total_Horas_Netas_Pagar=("Horas Netas", "sum")
                            ).reset_index()
                            
                            st.markdown("#### 📊 Consolidado de Nómina por Empleado")
                            st.dataframe(consolidado_periodo, use_container_width=True)
                            
                            st.markdown("#### 🗓️ Detalle Diario por Jornada")
                            st.dataframe(df_resumen_diario, use_container_width=True)
                            
                            # Botón de descarga de reporte
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
                        st.markdown("### 📋 Historial Completo de Metadatos (Crudo)")
                        st.dataframe(df, use_container_width=True)
                        
                    else:
                        st.info("Aún no hay registros en la base de datos.")
                except Exception as e:
                    st.error(f"Error al leer o procesar los datos: {e}")
        else:
            st.error("Google Sheets no está configurado correctamente.")
            
    elif admin_pin != "":
        st.error("PIN de administración incorrecto.")
        

