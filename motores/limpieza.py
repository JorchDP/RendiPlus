"""
limpieza.py  -  OptiPC, Fase 2: Limpieza
Busca archivos basura (temporales, cachés, papelera...) y los borra de forma segura.
Funciona en Windows y macOS (y también en Linux).

Igual que hardware.py, este archivo NO tiene interfaz: solo hace el trabajo.

Reglas de seguridad que sigue SIEMPRE:
  1. Solo toca las carpetas de la lista de categorías (nunca tus documentos).
  2. Nunca sigue accesos directos ni enlaces a otras carpetas.
  3. En temporales y cachés de apps, solo borra archivos con más de 24 horas
     (así no rompe algo que un programa esté usando justo ahora).
  4. Si un archivo está en uso o no hay permiso, lo salta sin detenerse.
  5. Los "archivos grandes" solo se MUESTRAN; nunca se borran automáticamente.
"""

import ctypes
import glob
import os
import platform
import stat
import subprocess
import sys
import time

import psutil

SISTEMA = platform.system()   # "Windows", "Darwin" (= macOS) o "Linux"
CASA = os.path.expanduser("~")


# ============================================================
#  Funciones de ayuda
# ============================================================

def formato_tamano(cantidad_bytes):
    """Convierte bytes a un texto fácil de leer: 15 KB, 340 MB, 2.4 GB."""
    if cantidad_bytes >= 1024 ** 3:
        return f"{cantidad_bytes / 1024 ** 3:.1f} GB"
    if cantidad_bytes >= 1024 ** 2:
        return f"{cantidad_bytes / 1024 ** 2:.0f} MB"
    if cantidad_bytes >= 1024:
        return f"{cantidad_bytes / 1024:.0f} KB"
    return f"{cantidad_bytes} B"


def variable(nombre):
    """Lee una variable de entorno de Windows (p. ej. LOCALAPPDATA). Devuelve '' si no existe."""
    return os.environ.get(nombre, "")


def es_admin():
    """¿La app se está ejecutando como administrador?"""
    try:
        if SISTEMA == "Windows":
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        return os.geteuid() == 0
    except Exception:
        return False


def reiniciar_como_admin():
    """(Solo Windows) Vuelve a abrir la app pidiendo permisos de administrador.
    Devuelve True si Windows aceptó abrirla."""
    if SISTEMA != "Windows":
        return False
    script = os.path.abspath(sys.argv[0])
    resultado = ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, '"' + script + '"', os.path.dirname(script), 1
    )
    return resultado > 32   # Windows devuelve un número mayor a 32 si funcionó


def ruta_segura(ruta):
    """Protección extra: rechaza rutas peligrosas aunque alguien las agregue por error
    (la raíz del disco, tu carpeta de usuario, carpetas del sistema, etc.)."""
    if not ruta:
        return False
    ruta = os.path.normcase(os.path.abspath(ruta))
    prohibidas = [CASA, os.path.dirname(CASA), "/", "/users", "/home", "/system", "/library"]
    if SISTEMA == "Windows":
        prohibidas = prohibidas + [
            "c:\\", "c:\\windows", "c:\\windows\\system32",
            "c:\\program files", "c:\\program files (x86)", "c:\\users",
        ]
    for prohibida in prohibidas:
        if ruta == os.path.normcase(os.path.abspath(prohibida)):
            return False
    # Debe tener al menos 3 niveles de profundidad (p. ej. C:\Users\Javi\...)
    partes = [p for p in ruta.replace("\\", "/").split("/") if p]
    return len(partes) >= 3


def es_enlace(ruta):
    """True si la ruta es un enlace simbólico o un 'junction' de Windows."""
    if os.path.islink(ruta):
        return True
    if hasattr(os.path, "isjunction") and os.path.isjunction(ruta):
        return True
    return False


def apps_abiertas(nombres):
    """De una lista de nombres de procesos, devuelve los que están abiertos ahora."""
    buscados = [n.lower() for n in nombres]
    encontrados = []
    for proceso in psutil.process_iter(["name"]):
        nombre = (proceso.info["name"] or "").lower()
        if nombre in buscados and nombre not in encontrados:
            encontrados.append(nombre)
    return encontrados


# ============================================================
#  Categorías de limpieza según el sistema
# ============================================================

def nueva_categoria(id_categoria, nombre, descripcion, rutas, edad_horas=24,
                    recomendado=True, requiere_admin=False, procesos=None, excluir=None):
    """Arma el diccionario de una categoría. Las rutas pueden llevar * (comodines)."""
    rutas_reales = []
    for ruta in rutas:
        if not ruta:
            continue
        for encontrada in glob.glob(ruta):
            if os.path.isdir(encontrada) and ruta_segura(encontrada):
                rutas_reales.append(encontrada)

    return {
        "id": id_categoria,
        "nombre": nombre,
        "descripcion": descripcion,
        "tipo": "carpetas",
        "rutas": rutas_reales,
        "edad_horas": edad_horas,
        "recomendado": recomendado,
        "requiere_admin": requiere_admin,
        "procesos": procesos or [],
        "excluir": [os.path.normcase(e) for e in (excluir or [])],
    }


def categoria_papelera():
    return {
        "id": "papelera",
        "nombre": "Papelera de reciclaje",
        "descripcion": "Archivos que ya borraste pero siguen ocupando espacio.",
        "tipo": "papelera",
        "rutas": [],
        "edad_horas": 0,
        "recomendado": True,
        "requiere_admin": False,
        "procesos": [],
        "excluir": [],
    }


def categorias_windows():
    local = variable("LOCALAPPDATA")
    roaming = variable("APPDATA")
    windir = variable("WINDIR") or "C:\\Windows"
    programdata = variable("PROGRAMDATA") or "C:\\ProgramData"

    navegadores = []
    for carpeta in [
        local + "\\Google\\Chrome\\User Data\\*",
        local + "\\Microsoft\\Edge\\User Data\\*",
        local + "\\BraveSoftware\\Brave-Browser\\User Data\\*",
    ]:
        navegadores.append(carpeta + "\\Cache")
        navegadores.append(carpeta + "\\Code Cache")
        navegadores.append(carpeta + "\\GPUCache")
    navegadores.append(local + "\\Mozilla\\Firefox\\Profiles\\*\\cache2")

    return [
        nueva_categoria(
            "temp_usuario", "Archivos temporales",
            "Archivos que los programas crean y olvidan borrar.",
            [variable("TEMP")],
        ),
        nueva_categoria(
            "temp_windows", "Temporales de Windows",
            "Temporales del propio sistema.",
            [windir + "\\Temp"], requiere_admin=True,
        ),
        categoria_papelera(),
        nueva_categoria(
            "navegadores", "Caché de navegadores",
            "Chrome, Edge, Brave y Firefox. No borra contraseñas, historial ni sesiones.",
            navegadores, edad_horas=0,
            procesos=["chrome.exe", "msedge.exe", "brave.exe", "firefox.exe"],
        ),
        nueva_categoria(
            "discord", "Caché de Discord",
            "Imágenes y videos que Discord guarda para cargar más rápido.",
            [roaming + "\\discord\\Cache", roaming + "\\discord\\Code Cache",
             roaming + "\\discord\\GPUCache"],
            edad_horas=0, procesos=["discord.exe"],
        ),
        nueva_categoria(
            "windows_update", "Descargas de Windows Update",
            "Instaladores de actualizaciones que ya se aplicaron.",
            [windir + "\\SoftwareDistribution\\Download"], requiere_admin=True,
        ),
        nueva_categoria(
            "errores", "Informes de errores",
            "Volcados de memoria y reportes de fallos antiguos.",
            [local + "\\CrashDumps",
             programdata + "\\Microsoft\\Windows\\WER\\ReportArchive",
             programdata + "\\Microsoft\\Windows\\WER\\ReportQueue"],
            edad_horas=0, requiere_admin=True,
        ),
        nueva_categoria(
            "shaders", "Caché de shaders (juegos)",
            "Ojo: los juegos pueden dar tirones la primera vez mientras la regeneran. "
            "Solo vale la pena si la caché está corrupta o necesitas espacio.",
            [local + "\\D3DSCache", local + "\\NVIDIA\\DXCache", local + "\\NVIDIA\\GLCache",
             local + "\\AMD\\DxCache", local + "\\AMD\\DxcCache"],
            edad_horas=0, recomendado=False,
        ),
    ]


def categorias_mac():
    cache = CASA + "/Library/Caches"
    cache_navegadores = [
        cache + "/Google/Chrome",
        cache + "/com.apple.Safari",
        cache + "/Firefox",
        cache + "/BraveSoftware",
        cache + "/Microsoft Edge",
    ]
    return [
        nueva_categoria(
            "cache_apps", "Caché de aplicaciones",
            "Datos temporales que las apps vuelven a crear cuando los necesitan.",
            [cache], excluir=cache_navegadores,
        ),
        categoria_papelera(),
        nueva_categoria(
            "navegadores", "Caché de navegadores",
            "Chrome, Safari, Firefox, Brave y Edge. No borra contraseñas ni historial.",
            cache_navegadores, edad_horas=0,
            procesos=["Google Chrome", "Safari", "firefox", "Brave Browser", "Microsoft Edge"],
        ),
        nueva_categoria(
            "discord", "Caché de Discord",
            "Imágenes y videos que Discord guarda para cargar más rápido.",
            [CASA + "/Library/Application Support/discord/Cache",
             CASA + "/Library/Application Support/discord/Code Cache"],
            edad_horas=0, procesos=["Discord"],
        ),
        nueva_categoria(
            "logs", "Registros (logs)",
            "Archivos de registro que las apps guardan para diagnosticar fallos.",
            [CASA + "/Library/Logs"],
        ),
        nueva_categoria(
            "xcode", "Datos de compilación de Xcode",
            "Solo si programas en Xcode. Se regeneran al compilar.",
            [CASA + "/Library/Developer/Xcode/DerivedData"], edad_horas=0, recomendado=False,
        ),
    ]


def categorias_linux():
    return [
        nueva_categoria(
            "cache_apps", "Caché de aplicaciones",
            "Datos temporales que las apps vuelven a crear cuando los necesitan.",
            [CASA + "/.cache"],
        ),
        categoria_papelera(),
        nueva_categoria(
            "temp_usuario", "Archivos temporales",
            "Archivos temporales antiguos (solo los tuyos).",
            ["/tmp"],
        ),
    ]


def obtener_categorias():
    """Devuelve la lista de categorías del sistema actual.
    Cada una lleva 'disponible' y 'nota' (por qué no se puede usar, si aplica)."""
    if SISTEMA == "Windows":
        categorias = categorias_windows()
    elif SISTEMA == "Darwin":
        categorias = categorias_mac()
    else:
        categorias = categorias_linux()

    administrador = es_admin()
    resultado = []
    for categoria in categorias:
        if categoria["tipo"] == "carpetas" and not categoria["rutas"]:
            continue   # esa app/carpeta no existe en este PC: no la mostramos
        categoria["disponible"] = True
        categoria["nota"] = ""
        if categoria["requiere_admin"] and not administrador:
            categoria["disponible"] = False
            categoria["nota"] = "Requiere abrir la app como administrador"
        resultado.append(categoria)
    return resultado


# ============================================================
#  Recorrer carpetas de forma segura
# ============================================================

def archivos_de_categoria(categoria):
    """Lista los archivos que se pueden borrar: (ruta, tamaño) de cada uno."""
    limite = time.time() - categoria["edad_horas"] * 3600
    archivos = []

    for ruta_base in categoria["rutas"]:
        for carpeta, subcarpetas, nombres in os.walk(ruta_base, followlinks=False):
            # Quitamos de la búsqueda los enlaces y las carpetas excluidas
            quedarse = []
            for sub in subcarpetas:
                ruta_sub = os.path.join(carpeta, sub)
                if es_enlace(ruta_sub):
                    continue
                if os.path.normcase(ruta_sub) in categoria["excluir"]:
                    continue
                quedarse.append(sub)
            subcarpetas[:] = quedarse

            for nombre in nombres:
                ruta = os.path.join(carpeta, nombre)
                try:
                    info = os.lstat(ruta)
                except OSError:
                    continue
                if not stat.S_ISREG(info.st_mode):
                    continue   # no es un archivo normal (enlace, dispositivo...)
                if info.st_mtime > limite:
                    continue   # es muy reciente: puede estar en uso
                archivos.append((ruta, info.st_size))
    return archivos


def borrar_carpetas_vacias(categoria):
    """Después de limpiar, borra las subcarpetas que quedaron vacías
    (nunca la carpeta principal de la categoría)."""
    for ruta_base in categoria["rutas"]:
        for carpeta, subcarpetas, nombres in os.walk(ruta_base, topdown=False, followlinks=False):
            if os.path.normcase(carpeta) == os.path.normcase(ruta_base):
                continue
            if es_enlace(carpeta):
                continue
            try:
                os.rmdir(carpeta)   # solo funciona si está vacía; si no, da error y la dejamos
            except OSError:
                pass


# ============================================================
#  Papelera
# ============================================================

def carpeta_papelera():
    if SISTEMA == "Darwin":
        return CASA + "/.Trash"
    return CASA + "/.local/share/Trash"


def analizar_papelera():
    if SISTEMA == "Windows":
        # Le preguntamos a Windows directamente cuánto ocupa la papelera
        class InfoPapelera(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_ulong),
                        ("i64Size", ctypes.c_longlong),
                        ("i64NumItems", ctypes.c_longlong)]

        info = InfoPapelera()
        info.cbSize = ctypes.sizeof(info)
        if ctypes.windll.shell32.SHQueryRecycleBinW(None, ctypes.byref(info)) == 0:
            return {"bytes": info.i64Size, "archivos": info.i64NumItems, "error": ""}
        return {"bytes": 0, "archivos": 0, "error": "No se pudo leer la papelera"}

    total = 0
    cantidad = 0
    try:
        for carpeta, subcarpetas, nombres in os.walk(carpeta_papelera(), followlinks=False):
            for nombre in nombres:
                try:
                    total = total + os.lstat(os.path.join(carpeta, nombre)).st_size
                    cantidad = cantidad + 1
                except OSError:
                    pass
        if SISTEMA == "Darwin":
            os.listdir(carpeta_papelera())   # en Mac moderno puede pedir permiso
    except PermissionError:
        return {"bytes": 0, "archivos": 0,
                "error": "Sin permiso para ver la papelera (se puede vaciar igual)"}
    return {"bytes": total, "archivos": cantidad, "error": ""}


def vaciar_papelera():
    antes = analizar_papelera()
    if SISTEMA == "Windows":
        # 7 = sin pedir confirmación, sin barra de progreso y sin sonido
        ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 7)
    elif SISTEMA == "Darwin":
        subprocess.run(
            ["osascript", "-e", 'tell application "Finder" to empty trash'],
            capture_output=True, timeout=120,
        )
    else:
        categoria = nueva_categoria("papelera", "", "", [carpeta_papelera() + "/files",
                                                         carpeta_papelera() + "/info"], edad_horas=0)
        borrar_archivos(categoria)
        borrar_carpetas_vacias(categoria)
    despues = analizar_papelera()
    liberado = max(antes["bytes"] - despues["bytes"], 0)
    borrados = max(antes["archivos"] - despues["archivos"], 0)
    return {"liberado": liberado, "borrados": borrados, "fallidos": despues["archivos"]}


# ============================================================
#  Analizar y limpiar
# ============================================================

def analizar_categoria(categoria):
    """Calcula cuánto espacio se puede liberar en una categoría (sin borrar nada)."""
    if categoria["tipo"] == "papelera":
        return analizar_papelera()
    archivos = archivos_de_categoria(categoria)
    total = 0
    for ruta, tamano in archivos:
        total = total + tamano
    return {"bytes": total, "archivos": len(archivos), "error": ""}


def borrar_archivos(categoria):
    liberado = 0
    borrados = 0
    fallidos = 0
    for ruta, tamano in archivos_de_categoria(categoria):
        try:
            os.remove(ruta)
            liberado = liberado + tamano
            borrados = borrados + 1
        except OSError:
            fallidos = fallidos + 1   # en uso o sin permiso: lo saltamos
    return {"liberado": liberado, "borrados": borrados, "fallidos": fallidos}


def limpiar_categoria(categoria):
    """Borra los archivos de una categoría. Devuelve cuánto se liberó."""
    if not categoria.get("disponible", True):
        return {"liberado": 0, "borrados": 0, "fallidos": 0}
    if categoria["tipo"] == "papelera":
        return vaciar_papelera()
    resultado = borrar_archivos(categoria)
    borrar_carpetas_vacias(categoria)
    return resultado


def espacio_libre_principal():
    """Espacio libre del disco donde está tu usuario (C: en Windows)."""
    try:
        return psutil.disk_usage(CASA).free
    except Exception:
        return 0


# ============================================================
#  Archivos grandes (solo se muestran, nunca se borran solos)
# ============================================================

def carpetas_personales():
    nombres = ["Downloads", "Desktop", "Documents", "Videos", "Movies",
               "Descargas", "Escritorio", "Documentos", "Vídeos"]
    carpetas = []
    for nombre in nombres:
        ruta = os.path.join(CASA, nombre)
        if os.path.isdir(ruta) and ruta not in carpetas:
            carpetas.append(ruta)
    return carpetas


def buscar_archivos_grandes(minimo_mb=500, maximo=25):
    """Busca archivos pesados en Descargas, Escritorio, Documentos y Videos."""
    minimo = minimo_mb * 1024 * 1024
    encontrados = []
    for base in carpetas_personales():
        for carpeta, subcarpetas, nombres in os.walk(base, followlinks=False):
            quedarse = []
            for sub in subcarpetas:
                if sub.startswith(".") or es_enlace(os.path.join(carpeta, sub)):
                    continue
                quedarse.append(sub)
            subcarpetas[:] = quedarse

            for nombre in nombres:
                ruta = os.path.join(carpeta, nombre)
                try:
                    info = os.lstat(ruta)
                except OSError:
                    continue
                if stat.S_ISREG(info.st_mode) and info.st_size >= minimo:
                    encontrados.append({
                        "ruta": ruta,
                        "nombre": nombre,
                        "tamano": info.st_size,
                        "dias": int((time.time() - info.st_mtime) / 86400),
                    })

    encontrados.sort(key=lambda archivo: archivo["tamano"], reverse=True)
    return encontrados[:maximo]


def mostrar_en_carpeta(ruta):
    """Abre el explorador de archivos con el archivo seleccionado."""
    try:
        if SISTEMA == "Windows":
            subprocess.Popen(["explorer", "/select,", os.path.normpath(ruta)])
        elif SISTEMA == "Darwin":
            subprocess.Popen(["open", "-R", ruta])
        else:
            subprocess.Popen(["xdg-open", os.path.dirname(ruta)])
    except Exception:
        pass


# Si ejecutas este archivo directo (python limpieza.py), solo ANALIZA (no borra nada)
if __name__ == "__main__":
    print("Administrador:", es_admin())
    for categoria in obtener_categorias():
        resultado = analizar_categoria(categoria)
        print(f"{categoria['nombre']:<32} {formato_tamano(resultado['bytes']):>10}"
              f"   {resultado['archivos']} archivos   {categoria['nota']}")
    print()
    print("Archivos grandes:")
    for archivo in buscar_archivos_grandes():
        print(" ", formato_tamano(archivo["tamano"]), archivo["ruta"])
