# ==========================================
# 📚 BASE DE CONOCIMIENTO Y REGLAS DE RUTEO (FORMATO HTML)
# ==========================================

reglas_ruteo = {
    "smx9_extendido": (
        "<b>Prioridades SMX9 SD2:</b><br><br>"
        "<ul>"
        "<li>📌 <b>Orígenes:</b> MXCD02, MXCD06</li>"
        "<li>👉 Último despacho de hoy (3 pm en adelante)</li>"
        "<li>👉 Fecha promesa + fecha quemada + onway</li>"
        "</ul>"
    ),
    "sgd2_extendido": (
        "<b>Prioridades SGD2 SD3:</b><br><br>" 
        "<ul>"
        "<li>📌 <b>Orígenes:</b> MXJC01 para SD3 y MXJC02 para SD2 (en caso de que no hayan ruteado SD2 en la mañana)</li>"
        "<li>👉 <b>MXJC01:</b> Último despacho de hoy (3 pm adelante) + fecha promesa + onway</li>"
        "<li>👉 <b>MXJC02:</b> Último despacho de hoy (1 pm) + fecha promesa + onway // Si salen poquitos, agarra todo el despacho del día + fecha promesa y quemada + todo at station y manda pivot para que SVC te valide vol.</li>"
        "<li>👉 Revisar unidades con SVC (a veces indica usar Small Van con la cantidad indicada para las car 5h de schedule)</li>"
        "<li>👉 Puedes pedir validación (no es necesario)</li>"
        "<li>👉 Prefijo SD3 siempre</li>"
        "</ul>"
    ),
    "smx5_precarga": ( 
        "<b>Prioridades SMX5 (PRECARGA):</b><br><br>"
        "<ul>"
        "<li>📌 <b>Origen:</b> MXCD09 + onway</li>"
        "<li>👀 <b>OJO:</b> Últimamente piden usar Small Van en Chalco y Xochimilco (revisar)</li>"
        "<li>👀 <b>OJO:</b> Con indicaciones de reducción de ORH en Xochimilco (u otro polígono)</li>"
        "<li>👉 Resto de planes asignar Car 8h y Extendidas</li>"
        "<li>👉 Revisar si mandan IDs a agregar del origen 10</li>"
        "<li>👉 <b>Cercanía de SVC:</b> Coyoacán, Iztapalapa, Tláhuac, Tlalpan Nte, Tlalpan Sur, Xochi, Chalco y Milpa Alta</li>"
        "</ul>"
    ),
    "smx5_extendido": (
        "<b>Prioridades SMX5 (EXTENDIDO):</b><br><br>"
        "<ul>"
        "<li>📌 <b>Orígenes:</b> MXCD02, MXCD06</li>"
        "<li>👉 Último despacho de hoy (3 pm en adelante)</li>"
        "<li>👉 Fecha promesa + fecha quemada + onway</li>"
        "</ul>"
    ),
    "smx4_extendido": (
        "<b>Prioridades SMX4:</b><br><br>"
        "<ul>"
        "<li>👉 Preguntar si habrá IDs a descartar</li>"
        "<li>📌 <b>Orígenes:</b> MXCD02, MXCD06</li>"
        "<li>👉 Último despacho de hoy (3 pm en adelante)</li>"
        "<li>👉 Fecha promesa + onway</li>"
        "<li>🏍️ Motos SPR 30</li>"
        "</ul>"
    ),
    "smx2_extendido": (
        "<b>Prioridades SMX2:</b><br><br>"
        "<ul>"
        "<li>📌 <b>Orígenes:</b> MXCD02, MXCD06</li>"
        "<li>👉 Último despacho de hoy (3 pm en adelante)</li>"
        "<li>👉 Fecha promesa + quemada + onway</li>"
        "<li>👉 Rutear con parámetros precargados en logis SIN SPR</li>"
        "</ul>"
    ),
    "smt2_extendido": (
        "<b>Prioridades SMT2:</b><br><br>"
        "<ul>"
        "<li>📌 <b>Origen:</b> MXNL01</li>"
        "<li>👉 Último despacho de hoy (3 pm en adelante)</li>"
        "<li>👉 Fecha promesa + quemada + onway</li>"
        "<li>👉 Se pide validación</li>"
        "</ul>"
    ),
    "scp1": (
        "<b>Prioridades SCP1 C1:</b><br><br>"
        "<ul>"
        "<li>📌 Ellos envían el volumen a tomar</li>"
        "<li>📌 Sale cherry (no olvidar compartir al SVC)</li>"
        "<li>📌 Si no te especifican el despacho a excluir haz tu pivot con todo el volumen y ahí revisas cuál despacho o salida coincide con la cantidad a excluir, eso lo pones como NO RUT (recuerda que debe ser onway) y le pides validación al SVC antes de subirlo a logis</li>"
        "<li>🔴 <b>Campeche:</b> ➤ Rental Large Van (excluir / sin nodos)</li>"
        "<li>🔴 <b>Campeche:</b> ➤ Delivery Cell (Dedicada / lleva todos nodos / paradas=nodos)</li>"
        "<li>🟣 <b>Delivery Cell:</b> ➤ Parámetros de Large Van MLP</li>"
        "<li>🟢 <b>Resto planes:</b> ➤ Large Van MLP (si hay nodo = híbrida)</li>"
        "</ul>"
    ),
    "smd1": (
        "<b>Prioridades SMD1 C1:</b><br><br>"
        "<ul>"
        "<li>📌 Sale cherry (no olvidar compartir al SVC - compartir captura de pantalla antes del cherry)</li>"
        "<li>🔴 <b>Centro:</b> ➤ Prioridad = Rental (híbridas) / Crowd / LV (híbridas) / SV</li>"
        "<li>🔴 <b>Centro:</b> ➤ Extra Large Van H&B (son 3 de 50 IDs c/u = ciudad Mérida) / MLP Bulk (pueden ir 2 en un centro y 1 en otro / depende en cuál haya + voluminosos)</li>"
        "<li>🟠 <b>Norte:</b> ➤ Prioridad = Crowd zon ext 10hrs / MLP</li>"
        "<li>🟡 <b>Kanasin:</b> ➤ Si sobran crowd colocarlas aquí</li>"
        "<li>🟣 <b>Resto de planes:</b> ➤ Large Van MLP</li>"
        "<li>🔵 <b>Planes ND:</b> ➤ Tekax y ___ = Large Van MLP</li>"
        "<li>🟤 Priorizar las LV y Rentals</li>"
        "</ul>"
    ),
    "sch1": (
        "<b>Prioridades SCH1 C1:</b><br><br>"
        "<ul>"
        "<li>🟢 Falta info</li>"
        "<li>🟢 Falta info</li>"
        "<li>🟢 Falta info</li>"
        "<li>🟢 Falta info</li>"
        "<li>🟣 Falta info</li>"
        "<li>🔵 Falta info</li>"
        "<li>🟤 Falta info</li>"
        "</ul>"
    ),
    "sja1": (
        "<b>Prioridades SJA1 C1:</b><br><br>" 
        "<ul>"
        "<li>📌 Ellos envían el volumen a tomar / Apagado CP</li>"
        "<li>🟢 <b>Centro 1/2 (PRIORIDAD):</b>"
        "  <ol style='margin-top: 5px; margin-bottom: 5px; padding-left: 20px;'>"
        "    <li>Rental Electric</li>"
        "    <li>Rental LV</li>"
        "    <li>Rental Replacement</li>"
        "    <li>MLP y Crowd</li>"
        "  </ol>"
        "</li>"
        "<li>🟢 <b>Centro 1/2:</b> ➤ 3.5 tons (dedicada=3 paradas) y delivery (dedicada=3 paradas)</li>"
        "<li>🟢 <b>Centro 1/2:</b> ➤ H&B (bulk=híbrida)</li>"
        "<li>🔴 <b>BULK:</b> ➤ 60 IDs de Xalapa = Voluminosos se cargan después de lo no ruteado del ciclo</li>"
        "<li>🚛 <b>FORÁNEOS:</b> = Large Van MLP / Con Nodos = Híbrida</li>"
        "<li>🚛 <b>FORÁNEOS:</b> = Small Van MLP / Sin nodos</li>"
        "<li>🚛 <b>FORÁNEOS:</b> = Xico y Tuzamapa / MLP, Crowd</li>"
        "<li>🔵 <b>EJA1-SP:</b> ➤ Media milla-ruteo fake</li>"
        "<li>🟤 <b>Alchichica ND-AM0:</b> ➤ 2 unidades Small Van MLP / 330 min ó 65 IDs c/u</li>"
        "</ul>"
    )
}


# ==========================================
# 🗺️ BASE DE DATOS DE ORIGENES (MAPA OPERATIVO)
# ==========================================
MAPA_ORIGENES = {
    # 🔵 REGIÓN METRO (CDMX)
    "smx3": {"region": "Metro (CDMX)", "origen": "MXCD02, MXCD06", "val": "❌ No"},
    "smx7": {"region": "Metro (CDMX)", "origen": "MXCD02, MXCD06", "val": "❌ No"},
    "smx8": {"region": "Metro (CDMX)", "origen": "MXCD10", "val": "❌ No"},
    "smx10": {"region": "Metro (CDMX)", "origen": "MXCD02, MXCD06, MXCD20", "val": "❌ No"},
    "smx10 sd3": {"region": "Metro (CDMX)", "origen": "MXCD20", "val": "❌ No"},
    "stl1": {"region": "Metro (CDMX)", "origen": "MXCD02", "val": "❌ No"},
    "shp1": {"region": "Metro (CDMX)", "origen": "MXCD10", "val": "❌ No"},

    # 🟡 REGIÓN CENTRO
    "ssl1": {"region": "Centro", "origen": "MXGT01", "val": "❌ No"},
    "sbj1": {"region": "Centro", "origen": "MXGT01", "val": "❌ No"},
    "sle1": {"region": "Centro", "origen": "MXGT01", "val": "❌ No"},
    "sgd1": {"region": "Centro", "origen": "MXJC01", "val": "❌ No"},
    "sgd3": {"region": "Centro", "origen": "MXJC01", "val": "❌ No"},

    # 🩵 REGIÓN NORTE
    "smt1": {"region": "Norte", "origen": "MXNL01", "val": "✔️ Sí"},
    "smt3": {"region": "Norte", "origen": "MXNL01", "val": "✔️ Sí"},
    "shm1": {"region": "Norte", "origen": "MXSO01", "val": "✔️ Sí"},

    # 🟠 REGIÓN SUR
    "smd2": {"region": "Sur", "origen": "MXYU01", "val": "✔️ Sí"}
}


# ==========================================
# 💡 PREGUNTAS FRECUENTES Y REGLAS OPERATIVAS ADICIONALES (FORMATO HTML)
# ==========================================
PREGUNTAS_FRECUENTES = {
    "large_van_sdd": (
        "🚐 <b>Large Van SDD (SCP1 C1 y SJA1 C1):</b><br><br>"
        "<ul>"
        "<li>Ya vienen precargadas en Logis por defecto.</li>"
        "<li>Se deben utilizar para <b>ambos services</b>.</li>"
        "</ul>"
    ),
    "large_van_scp1": (
        "🚐 <b>Large Van MLP / Large Van SDD para SCP1 C1:</b><br><br>"
        "<ul>"
        "<li>En <b>SCP1 C1</b>, las unidades <b>Large Van MLP</b> aparecen en Logis registradas con el nombre <b>Large Van SDD</b>.</li>"
        "<li>Ya vienen precargadas por defecto en el sistema para usarse en ambos services.</li>"
        "<li>🟢 <b>Regla para resto de planes:</b> Asignar Large Van MLP (si el plan lleva nodo, se configura como híbrida).</li>"
        "</ul>"
    ),
    "bulk_general": (
        "📦 <b>Unidades Bulk:</b><br><br>"
        "Se deben asignar en los polígonos que tengan <b>cantidad de paquetes voluminosos</b> y se cargan después de lo NO RUT en Logis."
    ),
    "bulk_sja1": (
        "📦 <b>Bulk en SJA1 C1:</b><br><br>"
        "<ul>"
        "<li>Van asignadas en <b>Centro 1</b> ó <b>Centro 2</b>, dependiendo en cuál de los dos haya mayor volumen de voluminosos.</li>"
        "</ul>"
    ),
    "prioridades_centro_sja1": (
        "🎯 <b>Prioridades de Asignación en Centro (SJA1):</b><br><br>"
        "Se deben asignar en este orden prioritario (en Centro 1 ó Centro 2):<br>"
        "<ol>"
        "<li>🚛 <b>Truck 3.5 Tons</b></li>"
        "<li>📦 <b>Delivery Cell Large Van</b></li>"
        "<li>⚡ <b>Rental Electric Large Van</b></li>"
        "<li>🚐 <b>Rental Large Van</b></li>"
        "<li>🔄 <b>Rental Replacement</b></li>"
        "<li>📦 <b>Extra Large Van H&B</b></li>"
        "</ol>"
    ),
    "prioridades_foraneos_sja1": (
        "🚛 <b>Prioridades Foráneos (SJA1):</b><br><br>"
        "<ul>"
        "<li><b>1º Lugar:</b> Large Van MLP (en Logis aparecen como <i>Large Van SDD</i>)."
        "  <ul style='margin-top: 4px; margin-bottom: 4px;'>"
        "    <li>👉 <b>PRIORIDAD ABSOLUTA:</b> Llenar primero los planes que llevan <b>nodos</b> (como Perote y Tlaltetela).</li>"
        "    <li>👉 Después cubrir el resto de foráneos hasta agotar las Large Van.</li>"
        "  </ul>"
        "</li>"
        "<li><b>2º Lugar:</b> Small Van MLP (en Logis aparecen como <i>Small Van SDD</i>).</li>"
        "</ul>"
    ),
    "tuzamapa_xico": (
        "🏞️ <b>Reglas Especiales para Xico y Tuzamapa (SJA1):</b><br><br>"
        "<ul>"
        "<li><b>Orden de prioridad:</b> Large Van MLP ➡️ Small Van MLP ➡️ Crowd (<i>Car 8h</i> y <i>Small Van 9h extra</i>).</li>"
        "<li>⚠️ <b>Mínimos obligatorios de MLP (Restricción de Logis):</b>"
        "  <ul style='margin-top: 4px; margin-bottom: 4px;'>"
        "    <li><b>Xico:</b> Debe llevar <b>al menos 2 ó 3 MLP</b>.</li>"
        "    <li><b>Tuzamapa:</b> Con <b>1 MLP</b> es suficiente.</li>"
        "    <li><b>Nota:</b> El resto del volumen se cubre con Crowd. Es crucial poner las MLP mínimas porque, aunque sobren Crowds en schedule, Logis no acepta más de cierto límite y deja paquetes fuera por restricción.</li>"
        "  </ul>"
        "</li>"
        "</ul>"
    ),
    "dropeo_nodos_sja1": (
        "⚠️ <b>Dropeo de Nodos (SJA1):</b><br><br>"
        "<ul>"
        "<li>Se cargan en <b>contingencia</b> utilizando las unidades disponibles del schedule.</li>"
        "<li>Si sobran <b>Rentals</b>, se usan primero.</li>"
        "<li>El resto se cubre con <b>MLP</b> (si hay disponibles) y luego con <b>Crowd</b>.</li>"
        "<li>📌 <i>Ten en cuenta que igual pueden quedar paquetes fuera por zona de restricción.</i></li>"
        "</ul>"
    ),
    "alchichica": (
        "🚛 <b>Plan Alchichica ND (SJA1):</b><br><br>"
        "<ul>"
        "<li>Se carga en <b>AM0</b> (Next Day).</li>"
        "<li>Se le asignan <b>2 unidades Small Van MLP</b> (en Logis aparecen como <i>Small Van SDD</i>).</li>"
        "<li>Si el sistema bota una unidad por bajo volumen, déjala así.</li>"
        "<li>📏 <b>Requisitos obligatorios (debe cumplir al menos 1):</b>"
        "  <ol style='margin-top: 4px; margin-bottom: 4px;'>"
        "    <li>Tener <b>65 IDs</b> por cada unidad.</li>"
        "    <li>Tener un <b>ORH de 300 minutos (5 hrs)</b>.</li>"
        "  </ol>"
        "</li>"
        "</ul>"
    ),
    "scp1_cambios": (
        "🔄 <b>Ajustes y Quitar Unidades en SCP1:</b><br><br>"
        "<ul>"
        "<li>Las Large Van MLP en logis aparecen como Large Van SDD, esas se usan.</li>"
        "<li>Pueden solicitar quitar unidades o pasar planes a <b>Ciclo 2</b> (se realizan los cambios y se pide validación al SVC).</li>"
        "<li>📏 <b>Regla de oro:</b> Las unidades deben cumplir con nuestro <b>ORH</b>; mientras cumplan con el tiempo, no hay problema.</li>"
        "<li>📌 <i>Nota:</i> Cuando el SVC pide quitar unidades, generalmente es porque van un poco bajas en ORH.</li>"
        "</ul>"
    ),
    "smd1_prioridad": (
        "📊 <b>Prioridades en SMD1:</b><br><br>"
        "<ul>"
        "<li>Recuerda que en SMD1 la prioridad de unidades y asignación de flota es <b>diferente</b> al resto de las estaciones.</li>"
        "</ul>"
    )
}
