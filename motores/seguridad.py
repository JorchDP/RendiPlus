"""
seguridad.py  -  Motor de seguridad de RendiPlus

RendiPlus NO es un antivirus propio: controla el antivirus que el sistema ya trae.
  - Windows: Microsoft Defender (estado, análisis, firmas, amenazas) y el Firewall.
  - Mac: XProtect, Gatekeeper, Firewall, SIP y FileVault (solo estado; XProtect analiza solo).
"""

import datetime
import os
import plistlib
import subprocess
import time

from motores import sistema
from motores.sistema import SISTEMA

_cache = {"estado": None, "hora": 0}
_analisis = {"proceso": None}

NOMBRES_FIREWALL = {"Domain": "Dominio", "Private": "Privada", "Public": "Pública"}

# ============================================================
#  Windows
# ============================================================

SCRIPT_ESTADO = "; ".join([
    "$ErrorActionPreference = 'SilentlyContinue'",
    "$r = [ordered]@{}",
    "$s = Get-MpComputerStatus",
    "if ($s) { $r.defender = [ordered]@{ "
    "activo = $s.AntivirusEnabled; tiempo_real = $s.RealTimeProtectionEnabled; "
    "servicio = $s.AMServiceEnabled; modo = [string]$s.AMRunningMode; "
    "antimanipulacion = $s.IsTamperProtected; edad_firmas = $s.AntivirusSignatureAge; "
    "firmas = $(if ($s.AntivirusSignatureLastUpdated) { $s.AntivirusSignatureLastUpdated.ToString('dd-MM-yyyy HH:mm') } else { '' }); "
    "edad_rapido = $s.QuickScanAge; "
    "rapido = $(if ($s.QuickScanEndTime) { $s.QuickScanEndTime.ToString('dd-MM-yyyy HH:mm') } else { '' }); "
    "completo = $(if ($s.FullScanEndTime) { $s.FullScanEndTime.ToString('dd-MM-yyyy HH:mm') } else { '' }) } }",
    "$r.productos = @(Get-CimInstance -Namespace root/SecurityCenter2 -ClassName AntiVirusProduct | "
    "Select-Object displayName, productState)",
    "$r.firewall = @(Get-NetFirewallProfile | Select-Object Name, @{n='Activo';e={[string]$_.Enabled}})",
    "$r",
])

SCRIPT_AMENAZAS = "; ".join([
    "$ErrorActionPreference = 'SilentlyContinue'",
    "$nombres = @{}",
    "Get-MpThreat | ForEach-Object { $nombres[[string]$_.ThreatID] = $_.ThreatName }",
    "@(Get-MpThreatDetection | Sort-Object InitialDetectionTime -Descending | Select-Object -First 15 | "
    "ForEach-Object { [ordered]@{ nombre = $nombres[[string]$_.ThreatID]; "
    "fecha = $_.InitialDetectionTime.ToString('dd-MM-yyyy HH:mm'); "
    "archivos = ($_.Resources -join ', '); resuelto = $_.ActionSuccess } })",
])


def ruta_mpcmdrun():
    """Programa de línea de comandos de Microsoft Defender."""
    candidatos = [os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"),
                               "Windows Defender", "MpCmdRun.exe")]
    plataforma = os.path.join(os.environ.get("ProgramData", r"C:\ProgramData"),
                              "Microsoft", "Windows Defender", "Platform")
    if os.path.isdir(plataforma):
        for version in sorted(os.listdir(plataforma), reverse=True):
            candidatos.append(os.path.join(plataforma, version, "MpCmdRun.exe"))
    for ruta in candidatos:
        if os.path.isfile(ruta):
            return ruta
    return None


def _verdadero(valor):
    return valor in (True, 1, "True", "true", "1")


def _producto_activo(estado_producto):
    """Windows guarda el estado de cada antivirus en un número; este bit indica si está encendido."""
    try:
        return (int(estado_producto) >> 12) & 0xF == 1
    except (TypeError, ValueError):
        return False


def _estado_windows():
    datos = sistema.powershell_json(SCRIPT_ESTADO) or {}
    defender = datos.get("defender") or {}
    productos = sistema.como_lista(datos.get("productos"))
    otros = [p.get("displayName") for p in productos
             if _producto_activo(p.get("productState")) and "defender" not in (p.get("displayName") or "").lower()]

    comprobaciones = []
    defender_principal = _verdadero(defender.get("activo")) and "passive" not in defender.get("modo", "").lower()

    # 1. Antivirus activo
    if defender_principal:
        antivirus = "Microsoft Defender"
        comprobaciones.append({"nombre": "Antivirus", "estado": "ok", "detalle": "Microsoft Defender está activo."})
    elif otros:
        antivirus = otros[0]
        comprobaciones.append({"nombre": "Antivirus", "estado": "ok",
                               "detalle": f"{antivirus} está protegiendo el equipo. Defender queda en reserva."})
    else:
        antivirus = "Ninguno"
        comprobaciones.append({"nombre": "Antivirus", "estado": "peligro",
                               "detalle": "No hay un antivirus activo. Actívalo en Seguridad de Windows."})

    if defender_principal:
        # 2. Tiempo real
        if _verdadero(defender.get("tiempo_real")):
            comprobaciones.append({"nombre": "Protección en tiempo real", "estado": "ok",
                                   "detalle": "Revisa cada archivo al abrirlo o descargarlo."})
        else:
            comprobaciones.append({"nombre": "Protección en tiempo real", "estado": "peligro",
                                   "detalle": "Está apagada: los archivos nuevos no se revisan al abrirlos."})
        # 3. Firmas
        edad = defender.get("edad_firmas")
        if isinstance(edad, int) and edad <= 3:
            estado_firmas = "ok"
        elif isinstance(edad, int) and edad <= 7:
            estado_firmas = "alerta"
        else:
            estado_firmas = "peligro"
        detalle = "Última actualización: " + (defender.get("firmas") or "desconocida") + "."
        comprobaciones.append({"nombre": "Base de amenazas (firmas)", "estado": estado_firmas,
                               "detalle": detalle, "accion": "firmas"})
        # 4. Último análisis
        edad_rapido = defender.get("edad_rapido")
        if not defender.get("rapido") or not isinstance(edad_rapido, int) or edad_rapido > 1000:
            comprobaciones.append({"nombre": "Último análisis", "estado": "alerta",
                                   "detalle": "No hay registro de un análisis rápido reciente."})
        elif edad_rapido <= 14:
            comprobaciones.append({"nombre": "Último análisis", "estado": "ok",
                                   "detalle": "Análisis rápido: " + defender["rapido"] + "."})
        else:
            comprobaciones.append({"nombre": "Último análisis", "estado": "alerta",
                                   "detalle": f"El último análisis rápido fue hace {edad_rapido} días."})
        # 5. Protección contra alteraciones
        if defender.get("antimanipulacion") is not None:
            if _verdadero(defender.get("antimanipulacion")):
                comprobaciones.append({"nombre": "Protección contra alteraciones", "estado": "ok",
                                       "detalle": "Impide que programas maliciosos apaguen Defender."})
            else:
                comprobaciones.append({"nombre": "Protección contra alteraciones", "estado": "alerta",
                                       "detalle": "Está apagada. Actívala en Seguridad de Windows > "
                                                  "Protección antivirus y contra amenazas."})

    # 6. Firewall
    perfiles = sistema.como_lista(datos.get("firewall"))
    if perfiles:
        apagados = [NOMBRES_FIREWALL.get(p.get("Name"), p.get("Name")) for p in perfiles
                    if not _verdadero(p.get("Activo"))]
        if apagados:
            comprobaciones.append({"nombre": "Firewall", "estado": "peligro",
                                   "detalle": "Apagado en la red " + ", ".join(apagados) + "."})
        else:
            comprobaciones.append({"nombre": "Firewall", "estado": "ok",
                                   "detalle": "Activo en todas las redes."})

    return {
        "disponible": bool(defender) or bool(productos),
        "antivirus": antivirus,
        "puede_analizar": defender_principal and ruta_mpcmdrun() is not None,
        "comprobaciones": comprobaciones,
        "edad_firmas": defender.get("edad_firmas"),
        "ultimo_completo": defender.get("completo") or "",
    }


def amenazas_recientes():
    """Amenazas que Defender detectó. Puede devolver None si no hay permiso para leerlas."""
    if SISTEMA != "Windows":
        return []
    datos = sistema.powershell_json(SCRIPT_AMENAZAS)
    lista = []
    for amenaza in sistema.como_lista(datos):
        lista.append({
            "nombre": amenaza.get("nombre") or "Amenaza desconocida",
            "fecha": amenaza.get("fecha") or "",
            "archivos": (amenaza.get("archivos") or "").replace("file:_", ""),
            "resuelto": _verdadero(amenaza.get("resuelto")),
        })
    return lista


def analizar(tipo, ruta=None):
    """Lanza un análisis con Defender. tipo: 'rapido', 'completo' o 'carpeta'.
    Devuelve (resultado, mensaje). resultado: 'limpio', 'amenazas', 'cancelado' o 'error'."""
    programa = ruta_mpcmdrun()
    if not programa:
        return "error", "No se encontró Microsoft Defender en este equipo."
    comando = [programa, "-Scan", "-ScanType", {"rapido": "1", "completo": "2", "carpeta": "3"}[tipo]]
    if tipo == "carpeta":
        comando = comando + ["-File", ruta]
    try:
        proceso = subprocess.Popen(comando, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
        _analisis["proceso"] = proceso
        salida, _ = proceso.communicate()
        texto = sistema.decodificar(salida)
    except Exception as error:
        return "error", str(error)
    finally:
        cancelado = _analisis.get("cancelado", False)
        _analisis["proceso"] = None
        _analisis["cancelado"] = False
    invalidar()
    if cancelado:
        return "cancelado", "Análisis cancelado."
    if proceso.returncode == 0:
        return "limpio", "No se encontraron amenazas."
    if proceso.returncode == 2 or "threat" in texto.lower():
        return "amenazas", "Defender encontró amenazas y actuó sobre ellas. Revisa la lista de amenazas."
    return "error", "El análisis no pudo completarse. " + texto[-200:].strip()


def cancelar_analisis():
    proceso = _analisis.get("proceso")
    if proceso and proceso.poll() is None:
        _analisis["cancelado"] = True
        proceso.terminate()


def actualizar_firmas():
    programa = ruta_mpcmdrun()
    if not programa:
        return False, "No se encontró Microsoft Defender."
    codigo, texto = sistema.ejecutar_con_codigo([programa, "-SignatureUpdate"], 900)
    invalidar()
    if codigo == 0:
        return True, "Base de amenazas actualizada."
    if not sistema.es_admin():
        return False, "No se pudo actualizar. Prueba abriendo RendiPlus como administrador."
    return False, "No se pudo actualizar. Revisa tu conexión a internet."


# ============================================================
#  Mac
# ============================================================

def _estado_mac():
    comprobaciones = []

    gatekeeper = sistema.ejecutar(["spctl", "--status"])
    comprobaciones.append({
        "nombre": "Gatekeeper", "estado": "ok" if "enabled" in gatekeeper else "peligro",
        "detalle": "Solo deja abrir apps de fuentes verificadas." if "enabled" in gatekeeper
        else "Está desactivado: cualquier app puede abrirse sin revisión."})

    xprotect = "/Library/Apple/System/Library/CoreServices/XProtect.bundle/Contents/Info.plist"
    try:
        with open(xprotect, "rb") as archivo:
            version = plistlib.load(archivo).get("CFBundleShortVersionString", "")
        fecha = datetime.date.fromtimestamp(os.path.getmtime(xprotect)).strftime("%d-%m-%Y")
        comprobaciones.append({"nombre": "XProtect (antivirus de macOS)", "estado": "ok",
                               "detalle": f"Versión {version}, actualizado el {fecha}. Analiza solo, sin "
                                          "que tengas que hacer nada."})
    except Exception:
        comprobaciones.append({"nombre": "XProtect (antivirus de macOS)", "estado": "desconocido",
                               "detalle": "No se pudo leer su versión."})

    firewall = sistema.ejecutar(["/usr/libexec/ApplicationFirewall/socketfilterfw", "--getglobalstate"])
    activo = "enabled" in firewall.lower() or "state = 1" in firewall.lower()
    comprobaciones.append({
        "nombre": "Firewall", "estado": "ok" if activo else "alerta",
        "detalle": "Activo." if activo else "Apagado (viene así de fábrica). Actívalo en Configuración > Red > Firewall."})

    sip = sistema.ejecutar(["csrutil", "status"])
    comprobaciones.append({
        "nombre": "Protección de integridad (SIP)", "estado": "ok" if "enabled" in sip else "alerta",
        "detalle": "Protege los archivos del sistema." if "enabled" in sip else "Desactivada."})

    filevault = sistema.ejecutar(["fdesetup", "status"])
    comprobaciones.append({
        "nombre": "FileVault (cifrado del disco)", "estado": "ok" if "On" in filevault else "alerta",
        "detalle": "Tus archivos están cifrados." if "On" in filevault
        else "Apagado: si pierdes el equipo, tus archivos se pueden leer."})

    return {"disponible": True, "antivirus": "XProtect", "puede_analizar": False,
            "comprobaciones": comprobaciones, "edad_firmas": None, "ultimo_completo": ""}


# ============================================================
#  Funciones públicas
# ============================================================

def estado_seguridad(usar_cache=True):
    """Estado de la protección. Se guarda 2 minutos para no consultarlo a cada rato."""
    if usar_cache and _cache["estado"] and time.time() - _cache["hora"] < 120:
        return _cache["estado"]
    if SISTEMA == "Windows":
        estado = _estado_windows()
    elif SISTEMA == "Darwin":
        estado = _estado_mac()
    else:
        estado = {"disponible": False, "antivirus": "", "puede_analizar": False,
                  "comprobaciones": [], "edad_firmas": None, "ultimo_completo": ""}
    _cache["estado"] = estado
    _cache["hora"] = time.time()
    return estado


def invalidar():
    _cache["estado"] = None


def abrir_panel_del_sistema():
    if SISTEMA == "Windows":
        sistema.abrir("windowsdefender:")
    elif SISTEMA == "Darwin":
        sistema.abrir("x-apple.systempreferences:com.apple.preference.security")
