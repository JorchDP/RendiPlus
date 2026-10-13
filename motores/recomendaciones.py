"""
recomendaciones.py  -  Motor de recomendaciones de RendiPlus

Revisa los componentes y la configuración del PC, y devuelve:
  - una lista de recomendaciones con prioridad (alta, media, baja)
  - lo que ya está bien
  - un puntaje de salud de 0 a 100
  - la calidad gráfica sugerida para los juegos según la GPU y la pantalla
"""

import os

from motores import inicio, perfiles, sistema
from motores.sistema import SISTEMA

PENALIZACION = {"alta": 12, "media": 6, "baja": 2}

URL_DRIVERS = {
    "nvidia": "https://www.nvidia.com/es-la/geforce/drivers/",
    "amd": "https://www.amd.com/es/support/download/drivers.html",
    "intel": "https://www.intel.com/content/www/us/en/support/detect.html",
}


# ============================================================
#  Nivel de la tarjeta gráfica (0 = integrada ... 5 = tope de gama)
# ============================================================

NIVELES_GPU = [
    ("rtx 5090", 5), ("rtx 4090", 5), ("rtx 5080", 5), ("rtx 4080", 5), ("rx 7900", 5),
    ("rtx 5070 ti", 4), ("rtx 4070 ti", 4), ("rtx 3090", 4), ("rtx 3080", 4), ("rtx 5070", 4),
    ("rtx 4070", 4), ("rtx 3070", 4), ("rtx 2080 ti", 4), ("rx 9070", 4), ("rx 7800", 4),
    ("rx 7700", 4), ("rx 6950", 4), ("rx 6900", 4), ("rx 6800", 4),
    ("rtx 5060", 3), ("rtx 4060", 3), ("rtx 3060", 3), ("rtx 2080", 3), ("rtx 2070", 3),
    ("rx 9060", 3), ("rx 7600", 3), ("rx 6750", 3), ("rx 6700", 3), ("rx 6650", 3), ("rx 6600", 3),
    ("rx 5700", 3), ("arc b580", 3), ("arc b570", 3), ("arc a770", 3), ("arc a750", 3),
    ("rtx 4050", 3), ("rtx 5050", 3),
    ("rtx 2060", 2), ("rtx 3050", 2), ("gtx 1660", 2), ("gtx 1080", 2), ("gtx 1070", 2),
    ("rx 5600", 2), ("rx 5500", 2), ("arc a580", 2),
    ("gtx 1650", 1), ("gtx 1060", 1), ("rx 590", 1), ("rx 580", 1), ("rx 570", 1), ("rx 6500", 1),
    ("arc a380", 1), ("rtx 2050", 1), ("gtx 1050", 1), ("gtx 9", 1), ("gtx 7", 0),
]
INTEGRADAS = ["uhd", "iris", "hd graphics", "radeon graphics", "radeon(tm) graphics", "vega",
              "intel(r) graphics", "arc graphics", "780m", "760m", "680m", "890m"]
NOMBRE_NIVEL = ["gráficos integrados", "gama básica", "gama media de entrada", "gama media",
                "gama alta", "tope de gama"]


def normalizar(nombre):
    texto = (nombre or "").lower()
    for basura in ("(tm)", "(r)", "™", "®"):
        texto = texto.replace(basura, "")
    return " ".join(texto.split())


def nivel_gpu(nombre):
    texto = normalizar(nombre)
    if not texto:
        return None
    nivel = None
    if texto.startswith("apple m"):
        if "max" in texto or "ultra" in texto:
            nivel = 4
        elif "pro" in texto:
            nivel = 3
        else:
            nivel = 2
    if nivel is None:
        for modelo, valor in NIVELES_GPU:
            if modelo in texto:
                nivel = valor
                break
    if nivel is None:
        for palabra in INTEGRADAS:
            if palabra in texto:
                nivel = 0
                break
    if nivel is not None and "laptop" in texto:
        nivel = max(0, nivel - 1)
    return nivel


def gpu_principal(gpus):
    """Si hay dos GPUs (integrada + dedicada), elige la mejor."""
    mejor = None
    mejor_nivel = -1
    for gpu in gpus:
        nivel = nivel_gpu(gpu.get("_nombre"))
        if nivel is not None and nivel > mejor_nivel:
            mejor = gpu
            mejor_nivel = nivel
    return mejor or (gpus[0] if gpus else {}), (mejor_nivel if mejor else None)


def marca_gpu(nombre):
    texto = normalizar(nombre)
    if "nvidia" in texto or "geforce" in texto or "rtx" in texto or "gtx" in texto:
        return "nvidia"
    if "amd" in texto or "radeon" in texto or "rx " in texto:
        return "amd"
    if "intel" in texto or "arc" in texto:
        return "intel"
    if "apple" in texto:
        return "apple"
    return ""


# ============================================================
#  Calidad gráfica sugerida
# ============================================================

ESCALERA = ["Bajo", "Medio", "Alto", "Muy alto", "Ultra"]


def calidad_grafica(datos_pc):
    gpu, nivel = gpu_principal(datos_pc.get("gpus", []))
    pantalla = datos_pc.get("pantalla") or {}
    if nivel is None:
        return None

    alto_pantalla = pantalla.get("alto", 1080)
    ancho_pantalla = pantalla.get("ancho", 1920)
    hz = pantalla.get("hz_max") or pantalla.get("hz") or 60
    if alto_pantalla <= 1080:
        castigo = 0
    elif alto_pantalla <= 1440:
        castigo = 1
    else:
        castigo = 2
    efectivo = max(0, min(5, nivel - castigo))
    base = {0: 0, 1: 1, 2: 2, 3: 2, 4: 3, 5: 4}[efectivo]

    texto = normalizar(gpu.get("_nombre"))
    marca = marca_gpu(gpu.get("_nombre"))
    if "rtx" in texto:
        escalador = "DLSS"
    elif marca == "intel" and "arc" in texto:
        escalador = "XeSS"
    elif marca == "apple":
        escalador = "MetalFX"
    else:
        escalador = "FSR"

    vram = gpu.get("_vram_gb") or 0
    if marca == "apple" or not vram:
        texturas = ESCALERA[min(4, base + 1)]
    elif vram < 4:
        texturas = "Bajo"
    elif vram < 6:
        texturas = "Medio"
    elif vram < 12:
        texturas = "Alto"
    else:
        texturas = "Ultra"

    rayos_ok = ("rtx" in texto or "rx 6" in texto or "rx 7" in texto or "rx 9" in texto) and efectivo >= 4

    if efectivo == 0:
        resolucion_rendimiento = "720p o 900p con " + escalador
    else:
        resolucion_rendimiento = f"{ancho_pantalla} x {alto_pantalla}"

    presets = [
        {
            "nombre": "Rendimiento",
            "para": "Shooters competitivos: Valorant, CS2, Fortnite",
            "ajustes": [
                ("Calidad general", ESCALERA[max(0, base - 1)]),
                ("Resolución", resolucion_rendimiento),
                ("Escalado", escalador + (" Rendimiento" if efectivo <= 2 else " Equilibrado")),
                ("Texturas", texturas if efectivo >= 2 else ESCALERA[max(0, base)]),
                ("Sombras", "Bajo"),
                ("Trazado de rayos", "Apagado"),
                ("FPS objetivo", f"{hz} o más" if hz > 60 else "60 estables"),
            ],
        },
        {
            "nombre": "Equilibrado",
            "para": "La mayoría de los juegos",
            "ajustes": [
                ("Calidad general", ESCALERA[base]),
                ("Resolución", f"{ancho_pantalla} x {alto_pantalla}"),
                ("Escalado", escalador + " Calidad" if efectivo <= 3 else "Nativo o " + escalador + " Calidad"),
                ("Texturas", texturas),
                ("Sombras", ESCALERA[max(0, base - 1)]),
                ("Trazado de rayos", "Bajo" if rayos_ok and efectivo >= 5 else "Apagado"),
                ("FPS objetivo", f"60 a {min(hz, 120)}" if hz > 60 else "60"),
            ],
        },
        {
            "nombre": "Calidad",
            "para": "Aventuras de un jugador y mundos abiertos",
            "ajustes": [
                ("Calidad general", ESCALERA[min(4, base + 1)]),
                ("Resolución", f"{ancho_pantalla} x {alto_pantalla}"),
                ("Escalado", escalador + " Calidad" if efectivo <= 3 else "Nativo"),
                ("Texturas", texturas),
                ("Sombras", ESCALERA[min(4, base + 1)]),
                ("Trazado de rayos", "Medio" if rayos_ok else "Apagado"),
                ("FPS objetivo", "Al menos 60" if efectivo >= 3 else "45 a 60"),
            ],
        },
    ]

    consejos = []
    if "rtx" in texto:
        consejos.append("En los juegos que lo tengan, activa NVIDIA Reflex (Activado + Boost) para bajar la latencia.")
    if marca == "amd":
        consejos.append("Activa AMD Anti-Lag desde el software AMD Adrenalin.")
    if hz > 60:
        consejos.append(f"Si tu monitor tiene G-Sync o FreeSync, limita los FPS a {hz - 3}: "
                        "menos tirones y menos latencia.")
    if vram and vram <= 6 and marca != "apple":
        consejos.append(f"Con {vram:.0f} GB de VRAM, si un juego da tirones, baja primero las texturas; "
                        "suele recuperar más fluidez que bajar cualquier otra opción.")
    if datos_pc.get("sistema", {}).get("_portatil"):
        consejos.append("Juega con el cargador conectado: con batería la GPU rinde bastante menos.")
    if (datos_pc.get("ram", {}).get("_total_gb") or 16) < 16:
        consejos.append("Cierra el navegador mientras juegas: con poca RAM, le quita memoria al juego.")

    return {
        "gpu": gpu.get("Modelo", ""),
        "nivel": nivel,
        "nombre_nivel": NOMBRE_NIVEL[nivel],
        "resolucion": f"{ancho_pantalla} x {alto_pantalla}",
        "hz": hz,
        "escalador": escalador,
        "presets": presets,
        "consejos": consejos,
    }


# ============================================================
#  Reglas
# ============================================================

def analizar(datos_pc, uso=None):
    uso = uso or {}
    lista = []
    positivos = []

    def agregar(prioridad, categoria, titulo, detalle, accion=None):
        lista.append({"prioridad": prioridad, "categoria": categoria, "titulo": titulo,
                      "detalle": detalle, "accion": accion})

    info_sistema = datos_pc.get("sistema", {})
    cpu = datos_pc.get("cpu", {})
    ram = datos_pc.get("ram", {})
    gpus = datos_pc.get("gpus", [])
    pantalla = datos_pc.get("pantalla") or {}
    discos = datos_pc.get("discos", [])
    fisicos = datos_pc.get("discos_fisicos", [])
    tipos = datos_pc.get("tipo_por_unidad", {})
    portatil = info_sistema.get("_portatil", False)

    # --- 1. Disco donde está el sistema ---
    if SISTEMA == "Windows":
        letra = (os.environ.get("SystemDrive") or "C:")[0].upper()
        tipo_sistema = tipos.get(letra, "")
        ssds = [d for d in fisicos if "SSD" in d["Tipo"]]
        if tipo_sistema == "HDD":
            detalle = ("Un disco duro mecánico es el mayor freno de un PC: arranque, apps y cargas lentas. ")
            if ssds:
                detalle = detalle + (f"Ya tienes un {ssds[0]['Tipo']} ({ssds[0]['Modelo']}): clonar Windows "
                                     "a ese disco es la mejora más notoria que puedes hacer, sin gastar nada.")
            else:
                detalle = detalle + "Un SSD es la mejora más notoria y barata que le puedes hacer a tu PC."
            agregar("alta", "Almacenamiento", f"Windows está en un disco duro (unidad {letra}:)", detalle,
                    {"tipo": "pagina", "pagina": "mejoras", "texto": "Ver qué comprar"} if not ssds else None)
        elif "SSD" in tipo_sistema:
            positivos.append(f"Windows está instalado en un {tipo_sistema}.")

        otras_hdd = sorted(l for l, t in tipos.items() if t == "HDD" and l != letra)
        if otras_hdd:
            unidades = ", ".join(l + ":" for l in otras_hdd)
            agregar("baja", "Almacenamiento", "Juegos en disco duro",
                    f"La unidad {unidades} es un disco duro (HDD). Si tienes juegos ahí, muévelos a un SSD: "
                    "cargan mucho más rápido. El HDD sirve bien para fotos, videos y respaldos.")

    # --- 2. Espacio libre ---
    for disco in discos:
        principal = (disco["unidad"].upper().startswith(
            (os.environ.get("SystemDrive") or "C:").upper()) or disco["unidad"] in ("/", "Macintosh HD"))
        libre = disco["libre"] / disco["total"] * 100 if disco["total"] else 100
        if principal and libre < 10:
            agregar("alta", "Almacenamiento", f"Queda muy poco espacio en {disco['unidad']}",
                    f"Solo {disco['libre']:.0f} GB libres ({libre:.0f} %). Con menos del 10 % libre, el sistema "
                    "se pone lento y las actualizaciones pueden fallar.",
                    {"tipo": "pagina", "pagina": "limpieza", "texto": "Liberar espacio"})
        elif principal and libre < 20:
            agregar("media", "Almacenamiento", f"Poco espacio libre en {disco['unidad']}",
                    f"{disco['libre']:.0f} GB libres ({libre:.0f} %). Lo ideal es mantener al menos un 20 % libre.",
                    {"tipo": "pagina", "pagina": "limpieza", "texto": "Liberar espacio"})
        elif principal:
            positivos.append(f"Tienes espacio de sobra en el disco principal ({disco['libre']:.0f} GB libres).")
        elif libre < 10:
            agregar("baja", "Almacenamiento", f"La unidad {disco['unidad']} está casi llena",
                    f"Quedan {disco['libre']:.0f} GB libres.")

    # --- 3. Memoria RAM ---
    total = ram.get("_total_gb") or 0
    if total and total < 7.5:
        agregar("alta", "Memoria", f"Solo tienes {total:.0f} GB de RAM",
                "Con menos de 8 GB, Windows y el navegador ya ocupan casi todo. Subir a 16 GB es una mejora enorme.",
                {"tipo": "pagina", "pagina": "mejoras", "texto": "Ver qué comprar"})
    elif total and total < 15:
        agregar("media", "Memoria", f"Tienes {total:.0f} GB de RAM",
                "Alcanza para lo básico, pero 16 GB es lo recomendado hoy para jugar sin tirones.",
                {"tipo": "pagina", "pagina": "mejoras", "texto": "Ver qué comprar"})
    elif total:
        positivos.append(f"{total:.0f} GB de RAM: suficiente para jugar y tener otras apps abiertas.")

    modulos = ram.get("_modulos") or []
    if len(modulos) == 1:
        agregar("alta", "Memoria", "La RAM funciona en un solo canal",
                "Tienes un solo módulo. Agregar otro igual activa el doble canal, que duplica el ancho de "
                "banda de la memoria y sube bastante los FPS, sobre todo en juegos que exigen al procesador.",
                {"tipo": "pagina", "pagina": "mejoras", "texto": "Ver qué comprar"})
    elif len(modulos) >= 2 and len(set(modulos)) > 1:
        tamanos = " + ".join(f"{m} GB" for m in modulos)
        agregar("baja", "Memoria", "Módulos de RAM de distinto tamaño",
                f"Tienes {tamanos}. Funciona en doble canal completo solo si cada canal suma lo mismo "
                "(por ejemplo, un módulo de 4 GB y uno de 8 GB en cada canal). Revisa el manual de tu "
                "placa madre para ver qué ranuras forman cada canal.")
    elif len(modulos) in (2, 4):
        positivos.append("La RAM está en doble canal, con módulos iguales.")

    velocidad = ram.get("_velocidad") or 0
    nominal = ram.get("_velocidad_nominal") or 0
    tipo_ram = ram.get("_tipo", "")
    if velocidad and nominal > velocidad + 100:
        agregar("media", "Memoria", "La RAM funciona más lenta de lo que puede",
                f"Tus módulos soportan {nominal} MT/s pero funcionan a {velocidad} MT/s. Activa el perfil "
                "XMP, DOCP o EXPO en la BIOS para usar su velocidad completa.")
    elif velocidad and cpu.get("_marca") == "AMD" and tipo_ram == "DDR4" and velocidad < 3000:
        agregar("baja", "Memoria", f"RAM a {velocidad} MT/s con un procesador Ryzen",
                "Los Ryzen rinden notablemente mejor con RAM a 3200 MT/s o más. Si tus módulos tienen "
                "perfil DOCP o XMP, actívalo en la BIOS; si no, tenlo en cuenta para tu próxima mejora.")

    # --- 4. Pantalla ---
    if pantalla.get("hz_max", 0) > pantalla.get("hz", 0) + 5:
        accion = None
        if SISTEMA == "Windows":
            accion = {"tipo": "abrir", "ruta": "ms-settings:display-advanced", "texto": "Abrir ajustes de pantalla"}
        agregar("alta", "Pantalla", f"Tu monitor puede ir a {pantalla['hz_max']} Hz y está a {pantalla['hz']} Hz",
                "Estás dejando fluidez de lado. En Configuración > Pantalla > Pantalla avanzada, elige la "
                f"frecuencia de actualización de {pantalla['hz_max']} Hz.", accion)
    elif pantalla.get("hz", 0) >= 100:
        positivos.append(f"El monitor está funcionando a {pantalla['hz']} Hz, su máximo.")

    # --- 5. Driver de la tarjeta gráfica ---
    gpu, nivel = gpu_principal(gpus)
    dias = gpu.get("_dias_driver")
    marca = marca_gpu(gpu.get("_nombre"))
    if dias is not None and dias > 180:
        accion = None
        if marca in URL_DRIVERS:
            accion = {"tipo": "url", "url": URL_DRIVERS[marca], "texto": "Descargar driver"}
        meses = dias // 30
        agregar("media", "Gráficos", f"El driver de la GPU tiene {meses} meses",
                "Los drivers nuevos traen mejoras de rendimiento para juegos recientes y corrigen errores.",
                accion)
    elif dias is not None:
        positivos.append("El driver de la tarjeta gráfica está al día.")

    temperatura = uso.get("gpu_temp")
    if temperatura is not None and temperatura >= 83:
        agregar("media", "Gráficos", f"La GPU está a {temperatura} °C",
                "Es una temperatura alta: puede bajar su velocidad para protegerse. Limpia el polvo de "
                "los ventiladores y revisa que el gabinete tenga buena ventilación.")

    # --- 6. Configuración de Windows ---
    if SISTEMA == "Windows":
        plan = perfiles.plan_activo()
        if plan:
            creados = sistema.leer_config("planes_creados", {})
            de_rendimiento = (plan["guid"] in (perfiles.GUID_ALTO_RENDIMIENTO, "e9a42b02-d5df-448d-aa00-03f14749eb61")
                              or plan["guid"] == creados.get(perfiles.GUID_ALTO_RENDIMIENTO)
                              or "rendimiento" in plan["nombre"].lower()
                              or "performance" in plan["nombre"].lower()
                              or (plan["guid"] == perfiles.GUID_EQUILIBRADO
                                  and perfiles.modo_energia() == perfiles.MODO_MAXIMO))
            if not de_rendimiento and not portatil:
                agregar("media", "Windows", f"Plan de energía: {plan['nombre']}",
                        "En un PC de escritorio conviene el plan de Alto rendimiento: el procesador "
                        "responde más rápido. El perfil Rendimiento lo activa por ti.",
                        {"tipo": "pagina", "pagina": "perfiles", "texto": "Ir a Perfiles"})
            elif de_rendimiento:
                if perfiles.modo_energia() == perfiles.MODO_MAXIMO and plan["guid"] == perfiles.GUID_EQUILIBRADO:
                    positivos.append("Modo de energía de Windows: Máximo rendimiento.")
                else:
                    positivos.append(f"Plan de energía: {plan['nombre']}.")

        if perfiles.leer_ajuste("modo_juego") is False:
            agregar("media", "Windows", "El Modo de juego está apagado",
                    "Con el Modo de juego, Windows le da prioridad al juego y evita que las actualizaciones "
                    "lo interrumpan.", {"tipo": "ajuste", "id": "modo_juego", "valor": True, "texto": "Activar"})
        else:
            positivos.append("El Modo de juego de Windows está activado.")

        texto_gpu = normalizar(gpu.get("_nombre"))
        moderna = ("rtx" in texto_gpu or "rx 6" in texto_gpu or "rx 7" in texto_gpu or "rx 9" in texto_gpu)
        if moderna and perfiles.leer_ajuste("hags") is False:
            accion = {"tipo": "ajuste", "id": "hags", "valor": True, "texto": "Activar"}
            if not sistema.es_admin():
                accion = {"tipo": "pagina", "pagina": "perfiles", "texto": "Ir a Perfiles"}
            agregar("baja", "Windows", "Programación de GPU por hardware apagada",
                    "Tu GPU la soporta. Puede bajar un poco la latencia y la necesitan funciones como "
                    "DLSS Frame Generation. Requiere reiniciar.", accion)

    if SISTEMA == "Darwin" and perfiles.bajo_consumo_mac_activo() and not portatil:
        agregar("baja", "Energía", "El modo de bajo consumo está activado",
                "Limita el rendimiento del procesador y la GPU.",
                {"tipo": "pagina", "pagina": "perfiles", "texto": "Ir a Perfiles"})

    # --- 7. Programas de inicio ---
    try:
        programas = inicio.programas_inicio()
    except Exception:
        programas = []
    sugeridos = [p for p in programas if p["activo"] and p["recomendacion"] == "desactivar"]
    if sugeridos:
        nombres = ", ".join(p["nombre"] for p in sugeridos[:4])
        if len(sugeridos) > 4:
            nombres = nombres + f" y {len(sugeridos) - 4} más"
        agregar("media" if len(sugeridos) >= 3 else "baja", "Inicio",
                (f"{len(sugeridos)} programas innecesarios arrancan con tu PC" if len(sugeridos) > 1
                 else "Un programa innecesario arranca con tu PC"),
                f"{nombres}. Desactivarlos hace que el PC esté listo antes y libera memoria.",
                {"tipo": "pagina", "pagina": "inicio", "texto": "Revisar"})
    elif programas:
        positivos.append("No hay programas innecesarios arrancando con el PC.")

    # --- 8. Uso de RAM en este momento ---
    if uso.get("ram", 0) >= 85:
        agregar("media", "Memoria", f"La RAM está al {uso['ram']:.0f} % ahora mismo",
                "Cuando se llena, Windows usa el disco como memoria y todo se pone lento. "
                "Cierra las apps que no estés usando.",
                {"tipo": "pagina", "pagina": "inicio", "texto": "Ver procesos"})

    # --- 9. Seguridad ---
    try:
        from motores import seguridad
        datos_seguridad = seguridad.estado_seguridad()
    except Exception:
        datos_seguridad = None
    if datos_seguridad and datos_seguridad["disponible"]:
        accion = {"tipo": "pagina", "pagina": "seguridad", "texto": "Ir a Seguridad"}
        problemas = [c for c in datos_seguridad["comprobaciones"] if c["estado"] == "peligro"]
        avisos = [c for c in datos_seguridad["comprobaciones"] if c["estado"] == "alerta"]
        for comprobacion in problemas:
            agregar("alta", "Seguridad", comprobacion["nombre"] + ": requiere atención",
                    comprobacion["detalle"], accion)
        for comprobacion in avisos:
            agregar("baja", "Seguridad", comprobacion["nombre"], comprobacion["detalle"], accion)
        if not problemas:
            positivos.append(f"Antivirus activo: {datos_seguridad['antivirus']}.")

    # --- Puntaje ---
    orden = {"alta": 0, "media": 1, "baja": 2}
    lista.sort(key=lambda r: orden[r["prioridad"]])
    puntaje = 100
    for recomendacion in lista:
        puntaje = puntaje - PENALIZACION[recomendacion["prioridad"]]
    puntaje = max(5, puntaje)

    return {
        "puntaje": puntaje,
        "lista": lista,
        "positivos": positivos,
        "pendientes_importantes": len([r for r in lista if r["prioridad"] in ("alta", "media")]),
        "graficos": calidad_grafica(datos_pc),
    }


def ejecutar_accion(accion):
    """Para acciones que no son 'ir a una página'. Devuelve True si funcionó."""
    if accion["tipo"] == "ajuste":
        return perfiles.escribir_ajuste(accion["id"], accion["valor"])
    if accion["tipo"] == "url":
        import webbrowser
        webbrowser.open(accion["url"])
        return True
    if accion["tipo"] == "abrir":
        sistema.abrir(accion["ruta"])
        return True
    return False
