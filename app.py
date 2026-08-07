# ==============================================================================
# 1. LIBRERÍAS E INICIALIZACIÓN DE PÁGINA Y ESTADO
# ==============================================================================
import io
import json
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from streamlit.components.v1 import html
from supabase import Client, create_client

st.set_page_config(
    page_title="Monitor Logístico - Liliana García",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inicializador de ruteos dinámicos en session_state
if "ruteos_dinamicos" not in st.session_state:
    st.session_state["ruteos_dinamicos"] = {}


# Inicializar cliente de Supabase
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


try:
    supabase = init_supabase()
except Exception as e:
    supabase = None


# Función para GUARDAR un ruteo en la base de datos
def guardar_ruteo_bd(nombre, datos_dict):
    if supabase:
        try:
            supabase.table("ruteos_guardados").insert(
                {"nombre": nombre, "datos": datos_dict}
            ).execute()
            return True
        except Exception as err:
            st.error(f"Error al guardar en BD: {err}")
    return False


# Función para CARGAR todos los ruteos de la base de datos
def cargar_ruteos_bd():
    if supabase:
        try:
            res = (
                supabase.table("ruteos_guardados")
                .select("*")
                .order("created_at")
                .execute()
            )
            return res.data
        except Exception as err:
            st.error(f"Error al cargar BD: {err}")
    return []


# ==============================================================================
# 2. ESTILOS CSS GENERALES Y COMPONENTES VISUALES
# ==============================================================================
st.markdown(
    """
    <style>
    .block-container {padding: 0rem !important;}
    footer, #MainMenu, header {visibility: hidden;}
    body { background-color: #25282b; }

    .poligono-bloque {
        letter-spacing: -0.2px; 
        white-space: nowrap;    
        zoom: 0.95; 
    }

    #contenedor-padre { display: flex; flex-direction: column; }
    
    .delta { display: none !important; }

    #visor { padding-right: 210px !important; box-sizing: border-box; }
    
    .tabla-flota-reducida {
        max-width: 80% !important;
        margin-left: 0 !important;
        margin-right: auto;
    }

    table {
        table-layout: fixed;
        width: 100%;
        word-wrap: break-word;
    }

    @media (max-width: 1200px) {
        .calc-row td, .calc-row select, .calc-row span {
            font-size: 12px !important;
        }
    }

    @media screen and (-webkit-min-device-pixel-ratio:0) {
        .poligono-bloque {
            zoom: 0.95; 
        }
    }

    /* --- VENTANA FLOTANTE --- */
    div[data-testid="stExpander"] {
        position: fixed !important;
        bottom: 30px !important;
        right: 20px !important;
        width: 480px !important;
        max-height: 600px !important;
        z-index: 999999 !important;
        background-color: #D6C2F0 !important;
        border-radius: 12px !important;
        border: 2px solid #6A35C9 !important;
        box-shadow: 0px 4px 20px rgba(0, 0, 0, 0.7) !important;
    }
    
    div[data-testid="stExpander"] summary p, 
    div[data-testid="stExpander"] summary span {
        color: #1A0A33 !important;
        font-weight: bold;
        font-size: 1.05rem !important;
    }

    /* --- MENSAJE DEL USUARIO --- */
    div[data-testid="stChatMessage"]:has(div[aria-label="user"]) {
        background-color: #7B42F6 !important;
        border-radius: 10px !important;
        padding: 8px !important;
        margin: 6px 0 !important;
        box-shadow: 0px 2px 5px rgba(0,0,0,0.2) !important;
    }

    /* --- MENSAJE DEL BOT / ASISTENTE --- */
    div[data-testid="stChatMessage"]:has(div[aria-label="assistant"]) {
        background-color: #FFFFFF !important;
        border: 2px solid #8F60EC !important;
        border-radius: 10px !important;
        padding: 8px !important;
        margin: 6px 0 !important;
    }

    div[data-testid="stChatMessage"] p {
        color: #1F152E !important;
        font-weight: 500 !important;
    }

    div[data-testid="stChatMessage"]:has(div[aria-label="user"]) p {
        color: #FFFFFF !important;
    }

    div[data-testid="stExpander"] div[data-testid="stVerticalBlock"] {
        max-height: 500px !important;
        overflow-y: auto !important;
        display: flex !important;
        flex-direction: column !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)


# ==============================================================================
# 3. ASISTENTE BOT DE PRIORIDADES DE RUTEO
# ==============================================================================
with st.expander("🤖 BOT prioridades", expanded=False):
    st.write("➡️ Escribe el SVC a consultar.")

    reglas_ruteo = {
        "scp1": (
            "**Prioridades SCP1 C1:**\n\n"
            "* 🔴 **Campeche:** Rental Large Van ➤ NODOS = Delivery"
            " Cell-Dedicada.\n"
            "* 🟢 **Resto planes:** Large Van MLP (nodo=híbrida)."
        ),
        "smx5": (
            "**Prioridades SMX5:**\n\n"
            "* 👉 Iztapalapa, Coyoacán y si alcanza Tláhuac = Small Van 9h\n"
            "* 👉 Resto de planes con car 8h\n"
            "* 👉 **Cercanía de SVC:** Coyoacán, Iztapalapa, Tláhuac, Tlalpan"
            " nte, Tlalpan sur, Xochi, Chalco y Milpa Alta"
        ),
        "smd1": (
            "**Prioridades SMD1 C1:**\n\n"
            "* 🟢 **Centro:** Rental(híbridas) / Crowd / LV(híbridas) / SV\n"
            "* 🟢 **Centro:** Extra large van H&B / MLP Bulk (ver en qué"
            " centro hay + voluminosos y ahí se meten)\n"
            "* 🔵 **Norte:** Crowd zon ext 10hrs / MLP\n"
            "* 🟣 **Kanasin:** Si sobran crowd colocarlas aquí\n"
            "* 🟤 Priorizar las LV y Rentals"
        ),
        "sch1": (
            "**Prioridades SCH1 C1:**\n\n"
            "* 🟢 Falta info\n"
            "* 🟢 Falta info\n"
            "* 🟢 Falta info\n"
            "* 🟢 Falta info\n"
            "* 🟣 Falta info\n"
            "* 🔵 Falta info\n"
            "* 🟤 Falta info"
        ),
        "sja1": (
            "**Prioridades SJA1 C1:**\n\n"
            "* 🟢 **Local:** Rentals Electric = meto todas\n"
            "* 🟢 **Local:** Si meto 3.5, delivery y H&B, quito 2)\n"
            "* 🟢 **Local:** Si meto 3.5 y delivery, quito 1)\n"
            "* 🟢 **Local:** Truck 3.5 MLP (dedicada=2 paradas), H&B"
            " (bulk=híbrida), Delivery Large van (dedicada=3 paradas)\n"
            "* 🟢 **Local:** Al terminal Rentals, se asignan MLP y crowd.\n"
            "* 🟣 **Planes foráneos:** MLP (nodo=híbrida) ➡️ Solo Xico/Tuzamapa"
            " ➤ MLP y Crowd.\n"
            "* 🔵 **EJA1-SP:** Media milla-ruteo fake.\n"
            "* 🟤 **Alchichica ND-AM0:** 2 unidades Small Van MLP/330 min = 65"
            " ids."
        ),
    }

    if "main_chat_messages" not in st.session_state:
        st.session_state.main_chat_messages = []

    with st.container(height=200):
        for msg in st.session_state.main_chat_messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    if query_main := st.chat_input(
        "Escribe tu consulta...", key="main_chat_input"
    ):
        st.session_state.main_chat_messages.append(
            {"role": "user", "content": query_main}
        )

        query_lower = query_main.lower()
        respuesta_main = (
            "No encontré regla para ese centro. Prueba con SCP1, SMX5, SMD1,"
            " SCH1 o SJA1."
        )

        for clave, texto in reglas_ruteo.items():
            if clave in query_lower:
                respuesta_main = f"**{clave.upper()}**:\n{texto}"
                break

        st.session_state.main_chat_messages.append(
            {"role": "assistant", "content": respuesta_main}
        )
        st.rerun()


# ==============================================================================
# 4. DATOS BASE Y DICCIONARIOS DE FLOTA / PLANES
# ==============================================================================
u_SDE = {
    "Moto Car - 3": [25, 30],
    "Moto Car Newbie": [25, 25],
    "Car - 5h": [25, 30],
    "Car - 5 Extendida": [25, 30],
    "Car - 3h": [25, 28],
}

u_PREC = {"Car - 8h": [70, 75], "Small 9h Ext Car": [70, 75]}

NOMBRES_PLANES_PREC = [
    "CHALCO",
    "COYOACÁN",
    "IZTAPALAPA",
    "MILPA ALTA",
    "TLAHUAC",
    "TLALPAN NORTE",
    "TLALPAN SUR",
    "XOCHIMILCO",
]

u_PREC_SMX2 = {
    "Car - 8h": [70, 75],
    "Small 9h Ext Car": [70, 75],
    "Car Zona Extendida": [65, 65],
}

NOMBRES_PLANES_PREG = [
    "CHALCO",
    "CHIMAS",
    "IXTAPALUCA VALLE CHALCO",
    "IZTAPALAPA 1",
    "IZTAPALAPA 2",
    "LA PAZ",
    "PUEBLOS",
    "TEXCOCO",
]

NOMBRES_PLANES_C1 = [
    "CALKINI",
    "CAMPECHE",
    "CANDELARIA",
    "CHAMPOTÓN",
    "ESCÁRCEGA",
    "ESCÁRCEGA EXT",
    "HOLPECHEN",
    "MAXCANUN",
    "SEYBAPLAYA",
    "PLAN 10",
    "PLAN 11",
]

u_C1 = {
    "Rental Large Van": [100, 100],
    "Large Van MLP": [100, 100],
    "Small Van MLP": [100, 100],
    "Delivery Cell Large Van": [1, 1],
    "Delivery Cell Small Van": [1, 1],
}

u_C2 = u_C1.copy()
u_C2["Large Van Híbrida"] = [100, 100]

u_C1_SJA1 = {
    "Small Van MLP foráneo": [110, 120],
    "Large Van MLP foráneo": [110, 120],
    "Car MLP": [80, 100],
    "Extra Large Van MLP H&B": [70, 70],
    "Rental Electric Large Van": [150, 150],
    "Rental Large Van": [120, 120],
    "Rental Replacement": [120, 120],
    "Truck 3.5 tons MLP": [1, 1],
    "Delivery Cell Large Van": [1, 1],
    "Car 8h": [70, 70],
    "Car Newbie": [70, 70],
    "Car Zona Extendida": [70, 70],
    "Moto 3h": [30, 30],
    "Small Van 9h": [70, 70],
    "Small Van 9h Ext": [70, 70],
    "Small Van Newbie": [70, 70],
    "Media Milla SP": [1, 1],
}

NOMBRES_PLANES_C1_SJA1 = [
    "ACTOPAN",
    "⚠️ CENTRO 1",
    "⚠️ CENTRO 2",
    "EJA1 SP",
    "MISANTLA",
    "NAOLINCO",
    "PEROTE",
    "TEZUITLAN",
    "TLALTETELA",
    "TRAPICHE",
    "TUZAMAPA",
    "XICO",
    "CONTINGENCIA NODO",
    "PLAN 14",
    "PLAN 15",
    "PLAN 16",
    "PLAN 17",
]

u_C1_SCH1 = {
    "Car MLP": [110, 120],
    "Small Van MLP": [110, 120],
    "Large Van MLP": [110, 120],
    "Small Van MLP Newbie": [110, 120],
    "Large Van MLP Newbie": [110, 120],
    "Extra large Van MLP": [110, 120],
    "Small Van MLP XPT": [110, 120],
    "Small Van MLP foráneo": [110, 120],
    "Large Van MLP foráneo": [110, 120],
    "Car MLP foráneo": [110, 120],
    "Extra large Van MLP H&B": [100, 100],
    "Rental Car": [120, 150],
    "Rental Electric Large Van": [120, 150],
    "Rental Large Van": [120, 150],
    "Rental Replacement": [120, 150],
    "Rental Small Van Electrica": [120, 150],
    "Rental Small Van": [120, 150],
    "Delivery Cells Car": [1, 1],
    "Truck 3.5 tons MLP": [1, 1],
    "Delivery Cell Large Van": [1, 1],
    "Car 8h": [70, 70],
    "Car Newbie": [50, 50],
    "Car Zona Extendida": [60, 60],
    "Moto 3h": [30, 30],
    "Moto Newbie": [25, 25],
    "Small Van 11h Ext": [70, 70],
    "Small Van 9h": [70, 70],
    "Small Van 9h Ext": [70, 70],
    "Small Van Newbie": [70, 70],
}

NOMBRES_PLANES_C1_SCH1 = [
    "AEROPUERTO",
    "CANTERA",
    "DELICIAS",
    "GRANJAS",
    "MEOQUI",
    "NORTE",
    "SUR",
    "CUAUHTEMOC",
    "PARRAL",
    "PLAN 10",
    "PLAN 11",
    "PLAN 12",
    "PLAN 13",
    "PLAN 14",
]

u_C1_SMD1 = {
    "Car MLP": [110, 120],
    "Small Van MLP": [110, 120],
    "Large Van MLP": [110, 120],
    "Small Van MLP Newbie": [110, 120],
    "Large Van MLP Newbie": [110, 120],
    "Extra large Van MLP": [110, 120],
    "Small Van MLP XPT": [110, 120],
    "Small Van MLP foráneo": [110, 120],
    "Large Van MLP foráneo": [110, 120],
    "Large Van MLP Bulk": [100, 100],
    "Extra large Van MLP H&B": [50, 50],
    "Rental Car": [120, 150],
    "Rental Electric Large Van": [120, 150],
    "Rental Large Van": [120, 150],
    "Rental Replacement": [120, 150],
    "Rental Small Van Electrica": [120, 150],
    "Rental Small Van": [120, 150],
    "Delivery Cells Car": [1, 1],
    "Truck 3.5 tons MLP": [1, 1],
    "Delivery Cell Large Van": [1, 1],
    "Car 8h": [70, 70],
    "Car Newbie": [50, 50],
    "Car Zona Ext 10h": [70, 70],
    "Moto 3h": [30, 30],
    "Moto Newbie": [25, 25],
    "Small Van 11h Ext": [70, 70],
    "Small Van 9h": [70, 70],
    "Small Van 9h Ext": [70, 70],
    "Small Van Newbie": [70, 70],
}

NOMBRES_PLANES_C1_SMD1 = [
    "⚠️ CENTRO 1",
    "⚠️ CENTRO 2",
    "⚠️ KANASIN",
    "MOTUL",
    "MUNA",
    "⚠️ NORTE",
    "SEYE",
    "UMAN",
    "PLAN 9",
    "PLAN 10",
    "PLAN 11",
    "PLAN 12",
    "PLAN 13",
    "PLAN 14",
]

ORH_FIJOS = {
    "Rental E. Large Van": ["500", "70"],
    "Rental E. Small Van": ["450", "70"],
    "Rental Large Van": ["54", "70"],
    "Rental Small Van": ["480", "70"],
    "Large Van MLP": ["500", "80"],
    "Small Van MLP": ["487", "70"],
    "Large Van SDD": ["487", "70"],
    "Small Van SDD": ["487", "70"],
    "Car MLP": ["300", "66"],
    "Car Newbie 3h": ["180", "66"],
    "Car Newbie": ["360", "83"],
    "Car - 8h": ["360", "66"],
    "Car - 8h E1": ["360", "66"],
    "Car - 5h": ["300", "66"],
    "Car - 3h": ["300", "66"],
    "Moto - 3h": ["180", "66"],
    "Small Van SDD": ["487", "70"],
    "Car Zona Extendida": ["360", "66"],
    "Car - 5 Extendida": ["330", "66"],
    "Small 9h Ext Car": ["360", "66"],
}


# ==============================================================================
# 5. FUNCIONES AUXILIARES DE GENERACIÓN DE FILAS Y POLÍGONOS
# ==============================================================================
def gen_master_rows(data_dict, table_id):
    rows = ""
    items = list(data_dict.items())
    total_items = len(items)

    nombres_prec = [
        "CHALCO",
        "COYOACÁN",
        "IZTAPALAPA",
        "MILPA ALTA",
        "TLAHUAC",
        "TLALPAN NORTE",
        "TLALPAN SUR",
        "XOCHIMILCO",
    ]
    nombres_smx2 = [
        "CHALCO",
        "CHIMAS",
        "IXTAPALUCA VALLE CHALCO",
        "IZTAPALAPA 1",
        "IZTAPALAPA 2",
        "LA PAZ",
        "PUEBLOS",
        "TEXCOCO",
    ]

    mostrar_orh_ocup = table_id in [1, 2, 6, 7, 8, 5]
    num_filas_objetivo = 45 if table_id == "PREC" else 4
    rango_final = max(total_items, num_filas_objetivo)

    for i in range(1, rango_final + 1):
        if (data_dict == u_PREC) and (i - 1) < len(nombres_prec):
            p_name = nombres_prec[i - 1]
        elif (data_dict == u_PREC_SMX2) and (i - 1) < len(nombres_smx2):
            p_name = nombres_smx2[i - 1]
        else:
            p_name = f"PLAN {i}"

        if (i - 1) < total_items:
            name, spr = items[i - 1]
        else:
            name, spr = "", [0, 0]

        if "---" in name:
            colspan = 8 if mostrar_orh_ocup else 5
            rows += f"""
            <tr class="es-divisor" style="background: #25282b !important; color: #25282b; height: 28px;">
                <td colspan="{colspan}" style="text-align: center; font-weight: bold; font-size: 13px; letter-spacing: 3px; border: none; pointer-events: none;"> 
                    {name}
                </td>
                <td class="edit-name" style="display:none;">IGNORAR</td>
                <td class="edit-spr-min" style="display:none;">0</td>
                <td class="edit-spr-max" style="display:none;">0</td>
                <td class="edit-orh" style="display:none;">0</td>
                <td class="edit-ocup" style="display:none;">0</td>
                <td class="f-stock" style="display:none;">0</td>
                <td class="f-left" style="display:none;">0</td>
            </tr>"""
        else:
            st_base = "background: #ebebeb; color: #969696;" if not name else ""

            celdas_orh_ocup = ""
            if mostrar_orh_ocup:
                celdas_orh_ocup = """
                <td contenteditable="true"
                    class="edit-orh"
                    oninput="recalc()"
                    style="text-align:center; border:0.2px solid #25282b; width:45px; background:#ffffff; color:#141414;">
                    0
                </td>

                <td class="orh-hora"
                    style="text-align:center; border:0.2px solid #25282b; width:60px; background:#f5f5f5; color:#141414; font-weight:bold;">
                    00:00 hs
                </td>

                <td contenteditable="true"
                    class="edit-ocup"
                    oninput="recalc()"
                    style="text-align:center; border:0.2px solid #25282b; width:70px; background:#ffffff; color:#25282b;">
                    0
                </td>
                """
            else:
                celdas_orh_ocup = """
                <td class="edit-orh" style="display:none;">0</td>
                <td class="orh-hora" style="display:none;">00:00 hs</td>
                <td class="edit-ocup" style="display:none;">0</td>
                """

            rows += f"""
            <tr class="master-row" style="{st_base}">
                <td contenteditable="true" class="edit-name" oninput="recalc()"
                    style="font-weight: bold; text-align: left; padding-left: 10px; border: 0.2px solid #25282b; width: 150px; color: #25282b;">
                    {name}
                </td>

                {celdas_orh_ocup}

                <td contenteditable="true" class="edit-spr-min" oninput="recalc()"
                    style="text-align: center; border: 0.2px solid #25282b; width: 45px; background-color: #25282b; color: #ffffff;">
                    {spr[0]}
                </td>

                <td contenteditable="true" class="edit-spr-max" oninput="recalc()"
                    style="text-align: center; border: 0.2px solid #25282b; width: 45px; background-color: #25282b; color: #ffffff;">
                    {spr[1]}
                </td>

                <td contenteditable="true" class="f-stock" oninput="recalc()"
                    style="text-align: center; border: 0.2px solid #25282b; width: 55px; font-weight: bold; font-size: 13px;">
                    0
                </td>

                <td class="f-ruteadas" 
                    style="text-align: center; border: 0.2px solid #25282b; width: 55px; background-color: #ffffff; font-weight: bold;">
                    0
                </td>

                <td class="f-left"
                    style="text-align:center; border:0.2px solid #25282b; width:45px; font-weight:bold; color:#25282b; border-radius:2px;">
                    0
                </td>
            </tr>"""
    return rows


def export_c1_csv():
    data = []
    for unidad, spr in u_C1.items():
        data.append({
            "PLAN": "C1",
            "UNIDAD": unidad,
            "SPR_MIN": spr[0],
            "SPR_MAX": spr[1],
        })

    df_c1 = pd.DataFrame(data)
    csv = df_c1.to_csv(index=False).encode("utf-8")
    return csv


def gen_poligonos(data_target=None):
    polys = ""

    btn_s = (
        "cursor:pointer; border:none; background:rgba(0,0,0,0.08);"
        " color:#25282b; font-weight:bold; width:24px; min-width:24px;"
        " max-width:24px; height:24px; min-height:24px; max-height:24px;"
        " border-radius:4px; flex-shrink:0; display:inline-flex;"
        " align-items:center; justify-content:center;"
    )

    nombres_prec = [
        "CHALCO", "COYOACÁN", "IZTAPALAPA", "MILPA ALTA",
        "TLAHUAC", "TLALPAN NORTE", "TLALPAN SUR", "XOCHIMILCO",
    ]
    nombres_smx2 = [
        "CHALCO", "CHIMAS", "IXTAPALUCA VALLE CHALCO", "IZTAPALAPA 1",
        "IZTAPALAPA 2", "LA PAZ", "PUEBLOS", "TEXCOCO",
    ]

    es_c1 = data_target in (u_C1, u_C1_SJA1, u_C1_SCH1, u_C1_SMD1)
    es_sde = data_target == u_SDE
    es_prec = data_target == u_PREC

    div_flex = (
        "display: flex; align-items: center; justify-content: space-between;"
        " padding: 2px 4px; width: 100%; min-width: 100%; max-width: 100%;"
        " box-sizing: border-box;"
    )
    span_num_u = (
        "font-weight: bold; display: inline-block; text-align: center; width:"
        " 28px; min-width: 28px; max-width: 28px; flex-shrink: 0;"
    )
    span_num_spr = (
        "font-weight: bold; display: inline-block; text-align: center; width:"
        " 38px; min-width: 38px; max-width: 43px; flex-shrink: 0;"
    )
    select_style = (
        "width:160px; max-width: 160px; border:none; background:transparent;"
        " font-weight:600; font-size:14px; color:#25282b; padding: 4px; cursor:"
        " pointer;"
    )

    fila_inner = f"""
    <tr class="calc-row">
        <td class="u-manual-cell" style="background: #d3f0e5; border: 0.6px solid #25282b; padding: 2px; width: 105px; min-width: 105px; max-width: 105px;">
            <div style="{div_flex}">
                <button style="{btn_s}" onclick="stepVal(this, -1, 'u')">-</button>
                <span contenteditable="true" class="u-manual" oninput="manualEdit(this)" style="{span_num_u} color: #25282b !important;">0</span>
                <button style="{btn_s}" onclick="stepVal(this, 1, 'u')">+</button>
            </div>
        </td>
        <td class="spr-real-cell" style="background: #FFFFFF; border: 0.6px solid #25282b; padding: 2px; width: 90px; min-width: 90px; max-width: 90px;">
            <div style="{div_flex}">
                <button style="{btn_s}" onclick="stepVal(this, -1, 's')">-</button>
                <span contenteditable="true" class="spr-real-val" oninput="manualEdit(this)" style="{span_num_spr} color: #25282b !important;">0</span>
                <button style="{btn_s}" onclick="stepVal(this, 1, 's')">+</button>
            </div>
        </td>
        <td style="border: 0.5px solid #25282b; padding: 2px; width: 170px; min-width: 170px; max-width: 170px;">
            <select class="s-type" onchange="resetRow(this); updateSelectColor(this);" style="{select_style} color: #808080;"> 
                <option value="">Seleccionar...</option>
            </select>
        </td>
        <td style="width: 45px; min-width: 45px; max-width: 45px; text-align: center; border: 0.5px solid #25282b;"><input type="checkbox" class="ok-check" style="transform: scale(1.7); accent-color: #9ACD32; cursor: pointer;"></td>
    </tr>"""

    campo_volumen_normal = """
<div style="text-align:center;">
    <span class="v-total-val" contenteditable="true" oninput="recalc()" style="display:inline-block; min-width:55px; padding:2px 8px; border:none; border-radius:4px; background:#ededed; font-size:22px; font-weight:bold; color:#808080; text-align:center;">0</span>
</div>"""

    campo_volumen_c1 = """
<div style="text-align:center;">
    <span class="v-total-val" contenteditable="true" oninput="recalc()" style="display:inline-block; min-width:55px; padding:2px 8px; border:none; border-radius:4px; background:#ededed; font-size:22px; font-weight:bold; color:#808080; text-align:center;">0</span>
</div>
<hr style="margin:4px 0; border:none; border-top:2px solid #999;">
<div style="font-size:13px;font-weight:bold;color:#25282b;">Nodos: <span class="nodos-val" contenteditable="true" style="display:inline-block; min-width:28px; text-align:center; border:none; border-radius:4px; background:#ededed; font-size:16px; font-weight:bold; color:#FF6347; padding:0 4px; margin-left:3px;">0</span></div>"""

    campo_campeche = """
<div style="text-align:center;">
    <span class="v-total-val" contenteditable="true" oninput="recalc()" style="display:inline-block; min-width:55px; padding:2px 8px; border:none; border-radius:4px; background:#ededed; font-size:22px; font-weight:bold; color:#808080; text-align:center;">0</span>
</div>
<hr style="margin:4px 0; border:none; border-top:2px solid #999;">
<div style="font-size:13px;font-weight:bold;color:#25282b;">Nodos: <span class="nodos-campeche" contenteditable="true" style="display:inline-block; min-width:28px; text-align:center; border:none; border-radius:4px; background:#ededed; font-size:16px; font-weight:bold; color:#FF6347; padding:0 4px; margin-left:3px;">0</span></div>"""

    if data_target == u_C1_SJA1:
        limite_tablas = len(NOMBRES_PLANES_C1_SJA1) + 1
    elif data_target == u_C1_SCH1:
        limite_tablas = 16
    elif data_target == u_C1_SMD1:
        limite_tablas = 20
    elif es_sde:
        limite_tablas = 5
    else:
        limite_tablas = 20

    for i in range(1, limite_tablas):
        if data_target == u_PREC and (i - 1) < len(nombres_prec):
            nombre_final = nombres_prec[i - 1]
        elif data_target == u_PREC_SMX2 and (i - 1) < len(nombres_smx2):
            nombre_final = nombres_smx2[i - 1]
        elif data_target == u_C1 and (i - 1) < len(NOMBRES_PLANES_C1):
            nombre_final = NOMBRES_PLANES_C1[i - 1]
        elif data_target == u_C1_SJA1 and (i - 1) < len(NOMBRES_PLANES_C1_SJA1):
            nombre_final = NOMBRES_PLANES_C1_SJA1[i - 1]
        elif data_target == u_C1_SCH1 and (i - 1) < len(NOMBRES_PLANES_C1_SCH1):
            nombre_final = NOMBRES_PLANES_C1_SCH1[i - 1]
        elif data_target == u_C1_SMD1 and (i - 1) < len(NOMBRES_PLANES_C1_SMD1):
            nombre_final = NOMBRES_PLANES_C1_SMD1[i - 1]
        else:
            nombre_final = f"PLAN {i}"

        if nombre_final == "CAMPECHE":
            contenido_volumen = campo_campeche
        elif es_c1:
            contenido_volumen = campo_volumen_c1
        else:
            contenido_volumen = campo_volumen_normal

        if es_sde:
            rowspan_actual = 5
        elif es_prec:
            rowspan_actual = 4
        elif data_target == u_C1_SJA1:
            rowspan_actual = 8 if nombre_final == "⚠️ CENTRO 1" else 5
        elif data_target == u_C1_SMD1:
            rowspan_actual = 5
        else:
            rowspan_actual = 3

        if es_sde:
            filas_extra = fila_inner * 4
        elif es_prec:
            filas_extra = fila_inner * 3
        elif data_target == u_C1_SJA1:
            filas_extra = fila_inner * 7 if nombre_final == "⚠️ CENTRO 1" else fila_inner * 4
        elif data_target == u_C1_SMD1:
            filas_extra = fila_inner * 4
        else:
            filas_extra = fila_inner * 2

        polys += f"""
        <div class="poligono-bloque" style="margin-bottom:12px; box-shadow: none; border-radius: 0px; overflow-x: auto; background: #ededed; border: 1.5px solid #25282b;">           
            <table style="width: 100%; min-width: 630px; border-collapse: collapse; border: 1.5px solid #25282b;">
                <thead>
                    <tr style="background: #25282b; color: white; font-size: 12px; height: 28px;">                        
                        <th style="padding: 0 10px; border-right: 1px solid #25282b; min-width: 130px; width: 130px;">PLAN</th>
                        <th style="border-right: 1px solid #25282b; width: 85px;">VOL. TOTAL</th>
                        <th style="width: 105px; min-width: 105px; max-width: 105px; border-right: 1px solid #25282b;"># USADAS</th>
                        <th style="width: 105px; min-width: 105px; max-width: 105px; border-right: 1px solid #25282b;">SPR</th>
                        <th style="width: 180px; min-width: 180px; max-width: 180px; border-right: 1px solid #25282b;">TIPO DE UNIDAD</th>
                        <th style="width: 45px; min-width: 45px; max-width: 45px; text-align: center;">OK</th> 
                    </tr>
                </thead>
                <tbody>
                    <tr class="calc-row"> 
                        <td class="plan-cell" rowspan="{rowspan_actual}" contenteditable="true" style="background: #dcdcdc; font-weight: bold; text-align:center; border: 1px solid #25282b; padding: 5px; color:#141414;">{nombre_final}</td>
                        <td class="vol-cell" rowspan="{rowspan_actual}" style="color:#808080; font-weight:bold; text-align:center; border:1px solid #25282b; padding:5px;">{contenido_volumen}</td>
                        <td class="u-manual-cell" style="background: #d3f0e5; border: 0.5px solid #25282b; padding: 2px; width: 105px; min-width: 105px; max-width: 105px;">
                            <div style="{div_flex}">
                                <button style="{btn_s}" onclick="stepVal(this, -1, 'u')">-</button> 
                                <span contenteditable="true" class="u-manual" oninput="manualEdit(this)" style="{span_num_u} color: #25282b !important;">0</span>
                                <button style="{btn_s}" onclick="stepVal(this, 1, 'u')">+</button>
                            </div>
                        </td>
                        <td class="spr-real-cell" style="background: #FFFFFF; border: 0.5px solid #25282b; padding: 2px; width: 90px; min-width: 90px; max-width: 90px;">
                            <div style="{div_flex}">
                                <button style="{btn_s}" onclick="stepVal(this, -1, 's')">-</button>
                                <span contenteditable="true" class="spr-real-val" oninput="manualEdit(this)" style="{span_num_spr}">0</span>
                                <button style="{btn_s}" onclick="stepVal(this, 1, 's')">+</button>
                            </div>
                        </td>
                        <td style="border: 0.5px solid #25282b; padding: 2px;">
                            <select class="s-type" onchange="resetRow(this)" style="{select_style}">
                                <option>Seleccionar...</option>
                            </select>
                        </td>
                        <td style="width: 45px; min-width: 45px; max-width: 45px; text-align: center; border: 0.5px solid #25282b;"><input type="checkbox" class="ok-check" style="transform: scale(1.7); accent-color: #9ACD32; cursor: pointer;"></td>
                    </tr>
                    {filas_extra}
                    <tr style="background:#ededed; height: 32px;">
                        <td colspan="3" style="text-align:center; font-weight:bold; border: 1px solid #25282b; font-size: 14px; color:#25282b;">ESTADO:</td>
                        <td class="v-calculado-total" style="font-weight: bold; font-size: 14px; color: #d32f2f; border: 1px solid #25282b; text-align: center;">0</td>
                        <td class="p-diff delta" colspan="2" style="text-align: center; font-weight: bold; border: 1px solid #25282b; font-size: 14px; color: #25282b">VACÍO:</td>
                    </tr>
                </tbody>
                <div style="text-align:center; padding:5px; background:#ededed;">
                    <button onclick="agregarFilaPlan(this)" style="cursor:pointer; margin-right:5px;">➕</button>
                    <button onclick="quitarFilaPlan(this)" style="cursor:pointer;">➖</button>
                    <span class="contador-filas" style="margin-left:10px;font-weight:bold;">Filas: {rowspan_actual}</span>
                </div>     
            </table>
        </div>"""

    return polys

PERFILES = {}
perfil_actual = "LUNES"


# ==============================================================================
# 6. PLANTILLA HTML/JAVASCRIPT COMPLETA (APP_HTML)
# ==============================================================================
app_html = f"""
<!DOCTYPE html>
<html>
<head>

    <!-- Librería de Supabase -->
    <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
    <style>
    
        tr.master-row:hover, tr.calc-row:hover {{
            background-color: #fffecd !important;
            outline: 2px solid #ffc107 !important;
            transition: background-color 0.15s ease, box-shadow 0.15s ease;
            cursor: pointer;
        }}
        tr.master-row:hover td, tr.calc-row:hover td {{ color: #000 !important; }}

        #mi-contador-scp1 {{
            position: fixed; top: 156px; right: 20px; 
            background: rgba(37, 40, 43, 0.98); color: #ffffff; padding: 16px; 
            border-radius: 10px; z-index: 999999; font-family: sans-serif;
            font-size: 14px; box-shadow: 0px 6px 18px rgba(0,0,0,0.6);
            border: 1.2px solid transparent; width: 300px; max-height: 410px;
            overflow-y: auto; pointer-events: auto; display: block;
        }}

        #mi-contador-sja1 {{
            position: fixed; top: 156px; right: 20px; 
            background: rgba(37, 40, 43, 0.98); color: #ffffff; padding: 16px; 
            border-radius: 10px; z-index: 999999; font-family: sans-serif;
            font-size: 14px; box-shadow: 0 6px 18px rgba(0,0,0,0.6);
            border: 1.2px solid transparent; width: 350px; max-height: 210px;
            overflow-y: auto; pointer-events: auto; display: none;
        }}

        .cont-item {{
            display: flex; justify-content: space-between; align-items: center;
            border-bottom: 1px solid rgba(255,255,255,0.15); padding: 8px 0;
        }}
        .cont-item:last-child {{ border-bottom: none; }}
        .cont-name {{
            font-weight: normal; color: #D3D3D3; white-space: nowrap;
            overflow: hidden; text-overflow: ellipsis; max-width: 150px; font-size: 14px;
        }}
        .cont-vals {{ font-family: monospace; font-weight: bold; text-align: right; font-size: 14px; }}

        .poligono-bloque button {{ box-shadow: 0 2px 4px rgba(0,0,0,0.1); transition: all 0.1s; }}
        .poligono-bloque button:active {{ box-shadow: 0 0px 0px transparent; transform: translateY(1px); }}
        .filter-btn:active {{ transform: translateY(4px); box-shadow: none !important; }}  

        tr.fila-ok {{ background-color: #e8f5e9 !important; transition: background-color 0.3s ease; }}
        tr.fila-ok td {{ color: #1b5e20 !important; }}

        body {{ font-family: sans-serif; background: #ffffff; padding: 14px; }}
        #visor {{ margin-right: 250px !important; }}

        .meli-table {{
            width: 100% !important; border-collapse: collapse !important;
            border-spacing: 0 !important; table-layout: fixed; background: white;
            border: 1px solid #25282b; box-shadow: none !important; border-radius: 0 !important; overflow: hidden;
        }}
        .meli-table th {{
            background: #f3f3f3 !important; color: #222 !important; font-size: 14px;
            font-weight: 600; border: 1px solid #25282b !important; padding: 4px 6px; text-align: center; height: 24px;
        }}
        .meli-table th:last-child {{ border-right: 2px solid #25282b !important; }}
        .meli-table td {{ border: 1px solid #25282b; padding: 2px 4px; font-size: 14px; height: 24px; background: white; color: #25282b; }}

        #fleet-sticky.fleet-floating {{
            position: fixed !important; top: 70px; left: 20px; right: 20px;
            width: min(1100px, 92vw) !important; margin: 0 auto; max-height: 360px !important;
            overflow: hidden !important; z-index: 999999 !important; background: rgba(255,255,255,0.98) !important;
            border: 4px solid #636363 !important; border-radius: 12px !important;
            box-shadow: 0 14px 28px rgba(0,0,0,0.30) !important; padding: 10px !important;
        }}

        #fleet-sticky.fleet-floating .t-content {{ max-height: 200px !important; overflow: auto !important; }}

        #fleet-drag-handle {{
            position: relative; z-index: 9999999; cursor: grab; user-select: none;
            -webkit-user-select: none; touch-action: none; -webkit-touch-callout: none;
            font-weight: 900; font-size: 12px; padding: 6px 10px; margin: -6px -6px 8px -6px;
            border-bottom: 1px solid rgba(0,0,0,0.10); color: #0a2e42;
        }}
        #fleet-drag-handle:active {{ cursor: grabbing; }}

        #fleet-sticky {{ position: static; top: auto; z-index: auto; background: transparent; border: none; border-radius: 0; padding: 0; box-shadow: none; backdrop-filter: none; }}

        #fleet-sticky.fleet-normal {{
            position: static !important; top: auto !important; left: auto !important;
            right: auto !important; bottom: auto !important; transform: none !important;
            z-index: auto !important; background: transparent !important; border: none !important;
            border-radius: 0 !important; padding: 0 !important; box-shadow: none !important; backdrop-filter: none !important;
        }}

        .master-row {{ border-radius: 9px; box-shadow: 1px 1px 5px #ededed, -2px -2px 6px #efefef; transition: all 0.2s ease; }}
        .meli-table td:first-child {{ border-radius: 3px 0 0 3px; }}
        .meli-table td:last-child {{ border-radius: 0 3px 3px 0; }}

        #google-alert {{
            position: fixed; top: -100px; left: 50%; transform: translateX(-50%);
            background: #d32f2f; color: white; padding: 15px 25px; border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3); transition: 0.4s; z-index: 10000;
        }}
        #google-alert.show {{ top: 20px; }}

        .tab-btn {{
            padding: 10px 12px; cursor: pointer; border: 1px solid #25282b;
            background: linear-gradient(180deg, #f0f0f0 0%, #dcdcdc 100%);
            border-radius: 8px 8px 0 0; font-weight: bold; font-size: 13px; color: #25282b;
            transition: all 0.2s ease; box-shadow: inset 0 1px 0 rgba(255,255,255,0.8), 0 2px 4px rgba(0,0,0,0.1);
            margin-right: 2px; outline: none;
        }}
        .tab-btn:hover {{
            background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
            color: #25282b; box-shadow: 0 4px 8px rgba(0,0,0,0.2); transform: translateY(-2px);
        }}
        .tab-btn.active {{
            background: linear-gradient(180deg, #424242 0%, #25282b 100%) !important;
            color: #ffffff !important; border: 1px solid #061821 !important;
            box-shadow: inset 0 2px 5px rgba(0,0,0,0.3); transform: translateY(0);
        }}

        .tools-panel {{ display: flex; flex-direction: column; gap: 10px; margin-top: 15px; }}
        .google-tool {{
            background: linear-gradient(145deg, #ffffff, #DDA0DD); padding: 15px;
            border-radius: 15px; border: 1px solid #25282b; text-align: center;
            box-shadow: 5px 5px 15px #d1d1d1, -5px -5px 15px #ffffff; transition: transform 0.2s;
        }}
        .google-tool:hover {{ transform: translateY(-3px); }}
        .google-tool input {{
            border-radius: 8px; border: 1px solid #25282b; padding: 5px;
            font-size: 16px; outline: none; box-shadow: inset 2px 2px 5px #d9dbde;
        }}

        #calc_wrapper {{ background: #22c5bc; border-radius: 20px; padding: 15px; border: transparent; outline: none; transition: 0.3s; }}
        #calc_wrapper:focus {{ box-shadow: 0 0 20px #FF00FF, 0 0 40px #FF00FF; border: 2px solid #FF00FF; }}
        #calc_display_box {{ background: #fffacd; border-radius: 10px; padding: 10px; text-align: right; margin-bottom: 10px; min-height: 60px; }}
        .calc-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 5px; }}
        .btn-c {{
            background: #f0f0f0; border: none; font-weight: bold; border-radius: 12px;
            padding: 12px; cursor: pointer; box-shadow: 3px 3px 6px #1da39b, -2px -2px 5px #27ebd2;
            transition: transform 0.1s;
        }}
        .btn-c:active {{ transform: scale(0.95); box-shadow: inset 2px 2px 5px #b1b1b1; }}
        .btn-c-eq {{ background: #FF00FF; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; font-size: 14px; }}
        .crono-card {{ background: #1c1c1c; border-radius: 12px; padding: 15px; color: white; font-family: sans-serif; text-align: center; }}

        html body .meli-table tbody tr:last-child td {{
            height: 25px !important; min-height: 25px !important; max-height: 20px !important;
            padding-top: 2px !important; padding-bottom: 3px !important; line-height: 25px !important; font-size: 14px !important;
        }}
        html body .meli-table tbody tr:last-child {{ height: 16px !important; }}

        .btn-start {{ background: #28a745; color: white; box-shadow: 0 5px 0 #1e7e34; }}
        .btn-stop  {{ background: #ffc107; color: #333;  box-shadow: 0 5px 0 #d39e00; }}
        .btn-reset {{ background: #dc3545; color: white; box-shadow: 0 5px 0 #bd2130; }}

        .crono-card button:active {{ transform: translateY(4px); box-shadow: 0 1px 0 #333; }}
        .crono-card button:hover {{ filter: brightness(1.1); }}

        #body-plan-container th, .meli-table:nth-of-type(2) th {{
            font-size: 22px !important; height: 90px !important; padding: 11px 6px !important; vertical-align: middle !important;
        }}

        body.excel-view #fleet-float,
        body.excel-view #ruteo-float,
        body.excel-view .tools-panel,
        body.excel-view #btn-excel-view {{ display: none !important; }}

        body.excel-view .meli-table td {{ padding: 2px 3px !important; font-size: 14px !important; }}
        body.excel-view .meli-table th {{
            padding: 2px 1px !important; font-size: 11px !important; letter-spacing: -0.3px !important;
            overflow: hidden !important; line-height: 1.0 !important; vertical-align: middle !important;
        }}

        body.excel-view .meli-table tfoot.fila-total td {{ font-size: 16px !important; padding: 6px 8px !important; line-height: 18px !important; font-weight: 900 !important; }}
        body.excel-view .meli-table tfoot.fila-total td[id^="total-ruteadas-"] {{ font-size: 20px !important; font-weight: 900 !important; color: #66CDAA !important; text-align: center !important; }}

        body.excel-view .poligono-bloque table {{ border-collapse: collapse !important; width: 120% !important; table-layout: fixed !important; }}
        body.excel-view .poligono-bloque td, body.excel-view .poligono-bloque th {{
            padding: 8px 3px !important; height: 60px !important; font-size: 13px !important;
            overflow: hidden !important; white-space: nowrap !important; text-overflow: ellipsis !important;
            text-align: center !important; vertical-align: middle !important;
        }}

        body.excel-view .poligono-bloque th:nth-child(5) {{ width: 90px !important; }}
        body.excel-view .poligono-bloque th:nth-child(6) {{ width: 55px !important; }}
        body.excel-view .poligono-bloque th:nth-child(7) {{ width: 45px !important; }}
    </style> 
</head>

<body>
<div id="google-alert">⚠️ <span id="alert-msg"></span> [ENTER para cerrar]</div>
<div style="display:flex; flex-direction:column; gap:20px; width:100%;">

    <div style="width:100%; padding:0; margin-bottom:10px;">
        <div style="background-color: #25282b; color: white; padding: 10px; border-radius: 2px; font-weight: bold; text-align: center; margin-bottom: 10px;">🚚 🚚 DISPONIBILIDAD DE FLOTA 🚛 🚛</div>

        <div id="panel-control-unico" style="display: flex; gap: 20px; background: #25282b; padding: 15px; border-radius: 10px; color: white; justify-content: center; align-items: center; margin: 20px 0;">
            <div style="text-align: center;">
                <div id="hora-actual" style="font-size: 22px; font-weight: bold;">00:00:00</div>
                <div style="font-size: 9px; color: #26d0ff; letter-spacing: 1px;">HORA ACTUAL</div>
            </div>
            <div style="text-align: center; border-left: 1px solid #ffffff; padding-left: 20px; min-width: 120px;">
                <div id="proximo-ruteo" style="font-size: 16px; font-weight: bold; color: #ff9b21; line-height: 1.1;">Sin tareas</div>
                <div id="hora-ruteo" style="font-size: 14px; font-weight: bold; color: #ffffff; margin-top: 2px;">--</div>
                <div style="font-size: 9px; color: #d0d0d0; letter-spacing: 1px; margin-top: 2px;">SIGUIENTE RUTEO</div>
            </div>
            <div style="text-align: center; border-left: 1px solid #ffffff; padding-left: 20px;">
                <div id="cuenta-regresiva" style="font-size: 22px; font-weight: bold; color: #7CFFB2;">00:00</div>
                <div style="font-size: 9px; color: #d0d0d0; letter-spacing: 1px;">TIEMPO RESTANTE</div>
            </div>
        </div>

        <div id="resumen-flota-ruteada" style="display: flex; gap: 15px; margin: 15px 0; justify-content: center;">
            <div style="background: #d7e5fa; padding: 8px; border-radius: 5px; border: 1px solid #bbdefb; text-align: center; width: 100px;">
                <div style="font-size: 10px; font-weight: bold; color: #0861c7;">MLP</div>
                <div id="val-mlp-rute-2" style="font-size: 14px; font-weight: bold;">0</div>
            </div>
            <div style="background: #c6f7f3; padding: 8px; border-radius: 5px; border: 1px solid #68b0ac; text-align: center; width: 100px;">
                <div style="font-size: 10px; font-weight: bold; color: #d021eb;">RENTAL</div>
                <div id="val-rental-rute-2" style="font-size: 14px; font-weight: bold;">0</div>
            </div>
            <div style="background: #d3f5d3; padding: 8px; border-radius: 5px; border: 1px solid #90EE90; text-align: center; width: 100px;">
                <div style="font-size: 10px; font-weight: bold; color: #209626;">CAR</div>
                <div id="val-car-rute-2" style="font-size: 14px; font-weight: bold;">0</div>
            </div>
        </div>

        <div id="dos-pct-global" style="background:#f5f5f5; border:1px solid #d0d0d0; border-radius:6px; padding:6px; margin-bottom:10px; text-align:center; font-weight:bold; color:#25282b;"></div>

        <div id="fleet-sticky" class="fleet-normal">
            <div id="fleet-drag-handle">
                <button id="fleet-toggle-btn" onclick="toggleFleetFloating();" style="float:center; cursor:pointer; border:none; background:#25282b; color:white; padding:3px 8px; border-radius:6px; font-weight:bold;">FLOTAR ☁️</button>
            </div>

            <div style="display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 5px;">
                <div style="position: relative; display: inline-flex; align-items: center; gap: 6px;">
                    <button onclick="toggleMenuPestanas()" style="cursor:pointer; background:#25282b; color:white; border:1px solid #454545; font-weight:bold; font-size:12px; padding:6px 10px; border-radius:6px; margin-right:4px;" title="Configurar visibilidad de pestañas">👁️ Pestañas</button>

                    <div id="panel-selector-pestanas" style="display:none; position:absolute; top:38px; left:0; background:#25282b; color:white; border:1px solid #454545; padding:10px 14px; border-radius:8px; z-index:99999; box-shadow:0 4px 12px rgba(0,0,0,0.5); font-size:13px; min-width:140px;">
                        <div style="font-weight:bold; margin-bottom:8px; border-bottom:1px solid #555; padding-bottom:4px; color:#26d4ca;">Mostrar / Ocultar:</div>
                        <label style="display:block; margin-bottom:6px; cursor:pointer;"><input type="checkbox" checked onchange="toggleBtnPestana('btn-tab-sde', this.checked)"> SDE</label>
                        <label style="display:block; margin-bottom:6px; cursor:pointer;"><input type="checkbox" checked onchange="toggleBtnPestana('btn-tab-smx5', this.checked)"> PREC SMX5</label>
                        <label style="display:block; margin-bottom:6px; cursor:pointer;"><input type="checkbox" checked onchange="toggleBtnPestana('btn-tab-smx2', this.checked)"> PREC SMX2</label>
                        <label style="display:block; margin-bottom:6px; cursor:pointer;"><input type="checkbox" checked onchange="toggleBtnPestana('btn-tab-scp1', this.checked)"> C1 SCP1</label>
                        <label style="display:block; margin-bottom:2px; cursor:pointer;"><input type="checkbox" checked onchange="toggleBtnPestana('btn-tab-sch1', this.checked)"> C1 SCH1</label>
                        <label style="display:block; margin-bottom:2px; cursor:pointer;"><input type="checkbox" checked onchange="toggleBtnPestana('btn-tab-smd1', this.checked)"> C1 SMD1</label>
                        <label style="display:block; margin-bottom:2px; cursor:pointer;"><input type="checkbox" checked onchange="toggleBtnPestana('btn-tab-sja1', this.checked)"> C1 SJA1</label>
                    </div>

                    <button id="btn-tab-sde" class="tab-btn" onclick="showTab(4, this)">SDE</button>
                    <button id="btn-tab-smx5" class="tab-btn" onclick="showTab(1, this)">PREC SMX5</button>
                    <button id="btn-tab-smx2" class="tab-btn" onclick="showTab(5, this)">PREC SMX2</button>
                    <button id="btn-tab-scp1" class="tab-btn active" onclick="showTab(2, this)">C1 SCP1</button>
                    <button id="btn-tab-sch1" class="tab-btn" onclick="showTab(7, this)">C1 SCH1</button>
                    <button id="btn-tab-smd1" class="tab-btn" onclick="showTab(8, this)">C1 SMD1</button>
                    <button id="btn-tab-sja1" class="tab-btn" onclick="showTab(6, this)">C1 SJA1</button>
                </div>

                <div style="padding-bottom: 5px; display: flex; gap: 6px; align-items: center;"> 
                    <button onclick="distribuirAutomatico()" style="cursor:pointer; background: #26d4ca; color: #2e3030; border: none; font-size: 12px; padding: 7px 12px; border-radius: 4px; font-weight: bold; box-shadow: 0 3px 0 #2d968f; transition: all 0.05s; outline: none;">🧠 AUTO-CALCULAR</button>
                    <button class="filter-btn" onclick="filterRows(true)" style="cursor:pointer; background: linear-gradient(180deg, #4f4f4f 0%, #25282b 100%); color: white; border: 1px solid #25282b; font-size: 12px; padding: 6px 12px; border-radius: 4px; font-weight: bold; box-shadow: 0 3px 0 #0a3045; transition: all 0.05s; outline: none;">ACTIVAS</button>
                    <button class="filter-btn" onclick="filterRows(false)" style="cursor:pointer; background: #808080; color:white; border:none; font-size:12px; padding:6px 12px; border-radius:4px; font-weight:bold; box-shadow: 0 3px 0 #454545; transition: all 0.05s; outline: none;">TODAS</button>
                </div>

                <button id="excel-btn" onclick="toggleExcelView()" style="cursor:pointer; background:#228B22; color:white; border:none; font-size:12px; padding:4px 10px; border-radius:4px; font-weight:bold; box-shadow:0 3px 0 #1c6d1c; transition:all 0.05s; outline:none; display: inline-flex; align-items: center; gap: 6px; transform: translateY(-6px); position: relative;">
                    <span style="font-size: 16px;">👁️</span>
                </button>
            </div>

            <!-- TABLAS DE DISPONIBILIDAD -->
            <div id="tab-2" class="t-content">
                <table class="meli-table" style="width: 100%; table-layout: fixed; border-collapse: collapse;">
                    <thead>
                        <tr style="background: linear-gradient(180deg, #0a2e42 0%, #25282b 100%); color: white;">
                            <th style="border-right: 0.5px solid #25282b; padding: 4px 8px; font-size: 14px; color: #25282b !important;">UNIDAD</th>
                            <th colspan="2" style="border-right: 0.5px solid #25282b; padding: 2px; font-size: 11px; color: #25282b !important; width: 105px;">ORH</th>
                            <th style="border-right: 0.5px solid #25282b; padding: 2px; font-size: 11px; color: #25282b !important; width: 45px;">% OCUP</th>
                            <th style="border-right: 0.5px solid #25282b; padding: 2px; font-size: 11px; color: #25282b !important; width: 45px;">SPR<br>MIN</th>
                            <th style="border-right: 0.5px solid #25282b; padding: 2px; font-size: 11px; color: #25282b !important; width: 45px;">SPR<br>MAX</th>
                            <th style="border-right:0.5px solid #25282b; padding:4px 8px; font-size:11px; color:#25282b !important; width:60px;">SCHEDULE</th>
                            <th style="border-right:0.7px solid #25282b; padding:4px 9px; font-size:11px; color:#25282b !important; width:57px; text-align:center; display:table-cell; vertical-align:middle;">USADAS</th>
                            <th style="border-right:0.5px solid #25282b; padding:4px 8px; font-size:11px; color:#25282b !important; width:50px;">DELTA</th>
                        </tr>
                    </thead>
                    <tbody id="body-2">{gen_master_rows(u_C1, 2)}</tbody>
                    <tfoot class="fila-total">
                        <tr class="fila-total">
                            <td style="border:none;"></td>
                            <td colspan="6" style="padding:6px; text-align:right;">🚛 TOTAL RUTEADAS</td>
                            <td id="total-ruteadas-2" style="text-align:center; color:#3CB371; font-size:16px; font-weight:bold;">0</td>
                        </tr>
                    </tfoot>
                </table>
            </div>

            <div id="tab-6" class="t-content" style="display:none;">
                <table class="meli-table" style="width: 100%; table-layout: fixed; border-collapse: collapse;">
                    <thead>
                        <tr style="background: linear-gradient(180deg, #0a2e42 0%, #25282b 100%); color: white;">
                            <th style="border-right: 0.5px solid #25282b; padding: 4px 8px; font-size: 14px; color: #25282b !important;">UNIDAD</th>
                            <th colspan="2" style="border-right: 0.5px solid #25282b; padding: 2px; font-size: 11px; color: #25282b !important; width: 105px;">ORH</th>
                            <th style="border-right: 0.5px solid #25282b; padding: 2px; font-size: 11px; color: #25282b !important; width: 45px;">% OCUP</th>
                            <th style="border-right: 0.5px solid #25282b; padding: 2px; font-size: 11px; color: #25282b !important; width: 45px;">SPR<br>MIN</th>
                            <th style="border-right: 0.5px solid #25282b; padding: 2px; font-size: 11px; color: #25282b !important; width: 45px;">SPR<br>MAX</th>
                            <th style="border-right:0.5px solid #25282b; padding:4px 8px; font-size:11px; color:#25282b !important; width:60px;">SCHEDULE</th>
                            <th style="border-right:0.7px solid #25282b; padding:4px 9px; font-size:11px; color:#25282b !important; width:57px; text-align:center; display:table-cell; vertical-align:middle;">USADAS</th>
                            <th style="border-right:0.5px solid #25282b; padding:4px 8px; font-size:11px; color:#25282b !important; width:50px;">DELTA</th>
                        </tr>
                    </thead>
                    <tbody id="body-6">{gen_master_rows(u_C1_SJA1, 6)}</tbody>
                    <tfoot class="fila-total"> 
                        <tr class="fila-total">
                            <td style="border:none;"></td>
                            <td colspan="6" style="padding:6px; text-align:right;">🚛 TOTAL RUTEADAS</td>
                            <td id="total-ruteadas-6" style="text-align:center; color:#3CB371; font-size:16px; font-weight:bold !important;">0</td>
                        </tr>
                    </tfoot>
                </table>
            </div>

            <div id="tab-7" class="t-content" style="display:none;">
                <table class="meli-table" style="width: 100%; table-layout: fixed; border-collapse: collapse;">
                    <thead>
                        <tr style="background: linear-gradient(180deg, #0a2e42 0%, #25282b 100%); color: white;">
                            <th style="border-right: 0.5px solid #25282b; padding: 4px 8px; font-size: 14px; color: #25282b !important;">UNIDAD</th>
                            <th colspan="2" style="border-right: 0.5px solid #25282b; padding: 2px; font-size: 11px; color: #25282b !important; width: 105px;">ORH</th>
                            <th style="border-right: 0.5px solid #25282b; padding: 2px; font-size: 11px; color: #25282b !important; width: 45px;">% OCUP</th>
                            <th style="border-right: 0.5px solid #25282b; padding: 2px; font-size: 11px; color: #25282b !important; width: 45px;">SPR<br>MIN</th>
                            <th style="border-right: 0.5px solid #25282b; padding: 2px; font-size: 11px; color: #25282b !important; width: 45px;">SPR<br>MAX</th>
                            <th style="border-right:0.5px solid #25282b; padding:4px 8px; font-size:11px; color:#25282b !important; width:60px;">SCHEDULE</th>
                            <th style="border-right:0.7px solid #25282b; padding:4px 9px; font-size:11px; color:#25282b !important; width:57px; text-align:center; display:table-cell; vertical-align:middle;">USADAS</th>
                            <th style="border-right:0.5px solid #25282b; padding:4px 8px; font-size:11px; color:#25282b !important; width:50px;">DELTA</th>
                        </tr>
                    </thead>
                    <tbody id="body-7">{gen_master_rows(u_C1_SCH1, 7)}</tbody>
                    <tfoot class="fila-total"> 
                        <tr class="fila-total">
                            <td style="border:none;"></td>
                            <td colspan="6" style="padding:6px; text-align:right;">🚛 TOTAL RUTEADAS</td>
                            <td id="total-ruteadas-7" style="text-align:center; color:#3CB371; font-size:16px; font-weight:bold !important;">0</td>
                        </tr>
                    </tfoot>
                </table>
            </div>

            <div id="tab-8" class="t-content" style="display:none;">
                <table class="meli-table" style="width: 100%; table-layout: fixed; border-collapse: collapse;">
                    <thead>
                        <tr style="background: linear-gradient(180deg, #0a2e42 0%, #25282b 100%); color: white;">
                            <th style="border-right: 0.5px solid #25282b; padding: 4px 8px; font-size: 14px; color: #25282b !important;">UNIDAD</th>
                            <th colspan="2" style="border-right: 0.5px solid #25282b; padding: 2px; font-size: 11px; color: #25282b !important; width: 105px;">ORH</th>
                            <th style="border-right: 0.5px solid #25282b; padding: 2px; font-size: 11px; color: #25282b !important; width: 45px;">% OCUP</th>
                            <th style="border-right: 0.5px solid #25282b; padding: 2px; font-size: 11px; color: #25282b !important; width: 45px;">SPR<br>MIN</th>
                            <th style="border-right: 0.5px solid #25282b; padding: 2px; font-size: 11px; color: #25282b !important; width: 45px;">SPR<br>MAX</th>
                            <th style="border-right:0.5px solid #25282b; padding:4px 8px; font-size:11px; color:#25282b !important; width:60px;">SCHEDULE</th>
                            <th style="border-right:0.7px solid #25282b; padding:4px 9px; font-size:11px; color:#25282b !important; width:57px; text-align:center; display:table-cell; vertical-align:middle;">USADAS</th>
                            <th style="border-right:0.5px solid #25282b; padding:4px 8px; font-size:11px; color:#25282b !important; width:50px;">DELTA</th>
                        </tr>
                    </thead>
                    <tbody id="body-8">{gen_master_rows(u_C1_SMD1, 8)}</tbody>
                    <tfoot class="fila-total"> 
                        <tr class="fila-total">
                            <td style="border:none;"></td>
                            <td colspan="6" style="padding:6px; text-align:right;">🚛 TOTAL RUTEADAS</td>
                            <td id="total-ruteadas-8" style="text-align:center; color:#3CB371; font-size:16px; font-weight:bold !important;">0</td>
                        </tr>
                    </tfoot>
                </table>
            </div>

            <div id="tab-1" class="t-content" style="display:none;">
                <table class="meli-table" style="width: 100%; table-layout: fixed; border-collapse: collapse;">
                    <thead>
                        <tr style="background: linear-gradient(180deg, #0a2e42 0%, #25282b 100%); color: white;">
                            <th style="border-right: 0.5px solid #25282b; padding: 4px 8px; font-size: 14px; color: #25282b !important;">UNIDAD</th>
                            <th colspan="2" style="border-right: 0.5px solid #25282b; padding: 2px; font-size: 11px; color: #25282b !important; width: 105px;">ORH</th>
                            <th style="border-right: 0.5px solid #25282b; padding: 2px; font-size: 11px; color: #25282b !important; width: 45px;">% OCUP</th>
                            <th style="border-right: 0.5px solid #25282b; padding: 2px; font-size: 11px; color: #25282b !important; width: 45px;">SPR<br>MIN</th>
                            <th style="border-right: 0.5px solid #25282b; padding: 2px; font-size: 11px; color: #25282b !important; width: 45px;">SPR<br>MAX</th>
                            <th style="border-right:0.5px solid #25282b; padding:4px 8px; font-size:11px; color: #25282b !important; width:60px;">SCHEDULE</th>
                            <th style="border-right:0.7px solid #25282b; padding:4px 9px; font-size:11px; color:#25282b !important; width:57px; text-align:center; display:table-cell; vertical-align:middle;">USADAS</th>
                            <th style="border-right:0.5px solid #25282b; padding:4px 8px; font-size:11px; color: #25282b !important; width:50px;">DELTA</th>
                        </tr>
                    </thead>
                    <tbody id="body-1">{gen_master_rows(u_PREC, 1)}</tbody>
                    <tfoot class="fila-total">
                        <tr class="fila-total">
                            <td style="border:none;"></td>
                            <td colspan="6" style="padding:6px; text-align:right;">🚛 TOTAL RUTEADAS</td>
                            <td id="total-car-real-1" style="text-align:center; color:#3CB371; font-size:16px; font-weight:bold;">0</td>
                        </tr>
                    </tfoot>
                </table>
            </div>

            <div id="tab-5" class="t-content" style="display:none;">
                <table class="meli-table" style="width: 100%; table-layout: fixed; border-collapse: collapse;">
                    <thead>
                        <tr style="background: linear-gradient(180deg, #0a2e42 0%, #25282b 100%); color: white;">
                            <th style="border-right: 0.5px solid #25282b; padding: 4px 8px; font-size: 14px; color: #25282b !important;">UNIDAD</th>
                            <th colspan="2" style="border-right: 0.5px solid #25282b; padding: 2px; font-size: 11px; color: #25282b !important; width: 105px;">ORH</th>
                            <th style="border-right: 0.5px solid #25282b; padding: 2px; font-size: 11px; color: #25282b !important; width: 45px;">% OCUP</th>
                            <th style="border-right: 0.5px solid #25282b; padding: 2px; font-size: 11px; color: #25282b !important; width: 45px;">SPR<br>MIN</th>
                            <th style="border-right: 0.5px solid #25282b; padding: 2px; font-size: 11px; color: #25282b !important; width: 45px;">SPR<br>MAX</th>
                            <th style="border-right:0.5px solid #25282b; padding:4px 8px; font-size:11px; color: #25282b !important; width:60px;">SCHEDULE</th>
                            <th style="border-right:0.7px solid #25282b; padding:4px 9px; font-size:11px; color:#25282b !important; width:57px; text-align:center; display:table-cell; vertical-align:middle;">USADAS</th>
                            <th style="border-right:0.5px solid #25282b; padding:4px 8px; font-size:11px; color: #25282b !important; width:50px;">DELTA</th>
                        </tr>
                    </thead>
                    <tbody id="body-5">{gen_master_rows(u_PREC_SMX2, 5)}</tbody>
                    <tfoot class="fila-total">
                        <tr class="fila-total">
                            <td style="border:none;"></td>
                            <td colspan="6" style="padding:6px; text-align:right;">🚛 TOTAL RUTEADAS</td>
                            <td id="total-car-real-5" style="text-align:center; color:#3CB371; font-size:16px; font-weight:bold;">0</td>
                        </tr>
                    </tfoot>
                </table>
            </div>

            <div id="tab-4" class="t-content" style="display:none;">
                <table class="meli-table" style="width: 100%; table-layout: fixed; border-collapse: collapse;">
                    <thead>
                        <tr style="background: linear-gradient(180deg, #0a2e42 0%, #25282b 100%); color: white;">
                            <th style="border-right: 0.5px solid #25282b; padding: 4px 8px; font-size: 14px; color: #25282b !important;">UNIDAD</th>
                            <th style="border-right: 0.5px solid #25282b; padding: 2px; font-size: 11px; color: #25282b !important; width: 45px;">SPR<br>MIN</th>
                            <th style="border-right: 0.5px solid #25282b; padding: 2px; font-size: 11px; color: #25282b !important; width: 45px;">SPR<br>MAX</th>
                            <th style="border-right:0.5px solid #25282b; padding:4px 8px; font-size:11px; color: #25282b !important; width:60px;">SCHEDULE</th>
                            <th style="border-right:0.7px solid #25282b; padding:4px 9px; font-size:11px; color:#25282b !important; width:57px; text-align:center; display:table-cell; vertical-align:middle;">USADAS</th>
                            <th style="border-right:0.5px solid #25282b; padding:4px 8px; font-size:11px; color: #25282b !important; width:50px;">DELTA</th>
                        </tr>
                    </thead>
                    <tbody id="body-4">{gen_master_rows(u_SDE, 4)}</tbody>
                    <tfoot class="fila-total">
                        <tr class="fila-total">
                            <td style="border:none;"></td>
                            <td colspan="3" style="padding:6px; text-align:right;">🚛 TOTAL RUTEADAS</td>
                            <td id="total-car-real-4" style="text-align:center; color:#3CB371; font-size:16px; font-weight:bold;">0</td>
                        </tr>
                    </tfoot>
                </table>
            </div>
        </div>

        <button id="toggle-tools-btn" onclick="toggleTools()" 
            style="display: none !important; background:#25282b !important; background-image: none !important; box-shadow: none !important; color: #ffffff !important; border: 1px solid #4682B4; font-size: 11px; padding: 5px 0; border-radius: 3px; font-weight: bold; outline: none; width: 100%; margin-bottom: 15px;">
            ❌ OCULTAR UTILERÍAS
        </button>

        <div style="width:100%; overflow-y:auto; overflow-x:hidden;">
            <div style="background: #25282b !important; background-image: none !important; box-shadow: none !important; border: none !important; color: #20B2AA; padding: 10px; border-radius: 6px; text-align: center; font-weight: bold; margin-top: 50px !important; margin-bottom: 10px !important;">
                📋 PLANIFICACIÓN POR POLÍGONOS
            </div>

            <div id="polys-2" class="p-content">{gen_poligonos(u_C1)}</div>
            <div id="polys-6" class="p-content" style="display:none;">{gen_poligonos(u_C1_SJA1)}</div>
            <div id="polys-7" class="p-content" style="display:none;">{gen_poligonos(u_C1_SCH1)}</div>
            <div id="polys-8" class="p-content" style="display:none;">{gen_poligonos(u_C1_SMD1)}</div>
            <div id="polys-1" class="p-content" style="display:none;">{gen_poligonos(u_PREC)}</div>
            <div id="polys-5" class="p-content" style="display:none;">{gen_poligonos(u_PREC_SMX2)}</div>
            <div id="polys-4" class="p-content" style="display:none;">{gen_poligonos(u_SDE)}</div>

            <div id="excel-polys" style="display:none; margin-top:10px;">
                <div style="background:#25282b; color:white; font-weight:bold; text-align:center; padding:8px; font-size:18px; border:1px solid #0f5b84;">
                    📋 RESUMEN DE POLÍGONOS
                </div>
                <table style="width:100%; border-collapse:collapse; background:white; font-size:16px; table-layout:fixed;">
                    <thead>
                        <tr style="background:#25282b; color:white; height:28px;">
                            <th style="border:1px solid #c0c0c0;">PLAN</th>
                            <th style="border:1px solid #c0c0c0;">VOL</th>
                            <th style="border:1px solid #c0c0c0;">UNIDAD</th>
                            <th style="border:1px solid #c0c0c0; width:55px;">ASIG</th>
                            <th style="border:1px solid #c0c0c0;">ORH / % OCUP</th>
                            <th style="border:1px solid #c0c0c0;">NODO</th>
                        </tr>
                    </thead>
                    <tbody id="excel-polys-body"></tbody>
                </table>
            </div>
        </div>

        <div id="fleet-float" hidden>
            <div style="font-weight:bold; margin-bottom:8px;">🚛 DISPONIBLE</div>
            <div id="fleet-float-body">Cargando...</div>
        </div>

<script>
    const perfiles = {json.dumps(PERFILES)};
    const perfilActual = "{perfil_actual}";

    let currentTab = 2;
    let editedRowsPlan = new Set();
    let curC = "";
    let chronoInterval;
    let startTime;
    let elapsedTime = 0;
    let estadoPaquetesAntesDeExcel = "none";

    // ==============================================================================
    // 🔌 CONEXIÓN SEGURA A SUPABASE EN JS
    // ==============================================================================
    const SUPABASE_URL = "https://srhqffxstkcraqwdxkkz.supabase.co";
    const SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNyaHFmZnhzdGtjcmFxd2R4a2t6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODU5ODIzMzQsImV4cCI6MjEwMTU1ODMzNH0.kWRQfjsw-o6-ZHUGQnENyE-DoQXd1HyV664rBPLXAOk";
    
    let supabaseClient = null;
    try {{
        if (window.supabase && typeof window.supabase.createClient === "function") {{
            supabaseClient = window.supabase.createClient(SUPABASE_URL, SUPABASE_KEY);
        }}
    }} catch(e) {{
        console.error("Error al inicializar Supabase:", e);
    }}

    async function cargarRuteosDesdeSupabase() {{
        if (!supabaseClient) return;
        try {{
            const {{ data, error }} = await supabaseClient
                .from('ruteos_guardados')
                .select('*')
                .order('created_at', {{ ascending: true }});

            if (error) {{
                console.error("Error leyendo de Supabase:", error);
                return;
            }}

            if (data && data.length > 0) {{
                console.log("Ruteos encontrados en Supabase:", data);
            }}
        }} catch (err) {{
            console.error("Excepción al conectar a Supabase:", err);
        }}
    }}

    window.addEventListener("load", function() {{
        setTimeout(cargarRuteosDesdeSupabase, 1000);
    }});

    function cambiarCiclo(valorTab) {{
        document.querySelectorAll('.t-content').forEach(el => {{
            el.style.display = 'none';
        }});
        const tablaActiva = document.getElementById('tab-' + valorTab);
        if (tablaActiva) {{
            tablaActiva.style.display = 'block';
        }}

        document.querySelectorAll('.p-content').forEach(el => {{
            el.style.display = 'none';
        }});
        const polyActivo = document.getElementById('polys-' + valorTab);
        if (polyActivo) {{
            polyActivo.style.display = 'block';
        }}

        currentTab = parseInt(valorTab);
        
        if (typeof recalc === 'function') {{
            recalc();
        }}
    }}

    function aplicarPerfil() {{
        let perfil = perfiles[perfilActual];
        if(!perfil) return;

        Object.keys(perfil).forEach(tabId => {{
            document.querySelectorAll('#body-' + tabId + ' tr').forEach(row => {{
                let unidad = row.querySelector('.edit-name')?.innerText.trim(); 
                if(perfil[tabId][unidad]) {{
                    let data = perfil[tabId][unidad];
                    let orh = row.querySelector('.edit-orh');
                    let disp = row.querySelector('.edit-ocup');

                    if(orh) orh.innerText = data.orh;
                    if(disp) disp.innerText = data.disp;
                }}
            }});
        }});
        recalc();
    }}

    (function initSuma() {{
        const inputs = document.querySelectorAll('.sum-input');
        const totalDisplay = document.getElementById('total-final');

        inputs.forEach(input => {{
            input.addEventListener('input', () => {{
                let sum = 0;
                inputs.forEach(i => {{
                    sum += parseFloat(i.value) || 0;
                }});
                if (totalDisplay) {{
                    totalDisplay.value = sum;
                }}
            }});
        }});
    }})();

    function agregarFilaPlan(btn){{
        const bloque = btn.closest(".poligono-bloque");
        const tbody = bloque.querySelector("tbody");
        const filas = tbody.querySelectorAll(".calc-row");
        const filaBase = filas[0];
        const nuevaFila = filaBase.cloneNode(true);

        nuevaFila.querySelectorAll("[rowspan]").forEach(td => {{
            td.remove();
        }});

        const u = nuevaFila.querySelector(".u-manual");
        if(u) u.innerText = "0";

        const spr = nuevaFila.querySelector(".spr-real-val");
        if(spr) spr.innerText = "0";

        const select = nuevaFila.querySelector(".s-type");
        if(select) select.selectedIndex = 0;

        const check = nuevaFila.querySelector(".ok-check");
        if(check) check.checked = false;

        const estado = tbody.querySelector("tr:last-child");
        tbody.insertBefore(nuevaFila, estado);

        actualizarRowspan(bloque);
        recalc();
    }}

    function quitarFilaPlan(btn){{
        const bloque = btn.closest(".poligono-bloque");
        const tbody = bloque.querySelector("tbody");
        const filas = tbody.querySelectorAll(".calc-row");

        if(filas.length <= 1){{
            return;
        }}

        filas[filas.length - 1].remove();
        actualizarRowspan(bloque);

        const tabla = bloque.querySelector("table");
        if(tabla){{
            tabla.style.width = "100%";
            tabla.style.tableLayout = "fixed";
            void tabla.offsetWidth;
            setTimeout(() => {{
                tabla.style.tableLayout = "fixed";
            }}, 50);
        }}
        recalc();
    }}

    function actualizarContador(bloque){{
        const filas = bloque.querySelectorAll(".calc-row");
        const contador = bloque.querySelector(".contador-filas");
        if(contador){{
            contador.innerText = "Filas: " + filas.length;
        }}
    }}

    function actualizarRowspan(bloque){{
        const filas = bloque.querySelectorAll(".calc-row").length;
        const plan = bloque.querySelector("td.plan-cell");
        const volumen = bloque.querySelector("td.vol-cell");

        if(plan) plan.rowSpan = filas;
        if(volumen) volumen.rowSpan = filas;

        const contador = bloque.querySelector(".contador-filas");
        if(contador){{
            contador.innerText = "Filas: " + filas;
        }}
    }}

    function toggleMenuPestanas() {{
        let panel = document.getElementById("panel-selector-pestanas");
        if (panel) {{
            panel.style.display = (panel.style.display === "none" || panel.style.display === "") ? "block" : "none";
        }}
    }}

    function toggleBtnPestana(btnId, visible) {{
        let btn = document.getElementById(btnId);
        if (btn) {{
            btn.style.display = visible ? "inline-block" : "none";
        }}
    }}

    function toggleFleetFloating() {{
        const panel = document.getElementById("fleet-sticky");
        const btn = document.getElementById("fleet-toggle-btn");
        if (!panel) return;

        const goingToFloat = !panel.classList.contains("fleet-floating");

        if (goingToFloat) {{
            panel.classList.remove("fleet-normal");
            panel.classList.add("fleet-floating");
            if (btn) btn.textContent = "NORMAL (enter)";
        }} else {{
            panel.classList.remove("fleet-floating");
            panel.classList.add("fleet-normal");
            panel.removeAttribute("style");
            if (btn) btn.textContent = "FLOTAR ☁️";
        }}
    }}

    function showTab(n, btn) {{
        const bloqueC1 = document.getElementById('contenedor-paquetes-c1');
        if (bloqueC1) {{
            if (n === 6) {{
                bloqueC1.style.display = 'block';
            }} else {{
                bloqueC1.style.display = 'none';
            }}
        }}

        if (document.body.classList.contains("excel-view")) {{
            document.body.classList.remove("excel-view");
            let bExcel = document.getElementById("excel-btn");
            if (bExcel) bExcel.innerHTML = "👁️";
            
            let excelPanel = document.getElementById("excel-polys");
            if (excelPanel) excelPanel.style.display = "none";
            
            const idsArestaurar = [
                "total-no-car-2", "total-car-schedule-2", "total-car-real-2",
                "total-no-car-6", "total-car-schedule-6", "total-car-real-6",
                "total-no-car-7", "total-car-schedule-7", "total-car-real-7",
                "total-no-car-8", "total-car-schedule-8", "total-car-real-8",
                "total-no-car-1", "total-car-schedule-1", "total-car-real-1",
                "total-no-car-5", "total-car-schedule-5", "total-car-real-5"
            ];
            idsArestaurar.forEach(id => {{
                let el = document.getElementById(id);
                if (el) {{
                    let fila = el.closest('tr');
                    if (fila) fila.style.removeProperty('display');
                }}
            }});
            
            document.querySelectorAll('.meli-table tfoot tr').forEach(fila => {{
                fila.style.setProperty('display', 'table-row', 'important');
            }});
        }}

        currentTab = n;
        document.querySelectorAll('.p-content, .t-content').forEach(el => el.style.display = 'none');
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));

        document.getElementById('polys-' + n).style.display = 'block';
        document.getElementById('tab-' + n).style.display = 'block';

        btn.classList.add('active');

        recalc();
        if (typeof actualizarVisibilidadContador === "function") actualizarVisibilidadContador();
        updateFleetFloat();

        const excelBtn = document.getElementById('excel-btn');
        if (excelBtn) {{
            if (n === 2 || n === 6 || n === 7 || n === 8) {{
                excelBtn.style.setProperty('display', 'inline-block', 'important');
            }} else {{
                excelBtn.style.setProperty('display', 'none', 'important');
            }}
        }}
    }}

    function showAlert(msg) {{
        document.getElementById('alert-msg').innerText = msg;
        document.getElementById('google-alert').classList.add('show');
    }}
    function hideAlert() {{ document.getElementById('google-alert').classList.remove('show'); }}

    function stepVal(btn, delta, type) {{
        let row = btn.closest('tr');
        let sel = row.querySelector('.s-type').value;
        
        if(sel === "Seleccionar..." || !sel) return;

        let fRows = Array.from(document.querySelectorAll('#body-' + currentTab + ' tr'));
        let fRow = fRows.find(r => r.querySelector('.edit-name').innerText.trim() === sel);
        
        if (!fRow) return;

        let left = parseInt(fRow.querySelector('.f-left').innerText) || 0;
        let sprMaxReal = parseFloat(fRow.querySelector('.edit-spr-max').innerText) || 0;

        if(type === 'u') {{
            let span = row.querySelector('.u-manual');
            let val = parseInt(span.innerText) || 0;
            let newVal = val + delta;
            if (newVal < 0) newVal = 0;

            if (delta > 0 && left <= 0) {{
                showAlert("⚠️ UNIDAD ADICIONAL. Se registrará como exceso en Delta.");
            }}
            
            span.innerText = newVal;
        }} else {{
            let span = row.querySelector('.spr-real-val');
            let val = parseFloat(span.innerText) || 0;
            let newVal = Math.round(val + delta);

            if (delta > 0 && newVal > sprMaxReal) {{
                showAlert("⚠️ NO PUEDES SOBREPASAR EL SPR MÁXIMO (" + sprMaxReal + ")");
                return; 
            }}
            
            span.innerText = newVal;
        }}
        editedRowsPlan.add(row);
        recalc();
    }}

    function actualizarHoraMinuto(celda){{
        let valor = celda.innerText.trim().replace(",", ".");
        if(valor === "") valor = "0";

        let numero = parseFloat(valor);
        if(isNaN(numero)) numero = 0;

        let minutosTotales;
        if(valor.includes(".")){{
            minutosTotales = Math.round(numero * 60);
        }} else if(numero >= 24){{
            minutosTotales = Math.round(numero);
        }} else{{
            minutosTotales = Math.round(numero * 60);
        }}

        let horas = Math.floor(minutosTotales / 60);
        let mins = minutosTotales % 60;

        let fila = celda.closest("tr");
        let hm = fila.querySelector(".orh-hora");

        if(hm){{
            hm.style.color = "#141414";
            hm.innerText = String(horas).padStart(2,"0") + ":" + String(mins).padStart(2,"0");
        }}
    }}

    document.querySelectorAll(".edit-orh").forEach(function(celda){{
        actualizarHoraMinuto(celda);
        celda.addEventListener("input", function(){{
            actualizarHoraMinuto(this);
        }});
    }});

    function actualizarDosPorciento() {{
        let volumenTotal = 0;
        document.querySelectorAll('#polys-' + currentTab + ' .v-total-val').forEach(el => {{
            volumenTotal += parseFloat(el.innerText) || 0;
        }});

        let permitido = Math.round(volumenTotal * 0.02);
        let div = document.getElementById('dos-pct-global');

        if (div) {{
            div.innerHTML = `<b>2% PERMITIDO:</b> ${{permitido.toLocaleString()}}`;
        }}
    }}

    function recalc() {{
        let fleet = {{}};
        let tabId = currentTab;

        // 1. Capturar datos de la flota (Tabla de arriba)
        document.querySelectorAll('#body-' + tabId + ' tr').forEach(row => {{
            let nameCell = row.querySelector('.edit-name');
            if (!nameCell) return;
            let name = nameCell.innerText.trim();
            let sch = parseInt(row.querySelector('.f-stock')?.innerText) || 0;
            let mi = row.querySelector('.edit-spr-min'), ma = row.querySelector('.edit-spr-max'), fs = row.querySelector('.f-stock');
            
            if(sch > 0) {{
                row.style.background = "white"; 
                if (fs) fs.style.background = "#fcf8cc"; 
                if (mi) {{ mi.style.background = "#ffffff"; mi.style.color = "#25282b"; mi.style.fontWeight = "bold"; }}
                if (ma) {{ ma.style.background = "#ffffff"; ma.style.color = "#25282b"; ma.style.fontWeight = "bold"; }}
                nameCell.style.color = "#25282b";
                nameCell.style.fontWeight = "bold";
            }} else {{
                row.style.background = "#DCDCDC"; 
                if (fs) fs.style.background = "#FFFF00"; 
                if (mi) {{ mi.style.background = "#dcdcdc"; mi.style.color = "#969696"; mi.style.fontWeight = "normal"; }}
                if (ma) {{ ma.style.background = "#dcdcdc"; ma.style.color = "#969696"; ma.style.fontWeight = "normal"; }}
                nameCell.style.color = "#969696";
                nameCell.style.fontWeight = "normal";
            }}
            
            if(name !== "" && name !== "NUEVA UNIDAD" && name !== "IGNORAR") {{
                fleet[name] = {{ max: parseFloat(ma?.innerText)||0, stock: sch, used: 0 }};
            }}
        }});

        // 2. Mapeo de ruteadas
        let mapeoRuteadas = {{}};
        document.querySelectorAll('#polys-' + tabId + ' .calc-row').forEach(row => {{
            let s = row.querySelector('.s-type')?.value;
            let u = parseInt(row.querySelector('.u-manual')?.innerText) || 0;
            if (s && s !== "Seleccionar...") {{
                mapeoRuteadas[s] = (mapeoRuteadas[s] || 0) + u;
            }}
        }});

        document.querySelectorAll('#body-' + tabId + ' tr').forEach(row => {{
            let nameCell = row.querySelector('.edit-name');
            let ruteadaCell = row.querySelector('.f-ruteadas');
            if (nameCell && ruteadaCell) {{
                let name = nameCell.innerText.trim();
                ruteadaCell.innerText = mapeoRuteadas[name] || 0;
            }}
        }});

        // 3. Recálculo por polígono
        document.querySelectorAll('#polys-' + tabId + ' .poligono-bloque').forEach(bl => {{
            let vT = parseFloat(bl.querySelector('.v-total-val')?.innerText) || 0, vA = 0;
            let vCalcEl = bl.querySelector('.v-calculado-total');

            let nombrePlanPadre = bl.querySelector('td[rowspan]')?.innerText?.toUpperCase()?.trim() || "";
            let esCentro = (nombrePlanPadre === "⚠️ CENTRO 1" || nombrePlanPadre === "⚠️ CENTRO 2");
            
            let celdaNodos = bl.querySelector('.nodos-val');
            let tieneNodo = (tabId == 6 && celdaNodos && parseInt(celdaNodos.innerText) > 0);
            
            let filas = bl.querySelectorAll('.calc-row');

            filas.forEach((r, index) => {{
                let sType = r.querySelector('.s-type');
                let uManual = r.querySelector('.u-manual');
                let sp = r.querySelector('.spr-real-val');
                if (!sType || !uManual || !sp) return;
                
                if (!esCentro && tieneNodo && index === 0 && (sType.value === "" || sType.value === "Seleccionar...")) {{
                    sType.value = "Large Van MLP foráneo";
                    uManual.innerText = "1";
                }}

                if (sType.value === "" || sType.value === "Seleccionar...") {{
                    uManual.innerText = "0";
                }}
                
                let s = sType.value;
                let u = parseInt(uManual.innerText) || 0;

                if (nombrePlanPadre.includes("ALCHICHICA")) {{
                    if (s !== "Seleccionar..." && s !== "") {{
                        vA += (u * (parseFloat(sp.innerText) || 0));
                        sp.style.fontWeight = "bold";
                        sp.style.setProperty("background-color", "#edf2f2");
                        sp.style.setProperty("color", "#25282b");
                    }}
                    return; 
                }}

                if(s !== "Seleccionar..." && s !== "" && fleet[s]) {{
                    if(!editedRowsPlan.has(r)) sp.innerText = fleet[s].max; 
                    fleet[s].used += u; 
                    vA += (u * (parseFloat(sp.innerText) || 0));
                    sp.style.setProperty("background-color", "#edf2f2");
                    sp.style.setProperty("color", "#25282b");
                }} else {{
                    sp.style.setProperty("background-color", "#FFFFFF");
                }}
            }});

            if (vCalcEl) vCalcEl.innerText = Math.round(vA);
            let d = bl.querySelector('.p-diff');
            if (d) {{
                let diffVal = Math.round(vA);
                if (vT === 0) d.innerText = "VACÍO";
                else if (diffVal === Math.round(vT)) {{ d.innerText = "OK"; d.style.background = "#61b888"; }}
                else if (vA > vT) {{ d.innerText = "EXCESO: " + Math.round(vA - vT); d.style.background = "#f2bd5c"; }}
                else {{ d.innerText = "FALTAN: " + Math.round(vT - vA); d.style.background = "#fc9a88"; }}
            }}
        }});

        // 4. Actualización Deltas
        document.querySelectorAll('#body-' + tabId + ' tr').forEach(row => {{
            let nameCell = row.querySelector('.edit-name');
            if (!nameCell) return;
            
            let ruteadasManuales = parseFloat(row.querySelector('.f-ruteadas')?.innerText || 0);
            let stock = parseFloat(row.querySelector('.f-stock')?.innerText || 0);
            let cL = row.querySelector('.f-left');
            
            let ruteadaCell = row.querySelector('.f-ruteadas');
            if (ruteadaCell) {{
                if (ruteadasManuales > 0) {{
                    ruteadaCell.style.backgroundColor = "#d3f0e5";
                    ruteadaCell.style.color = "#008B8B";
                    ruteadaCell.style.fontWeight = "bold";
                }} else {{
                    ruteadaCell.style.backgroundColor = "#dcdcdc";
                    ruteadaCell.style.color = "";
                    ruteadaCell.style.fontWeight = "bold";
                }}
            }}

            if (cL) {{
                let exceso = ruteadasManuales - stock;
                if (exceso > 0) {{
                    cL.innerText = "+" + exceso;
                    cL.style.color = "red"; 
                    cL.style.fontWeight = "bold"; 
                    cL.style.background = "transparent";
                }} else if (ruteadasManuales === stock && stock > 0) {{
                    cL.innerText = "0";
                    cL.style.color = "white"; 
                    cL.style.background = "#fc765d";
                    cL.style.fontWeight = "bold";
                }} else {{
                    let restantes = stock - ruteadasManuales;
                    cL.innerText = restantes;
                    cL.style.color = "#17191a"; 
                    cL.style.background = "transparent"; 
                    cL.style.fontWeight = "normal";
                }}
            }}
        }});

        if (typeof updateFleetFloat === "function") updateFleetFloat();
        if (typeof actualizarDosPorciento === "function") actualizarDosPorciento();
    }}

    document.addEventListener('keydown', function(event) {{
        if (event.key !== 'Enter') return;

        const ae = document.activeElement;
        const tag = ae && ae.tagName ? ae.tagName.toLowerCase() : "";
        if (tag === "button" || tag === "input" || tag === "select" || tag === "textarea") return;
        if (ae && ae.isContentEditable) return;

        const fleet = document.getElementById("fleet-sticky");
        if (fleet && fleet.classList.contains("fleet-floating")) {{
            event.preventDefault();
            if (typeof toggleFleetFloating === "function") toggleFleetFloating();
            return;
        }}

        let panel = document.getElementById('panel-prioridades');
        if (panel && panel.style.top === "0px") {{
            panel.style.top = "-600px";
            if (document.activeElement) document.activeElement.blur();
        }}

        let alerta = document.querySelector('.alerta-roja, .p-diff');
        if (alerta && alerta.innerText.includes('EXCESO')) {{
            if (document.activeElement) document.activeElement.blur();
        }}
    }});

    function focusCalc() {{
        document.getElementById('calc_wrapper').focus();
    }}

    function filterRows(onlyActive) {{
        const rows = document.querySelectorAll('#body-' + currentTab + ' .master-row');
        rows.forEach(row => {{
            const stock = parseInt(row.querySelector('.f-stock').innerText) || 0;
            row.style.display = (onlyActive && stock === 0) ? 'none' : '';
        }});
    }}

    let herramientasVisibles = true;

    function toggleTools() {{
        const crono = document.querySelector('.crono-card');
        const convertidorContenido = document.querySelectorAll('.google-tool > *:not(#toggle-tools-btn)');
        const boton = document.getElementById('toggle-tools-btn');

        herramientasVisibles = !herramientasVisibles;

        if (crono) crono.style.display = herramientasVisibles ? '' : 'none';

        convertidorContenido.forEach(elemento => {{
            elemento.style.display = herramientasVisibles ? '' : 'none';
        }});

        if (!herramientasVisibles) {{
            boton.innerHTML = '🛠️ MOSTRAR UTILERÍAS';
            boton.className = 'btn-mostrar';
        }} else {{
            boton.innerHTML = '❌ OCULTAR UTILERÍAS';
            boton.className = 'btn-ocultar';
        }}
    }}

    function convertTime() {{
        let m = parseInt(document.getElementById('min-in').value) || 0;
        document.getElementById('time-res').innerText = Math.floor(m/60) + "h " + (m%60) + "m";
    }}
    function an(n) {{ curC += n; updateCalc(); }}
    function ao(o) {{ curC += " " + o + " "; updateCalc(); }}
    function cl() {{ curC = ""; updateCalc(); document.getElementById('calc_h').innerText = ""; }}
    function del() {{ curC = curC.trim().slice(0, -1); updateCalc(); }}
    function updateCalc() {{ document.getElementById('calc_r').innerText = curC || "0"; }}
    function calc_eq() {{ try {{ let res = eval(curC); document.getElementById('calc_h').innerText = curC + " ="; curC = res.toString(); updateCalc(); }} catch {{ }} }}

    function updateReloj() {{ document.getElementById('reloj-actual').innerText = new Date().toLocaleTimeString('en-GB'); }}
    setInterval(updateReloj, 1000);

    function startC() {{ if(!chronoInterval) {{ startTime = Date.now() - elapsedTime; chronoInterval = setInterval(()=>{{ elapsedTime = Date.now() - startTime; updateCDisplay(); }}, 100); }} }}
    function stopC() {{ clearInterval(chronoInterval); chronoInterval = null; }}
    function resetC() {{ stopC(); elapsedTime = 0; updateCDisplay(); }}
    function updateCDisplay() {{ 
        let d = new Date(elapsedTime);
        let h = String(Math.floor(elapsedTime/3600000)).padStart(2,'0');
        let m = String(d.getUTCMinutes()).padStart(2,'0');
        let s = String(d.getUTCSeconds()).padStart(2,'0');
        let ms = Math.floor(d.getUTCMilliseconds()/100);
        document.getElementById('crono-main').innerText = `${{h}}:${{m}}:${{s}}.${{ms}}`;
    }}

    function manualEdit(el) {{ 
        let r = el.closest('tr');
        if (r) {{
            editedRowsPlan.add(r);
            let table = r.closest('table');
            let tbody = table ? table.querySelector('tbody') : null;
            let selectType = r.querySelector('.s-type');
            let unidadSeleccionada = selectType ? selectType.value : "";
            
            let permiteInfinito = false;
            let esUnidadCar = unidadSeleccionada.toLowerCase().includes("car");

            let activeTabBtn = document.querySelector('.tab-btn.active');
            if (activeTabBtn) {{
                let tabId = activeTabBtn.textContent.trim();
                
                if ((currentTab === 7 || currentTab === 8) && unidadSeleccionada.trim() === "CAR 8H") {{
                    permiteInfinito = true;
                }} else if (tabId === "C1 SCP1" && unidadSeleccionada.trim() === "Large Van MLP") {{
                    permiteInfinito = true;
                }} else if ((tabId === "SDE" || tabId === "PREC") && esUnidadCar) {{
                    permiteInfinito = true;
                }}
            }}

            if (permiteInfinito && tbody) {{
                let filasCalculo = tbody.querySelectorAll('tr.calc-row');
                let ultimaFila = filasCalculo[filasCalculo.length - 1];
                
                if (r === ultimaFila) {{
                    let nuevaFila = r.cloneNode(true);
                    let nuevoSelect = nuevaFila.querySelector('.s-type');
                    if (nuevoSelect) {{
                        nuevoSelect.value = "";
                        nuevoSelect.style.color = "#808080";
                    }}
                    let nuevoSpanU = nuevaFila.querySelector('.u-manual');
                    if (nuevoSpanU) nuevoSpanU.innerText = "0";
                    let nuevoSpanS = nuevaFila.querySelector('.spr-real-val');
                    if (nuevoSpanS) nuevoSpanS.innerText = "0";
                    let nuevoCheck = nuevaFila.querySelector('.ok-check');
                    if (nuevoCheck) nuevoCheck.checked = false;

                    tbody.appendChild(nuevaFila);
                }}
            }}
        }}
        recalc(); 
    }}

    function resetRow(sel) {{ 
        let r = sel.closest('tr');
        if (!r) return;
        let table = sel.closest('table');
        if (!table) return;

        let tbody = table.querySelector('tbody');
        let unidadSeleccionada = sel.value;

        if (unidadSeleccionada === "") {{
            r.querySelector('.u-manual').innerText = "0";
            r.querySelector('.spr-real-val').innerText = "0";
            editedRowsPlan.delete(r);
            recalc();
            return;
        }}

        let volTotalSpan = table.querySelector('.v-total-val');
        let volumenTotal = volTotalSpan ? parseFloat(volTotalSpan.textContent) || 0 : 0;

        let sprEncontrado = 0;
        let stockInicialFlota = 0;
        let totalUnidadesUsadasEnEstaPestana = 0;
        
        let filasFlota = document.querySelectorAll('#body-' + currentTab + ' .master-row');
        for (let filaFlota of filasFlota) {{
            let celdaNombre = filaFlota.querySelector('.edit-name');
            if (celdaNombre && celdaNombre.innerText.trim() === unidadSeleccionada.trim()) {{
                let celdaSprMax = filaFlota.querySelector('.edit-spr-max');
                let celdaStock = filaFlota.querySelector('.f-stock');
                
                if (celdaSprMax) sprEncontrado = parseFloat(celdaSprMax.innerText) || 0;
                if (celdaStock) stockInicialFlota = parseInt(celdaStock.innerText) || 0;
                break;
            }}
        }}

        let spanS = r.querySelector('.spr-real-val');
        if (spanS) spanS.innerText = sprEncontrado;

        let volumenYaCubierto = 0;
        let todasLasFilasPlan = tbody.querySelectorAll('tr.calc-row');
        
        todasLasFilasPlan.forEach(filaPlan => {{
            if (filaPlan !== r) {{
                let u = parseInt(filaPlan.querySelector('.u-manual').innerText) || 0;
                let spr = parseFloat(filaPlan.querySelector('.spr-real-val').innerText) || 0;
                volumenYaCubierto += (u * spr);
            }}
        }});

        let volumenRestantePlan = volumenTotal - volumenYaCubierto;
        if (volumenRestantePlan < 0) volumenRestantePlan = 0;

        document.querySelectorAll('#polys-' + currentTab + ' .calc-row').forEach(fGlobal => {{
            if (fGlobal !== r) {{
                let t = fGlobal.querySelector('.s-type')?.value || "";
                if (t.trim() === unidadSeleccionada.trim()) {{
                    totalUnidadesUsadasEnEstaPestana += parseInt(fGlobal.querySelector('.u-manual').innerText) || 0;
                }}
            }}
        }});

        let inventarioDisponibleReal = stockInicialFlota - totalUnidadesUsadasEnEstaPestana;
        if (inventarioDisponibleReal < 0) inventarioDisponibleReal = 0;

        let unidadesCalculadas = 0;
        
        if (unidadSeleccionada.trim() === "Delivery Cell Large Van") {{
            unidadesCalculadas = 1;
        }} else if (volumenRestantePlan > 0 && sprEncontrado > 0) {{
            unidadesCalculadas = Math.ceil(volumenRestantePlan / sprEncontrado);
            let permiteInfinito = false;
            let esUnidadCar = unidadSeleccionada.toLowerCase().includes("car");
            let activeTabBtn = document.querySelector('.tab-btn.active');
            
            if (activeTabBtn) {{
                let tabId = activeTabBtn.textContent.trim();
                if ((currentTab === 7 || currentTab === 8) && unidadSeleccionada.trim() === "CAR 8H") {{
                    permiteInfinito = true;
                }} else if (tabId === "C1 SCP1" && unidadSeleccionada.trim() === "Large Van MLP") {{
                    permiteInfinito = true;
                }} else if ((currentTab === 1 || currentTab === 5 || currentTab === 4) && esUnidadCar) {{
                    if (unidadSeleccionada.trim() !== "Small 9h Ext Car") {{
                        permiteInfinito = true;
                    }}
                }}
            }}

            if (!permiteInfinito) {{
                if (unidadesCalculadas > inventarioDisponibleReal) {{
                    unidadesCalculadas = inventarioDisponibleReal;
                    if (unidadesCalculadas === 0) {{
                        showAlert("⚠️ FLOTA AGOTADA. No quedan unidades disponibles de: " + unidadSeleccionada);
                    }} else {{
                        showAlert("⚠️ FLOTA INSUFICIENTE. Se asignaron las últimas " + unidadesCalculadas + " unidades para amortiguar el volumen.");
                    }}
                }}
            }}
        }}

        let spanU = r.querySelector('.u-manual');
        if (spanU) spanU.innerText = unidadesCalculadas;

        let permiteInfinitoFila = false;
        let esUnidadCarFila = unidadSeleccionada.toLowerCase().includes("car");
        let activeTabBtnFila = document.querySelector('.tab-btn.active');
        
        if (activeTabBtnFila) {{
            let tabId = activeTabBtnFila.textContent.trim();
            if (tabId === "C1 SCP1" && unidadSeleccionada.trim() === "Large Van MLP") {{
                permiteInfinitoFila = true;
            }} else if ((currentTab === 1 || currentTab === 5 || currentTab === 4) && esUnidadCarFila) {{
                if (unidadSeleccionada.trim() !== "Small 9h Ext Car") {{
                    permiteInfinitoFila = true;
                }}
            }}
        }}

        if (permiteInfinitoFila && tbody) {{
            let filasCalculo = tbody.querySelectorAll('tr.calc-row');
            let ultimaFila = filasCalculo[filasCalculo.length - 1];
            
            if (r === ultimaFila) {{
                let nuevaFila = r.cloneNode(true);
                let nuevoSelect = nuevaFila.querySelector('.s-type');
                if (nuevoSelect) {{
                    nuevoSelect.value = "";
                    nuevoSelect.style.color = "#808080";
                }}
                let nuevoSpanU = nuevaFila.querySelector('.u-manual');
                if (nuevoSpanU) nuevoSpanU.innerText = "0";
                let nuevoSpanS = nuevaFila.querySelector('.spr-real-val');
                if (nuevoSpanS) nuevoSpanS.innerText = "0";
                let nuevoCheck = nuevaFila.querySelector('.ok-check');
                if (nuevoCheck) nuevoCheck.checked = false;

                tbody.appendChild(nuevaFila);
            }}
        }}

        if (typeof manualEdit === 'function' && spanU) {{
            manualEdit(spanU);
        }} else {{
            recalc();
        }}
    }}

    document.addEventListener('keydown', (e) => {{
        const calc = document.getElementById('calc_wrapper');
        const alerta = document.getElementById('google-alert');

        if (e.key === 'Enter' && alerta.classList.contains('show')) {{
            e.preventDefault();
            e.stopPropagation();
            hideAlert();
            return;
        }}

        if (document.activeElement === calc) {{
            if (e.key >= '0' && e.key <= '9') an(e.key);
            if (e.key === '+') ao('+');
            if (e.key === '-') ao('-');
            if (e.key === '*') ao('*');
            if (e.key === '/') {{ e.preventDefault(); ao('/'); }}
            if (e.key === 'Enter') {{ e.preventDefault(); calc_eq(); }}
            if (e.key === 'Escape') cl();
            if (e.key === 'Backspace') del();
        }}
    }});

    function toggleExcelView() {{
        const isExcel = !document.body.classList.contains("excel-view");
        document.body.classList.toggle("excel-view", isExcel);
        
        let btn = document.getElementById("excel-btn");
        let excel = document.getElementById("excel-polys");
        let bPaquetes = document.getElementById("contenedor-paquetes-c1");
        
        const idsAocultar = [
            "total-no-car-2", "total-car-schedule-2", "total-car-real-2",
            "total-no-car-6", "total-car-schedule-6", "total-car-real-6",
            "total-no-car-7", "total-car-schedule-7", "total-car-real-7",
            "total-no-car-8", "total-car-schedule-8", "total-car-real-8",
            "total-no-car-1", "total-car-schedule-1", "total-car-real-1",
            "total-no-car-5", "total-car-schedule-5", "total-car-real-5"
        ];
        if (isExcel) {{
            if (bPaquetes) {{
                estadoPaquetesAntesDeExcel = bPaquetes.style.display;
                bPaquetes.style.display = "none";
            }}
            
            generarExcelPolys();
            btn.innerHTML = "N";
            if(excel) excel.style.display = "block";
            
            ["polys-1", "polys-2", "polys-4", "polys-5", "polys-6", "polys-7", "polys-8"].forEach(id => {{
                let el = document.getElementById(id);
                if(el) el.style.display = "none";
            }});
            idsAocultar.forEach(id => {{
                let el = document.getElementById(id);
                if(el) {{
                    let fila = el.closest('tr');
                    if(fila) fila.style.display = 'none';
                }}
            }});
        }} else {{
            if (bPaquetes) {{
                bPaquetes.style.display = estadoPaquetesAntesDeExcel;
            }}
            
            btn.innerHTML = "👁️";
            if(excel) excel.style.display = "none";
            
            ["polys-1", "polys-2", "polys-4", "polys-5", "polys-6", "polys-7", "polys-8"].forEach(id => {{
                let el = document.getElementById(id);
                if(el) el.style.display = (id === "polys-" + currentTab) ? "block" : "none";
            }});
            
            if (contScp1 && contSja1) {{
                if (currentTab == 2) {{
                    contScp1.style.display = 'block';
                    contSja1.style.display = 'none';
                }} else if (currentTab == 6) {{
                    contScp1.style.display = 'none';
                    contSja1.style.display = 'block';
                }} else {{
                    contScp1.style.display = 'none';
                    contSja1.style.display = 'none';
                }}
            }}

            idsAocultar.forEach(id => {{
                let el = document.getElementById(id);
                if(el) {{
                    let fila = el.closest('tr');
                    if(fila) fila.style.removeProperty('display');
                }}
            }});
            document.querySelectorAll('.meli-table tfoot tr').forEach(fila => {{
                fila.style.setProperty('display', 'table-row', 'important');
                actualizarVisibilidadContador();
            }});
        }}
    }}

    function generarExcelPolys() {{
        let body = document.getElementById("excel-polys-body");
        if(!body) return;

        body.innerHTML = "";
        let tabId = currentTab;
        document.querySelectorAll('#polys-' + tabId + ' .poligono-bloque').forEach(bl => {{
            let plan = bl.querySelector('tbody tr td')?.innerText.trim() || "";
            let vol = bl.querySelector('.v-total-val')?.innerText.trim() || "0";

            let nodoExcel = bl.querySelector('.nodos-val')?.innerText.trim() ||
                            bl.querySelector('.nodos-campeche')?.innerText.trim() || "0";
            let nodoTxt = (parseInt(nodoExcel) || 0) > 0 ? nodoExcel : "-";

            let filasCalc = Array.from(bl.querySelectorAll('.calc-row'));
            let filasValidas = filasCalc.filter(r => {{
                let u = r.querySelector('.s-type')?.value || "";
                return u !== "" && u !== "Seleccionar...";
            }});

            if (filasValidas.length === 0) return;

            filasValidas.forEach((r, index) => {{
                let unidad = r.querySelector('.s-type')?.value || "";
                let asignadas = r.querySelector('.u-manual')?.innerText.trim() || "0";

                let fRows = Array.from(document.querySelectorAll('#body-' + tabId + ' tr'));
                let fRow = fRows.find(fr => fr.querySelector('.edit-name')?.innerText.trim() === unidad);
                let valSpr = "-";

                if (fRow) {{
                    let orh  = fRow.querySelector(".edit-orh")?.innerText.trim() || "0";
                    let ocup = fRow.querySelector(".edit-ocup")?.innerText.trim() || "0";
                    valSpr = orh + " / " + ocup;
                }}

                let filaHtml = '<tr>';
                if (index === 0) {{
                    filaHtml += `
                        <td rowspan="${{filasValidas.length}}" style="border:1px solid #808080; padding:3px; text-align:center; font-weight:bold; vertical-align:middle;">${{plan}}</td>
                        <td rowspan="${{filasValidas.length}}" style="border:1px solid #808080; text-align:center; font-weight:bold; vertical-align:middle;">${{vol}}</td>
                    `;
                }}
                filaHtml += `
                    <td style="border:1px solid #808080; padding-left:6px; vertical-align:middle;">${{unidad}}</td>
                    <td style="border:1px solid #808080; text-align:center; vertical-align:middle; font-weight:bold;">${{asignadas}}</td>
                    <td style="border:1px solid #808080; text-align:center; vertical-align:middle;">${{valSpr}}</td>
                `;
                if (index === 0) {{
                    filaHtml += `<td rowspan="${{filasValidas.length}}" style="border:1px solid #808080; text-align:center; font-weight:bold; vertical-align:middle;">${{nodoTxt}}</td>`;
                }}
                filaHtml += '</tr>';
                body.innerHTML += filaHtml;
            }});
        }});

        let valRuteadasNormal = document.getElementById('total-ruteadas-' + tabId)?.innerText || "0";
        let celdaTotalExcel = document.getElementById('excel-total-ruteadas-naranja');
        if(celdaTotalExcel) celdaTotalExcel.innerText = valRuteadasNormal;

        let tablaActual = document.querySelector('#tab-' + tabId + ' table');
        if (tablaActual) {{
            let filasFooter = tablaActual.querySelectorAll('tfoot tr');
            filasFooter.forEach(fila => {{
                if (!fila.innerText.includes("TOTAL RUTEADAS")) {{
                    fila.style.display = 'none';
                }}
            }});
        }}
    }}

    function obtenerCarFlexible() {{
        const opciones = ["Car - 8h", "Car - 5h", "Car - 3h"];
        for (let nombre of opciones) {{
            let unidad = fleet.find(f => f.nombre === nombre && f.stock > 0);
            if (unidad) return unidad;
        }}
        return null;
    }}

    function distribuirAutomatico() {{
        let fleet = [];
        document.querySelectorAll('#body-' + currentTab + ' tr').forEach(row => {{
            let nombre = row.querySelector('.edit-name')?.innerText.trim();
            let sprMax = parseFloat(row.querySelector('.edit-spr-max')?.innerText) || 0;
            let stock = parseInt(row.querySelector('.f-stock')?.innerText) || 0;

            if (nombre && nombre !== "IGNORAR" && stock > 0) {{
                fleet.push({{
                    nombre: nombre,
                    spr: sprMax,
                    stock: stock,
                    restante: stock
                }});
            }}
        }});

        document.querySelectorAll('#polys-' + currentTab + ' .calc-row').forEach(r => {{
            let tipo = r.querySelector('.s-type')?.value;
            let unidades = parseInt(r.querySelector('.u-manual')?.innerText) || 0;

            if (tipo && tipo !== "Seleccionar..." && unidades > 0) {{
                let unidadReal = fleet.find(f => f.nombre === tipo);
                if (unidadReal) {{
                    unidadReal.restante -= unidades;
                }}
            }}
        }});

        console.log("FLEET DISPONIBLE EN PESTAÑA ACTIVA:", fleet.map(f => f.nombre));
        fleet.sort((a, b) => b.spr - a.spr);

        let bloques = Array.from(document.querySelectorAll('#polys-' + currentTab + ' .poligono-bloque'));
        let polys = [];

        bloques.forEach(bl => {{
            let volumen = parseFloat(bl.querySelector('.v-total-val')?.innerText) || 0;
            if (volumen > 0) {{
                polys.push({{
                    bloque: bl,
                    volumen: volumen
                }});
            }}
        }});

        if (currentTab == 1) {{
            let small9h = fleet.find(f => f.nombre === "Small 9h Ext Car");
            if (small9h && small9h.restante > 0) {{
                let planesPrioridad = ["IZTAPALAPA", "COYOACÁN"];
                planesPrioridad.forEach(nombreBuscado => {{
                    let polyPlan = polys.find(p => (p.bloque.querySelector('td[rowspan]')?.innerText?.trim()?.toUpperCase() || "") === nombreBuscado);
                    if (!polyPlan) return;

                    let objetivo = parseFloat(polyPlan.bloque.querySelector('.v-total-val')?.innerText) || 0;
                    let yaAsignado = 0;
                    polyPlan.bloque.querySelectorAll('.calc-row').forEach(r => {{
                        yaAsignado += (parseInt(r.querySelector('.u-manual')?.innerText) || 0) * (parseFloat(r.querySelector('.spr-real-val')?.innerText) || 0);
                    }});

                    let restante = objetivo - yaAsignado;
                    if (restante <= 0) return;

                    let usar = Math.min(Math.ceil(restante / small9h.spr), small9h.restante);
                    if (usar <= 0) return;

                    let filaLibre = Array.from(polyPlan.bloque.querySelectorAll('.calc-row')).find(f => {{
                        let tipo = f.querySelector('.s-type')?.value?.trim() || "";
                        let unidades = parseInt(f.querySelector('.u-manual')?.innerText) || 0;
                        return unidades === 0 && (tipo === "" || tipo === "Seleccionar...");
                    }});

                    if (filaLibre) {{
                        filaLibre.querySelector('.s-type').value = small9h.nombre;
                        filaLibre.querySelector('.u-manual').innerText = usar;
                        filaLibre.querySelector('.spr-real-val').innerText = small9h.spr;
                        editedRowsPlan.add(filaLibre);
                        small9h.restante -= usar;
                    }}
                }});

                if (small9h.restante > 0) {{
                    polys.forEach(polyPlan => {{
                        if (small9h.restante <= 0) return;
                        let nombrePlan = polyPlan.bloque.querySelector('td[rowspan]')?.innerText?.trim()?.toUpperCase() || "";
                        if (nombrePlan !== "TLAHUAC") return;

                        let objetivo = parseFloat(polyPlan.bloque.querySelector('.v-total-val')?.innerText) || 0;
                        let yaAsignado = 0;
                        polyPlan.bloque.querySelectorAll('.calc-row').forEach(r => {{
                            yaAsignado += (parseInt(r.querySelector('.u-manual')?.innerText) || 0) * (parseFloat(r.querySelector('.spr-real-val')?.innerText) || 0);
                        }});

                        let restante = objetivo - yaAsignado;
                        if (restante <= 0) return;

                        let usar = Math.min(Math.ceil(restante / small9h.spr), small9h.restante);
                        if (usar <= 0) return;

                        let filaLibre = Array.from(polyPlan.bloque.querySelectorAll('.calc-row')).find(f => {{
                            let tipo = f.querySelector('.s-type')?.value?.trim() || "";
                            let unidades = parseInt(f.querySelector('.u-manual')?.innerText) || 0;
                            return unidades === 0 && (tipo === "" || tipo === "Seleccionar...");
                        }});

                        if (filaLibre) {{
                            filaLibre.querySelector('.s-type').value = small9h.nombre;
                            filaLibre.querySelector('.u-manual').innerText = usar;
                            filaLibre.querySelector('.spr-real-val').innerText = small9h.spr;
                            editedRowsPlan.add(filaLibre);
                            small9h.restante -= usar;
                        }}
                    }});
                }}
            }}
        }}

        if (currentTab == 5) {{
            let smallVan = fleet.find(f => f.nombre === "Small Van SDD");
            if (smallVan && smallVan.restante > 0) {{
                let planesPrioridad = ["IZTAPALAPA 1", "IZTAPALAPA 2", "LA PAZ"];
                planesPrioridad.forEach(nombreBuscado => {{
                    let polyPlan = polys.find(p => (p.bloque.querySelector('td[rowspan]')?.innerText?.trim()?.toUpperCase() || "") === nombreBuscado);
                    if (!polyPlan) return;

                    let objetivo = parseFloat(polyPlan.bloque.querySelector('.v-total-val')?.innerText) || 0;
                    let yaAsignado = 0;
                    polyPlan.bloque.querySelectorAll('.calc-row').forEach(r => {{
                        yaAsignado += (parseInt(r.querySelector('.u-manual')?.innerText) || 0) * (parseFloat(r.querySelector('.spr-real-val')?.innerText) || 0);
                    }});

                    let restante = objetivo - yaAsignado;
                    if (restante <= 0) return;

                    let usar = Math.min(Math.ceil(restante / smallVan.spr), smallVan.restante);
                    if (usar <= 0) return;

                    let filaLibre = Array.from(polyPlan.bloque.querySelectorAll('.calc-row')).find(f => {{
                        let tipo = f.querySelector('.s-type')?.value?.trim() || "";
                        let unidades = parseInt(f.querySelector('.u-manual')?.innerText) || 0;
                        return unidades === 0 && (tipo === "" || tipo === "Seleccionar...");
                    }});

                    if (filaLibre) {{
                        filaLibre.querySelector('.s-type').value = smallVan.nombre;
                        filaLibre.querySelector('.u-manual').innerText = usar;
                        filaLibre.querySelector('.spr-real-val').innerText = smallVan.spr;
                        editedRowsPlan.add(filaLibre);
                        smallVan.restante -= usar;
                    }}
                }});

                if (smallVan.restante > 0) {{
                    polys.forEach(polyPlan => {{
                        if (smallVan.restante <= 0) return;
                        let nombrePlan = polyPlan.bloque.querySelector('td[rowspan]')?.innerText?.trim()?.toUpperCase() || "";
                        if (!nombrePlan.includes("CHIMAS")) return;

                        let objetivo = parseFloat(polyPlan.bloque.querySelector('.v-total-val')?.innerText) || 0;
                        let yaAsignado = 0;
                        polyPlan.bloque.querySelectorAll('.calc-row').forEach(r => {{
                            yaAsignado += (parseInt(r.querySelector('.u-manual')?.innerText) || 0) * (parseFloat(r.querySelector('.spr-real-val')?.innerText) || 0);
                        }});

                        let restante = objetivo - yaAsignado;
                        if (restante <= 0) return;

                        let usar = Math.min(Math.ceil(restante / smallVan.spr), smallVan.restante);
                        if (usar <= 0) return;

                        let filaLibre = Array.from(polyPlan.bloque.querySelectorAll('.calc-row')).find(f => {{
                            let tipo = f.querySelector('.s-type')?.value?.trim() || "";
                            let unidades = parseInt(f.querySelector('.u-manual')?.innerText) || 0;
                            return unidades === 0 && (tipo === "" || tipo === "Seleccionar...");
                        }});

                        if (filaLibre) {{
                            filaLibre.querySelector('.s-type').value = smallVan.nombre;
                            filaLibre.querySelector('.u-manual').innerText = usar;
                            filaLibre.querySelector('.spr-real-val').innerText = smallVan.spr;
                            editedRowsPlan.add(filaLibre);
                            smallVan.restante -= usar;
                        }}
                    }});
                }}
            }}

            let CarZonaExtendida = fleet.find(f => f.nombre === "Car Zona Extendida");
            if (CarZonaExtendida && CarZonaExtendida.restante > 0) {{
                let planesPrioridad = ["PUEBLOS", "TEXCOCO"];
                planesPrioridad.forEach(nombreBuscado => {{
                    let polyPlan = polys.find(p => (p.bloque.querySelector('td[rowspan]')?.innerText?.trim()?.toUpperCase() || "") === nombreBuscado);
                    if (!polyPlan) return;

                    let objetivo = parseFloat(polyPlan.bloque.querySelector('.v-total-val')?.innerText) || 0;
                    let yaAsignado = 0;
                    polyPlan.bloque.querySelectorAll('.calc-row').forEach(r => {{
                        yaAsignado += (parseInt(r.querySelector('.u-manual')?.innerText) || 0) * (parseFloat(r.querySelector('.spr-real-val')?.innerText) || 0);
                    }});

                    let restante = objetivo - yaAsignado;
                    if (restante <= 0) return;

                    let usar = Math.min(Math.ceil(restante / CarZonaExtendida.spr), CarZonaExtendida.restante);
                    if (usar <= 0) return;

                    let filaLibre = Array.from(polyPlan.bloque.querySelectorAll('.calc-row')).find(f => {{
                        let tipo = f.querySelector('.s-type')?.value?.trim() || "";
                        let unidades = parseInt(f.querySelector('.u-manual')?.innerText) || 0;
                        return unidades === 0 && (tipo === "" || tipo === "Seleccionar...");
                    }});

                    if (filaLibre) {{
                        filaLibre.querySelector('.s-type').value = CarZonaExtendida.nombre;
                        filaLibre.querySelector('.u-manual').innerText = usar;
                        filaLibre.querySelector('.spr-real-val').innerText = CarZonaExtendida.spr;
                        editedRowsPlan.add(filaLibre);
                        CarZonaExtendida.restante -= usar;
                    }}
                }});

                if (CarZonaExtendida.restante > 0) {{
                    let chalco = polys.find(p => (p.bloque.querySelector('td[rowspan]')?.innerText?.trim()?.toUpperCase() || "") === "CHALCO");
                    if (chalco) {{
                        let filaLibre = Array.from(chalco.bloque.querySelectorAll('.calc-row')).find(f => {{
                            let tipo = f.querySelector('.s-type')?.value?.trim() || "";
                            let unidades = parseInt(f.querySelector('.u-manual')?.innerText) || 0;
                            return unidades === 0 && (tipo === "" || tipo === "Seleccionar...");
                        }});
                        if (filaLibre) {{
                            filaLibre.querySelector('.s-type').value = CarZonaExtendida.nombre;
                            filaLibre.querySelector('.u-manual').innerText = CarZonaExtendida.restante;
                            filaLibre.querySelector('.spr-real-val').innerText = CarZonaExtendida.spr;
                            editedRowsPlan.add(filaLibre);
                            CarZonaExtendida.restante = 0;
                        }}
                    }}
                }}
            }}
        }}

        if (currentTab == 2) {{
            let largeVanMLP = fleet.find(f => f.nombre === "Large Van MLP");
            if (largeVanMLP && largeVanMLP.restante > 0) {{
                let planesPrioridad = ["ESCÁRCEGA", "ESCÁRCEGA EXT", "MAXCANUN", "CANDELARIA", "SEYBAPLAYA", "CHAMPOTÓN", "HOLPECHEN"];
                planesPrioridad.forEach(nombreBuscado => {{
                    let polyPlan = polys.find(p => (p.bloque.querySelector('td[rowspan]')?.innerText?.trim()?.toUpperCase() || "") === nombreBuscado);
                    if (!polyPlan) return;

                    let objetivo = parseFloat(polyPlan.bloque.querySelector('.v-total-val')?.innerText) || 0;
                    let yaAsignado = 0;
                    polyPlan.bloque.querySelectorAll('.calc-row').forEach(r => {{
                        yaAsignado += (parseInt(r.querySelector('.u-manual')?.innerText) || 0) * (parseFloat(r.querySelector('.spr-real-val')?.innerText) || 0);
                    }});

                    let restante = objetivo - yaAsignado;
                    if (restante <= 0) return;

                    let usar = Math.min(Math.ceil(restante / largeVanMLP.spr), largeVanMLP.restante);
                    if (usar <= 0) return;

                    let filaLibre = Array.from(polyPlan.bloque.querySelectorAll('.calc-row')).find(f => {{
                        let tipo = f.querySelector('.s-type')?.value?.trim() || "";
                        let unidades = parseInt(f.querySelector('.u-manual')?.innerText) || 0;
                        return unidades === 0 && (tipo === "" || tipo === "Seleccionar...");
                    }});

                    if (filaLibre) {{
                        filaLibre.querySelector('.s-type').value = largeVanMLP.nombre;
                        filaLibre.querySelector('.u-manual').innerText = usar;
                        filaLibre.querySelector('.spr-real-val').innerText = largeVanMLP.spr;
                        editedRowsPlan.add(filaLibre);
                        largeVanMLP.restante -= usar;
                    }}
                }});
            }}

            let deliveryCell = fleet.find(f => f.nombre === "Delivery Cell Large Van");
            if (deliveryCell && deliveryCell.restante > 0) {{
                let campeche = polys.find(p => (p.bloque.querySelector('td[rowspan]')?.innerText?.trim()?.toUpperCase() || "") === "CAMPECHE");
                if (campeche) {{
                    let nodos = parseInt(campeche.bloque.querySelector('.nodos-campeche')?.innerText) || 0;
                    if (nodos > 0) {{
                        let filaLibre = Array.from(campeche.bloque.querySelectorAll('.calc-row')).find(f => {{
                            let tipo = f.querySelector('.s-type')?.value?.trim() || "";
                            let unidades = parseInt(f.querySelector('.u-manual')?.innerText) || 0;
                            return unidades === 0 && (tipo === "" || tipo === "Seleccionar...");
                        }});
                        if (filaLibre) {{
                            filaLibre.querySelector('.s-type').value = deliveryCell.nombre;
                            filaLibre.querySelector('.u-manual').innerText = 1;
                            filaLibre.querySelector('.spr-real-val').innerText = deliveryCell.spr;
                            editedRowsPlan.add(filaLibre);
                            deliveryCell.restante -= 1;
                        }}
                    }}
                }}
            }}
        }}

        if (currentTab == 6) {{
            polys.forEach(poly => {{
                procesarAsignacionUnidadSJA1(poly);
            }});
        }} else {{
            polys.forEach(poly => {{
                let bloque = poly.bloque;
                let nombrePlan = bloque.querySelector('td[rowspan]')?.innerText?.toUpperCase()?.trim() || "";
                let objetivo = parseFloat(bloque.querySelector('.v-total-val')?.innerText) || 0;

                let yaAsignado = 0;
                bloque.querySelectorAll('.calc-row').forEach(r => {{
                    yaAsignado += (parseInt(r.querySelector('.u-manual')?.innerText) || 0) * (parseFloat(r.querySelector('.spr-real-val')?.innerText) || 0);
                }});

                let restante = objetivo - yaAsignado;
                if (restante <= 0) return;

                let filas = Array.from(bloque.querySelectorAll('.calc-row'));
                for (let fila of filas) {{
                    let yaTieneUnidad = parseInt(fila.querySelector('.u-manual')?.innerText) > 0;
                    let tipoActual = fila.querySelector('.s-type')?.value?.trim() || "";
                    let yaTieneTipo = tipoActual !== "" && tipoActual !== "Seleccionar...";

                    if (yaTieneUnidad || yaTieneTipo) continue;
                    if (restante <= 0) break;

                    let unidad = null;

                    if (currentTab == 2 && nombrePlan == "CAMPECHE") {{
                        unidad = fleet.find(f => f.nombre === "Rental Large Van");
                    }} else if (currentTab == 2) {{
                        unidad = fleet.find(f => f.restante > 0 && f.nombre !== "Rental Large Van");
                    }} else {{
                        unidad = fleet.find(f => f.restante > 0);
                    }}

                    if (!unidad) {{
                        if (currentTab == 4) {{
                            let options = ["Car - 5h", "Car - 3h"];
                            for (let opt of options) {{
                                unidad = fleet.find(f => f.nombre.includes(opt));
                                if (unidad) break;
                            }}
                        }} else if (currentTab == 7) {{
                            let options = ["Car - 8h"];
                            for (let opt of options) {{
                                unidad = fleet.find(f => f.nombre.includes(opt));
                                if (unidad) break;
                            }}
                        }} else if (currentTab == 8) {{
                            let options = ["Car - 8h"];
                            for (let opt of options) {{
                                unidad = fleet.find(f => f.nombre.includes(opt));
                                if (unidad) break;
                            }}
                        }} else if (currentTab == 2) {{
                            let options = ["Large Van MLP", "Car - 8h", "Car - 5h"];
                            for (let opt of options) {{
                                unidad = fleet.find(f => f.nombre.includes(opt));
                                if (unidad) break;
                            }}
                        }} else if (currentTab == 1 || currentTab == 5) {{
                            let options = ["Car - 8h", "Car - 5h"];
                            for (let opt of options) {{
                                unidad = fleet.find(f => f.nombre.includes(opt));
                                if (unidad) break;
                            }}
                        }}
                        if (!unidad) break;
                    }}

                    let necesarias = Math.ceil(restante / unidad.spr);
                    let usar;

                    let permiteNegativo = unidad.nombre === "Car - 8h" || unidad.nombre === "Car - 5h" || unidad.nombre === "Car - 3h" || (currentTab == 2 && unidad.nombre === "Large Van MLP");
                    if (unidad.restante > 0) {{
                        usar = Math.min(necesarias, unidad.restante);
                    }} else if (permiteNegativo) {{
                        usar = necesarias;
                    }} else {{
                        usar = 0;
                    }}

                    if (usar <= 0) continue;

                    let filaExistente = filas.find(f => f.querySelector('.s-type')?.value === unidad.nombre);
                    if (filaExistente) {{
                        let actual = parseInt(filaExistente.querySelector('.u-manual')?.innerText) || 0;
                        filaExistente.querySelector('.u-manual').innerText = actual + usar;
                        filaExistente.querySelector('.spr-real-val').innerText = unidad.spr;
                        editedRowsPlan.add(filaExistente);
                    }} else {{
                        fila.querySelector('.s-type').value = unidad.nombre;
                        fila.querySelector('.u-manual').innerText = usar;
                        fila.querySelector('.spr-real-val').innerText = unidad.spr;
                        editedRowsPlan.add(fila);
                    }}

                    unidad.restante -= usar;
                    restante -= (usar * unidad.spr);
                }}
            }});
        }}
        recalc();
    }}

    function procesarAsignacionUnidadSJA1(poly) {{
        let bloque = poly.bloque;
        let nombrePlan = bloque.querySelector('td[rowspan]')?.innerText?.toUpperCase()?.trim() || "";
        let objetivo = parseFloat(bloque.querySelector('.v-total-val')?.innerText) || 0;

        let yaAsignado = 0;
        bloque.querySelectorAll('.calc-row').forEach(r => {{
            let unidades = parseInt(r.querySelector('.u-manual')?.innerText) || 0;
            let spr = parseFloat(r.querySelector('.spr-real-val')?.innerText) || 0;
            yaAsignado += (unidades * spr);
        }});

        let restante = objetivo - yaAsignado;
        if (restante <= 0) return;

        let filas = Array.from(bloque.querySelectorAll('.calc-row'));
        for (let fila of filas) {{
            let yaTieneUnidad = parseInt(fila.querySelector('.u-manual')?.innerText) > 0;
            let tipoActual = fila.querySelector('.s-type')?.value?.trim() || "";
            let yaTieneTipo = tipoActual !== "" && tipoActual !== "Seleccionar...";

            if (yaTieneUnidad || yaTieneTipo) continue;
            if (restante <= 0) break;

            let unidad = null;

            if (nombrePlan === "⚠️ CENTRO 1" || nombrePlan === "⚠️ CENTRO 2") {{
                if (nombrePlan === "⚠️ CENTRO 1") {{
                    const listaEspecialesC1 = [
                        "Extra Large Van MLP H&B", 
                        "Truck 3.5 tons MLP", 
                        "Delivery Cell Large Van"
                    ];
                    
                    for (let nombre of listaEspecialesC1) {{
                        unidad = fleet.find(f => f.restante > 0 && f.nombre.toLowerCase() === nombre.toLowerCase());
                        if (unidad) break;
                    }}

                    if (!unidad) {{
                        const listaRental = ["Rental Electric Large Van", "Rental Large Van", "Rental Replacement"];
                        for (let nombre of listaRental) {{
                            unidad = fleet.find(f => f.restante > 0 && f.nombre.toLowerCase().includes(nombre.toLowerCase()));
                            if (unidad) break;
                        }}
                    }}

                }} else if (nombrePlan === "⚠️ CENTRO 2") {{
                    const listaRental = ["Rental Electric Large Van", "Rental Large Van", "Rental Replacement"];
                    for (let nombre of listaRental) {{
                        unidad = fleet.find(f => f.restante > 0 && f.nombre.toLowerCase().includes(nombre.toLowerCase()));
                        if (unidad) break;
                    }}
                }}
            }}
            else if (nombrePlan.includes("EJA1 SP") || nombrePlan.includes("EJA1")) {{
                unidad = fleet.find(f => f.restante > 0 && (f.nombre.toLowerCase().includes("media milla sp") || f.nombre.toLowerCase().includes("media milla")));
            }}
            else if (nombrePlan === "XICO" || nombrePlan === "TUZAMAPA") {{
                unidad = fleet.find(f => f.restante > 0 && f.nombre.toLowerCase().includes("large van mlp foráneo"));

                if (!unidad) {{
                    unidad = fleet.find(f => f.restante > 0 && f.nombre.toLowerCase().includes("small van mlp foráneo"));
                }}

                if (!unidad) {{
                    let listaSustitutas = [
                        "car 8h", 
                        "car newbie", 
                        "car zona extendida", 
                        "small van 9h", 
                        "small van 9h ext", 
                        "small van newbie", 
                        "moto 3h"
                    ];
                    for (let palabra of listaSustitutas) {{
                        unidad = fleet.find(f => f.restante > 0 && f.nombre.toLowerCase().includes(palabra));
                        if (unidad) break;
                    }}
                }}
            }}
            else if (nombrePlan === "PEROTE" || nombrePlan === "TLALTETELA") {{
                unidad = fleet.find(f => f.restante > 0 && f.nombre.toLowerCase().includes("large van mlp foráneo"));

                if (!unidad) {{
                    unidad = fleet.find(f => f.restante > 0 && f.nombre.toLowerCase().includes("small van mlp foráneo"));
                }}
            }}
            else {{
                unidad = fleet.find(f => f.restante > 0 && f.nombre.toLowerCase().includes("large van mlp foráneo"));
                
                if (!unidad) {{
                    unidad = fleet.find(f => f.restante > 0 && f.nombre.toLowerCase().includes("small van mlp foráneo"));
                }}
            }}

            if (!unidad) break;

            let necesarias = Math.ceil(restante / unidad.spr);
            let usar = (unidad.restante > 0) ? Math.min(necesarias, unidad.restante) : 0;

            if (usar <= 0) continue;

            let filaExistente = filas.find(f => f.querySelector('.s-type')?.value === unidad.nombre);
            if (filaExistente) {{
                let actual = parseInt(filaExistente.querySelector('.u-manual')?.innerText) || 0;
                filaExistente.querySelector('.u-manual').innerText = actual + usar;
                filaExistente.querySelector('.spr-real-val').innerText = unidad.spr;
                editedRowsPlan.add(filaExistente);
            }} else {{
                fila.querySelector('.s-type').value = unidad.nombre;
                fila.querySelector('.u-manual').innerText = usar;
                fila.querySelector('.spr-real-val').innerText = unidad.spr;
                editedRowsPlan.add(fila);
            }}

            unidad.restante -= usar;
            restante -= (usar * unidad.spr);
        }}
    }}

    function actualizarTotales() {{
        return;
    }}

    function updateSelectColor(selectElement) {{
        if (selectElement.value === "") {{
            selectElement.style.color = "#A9A9A9";
        }} else {{
            selectElement.style.color = "#25282b";
        }}
    }}

    function updateFleetFloat() {{
        let htmlLeft = "";
        let htmlRight = "";

        let totalMLPReal = 0;
        let totalMLPStock = 0;
        let totalRentalReal = 0;
        let totalRentalStock = 0;
        let totalCarReal = 0;
        let totalCarSchedule = 0;
        let totalNoCar = 0;

        document.querySelectorAll('#body-' + currentTab + ' tr').forEach(row => {{
            let name = row.querySelector('.edit-name')?.innerText.trim();
            let stock = parseInt(row.querySelector('.f-stock')?.innerText) || 0;
            let asignado = parseInt(row.querySelector('.f-ruteadas')?.innerText) || 0;

            if(name && (stock > 0 || asignado > 0)) {{
                let nameLower = name.toLowerCase();

                let esExtraLargeMLP = nameLower.includes("extra large van mlp h&b") || nameLower.includes("extra large van mlp h & b");
                let esTruck35MLP = nameLower.includes("truck 3.5 tons mlp") || nameLower.includes("truck 3.5 ton mlp");
                let debeExcluirMLP = esExtraLargeMLP || esTruck35MLP;

                let esCarStrict = (
                    (nameLower.includes("car") || nameLower.includes("moto") || nameLower.includes("small van") || nameLower.includes("newbie")) &&
                    !nameLower.includes("mlp") && !nameLower.includes("van grande") && !nameLower.includes("large van")
                );

                if (esCarStrict) {{
                    totalCarSchedule += stock;
                }}

                if (name.includes("MLP") && !debeExcluirMLP) {{
                    totalMLPStock += stock;
                    totalMLPReal += asignado;
                }}

                if (nameLower.includes("rental")) {{
                    totalRentalStock += stock;
                    totalRentalReal += asignado;
                }}

                let colorCategoria = esCarStrict ? "#FF4500" : "#0000CD";

                if (esCarStrict) {{
                    totalCarReal += asignado;
                }} else {{
                    if (!debeExcluirMLP && (name === "Large Van MLP" || name === "Small Van MLP" || name.includes("foráneo"))) {{
                        totalNoCar += asignado;
                    }}
                }}

                let leftDisplay = row.querySelector('.f-left')?.innerText || "0";

                htmlLeft += `
                    <div style="display:flex; justify-content:space-between; margin-bottom:4px; font-size:14px;"> 
                        <span style="color:#0a2745;">${{name}}</span>
                        <span style="color:${{colorCategoria}}; font-weight:bold;">${{leftDisplay}}/${{stock}}</span>
                    </div>
                `;
            }}
        }});

        htmlRight = `
            <div style="margin-top: 5px; padding-top: 5px;"> 
                <div style="display:flex; justify-content:space-between; color: #D2691E; font-weight: 800; font-size: 14px;">
                    <span>TOTAL CAR (sched):</span> <span>${{totalCarSchedule}}</span>
                </div>
                <div style="display:flex; justify-content:space-between; color: #FF4500; font-weight: 800; font-size: 14px; margin-bottom: 8px;">
                    <span>TOTAL CAR (real):</span> <span>${{totalCarReal}}</span>
                </div>

                <div style="border-top: 1px solid #25282b; padding-top: 4px;"></div>

                <div style="display:flex; justify-content:space-between; color: #0000CD; font-weight: 800; font-size: 14px;">
                    <span>TOTAL MLP (decl):</span> <span>${{totalMLPStock}}</span>
                </div>
                <div style="display:flex; justify-content:space-between; color: #0000CD; font-weight: 800; font-size: 14px; margin-bottom: 8px;">
                    <span>TOTAL MLP (rute):</span> <span>${{totalMLPReal}}</span>
                </div>

                <div style="border-top: 1px solid #25282b; padding-top: 4px;"></div>

                <div style="display:flex; justify-content:space-between; color: #25282b; font-weight: 800; font-size: 14px;">
                    <span>TOTAL RENTAL (decl):</span> <span>${{totalRentalStock}}</span>
                </div>
                <div style="display:flex; justify-content:space-between; color: #25282b; font-weight: 800; font-size: 14px;">
                    <span>TOTAL RENTAL (rute):</span> <span>${{totalRentalReal}}</span>
                </div>
            </div>
        `;

        let html = `
        <div style="display:flex; gap:15px; align-items:flex-start;">
            <div style="flex:1; min-width:180px;">${{htmlLeft}}</div>
            <div style="width:190px; border-left:2px solid #25282b; padding-left:12px;">${{htmlRight}}</div>
        </div>
        `;

        let elNoCar = document.getElementById('total-no-car-' + currentTab);
        if (elNoCar) elNoCar.innerText = totalNoCar; 

        let elCarReal = document.getElementById('total-car-real-' + currentTab);
        if (elCarReal) elCarReal.innerText = totalCarReal;

        let totalRuteadas = totalMLPReal + totalCarReal + totalRentalReal; 
        let elRuteadas = document.getElementById('total-ruteadas-' + currentTab);
        if (elRuteadas) elRuteadas.innerText = totalRuteadas;

        let elCarSchedule = document.getElementById('total-car-schedule-' + currentTab);
        if (elCarSchedule) elCarSchedule.innerText = totalCarSchedule;

        document.getElementById('fleet-float-body').innerHTML = html;

        document.getElementById("val-mlp-rute-2").innerText = totalMLPReal;
        document.getElementById("val-rental-rute-2").innerText = totalRentalReal;
        document.getElementById("val-car-rute-2").innerText = totalCarReal;

        if (typeof guardarEstado === 'function') {{ guardarEstado(); }}
    }}

    aplicarPerfil();
    recalc();

    function togglePrioridades() {{
        const panel = document.getElementById('panel-prioridades');
        if (panel.style.top === '0px') {{
            panel.style.top = '-600px';
        }} else {{
            panel.style.top = '0px';
        }}
    }}

    function actualizarSelects() {{
        const listaPermitidas = [
            "Small Van MLP foráneo",
            "Car 8h",
            "Car - 8h"
        ];

        document.querySelectorAll('.s-type').forEach(select => {{
            let valorActual = select.value;
            select.innerHTML = '<option value="">Seleccionar...</option>';
            
            document.querySelectorAll('#body-' + currentTab + ' tr').forEach(row => {{
                let name = row.querySelector('.edit-name')?.innerText.trim();
                if (!name || name === "IGNORAR") return;
                
                let stock = parseInt(row.querySelector('.f-stock')?.innerText) || 0;
                let left = parseInt(row.querySelector('.f-left')?.innerText) || 0;
                let nameLower = name.toLowerCase();

                let permiteSinStock = listaPermitidas.some(u => nameLower.includes(u));
                
                if (permiteSinStock || left > 0 || stock > 0) {{
                    let opt = document.createElement('option');
                    opt.value = name;
                    opt.textContent = name;
                    select.appendChild(opt);
                }}
            }});
            select.value = valorActual;
        }});
    }}

    document.addEventListener('input', (e) => {{
        if (e.target.classList.contains('f-stock') || e.target.classList.contains('u-manual')) {{
            recalc(); 
        }}
    }});

    window.addEventListener('load', () => {{
        actualizarSelects();
        agregarIndicadorSchedule();
    }});

    actualizarDosPorciento();

    /* NAVEGACIÓN TECLADO TIPO EXCEL */
    document.addEventListener("keydown", function(e){{
        const celda = document.activeElement;
        if (!celda || !celda.hasAttribute("contenteditable")) return;

        const fila = celda.closest("tr");
        if (!fila) return;

        const tabla = fila.closest("table");
        if (!tabla) return;

        const filas = Array.from(tabla.querySelectorAll("tbody tr"));
        const filaIdx = filas.indexOf(fila);
        const celdasFila = Array.from(fila.querySelectorAll('[contenteditable="true"]'));
        const colIdx = celdasFila.indexOf(celda);

        if(e.key === "ArrowDown"){{
            e.preventDefault();
            const sigFila = filas[filaIdx + 1];
            if(sigFila){{
                const celdas = sigFila.querySelectorAll('[contenteditable="true"]');
                if(celdas[colIdx]) celdas[colIdx].focus();
            }}
        }}

        if(e.key === "ArrowUp"){{
            e.preventDefault();
            const antFila = filas[filaIdx - 1];
            if(antFila){{
                const celdas = antFila.querySelectorAll('[contenteditable="true"]');
                if(celdas[colIdx]) celdas[colIdx].focus();
            }}
        }}

        if(e.key === "ArrowRight"){{
            e.preventDefault();
            if(celdasFila[colIdx + 1]){{
                celdasFila[colIdx + 1].focus();
            }}
        }}

        if(e.key === "ArrowLeft"){{
            e.preventDefault();
            if(celdasFila[colIdx - 1]){{
                celdasFila[colIdx - 1].focus();
            }}
        }}
    }});

    /* SELECCIÓN AUTOMÁTICA DE TEXTO EN CELDAS */
    document.addEventListener("focusin", function(e) {{
        const celda = e.target;
        if (!celda.hasAttribute("contenteditable")) return;

        setTimeout(() => {{
            const rango = document.createRange();
            rango.selectNodeContents(celda);
            const seleccion = window.getSelection();
            seleccion.removeAllRanges();
            seleccion.addRange(rango);
        }}, 0);
    }});

    /* CONTROL DE RELOJ Y TAREAS */
    const ruteos = [
        {{ nombre:"SMX9", hora:"16:40" }},
        {{ nombre:"SMX5", hora:"17:20" }},
        {{ nombre:"SMX2", hora:"18:05" }},
        {{ nombre:"SMT2", hora:"18:40" }},
        {{ nombre:"SJA1 C1", hora:"23:30" }}
    ];

    let ultimaAlerta = "";

    function actualizarRelojRuteos() {{
        const ahora = new Date();
        document.getElementById("hora-actual").innerText = ahora.toLocaleTimeString();
        
        let siguiente = null;
        for (let tarea of ruteos) {{
            let partes = tarea.hora.split(":");
            let fechaTarea = new Date();
            fechaTarea.setHours(parseInt(partes[0]), parseInt(partes[1]), 0, 0);
            if (fechaTarea > ahora) {{
                siguiente = {{ tarea, fechaTarea }};
                break;
            }}
        }}

        const elProximo = document.getElementById("proximo-ruteo");
        const elCuenta = document.getElementById("cuenta-regresiva");
        const elHora = document.getElementById("hora-ruteo");

        if (!siguiente) {{
            elProximo.innerText = "Fin del turno";
            if (elHora) elHora.innerText = "--";
            elCuenta.innerText = "--:--";
        }} else {{
            elProximo.innerText = siguiente.tarea.nombre;
            if (elHora) {{
                elHora.innerText = "A LAS " + siguiente.tarea.hora;
            }}
            
            let diff = siguiente.fechaTarea - ahora;
            let mins = Math.floor(diff / 60000);
            let secs = Math.floor((diff % 60000) / 1000);
            
            elCuenta.innerText = String(mins).padStart(2,"0") + ":" + String(secs).padStart(2,"0");
            elCuenta.style.color = mins < 5 ? "#FF0000" : "#7CFFB2";
        }}
    }}
    setInterval(actualizarRelojRuteos, 1000);
    actualizarRelojRuteos();

    /* CONTROL DE ARRASTRE FLOTANTE DE PANTALLA */
    function iniciarArrastreFlotante(e) {{
        const el = document.getElementById("fleet-sticky");
        const handle = document.getElementById("handle-moverse-flotante");
        if (!el || !handle) return;

        e.preventDefault();
        e.stopPropagation();

        if (e.pointerId !== undefined) {{
            try {{
                handle.setPointerCapture(e.pointerId);
            }} catch(err) {{}}
        }}

        const startY = e.clientY;
        const rect = el.getBoundingClientRect();
        const startTop = rect.top;

        handle.style.cursor = "grabbing";

        function enMovimiento(evt) {{
            const dy = evt.clientY - startY;
            let newTop = startTop + dy;

            const minTop = 10;
            const maxTop = window.innerHeight - el.offsetHeight - 10;
            newTop = Math.max(minTop, Math.min(maxTop, newTop));

            el.style.setProperty("top", newTop + "px", "important");
        }}

        function alSoltar(evt) {{
            handle.style.cursor = "grab";
            
            if (evt && evt.pointerId !== undefined) {{
                try {{
                    handle.releasePointerCapture(evt.pointerId);
                }} catch(err) {{}}
            }}

            window.removeEventListener("pointermove", enMovimiento, true);
            window.removeEventListener("pointerup", alSoltar, true);
            window.removeEventListener("pointercancel", alSoltar, true);
        }}

        window.addEventListener("pointermove", enMovimiento, true);
        window.addEventListener("pointerup", alSoltar, true);
        window.addEventListener("pointercancel", alSoltar, true);
    }}
</script>
</body>
</html>
"""

# INYECCIÓN DE RUTEOS DESDE BD
ruteos_bd = cargar_ruteos_bd()

if ruteos_bd:
    ruteos_json_str = json.dumps(ruteos_bd)
    script_cargas = f"""
    <script>
        document.addEventListener("DOMContentLoaded", function() {{
            let ruteosCargados = {ruteos_json_str};
            if (window.restaurarRuteosDesdeBD && Array.isArray(ruteosCargados)) {{
                window.restaurarRuteosDesdeBD(ruteosCargados);
            }}
        }});
    </script>
    </body>
    """
    app_html = app_html.replace("</body>", script_cargas)

# Renderizado principal
html(app_html, height=1200, scrolling=True)


# ==============================================================================
# 7. BLOQUE DE NOTITAS OPERATIVAS COMPLEMENTARIAS
# ==============================================================================
ID_IMAGEN = "1M4GLEwFzhLrZjV-zmvGrdTQhC6IjwxOJ"
url_final = f"https://drive.google.com/thumbnail?id={ID_IMAGEN}&sz=w1000"

info_operativa = {
    "SDE": f"""
        <div style='text-align: center; margin-bottom: 25px;'>
            <img src="{url_final}" style="width: 100%; max-width: 800px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.2);">
        </div>

        <h3 style='color: #000; margin-bottom: 5px;'>ROL VP04</h3>
        <hr style='border: 1px solid #1E90FF; margin-bottom: 20px;'>
        
        <div style='background: white; border-left: 6px solid #1E90FF; padding: 15px; border-radius: 8px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); color: #000; margin-bottom: 20px;'>
            <p style='margin: 0;'><strong>👉👉 PARA SDE</strong><br>
            - 🔷 Revisar si SVC agrega blancos<br>
            - Orígenes (imagen) + onway + despacho de hoy de las 3 pm en adelante + fecha promesa y/o quemada ...validar<br>
            - SPR 30<br>
            - ❌ delimitación / ❌ restricción<br>
            - Quito puntos muy lejanos</p>
        </div>

        <h3 style='color: #000; margin-top: 25px;'>🟪 SDE 🟪</h3>
        <hr style='border: 1px solid #FF00FF; margin-bottom: 20px;'>
        
        <div style='background: white; border-left: 6px solid #FF00FF; padding: 12px; border-radius: 8px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); color: #000; margin-bottom: 12px;'>
            <p style='margin: 0;'><strong><span style="color: #FF00FF;">●</span> SMX9 PM2 - ⏰ 16:40 - 17:00</strong><br>
            - 📌 Orígenes: MXCD02, MXCD06<br>
            - 👉 Vol aprox. 800 / en peak puede aumentar hasta 1600<br>
            - 👉 fecha promesa</p>
        </div>

        <div style='background: white; border-left: 6px solid #FF00FF; padding: 12px; border-radius: 8px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); color: #000; margin-bottom: 12px;'>
            <p style='margin: 0;'><strong><span style="color: #FF00FF;">●</span> SGD2 PM2 - ⏰ 17:00 - 17:20</strong><br>
             - 📌 Orígenes: MXJC01 para SD3 y MXJC02 para SD2 (en caso de que no hayan ruteado sd2 en la mañana)<br>
             - 👉 MXJC01 último despacho de hoy + fecha promesa y quemada + onway<br>
             - 👉 MXJC02 - revisar el volumen que tenían en la mañana y revisar si te da lo mismo con el último despacho + fecha promesa y quemada + onway // si salen poquitos, agarra todo el despacho del día + fecha promesa y quemada + todo at station y manda pivot para que SVC te valide vol.<br>
             - 👉 Vol aprox. 170 - 250 aprox<br>
             - 👉 prefijo SD3 siempre</p>
        </div>

        <div style='background: white; border-left: 6px solid #FF00FF; padding: 12px; border-radius: 8px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); color: #000; margin-bottom: 12px;'>
            <p style='margin: 0;'><strong><span style="color: #FF00FF;">●</span> SMX5 PM2 - ⏰ 17:20 - 17:40</strong><br>
             - 📌 Orígenes: MXCD02, MXCD06<br>
             - 👉 Vol aprox. 400<br>
             - 👉 fecha promesa + quemada</p>
        </div>

        <div style='background: white; border-left: 6px solid #FF00FF; padding: 12px; border-radius: 8px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); color: #000; margin-bottom: 12px;'>
            <p style='margin: 0;'><strong><span style="color: #FF00FF;">●</span> SMX4 PM2 - ⏰ 17:40 - 18:00</strong><br>
            - 📌 Orígenes: MXCD02, MXCD06<br>
            - 👉 Vol aprox. 550<br>
            - 👉 Preguntar si habrá ids a descartar<br>
            - 🏍️ Motos SPR 30<br>
            - 👉 fecha promesa + quemada</p> 
        </div>

        <div style='background: white; border-left: 6px solid #FF00FF; padding: 12px; border-radius: 8px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); color: #000; margin-bottom: 12px;'>
            <p style='margin: 0;'><strong><span style="color: #FF00FF;">●</span> SMX2 PM2 - ⏰ 18:00 - 18:20</strong><br>
            - 📌 Orígenes: MXCD02, MXCD06<br>
            - 👉 fecha promesa + quemada</br>
            - 👉 Vol aprox. 250<br>
            - 👉 Parámetros ORH=210 OCUP=66%</p>
        </div>

        <div style='background: white; border-left: 6px solid #FF00FF; padding: 12px; border-radius: 8px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); color: #000; margin-bottom: 12px;'>
            <p style='margin: 0;'><strong><span style="color: #FF00FF;">●</span> SMT2 PM2 - ⏰ 18:40 - 19:00</strong><br>
            - 📌 Origen MXNL01<br>
            - 👉 Despacho hoy después 3 pm<br>
            - 👉 fecha promesa + quemada<br>
            - 👉 Vol. 800 aprox.<br>
            - 👉 SPR 27-28 / se van las 30 unidades<br>
            - 👉 Pido validación</p>
        </div>

        <h3 style='color: #000; margin-top: 25px;'>🟥 CICLO 1 🟥</h3>
        <hr style='border: 1px solid #ff8c00; margin-bottom: 20px;'>

        <div style='background: white; border-left: 6px solid #DC143C; padding: 12px; border-radius: 8px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); color: #000; margin-bottom: 12px;'>
            <p style='margin: 0;'><strong><span style="color: #DC143C;">●</span> SCP1 AM1 - ⏰ 20:00 - 21:00</strong><br>
             - 📌 Ellos envían el volumen a tomar<br>
             - ✅ Poco volumen = polígonos que no salen en logis porque se pegan a otros que están cerca<br>
             - 🚛 FORÁNEOS = Large Van MLP / Con Nodos = Híbrida<br>
             - 🚛 CAMPECHE = Rental Large Van (local)= excluír/ Delivery Cell (dedicada/ORH de large van) = NODOS con paradas según # nodos</p>
        </div>

        <div style='background: white; border-left: 6px solid #DC143C; padding: 12px; border-radius: 8px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); color: #000; margin-bottom: 12px;'>
            <p style='margin: 0;'><strong><span style="color: #DC143C;">●</span> SJA1 AM1 - ⏰ 23:30 - 00:30</strong><br>
             - 📌 Ellos envían el volumen a tomar /Apagado CP<br>
             - 🚛 FORÁNEOS = Large Van MLP / Con Nodos = Híbrida<br>
             - 🚛 FORÁNEOS = Small Van MLP / Sin nodos<br>
             - 🚛 FORÁNEOS = Xico y Tuzamapa / Mlp, Crowd<br>
             - 🚛 CENTRO (local) = Rental Large Van = híbridas/ Delivery Cell (3 paradas) / 3.5 tons (2 paradas)</p>
        </div>

        <h3 style='color: #000; margin-top: 25px;'>🟧 PRE-CARGA 🟧</h3>
        <hr style='border: 1px solid #ff8c00; margin-bottom: 20px;'>

        <div style='background: white; border-left: 6px solid #ff8c00; padding: 15px; border-radius: 8px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); color: #000; margin-bottom: 20px;'>
            <p style='margin: 0;'><strong>👉👉 INDICACIONES</strong><br>
            - 📌 Origen + despachos (playbook - ó indicados por SVC) + onway<br>
            - 👉 Schedule del día siguiente / apartado en archivo AMO<br>
            - ➕ Mandan ids a agregar<br>
            - ✅ delimitación / ✅ dejar restricción</p>
        </div>
        
        <div style='background: white; border-left: 6px solid #ff8c00; padding: 12px; border-radius: 8px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); color: #000; margin-bottom: 12px;'>
            <p style='margin: 0;'><strong><span style="color: #ff8c00;">●</span> SMX5 AM3 - ⏰ 21:30 - 22:10</strong><br>
             - 📌 Origen 09 + onway<br>
             - ➕ Agregan ids a ciclo (de origen 10)<br>
             - 🚛 Small van 9h en Iztapalapa, Coyoacán y si sobra en Tláhuac</p>
        </div>

        <h3 style='color: #000; margin-top: 25px;'>👉 OTROS RUTEO PM2 (SDE)</h3>
        <hr style='border: 1px solid #808080; margin-bottom: 20px;'> 

        <div style='background: white; border-left: 6px solid #808080; padding: 12px; border-radius: 8px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); color: #000; margin-bottom: 12px;'>
            <p style='margin: 0;'><strong><span style="color: #808080;">●</span> SMX20 (SMX10) PM2 - ⏰ 0:20 pm</strong><br>
            - 📌 Origen 20 / ❌ SPR / ❌ Ocupación<br>
            - 👉 Meto ORH de 4 hrs para crowd 5 hrs / solo para dividir paquetes uso SPR 30<br>
            - 👉 Pido validación ➡️ @Luisa Itzel Perez y @Ibrahim</p>
        </div>

        <div style='background: white; border-left: 6px solid #808080; padding: 12px; border-radius: 8px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); color: #000; margin-bottom: 12px;'>
            <p style='margin: 0;'><strong><span style="color: #808080;">●</span> SMX8 PM2 - ⏰ 5:30 pm</strong><br>
            - 👉 Sin schedule</p>
        </div>

        <div style='background: white; border-left: 6px solid #808080; padding: 12px; border-radius: 8px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); color: #000; margin-bottom: 12px;'>
            <p style='margin: 0;'><strong><span style="color: #808080;">●</span> SMX3 PM2 - ⏰ 4:30 pm</strong><br>
            - 📌 Orígenes: MXCD02, MXCD06<br>
            - ✅ delimitación (salen planes) / ❌ restricción<br>
            - SPR 30/Moto y Crowd<br>
            - 🏍️ MOTOS ➡️ Cuauhtémoc-Polanco</p>
        </div>

        <div style='background: white; border-left: 6px solid #808080; padding: 12px; border-radius: 8px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); color: #000; margin-bottom: 12px;'>
            <p style='margin: 0;'><strong><span style="color: #808080;">●</span> SBJ1 PM2 - ⏰ A partir de las 5:00 pm</strong><br>
            - 👉 Pido autorización para iniciar ruteo / SPR 28 / 200-300 pqt aprox</p>
        </div>

        <div style='background: white; border-left: 6px solid #808080; padding: 12px; border-radius: 8px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); color: #000; margin-bottom: 12px;'>
            <p style='margin: 0;'><strong><span style="color: #808080;">●</span> SHM1 PM2 - ⏰ 7:20 pm</strong><br>
            - 👉 SPR 21 / crowd 5 hrs</p>
        </div>

        <div style='background: white; border-left: 6px solid #808080; padding: 12px; border-radius: 8px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); color: #000; margin-bottom: 12px;'>
            <p style='margin: 0;'><strong><span style="color: #808080;">●</span> SMT1 PM2 - ⏰ 5:10 pm</strong><br>
            - 📌 Orígen: MXNL01<br>
            - 👉 SVC manda data (la envían tarde, solo hago el cruce para cotejo)</p>
        </div>

        <div style='background: white; border-left: 6px solid #808080; padding: 12px; border-radius: 8px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); color: #000; margin-bottom: 12px;'>
            <p style='margin: 0;'><strong><span style="color: #808080;">●</span> SMT3 PM2 - ⏰ 5:15 pm</strong><br>
            - 👉 SPR 28 / crowd 5 hrs / 500 pqt aprox</p>
        </div>

        <div style='background: white; border-left: 6px solid #808080; padding: 12px; border-radius: 8px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); color: #000; margin-bottom: 12px;'>
            <p style='margin: 0;'><strong><span style="color: #808080;">●</span> SGD1 PM2 - ⏰ 4:50 pm</strong><br>
             - 📌 Orígen: MXJC01</p>
        </div>

        <div style='background: white; border-left: 6px solid #808080; padding: 12px; border-radius: 8px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); color: #000; margin-bottom: 12px;'>
            <p style='margin: 0;'><strong><span style="color: #808080;">●</span> SGD2 PM2 - ⏰ 0:00 pm</strong><br>
            - 👉 SPR 28</p>
        </div>

        <div style='background: white; border-left: 6px solid #808080; padding: 12px; border-radius: 8px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); color: #000; margin-bottom: 12px;'>
            <p style='margin: 0;'><strong><span style="color: #808080;">●</span> SGD3 PM2 - ⏰ 4:50 pm</strong><br>
            - 👉 SPR 30 / crowd 5 y 3 hrs</p>
        </div>

        <div style='background: white; border-left: 6px solid #808080; padding: 12px; border-radius: 8px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); color: #000; margin-bottom: 12px;'>
            <p style='margin: 0;'><strong><span style="color: #808080;">●</span> SMD2 PM1 - ⏰ 5:30 pm</strong><br>
            - 📌 Orígen: MXYU01<br>
            - 👉 Sin schedule / contemplo crowd 5 hrs<br>
            - 🚛 SVC manda en cuantas unidades y el SPR / entre 5 a 6 crowd 5 hrs con SPR 30<br>
            - 👉 Espero a que carguen volumen (x lo general lo cargan 10 min. antes de las 6:00 pm)<br>
            - 👉 Pido validación<br>
            - 👉 Piden mejor dispersion, indico: "Se publicó de acuerdo a la herramienta team, ya no podemos manipular la dispersión como antes"</p>
        </div>

        <div style='background: white; border-left: 6px solid #808080; padding: 12px; border-radius: 8px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); color: #000; margin-bottom: 12px;'>
            <p style='margin: 0;'><strong><span style="color: #808080;">●</span> SPB1 PM2 - ⏰ 6:00 pm</strong><br>
            - 📌 Origen MXPB01<br>
            - 👉 Sin schedule / ocupo crowd 5 hrs a 30 SPR - depende puede mandarlas a 25 SPR<br>
            - 👉 Se carga en contingencia, no tiene ciclo normal creado<br>
            - 👉 Revisan volumen, notifican con palomita<br>
            - 👉 Pido validación</p>
        </div>

        <div style='background: white; border-left: 6px solid #ff8c00; padding: 12px; border-radius: 8px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); color: #000; margin-bottom: 12px;'>
            <p style='margin: 0;'><strong><span style="color: #ff8c00;">●</span> SMX2 AM3 - ⏰ 22:40 - 23:20</strong><br>
             - 📌 Orígenes: MXCD02 despacho de hoy hasta 16:00 / MXCD09  despacho de hoy hasta 14:00 / MXCD10  despacho de hoy hasta 21:00<br>
             - 👉 Todo Onway<br>
             - 👀 Revisar si se agrega ➕ forms<br>
             - ✅ Validan volumen / aprox. 1900-2000<br>
             - 🚛 Extendidas en Texcoco, Pueblos y Chalco</p>
        </div>
    """,
    "SIDE_LINE": """
        <h3 style='color: #000; margin-bottom: 5px;'>¿CÓMO LO HAGO?</h3>
        <hr style='border: 1px solid #1E90FF; margin-bottom: 20px;'>
        <div style='background: white; border-left: 6px solid #1E90FF; padding: 15px; border-radius: 8px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); color: #000; margin-bottom: 20px;'>
            <p style='margin: 0;'>1️⃣ Descargo query de places (script job de SVC trabajado ▶️ ejecutar)<br>
            2️⃣ Routing matutino ▶️ busco lista places (sáb / dom)</p>
        </div>
        <div style='background: white; border-left: 6px solid #1E90FF; padding: 15px; border-radius: 8px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); color: #000;'>
            <p style='margin: 0;'><strong>PASOS DETALLADOS:</strong><br>
            ▶️ Docto script job ▶️ BuscarV ▶️ columna U (customer id) ▶️ clic 1a celda<br>
            ▶️ En archivo places (copio desde place id / 5,0)<br>
            ▶️ Sale A, B ó C ▶️ copio y pego esos id´s ▶️ nueva pestaña en data (nombro "places")<br>
            ▶️ En data ▶️ buscarv para buscar en pestaña places<br>
            ▶️ No deben coincidir todos los id´s<br>
            ▶️ Lo que salga de cruce = places (no se rutea)<br><br>
            <strong>- Elijo "pasar al siguiente día"</strong><br>
            - C1 y C2 es el mismo proceso</p>
        </div>
    """,
    "ENLACES": """
        <h3 style='color: #000; margin-bottom: 5px;'>ENLACES</h3>
        <hr style='border: 1px solid #1E90FF; margin-bottom: 20px;'>
        <div style='background: white; border-left: 6px solid #1E90FF; padding: 15px; border-radius: 8px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); color: #000;'>
            <div style='display: flex; flex-direction: column; gap: 15px;'>
                <a href="https://drive.google.com/drive/folders/1VNCUhdFxnV6MltnBFt4sH6AN_FJjL5jj" target="_blank" style="color: #1E90FF; text-decoration: none; font-weight: bold;">📁 SUBIR DATAS</a>
                <a href="https://docs.google.com/spreadsheets/d/1mj1krN2hXQQ1yFzswDoPscd9tPhguDnB-mAxB4aLPy0/edit" target="_blank" style="color: #1E90FF; text-decoration: none; font-weight: bold;">📅 SCHEDULE METRO</a>
                <a href="https://docs.google.com/spreadsheets/d/1mj1krN2hXQQ1yFzswDoPscd9tPhguDnB-mAxB4aLPy0/edit" target="_blank" style="color: #1E90FF; text-decoration: none; font-weight: bold;">📅 SCHEDULE CENTRO</a>
                <a href="https://docs.google.com/spreadsheets/d/1Gw1RG4XGfDCyz2lKmoj01OoOHQcaPpVagWCeKj-oCzE/edit" target="_blank" style="color: #1E90FF; text-decoration: none; font-weight: bold;">📅 SCHEDULE NORTE</a>
                <a href="https://docs.google.com/spreadsheets/d/1irZgPeFGGtJL2rRu2CYK6NHsjoieX-9DEA-rQCrRjKI/edit" target="_blank" style="color: #1E90FF; text-decoration: none; font-weight: bold;">📅 SCHEDULE SUR</a>
            </div>
        </div>
    """,
    "C1": """
        <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #25282b; padding: 5px;">
            <h2 style='color: #008000; margin-top: 10px; margin-bottom: 5px; font-weight: bold;'>👉 *** SJA1 C1 (Nueva exp)***</h2>
            <hr style='border: 1.5px solid #008000; margin-bottom: 15px;'> 

            <div style="background: #ffffff; padding: 15px; border-radius: 8px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); margin-bottom: 15px;">
                <p style="margin: 0; font-size: 14px; line-height: 1.5;">• SVC indica si será uniciclo o 2 ciclos (mandan orígenes).</p>
            </div>

            <h4 style="color: #ff8c00; margin: 15px 0 5px 0; font-weight: bold; font-size: 15px;">📦 VOLUMEN</h4>
            <div style="background: white; border-left: 5px solid #ff8c00; padding: 12px; border-radius: 4px; margin-bottom: 15px; font-size: 13.5px; line-height: 1.6;">
                • <strong>NO RUT:</strong> 🚫 Todo lo <em>At station (sorting+buffered) - EJA1</em> (está en id nodo/cluster) se manda a no rut (no sale en Pivot).<br>
                • <strong>C1:</strong> Orígenes solo lo onway / si piden tomar <em>at station + buffered</em> se toma de toda la data para C1.<br>
                • <strong>C2:</strong> Orígenes solo lo onway nada más.<br>
                • <strong>En caso de BULK:</strong> Xalapa 60 ids. Revisar tipo de nodo y vigencia del nodo.<br>
                • <strong>Fecha ETA:</strong> Fecha a trabajar y solita. 🚫 Prohibido fecha futura.
            </div>

            <h4 style="color: #1E90FF; margin: 15px 0 5px 0; font-weight: bold; font-size: 15px;">⚙️ LOGIS</h4>
            <div style="background: white; border-left: 5px solid #1E90FF; padding: 12px; border-radius: 4px; margin-bottom: 15px; font-size: 13.5px; line-height: 1.6;">
                • <strong>👉 PIVOT:</strong> ✅ Subo lo NO ruteado (EJA1-at station + C2-depende si son 2 ciclos).<br>
                • Identificar voluminosos (si hay BULK).<br>
                • <strong>UNICICLO:</strong> 🚫 No se permite cherry.<br>
                • <strong>2 CICLOS:</strong> ✅ Permitido cherry.
            </div>

            <h4 style="color: #6a1b9a; margin: 15px 0 5px 0; font-weight: bold; font-size: 15px;">🛑 DROPEO NODOS</h4>
            <div style="background: white; border-left: 5px solid #6a1b9a; padding: 12px; border-radius: 4px; margin-bottom: 15px; font-size: 13.5px; line-height: 1.6;">
                • Si dropea nodos de centro se cargan en <strong>AM1 Cont. con crowd</strong>:<br>
                <span style="padding-left: 15px; display:block;">- Descargo data y se hace cruce con data original (con C1), subo lo ND.</span>
                • No se quita delimitación.<br>
                • Sale Alchichica (se borra).<br>
                • Se publica XPT (no permite editar). ¿EJA1 SP también?
            </div>

            <h4 style="color: #d32f2f; margin: 15px 0 5px 0; font-weight: bold; font-size: 15px;">🛡️ ALCHICHICA ND (AM0)</h4>
            <div style="background: white; border-left: 5px solid #d32f2f; padding: 12px; border-radius: 4px; margin-bottom: 15px; font-size: 13.5px; line-height: 1.6;">
                • Se carga en AM0 con ✅ <strong>2 Small Van MLP</strong>.<br>
                • Unidades no se descuentan de schedule.<br>
                • <strong>Procedimiento:</strong> Se vuelve a subir data de no ruteado y se eliminan el resto de planes, solo se deja Alchichica.<br>
                • Descargo data y se hace cruce con data original (con C1), subo lo ND.
            </div>

            <h4 style="color: #2e7d32; margin: 15px 0 5px 0; font-weight: bold; font-size: 15px;">🚚 UNIDADES PARA ASIGNAR</h4>
            <div style="background: white; border-left: 5px solid #2e7d32; padding: 12px; border-radius: 4px; margin-bottom: 15px; font-size: 13.5px; line-height: 1.6;">
                <strong>🟢 LOCAL:</strong><br>
                • ✅ <strong>RENTALS como híbridas</strong> (SPR 150-170).<br>
                • <strong>CROWD-newbie / 8h / 9h:</strong> (SPR aprox 70).<br>
                • <strong>MLP:</strong> (SPR aprox 110-120).<br>
                • Delivery cell y truck 3.5 con 3 paradas (dedicadas).<br>
                • ⚡ Acabamos primero capacidad MLP y luego CROWD.<br>
                • 🚫 No apagar reglas de restricción para los DM planeados.<br>
                • Nodos = 👉 Rental híbrida.<br><br>

                <strong>🟢 FORÁNEOS:</strong><br>
                • ✅ <strong>Solo MLP</strong> (SPR aprox 110-120).<br>
                • Nodos = MLP híbrida (large preferencia).<br>
                • 💡 <strong>Xico y Tuzamapa SÍ pueden</strong> llevar unidades CROWD-newbie / 8h / 9h / 9h ext.<br>
                • <strong>EJA1 - SP:</strong> ✅ Media milla
            </div>

            <h4 style="color: #333333; margin: 15px 0 5px 0; font-weight: bold; font-size: 15px;">📢 REGLAS GENERALES </h4>
            <div style="background: #fdfefe; border: 1px solid #d0d3d4; padding: 15px; border-radius: 6px; font-size: 13.5px; line-height: 1.6;">
                <p style="margin-top:0; font-weight:bold;">Buenas noches, team. Les pido su apoyo considerando los siguientes puntos para el ruteo:</p>
                • ✅ Contemplar toda la flota disponible en el schedule.<br>
                • ✅ El polígono de Alchichica deberá operar con AM0 por temas de seguridad.<br>
                • Procurar que las unidades Small no superen los 65 ID's en SPR o (300min = 5 hrs).<br>
                • ✅ Utilizar todas las rentals disponibles y configurarlas como híbridas.<br>
                • ✅ En el polígono Centro, cubrir primero la operación con rentals; si es necesario, complementar con crowd o MLP.<br>
                • ✅ Considerar el Mega Nodo (TRUCK 3.5), ruteo de newbies y zonas extendidas con crowd, especialmente en Xico y Tuzamapan.<br><br>
                
                <div style="background: #fdf2f2; border: 1px solid #fadbd8; padding: 10px; border-radius: 4px; color: #c0392b; font-weight: bold; margin-top: 5px;">
                    🚫 Las unidades CROWD NO pueden ir a Tezuitlán (zona muy alejada del SVC).<br>
                    🚫 Las RENTALS NO pueden ir a zonas tan foráneas (Tlaltetela y Perote).
                </div>
            </div>
        </div>
    """,
    "C2": (
        "<div style='text-align:center; padding-top:100px;"
        " color:#666;'><i>Información C2 pendiente...</i></div>"
    ),
    "PREC": (
        "<div style='text-align:center; padding-top:100px;"
        " color:#666;'><i>Información PRECARGA pendiente...</i></div>"
    ),
}

html_notitas = """
<style>
    body { background-color: #25282b; font-family: 'Segoe UI', Tahoma, sans-serif; margin: 0; }
    .main-box { background: #25282b; padding: 10px; }
    
    .unified-console {
        background: #25282b; border-radius: 15px; padding: 15px; 
        margin-bottom: 20px; border: 1px solid #25282b; text-align: center;
    }
    .display-screen {
        background: #25282b; border-radius: 10px; padding: 10px; margin-bottom: 15px; border: 2px solid #25282b;
    }
    .btn-3d {
        background: linear-gradient(145deg, #1e90ff, #1c82e6);
        color: white; border: none; padding: 12px 25px; border-radius: 10px;
        font-weight: bold; cursor: pointer; box-shadow: 0 5px #0a56a3; transition: 0.1s;
    }
    .btn-3d:active { box-shadow: 0 2px #0a56a3; transform: translateY(3px); }

    .tab-bar { display: flex; gap: 8px; margin-bottom: 15px; overflow-x: auto; }
    .tab-btn {
        background: #333; color: white; border: none; padding: 10px 18px;
        border-radius: 8px; cursor: pointer; font-weight: bold; font-size: 12px; white-space: nowrap;
    }
    .tab-btn.active { background: #add8e6; color: black; box-shadow: 0 0 12px #add8e6; }

    body:not(.tab-2) #excel-btn { display: none !important; }

    .content-area { background: #c8dee0; border-radius: 12px; padding: 20px; min-height: 600px; color: #000; }
</style>

<div class="main-box">
    <div class="unified-console"> 
        <div class="display-screen">
            <div style="color: #ffffff; font-size: 10px; margin-bottom: 5px;">HORA / RESTADOR / CONVERTIDOR</div>
            <div id="horaReal" style="font-size: 38px; color: #FF00FF; font-family: sans-serif; font-weight: bold;">--:--</div>
        </div>
        <div style="display: flex; justify-content: center; align-items: center; gap: 15px;">
            <div>
                <span style="color: #add8e6; font-size: 11px; display: block;">MINUTOS</span>
                <input type="number" id="minInput" value="10" 
                    style="background: #222; color: #FFE4E1; border: none; padding: 8px; border-radius: 5px; width: 70px; text-align: center; font-size: 20px; font-weight: bold;">
            </div>
            <button class="btn-3d" onclick="ejecutarTodo()">CALCULAR</button>
        </div>
    </div>

    <h3 style="color: #1E90FF; text-align: center; margin-bottom: 15px;">🍓 NOTITAS OPERATIVAS</h3>
    <div class="tab-bar">
        <button class="tab-btn active" onclick="changeTab(event, 'SDE')">SDE</button>
        <button class="tab-btn" onclick="changeTab(event, 'C1')">C1</button>
        <button class="tab-btn" onclick="changeTab(event, 'C2')">C2</button>
        <button class="tab-btn" onclick="changeTab(event, 'PREC')">PREC</button>
        <button class="tab-btn" onclick="changeTab(event, 'SIDE_LINE')">SIDE LINE</button>
        <button class="tab-btn" onclick="changeTab(event, 'ENLACES')">ENLACES</button>
    </div>
    <div id="visor" class="content-area">
        __SDE_CONTENT__
    </div>
</div>

<script>
    const allData = __ALL_DATA__;  

    function changeTab(e, name) {
        document.getElementById('visor').innerHTML = allData[name];
        let btns = document.getElementsByClassName('tab-btn');
        for (let b of btns) { b.classList.remove('active'); }
        e.currentTarget.classList.add('active');
    }
    function ejecutarTodo() {
        const mins = document.getElementById('minInput').value || 0;
        const ahora = new Date();
        const nuevaFecha = new Date(ahora.getTime() - (mins * 60000));
        const h = String(nuevaFecha.getHours()).padStart(2, '0');
        const m = String(nuevaFecha.getMinutes()).padStart(2, '0');
        document.getElementById('horaReal').innerText = h + ":" + m;
    }
    ejecutarTodo();
</script>
"""

# Reemplazo seguro de variables en notitas
html_notitas = html_notitas.replace("__SDE_CONTENT__", info_operativa["SDE"])
html_notitas = html_notitas.replace("__ALL_DATA__", json.dumps(info_operativa))

st.markdown("---")
components.html(html_notitas, height=1200, scrolling=True)
