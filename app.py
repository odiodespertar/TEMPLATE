import json
import io
import pandas as pd
import streamlit as st 
import extra_streamlit_components as stx
import time
from streamlit.components.v1 import html  
from supabase import Client, create_client
from reglas import MAPA_ORIGENES, PREGUNTAS_FRECUENTES

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

token_auth = ""
if "supabase_session" in st.session_state and st.session_state.supabase_session:
    session_obj = st.session_state.supabase_session
    if hasattr(session_obj, "access_token"):
        token_auth = session_obj.access_token
    elif isinstance(session_obj, dict):
        token_auth = session_obj.get("access_token", "")

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

st.markdown("""
    <style>
    .block-container {padding: 0rem !important;}
    footer, #MainMenu {visibility: hidden;}
    header {visibility: visible !important;}
    body { background-color: #25282b; }
    .poligono-bloque { letter-spacing: -0.2px; white-space: nowrap; zoom: 0.95; }
    #contenedor-padre { display: flex; flex-direction: column; }
    .delta { display: none !important; }
    #visor { padding-right: 210px !important; box-sizing: border-box; }
    .tabla-flota-reducida { max-width: 80% !important; margin-left: 0 !important; margin-right: auto; }
    table { table-layout: fixed; width: 100%; word-wrap: break-word; }
    </style>
""", unsafe_allow_html=True)

# DATOS BASE
u_SDE = {"Moto Car - 3": [25, 30], "Moto Car Newbie": [25, 25], "Car - 5h": [25, 30], "Car - 5 Extendida": [25, 30], "Car - 3h": [25, 28]}
u_PREC = {"Car - 8h": [70, 75], "Small 9h Ext Car": [70, 75]}
NOMBRES_PLANES_PREC = ["CHALCO", "COYOACÁN", "IZTAPALAPA", "MILPA ALTA", "TLAHUAC", "TLALPAN NORTE", "TLALPAN SUR", "XOCHIMILCO"]

u_PREC_SMX2 = {"Car - 8h": [70, 75], "Small 9h Ext Car": [70, 75], "Car Zona Extendida": [65, 65]}
NOMBRES_PLANES_PREG = ["CHALCO", "CHIMAS", "IXTAPALUCA VALLE CHALCO", "IZTAPALAPA 1", "IZTAPALAPA 2", "LA PAZ", "PUEBLOS", "TEXCOCO"]

NOMBRES_PLANES_C1 = ["CALKINI", "CAMPECHE", "CANDELARIA", "CHAMPOTÓN", "ESCÁRCEGA", "ESCÁRCEGA EXT", "HOLPECHEN", "MAXCANUN", "SEYBAPLAYA", "PLAN 10", "PLAN 11"]
u_C1 = {"Rental Large Van": [100, 100], "Large Van MLP": [100, 100], "Small Van MLP":[100, 100], "Delivery Cell Large Van": [1, 1], "Delivery Cell Small Van": [1, 1]}

u_C1_SJA1 = { 
    "Small Van MLP foráneo": [110, 120], "Large Van MLP foráneo": [110, 120], "Car MLP": [80, 100],
    "Extra Large Van MLP H&B": [70, 70], "Rental Electric Large Van": [150, 150], "Rental Large Van": [120, 120],
    "Rental Replacement": [120, 120], "Truck 3.5 tons MLP": [1, 1], "Delivery Cell Large Van": [1, 1],
    "Car 8h": [70, 70], "Car Newbie": [70, 70], "Car Zona Extendida": [70, 70], "Moto 3h": [30, 30],
    "Small Van 9h": [70, 70], "Small Van 9h Ext": [70, 70], "Small Van Newbie": [70, 70], "Media Milla SP": [1, 1]
}
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

# 🟢 PREPARACIÓN LIMPIA DE DATOS JSON (SIN ERRORES)
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
            width: 45px; height: 42px; border: 1px solid #444; border-radius: 6px;
            background: #25282b; color: white; font-size: 22px; font-weight: bold; cursor: pointer;
        }}
        #menu-lateral-ruteos {{
            position: fixed; top: 0; left: -410px; width: 380px; height: 100vh;
            background: #1e2022; z-index: 9999998; border-radius: 0 18px 18px 0;
            box-shadow: 8px 0 20px rgba(0, 0, 0, 0.65); transition: left 0.3s ease;
            padding: 20px 15px; box-sizing: border-box; color: white; overflow-y: auto;
        }}
        #menu-lateral-ruteos.abierto {{ left: 0; }}
        .opcion-menu-ruteos {{
            width: 100%; padding: 12px 15px; margin-bottom: 8px; border-radius: 7px;
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
        <span style="font-size:16px; font-weight:bold; color:#66CDAA;">MENÚ PRINCIPAL</span>
        <button onclick="abrirCerrarMenuRuteos()" style="background:none; border:none; color:white; font-size:20px; cursor:pointer;">✕</button>
    </div>

    <button class="opcion-menu-ruteos" onclick="togglePanelBotLateral()">🤖 &nbsp; ASISTENTE DE RUTEO</button>

    <div id="panel-bot-lateral-contenido" style="display: none; margin-top: 10px; background: #17191b; border: 1px solid #34383d; border-radius: 12px; padding: 10px;">
        <div style="text-align: center; font-size: 24px;">🚚</div>
        <div style="text-align: center; font-size: 11px; font-weight: bold; color: #22c55e; margin-bottom: 8px;">● ROUTING ONLINE</div>
        
        <button onclick="enviarConsultaBotLateral('resumen')" style="width: 100%; cursor: pointer; background: #28a745; color: white; border: none; padding: 6px; border-radius: 6px; font-weight: bold; font-size: 12px; margin-bottom: 8px;">
            📋 Armar Resumen de Cierre
        </button>

        <div id="box-mensajes-bot" style="max-height: 480px; overflow-y: auto; display: flex; flex-direction: column; gap: 10px; font-size: 14px; padding: 6px;">
            <div style="background: #25282b; border-left: 3px solid #0284c7; padding: 8px; border-radius: 6px; color: #ffffff;">
                🤖 <b>Asistente de Ruteo:</b><br>Consulta por un SVC (ej. SJA1, SCP1, SMD1, SDD, Bulk, Alchichica) o presiona arriba para armar el cierre de turno.
            </div>
        </div>

        <div style="display: flex; gap: 6px; margin-top: 10px;">
            <input type="text" id="input-bot-lateral" placeholder="Escribe tu consulta..." onkeydown="if(event.key==='Enter') enviarConsultaBotLateral()" style="flex: 1; padding: 8px 10px; border-radius: 6px; border: 1px solid #444; background: #25282b; color: white; font-size: 14px;">
            <button onclick="enviarConsultaBotLateral()" style="cursor: pointer; background: #0284c7; color: white; border: none; padding: 8px 12px; border-radius: 6px; font-weight: bold; font-size: 14px;">🚀</button>
        </div>
    </div>
</div>

<script>
    var MAPA_ORIGENES = {datos_mapa_json};
    var PREGUNTAS_FRECUENTES = {datos_faq_json};

    var flujoResumen = false;
    var pasoResumen = 0;
    var dataResumen = {{}};

    function abrirCerrarMenuRuteos() {{
        var menu = document.getElementById("menu-lateral-ruteos");
        if (!menu) return;
        menu.classList.toggle("abierto");
    }}

    function togglePanelBotLateral() {{
        var panel = document.getElementById("panel-bot-lateral-contenido");
        if (!panel) return;
        panel.style.display = (panel.style.display === "none" || panel.style.display === "") ? "block" : "none";
    }}

    function enviarConsultaBotLateral(opcionDirecta) {{
        var input = document.getElementById("input-bot-lateral");
        var box = document.getElementById("box-mensajes-bot");
        if (!box) return;

        var consulta = opcionDirecta || (input ? input.value.trim() : "");
        if (!consulta) return;

        box.innerHTML += '<div style="background: #315c4f; border-right: 3px solid #38bdf8; padding: 8px; border-radius: 6px; color: #ffffff; text-align: right; margin-bottom: 6px;"><b>Tú:</b> ' + consulta + '</div>';
        if (input) input.value = "";

        var q = consulta.toLowerCase();
        var partesRespuesta = [];

        if (q.indexOf("resumen") !== -1 || q.indexOf("cierre") !== -1 || q.indexOf("ciere") !== -1 || flujoResumen) {{
            procesarFlujoResumen(q, box);
            box.scrollTop = box.scrollHeight;
            return;
        }}

        var svcMapa = null;
        Object.keys(MAPA_ORIGENES).forEach(function(key) {{
            if (q.indexOf(key.toLowerCase()) !== -1) svcMapa = key;
        }});

        if (svcMapa) {{
            var info = MAPA_ORIGENES[svcMapa];
            var origenTag = '<span style="background:#e2e8f0; color:#0f172a; padding:2px 6px; border-radius:4px; font-weight:bold; font-family:monospace;">' + info.origen + '</span>';
            
            var bloqueMapa = '📍 <b>Origen y Validación para ' + svcMapa.toUpperCase() + ':</b><br>' +
                             '• 🗺️ <b>Región:</b> Región ' + info.region + '<br>' +
                             '• 🏢 <b>Origen(es) On Way:</b> ' + origenTag + '<br>' +
                             '• ✅ <b>Validación requerida:</b> ' + info.val;
            
            partesRespuesta.push(bloqueMapa);

            if (info.reglas && info.reglas.length > 0) {{
                var textoHTML = info.reglas.replace(/\*\*(.*?)\*\*/g, '<b>$1</b>').replace(/\n/g, '<br>');
                partesRespuesta.push('📋 <b>Indicaciones específicas:</b><br><br>' + textoHTML);
            }}
        }}

        var coincidenciasFaq = [];
        if (q.indexOf("sdd") !== -1 || q.indexOf("large van sdd") !== -1) coincidenciasFaq.push(PREGUNTAS_FRECUENTES["large_van_sdd"]);
        if (q.indexOf("bulk") !== -1) {{
            if (q.indexOf("sja1") !== -1 || q.indexOf("centro 1") !== -1 || q.indexOf("centro 2") !== -1) coincidenciasFaq.push(PREGUNTAS_FRECUENTES["bulk_sja1"]);
            else coincidenciasFaq.push(PREGUNTAS_FRECUENTES["bulk_general"]);
        }}
        if (q.indexOf("alchichica") !== -1) coincidenciasFaq.push(PREGUNTAS_FRECUENTES["alchichica"]);
        if (q.indexOf("xico") !== -1 || q.indexOf("tuzamapa") !== -1) coincidenciasFaq.push(PREGUNTAS_FRECUENTES["tuzamapa_xico"]);
        if (q.indexOf("dropeo") !== -1 || q.indexOf("drop") !== -1) coincidenciasFaq.push(PREGUNTAS_FRECUENTES["dropeo_nodos_sja1"]);

        if (coincidenciasFaq.length > 0) {{
            partesRespuesta.push(coincidenciasFaq.join("<br><hr style='border:0; border-top:1px dashed #555;'><br>"));
        }}

        var respuestaFinal = "";
        if (partesRespuesta.length > 0) {{
            respuestaFinal = partesRespuesta.join("<br><hr style='border:0; border-top:1px dashed #555;'><br>");
        }} else {{
            respuestaFinal = "⚠️ No encontré esa consulta. Puedes consultar por un SVC (ej. SJA1, SCP1, SMD1, SGD2, SMX5, Bulk, Alchichica) o escribir **resumen** para armar el cierre.";
        }}

        setTimeout(function() {{
            box.innerHTML += '<div style="background: #25282b; border-left: 3px solid #0284c7; padding: 10px; border-radius: 6px; color: #ffffff; margin-bottom: 6px; font-size:13px; line-height: 1.4;">🤖 <b>Asistente:</b><br><br>' + respuestaFinal + '</div>';
            box.scrollTop = box.scrollHeight;
        }}, 150);
    }}

    function procesarFlujoResumen(q, box) {{
        if (!flujoResumen) {{
            flujoResumen = true;
            pasoResumen = 1;
            dataResumen = {{}};
        }}

        var viejosBotones = box.querySelectorAll(".bloque-paso-resumen");
        viejosBotones.forEach(function(el) {{ el.remove(); }});

        var htmlBot = "";
        if (pasoResumen === 1) {{
            htmlBot = '<div class="bloque-paso-resumen">📋 <b>Generador de Cierre (Paso 1/5):</b><br><span style="color:#d0d0d0;">¿Qué tipo de ciclo fue?</span><br><br><div style="display:flex; gap:6px;"><button onclick="responderPasoResumen(\'ciclo\', \'Uniciclo\', 2)" style="flex:1; cursor:pointer; background:#0284c7; color:white; border:none; padding:6px; border-radius:6px; font-weight:bold;">1️⃣ Uniciclo</button><button onclick="responderPasoResumen(\'ciclo\', \'C1\', 2)" style="flex:1; cursor:pointer; background:#0284c7; color:white; border:none; padding:6px; border-radius:6px; font-weight:bold;">2️⃣ Ciclo 1</button></div></div>';
        }} else if (pasoResumen === 2) {{
            htmlBot = '<div class="bloque-paso-resumen">📋 <b>Generador de Cierre (Paso 2/5):</b><br><span style="color:#d0d0d0;">Unidades dedicadas para Centro: ¿Logis tomó todas?</span><br><br><div style="display:flex; gap:6px;"><button onclick="responderPasoResumen(\'logis_tomo_todas\', true, 2.5)" style="flex:1; cursor:pointer; background:#0284c7; color:white; border:none; padding:6px; border-radius:6px; font-weight:bold;">1️⃣ Sí</button><button onclick="responderPasoResumen(\'logis_tomo_todas\', false, 2.2)" style="flex:1; cursor:pointer; background:#0284c7; color:white; border:none; padding:6px; border-radius:6px; font-weight:bold;">2️⃣ No</button></div></div>';
        }} else if (pasoResumen === 2.2) {{
            htmlBot = '<div class="bloque-paso-resumen">📋 <b>Generador de Cierre (Paso 2.2):</b><br><span style="color:#d0d0d0;">¿Cuál dejó fuera?</span><br><br><button onclick="responderPasoResumen(\'unidades_fuera\', \'la 3.5 tons\', 2.5)">🚛 La 3.5 tons</button><button onclick="responderPasoResumen(\'unidades_fuera\', \'la Delivery Cell\', 2.5)">📦 La Delivery Cell</button><button onclick="responderPasoResumen(\'unidades_fuera\', \'ambas\', 2.5)">❌ Ambas</button></div>';
        }} else if (pasoResumen === 2.5) {{
            htmlBot = '<div class="bloque-paso-resumen">📋 <b>Generador de Cierre (Paso 3/5):</b><br><span style="color:#d0d0d0;">¿Hubo Bulk (H&B)?</span><br><br><button onclick="responderPasoResumen(\'hubo_bulk\', true, 3)">1️⃣ Sí</button><button onclick="responderPasoResumen(\'hubo_bulk\', false, 3)">2️⃣ No</button></div>';
        }} else if (pasoResumen === 3) {{
            htmlBot = '<div class="bloque-paso-resumen">📋 <b>Generador de Cierre (Paso 4/5):</b><br><span style="color:#d0d0d0;">¿Hubo dropeo de nodos?</span><br><br><button onclick="responderPasoResumen(\'dropeo_nodos\', true, 3.5)">1️⃣ Sí</button><button onclick="responderPasoResumen(\'dropeo_nodos\', false, 4)">2️⃣ No</button></div>';
        }} else if (pasoResumen === 3.5) {{
            htmlBot = '<div class="bloque-paso-resumen">📋 <b>Generador de Cierre:</b><br><span style="color:#d0d0d0;">¿Dropeo por restricción?</span><br><br><button onclick="responderPasoResumen(\'dropeo_restriccion\', true, 4)">1️⃣ Sí</button><button onclick="responderPasoResumen(\'dropeo_restriccion\', false, 4)">2️⃣ No</button></div>';
        }} else if (pasoResumen === 4) {{
            htmlBot = '<div class="bloque-paso-resumen">📋 <b>Generador de Cierre (Paso 5/5):</b><br><span style="color:#d0d0d0;">¿Cargó Alchichica ND?</span><br><br><button onclick="responderPasoResumen(\'alchichica\', true, 4.5)">1️⃣ Sí</button><button onclick="responderPasoResumen(\'alchichica\', false, 5)">2️⃣ No</button></div>';
        }} else if (pasoResumen === 4.5) {{
            htmlBot = '<div class="bloque-paso-resumen">📋 <b>Generador de Cierre:</b><br><span style="color:#d0d0d0;">¿Con 2 Small Van MLP?</span><br><br><button onclick="responderPasoResumen(\'alchichica_2sv\', true, 5)">1️⃣ Sí</button><button onclick="responderPasoResumen(\'alchichica_2sv\', false, 5)">2️⃣ No</button></div>';
        }} else if (pasoResumen === 5) {{
            htmlBot = '<div class="bloque-paso-resumen">📋 <b>Preguntas completadas:</b><br><button onclick="generarReporteFinalResumen()" style="width:100%; background:#28a745; color:white; padding:8px; border-radius:6px; font-weight:bold;">🚀 Generar Resumen Completo</button></div>';
        }}

        box.innerHTML += '<div style="background: #25282b; border-left: 3px solid #0284c7; padding: 8px; border-radius: 6px; color: #ffffff; margin-bottom: 6px;">🤖 <b>Asistente:</b><br>' + htmlBot + '</div>';
        box.scrollTop = box.scrollHeight;
    }}

    function responderPasoResumen(clave, valor, siguientePaso) {{
        dataResumen[clave] = valor;
        pasoResumen = siguientePaso;
        var box = document.getElementById("box-mensajes-bot");
        if (!box) return;
        var textoConfirmacion = typeof valor === "boolean" ? (valor ? "Sí" : "No") : valor;
        box.innerHTML += '<div style="background: #315c4f; border-right: 3px solid #38bdf8; padding: 6px 10px; border-radius: 6px; color: #ffffff; text-align: right; margin-bottom: 6px; font-size: 11px;">✔ Seleccionaste: <b>' + textoConfirmacion + '</b></div>';
        procesarFlujoResumen("", box);
    }}

    function generarReporteFinalResumen() {{
        var box = document.getElementById("box-mensajes-bot");
        var d = dataResumen;
        var cicloTxt = d.ciclo || "C1";

        var textoUnidades = "";
        if (d.logis_tomo_todas || !d.unidades_fuera) {{
            textoUnidades = "👉 <b>Unidades 3.5 tons y Delivery Cell</b>: se asignaron al polígono de Centro, logis tomó ambas.";
        }} else if (d.unidades_fuera === "ambas") {{
            textoUnidades = "👉 <b>Unidades 3.5 tons y Delivery Cell</b>: se asignaron al polígono de Centro, logis dejó fuera ambas.";
        }} else {{
            textoUnidades = "👉 <b>Unidades 3.5 tons y Delivery Cell</b>: se asignaron al polígono de Centro, logis dejó fuera " + d.unidades_fuera + ".";
        }}

        var textoBulk = d.hubo_bulk ? "📦 Se asignó H&B para el volumen Bulk.<br>" : "";
        var textoDropeo = d.dropeo_nodos ? (d.dropeo_restriccion ? "👉 <b>Hubo dropeo de nodo</b> y se cargó en contingencia (logis nos dejó fuera ids por zona de restricción)." : "👉 <b>Hubo dropeo de nodo</b> y se cargó en contingencia.") : "👉 No hubo dropeo de nodo.";
        var textoAlchichica = d.alchichica ? (d.alchichica_2sv !== false ? "🚛 Se cargó plan de <b>Alchichica ND</b> en AM0 con 2 unidades Small Van MLP.<br>" : "🚛 Se cargó plan de <b>Alchichica ND</b> en AM0.<br>") : "";

        var resumenFinal = "<b>**Queda publicado " + cicloTxt + " team**:</b><br><br>" +
            "📌 Se trabajó con el volumen disponible al momento de iniciar el ruteo.<br>" +
            "📌 Se cargaron las Rentals como híbridas en Centro, pero el sistema no las consideró todas como híbridas.<br>" +
            textoUnidades + "<br>" + textoBulk + textoDropeo + "<br>" + textoAlchichica +
            "📌 Se usaron los parámetros establecidos.<br>📋 Comparto template final.<br><br><b>**¡Excelente turno! 👋**</b>";

        flujoResumen = false;
        pasoResumen = 0;

        box.innerHTML += '<div style="background: #1a1c1e; border: 2px solid #28a745; padding: 12px; border-radius: 6px; color: #ffffff; margin-bottom: 6px; font-size:14px; line-height: 1.5;">📋 <b>REPORTE GENERADO:</b><br><br>' + resumenFinal + '</div>';
        box.scrollTop = box.scrollHeight;
    }}
</script>
</body>
</html>
"""

html(app_html, height=1000, scrolling=True)
