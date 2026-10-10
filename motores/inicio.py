"""
inicio.py  -  Motor de "Inicio y procesos" de RendiPlus

1) Programas que arrancan solos al prender el PC.
   - Windows: los desactiva igual que el Administrador de tareas (clave StartupApproved),
     así que es 100 % reversible y no borra nada.
   - Mac: elementos de inicio de sesión y agentes de ~/Library/LaunchAgents.
2) Procesos activos: cuánto consumen y cerrarlos.
"""

import glob
import os
import plistlib
import time

import psutil

from motores import sistema
from motores.sistema import SISTEMA

# ============================================================
#  Qué recomendar para cada programa
# ============================================================

SE_PUEDE_DESACTIVAR = [
    "spotify", "discord", "steam", "epicgames", "epic games", "eadesktop", "ea app", "origin",
    "battle.net", "ubisoft", "uplay", "upc.exe", "teams", "skype", "opera", "edgeautolaunch",
    "msedge", "adobe", "acrobat", "creative cloud", "ccleaner", "whatsapp", "telegram", "zoom",
    "riotclient", "riot client", "utorrent", "bittorrent", "itunes", "jusched", "googledrivesync",
    "cortana", "wallpaper", "messenger", "lghub_updater", "overwolf", "gog galaxy", "goggalaxy",
]
MEJOR_MANTENER = [
    "securityhealth", "windowsdefender", "defender", "realtek", "rtkaud", "nvidia", "nvcontainer",
    "amd", "radeon", "igfx", "intel", "synaptics", "elan", "bluetooth", "ctfmon", "vgtray",
    "antivirus", "avast", "avg", "kaspersky", "eset", "norton", "mcafee", "bitdefender", "malwarebytes",
]


def recomendacion(nombre, comando):
    texto = (nombre + " " + comando).lower()
    for palabra in MEJOR_MANTENER:
        if palabra in texto:
            return "mantener"
    for palabra in SE_PUEDE_DESACTIVAR:
        if palabra in texto:
            return "desactivar"
    return "neutral"


def ejecutable_de(comando):
    """Saca la ruta del programa desde un comando como '"C:\\...\\app.exe" --minimized'."""
    comando = os.path.expandvars((comando or "").strip())
    if comando.startswith('"'):
        fin = comando.find('"', 1)
        if fin > 0:
            return comando[1:fin]
        return comando.strip('"')
    posicion = comando.lower().find(".exe")
    if posicion >= 0:
        return comando[:posicion + 4]
    return comando.split(" ")[0]


# ============================================================
#  Windows
# ============================================================

RUTA_RUN = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUTA_RUN32 = r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run"
RUTA_APROBADOS = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved"


def _estado_aprobado(raiz, subclave, valor):
    """Windows guarda si está activo en un valor binario: 1.er byte par = activo, impar = desactivado."""
    datos = sistema.leer_registro(raiz, RUTA_APROBADOS + "\\" + subclave, valor)
    if not datos:
        return True
    return datos[0] % 2 == 0


def _programas_windows():
    programas = []
    fuentes = [
        ("HKCU", RUTA_RUN, "Run", "Solo tu usuario"),
        ("HKLM", RUTA_RUN, "Run", "Todos los usuarios"),
        ("HKLM", RUTA_RUN32, "Run32", "Todos los usuarios"),
    ]
    for raiz, ruta, subclave, ubicacion in fuentes:
        for nombre, comando in sistema.valores_registro(raiz, ruta):
            if not nombre or not isinstance(comando, str):
                continue
            programas.append({
                "id": raiz + "|" + subclave + "|" + nombre,
                "nombre": nombre,
                "comando": comando,
                "ejecutable": os.path.basename(ejecutable_de(comando)),
                "raiz": raiz,
                "subclave": subclave,
                "valor": nombre,
                "ubicacion": ubicacion,
                "requiere_admin": raiz == "HKLM",
                "activo": _estado_aprobado(raiz, subclave, nombre),
            })

    carpetas = [
        ("HKCU", os.path.join(os.environ.get("APPDATA", ""),
                              r"Microsoft\Windows\Start Menu\Programs\Startup"), "Solo tu usuario"),
        ("HKLM", os.path.join(os.environ.get("PROGRAMDATA", ""),
                              r"Microsoft\Windows\Start Menu\Programs\StartUp"), "Todos los usuarios"),
    ]
    for raiz, carpeta, ubicacion in carpetas:
        if not os.path.isdir(carpeta):
            continue
        for archivo in sorted(os.listdir(carpeta)):
            if archivo.lower() == "desktop.ini":
                continue
            nombre = os.path.splitext(archivo)[0]
            programas.append({
                "id": raiz + "|StartupFolder|" + archivo,
                "nombre": nombre,
                "comando": os.path.join(carpeta, archivo),
                "ejecutable": "",
                "raiz": raiz,
                "subclave": "StartupFolder",
                "valor": archivo,
                "ubicacion": ubicacion + " (carpeta Inicio)",
                "requiere_admin": raiz == "HKLM",
                "activo": _estado_aprobado(raiz, "StartupFolder", archivo),
            })
    return programas


def _cambiar_windows(programa, activo):
    if activo:
        datos = bytes([2, 0, 0, 0]) + bytes(8)
    else:
        # 3 = desactivado, seguido de la fecha en formato de Windows (FILETIME)
        fecha = int((time.time() + 11644473600) * 10 ** 7)
        datos = bytes([3, 0, 0, 0]) + fecha.to_bytes(8, "little")
    return sistema.escribir_registro(programa["raiz"], RUTA_APROBADOS + "\\" + programa["subclave"],
                                     programa["valor"], datos, tipo="binario")


# ============================================================
#  Mac
# ============================================================

def _uid():
    return str(os.getuid())


def _deshabilitados_launchctl():
    texto = sistema.ejecutar(["launchctl", "print-disabled", "gui/" + _uid()])
    deshabilitados = set()
    for linea in texto.splitlines():
        if "=>" in linea and ("disabled" in linea or "true" in linea):
            etiqueta = linea.split("=>")[0].strip().strip('"')
            deshabilitados.add(etiqueta)
    return deshabilitados


def _programas_mac():
    programas = []

    # Elementos de inicio de sesión (los de Configuración > General > Ítems de inicio)
    script = ("JSON.stringify(Application('System Events').loginItems()"
              ".map(function(i){return {nombre: i.name(), ruta: i.path()}}))")
    texto = sistema.ejecutar(["osascript", "-l", "JavaScript", "-e", script])
    desactivados = sistema.leer_config("inicio_mac_desactivados", {})
    try:
        import json
        elementos = json.loads(texto)
    except Exception:
        elementos = []
    for elemento in elementos:
        programas.append({
            "id": "login|" + elemento["nombre"], "nombre": elemento["nombre"],
            "comando": elemento.get("ruta") or "", "ejecutable": elemento["nombre"],
            "tipo_mac": "login", "ubicacion": "Ítems de inicio de sesión",
            "requiere_admin": False, "activo": True,
        })
    for nombre, ruta in desactivados.items():
        programas.append({
            "id": "login|" + nombre, "nombre": nombre, "comando": ruta, "ejecutable": nombre,
            "tipo_mac": "login", "ubicacion": "Ítems de inicio de sesión",
            "requiere_admin": False, "activo": False,
        })

    # Agentes del usuario (~/Library/LaunchAgents)
    deshabilitados = _deshabilitados_launchctl()
    for archivo in sorted(glob.glob(os.path.expanduser("~/Library/LaunchAgents/*.plist"))):
        try:
            with open(archivo, "rb") as contenido:
                datos = plistlib.load(contenido)
        except Exception:
            continue
        etiqueta = datos.get("Label") or os.path.basename(archivo)[:-6]
        comando = " ".join(datos.get("ProgramArguments") or [datos.get("Program", "")])
        programas.append({
            "id": "agente|" + etiqueta, "nombre": etiqueta, "comando": comando,
            "ejecutable": os.path.basename(comando.split(" ")[0]), "tipo_mac": "agente",
            "etiqueta": etiqueta, "ubicacion": "Agente en segundo plano",
            "requiere_admin": False, "activo": etiqueta not in deshabilitados,
        })
    return programas


def _cambiar_mac(programa, activo):
    if programa.get("tipo_mac") == "agente":
        accion = "enable" if activo else "disable"
        codigo, texto = sistema.ejecutar_con_codigo(
            ["launchctl", accion, "gui/" + _uid() + "/" + programa["etiqueta"]])
        return codigo == 0

    desactivados = sistema.leer_config("inicio_mac_desactivados", {})
    nombre = programa["nombre"].replace('"', "")
    if activo:
        ruta = desactivados.get(programa["nombre"], programa["comando"]).replace('"', "")
        script = ('tell application "System Events" to make login item at end with properties '
                  '{path:"' + ruta + '", hidden:false}')
        codigo, texto = sistema.ejecutar_con_codigo(["osascript", "-e", script])
        if codigo == 0:
            desactivados.pop(programa["nombre"], None)
    else:
        script = 'tell application "System Events" to delete login item "' + nombre + '"'
        codigo, texto = sistema.ejecutar_con_codigo(["osascript", "-e", script])
        if codigo == 0:
            desactivados[programa["nombre"]] = programa["comando"]
    sistema.guardar_config("inicio_mac_desactivados", desactivados)
    return codigo == 0


# ============================================================
#  Linux (para pruebas): ~/.config/autostart
# ============================================================

def _programas_linux():
    programas = []
    for archivo in sorted(glob.glob(os.path.expanduser("~/.config/autostart/*.desktop"))):
        nombre = os.path.basename(archivo)[:-8]
        comando = ""
        activo = True
        try:
            with open(archivo, encoding="utf-8") as contenido:
                for linea in contenido:
                    if linea.startswith("Name=") and nombre == os.path.basename(archivo)[:-8]:
                        nombre = linea[5:].strip()
                    if linea.startswith("Exec="):
                        comando = linea[5:].strip()
                    if linea.strip() in ("Hidden=true", "X-GNOME-Autostart-enabled=false"):
                        activo = False
        except Exception:
            continue
        programas.append({"id": "linux|" + archivo, "nombre": nombre, "comando": comando,
                          "ejecutable": os.path.basename(comando.split(" ")[0]), "archivo": archivo,
                          "ubicacion": "Autoarranque", "requiere_admin": False, "activo": activo})
    return programas


def _cambiar_linux(programa, activo):
    try:
        with open(programa["archivo"], encoding="utf-8") as contenido:
            lineas = [l for l in contenido if not l.startswith("Hidden=")
                      and not l.startswith("X-GNOME-Autostart-enabled=")]
        lineas.append("X-GNOME-Autostart-enabled=" + ("true" if activo else "false") + "\n")
        with open(programa["archivo"], "w", encoding="utf-8") as contenido:
            contenido.writelines(lineas)
        return True
    except Exception:
        return False


# ============================================================
#  Funciones públicas
# ============================================================

def programas_inicio():
    """Lista de programas que arrancan con el PC, con su recomendación."""
    if SISTEMA == "Windows":
        programas = _programas_windows()
    elif SISTEMA == "Darwin":
        programas = _programas_mac()
    else:
        programas = _programas_linux()

    administrador = sistema.es_admin()
    for programa in programas:
        programa["recomendacion"] = recomendacion(programa["nombre"], programa["comando"])
        programa["bloqueado"] = programa["requiere_admin"] and not administrador
    programas.sort(key=lambda p: (not p["activo"], p["nombre"].lower()))
    return programas


def cambiar_estado(programa, activo):
    """Activa o desactiva un programa de inicio. Devuelve True si funcionó."""
    if SISTEMA == "Windows":
        return _cambiar_windows(programa, activo)
    if SISTEMA == "Darwin":
        return _cambiar_mac(programa, activo)
    return _cambiar_linux(programa, activo)


# ============================================================
#  Procesos activos
# ============================================================

PROTEGIDOS = {
    # Windows
    "system", "system idle process", "registry", "smss.exe", "csrss.exe", "wininit.exe",
    "winlogon.exe", "services.exe", "lsass.exe", "svchost.exe", "dwm.exe", "explorer.exe",
    "fontdrvhost.exe", "memcompression", "memory compression", "sihost.exe", "audiodg.exe",
    "ctfmon.exe", "runtimebroker.exe", "taskhostw.exe", "spoolsv.exe", "searchindexer.exe",
    "msmpeng.exe", "securityhealthservice.exe", "wmiprvse.exe", "conhost.exe", "dllhost.exe",
    "startmenuexperiencehost.exe", "shellexperiencehost.exe", "textinputhost.exe",
    "applicationframehost.exe", "lsaiso.exe", "secure system", "nvcontainer.exe",
    "nvdisplay.container.exe", "atiesrxx.exe", "atieclxx.exe", "amdrsserv.exe",
    # Mac
    "kernel_task", "launchd", "windowserver", "loginwindow", "finder", "dock", "systemuiserver",
    "mds", "mds_stores", "mdworker", "coreaudiod", "cfprefsd", "trustd", "logd", "controlcenter",
    # Linux
    "systemd", "init", "kthreadd", "xorg", "xvfb",
}


def es_protegido(nombre):
    nombre = (nombre or "").lower()
    if nombre in PROTEGIDOS:
        return True
    return nombre.startswith("python") or nombre.startswith("rendiplus") or nombre.startswith("py.exe")


def procesos_activos(limite=18):
    """Apps agrupadas por nombre con su RAM y CPU. La primera llamada da CPU 0 (necesita dos lecturas)."""
    nucleos = psutil.cpu_count() or 1
    grupos = {}
    for proceso in psutil.process_iter(["name", "memory_info"]):
        info = proceso.info
        if info["memory_info"] is None or info["memory_info"].rss < 1024 * 1024:
            continue   # sin memoria propia: hilos del sistema que no vale la pena mostrar
        try:
            cpu = proceso.cpu_percent(None)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            cpu = 0
        nombre = info["name"] or "?"
        if nombre not in grupos:
            grupos[nombre] = {"nombre": nombre, "ram": 0, "cpu": 0.0, "cantidad": 0,
                              "protegido": es_protegido(nombre)}
        grupos[nombre]["ram"] = grupos[nombre]["ram"] + info["memory_info"].rss
        grupos[nombre]["cpu"] = grupos[nombre]["cpu"] + cpu / nucleos
        grupos[nombre]["cantidad"] = grupos[nombre]["cantidad"] + 1
    lista = sorted(grupos.values(), key=lambda g: g["ram"], reverse=True)
    return lista[:limite]


def cerrar_proceso(nombre):
    """Cierra todos los procesos con ese nombre. Devuelve (cerrados, fallidos)."""
    if es_protegido(nombre):
        return 0, 0
    propio = os.getpid()
    padre = os.getppid()
    cerrados = 0
    fallidos = 0
    victimas = []
    for proceso in psutil.process_iter(["name"]):
        if proceso.info["name"] == nombre and proceso.pid not in (propio, padre):
            try:
                proceso.terminate()
                victimas.append(proceso)
                cerrados = cerrados + 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                fallidos = fallidos + 1
    psutil.wait_procs(victimas, timeout=3)
    return cerrados, fallidos
