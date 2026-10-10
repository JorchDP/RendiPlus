"""
hardware.py  -  Motor de diagnóstico de RendiPlus
Lee los componentes del PC y su uso en tiempo real. Funciona en Windows y macOS.

Convención: en los diccionarios que devuelve, las claves que empiezan con "_"
son datos internos (números para el motor de recomendaciones) y no se muestran.
"""

import ctypes
import datetime
import json
import platform
import re
import threading
import time

import psutil

from motores.sistema import SISTEMA, como_lista, ejecutar, powershell_json

# --- Soporte opcional para GPUs NVIDIA (uso, VRAM y temperatura en vivo) ---
# Se inicia en segundo plano (iniciar_nvidia): el driver puede tardar en responder
# y no queremos que la ventana espere por eso.
NVIDIA_OK = False
try:
    import pynvml
except Exception:
    pynvml = None


def iniciar_nvidia():
    global NVIDIA_OK
    if pynvml is None:
        return False
    try:
        pynvml.nvmlInit()
        NVIDIA_OK = pynvml.nvmlDeviceGetCount() > 0
    except Exception:
        NVIDIA_OK = False
    return NVIDIA_OK

psutil.cpu_percent(interval=None)   # la primera lectura siempre da 0: la "calentamos"

_cache = {}


def a_gb(cantidad_bytes):
    return round(cantidad_bytes / (1024 ** 3), 1)


# ============================================================
#  Windows: una sola consulta a PowerShell para todo (más rápido)
# ============================================================

SCRIPT_WINDOWS = "; ".join([
    "$ErrorActionPreference = 'SilentlyContinue'",
    "$r = [ordered]@{}",
    "$r.mem = @(Get-CimInstance Win32_PhysicalMemory | "
    "Select-Object Capacity, Speed, ConfiguredClockSpeed, SMBIOSMemoryType)",
    "$r.gpu = @(Get-CimInstance Win32_VideoController | Select-Object Name, AdapterRAM, "
    "DriverVersion, @{n='Fecha';e={$_.DriverDate.ToString('yyyy-MM-dd')}})",
    "$r.discos = @(Get-PhysicalDisk | Select-Object DeviceId, FriendlyName, MediaType, BusType, Size)",
    "$r.particiones = @(Get-Partition | Where-Object DriveLetter | "
    "Select-Object @{n='Letra';e={[string]$_.DriveLetter}}, DiskNumber)",
    "$r",
])


def datos_windows():
    if "windows" not in _cache:
        _cache["windows"] = powershell_json(SCRIPT_WINDOWS) or {}
    return _cache["windows"]


# ============================================================
#  Sistema operativo
# ============================================================

def info_sistema():
    if SISTEMA == "Darwin":
        nombre = "macOS " + platform.mac_ver()[0]
    elif SISTEMA == "Windows":
        build = platform.version().split(".")[-1]
        if build.isdigit() and int(build) >= 22000:
            nombre = "Windows 11"
        else:
            nombre = "Windows " + platform.release()
        nombre = nombre + " (build " + build + ")"
    else:
        nombre = platform.system() + " " + platform.release()

    bateria = None
    try:
        bateria = psutil.sensors_battery()
    except Exception:
        pass

    return {
        "Sistema": nombre,
        "Equipo": platform.node(),
        "Tipo": "Portátil" if bateria is not None else "Escritorio",
        "_portatil": bateria is not None,
        "_nombre_corto": nombre.split(" (")[0],
    }


# ============================================================
#  Procesador
# ============================================================

def nombre_cpu():
    if SISTEMA == "Windows":
        try:
            import winreg
            clave = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                   r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            return winreg.QueryValueEx(clave, "ProcessorNameString")[0].strip()
        except Exception:
            pass
    elif SISTEMA == "Darwin":
        nombre = ejecutar(["sysctl", "-n", "machdep.cpu.brand_string"])
        if nombre:
            return nombre
    else:
        try:
            with open("/proc/cpuinfo") as archivo:
                for linea in archivo:
                    if linea.startswith("model name"):
                        return linea.split(":", 1)[1].strip()
        except Exception:
            pass
    return platform.processor() or "Desconocido"


def info_cpu():
    fisicos = psutil.cpu_count(logical=False)
    logicos = psutil.cpu_count(logical=True)
    nombre = nombre_cpu()
    datos = {"Modelo": nombre}

    if fisicos:
        datos["Núcleos"] = f"{fisicos} núcleos, {logicos} hilos"
    else:
        datos["Núcleos"] = f"{logicos} hilos"

    if SISTEMA == "Darwin":
        rendimiento = ejecutar(["sysctl", "-n", "hw.perflevel0.physicalcpu"])
        eficiencia = ejecutar(["sysctl", "-n", "hw.perflevel1.physicalcpu"])
        if rendimiento.isdigit() and eficiencia.isdigit():
            datos["Tipo de núcleos"] = f"{rendimiento} de rendimiento y {eficiencia} de eficiencia"

    try:
        frecuencia = psutil.cpu_freq()
        if frecuencia and frecuencia.max:
            datos["Frecuencia"] = f"{round(frecuencia.max / 1000, 2)} GHz"
        elif frecuencia and frecuencia.current:
            datos["Frecuencia"] = f"{round(frecuencia.current / 1000, 2)} GHz"
    except Exception:
        pass

    minuscula = nombre.lower()
    if "amd" in minuscula or "ryzen" in minuscula:
        datos["_marca"] = "AMD"
    elif "intel" in minuscula:
        datos["_marca"] = "Intel"
    elif "apple" in minuscula:
        datos["_marca"] = "Apple"
    else:
        datos["_marca"] = ""
    return datos


# ============================================================
#  Memoria RAM
# ============================================================

TIPOS_RAM = {20: "DDR", 21: "DDR2", 24: "DDR3", 26: "DDR4", 34: "DDR5", 35: "LPDDR5"}


def info_ram():
    memoria = psutil.virtual_memory()
    datos = {"Total": f"{a_gb(memoria.total)} GB", "_total_gb": a_gb(memoria.total)}

    if SISTEMA == "Windows":
        modulos = como_lista(datos_windows().get("mem"))
        if modulos:
            tamanos = []
            for modulo in modulos:
                tamanos.append(round(a_gb(int(modulo.get("Capacity") or 0))))
            textos = []
            for tamano in tamanos:
                textos.append(f"{tamano} GB")
            datos["Módulos"] = f"{len(modulos)} ({' + '.join(textos)})"

            tipo = TIPOS_RAM.get(modulos[0].get("SMBIOSMemoryType"), "")
            velocidad = modulos[0].get("ConfiguredClockSpeed") or modulos[0].get("Speed")
            if velocidad:
                datos["Velocidad"] = f"{tipo} {velocidad} MT/s".strip()

            datos["_modulos"] = tamanos
            datos["_tipo"] = tipo
            datos["_velocidad"] = int(velocidad or 0)
            datos["_velocidad_nominal"] = int(modulos[0].get("Speed") or 0)

    elif SISTEMA == "Darwin":
        texto = ejecutar(["system_profiler", "SPMemoryDataType", "-json"])
        try:
            info = json.loads(texto)["SPMemoryDataType"][0]
            if info.get("dimm_type"):
                datos["Tipo"] = info["dimm_type"]
        except Exception:
            pass
        if platform.machine() == "arm64":
            datos["Arquitectura"] = "Memoria unificada"
    return datos


# ============================================================
#  Tarjeta gráfica
# ============================================================

def vram_windows():
    """Lee la VRAM real desde el registro (Win32_VideoController no pasa de 4 GB)."""
    resultado = {}
    try:
        import winreg
        ruta = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
        clase = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, ruta)
        indice = 0
        while True:
            try:
                subclave = winreg.EnumKey(clase, indice)
            except OSError:
                break
            indice = indice + 1
            try:
                clave = winreg.OpenKey(clase, subclave)
                nombre = winreg.QueryValueEx(clave, "DriverDesc")[0]
                memoria = winreg.QueryValueEx(clave, "HardwareInformation.qwMemorySize")[0]
                if isinstance(memoria, bytes):
                    memoria = int.from_bytes(memoria, "little")
                resultado[nombre.strip()] = int(memoria)
            except Exception:
                pass
    except Exception:
        pass
    return resultado


def info_gpus():
    gpus = []

    if SISTEMA == "Windows":
        vram_registro = vram_windows()
        for controlador in como_lista(datos_windows().get("gpu")):
            nombre = (controlador.get("Name") or "Desconocida").strip()
            if "Remote Display" in nombre or "Basic Display" in nombre:
                continue
            gpu = {"Modelo": nombre, "_nombre": nombre}
            vram = vram_registro.get(nombre) or controlador.get("AdapterRAM") or 0
            if vram:
                gpu["VRAM"] = f"{a_gb(int(vram))} GB"
                gpu["_vram_gb"] = a_gb(int(vram))
            if controlador.get("DriverVersion"):
                gpu["Driver"] = controlador["DriverVersion"]
            fecha = controlador.get("Fecha")
            if fecha:
                try:
                    dia = datetime.date.fromisoformat(str(fecha)[:10])
                    gpu["Fecha del driver"] = dia.strftime("%d-%m-%Y")
                    gpu["_dias_driver"] = (datetime.date.today() - dia).days
                except ValueError:
                    pass
            gpus.append(gpu)

    elif SISTEMA == "Darwin":
        texto = ejecutar(["system_profiler", "SPDisplaysDataType", "-json"])
        try:
            lista = json.loads(texto).get("SPDisplaysDataType", [])
        except Exception:
            lista = []
        for item in lista:
            nombre = item.get("sppci_model") or item.get("_name") or "Desconocida"
            gpu = {"Modelo": nombre, "_nombre": nombre}
            if item.get("sppci_cores"):
                gpu["Núcleos GPU"] = str(item["sppci_cores"])
            vram = item.get("spdisplays_vram") or item.get("spdisplays_vram_shared")
            if vram:
                gpu["VRAM"] = vram
            elif "Apple" in nombre:
                gpu["VRAM"] = "Compartida con la RAM"
            gpus.append(gpu)

    else:
        for linea in ejecutar(["lspci"]).splitlines():
            if "VGA" in linea or "3D controller" in linea:
                nombre = linea.split(": ", 1)[-1]
                gpus.append({"Modelo": nombre, "_nombre": nombre})

    if not gpus:
        gpus.append({"Modelo": "No detectada", "_nombre": ""})
    return gpus


# ============================================================
#  Pantalla (resolución y frecuencia)
# ============================================================

class _ModoPantalla(ctypes.Structure):
    """Molde de la estructura DEVMODEW de Windows (describe un modo de pantalla)."""
    _fields_ = [
        ("dmDeviceName", ctypes.c_uint16 * 32),   # texto de 32 caracteres (UTF-16)
        ("dmSpecVersion", ctypes.c_uint16), ("dmDriverVersion", ctypes.c_uint16),
        ("dmSize", ctypes.c_uint16), ("dmDriverExtra", ctypes.c_uint16),
        ("dmFields", ctypes.c_uint32),
        ("dmPositionX", ctypes.c_int32), ("dmPositionY", ctypes.c_int32),
        ("dmDisplayOrientation", ctypes.c_uint32), ("dmDisplayFixedOutput", ctypes.c_uint32),
        ("dmColor", ctypes.c_int16), ("dmDuplex", ctypes.c_int16),
        ("dmYResolution", ctypes.c_int16), ("dmTTOption", ctypes.c_int16),
        ("dmCollate", ctypes.c_int16),
        ("dmFormName", ctypes.c_uint16 * 32),
        ("dmLogPixels", ctypes.c_uint16),
        ("dmBitsPerPel", ctypes.c_uint32),
        ("dmPelsWidth", ctypes.c_uint32), ("dmPelsHeight", ctypes.c_uint32),
        ("dmDisplayFlags", ctypes.c_uint32), ("dmDisplayFrequency", ctypes.c_uint32),
        ("dmICMMethod", ctypes.c_uint32), ("dmICMIntent", ctypes.c_uint32),
        ("dmMediaType", ctypes.c_uint32), ("dmDitherType", ctypes.c_uint32),
        ("dmReserved1", ctypes.c_uint32), ("dmReserved2", ctypes.c_uint32),
        ("dmPanningWidth", ctypes.c_uint32), ("dmPanningHeight", ctypes.c_uint32),
    ]


def info_pantalla():
    """Resolución y Hz de la pantalla principal, y los Hz máximos que soporta."""
    if SISTEMA == "Windows":
        try:
            enumerar = ctypes.windll.user32.EnumDisplaySettingsW
            actual = _ModoPantalla()
            actual.dmSize = ctypes.sizeof(_ModoPantalla)
            if not enumerar(None, -1, ctypes.byref(actual)):   # -1 = modo actual
                return {}
            maximo = actual.dmDisplayFrequency
            indice = 0
            modo = _ModoPantalla()
            modo.dmSize = ctypes.sizeof(_ModoPantalla)
            while enumerar(None, indice, ctypes.byref(modo)):
                misma_resolucion = (modo.dmPelsWidth == actual.dmPelsWidth
                                    and modo.dmPelsHeight == actual.dmPelsHeight)
                if misma_resolucion and modo.dmDisplayFrequency > maximo:
                    maximo = modo.dmDisplayFrequency
                indice = indice + 1
            return {"ancho": actual.dmPelsWidth, "alto": actual.dmPelsHeight,
                    "hz": actual.dmDisplayFrequency, "hz_max": maximo}
        except Exception:
            return {}

    if SISTEMA == "Darwin":
        texto = ejecutar(["system_profiler", "SPDisplaysDataType", "-json"])
        try:
            for item in json.loads(texto).get("SPDisplaysDataType", []):
                for pantalla in item.get("spdisplays_ndrvs", []):
                    descripcion = pantalla.get("_spdisplays_resolution", "")
                    encontrado = re.search(r"(\d+)\s*x\s*(\d+)(?:\s*@\s*([\d.]+)\s*Hz)?", descripcion)
                    if encontrado:
                        hz = round(float(encontrado.group(3) or 60))
                        return {"ancho": int(encontrado.group(1)), "alto": int(encontrado.group(2)),
                                "hz": hz, "hz_max": hz}
        except Exception:
            pass
    return {}


# ============================================================
#  Almacenamiento
# ============================================================

TIPOS_DISCO = {0: "Sin especificar", 3: "HDD", 4: "SSD", 5: "SCM"}
BUSES = {7: "USB", 8: "RAID", 10: "SAS", 11: "SATA", 17: "NVMe"}


def info_discos_fisicos():
    """(Solo Windows) Discos físicos: modelo, si es HDD/SSD/NVMe y capacidad."""
    if SISTEMA != "Windows":
        return []
    fisicos = []
    for disco in como_lista(datos_windows().get("discos")):
        tipo = disco.get("MediaType")
        if isinstance(tipo, int):
            tipo = TIPOS_DISCO.get(tipo, "Desconocido")
        bus = disco.get("BusType")
        if isinstance(bus, int):
            bus = BUSES.get(bus, "")
        if bus == "NVMe":
            tipo = "SSD NVMe"
        if bus == "USB":
            tipo = "Externo (USB)"
        fisicos.append({
            "id": str(disco.get("DeviceId")),
            "Modelo": (disco.get("FriendlyName") or "Disco").strip(),
            "Tipo": tipo or "Desconocido",
            "Capacidad": f"{a_gb(int(disco.get('Size') or 0)):.0f} GB",
        })
    return fisicos


def tipo_por_unidad(fisicos):
    """(Solo Windows) Qué tipo de disco hay detrás de cada letra: {'C': 'SSD NVMe', ...}."""
    tipos = {}
    for disco in fisicos:
        tipos[disco["id"]] = disco["Tipo"]
    resultado = {}
    for particion in como_lista(datos_windows().get("particiones")):
        letra = str(particion.get("Letra") or "").strip()
        numero = str(particion.get("DiskNumber"))
        if letra.isalpha() and numero in tipos:
            resultado[letra.upper()] = tipos[numero]
    return resultado


def info_discos(tipos_unidad=None):
    tipos_unidad = tipos_unidad or {}
    discos = []
    for particion in psutil.disk_partitions(all=False):
        punto = particion.mountpoint
        if SISTEMA == "Windows":
            if "cdrom" in particion.opts or particion.fstype == "":
                continue
        elif SISTEMA == "Darwin":
            if punto != "/" and not punto.startswith("/Volumes/"):
                continue
        else:
            if particion.fstype in ("squashfs", "tmpfs", "overlay"):
                continue
            if punto.startswith("/snap") or punto.startswith("/boot"):
                continue
        try:
            uso = psutil.disk_usage(punto)
        except Exception:
            continue

        total = a_gb(uso.total)
        libre = a_gb(uso.free)
        if total < 1:
            continue

        if SISTEMA == "Darwin":
            usado = round(total - libre, 1)
            porcentaje = round(usado / total * 100, 1) if total else 0
            nombre = "Macintosh HD" if punto == "/" else punto.replace("/Volumes/", "")
            tipo = "SSD"
        else:
            usado = a_gb(uso.used)
            porcentaje = uso.percent
            nombre = punto
            tipo = tipos_unidad.get(punto[:1].upper(), "") if SISTEMA == "Windows" else ""

        discos.append({"unidad": nombre, "total": total, "usado": usado, "libre": libre,
                       "porcentaje": porcentaje, "tipo": tipo})
    return discos


# ============================================================
#  Uso en tiempo real
# ============================================================

def info_bateria():
    try:
        bateria = psutil.sensors_battery()
    except Exception:
        bateria = None
    if bateria is None:
        return None
    return {"porcentaje": round(bateria.percent), "enchufado": bateria.power_plugged}


# ============================================================
#  Sensores de temperatura en Windows
#  Windows no entrega la temperatura del CPU por sí solo. Si el usuario tiene abierto
#  LibreHardwareMonitor (gratis), RendiPlus la lee desde ahí en un hilo aparte.
# ============================================================

_sensores = {"cpu_temp": None, "gpu_temp": None, "fuente": None, "estado": "sin_iniciar"}
PRIORIDAD_CPU = ["cpu package", "core (tctl/tdie)", "core (tctl)", "tdie", "tctl", "cpu (tctl/tdie)",
                 "core average"]
URL_LHM = "https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases"


def iniciar_sensores():
    if SISTEMA != "Windows" or _sensores["estado"] != "sin_iniciar":
        return
    _sensores["estado"] = "buscando"
    threading.Thread(target=_bucle_sensores, daemon=True).start()


def _leer_lhm(win32com):
    for espacio, fuente in (("root\\LibreHardwareMonitor", "LibreHardwareMonitor"),
                            ("root\\OpenHardwareMonitor", "OpenHardwareMonitor")):
        try:
            wmi = win32com.client.GetObject("winmgmts:" + espacio)
            filas = wmi.ExecQuery("SELECT Name, Value, Identifier FROM Sensor WHERE SensorType='Temperature'")
            lectura = [(str(f.Name).lower(), float(f.Value), str(f.Identifier).lower()) for f in filas]
            if lectura:
                return lectura, fuente
        except Exception:
            continue
    return None, None


def _leer_web_lhm():
    """Plan B: LibreHardwareMonitor con su "Servidor web remoto" activado publica los datos
    en http://localhost:8085/data.json. No necesita pywin32 ni permisos especiales."""
    import urllib.request
    try:
        with urllib.request.urlopen("http://127.0.0.1:8085/data.json", timeout=1.5) as respuesta:
            arbol = json.loads(respuesta.read().decode("utf-8", errors="replace"))
    except Exception:
        return None, None

    lectura = []

    def recorrer(nodo, tipo_equipo):
        imagen = (nodo.get("ImageURL") or "").lower()
        if "cpu" in imagen:
            tipo_equipo = "cpu"
        elif "nvidia" in imagen or "ati" in imagen or "amd" in imagen or "gpu" in imagen:
            tipo_equipo = "gpu"
        valor = str(nodo.get("Value") or "")
        if "°C" in valor and not nodo.get("Children"):
            numero = re.search(r"[-\d.,]+", valor)
            if numero:
                try:
                    grados = float(numero.group(0).replace(",", "."))
                    identificador = (nodo.get("SensorId") or "/" + tipo_equipo + "/").lower()
                    if tipo_equipo not in identificador:
                        identificador = identificador + "/" + tipo_equipo
                    lectura.append((str(nodo.get("Text", "")).lower(), grados, identificador))
                except ValueError:
                    pass
        for hijo in nodo.get("Children") or []:
            recorrer(hijo, tipo_equipo)

    recorrer(arbol, "")
    if lectura:
        return lectura, "LibreHardwareMonitor"
    return None, None


def _bucle_sensores():
    win32com = None
    try:
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
    except ImportError:
        win32com = None
    while True:
        lectura, fuente = (None, None)
        if win32com is not None:
            lectura, fuente = _leer_lhm(win32com)
        if not lectura:
            lectura, fuente = _leer_web_lhm()
        if lectura:
            cpu = [l for l in lectura if "cpu" in l[2]]
            temperatura = None
            for nombre in PRIORIDAD_CPU:
                for sensor in cpu:
                    if sensor[0] == nombre:
                        temperatura = sensor[1]
                        break
                if temperatura is not None:
                    break
            if temperatura is None and cpu:
                temperatura = max(sensor[1] for sensor in cpu)
            gpu = [l[1] for l in lectura if "gpu" in l[2] and l[0] in ("gpu core", "gpu")]
            _sensores.update(cpu_temp=round(temperatura) if temperatura else None,
                             gpu_temp=round(gpu[0]) if gpu else None, fuente=fuente, estado="activo")
        else:
            estado = "sin_programa" if win32com is not None else "falta_pywin32"
            _sensores.update(cpu_temp=None, gpu_temp=None, fuente=None, estado=estado)
        time.sleep(3)


def estado_sensores():
    """'activo', 'sin_programa', 'falta_pywin32', 'buscando' o 'no_aplica'."""
    if SISTEMA != "Windows":
        return {"estado": "no_aplica", "fuente": None}
    return {"estado": _sensores["estado"], "fuente": _sensores["fuente"]}


def temperatura_cpu():
    if SISTEMA == "Windows":
        return _sensores["cpu_temp"]
    if not hasattr(psutil, "sensors_temperatures"):
        return None
    try:
        sensores = psutil.sensors_temperatures()
    except Exception:
        return None
    for nombre in ("coretemp", "k10temp", "cpu_thermal", "acpitz"):
        if nombre in sensores and sensores[nombre]:
            return round(sensores[nombre][0].current)
    return None


def uso_en_vivo():
    memoria = psutil.virtual_memory()
    datos = {
        "cpu": psutil.cpu_percent(interval=None),
        "ram": memoria.percent,
        "ram_usada": a_gb(memoria.total - memoria.available),
        "ram_total": a_gb(memoria.total),
        "gpu": None, "gpu_temp": None, "vram_usada": None, "vram_total": None,
        "cpu_temp": temperatura_cpu(),
        "bateria": info_bateria(),
    }
    if NVIDIA_OK:
        try:
            gpu = pynvml.nvmlDeviceGetHandleByIndex(0)
            datos["gpu"] = pynvml.nvmlDeviceGetUtilizationRates(gpu).gpu
            datos["gpu_temp"] = pynvml.nvmlDeviceGetTemperature(gpu, pynvml.NVML_TEMPERATURE_GPU)
            memoria_gpu = pynvml.nvmlDeviceGetMemoryInfo(gpu)
            datos["vram_usada"] = a_gb(memoria_gpu.used)
            datos["vram_total"] = a_gb(memoria_gpu.total)
        except Exception:
            pass
    if datos["gpu_temp"] is None and _sensores["gpu_temp"] is not None:
        datos["gpu_temp"] = _sensores["gpu_temp"]
    return datos


def procesos_que_mas_consumen(cantidad=5):
    por_nombre = {}
    for proceso in psutil.process_iter(["name", "memory_info"]):
        info = proceso.info
        if info["memory_info"] is None:
            continue
        nombre = info["name"] or "?"
        por_nombre[nombre] = por_nombre.get(nombre, 0) + info["memory_info"].rss
    ordenados = sorted(por_nombre.items(), key=lambda par: par[1], reverse=True)
    resultado = []
    for nombre, memoria in ordenados[:cantidad]:
        resultado.append({"nombre": nombre, "ram_mb": round(memoria / (1024 ** 2))})
    return resultado


# ============================================================
#  Todo junto
# ============================================================

def info_completa():
    """Toda la información fija del PC (se lee una vez al abrir la app)."""
    _cache.clear()
    fisicos = info_discos_fisicos()
    tipos = tipo_por_unidad(fisicos)
    return {
        "sistema": info_sistema(),
        "cpu": info_cpu(),
        "ram": info_ram(),
        "gpus": info_gpus(),
        "pantalla": info_pantalla(),
        "discos": info_discos(tipos),
        "discos_fisicos": fisicos,
        "tipo_por_unidad": tipos,
    }


def visibles(datos):
    """Quita las claves internas (las que empiezan con _) para mostrar en pantalla."""
    resultado = {}
    for clave, valor in datos.items():
        if not clave.startswith("_"):
            resultado[clave] = valor
    return resultado


def generar_informe(datos):
    lineas = ["===== Informe RendiPlus ====="]
    for titulo, clave in [("SISTEMA", "sistema"), ("PROCESADOR", "cpu"), ("MEMORIA RAM", "ram")]:
        lineas.append("")
        lineas.append(titulo)
        for etiqueta, valor in visibles(datos.get(clave, {})).items():
            lineas.append(f"  {etiqueta}: {valor}")
    lineas.append("")
    lineas.append("GRÁFICOS")
    for gpu in datos.get("gpus", []):
        for etiqueta, valor in visibles(gpu).items():
            lineas.append(f"  {etiqueta}: {valor}")
    pantalla = datos.get("pantalla") or {}
    if pantalla:
        lineas.append(f"  Pantalla: {pantalla['ancho']} x {pantalla['alto']} a {pantalla['hz']} Hz "
                      f"(máximo {pantalla['hz_max']} Hz)")
    lineas.append("")
    lineas.append("ALMACENAMIENTO")
    for disco in datos.get("discos", []):
        lineas.append(f"  {disco['unidad']} {disco['tipo']}: {disco['libre']} GB libres de "
                      f"{disco['total']} GB ({disco['porcentaje']} % usado)")
    for disco in datos.get("discos_fisicos", []):
        lineas.append(f"  {disco['Modelo']}: {disco['Tipo']}, {disco['Capacidad']}")
    return "\n".join(lineas)


if __name__ == "__main__":
    print(generar_informe(info_completa()))
