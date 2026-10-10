"""
perfiles.py  -  Motor de perfiles de RendiPlus

Un perfil cambia varios ajustes reales de una vez:
  - Plan de energía de Windows (powercfg) / Modo de bajo consumo en Mac (pmset)
  - Modo de juego de Windows
  - Efectos de transparencia
  - Cerrar apps en segundo plano que el usuario elige
Además hay ajustes individuales (aceleración del mouse, programación de GPU por hardware).

Todo lo que se cambia guarda su valor anterior para poder deshacerlo desde el Historial.
"""

import ctypes
import re
import uuid

from motores import inicio, sistema
from motores.sistema import SISTEMA

# ============================================================
#  Planes de energía (Windows)
# ============================================================

GUID_EQUILIBRADO = "381b4222-f694-41f0-9685-ff5bb260df2e"
GUID_ALTO_RENDIMIENTO = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"
GUID_AHORRO = "a1841308-3541-4fab-bc81-f71556f20b4a"
PATRON_GUID = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
PATRON_PLAN = re.compile(r"(" + PATRON_GUID + r")\s*\(([^)]*)\)\s*(\*)?")


def planes_energia():
    """Lista de planes: [{'guid', 'nombre', 'activo'}]. Funciona con Windows en cualquier idioma."""
    if SISTEMA != "Windows":
        return []
    planes = []
    for linea in sistema.ejecutar(["powercfg", "/list"]).splitlines():
        encontrado = PATRON_PLAN.search(linea)
        if encontrado:
            planes.append({"guid": encontrado.group(1).lower(),
                           "nombre": encontrado.group(2).strip(),
                           "activo": encontrado.group(3) == "*"})
    return planes


def plan_activo():
    for plan in planes_energia():
        if plan["activo"]:
            return plan
    return None


def activar_plan(guid):
    if not guid:
        return False
    codigo, texto = sistema.ejecutar_con_codigo(["powercfg", "/setactive", guid])
    return codigo == 0


def asegurar_plan(guid_base):
    """Devuelve el GUID de un plan del tipo pedido. Si Windows lo tiene escondido
    (pasa mucho con 'Alto rendimiento'), crea una copia una sola vez."""
    guids = [plan["guid"] for plan in planes_energia()]
    if guid_base in guids:
        return guid_base
    creados = sistema.leer_config("planes_creados", {})
    if creados.get(guid_base) in guids:
        return creados[guid_base]
    codigo, texto = sistema.ejecutar_con_codigo(["powercfg", "-duplicatescheme", guid_base])
    for guid in re.findall(PATRON_GUID, texto):
        guid = guid.lower()
        if guid != guid_base:
            creados[guid_base] = guid
            sistema.guardar_config("planes_creados", creados)
            return guid
    return None


# ============================================================
#  Modo de energía de Windows 10/11 (Configuración > Sistema > Energía)
#  Muchos equipos con Windows 11 solo permiten el plan "Equilibrado": ahí el rendimiento
#  se elige con este "modo de energía", que va encima del plan.
# ============================================================

MODO_MAXIMO = "ded574b5-45a0-4f42-8737-46345c09c238"       # Máximo rendimiento
MODO_EQUILIBRADO = "00000000-0000-0000-0000-000000000000"  # Equilibrado
MODO_EFICIENCIA = "961cc777-2547-4f9d-8174-7d86181b8a7a"   # Máxima eficiencia energética
NOMBRES_MODO = {MODO_MAXIMO: "Máximo rendimiento", MODO_EQUILIBRADO: "Equilibrado",
                MODO_EFICIENCIA: "Máxima eficiencia energética"}


class _GUID(ctypes.Structure):
    _fields_ = [("Data1", ctypes.c_uint32), ("Data2", ctypes.c_uint16),
                ("Data3", ctypes.c_uint16), ("Data4", ctypes.c_ubyte * 8)]


def modo_energia():
    """GUID del modo de energía activo, o None si este Windows no lo tiene."""
    if SISTEMA != "Windows":
        return None
    try:
        funcion = ctypes.windll.powrprof.PowerGetActualOverlayScheme
        guid = _GUID()
        if funcion(ctypes.byref(guid)) != 0:
            return None
        return str(uuid.UUID(bytes_le=bytes(guid)))
    except Exception:
        return None


def poner_modo_energia(guid_texto):
    if SISTEMA != "Windows" or not guid_texto:
        return False
    try:
        funcion = ctypes.windll.powrprof.PowerSetActiveOverlayScheme
        funcion.argtypes = [_GUID]
        guid = _GUID.from_buffer_copy(uuid.UUID(guid_texto).bytes_le)
        return funcion(guid) == 0
    except Exception:
        return False


# ============================================================
#  Modo de bajo consumo (Mac)
# ============================================================

def bajo_consumo_mac_activo():
    texto = sistema.ejecutar(["pmset", "-g"])
    encontrado = re.search(r"lowpowermode\s+(\d)", texto)
    if encontrado:
        return encontrado.group(1) == "1"
    return None


def bajo_consumo_mac(activar):
    """Pide la contraseña del Mac con la ventana normal del sistema."""
    valor = "1" if activar else "0"
    script = 'do shell script "pmset -a lowpowermode ' + valor + '" with administrator privileges'
    codigo, texto = sistema.ejecutar_con_codigo(["osascript", "-e", script], 120)
    return codigo == 0


# ============================================================
#  Ajustes individuales (Windows)
# ============================================================

AJUSTES = [
    {"id": "modo_juego", "nombre": "Modo de juego",
     "descripcion": "Windows da prioridad al juego abierto y evita que las actualizaciones lo interrumpan.",
     "impacto": "Medio", "requiere_admin": False, "requiere_reinicio": False},
    {"id": "transparencias", "nombre": "Efectos de transparencia",
     "descripcion": "Las ventanas y la barra de tareas se ven translúcidas. Apagarlas libera un poco "
                    "de GPU en equipos modestos.",
     "impacto": "Bajo", "requiere_admin": False, "requiere_reinicio": False},
    {"id": "aceleracion_mouse", "nombre": "Aceleración del mouse",
     "descripcion": "La 'precisión del puntero mejorada' de Windows. No da FPS, pero apagarla hace "
                    "que la puntería en juegos sea más consistente.",
     "impacto": "Puntería", "requiere_admin": False, "requiere_reinicio": False},
    {"id": "hags", "nombre": "Programación de GPU por hardware",
     "descripcion": "La GPU administra su propia memoria. Puede bajar la latencia en GPUs modernas "
                    "(NVIDIA RTX 20 o superior, AMD RX 5000 o superior).",
     "impacto": "Variable", "requiere_admin": True, "requiere_reinicio": True},
]

RUTA_JUEGO = r"Software\Microsoft\GameBar"
RUTA_TEMA = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
RUTA_GPU = r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers"


def _avisar_cambio_tema():
    """Le avisa a Windows que cambió la apariencia, para que se aplique sin reiniciar."""
    try:
        resultado = ctypes.c_ulong()
        ctypes.windll.user32.SendMessageTimeoutW(0xFFFF, 0x001A, 0, "ImmersiveColorSet", 2, 1000,
                                                 ctypes.byref(resultado))
    except Exception:
        pass


def ajustes_disponibles():
    if SISTEMA != "Windows":
        return []
    administrador = sistema.es_admin()
    lista = []
    for ajuste in AJUSTES:
        copia = dict(ajuste)
        copia["valor"] = leer_ajuste(ajuste["id"])
        copia["bloqueado"] = ajuste["requiere_admin"] and not administrador
        lista.append(copia)
    return lista


def leer_ajuste(id_ajuste):
    """Devuelve True (activado), False (desactivado) o None (no se pudo leer)."""
    if SISTEMA != "Windows":
        return None
    if id_ajuste == "modo_juego":
        return sistema.leer_registro("HKCU", RUTA_JUEGO, "AutoGameModeEnabled", 1) == 1
    if id_ajuste == "transparencias":
        return sistema.leer_registro("HKCU", RUTA_TEMA, "EnableTransparency", 1) == 1
    if id_ajuste == "aceleracion_mouse":
        try:
            valores = (ctypes.c_int * 3)()
            ctypes.windll.user32.SystemParametersInfoW(0x0003, 0, valores, 0)   # SPI_GETMOUSE
            return valores[2] != 0
        except Exception:
            return None
    if id_ajuste == "hags":
        return sistema.leer_registro("HKLM", RUTA_GPU, "HwSchMode", 1) == 2
    return None


def escribir_ajuste(id_ajuste, valor):
    """Cambia un ajuste. Devuelve True si funcionó."""
    if SISTEMA != "Windows":
        return False
    if id_ajuste == "modo_juego":
        return sistema.escribir_registro("HKCU", RUTA_JUEGO, "AutoGameModeEnabled", 1 if valor else 0)
    if id_ajuste == "transparencias":
        bien = sistema.escribir_registro("HKCU", RUTA_TEMA, "EnableTransparency", 1 if valor else 0)
        _avisar_cambio_tema()
        return bien
    if id_ajuste == "aceleracion_mouse":
        try:
            numeros = [6, 10, 1] if valor else [0, 0, 0]   # [6, 10, 1] = valores de fábrica de Windows
            valores = (ctypes.c_int * 3)(*numeros)
            # SPI_SETMOUSE, guardando el cambio y avisando a las apps (3)
            return bool(ctypes.windll.user32.SystemParametersInfoW(0x0004, 0, valores, 3))
        except Exception:
            return False
    if id_ajuste == "hags":
        return sistema.escribir_registro("HKLM", RUTA_GPU, "HwSchMode", 2 if valor else 1)
    return False


# ============================================================
#  Apps que se cierran al activar "Rendimiento"
# ============================================================

if SISTEMA == "Darwin":
    APPS_CANDIDATAS = [
        ("Microsoft Teams", "Microsoft Teams", True), ("Creative Cloud", "Adobe Creative Cloud", True),
        ("Epic Games Launcher", "Epic Games Launcher", True), ("Spotify", "Spotify", False),
        ("Discord", "Discord", False), ("Google Chrome", "Google Chrome", False),
        ("Safari", "Safari", False), ("OneDrive", "OneDrive", False),
    ]
else:
    APPS_CANDIDATAS = [
        ("ms-teams.exe", "Microsoft Teams", True), ("Teams.exe", "Microsoft Teams (clásico)", True),
        ("EpicGamesLauncher.exe", "Epic Games Launcher", True), ("EADesktop.exe", "EA app", True),
        ("Battle.net.exe", "Battle.net", True), ("upc.exe", "Ubisoft Connect", True),
        ("Creative Cloud.exe", "Adobe Creative Cloud", True), ("OneDrive.exe", "OneDrive", False),
        ("Spotify.exe", "Spotify", False), ("Discord.exe", "Discord", False),
        ("chrome.exe", "Google Chrome", False), ("msedge.exe", "Microsoft Edge", False),
    ]


def apps_a_cerrar():
    """Procesos que el usuario eligió cerrar (si nunca eligió, se usan los marcados por defecto)."""
    guardadas = sistema.leer_config("apps_a_cerrar")
    if guardadas is None:
        return [proceso for proceso, nombre, marcada in APPS_CANDIDATAS if marcada]
    return guardadas


def guardar_apps_a_cerrar(lista):
    sistema.guardar_config("apps_a_cerrar", lista)


# ============================================================
#  Perfiles
# ============================================================

PERFILES = {
    "rendimiento": {
        "nombre": "Rendimiento",
        "para": "Para jugar y tareas pesadas",
        "plan": GUID_ALTO_RENDIMIENTO, "modo": MODO_MAXIMO, "bajo_consumo_mac": False,
        "ajustes": {"modo_juego": True, "transparencias": False},
        "cerrar_apps": True,
        "cambios": ["Plan de energía Alto rendimiento", "Modo de juego activado",
                    "Transparencias apagadas", "Cierra las apps en segundo plano que elijas"],
    },
    "equilibrado": {
        "nombre": "Equilibrado",
        "para": "Para el uso de todos los días",
        "plan": GUID_EQUILIBRADO, "modo": MODO_EQUILIBRADO, "bajo_consumo_mac": False,
        "ajustes": {"modo_juego": True, "transparencias": True},
        "cerrar_apps": False,
        "cambios": ["Plan de energía Equilibrado", "Modo de juego activado",
                    "Transparencias encendidas", "No cierra ninguna app"],
    },
    "ahorro": {
        "nombre": "Ahorro",
        "para": "Para la batería y un equipo silencioso",
        "plan": GUID_AHORRO, "modo": MODO_EFICIENCIA, "bajo_consumo_mac": True,
        "ajustes": {"transparencias": False},
        "cerrar_apps": False,
        "cambios": ["Plan de energía Economizador", "Transparencias apagadas",
                    "Menos calor y ruido de ventiladores", "No cierra ninguna app"],
    },
}

if SISTEMA == "Darwin":
    PERFILES["rendimiento"]["cambios"] = ["Modo de bajo consumo apagado",
                                          "Cierra las apps en segundo plano que elijas"]
    PERFILES["equilibrado"]["cambios"] = ["Modo de bajo consumo apagado", "No cierra ninguna app"]
    PERFILES["ahorro"]["cambios"] = ["Modo de bajo consumo activado", "Más batería, menos calor",
                                     "No cierra ninguna app"]


def perfil_activo():
    return sistema.leer_config("perfil_activo")


def guardar_perfil_activo(clave):
    sistema.guardar_config("perfil_activo", clave)


def aplicar_perfil(clave):
    """Aplica un perfil. Devuelve (resultados, pasos_para_deshacer).
    resultados es una lista de (texto, funcionó)."""
    perfil = PERFILES[clave]
    resultados = []
    deshacer = [{"tipo": "perfil", "valor": perfil_activo()}]

    if SISTEMA == "Windows":
        anterior = plan_activo()
        modo_anterior = modo_energia()
        guid = asegurar_plan(perfil["plan"])
        actual = None
        if guid and activar_plan(guid):
            actual = plan_activo()   # comprobamos que Windows de verdad lo cambió
        if actual and actual["guid"] == guid:
            if anterior and anterior["guid"] != guid:
                deshacer.append({"tipo": "plan", "valor": anterior["guid"]})
            resultados.append(("Plan de energía: " + actual["nombre"], True))
        else:
            # Windows no aceptó el plan (pasa mucho en Windows 11): usamos el modo de energía,
            # que solo funciona con el plan Equilibrado activo.
            actual = plan_activo()
            if actual and actual["guid"] != GUID_EQUILIBRADO and activar_plan(GUID_EQUILIBRADO):
                deshacer.append({"tipo": "plan", "valor": actual["guid"]})
                actual = plan_activo()
            if modo_anterior is None:
                resultados.append(("Windows no permitió cambiar el plan de energía", False))
        # Con el plan Equilibrado activo, el modo de energía es lo que decide el rendimiento
        actual = plan_activo()
        if actual and actual["guid"] == GUID_EQUILIBRADO and modo_anterior is not None:
            if modo_anterior == perfil["modo"]:
                resultados.append(("Modo de energía: ya estaba en " + NOMBRES_MODO[perfil["modo"]], True))
            elif poner_modo_energia(perfil["modo"]) and modo_energia() == perfil["modo"]:
                deshacer.append({"tipo": "modo_energia", "valor": modo_anterior})
                resultados.append(("Modo de energía: " + NOMBRES_MODO[perfil["modo"]], True))
            else:
                resultados.append(("Windows no permitió cambiar el modo de energía", False))

        for id_ajuste, valor in perfil["ajustes"].items():
            antes = leer_ajuste(id_ajuste)
            nombre = next(a["nombre"] for a in AJUSTES if a["id"] == id_ajuste)
            if antes == valor:
                resultados.append((nombre + ": ya estaba como corresponde", True))
                continue
            if escribir_ajuste(id_ajuste, valor):
                deshacer.append({"tipo": "ajuste", "id": id_ajuste, "valor": antes})
                resultados.append((nombre + (": activado" if valor else ": desactivado"), True))
            else:
                resultados.append((nombre + ": no se pudo cambiar", False))

    elif SISTEMA == "Darwin":
        antes = bajo_consumo_mac_activo()
        if antes is not None and antes != perfil["bajo_consumo_mac"]:
            if bajo_consumo_mac(perfil["bajo_consumo_mac"]):
                deshacer.append({"tipo": "energia_mac", "valor": antes})
                resultados.append(("Modo de bajo consumo cambiado", True))
            else:
                resultados.append(("No se cambió el modo de bajo consumo (se canceló la contraseña)", False))

    if perfil["cerrar_apps"]:
        cerradas = []
        for proceso in apps_a_cerrar():
            cuantos, fallidos = inicio.cerrar_proceso(proceso)
            if cuantos:
                cerradas.append(proceso.replace(".exe", ""))
        if cerradas:
            resultados.append(("Apps cerradas: " + ", ".join(cerradas), True))
        else:
            resultados.append(("No había apps en segundo plano que cerrar", True))

    guardar_perfil_activo(clave)
    return resultados, deshacer
