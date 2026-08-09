import json
import io
import pandas as pd
import streamlit as st 
import extra_streamlit_components as stx
import time
from streamlit.components.v1 import html  
from supabase import Client, create_client
from reglas import reglas_ruteo, MAPA_ORIGENES, PREGUNTAS_FRECUENTES

st.set_page_config(page_title="Monitor Logístico - Liliana García", layout="wide", initial_sidebar_state="expanded")

# ==========================================
# CONEXIÓN NATIVA A SUPABASE
# ==========================================
@st.cache_resource
def init_supabase():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception:
        return None

supabase = init_supabase()

def cargar_ruteos_bd():
    if supabase and st.session_state.get("usuario_auth"):
        try:
            user_id_actual = st.session_state.usuario_auth.id
            res = supabase.table("ruteos_guardados") \
                .select("*") \
                .eq("user_id", user_id_actual) \
                .order("created_at") \
                .execute()
            return res.data
        except Exception as e:
            return []
    return []

def guardar_nuevo_ruteo_bd(nombre, datos):
    if supabase and st.session_state.get("usuario_auth"):
        try:
            user_id_actual = st.session_state.usuario_auth.id
            res = supabase.table("ruteos_guardados").insert({
                "user_id": user_id_actual,
                "nombre": nombre,
                "datos": datos
            }).execute()
            return True, res.data
        except Exception as e:
            return False, str(e)
    return False, "Usuario no autenticado."

def guardar_ruteo_servidor(nombre, datos_json_str):
    if supabase and st.session_state.get("usuario_auth"):
        try:
            u_id = st.session_state.usuario_auth.id
            datos_obj = json.loads(datos_json_str)
            res = supabase.table("ruteos_guardados").insert({
                "user_id": u_id,
                "nombre": nombre,
                "datos": datos_obj
            }).execute()
            return True
        except Exception as e:
            print("Error al guardar:", e)
            return False
    return False

# ==============================================================================
# 🔑 LOGIN CON SUPABASE AUTH (BLOQUEO DE PANTALLA)
# ==============================================================================
cookie_manager = stx.CookieManager(key="cookie_manager_auth")

if "usuario_auth" not in st.session_state:
    st.session_state.usuario_auth = None

if "verificando_cookie" not in st.session_state:
    st.session_state.verificando_cookie = True

USUARIOS_LOGIN = {
    "johan": "johanmichael.velazquezrangel@mercadolibre.com.mx",
    "lili": "odiodespertar@gmail.com",
}

if st.session_state.usuario_auth is None:
    session_id_cookie = cookie_manager.get(cookie="sb_refresh_token")
    if session_id_cookie and supabase:
        try:
            res_refresh = supabase.auth.refresh_session(session_id_cookie)
            if res_refresh and res_refresh.session and res_refresh.user:
                st.session_state.usuario_auth = res_refresh.user
                st.session_state.supabase_session = res_refresh.session
                nuevo_refresh_token = res_refresh.session.refresh_token

                if nuevo_refresh_token:
                    cookie_manager.set("sb_refresh_token", nuevo_refresh_token, max_age=30 * 24 * 3600)

                usuario_email = res_refresh.user.email or ""
                usuario_encontrado = None
                for nombre_usuario, correo in USUARIOS_LOGIN.items():
                    if correo.lower() == usuario_email.lower():
                        usuario_encontrado = nombre_usuario
                        break

                if usuario_encontrado:
                    st.session_state["usuario_activo"] = usuario_encontrado
                else:
                    st.session_state["usuario_activo"] = usuario_email.split("@")[0].replace(".", "_")

                st.session_state.verificando_cookie = False
                st.rerun()
            else:
                st.session_state.verificando_cookie = False
        except Exception as e:
            st.session_state.verificando_cookie = False
    else:
        if st.session_state.verificando_cookie:
            time.sleep(0.5)
            st.session_state.verificando_cookie = False
            st.rerun()

if st.session_state.usuario_auth is None:
    st.markdown("🚚 MONITOR LOGÍSTICO", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("form_login"):
            st.subheader("🔑 Iniciar Sesión")
            usuario_input = st.text_input("Usuario:")
            password_input = st.text_input("Contraseña:", type="password")
            btn_login = st.form_submit_button("ENTRAR", use_container_width=True)

            if btn_login:
                usuario = usuario_input.strip().lower()
                if not usuario or not password_input:
                    st.error("⚠️ Ingrese usuario y contraseña.")
                elif usuario not in USUARIOS_LOGIN:
                    st.error("❌ Usuario no encontrado.")
                else:
                    try:
                        email_login = USUARIOS_LOGIN[usuario]
                        res = supabase.auth.sign_in_with_password({
                            "email": email_login,
                            "password": password_input.strip()
                        })
                        st.session_state.usuario_auth = res.user
                        st.session_state.supabase_session = res.session
                        st.session_state["usuario_activo"] = usuario

                        if res.session and res.session.refresh_token:
                            cookie_manager.set("sb_refresh_token", res.session.refresh_token, max_age=30 * 24 * 3600)

                        st.rerun()
                    except Exception:
                        st.error("❌ Usuario o contraseña incorrectos.")
    st.stop()

# ==============================================================================
# 👤 MOSTRAR USUARIO ACTIVO Y BOTÓN DE SALIDA
# ==============================================================================
st.sidebar.markdown(f"👤 **Usuario Conectado:** `{st.session_state['usuario_activo']}`")
if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
    try:
        supabase.auth.sign_out()
    except Exception:
        pass
    st.session_state.usuario_auth = None
    st.session_state.supabase_session = None
    st.rerun()

usuario_activo = st.session_state["usuario_activo"]
user_id_auth = st.session_state.usuario_auth.id

# ==========================================
# ESTADO Y CONTROL DEL MODO FLOTANTE
# ==========================================
if "flotar_activo" not in st.session_state:
    st.session_state.flotar_activo = False

def toggle_flotar():
    st.session_state.flotar_activo = not st.session_state.flotar_activo

if st.session_state.flotar_activo:
    st.markdown("""
        <style>
            div[data-testid="stHorizontalBlock"]:has(> div:has(h3)), 
            div.element-container:has(div.stMetric),
            div.element-container:has(text),
            div[data-testid="stHorizontalBlock"] button:not(:has(p:contains("FLOTAR"))),
            .row-widget.stButton:not(:has(button:contains("FLOTAR"))) {
                display: none !important;
            }

            table, div[data-testid="stTable"], .js-plotly-plot {
                max-height: 380px !important;
                overflow-y: auto !important;
                display: block !important;
            }
        </style>
    """, unsafe_allow_html=True)

# ==========================================
# CSS GENERAL Y ESTILOS DEL BOT FLOTANTE
# ==========================================
st.markdown("""
    <style>
    .block-container {padding: 0rem !important;}
    footer, #MainMenu {visibility: hidden;}
    header {visibility: visible !important;}
    body { background-color: #25282b; }
    .poligono-bloque {
        letter-spacing: -0.2px; 
        white-space: nowrap;    
        zoom: 0.95; 
    }
    #contenedor-padre { display: flex; flex-direction: column; }
    .delta { display: none !important; }
    #visor { padding-right: 210px !important; box-sizing: border-box; }
    table { table-layout: fixed; width: 100%; word-wrap: break-word; }

    /* ESTILO VENTANA FLOTANTE AMARILLA BOT */
    div[data-testid="stExpander"] {
        position: fixed !important;
        bottom: 15px !important;
        right: 15px !important;
        width: 550px !important;
        max-height: 100vh !important;
        z-index: 999999 !important;
        background-color: #fcf1b6 !important;
        border-radius: 12px !important;
        border: 4px solid #FFD700 !important;
        box-shadow: 0px 4px 20px rgba(0, 0, 0, 0.7) !important;
        overflow: hidden !important;
    }
    
    div[data-testid="stExpander"] summary,
    div[data-testid="stExpander"] summary p, 
    div[data-testid="stExpander"] summary span,
    div[data-testid="stExpander"] summary div,
    div[data-testid="stExpander"] summary svg {
        color: #1e1d1f !important;
        fill: #19191a !important;
        font-weight: 800 !important;
        font-size: 1.1rem !important;
    }

    div[data-testid="stExpander"] div[data-testid="stMarkdownContainer"] p {
        color: #19191a !important;
        font-weight: bold !important;
    }

    div[data-testid="stChatMessage"]:has(div[aria-label="user"]),
    div[data-testid="stChatMessage"]:has([data-testid*="User"]) {
        background-color: #FFD700 !important;
        border-radius: 10px !important;
        padding: 8px !important;
        margin: 6px 0 !important;
        box-shadow: 0px 2px 5px rgba(0,0,0,0.2) !important;
    }

    div[data-testid="stChatMessage"]:has(div[aria-label="user"]) *,
    div[data-testid="stChatMessage"]:has([data-testid*="User"]) * {
        color: #FFFFFF !important;
    }

    div[data-testid="stChatMessage"]:has(div[aria-label="assistant"]),
    div[data-testid="stChatMessage"]:has([data-testid*="Assistant"]) {
        color-scheme: light !important;
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border: 2px solid #FFD700 !important;
        border-radius: 10px !important;
        padding: 8px !important;
        margin: 6px 0 !important;
    }

    div[data-testid="stChatMessage"]:has(div[aria-label="assistant"]) *,
    div[data-testid="stChatMessage"]:has([data-testid*="Assistant"]) * {
        color-scheme: light !important;
        color: #000000 !important;
        font-weight: 600 !important;
        line-height: 1.8 !important; /* Interlineado amplio */
    }

    div[data-testid="stExpander"] div[data-testid="stVerticalBlock"] {
        max-height: 760px !important;
        overflow-y: auto !important;
        display: flex !important;
        flex-direction: column !important;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 🤖 BOT FLOTANTE RESTAURADO
# ==========================================
with st.expander("🤖 ¿INDICACIONES DE RUTEO? Te ayudo", expanded=False):

    st.markdown("""
    <style>
        div[data-testid="stExpander"] button {
            background-color: #f1f5f9 !important;
            color: #0f172a !important;
            border: 1px solid #cbd5e1 !important;
            font-weight: 600 !important;
        }
        div[data-testid="stExpander"] button:hover {
            background-color: #e2e8f0 !important;
            color: #0284c7 !important;
            border-color: #0284c7 !important;
        }
        div[data-testid="stExpander"] label p {
            color: #0f172a !important;
            font-weight: 600 !important;
        }
    </style>
    """, unsafe_allow_html=True)

    st.write("👉 Consulta un SVC para indicaciones 🔍")

    if "main_chat_messages" not in st.session_state:
        st.session_state.main_chat_messages = []
    if "esperando_subtipo_smx5" not in st.session_state:
        st.session_state.esperando_subtipo_smx5 = False
    if "flujo_resumen" not in st.session_state:
        st.session_state.flujo_resumen = False
    if "paso_resumen" not in st.session_state:
        st.session_state.paso_resumen = 0
    if "paso_historial" not in st.session_state:
        st.session_state.paso_historial = []
    if "data_resumen" not in st.session_state:
        st.session_state.data_resumen = {}

    with st.container(height=480):
        for idx, msg in enumerate(st.session_state.main_chat_messages):
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"], unsafe_allow_html=True)
                
                if st.session_state.flujo_resumen and idx == len(st.session_state.main_chat_messages) - 1:
                    paso = st.session_state.paso_resumen

                    if paso == 1:
                        st.write("👇 **¿Qué tipo de ciclo fue?:**")
                        col1, col2 = st.columns(2)
                        if col1.button("1️⃣ Uniciclo", key="btn_resumen_uniciclo", use_container_width=True):
                            st.session_state.data_resumen["ciclo"] = "Uniciclo"
                            st.session_state.paso_historial.append(1)
                            st.session_state.paso_resumen = 2
                            st.rerun()
                        if col2.button("2️⃣ Ciclo 1", key="btn_resumen_c1", use_container_width=True):
                            st.session_state.data_resumen["ciclo"] = "C1"
                            st.session_state.paso_historial.append(1)
                            st.session_state.paso_resumen = 2
                            st.rerun()

                    elif paso == 2:
                        st.write("👇 **Unidades dedicadas para nodos (selecciona la casilla):**")
                        u1 = st.checkbox("3.5 tons", key="chk_35")
                        u2 = st.checkbox("Delivery Cell", key="chk_del")
                        
                        unidades_elegidas = []
                        if u1: unidades_elegidas.append("3.5 tons")
                        if u2: unidades_elegidas.append("Delivery Cell")
                        
                        st.write("¿Logis tomó todas?")
                        col_s, col_n = st.columns(2)
                        if col_s.button("1️⃣ Sí", use_container_width=True):
                            st.session_state.data_resumen["unidades_centro"] = unidades_elegidas
                            st.session_state.data_resumen["logis_tomo_todas"] = True
                            st.session_state.paso_historial.append(2)
                            st.session_state.paso_resumen = 2.5
                            st.rerun()
                        if col_n.button("2️⃣ No", use_container_width=True):
                            st.session_state.data_resumen["unidades_centro"] = unidades_elegidas
                            st.session_state.data_resumen["logis_tomo_todas"] = False
                            st.session_state.paso_historial.append(2)
                            st.session_state.paso_resumen = 2.2
                            st.rerun()

                    elif paso == 2.2:
                        st.write("👇 **¿Cuál o cuáles unidades dejó fuera Logis?**")
                        unis_pre = st.session_state.data_resumen.get("unidades_centro", [])
                        fuera_elegidas = []
                        for i_idx, u in enumerate(unis_pre):
                            if st.checkbox(f"Dejó fuera: {u}", key=f"chk_fuera_{i_idx}"):
                                fuera_elegidas.append(u)
                        
                        if st.button("Continuar ➡️", use_container_width=True):
                            st.session_state.data_resumen["unidades_fuera"] = fuera_elegidas
                            st.session_state.paso_historial.append(2.2)
                            st.session_state.paso_resumen = 2.5
                            st.rerun()

                    elif paso == 2.5:
                        st.write("👇 **¿Hubo Bulk (H&B)?**")
                        c1, c2 = st.columns(2)
                        if c1.button("1️⃣ Sí", use_container_width=True):
                            st.session_state.data_resumen["hubo_bulk"] = True
                            st.session_state.paso_historial.append(2.5)
                            st.session_state.paso_resumen = 3
                            st.rerun()
                        if c2.button("2️⃣ No", use_container_width=True):
                            st.session_state.data_resumen["hubo_bulk"] = False
                            st.session_state.paso_historial.append(2.5)
                            st.session_state.paso_resumen = 3
                            st.rerun()

                    elif paso == 3:
                        st.write("👇 **¿Hubo dropeo de nodos?**")
                        c1, c2 = st.columns(2)
                        if c1.button("1️⃣ Sí", use_container_width=True):
                            st.session_state.data_resumen["dropeo_nodos"] = True
                            st.session_state.paso_historial.append(3)
                            st.session_state.paso_resumen = 3.5
                            st.rerun()
                        if c2.button("2️⃣ No", use_container_width=True):
                            st.session_state.data_resumen["dropeo_nodos"] = False
                            st.session_state.data_resumen["dropeo_restriccion"] = False
                            st.session_state.paso_historial.append(3)
                            st.session_state.paso_resumen = 4
                            st.rerun()

                    elif paso == 3.5:
                        st.write("👇 **¿En la contingencia hubo dropeo de IDs por restricción?**")
                        c1, c2 = st.columns(2)
                        if c1.button("1️⃣ Sí", use_container_width=True):
                            st.session_state.data_resumen["dropeo_restriccion"] = True
                            st.session_state.paso_historial.append(3.5)
                            st.session_state.paso_resumen = 4
                            st.rerun()
                        if c2.button("2️⃣ No", use_container_width=True):
                            st.session_state.data_resumen["dropeo_restriccion"] = False
                            st.session_state.paso_historial.append(3.5)
                            st.session_state.paso_resumen = 4
                            st.rerun()

                    elif paso == 4:
                        st.write("👇 **¿Se cargó Alchichica ND en AM0?**")
                        c1, c2 = st.columns(2)
                        if c1.button("1️⃣ Sí", use_container_width=True):
                            st.session_state.data_resumen["alchichica"] = True
                            st.session_state.paso_historial.append(4)
                            st.session_state.paso_resumen = 4.5
                            st.rerun()
                        if c2.button("2️⃣ No", use_container_width=True):
                            st.session_state.data_resumen["alchichica"] = False
                            st.session_state.paso_historial.append(4)
                            st.session_state.paso_resumen = 5
                            st.rerun()

                    elif paso == 4.5:
                        st.write("👇 **¿Fue con 2 Small Van MLP?**")
                        c1, c2 = st.columns(2)
                        if c1.button("1️⃣ Sí", use_container_width=True):
                            st.session_state.data_resumen["alchichica_2sv"] = True
                            st.session_state.paso_historial.append(4.5)
                            st.session_state.paso_resumen = 5
                            st.rerun()
                        if c2.button("2️⃣ No", use_container_width=True):
                            st.session_state.data_resumen["alchichica_2sv"] = False
                            st.session_state.paso_historial.append(4.5)
                            st.session_state.paso_resumen = 5
                            st.rerun()

                    elif paso == 5:
                        st.write("👇 **Día del ruteo:**")
                        dia_sel = st.selectbox("Selecciona:", ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"], index=4)
                        
                        if st.button("🚀 Generar Resumen", use_container_width=True):
                            d = st.session_state.data_resumen
                            ciclo_txt = d.get("ciclo", "C1")
                            unis = d.get("unidades_centro", [])
                            logis_tomo_todas = d.get("logis_tomo_todas", True)
                            unis_fuera = d.get("unidades_fuera", [])

                            if logis_tomo_todas or not unis_fuera:
                                texto_unidades = "👉 <b>Unidades 3.5 tons y Delivery Cell</b>: se asignaron al polígono de Centro, logis tomó ambas."
                            elif len(unis_fuera) == len(unis):
                                texto_unidades = "👉 <b>Unidades 3.5 tons y Delivery Cell</b>: se asignaron al polígono de Centro, logis dejó fuera ambas."
                            else:
                                fuera_str = " y ".join([", ".join(unis_fuera[:-1]), unis_fuera[-1]]) if len(unis_fuera) > 1 else unis_fuera[0]
                                texto_unidades = f"👉 <b>Unidades 3.5 tons y Delivery Cell</b>: se asignaron al polígono de Centro, logis dejó fuera la {fuera_str}."

                            if d.get("dropeo_nodos", False):
                                if d.get("dropeo_restriccion", False):
                                    texto_dropeo = "👉 <b>Hubo dropeo de nodo</b> y se cargó en contingencia (logis nos dejó fuera ids por zona de restricción)."
                                else:
                                    texto_dropeo = "👉 <b>Hubo dropeo de nodo</b> y se cargó en contingencia."
                            else:
                                texto_dropeo = "👉 No hubo dropeo de nodo."

                            if d.get("alchichica", False):
                                if d.get("alchichica_2sv", True):
                                    texto_alchichica = "🚛 Se cargó plan de <b>Alchichica ND</b> en AM0 con 2 unidades Small Van MLP."
                                else:
                                    texto_alchichica = "🚛 Se cargó plan de <b>Alchichica ND</b> en AM0."
                            else:
                                texto_alchichica = ""

                            texto_bulk = "📦 Se asignó H&B para el volumen Bulk." if d.get("hubo_bulk", False) else ""

                            lineas_html = [
                                f"**Queda publicado {ciclo_txt} team**:<br><br>",
                                '<span style="font-weight: normal;">',
                                "📌 Se trabajó con el volumen disponible al momento de iniciar el ruteo.<br>",
                                "📌 Se cargaron las Rentals como híbridas en Centro, pero el sistema no las consideró todas como híbridas.<br>",
                                f"{texto_unidades}<br>"
                            ]
                            if texto_bulk: lineas_html.append(f"{texto_bulk}<br>")
                            lineas_html.append(f"{texto_dropeo}<br>")
                            if texto_alchichica: lineas_html.append(f"{texto_alchichica}<br>")
                            lineas_html.append(f"📌 Se usaron los parámetros establecidos para C1 del día {dia_sel}.<br>")
                            lineas_html.append("📋 Comparto template final.")
                            lineas_html.append("</span><br><br>")
                            lineas_html.append("<b>**¡Excelente turno! 👋**</b>")

                            resumen_final = "".join(lineas_html)

                            st.session_state.flujo_resumen = False
                            st.session_state.paso_resumen = 0
                            st.session_state.paso_historial = []
                            st.session_state.main_chat_messages.append({"role": "assistant", "content": resumen_final})
                            st.rerun()

                    if len(st.session_state.paso_historial) > 0 and paso > 1:
                        st.markdown("---")
                        if st.button("↩️ Volver al paso anterior / Corregir", key="btn_atras_resumen"):
                            st.session_state.paso_resumen = st.session_state.paso_historial.pop()
                            st.rerun()

        if query_main := st.chat_input("✏️ Escribe tu consulta...", key="main_chat_input"):
            st.session_state.main_chat_messages.append({"role": "user", "content": query_main})
            query_lower = query_main.lower().strip()

            if "resumen" in query_lower or "cierre" in query_lower or "ciere" in query_lower:
                st.session_state.flujo_resumen = True
                st.session_state.paso_resumen = 1
                st.session_state.paso_historial = []
                st.session_state.data_resumen = {}
                st.session_state.main_chat_messages.append({
                    "role": "assistant", 
                    "content": "📋 **Generador de Cierre.** Responde seleccionando las opciones de abajo:"
                })
                st.rerun()

            else:
                partes_respuesta = []
                svc_mapa = None
                for key in MAPA_ORIGENES.keys():
                    if key in query_lower:
                        svc_mapa = key
                        break

                if svc_mapa:
                    info = MAPA_ORIGENES[svc_mapa]
                    origen_tag = f"<span style='background-color: #e2e8f0; color: #0f172a; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-family: monospace;'>{info['origen']}</span>"
                    
                    bloque_mapa = (
                        f"📍 **Origen y Validación para {svc_mapa.upper()}:**\n\n"
                        f"* 🗺️ **Región:** Región {info['region']}\n"
                        f"* 🏢 **Origen(es) On Way:** {origen_tag}\n"
                        f"* ✅ **Validación requerida:** {info['val']}"
                    )
                    partes_respuesta.append(bloque_mapa)

                    if "reglas" in info and info["reglas"]:
                        bloque_reglas = f"📋 **Indicaciones específicas:**\n\n{info['reglas']}"
                        partes_respuesta.append(bloque_reglas)

                coincidencias_faq = []
                if any(w in query_lower for w in ["large van sdd", "sdd"]):
                    coincidencias_faq.append(PREGUNTAS_FRECUENTES["large_van_sdd"])
                if "bulk" in query_lower:
                    if "sja1" in query_lower or "centro 1" in query_lower or "centro 2" in query_lower:
                        coincidencias_faq.append(PREGUNTAS_FRECUENTES["bulk_sja1"])
                    else:
                        coincidencias_faq.append(PREGUNTAS_FRECUENTES["bulk_general"])
                if "alchichica" in query_lower: 
                    coincidencias_faq.append(PREGUNTAS_FRECUENTES["alchichica"])
                if any(w in query_lower for w in ["xico", "tuzamapa"]):
                    coincidencias_faq.append(PREGUNTAS_FRECUENTES["tuzamapa_xico"])
                if "dropeo" in query_lower or "drop" in query_lower:
                    coincidencias_faq.append(PREGUNTAS_FRECUENTES["dropeo_nodos_sja1"])

                if coincidencias_faq:
                    partes_respuesta.append("\n\n---\n\n".join(coincidencias_faq))

                if partes_respuesta:
                    respuesta_main = "\n\n---\n\n".join(partes_respuesta)
                else:
                    respuesta_main = "⚠️ No encontré esa consulta. Puedes consultar por un SVC (ej. SJA1, SCP1, SMD1, SGD2, SMX5, Bulk, Alchichica) o escribir **resumen** para armar el cierre."

            st.session_state.main_chat_messages.append({"role": "assistant", "content": respuesta_main})
            st.rerun()

# --- DATOS BASE DE ASIGNACIÓN DE FLOTA ---
u_SDE = {"Moto Car - 3": [25, 30], "Moto Car Newbie": [25, 25], "Car - 5h": [25, 30], "Car - 5 Extendida": [25, 30], "Car - 3h": [25, 28]}
u_PREC = {"Car - 8h": [70, 75], "Small 9h Ext Car": [70, 75]}
u_PREC_SMX2 = {"Car - 8h": [70, 75], "Small 9h Ext Car": [70, 75], "Car Zona Extendida": [65, 65]}
u_C1 = {"Rental Large Van": [100, 100], "Large Van MLP": [100, 100], "Small Van MLP":[100, 100], "Delivery Cell Large Van": [1, 1], "Delivery Cell Small Van": [1, 1]}

u_C1_SJA1 = { 
    "Small Van MLP foráneo": [110, 120], "Large Van MLP foráneo": [110, 120], "Car MLP": [80, 100],
    "Extra Large Van MLP H&B": [70, 70], "Rental Electric Large Van": [150, 150], "Rental Large Van": [120, 120],
    "Rental Replacement": [120, 120], "Truck 3.5 tons MLP": [1, 1], "Delivery Cell Large Van": [1, 1],
    "Car 8h": [70, 70], "Car Newbie": [70, 70], "Car Zona Extendida": [70, 70], "Moto 3h": [30, 30],
    "Small Van 9h": [70, 70], "Small Van 9h Ext": [70, 70], "Small Van Newbie": [70, 70], "Media Milla SP": [1, 1]
}

NOMBRES_PLANES_PREC = ["CHALCO", "COYOACÁN", "IZTAPALAPA", "MILPA ALTA", "TLAHUAC", "TLALPAN NORTE", "TLALPAN SUR", "XOCHIMILCO"]
NOMBRES_PLANES_PREG = ["CHALCO", "CHIMAS", "IXTAPALUCA VALLE CHALCO", "IZTAPALAPA 1", "IZTAPALAPA 2", "LA PAZ", "PUEBLOS", "TEXCOCO"]
NOMBRES_PLANES_C1 = ["CALKINI", "CAMPECHE", "CANDELARIA", "CHAMPOTÓN", "ESCÁRCEGA", "ESCÁRCEGA EXT", "HOLPECHEN", "MAXCANUN", "SEYBAPLAYA", "PLAN 10", "PLAN 11"]
NOMBRES_PLANES_C1_SJA1 = ["ACTOPAN", "⚠️ CENTRO 1", "⚠️ CENTRO 2", "EJA1 SP", "MISANTLA", "NAOLINCO", "PEROTE", "TEZUITLAN", "TLALTETELA", "TRAPICHE", "TUZAMAPA", "XICO", "CONTINGENCIA NODO", "PLAN 14", "PLAN 15", "PLAN 16", "PLAN 17"]

u_C1_SCH1 = { "Car MLP": [110, 120], "Small Van MLP": [110, 120], "Large Van MLP": [110, 120] }
NOMBRES_PLANES_C1_SCH1 = ["AEROPUERTO", "CANTERA", "DELICIAS", "GRANJAS", "MEOQUI", "NORTE", "SUR", "CUAUHTEMOC", "PARRAL"]

u_C1_VACIA = { "Car MLP": [110, 120], "Small Van MLP": [110, 120] }
NOMBRES_PLANES_C1_VACIA = ["PLAN 1", "PLAN 2", "PLAN 3", "PLAN 4", "PLAN 5"]

u_C1_SMD1 = { "Car MLP": [110, 120], "Small Van MLP": [110, 120] }
NOMBRES_PLANES_C1_SMD1 = ["⚠️ CENTRO 1", "⚠️ CENTRO 2", "⚠️ KANASIN"]

def gen_master_rows(data_dict, table_id):
    rows = ""
    items = list(data_dict.items())
    total_items = len(items)

    for i in range(1, max(total_items, 3) + 1):
        if (i-1) < total_items:
            name, spr = items[i-1]
        else:
            name, spr = "", [0, 0]

        rows += f'''
        <tr class="master-row">
            <td contenteditable="true" class="edit-name" style="font-weight: bold; border: 0.2px solid #25282b;">{name}</td>
            <td contenteditable="true" class="edit-spr-min" style="text-align: center; border: 0.2px solid #25282b;">{spr[0]}</td>
            <td contenteditable="true" class="edit-spr-max" style="text-align: center; border: 0.2px solid #25282b;">{spr[1]}</td>
            <td contenteditable="true" class="f-stock" style="text-align: center; border: 0.2px solid #25282b;">0</td>
            <td class="f-ruteadas" style="text-align: center; border: 0.2px solid #25282b;">0</td>
            <td class="f-left" style="text-align:center; border:0.2px solid #25282b;">0</td>
        </tr>'''
    return rows

def gen_poligonos(data_target=None):
    return '<div class="poligono-bloque" style="padding:10px; background:#ededed; color:#25282b;">Polígonos cargados...</div>'

PERFILES = {}
perfil_actual = "LUNES"

# PREPARACIÓN DE DATOS JSON DE MAPA
datos_mapa_json = json.dumps(MAPA_ORIGENES)
datos_faq_json = json.dumps(PREGUNTAS_FRECUENTES)

app_html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: sans-serif; background: #25282b; color: white; padding: 14px; }}
        #btn-menu-lateral {{
            position: fixed; top: 0px; left: 5px; z-index: 9999999;
            width: 42px; height: 42px; border: 1px solid #444; border-radius: 6px;
            background: #25282b; color: white; font-size: 22px; font-weight: bold; cursor: pointer;
        }}
        #menu-lateral-ruteos {{
            position: fixed; top: 0; left: -420px; width: 400px; height: 100vh;
            background: #1e2022; z-index: 9999998; border-radius: 0 18px 18px 0;
            box-shadow: 8px 0 20px rgba(0, 0, 0, 0.65); transition: left 0.3s ease;
            padding: 20px 15px; box-sizing: border-box; color: white; overflow-y: auto;
        }}
        #menu-lateral-ruteos.abierto {{ left: 0; }}
        .opcion-menu-ruteos {{
            width: 100%; padding: 13px 15px; margin-bottom: 9px; border-radius: 7px;
            border: 1px solid #3b3f43; background: #292c30; color: #e4e6e8;
            font-size: 14px; font-weight: 600; text-align: left; cursor: pointer;
        }}
        .opcion-menu-ruteos:hover {{ background: #363a3f; border-color: #66CDAA; color: white; }}
    </style>
</head>
<body>

<button id="btn-menu-lateral" onclick="abrirCerrarMenuRuteos()">☰</button>

<div id="menu-lateral-ruteos">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
        <span style="font-size:15px; font-weight:bold; color:#66CDAA;">MENÚ PRINCIPAL</span>
        <button onclick="abrirCerrarMenuRuteos()" style="background:none; border:none; color:white; font-size:21px; cursor:pointer;">✕</button>
    </div>

    <button class="opcion-menu-ruteos" onclick="accionMenuRuteos('excel')">📊 &nbsp; VISTA EXCEL</button>
    <button class="opcion-menu-ruteos" onclick="accionMenuRuteos('nuevo')">➕ &nbsp; CREAR NUEVO RUTEO</button>
    <button class="opcion-menu-ruteos" onclick="accionMenuRuteos('gestionar')">🗑️ &nbsp; GESTIONAR / BORRAR RUTEOS</button>
    <button class="opcion-menu-ruteos" onclick="accionMenuRuteos('limpiar')">🧹 &nbsp; LIMPIAR PANTALLA</button>
</div>

<script>
    function abrirCerrarMenuRuteos() {{
        const menu = document.getElementById("menu-lateral-ruteos");
        const boton = document.getElementById("btn-menu-lateral");
        if (!menu || !boton) return;
        menu.classList.toggle("abierto");
        if (menu.classList.contains("abierto")) {{
            boton.style.display = "none";
        }} else {{
            boton.style.display = "block";
        }}
    }}

    function cerrarMenuRuteos() {{
        const menu = document.getElementById("menu-lateral-ruteos");
        if (!menu) return;
        menu.classList.remove("abierto");
    }}

    function toggleSubmenuRuteos() {{
        const submenu = document.getElementById("submenu-ruteos-lateral");
        if (!submenu) return;
        if (submenu.style.display === "block") {{
            submenu.style.display = "none";
        }} else {{
            cargarRuteosEnMenuLateral();
            submenu.style.display = "block";
        }}
    }}

    function cargarRuteosEnMenuLateral() {{
        const selector = document.getElementById("ciclo-selector");
        const submenu = document.getElementById("submenu-ruteos-lateral");
        if (!selector || !submenu) return;
        submenu.innerHTML = "";
        Array.from(selector.options).forEach(opcion => {{
            const boton = document.createElement("button");
            boton.type = "button";
            boton.className = "ruteo-submenu-item";
            boton.innerText = opcion.textContent;
            boton.setAttribute("data-valor", opcion.value);
            if (opcion.value === selector.value) {{
                boton.classList.add("activo");
            }}
            boton.onclick = function() {{
                seleccionarRuteoDesdeMenu(this.getAttribute("data-valor"));
            }};
            submenu.appendChild(boton);
        }});
    }}

    function seleccionarRuteoDesdeMenu(valor) {{
        const selector = document.getElementById("ciclo-selector");
        if (!selector) return;
        selector.value = valor;
        cambiarCiclo(valor);
        cargarRuteosEnMenuLateral();
    }}

    function accionMenuRuteos(accion) {{
        if (accion === 'excel') {{
            toggleExcelView();
        }} else if (accion === 'nuevo') {{
            abrirCreadorRuteo();
        }} else if (accion === 'gestionar') {{
            abrirGestorEliminacionMasiva();
        }} else if (accion === 'limpiar') {{
            limpiarPantallaCompleta();
        }}
    }}
</script>

</body>
</html>
"""

html(app_html, height=1000, scrolling=True)

# ==============================================================================
# MAPA OPERATIVO Y HORA
# ==============================================================================
ID_IMAGEN = "1M4GLEwFzhLrZjV-zmvGrdTQhC6IjwxOJ"
url_final = f"https://drive.google.com/thumbnail?id={ID_IMAGEN}&sz=w1000"

html_limpio = f"""
<style>
    body {{ background-color: #25282b; font-family: 'Segoe UI', Tahoma, sans-serif; margin: 0; }}
    .main-box {{ background: #25282b; padding: 10px; display: flex; flex-direction: column; align-items: center; }}
    .map-container {{
        background: #1e1e1e; border-radius: 12px; padding: 15px; 
        width: 100%; max-width: 900px; text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.3);
    }}
    .map-container img {{ max-width: 100%; height: auto; border-radius: 8px; border: 2px solid #444; }}
</style>

<div class="main-box">
    <div class="map-container">
        <h3 style="color: #1E90FF; margin-top: 0; margin-bottom: 15px;">🗺️ MAPA OPERATIVO</h3>
        <img src="{url_final}" alt="Mapa de regiones">
    </div>
</div>
"""

st.markdown("---")
html(html_limpio, height=850, scrolling=True)
