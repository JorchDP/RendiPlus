"""
programas.py  -  Motor de programas instalados de RendiPlus

Lista lo que hay instalado en cada disco y cuánto ocupa:
  - Windows: programas (registro de Windows), juegos de Steam, Epic Games y Xbox / Game Pass.
  - Mac: aplicaciones de /Applications y juegos de Steam.

Para desinstalar, RendiPlus NUNCA borra carpetas por su cuenta: abre el desinstalador propio de
cada programa (el mismo que usa Windows en "Aplicaciones instaladas"), o Steam / Epic / la
Papelera del Mac. Así cada programa se limpia bien (registro, accesos directos, servicios).
"""

import glob
import json
import os
import re
import threading
import time

from motores import sistema
from motores.sistema import SISTEMA

RUTA_DESINSTALAR = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
ARCHIVO_TAMANOS = "tamanos_programas.json"

# Programas que usan otros programas: se pueden desinstalar, pero con un aviso más fuerte
PALABRAS_NECESARIO = ["visual c++", "redistributable", ".net", "runtime", "directx", "driver", "controlador",
                      "chipset", "physx", "webview2", "vulkan", "realtek", "management engine",
                      "nvidia graphics", "nvidia hd audio", "nvidia app", "amd software", "intel(r) graphics",
                      "update health", "windows sdk", "microsoft gameinput", "xbox", "microsoft edge"]
ACTUALIZACIONES = ("update", "hotfix", "security update", "service pack")


def es_necesario(nombre):
    texto = nombre.lower()
    return any(palabra in texto for palabra in PALABRAS_NECESARIO)


def unidad_de(ruta):
    if not ruta:
        return ""
    if SISTEMA == "Windows":
        return os.path.splitdrive(ruta)[0].upper()
    if ruta.startswith("/Volumes/"):
        return ruta.split("/")[2]
    return "Macintosh HD" if SISTEMA == "Darwin" else "/"


def _normal(ruta):
    return os.path.normcase(os.path.normpath(ruta)) if ruta else ""


def carpetas_genericas():
    """Carpetas que contienen muchos programas: nunca se miden como si fueran de uno solo."""
    nombres = ["SystemRoot", "ProgramFiles", "ProgramFiles(x86)", "ProgramW6432", "ProgramData",
               "USERPROFILE", "LOCALAPPDATA", "APPDATA", "PUBLIC", "CommonProgramFiles",
               "CommonProgramFiles(x86)"]
    genericas = set()
    for nombre in nombres:
        valor = os.environ.get(nombre)
        if valor:
            genericas.add(_normal(valor))
    perfil = os.path.expanduser("~")
    for sub in ("", "Desktop", "Documents", "Downloads", "AppData", "AppData\\Local\\Programs",
                "AppData\\Local", "AppData\\Roaming", "Applications", "Library"):
        genericas.add(_normal(os.path.join(perfil, sub)))
    for raiz in ("/Applications", "/Library", "/System", "/usr", "/opt"):
        genericas.add(_normal(raiz))
    return genericas


def carpeta_valida(ruta, genericas):
    if not ruta or not os.path.isdir(ruta):
        return False
    normal = _normal(ruta)
    if normal in genericas:
        return False
    if SISTEMA == "Windows":
        unidad, resto = os.path.splitdrive(normal)
        if resto.strip("\\/") == "":
            return False                  # la raíz de un disco (C:\)
        segmentos = resto.lower().strip("\\").split("\\")
        if "installer" in segmentos or "package cache" in segmentos or "temp" in segmentos:
            return False
    return True


# ============================================================
#  Windows: programas del registro
# ============================================================

def _leer_valores(clave):
    import winreg
    valores = {}
    indice = 0
    while True:
        try:
            nombre, dato, tipo = winreg.EnumValue(clave, indice)
        except OSError:
            break
        valores[nombre] = dato
        indice = indice + 1
    return valores


def _ruta_desde_comando(texto):
    """Saca la ruta del .exe de un texto como '"C:\\App\\unins000.exe" /SILENT' o 'C:\\App\\app.exe,0'."""
    if not texto:
        return ""
    texto = os.path.expandvars(str(texto).strip())
    if texto.startswith('"'):
        fin = texto.find('"', 1)
        ruta = texto[1:fin] if fin > 0 else texto[1:]
    else:
        encontrado = re.match(r"(.+?\.(?:exe|ico|dll))\b", texto, re.IGNORECASE)
        ruta = encontrado.group(1) if encontrado else texto.split(",")[0]
    return ruta.strip()


def programas_registro(genericas):
    import winreg
    fuentes = [("HKLM", winreg.HKEY_LOCAL_MACHINE, winreg.KEY_WOW64_64KEY),
               ("HKLM", winreg.HKEY_LOCAL_MACHINE, winreg.KEY_WOW64_32KEY),
               ("HKCU", winreg.HKEY_CURRENT_USER, 0)]
    programas = []
    for nombre_raiz, raiz, vista in fuentes:
        try:
            base = winreg.OpenKey(raiz, RUTA_DESINSTALAR, 0, winreg.KEY_READ | vista)
        except OSError:
            continue
        indice = 0
        while True:
            try:
                subclave = winreg.EnumKey(base, indice)
            except OSError:
                break
            indice = indice + 1
            try:
                with winreg.OpenKey(base, subclave) as clave:
                    valores = _leer_valores(clave)
            except OSError:
                continue

            nombre = str(valores.get("DisplayName") or "").strip()
            desinstalar = str(valores.get("UninstallString") or "").strip()
            if not nombre or not desinstalar:
                continue
            if valores.get("SystemComponent") == 1 or valores.get("ParentKeyName"):
                continue
            if str(valores.get("ReleaseType") or "").lower() in ACTUALIZACIONES:
                continue
            if re.match(r"(security update|update for|hotfix for|kb\d{6,})", nombre, re.IGNORECASE):
                continue

            carpeta = os.path.expandvars(str(valores.get("InstallLocation") or "").strip().strip('"'))
            if not carpeta_valida(carpeta, genericas):
                carpeta = ""
                for candidato in (valores.get("DisplayIcon"), desinstalar):
                    ruta = _ruta_desde_comando(candidato)
                    if ruta and os.path.isfile(ruta) and "msiexec" not in ruta.lower():
                        directorio = os.path.dirname(ruta)
                        if carpeta_valida(directorio, genericas):
                            carpeta = directorio
                            break

            tamano = valores.get("EstimatedSize")
            tamano = int(tamano) * 1024 if isinstance(tamano, int) and tamano > 0 else None
            programas.append({
                "id": f"reg:{nombre_raiz}:{vista}:{subclave}",
                "nombre": nombre,
                "editor": str(valores.get("Publisher") or "").strip(),
                "version": str(valores.get("DisplayVersion") or "").strip(),
                "origen": "Programa",
                "juego": False,
                "carpeta": carpeta,
                "unidad": unidad_de(carpeta),
                "bytes": tamano,
                "estimado": tamano is not None,
                "necesario": es_necesario(nombre),
                "desinstalar": {"tipo": "comando", "comando": desinstalar,
                                "msi": bool(valores.get("WindowsInstaller"))},
                "registro": {"raiz": nombre_raiz, "vista": vista, "clave": subclave},
                "clave_registro": subclave,
            })
        winreg.CloseKey(base)
    return programas


# ============================================================
#  Steam, Epic Games y Xbox
# ============================================================

def _leer_acf(ruta):
    """Lee un archivo de Steam (.acf / .vdf) y devuelve sus pares "clave" "valor"."""
    try:
        with open(ruta, encoding="utf-8", errors="replace") as archivo:
            texto = archivo.read()
    except OSError:
        return {}
    pares = {}
    for clave, valor in re.findall(r'"([^"]+)"\s+"([^"]*)"', texto):
        pares.setdefault(clave.lower(), valor.replace("\\\\", "\\"))
    return pares


def bibliotecas_steam():
    bases = []
    if SISTEMA == "Windows":
        ruta = sistema.leer_registro("HKCU", r"Software\Valve\Steam", "SteamPath")
        if ruta:
            bases.append(os.path.normpath(ruta))
        bases.append(os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"), "Steam"))
    elif SISTEMA == "Darwin":
        bases.append(os.path.expanduser("~/Library/Application Support/Steam"))
    else:
        bases.append(os.path.expanduser("~/.local/share/Steam"))

    bibliotecas = []
    for base in bases:
        if not os.path.isdir(os.path.join(base, "steamapps")):
            continue
        bibliotecas.append(base)
        try:
            with open(os.path.join(base, "steamapps", "libraryfolders.vdf"), encoding="utf-8",
                      errors="replace") as archivo:
                for ruta in re.findall(r'"path"\s+"([^"]+)"', archivo.read()):
                    bibliotecas.append(os.path.normpath(ruta.replace("\\\\", "\\")))
        except OSError:
            pass
    unicas = []
    vistas = set()
    for biblioteca in bibliotecas:
        if _normal(biblioteca) not in vistas and os.path.isdir(biblioteca):
            vistas.add(_normal(biblioteca))
            unicas.append(biblioteca)
    return unicas


def juegos_steam():
    juegos = []
    for biblioteca in bibliotecas_steam():
        for manifiesto in glob.glob(os.path.join(biblioteca, "steamapps", "appmanifest_*.acf")):
            datos = _leer_acf(manifiesto)
            appid = datos.get("appid")
            nombre = datos.get("name")
            if not appid or not nombre or appid == "228980":     # 228980 = redistribuibles de Steam
                continue
            carpeta = os.path.join(biblioteca, "steamapps", "common", datos.get("installdir", ""))
            tamano = int(datos["sizeondisk"]) if datos.get("sizeondisk", "").isdigit() else None
            juegos.append({
                "id": "steam:" + appid,
                "nombre": nombre, "editor": "", "version": "",
                "origen": "Steam", "juego": True,
                "carpeta": carpeta if os.path.isdir(carpeta) else "",
                "unidad": unidad_de(carpeta),
                "bytes": tamano or None, "estimado": False, "necesario": False,
                "desinstalar": {"tipo": "url", "url": "steam://uninstall/" + appid},
                "manifiesto": manifiesto,
            })
    return juegos


def juegos_epic():
    if SISTEMA != "Windows":
        return []
    carpeta = os.path.join(os.environ.get("ProgramData", r"C:\ProgramData"),
                           "Epic", "EpicGamesLauncher", "Data", "Manifests")
    juegos = []
    for manifiesto in glob.glob(os.path.join(carpeta, "*.item")):
        try:
            with open(manifiesto, encoding="utf-8", errors="replace") as archivo:
                datos = json.load(archivo)
        except (OSError, ValueError):
            continue
        if datos.get("bIsIncompleteInstall") or not datos.get("DisplayName"):
            continue
        ubicacion = os.path.normpath(datos.get("InstallLocation") or "")
        tamano = datos.get("InstallSize")
        juegos.append({
            "id": "epic:" + str(datos.get("AppName") or datos["DisplayName"]),
            "nombre": datos["DisplayName"], "editor": "", "version": "",
            "origen": "Epic Games", "juego": True,
            "carpeta": ubicacion if os.path.isdir(ubicacion) else "",
            "unidad": unidad_de(ubicacion),
            "bytes": int(tamano) if isinstance(tamano, (int, float)) and tamano > 0 else None,
            "estimado": False, "necesario": False,
            "desinstalar": {"tipo": "epic", "url": "com.epicgames.launcher://"},
            "manifiesto": manifiesto,
        })
    return juegos


def juegos_xbox():
    """Juegos de la app Xbox / Game Pass: se instalan en X:\\XboxGames de cada disco."""
    if SISTEMA != "Windows":
        return []
    juegos = []
    import string
    for letra in string.ascii_uppercase:
        raiz = letra + ":\\XboxGames"
        if not os.path.isdir(raiz):
            continue
        try:
            nombres = os.listdir(raiz)
        except OSError:
            continue
        for nombre in nombres:
            carpeta = os.path.join(raiz, nombre)
            if not os.path.isdir(carpeta) or nombre.lower() in ("gamesave", "temp"):
                continue
            juegos.append({
                "id": "xbox:" + carpeta.lower(),
                "nombre": nombre, "editor": "", "version": "",
                "origen": "Xbox", "juego": True,
                "carpeta": carpeta, "unidad": letra + ":",
                "bytes": None, "estimado": False, "necesario": False,
                "desinstalar": {"tipo": "ajustes", "url": "ms-settings:appsfeatures"},
            })
    return juegos


# ============================================================
#  Mac: aplicaciones
# ============================================================

def apps_mac():
    apps = []
    for raiz in ("/Applications", os.path.expanduser("~/Applications")):
        try:
            nombres = sorted(os.listdir(raiz))
        except OSError:
            continue
        for nombre in nombres:
            ruta = os.path.join(raiz, nombre)
            if not nombre.endswith(".app"):
                continue
            apps.append({
                "id": "mac:" + ruta,
                "nombre": nombre[:-4], "editor": "", "version": "",
                "origen": "Aplicación", "juego": False,
                "carpeta": ruta, "unidad": unidad_de(ruta),
                "bytes": None, "estimado": False,
                "necesario": False,
                "desinstalar": {"tipo": "papelera", "ruta": ruta},
            })
    return apps


# ============================================================
#  Todo junto
# ============================================================

PALABRAS_JUEGO = ["riot", "valorant", "league of legends", "battle.net", "ea app", "ubisoft", "rockstar",
                  "minecraft", "roblox", "fortnite", "genshin", "hoyoplay", "game", "juego"]


def listar():
    """Lista de todo lo instalado, sin duplicados, con los tamaños guardados de la última medición."""
    genericas = carpetas_genericas()
    if SISTEMA == "Windows":
        juegos = juegos_steam() + juegos_epic() + juegos_xbox()
        programas = programas_registro(genericas)
        ids_steam = {j["id"].split(":", 1)[1] for j in juegos if j["origen"] == "Steam"}
        filtrados = []
        for programa in programas:
            clave = programa["clave_registro"]
            if clave.startswith("Steam App ") and clave[len("Steam App "):] in ids_steam:
                continue                       # ya está en la lista de Steam, con su tamaño real
            filtrados.append(programa)
        lista = juegos + filtrados
    elif SISTEMA == "Darwin":
        lista = juegos_steam() + apps_mac()
    else:
        lista = juegos_steam()

    # Sin duplicados (un mismo programa puede aparecer en la parte de 32 y de 64 bits)
    unicos = []
    vistos = set()
    for programa in lista:
        llave = (programa["nombre"].lower(), _normal(programa["carpeta"]))
        if llave in vistos:
            continue
        vistos.add(llave)
        texto = (programa["nombre"] + " " + programa["editor"]).lower()
        if not programa["juego"] and any(palabra in texto for palabra in PALABRAS_JUEGO):
            programa["juego"] = "game bar" not in texto and "gameinput" not in texto
        unicos.append(programa)

    # Si dos programas comparten carpeta (por ejemplo, dos idiomas de Office), el tamaño se
    # cuenta una sola vez: en el primero
    duenos = {}
    for programa in sorted(unicos, key=lambda p: p["bytes"] or 0, reverse=True):
        carpeta = _normal(programa["carpeta"])
        if not carpeta:
            continue
        if carpeta in duenos:
            programa["comparte_con"] = duenos[carpeta]
            programa["bytes"] = None
            programa["estimado"] = False
        else:
            duenos[carpeta] = programa["nombre"]

    medidos = sistema.leer_json(ARCHIVO_TAMANOS, {})
    for programa in unicos:
        if programa.get("comparte_con"):
            continue
        guardado = medidos.get(_normal(programa["carpeta"]))
        if guardado:
            programa["bytes"] = guardado
            programa["estimado"] = False
    return unicos


# ============================================================
#  Medir el tamaño real de las carpetas (en segundo plano)
# ============================================================

def tamano_carpeta(ruta, excluir=(), detener=None):
    """Suma los archivos de una carpeta. No sigue accesos directos ni uniones (junctions),
    y salta las subcarpetas de 'excluir' (que pertenecen a otros programas)."""
    if not os.path.isdir(ruta):
        return None                 # la carpeta ya no existe: no se inventa un tamaño de 0
    total = 0
    pendientes = [ruta]
    while pendientes:
        if detener is not None and detener.is_set():
            return None
        actual = pendientes.pop()
        try:
            with os.scandir(actual) as entradas:
                for entrada in entradas:
                    try:
                        if entrada.is_symlink() or getattr(entrada, "is_junction", lambda: False)():
                            continue
                        if entrada.is_dir(follow_symlinks=False):
                            if _normal(entrada.path) not in excluir:
                                pendientes.append(entrada.path)
                        else:
                            total = total + entrada.stat(follow_symlinks=False).st_size
                    except OSError:
                        continue
        except OSError:
            continue
    return total


class Medicion:
    """Mide las carpetas de la lista en un hilo aparte. La página consulta 'avance' y 'listo'."""

    def __init__(self, programas):
        # Steam y Epic ya informan el tamaño exacto: solo se mide lo que no tiene tamaño o es aproximado
        self.todas = [_normal(p["carpeta"]) for p in programas if p["carpeta"]]
        self.programas = [p for p in programas if p["carpeta"] and not p.get("comparte_con")
                          and (p["bytes"] is None or p["estimado"] or p["origen"] in ("Programa", "Aplicación"))]
        self.avance = 0
        self.total = len(self.programas)
        self.listo = False
        self.cambios = 0
        self.detener = threading.Event()
        self.hilo = threading.Thread(target=self._medir, daemon=True)

    def iniciar(self):
        self.hilo.start()
        return self

    def cancelar(self):
        self.detener.set()

    def _medir(self):
        carpetas = self.todas
        guardados = sistema.leer_json(ARCHIVO_TAMANOS, {})
        # Los más pesados primero: así lo importante aparece antes
        orden = sorted(self.programas, key=lambda p: p["bytes"] or 0, reverse=True)
        for programa in orden:
            if self.detener.is_set():
                break
            propia = _normal(programa["carpeta"])
            # Las carpetas de otros programas que están DENTRO de esta no se cuentan dos veces
            # (por ejemplo, los juegos que viven dentro de la carpeta de Steam)
            excluir = {c for c in carpetas if c != propia and c.startswith(propia + os.sep)}
            tamano = tamano_carpeta(programa["carpeta"], excluir, self.detener)
            if tamano is not None:
                programa["bytes"] = tamano
                programa["estimado"] = False
                guardados[propia] = tamano
                self.cambios = self.cambios + 1
            self.avance = self.avance + 1
        try:
            sistema.guardar_json(ARCHIVO_TAMANOS, guardados)
        except OSError:
            pass
        self.listo = True


# ============================================================
#  Desinstalar
# ============================================================

def separar_comando(comando):
    comando = comando.strip()
    if comando.startswith('"'):
        fin = comando.find('"', 1)
        if fin > 0:
            return comando[1:fin], comando[fin + 1:].strip()
    encontrado = re.match(r"(.+?\.exe)\b(.*)", comando, re.IGNORECASE)
    if encontrado:
        return encontrado.group(1).strip(), encontrado.group(2).strip()
    partes = comando.split(" ", 1)
    return partes[0], (partes[1] if len(partes) > 1 else "")


def desinstalar(programa):
    """Abre el desinstalador del programa. Devuelve (True, mensaje) o (False, motivo)."""
    datos = programa.get("desinstalar") or {}
    tipo = datos.get("tipo")

    if tipo == "comando" and SISTEMA == "Windows":
        import ctypes
        try:
            ctypes.windll.ole32.CoInitialize(None)   # ShellExecute lo pide cuando se llama desde un hilo
        except Exception:
            pass
        programa_exe, argumentos = separar_comando(os.path.expandvars(datos["comando"]))
        if "msiexec" in programa_exe.lower():
            # "/I{...}" abre el modo de mantenimiento; "/X{...}" va directo a desinstalar
            argumentos = re.sub(r"(?i)/I\s*\{", "/X{", argumentos)
        # ShellExecute muestra el aviso de permisos de Windows cuando el desinstalador lo necesita
        resultado = ctypes.windll.shell32.ShellExecuteW(None, "open", programa_exe, argumentos, None, 1)
        if resultado > 32:
            return True, "Se abrió el desinstalador de " + programa["nombre"]
        if resultado == 5:
            return False, "Windows no dio permiso para abrir el desinstalador"
        return False, "No se encontró el desinstalador de " + programa["nombre"]

    if tipo in ("url", "epic", "ajustes"):
        sistema.abrir(datos["url"])
        if tipo == "epic":
            return True, "Se abrió Epic Games: desinstálalo desde tu Biblioteca"
        if tipo == "ajustes":
            return True, "Se abrió Aplicaciones instaladas: busca " + programa["nombre"]
        return True, "Steam te pedirá confirmar la desinstalación"

    if tipo == "papelera" and SISTEMA == "Darwin":
        ruta = datos["ruta"].replace('"', '\\"')
        codigo, texto = sistema.ejecutar_con_codigo(
            ["osascript", "-e", f'tell application "Finder" to delete (POSIX file "{ruta}")'])
        if codigo == 0:
            return True, programa["nombre"] + " se movió a la Papelera"
        return False, "macOS no permitió moverlo a la Papelera"

    return False, "Este programa no tiene desinstalador"


def sigue_instalado(programa):
    """Para saber si el usuario terminó de desinstalarlo."""
    if programa.get("registro") and SISTEMA == "Windows":
        import winreg
        datos = programa["registro"]
        raiz = winreg.HKEY_LOCAL_MACHINE if datos["raiz"] == "HKLM" else winreg.HKEY_CURRENT_USER
        try:
            winreg.CloseKey(winreg.OpenKey(raiz, RUTA_DESINSTALAR + "\\" + datos["clave"], 0,
                                           winreg.KEY_READ | datos["vista"]))
            return True
        except OSError:
            return False
    if programa.get("manifiesto"):
        return os.path.exists(programa["manifiesto"])
    if programa.get("carpeta"):
        return os.path.exists(programa["carpeta"])
    return True


def esperar_desinstalacion(programa, al_terminar, minutos=15):
    """Revisa cada 3 segundos si el programa ya no está, en un hilo aparte."""
    def revisar():
        limite = time.monotonic() + minutos * 60
        while time.monotonic() < limite:
            time.sleep(3)
            if not sigue_instalado(programa):
                al_terminar(programa)
                return
    threading.Thread(target=revisar, daemon=True).start()


def abrir_carpeta(programa):
    if programa.get("carpeta"):
        sistema.abrir(programa["carpeta"])
        return True
    return False


if __name__ == "__main__":
    for item in sorted(listar(), key=lambda p: p["bytes"] or 0, reverse=True)[:30]:
        megas = (item["bytes"] or 0) / 1024 ** 2
        print(f"{megas:10.0f} MB  {item['unidad']:4} {item['origen']:10} {item['nombre']}")
