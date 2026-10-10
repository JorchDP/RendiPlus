"""
sistema.py  -  Herramientas compartidas por todos los motores de RendiPlus:
ejecutar comandos, leer/escribir el registro de Windows, permisos y archivos de datos.
"""

import ctypes
import json
import os
import platform
import subprocess
import sys

SISTEMA = platform.system()   # "Windows", "Darwin" (= macOS) o "Linux"
NOMBRE_APP = "RendiPlus"


# ============================================================
#  Ejecutar comandos del sistema
# ============================================================

def decodificar(datos):
    """Convierte la salida de un comando en texto, probando varias codificaciones
    (en Windows en español, comandos como powercfg no usan UTF-8)."""
    if not datos:
        return ""
    try:
        return datos.decode("utf-8")
    except UnicodeDecodeError:
        pass
    for codigo in ("oem", "mbcs", "cp850", "latin-1"):
        try:
            return datos.decode(codigo)
        except (LookupError, UnicodeDecodeError):
            continue
    return datos.decode("utf-8", errors="replace")


def ejecutar_con_codigo(comando, tiempo_maximo=60):
    """Ejecuta un comando. Devuelve (codigo, texto). Código 0 = todo bien."""
    try:
        if SISTEMA == "Windows":
            resultado = subprocess.run(
                comando, capture_output=True, timeout=tiempo_maximo,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        else:
            resultado = subprocess.run(comando, capture_output=True, timeout=tiempo_maximo)
        texto = decodificar(resultado.stdout) + decodificar(resultado.stderr)
        return resultado.returncode, texto.strip()
    except Exception as error:
        return -1, str(error)


def ejecutar(comando, tiempo_maximo=60):
    """Ejecuta un comando y devuelve solo su texto."""
    codigo, texto = ejecutar_con_codigo(comando, tiempo_maximo)
    return texto


def powershell_json(script):
    """(Solo Windows) Ejecuta PowerShell y convierte el resultado (JSON) en datos de Python."""
    comando = ["powershell", "-NoProfile", "-NonInteractive", "-Command",
               script + " | ConvertTo-Json -Depth 4 -Compress"]
    try:
        resultado = subprocess.run(
            comando, capture_output=True, timeout=90,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        texto = decodificar(resultado.stdout).strip()
        if not texto:
            return None
        return json.loads(texto)
    except Exception:
        return None


def como_lista(datos):
    """PowerShell devuelve un objeto suelto cuando hay un solo resultado: lo pasamos a lista."""
    if datos is None:
        return []
    if isinstance(datos, list):
        return datos
    return [datos]


# ============================================================
#  Permisos
# ============================================================

def es_admin():
    try:
        if SISTEMA == "Windows":
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        return os.geteuid() == 0
    except Exception:
        return False


def reiniciar_como_admin():
    """(Solo Windows) Vuelve a abrir la app pidiendo permisos de administrador."""
    if SISTEMA != "Windows":
        return False
    if getattr(sys, "frozen", False):
        # Versión .exe: se relanza a sí misma
        programa = sys.executable
        argumentos = ""
    else:
        programa = sys.executable
        argumentos = '"' + os.path.abspath(sys.argv[0]) + '"'
    resultado = ctypes.windll.shell32.ShellExecuteW(
        None, "runas", programa, argumentos, os.getcwd(), 1
    )
    return resultado > 32


# ============================================================
#  Registro de Windows
# ============================================================

def _raiz(nombre):
    import winreg
    if nombre == "HKLM":
        return winreg.HKEY_LOCAL_MACHINE
    return winreg.HKEY_CURRENT_USER


def leer_registro(raiz, ruta, nombre, defecto=None):
    """Lee un valor del registro. Si no existe, devuelve 'defecto'."""
    try:
        import winreg
        acceso = winreg.KEY_READ | winreg.KEY_WOW64_64KEY
        with winreg.OpenKey(_raiz(raiz), ruta, 0, acceso) as clave:
            return winreg.QueryValueEx(clave, nombre)[0]
    except Exception:
        return defecto


def escribir_registro(raiz, ruta, nombre, valor, tipo="dword"):
    """Escribe un valor en el registro. Devuelve True si funcionó."""
    try:
        import winreg
        acceso = winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY
        with winreg.CreateKeyEx(_raiz(raiz), ruta, 0, acceso) as clave:
            if tipo == "binario":
                winreg.SetValueEx(clave, nombre, 0, winreg.REG_BINARY, valor)
            elif tipo == "texto":
                winreg.SetValueEx(clave, nombre, 0, winreg.REG_SZ, str(valor))
            else:
                winreg.SetValueEx(clave, nombre, 0, winreg.REG_DWORD, int(valor))
        return True
    except Exception:
        return False


def borrar_valor_registro(raiz, ruta, nombre):
    try:
        import winreg
        acceso = winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY
        with winreg.OpenKey(_raiz(raiz), ruta, 0, acceso) as clave:
            winreg.DeleteValue(clave, nombre)
        return True
    except FileNotFoundError:
        return True
    except Exception:
        return False


def valores_registro(raiz, ruta):
    """Lista todos los valores de una clave: [(nombre, dato), ...]."""
    lista = []
    try:
        import winreg
        acceso = winreg.KEY_READ | winreg.KEY_WOW64_64KEY
        with winreg.OpenKey(_raiz(raiz), ruta, 0, acceso) as clave:
            indice = 0
            while True:
                try:
                    nombre, dato, tipo = winreg.EnumValue(clave, indice)
                except OSError:
                    break
                lista.append((nombre, dato))
                indice = indice + 1
    except Exception:
        pass
    return lista


# ============================================================
#  Archivos de datos de la app (historial, configuración)
# ============================================================

def carpeta_datos():
    if SISTEMA == "Windows":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    elif SISTEMA == "Darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.path.expanduser("~/.config")
    carpeta = os.path.join(base, NOMBRE_APP)
    os.makedirs(carpeta, exist_ok=True)
    return carpeta


def leer_json(nombre, defecto):
    try:
        with open(os.path.join(carpeta_datos(), nombre), encoding="utf-8") as archivo:
            return json.load(archivo)
    except Exception:
        return defecto


def guardar_json(nombre, datos):
    ruta = os.path.join(carpeta_datos(), nombre)
    temporal = ruta + ".tmp"
    with open(temporal, "w", encoding="utf-8") as archivo:
        json.dump(datos, archivo, ensure_ascii=False, indent=2)
    os.replace(temporal, ruta)   # así nunca queda un archivo a medio escribir


def leer_config(clave, defecto=None):
    return leer_json("config.json", {}).get(clave, defecto)


def guardar_config(clave, valor):
    config = leer_json("config.json", {})
    config[clave] = valor
    guardar_json("config.json", config)


def abrir(ruta):
    """Abre una carpeta, archivo o enlace con el programa predeterminado."""
    try:
        if SISTEMA == "Windows":
            os.startfile(ruta)
        elif SISTEMA == "Darwin":
            subprocess.Popen(["open", ruta])
        else:
            subprocess.Popen(["xdg-open", ruta])
    except Exception:
        pass
