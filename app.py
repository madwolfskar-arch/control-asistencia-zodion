import streamlit as st
import requests
import json
import base64

# Configuración de la página
st.set_page_config(page_title="Control de Asistencia - Zodion", page_icon="📲", layout="centered")

# URL de la Aplicación Web de Google Apps Script
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbyo42rKvU2fhYeBSMEe8xGujZk8umURYMT5yeERlBzEYjerlPiHQ2gXpd3AE6OIpc3d/exec"

if "admin_autenticado" not in st.session_state:
    st.session_state["admin_autenticado"] = False

st.title("📲 Control de Asistencia - Zodion")
st.markdown("Sistema de registro de control de personal y evidencias.")

# --- CONTROL DE SESIÓN POR PIN ---
if not st.session_state["admin_autenticado"]:
    st.markdown("---")
    st.subheader("🔐 Acceso Administrativo")
    pin_ingresado = st.text_input("Ingrese el PIN de seguridad para iniciar sesión:", type="password")
    
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("Ingresar", type="primary"):
            pin_correcto = st.secrets["admin"]["pin"]
            if pin_ingresado == pin_correcto:
                st.session_state["admin_autenticado"] = True
                st.rerun()
            else:
                st.error("PIN incorrecto.")
    st.stop()

with st.sidebar:
    st.markdown("### Panel de Control")
    if st.button("Cerrar Sesión Administrador"):
        st.session_state["admin_autenticado"] = False
        st.rerun()

st.markdown("---")

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
    else:
        with st.spinner("Subiendo evidencia y registrando asistencia..."):
            try:
                # Convertir la foto tomada por la cámara a formato Base64
                bytes_data = foto_capturada.getvalue()
                base64_image = base64.b64encode(bytes_data).decode('utf-8')
                data_uri = f"data:image/jpeg;base64,{base64_image}"

                # Preparar el cuerpo de la petición hacia Google Apps Script
                payload = {
                    "establecimiento": establecimiento_final,
                    "cedula": cedula,
                    "nombre": nombre,
                    "cargo": cargo,
                    "evento": tipo_evento,
                    "fileData": data_uri,
                    "fileName": f"evidencia_{cedula}.jpg"
                }

                # Enviar petición POST al endpoint de Apps Script
                response = requests.post(
                    WEB_APP_URL,
                    data=json.dumps(payload),
                    headers={"Content-Type": "text/plain;charset=utf-8"}
                )

                resultado = response.json()

                if resultado.get("status") == "success":
                    st.success("¡Asistencia registrada y foto guardada con éxito!")
                    st.balloons()
                else:
                    st.error(f"Error al procesar el registro: {resultado.get('message')}")

            except Exception as e:
                st.error(f"Error en la comunicación con el servidor: {e}")
                
