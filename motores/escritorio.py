"""
escritorio.py  -  Integración de RendiPlus con el escritorio

  - Iniciar con Windows (minimizado en la bandeja, junto al reloj)
  - Ícono en la bandeja con menú para cambiar de perfil rápido
  - Una sola ventana abierta a la vez (si la abres de nuevo, aparece la que ya estaba)
  - Reiniciar la app (por ejemplo, al cambiar de tema)
"""

import os
import socket
import subprocess
import sys
import threading

from motores import sistema
from motores.sistema import SISTEMA

RUTA_RUN = r"Software\Microsoft\Windows\CurrentVersion\Run"
NOMBRE_INICIO = "RendiPlus"
PUERTO_INSTANCIA = 47851

_estado = {"icono": None, "socket": None}


# ============================================================
#  Cómo volver a abrir la app
# ============================================================

def comando_app(minimizado=False, sin_consola=True):
    """La lista de argumentos para abrir RendiPlus (sirve como .exe y como script)."""
    if getattr(sys, "frozen", False):
        comando = [sys.executable]
    else:
        python = sys.executable
        if sin_consola and SISTEMA == "Windows":
            pythonw = os.path.join(os.path.dirname(python), "pythonw.exe")
            if os.path.isfile(pythonw):
                python = pythonw
        comando = [python, os.path.abspath(sys.argv[0])]
    if minimizado:
        comando.append("--minimizado")
    return comando


def reiniciar_app():
    """Abre una copia nueva de la app. Quien llama debe cerrar la ventana actual después."""
    liberar_instancia()
    subprocess.Popen(comando_app(), cwd=os.path.dirname(os.path.abspath(sys.argv[0])))


# ============================================================
#  Iniciar con Windows
# ============================================================

def inicio_disponible():
    return SISTEMA == "Windows"


def inicia_con_sistema():
    if not inicio_disponible():
        return False
    return sistema.leer_registro("HKCU", RUTA_RUN, NOMBRE_INICIO) is not None


def cambiar_inicio_con_sistema(activar):
    if not inicio_disponible():
        return False
    if activar:
        comando = " ".join('"' + parte + '"' if not parte.startswith("--") else parte
                           for parte in comando_app(minimizado=True))
        return sistema.escribir_registro("HKCU", RUTA_RUN, NOMBRE_INICIO, comando, tipo="texto")
    return sistema.borrar_valor_registro("HKCU", RUTA_RUN, NOMBRE_INICIO)


# ============================================================
#  Bandeja del sistema (solo Windows: en Mac la bandeja choca con la ventana)
# ============================================================

def bandeja_disponible():
    if SISTEMA != "Windows":
        return False
    try:
        import pystray  # noqa: F401
        from PIL import Image  # noqa: F401
        return True
    except Exception:
        return False


def iniciar_bandeja(ruta_icono, al_abrir, al_perfil, al_salir, perfiles_disponibles, perfil_activo):
    """Muestra el ícono junto al reloj. Las funciones al_* se llaman desde otro hilo:
    quien las entrega debe pasarlas a la ventana de forma segura (RendiPlus usa una cola)."""
    if _estado["icono"] or not bandeja_disponible():
        return False
    import pystray
    from PIL import Image

    def opcion_perfil(clave, nombre):
        return pystray.MenuItem(nombre, lambda icono, item: al_perfil(clave),
                                checked=lambda item: perfil_activo() == clave, radio=True)

    menu = pystray.Menu(
        pystray.MenuItem("Abrir RendiPlus", lambda icono, item: al_abrir(), default=True),
        pystray.MenuItem("Perfil", pystray.Menu(
            *[opcion_perfil(clave, nombre) for clave, nombre in perfiles_disponibles])),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Salir", lambda icono, item: al_salir()),
    )
    icono = pystray.Icon("RendiPlus", Image.open(ruta_icono), "RendiPlus", menu)
    icono.run_detached()
    _estado["icono"] = icono
    return True


def avisar_en_bandeja(texto):
    icono = _estado["icono"]
    if icono:
        try:
            icono.notify(texto, "RendiPlus")
        except Exception:
            pass


def detener_bandeja():
    icono = _estado["icono"]
    _estado["icono"] = None
    if icono:
        try:
            icono.stop()
        except Exception:
            pass


# ============================================================
#  Una sola instancia
# ============================================================

def instancia_unica(al_pedir_mostrar):
    """Devuelve False si RendiPlus ya estaba abierto (y le pide que se muestre)."""
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if SISTEMA != "Windows":
        # Permite reabrir enseguida tras reiniciar (en Windows esta opción significa otra cosa)
        servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        servidor.bind(("127.0.0.1", PUERTO_INSTANCIA))
        servidor.listen(2)
    except OSError:
        servidor.close()
        try:
            conexion = socket.create_connection(("127.0.0.1", PUERTO_INSTANCIA), timeout=1)
            conexion.sendall(b"mostrar")
            conexion.close()
        except OSError:
            pass
        return False

    servidor.settimeout(0.5)

    def escuchar():
        # Se revisa cada medio segundo si la app sigue usando este puerto
        while _estado["socket"] is servidor:
            try:
                conexion, _ = servidor.accept()
            except socket.timeout:
                continue
            except OSError:
                return   # el socket se cerró: la app se está reiniciando
            conexion.close()
            al_pedir_mostrar()

    _estado["socket"] = servidor
    threading.Thread(target=escuchar, daemon=True).start()
    return True


def liberar_instancia():
    servidor = _estado["socket"]
    _estado["socket"] = None
    if servidor:
        try:
            servidor.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            servidor.close()
        except OSError:
            pass
