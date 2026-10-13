"""
app.py  -  RendiPlus
Abre la app con:   py app.py        (en Mac: python3 app.py)

Este archivo arma la ventana: la barra lateral, el cambio entre páginas, la bandeja del
sistema y los datos que comparten todas las páginas. Cada página vive en
interfaz/pagina_*.py y cada "motor" (lo que hace el trabajo de verdad) en motores/*.py.
"""

import queue
import sys
import threading
import time
import traceback

import customtkinter as ctk

from motores import escritorio, hardware, perfiles, recomendaciones, sistema, historial

# ============================================================
#  Una sola RendiPlus abierta a la vez
# ============================================================

cola = queue.Queue()   # pedidos que llegan desde otros hilos (bandeja, segunda instancia)
if not escritorio.instancia_unica(lambda: cola.put(("mostrar", None))):
    print("RendiPlus ya estaba abierto: se le pidió que muestre su ventana.")
    print("Si no aparece, cierra los procesos de Python en el Administrador de tareas y vuelve a abrirlo.")
    sys.exit(0)   # ya estaba abierta: le pedimos que se muestre y salimos

from interfaz import tema  # noqa: E402  (se importa después: lee el tema guardado)
from interfaz import (pagina_panel, pagina_limpieza, pagina_programas, pagina_inicio,  # noqa: E402
                      pagina_perfiles, pagina_seguridad, pagina_recomendaciones, pagina_mejoras,
                      pagina_historial, pagina_configuracion)

INICIO_MINIMIZADO = "--minimizado" in sys.argv

if sistema.SISTEMA == "Windows":
    try:
        # Hace que la barra de tareas muestre el ícono de RendiPlus y no el de Python
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("RendiPlus.App")
    except Exception:
        pass

ctk.set_appearance_mode(tema.MODO)

ventana = ctk.CTk(fg_color=tema.FONDO)
# Importante: NO se usa withdraw() ni transparencia aquí. En Windows, CustomTkinter vuelve a
# esconder la ventana si se escondió antes de arrancar, y la transparencia hace que Windows
# dibuje la ventana más lento.
ventana.title(tema.NOMBRE_APP)
ventana.geometry("1320x840")
ventana.minsize(1120, 720)
tema.elegir_fuentes()


def poner_icono():
    try:
        if sistema.SISTEMA == "Windows":
            ventana.iconbitmap(tema.ruta_recurso("icono.ico"))
        else:
            import tkinter as tk
            imagen = tk.PhotoImage(file=tema.ruta_recurso("icono.png"))
            ventana.iconphoto(True, imagen)
            ventana.icono = imagen   # guardamos la imagen para que no se borre
    except Exception:
        pass


poner_icono()
ventana.after(300, poner_icono)   # CustomTkinter pone su propio ícono al inicio; lo reemplazamos


# ============================================================
#  Datos compartidos entre páginas
# ============================================================

app = {
    "ventana": ventana,
    "datos_pc": {},          # componentes del PC (se llenan al abrir)
    "uso": {},               # uso en tiempo real (se actualiza cada segundo)
    "historia": {"cpu": [], "ram": [], "gpu": []},
    "recomendaciones": None,
    "pagina": None,
    "oculta": False,         # True cuando la ventana está escondida en la bandeja
    "eventos": {},
}


def suscribir(evento, funcion):
    """Una página pide que la avisen cuando pase algo ('uso', 'datos', 'recomendaciones', 'perfil')."""
    app["eventos"].setdefault(evento, []).append(funcion)


def emitir(evento, dato=None):
    for funcion in app["eventos"].get(evento, []):
        try:
            funcion(dato)
        except Exception:
            traceback.print_exc()


def en_segundo_plano(trabajo, al_terminar=None):
    """Ejecuta 'trabajo' sin congelar la ventana y luego llama a al_terminar(resultado)."""
    resultado = {}

    def envoltura():
        try:
            resultado["valor"] = trabajo()
        except Exception:
            traceback.print_exc()
            resultado["valor"] = None

    hilo = threading.Thread(target=envoltura, daemon=True)
    hilo.start()

    def revisar():
        if hilo.is_alive():
            ventana.after(80, revisar)
        elif al_terminar:
            al_terminar(resultado.get("valor"))

    ventana.after(40, revisar)


app["suscribir"] = suscribir
app["emitir"] = emitir
app["en_segundo_plano"] = en_segundo_plano


# ============================================================
#  Estructura: barra lateral + zona principal
# ============================================================

lateral = ctk.CTkFrame(ventana, fg_color=tema.LATERAL, corner_radius=0, width=240)
lateral.pack(side="left", fill="y")
lateral.pack_propagate(False)

ctk.CTkFrame(ventana, width=1, fg_color=tema.LINEA, corner_radius=0).pack(side="left", fill="y")

principal = ctk.CTkFrame(ventana, fg_color=tema.FONDO, corner_radius=0)
principal.pack(side="left", fill="both", expand=True)

# --- Marca ---
marca = ctk.CTkFrame(lateral, fg_color="transparent", height=1)
marca.pack(fill="x", padx=22, pady=(24, 24))
ctk.CTkLabel(marca, text="R", width=38, height=38, corner_radius=10, fg_color=tema.ORO,
             text_color=tema.TEXTO_SOBRE_ORO, font=tema.fuente(22, True, titulo=True)).pack(side="left")
nombre_marca = ctk.CTkFrame(marca, fg_color="transparent", height=1)
nombre_marca.pack(side="left", padx=12)
ctk.CTkLabel(nombre_marca, text=tema.NOMBRE_APP, font=tema.fuente(21, True, titulo=True),
             text_color=tema.TEXTO, anchor="w", height=22).pack(fill="x")
ctk.CTkLabel(nombre_marca, text="Optimizador de PC", font=tema.fuente(11),
             text_color=tema.TEXTO_TENUE, anchor="w", height=16).pack(fill="x")

# --- Menú ---
PAGINAS = [
    ("panel", "Panel", pagina_panel),
    ("limpieza", "Limpieza", pagina_limpieza),
    ("programas", "Programas y discos", pagina_programas),
    ("inicio", "Inicio y procesos", pagina_inicio),
    ("perfiles", "Perfiles", pagina_perfiles),
    ("seguridad", "Seguridad", pagina_seguridad),
    ("recomendaciones", "Recomendaciones", pagina_recomendaciones),
    ("mejoras", "Mejoras de hardware", pagina_mejoras),
    ("historial", "Historial", pagina_historial),
    ("configuracion", "Configuración", pagina_configuracion),
]
items_menu = {}
paginas_creadas = {}


def crear_item_menu(clave, texto):
    if clave == "configuracion":
        tema.separador(lateral).pack(fill="x", padx=24, pady=10)
    fila = ctk.CTkFrame(lateral, fg_color="transparent", height=38)
    fila.pack(fill="x", padx=(10, 14), pady=1)
    indicador = ctk.CTkFrame(fila, width=3, height=22, fg_color=tema.LATERAL, corner_radius=2)
    indicador.pack(side="left", padx=(0, 7))
    boton = ctk.CTkButton(
        fila, text=texto, anchor="w", height=36, corner_radius=8, fg_color="transparent",
        hover_color=tema.SUPERFICIE, text_color=tema.TEXTO_SUAVE, font=tema.fuente(14),
        command=lambda: ir_a(clave),
    )
    boton.pack(side="left", fill="x", expand=True)
    contador = ctk.CTkLabel(fila, text="", width=24, height=20, corner_radius=10,
                            fg_color=tema.CORAL, text_color="#FFFFFF", font=tema.fuente(11, True))
    items_menu[clave] = {"boton": boton, "indicador": indicador, "contador": contador}


for clave_pagina, texto_pagina, modulo_pagina in PAGINAS:
    crear_item_menu(clave_pagina, texto_pagina)


def poner_contador(clave, numero):
    contador = items_menu[clave]["contador"]
    if numero:
        contador.configure(text=str(numero))
        contador.place(relx=1.0, x=-10, rely=0.5, anchor="e")
    else:
        contador.place_forget()


def mostrar_marco(marco):
    marco.place(relx=0, rely=0, relwidth=1, relheight=1)
    marco.tkraise()   # por encima del fondo dibujado de la zona principal


def construir_pagina(clave):
    """Arma una página (si todavía no existe) y la deja lista pero fuera de la vista.
    Las páginas escondidas no se dibujan ni se recalculan: así la ventana va más liviana."""
    if clave in paginas_creadas:
        return
    marco = ctk.CTkFrame(principal, fg_color=tema.FONDO, corner_radius=0)
    marco.place(relx=0, rely=0, relwidth=1, relheight=1)
    marco.lower()             # se arma por debajo, sin que se vea
    modulo = next(m for c, t, m in PAGINAS if c == clave)
    respuesta = modulo.construir(marco, app) or {}
    marco.update_idletasks()   # calcula su tamaño ahora, para que después aparezca al instante
    marco.place_forget()
    paginas_creadas[clave] = {"marco": marco, "al_mostrar": respuesta.get("al_mostrar")}


def ir_a(clave):
    if app["pagina"] == clave:
        return
    construir_pagina(clave)
    anterior = paginas_creadas.get(app["pagina"])
    mostrar_marco(paginas_creadas[clave]["marco"])
    if anterior:
        anterior["marco"].place_forget()
    app["pagina"] = clave

    for clave_item, item in items_menu.items():
        activo = clave_item == clave
        item["boton"].configure(
            fg_color=tema.SUPERFICIE if activo else "transparent",
            text_color=tema.TEXTO if activo else tema.TEXTO_SUAVE,
            font=tema.fuente(14, activo),
        )
        item["indicador"].configure(fg_color=tema.ORO if activo else tema.LATERAL)

    if paginas_creadas[clave]["al_mostrar"]:
        ventana.after(10, paginas_creadas[clave]["al_mostrar"])


app["ir_a"] = ir_a


ultima_interaccion = {"hora": 0.0}


def registrar_interaccion(evento=None):
    ultima_interaccion["hora"] = time.monotonic()


for secuencia in ("<ButtonPress>", "<KeyPress>", "<MouseWheel>", "<Motion>"):
    ventana.bind_all(secuencia, registrar_interaccion, add="+")


def precargar_paginas():
    """Arma las demás páginas de a una, solo cuando no estás usando la app (si haces clic
    o scroll, espera). Así la primera visita a cada página es instantánea sin trabar el inicio."""
    if time.monotonic() - ultima_interaccion["hora"] < 1.5:
        ventana.after(700, precargar_paginas)
        return
    for clave, texto, modulo in PAGINAS:
        if clave not in paginas_creadas:
            construir_pagina(clave)
            ventana.after(500, precargar_paginas)
            return


# --- Pie de la barra lateral: monitor mini, perfil y permisos ---
pie = ctk.CTkFrame(lateral, fg_color="transparent", height=1)
pie.pack(side="bottom", fill="x", padx=22, pady=(0, 20))

mini = {}
for clave_mini, nombre_mini, color_mini in [("cpu", "CPU", tema.ORO), ("ram", "RAM", tema.ACERO)]:
    fila_mini = ctk.CTkFrame(pie, fg_color="transparent", height=1)
    fila_mini.pack(fill="x", pady=3)
    ctk.CTkLabel(fila_mini, text=nombre_mini, font=tema.fuente(11), text_color=tema.TEXTO_TENUE,
                 width=34, anchor="w").pack(side="left")
    valor_mini = ctk.CTkLabel(fila_mini, text="0 %", font=tema.fuente(11, True),
                              text_color=tema.TEXTO_SUAVE, width=40, anchor="e")
    valor_mini.pack(side="right")
    barra_mini = tema.barra(fila_mini, color_mini, alto=4)
    barra_mini.pack(side="left", fill="x", expand=True, padx=6)
    mini[clave_mini] = (barra_mini, valor_mini)

tema.separador(pie).pack(fill="x", pady=(12, 10))
texto_perfil = ctk.CTkLabel(pie, text="", font=tema.fuente(12), text_color=tema.TEXTO_SUAVE, anchor="w")
texto_perfil.pack(fill="x")

if sistema.es_admin():
    tema.insignia(pie, "Modo administrador", tema.ORO).pack(anchor="w", pady=(8, 0))
elif sistema.SISTEMA == "Windows":
    def abrir_como_admin():
        escritorio.liberar_instancia()     # deja pasar a la copia con permisos
        if sistema.reiniciar_como_admin():
            salir()
        else:
            escritorio.instancia_unica(lambda: cola.put(("mostrar", None)))

    tema.boton(pie, "Abrir como administrador", abrir_como_admin, "secundario", alto=32).pack(
        fill="x", pady=(10, 0))

ctk.CTkLabel(pie, text="Versión " + tema.VERSION, font=tema.fuente(10),
             text_color=tema.TEXTO_TENUE, anchor="w").pack(fill="x", pady=(10, 0))


def actualizar_perfil_lateral(dato=None):
    perfil = perfiles.perfil_activo()
    if perfil:
        texto_perfil.configure(text="Perfil activo: " + perfiles.PERFILES[perfil]["nombre"])
    else:
        texto_perfil.configure(text="Sin perfil activo")


suscribir("perfil", actualizar_perfil_lateral)


# ============================================================
#  Avisos flotantes ("Perfil activado", "Listo", etc.)
# ============================================================

aviso = ctk.CTkFrame(ventana, fg_color=tema.SUPERFICIE_ALTA, corner_radius=10,
                     border_width=1, border_color=tema.LINEA)
punto_aviso = ctk.CTkFrame(aviso, width=8, height=8, corner_radius=4, fg_color=tema.VERDE)
punto_aviso.pack(side="left", padx=(16, 0))
texto_aviso = ctk.CTkLabel(aviso, text="", font=tema.fuente(13), text_color=tema.TEXTO)
texto_aviso.pack(side="left", padx=(10, 18), pady=12)
tarea_aviso = {"id": None}


def notificar(texto, color=None):
    if app["oculta"]:
        escritorio.avisar_en_bandeja(texto)
        return
    texto_aviso.configure(text=texto)
    punto_aviso.configure(fg_color=color or tema.VERDE)
    aviso.place(relx=1.0, rely=1.0, x=-28, y=-28, anchor="se")
    aviso.lift()
    if tarea_aviso["id"]:
        ventana.after_cancel(tarea_aviso["id"])
    tarea_aviso["id"] = ventana.after(4000, aviso.place_forget)


app["notificar"] = notificar


# ============================================================
#  Ventana, bandeja y salida
# ============================================================

def aparecer():
    """Muestra la ventana (también cuando vuelve desde la bandeja)."""
    app["oculta"] = False
    ventana.deiconify()
    ventana.lift()
    ventana.focus_force()
    if app["uso"]:
        emitir("uso", app["uso"])


def esconder():
    app["oculta"] = True
    ventana.withdraw()
    if not sistema.leer_config("aviso_bandeja_mostrado", False):
        sistema.guardar_config("aviso_bandeja_mostrado", True)
        escritorio.avisar_en_bandeja("RendiPlus sigue funcionando aquí. Haz clic en el ícono para abrirlo.")


def salir():
    escritorio.detener_bandeja()
    escritorio.liberar_instancia()
    ventana.destroy()


def al_cerrar_ventana():
    if sistema.leer_config("bandeja", False) and escritorio.bandeja_disponible():
        activar_bandeja()
        esconder()
    else:
        salir()


def reiniciar():
    escritorio.reiniciar_app()
    salir()


def aplicar_perfil(clave):
    nombre = perfiles.PERFILES[clave]["nombre"]

    def listo(respuesta):
        if not respuesta:
            notificar("No se pudo aplicar el perfil " + nombre, tema.CORAL)
            return
        resultados, deshacer = respuesta
        historial.registrar("Perfil", "Se activó el perfil " + nombre, deshacer)
        notificar("Perfil " + nombre + " activado")
        emitir("perfil")
        recalcular()

    en_segundo_plano(lambda: perfiles.aplicar_perfil(clave), listo)


def activar_bandeja():
    escritorio.iniciar_bandeja(
        tema.ruta_recurso("icono.png"),
        al_abrir=lambda: cola.put(("mostrar", None)),
        al_perfil=lambda clave: cola.put(("perfil", clave)),
        al_salir=lambda: cola.put(("salir", None)),
        perfiles_disponibles=[(clave, datos["nombre"]) for clave, datos in perfiles.PERFILES.items()],
        perfil_activo=perfiles.perfil_activo,
    )


def procesar_cola():
    """Atiende lo que pidieron otros hilos, siempre desde el hilo de la ventana."""
    while not cola.empty():
        pedido, dato = cola.get()
        if pedido == "mostrar":
            aparecer()
        elif pedido == "perfil":
            aplicar_perfil(dato)
        elif pedido == "salir":
            salir()
            return
    ventana.after(150, procesar_cola)


ventana.protocol("WM_DELETE_WINDOW", al_cerrar_ventana)
app["reiniciar"] = reiniciar
app["activar_bandeja"] = activar_bandeja
app["aplicar_perfil"] = aplicar_perfil


# ============================================================
#  Actualizaciones automáticas
# ============================================================

def tic():
    """Cada segundo: lee el uso en vivo y avisa a quien lo necesite."""
    try:
        uso = hardware.uso_en_vivo()
    except Exception:
        uso = app["uso"]
    app["uso"] = uso
    for clave in ("cpu", "ram", "gpu"):
        valor = uso.get(clave)
        if valor is not None:
            app["historia"][clave].append(valor)
            del app["historia"][clave][:-tema.PUNTOS_GRAFICO]
    if not app["oculta"]:
        for clave_mini in mini:
            barra_mini, valor_mini = mini[clave_mini]
            tema.mover_barra(barra_mini, uso.get(clave_mini, 0) / 100)
            tema.actualizar(valor_mini, text=f"{uso.get(clave_mini, 0):.0f} %")
        emitir("uso", uso)
    ventana.after(1000, tic)


def recalcular():
    """Vuelve a calcular las recomendaciones (por ejemplo, después de un cambio)."""
    if not app["datos_pc"]:
        return
    if app.get("calculando"):
        app["otra_vez"] = True
        return
    app["calculando"] = True

    def listo(resultado):
        app["calculando"] = False
        if resultado:
            app["recomendaciones"] = resultado
            poner_contador("recomendaciones", resultado["pendientes_importantes"])
            emitir("recomendaciones", resultado)
        if app.pop("otra_vez", False):
            recalcular()

    en_segundo_plano(lambda: recomendaciones.analizar(app["datos_pc"], app["uso"]), listo)


app["recalcular"] = recalcular


def datos_listos(datos):
    app["datos_pc"] = datos or {}
    emitir("datos", app["datos_pc"])
    recalcular()
    ventana.after(2500, precargar_paginas)


ir_a("panel")
actualizar_perfil_lateral()
hardware.iniciar_sensores()
en_segundo_plano(hardware.iniciar_nvidia, lambda lista: emitir("gpu_lista") if lista else None)
tic()
en_segundo_plano(hardware.info_completa, datos_listos)
procesar_cola()

def iniciar_oculta():
    app["oculta"] = True
    ventana.withdraw()


def asegurar_visible():
    """Red de seguridad: si por cualquier motivo la ventana quedó escondida, se muestra."""
    if app["oculta"]:
        return
    try:
        if ventana.state() == "withdrawn":
            ventana.deiconify()
    except Exception:
        pass


if INICIO_MINIMIZADO and escritorio.bandeja_disponible():
    activar_bandeja()
    ventana.after(100, iniciar_oculta)
else:
    if sistema.leer_config("bandeja", False):
        activar_bandeja()
    ventana.after(100, aparecer)       # se muestra cuando la ventana ya existe de verdad
    ventana.after(1500, asegurar_visible)

ventana.mainloop()
