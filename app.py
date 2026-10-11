# --- Conexión con Google Sheets usando los Secretos de Streamlit (Método Moderno y Robusto) ---
@st.cache_resource
def init_connection():
    try:
        # Lee las credenciales desde los secretos seguros de Streamlit Cloud
        secret_dict = dict(st.secrets["gcp_service_account"])
        
        # Limpieza robusta de la llave privada para evitar errores de formato PEM o saltos de línea
        if "private_key" in secret_dict:
            pk = secret_dict["private_key"]
            pk = pk.replace("\\n", "\n").replace("\r\n", "\n").strip()
            # Asegurar que tenga las marcas correctas si por alguna razón faltaran
            if not pk.startswith("-----BEGIN PRIVATE KEY-----"):
                pk = "-----BEGIN PRIVATE KEY-----\n" + pk
            if not pk.endswith("-----END PRIVATE KEY-----"):
                pk = pk + "\n-----END PRIVATE KEY-----"
            secret_dict["private_key"] = pk

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        creds = Credentials.from_service_account_info(secret_dict, scopes=scopes)
        client = gspread.authorize(creds)
        
        # Abre la hoja de cálculo por su nombre exacto en Google Drive
        sheet_name = st.secrets["sheets"]["sheet_name"]
        sheet = client.open(sheet_name).sheet1
        return sheet
    except Exception as e:
        st.error(f"Error al conectar con Google Sheets. Verifica tus secretos en Streamlit: {e}")
        return None
