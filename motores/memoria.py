"""
memoria.py  -  Motor de memoria RAM de RendiPlus

Tres herramientas:
  1. Liberar memoria: le pide a cada programa que devuelva la RAM que no está usando en este
     momento (en Windows, "vaciar el conjunto de trabajo", lo mismo que hacen RAMMap y los
     limpiadores de RAM). El programa sigue abierto; si después necesita esa memoria, la vuelve
     a tomar. Nunca se toca el programa que está en primer plano (por ejemplo, el juego).
  2. Liberar automáticamente: si la RAM pasa de un límite (por ejemplo 85 %), libera sola.
  3. Mantener cerradas: una lista de apps que el usuario no quiere abiertas (por ejemplo, las que
     se vuelven a abrir solas). Mientras esté activo, RendiPlus las cierra cada vez que aparecen.
"""

import os
import threading
import time

import psutil

from motores import inicio, sistema
from motores.sistema import SISTEMA

# Nombres más claros para los procesos más comunes
NOMBRES_AMIGABLES = {
    "chrome.exe": "Google Chrome", "msedge.exe": "Microsoft Edge", "firefox.exe": "Firefox",
    "opera.exe": "Opera", "brave.exe": "Brave", "discord.exe": "Discord", "spotify.exe": "Spotify",
    "steam.exe": "Steam", "steamwebhelper.exe": "Steam (ventanas internas)",
    "epicgameslauncher.exe": "Epic Games Launcher", "epicwebhelper.exe": "Epic Games (ventanas internas)",
    "riotclientservices.exe": "Riot Client", "riotclientux.exe": "Riot Client",
    "battle.net.exe": "Battle.net", "eadesktop.exe": "EA app", "upc.exe": "Ubisoft Connect",
    "teams.exe": "Microsoft Teams", "ms-teams.exe": "Microsoft Teams", "onedrive.exe": "OneDrive",
    "whatsapp.exe": "WhatsApp", "whatsapp.root.exe": "WhatsApp", "telegram.exe": "Telegram",
    "code.exe": "Visual Studio Code", "msmpeng.exe": "Microsoft Defender",
    "memcompression": "Compresión de memoria de Windows", "memory compression": "Compresión de memoria de Windows",
    "explorer.exe": "Explorador de Windows", "dwm.exe": "Escritorio de Windows",
    "svchost.exe": "Servicios de Windows", "searchhost.exe": "Búsqueda de Windows",
    "phoneexperiencehost.exe": "Vínculo móvil", "widgets.exe": "Widgets de Windows",
    "msedgewebview2.exe": "Edge WebView2 (lo usan otras apps)", "obs64.exe": "OBS Studio",
    "nvidia app.exe": "NVIDIA App", "nvcontainer.exe": "NVIDIA (servicios)",
    "googledrivefs.exe": "Google Drive", "dropbox.exe": "Dropbox", "zoom.exe": "Zoom",
    "adobe desktop service.exe": "Adobe Creative Cloud", "creative cloud.exe": "Adobe Creative Cloud",
}


def nombre_amigable(nombre):
    clave = (nombre or "").lower()
    if clave in NOMBRES_AMIGABLES:
        return NOMBRES_AMIGABLES[clave]
    base = nombre[:-4] if clave.endswith(".exe") else nombre
    return base[:1].upper() + base[1:] if base else "?"


# ============================================================
#  Estado de la memoria
# ============================================================

def estado_memoria():
    memoria = psutil.virtual_memory()
    datos = {
        "total": memoria.total,
        "en_uso": memoria.total - memoria.available,
        "disponible": memoria.available,
        "porcentaje": memoria.percent,
        "cache": None,
    }
    if SISTEMA == "Windows":
        try:
            import ctypes
            from ctypes import wintypes

            class INFO(ctypes.Structure):
                _fields_ = [("cb", wintypes.DWORD), ("CommitTotal", ctypes.c_size_t),
                            ("CommitLimit", ctypes.c_size_t), ("CommitPeak", ctypes.c_size_t),
                            ("PhysicalTotal", ctypes.c_size_t), ("PhysicalAvailable", ctypes.c_size_t),
                            ("SystemCache", ctypes.c_size_t), ("KernelTotal", ctypes.c_size_t),
                            ("KernelPaged", ctypes.c_size_t), ("KernelNonpaged", ctypes.c_size_t),
                            ("PageSize", ctypes.c_size_t), ("HandleCount", wintypes.DWORD),
                            ("ProcessCount", wintypes.DWORD), ("ThreadCount", wintypes.DWORD)]
            info = INFO()
            info.cb = ctypes.sizeof(INFO)
            if ctypes.windll.kernel32.K32GetPerformanceInfo(ctypes.byref(info), info.cb):
                datos["cache"] = info.SystemCache * info.PageSize
                datos["comprometida"] = info.CommitTotal * info.PageSize
                datos["limite_comprometida"] = info.CommitLimit * info.PageSize
        except Exception:
            pass
    return datos


def apps_en_memoria(limite=14):
    """Apps agrupadas por nombre (Chrome abre decenas de procesos) con la RAM que usan."""
    vigiladas = {n.lower() for n in leer_vigiladas()}
    grupos = {}
    for proceso in psutil.process_iter(["name", "memory_info"]):
        info = proceso.info
        if info["memory_info"] is None or info["memory_info"].rss < 1024 * 1024:
            continue
        nombre = info["name"] or "?"
        clave = nombre.lower()
        if clave not in grupos:
            grupos[clave] = {"nombre": nombre, "titulo": nombre_amigable(nombre), "ram": 0, "cantidad": 0,
                             "protegido": inicio.es_protegido(nombre), "vigilada": clave in vigiladas}
        grupos[clave]["ram"] = grupos[clave]["ram"] + info["memory_info"].rss
        grupos[clave]["cantidad"] = grupos[clave]["cantidad"] + 1
    lista = sorted(grupos.values(), key=lambda g: g["ram"], reverse=True)
    return lista[:limite]


# ============================================================
#  Liberar memoria
# ============================================================

def _pid_en_primer_plano():
    if SISTEMA != "Windows":
        return None
    try:
        import ctypes
        from ctypes import wintypes
        ventana = ctypes.windll.user32.GetForegroundWindow()
        pid = wintypes.DWORD()
        ctypes.windll.user32.GetWindowThreadProcessId(ventana, ctypes.byref(pid))
        return pid.value or None
    except Exception:
        return None


def _vaciar_windows(excluir):
    import ctypes
    from ctypes import wintypes
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.K32EmptyWorkingSet.argtypes = [wintypes.HANDLE]
    kernel32.K32EmptyWorkingSet.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    permisos = 0x0100 | 0x0400          # PROCESS_SET_QUOTA | PROCESS_QUERY_INFORMATION
    vaciados = 0
    for proceso in psutil.process_iter(["name"]):
        pid = proceso.pid
        if pid in excluir or pid in (0, 4):
            continue
        manija = kernel32.OpenProcess(permisos, False, pid)
        if not manija:
            continue                     # procesos del sistema sin permiso: se saltan
        try:
            if kernel32.K32EmptyWorkingSet(manija):
                vaciados = vaciados + 1
        finally:
            kernel32.CloseHandle(manija)
    return vaciados


def liberar(cerrar_lista=False):
    """Libera RAM y devuelve {"liberado": bytes, "procesos": n, "cerradas": [nombres]}."""
    antes = psutil.virtual_memory().available
    cerradas = cerrar_vigiladas() if cerrar_lista else []
    excluir = {os.getpid()}
    primer_plano = _pid_en_primer_plano()
    if primer_plano and primer_plano != os.getpid():
        excluir.add(primer_plano)
        try:
            # El juego puede tener procesos hijos (por ejemplo, el anticheat): tampoco se tocan
            excluir.update(hijo.pid for hijo in psutil.Process(primer_plano).children(recursive=True))
        except psutil.Error:
            pass

    procesos = 0
    if SISTEMA == "Windows":
        procesos = _vaciar_windows(excluir)
    elif SISTEMA == "Darwin":
        # "purge" vacía la caché de disco; macOS pide la contraseña de administrador
        codigo, _ = sistema.ejecutar_con_codigo(
            ["osascript", "-e", 'do shell script "purge" with administrator privileges'], tiempo_maximo=60)
        procesos = 1 if codigo == 0 else 0

    time.sleep(1.5)                      # Windows tarda un poco en reflejar la memoria libre
    despues = psutil.virtual_memory().available
    return {"liberado": max(0, despues - antes), "procesos": procesos, "cerradas": cerradas}


# ============================================================
#  Apps que se mantienen cerradas
# ============================================================

def leer_vigiladas():
    return list(sistema.leer_config("ram_vigiladas", []) or [])


def guardar_vigiladas(lista):
    unicas = []
    for nombre in lista:
        if nombre and nombre.lower() not in {u.lower() for u in unicas}:
            unicas.append(nombre)
    sistema.guardar_config("ram_vigiladas", unicas)


def agregar_vigilada(nombre):
    if inicio.es_protegido(nombre):
        return False
    guardar_vigiladas(leer_vigiladas() + [nombre])
    return True


def quitar_vigilada(nombre):
    guardar_vigiladas([n for n in leer_vigiladas() if n.lower() != nombre.lower()])


def cerrar_vigiladas():
    """Cierra las apps de la lista que estén abiertas. Devuelve los nombres que cerró."""
    vigiladas = {n.lower(): n for n in leer_vigiladas()}
    if not vigiladas:
        return []
    abiertas = set()
    for proceso in psutil.process_iter(["name"]):
        nombre = (proceso.info["name"] or "").lower()
        if nombre in vigiladas:
            abiertas.add(vigiladas[nombre])
    cerradas = []
    for nombre in sorted(abiertas):
        cerrados, _ = inicio.cerrar_proceso(nombre)
        if cerrados:
            cerradas.append(nombre)
    return cerradas


def inicio_de(nombre):
    """Si la app arranca sola con el PC, devuelve esa entrada de inicio (para ofrecer quitarla)."""
    try:
        for programa in inicio.programas_inicio():
            if programa["activo"] and not programa["bloqueado"] and \
                    (programa.get("ejecutable") or "").lower() == nombre.lower():
                return programa
    except Exception:
        pass
    return None


# ============================================================
#  Vigilante en segundo plano
# ============================================================

class Vigilante:
    """Corre en un hilo aparte mientras RendiPlus está abierto (también minimizado en la bandeja).
    avisar(texto) se llama desde ese hilo: quien lo reciba debe pasarlo al hilo de la ventana."""

    ESPERA_AUTO = 5 * 60          # tras liberar solo, espera 5 minutos antes de volver a hacerlo

    def __init__(self, avisar):
        self.avisar = avisar
        self.ultima_liberacion = 0.0
        self.avisadas = set()
        self.detener = threading.Event()
        self.hilo = threading.Thread(target=self._bucle, daemon=True)

    def iniciar(self):
        self.hilo.start()
        return self

    def _bucle(self):
        vueltas = 0
        while not self.detener.wait(5):
            vueltas = vueltas + 1
            try:
                self._revisar(vueltas)
            except Exception:
                pass

    def _revisar(self, vueltas):
        if sistema.leer_config("ram_vigilar", False):
            for nombre in cerrar_vigiladas():
                if nombre.lower() not in self.avisadas:
                    self.avisadas.add(nombre.lower())
                    self.avisar(f"Cerré {nombre_amigable(nombre)}, que está en tu lista de apps cerradas")

        if vueltas % 6 == 0 and sistema.leer_config("ram_auto", False):
            limite = int(sistema.leer_config("ram_umbral", 85))
            if psutil.virtual_memory().percent >= limite and \
                    time.monotonic() - self.ultima_liberacion > self.ESPERA_AUTO:
                self.ultima_liberacion = time.monotonic()
                resultado = liberar()
                if resultado["liberado"] >= 200 * 1024 ** 2:
                    gb = resultado["liberado"] / 1024 ** 3
                    self.avisar(f"La RAM pasó del {limite} %: liberé {gb:.1f} GB")
