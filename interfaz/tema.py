"""
tema.py  -  Identidad visual de RendiPlus
Colores, tipografías y piezas reutilizables (tarjetas, botones, gráficos...).
Si quieres cambiar el look de toda la app, este es el único archivo que tocas.
"""

import math
import os
import sys
import tkinter as tk
import tkinter.font as tkfont

import customtkinter as ctk

from motores.sistema import leer_config

NOMBRE_APP = "RendiPlus"
VERSION = "1.2"

# ============================================================
#  Temas de color. El elegido se guarda en la configuración y se aplica al abrir la app.
# ============================================================

TEMAS = {
    "marino": {
        "nombre": "Marino", "descripcion": "Azul marino de noche con acento oro viejo", "modo": "dark",
        "FONDO": "#0E1626", "LATERAL": "#0A111E", "SUPERFICIE": "#152036", "SUPERFICIE_ALTA": "#1C2943",
        "LINEA": "#26334F", "TEXTO": "#E9EDF5", "TEXTO_SUAVE": "#97A3BA", "TEXTO_TENUE": "#5F6B84",
        "ORO": "#C9A55C", "ORO_CLARO": "#DDBD78", "TEXTO_SOBRE_ORO": "#16120A",
        "ACERO": "#6E93D6", "VERDE": "#5FC79A", "AMBAR": "#E8B04A", "CORAL": "#E5636B",
        "PERILLA": "#E9EDF5", "INTERRUPTOR_APAGADO": "#26334F",
    },
    "grafito": {
        "nombre": "Grafito", "descripcion": "Gris carbón con acento cobre", "modo": "dark",
        "FONDO": "#131518", "LATERAL": "#0D0F11", "SUPERFICIE": "#1B1E22", "SUPERFICIE_ALTA": "#23272C",
        "LINEA": "#30353C", "TEXTO": "#ECEEF1", "TEXTO_SUAVE": "#A2A9B3", "TEXTO_TENUE": "#68707B",
        "ORO": "#D08A5B", "ORO_CLARO": "#E09F74", "TEXTO_SOBRE_ORO": "#1A0F08",
        "ACERO": "#7FA3C7", "VERDE": "#62C29A", "AMBAR": "#E3B04B", "CORAL": "#E06A6A",
        "PERILLA": "#ECEEF1", "INTERRUPTOR_APAGADO": "#30353C",
    },
    "claro": {
        "nombre": "Claro", "descripcion": "Fondo claro con acento oro, para lugares con mucha luz",
        "modo": "light",
        "FONDO": "#F2F4F8", "LATERAL": "#E7EBF2", "SUPERFICIE": "#FFFFFF", "SUPERFICIE_ALTA": "#F1F4F9",
        "LINEA": "#DCE2EC", "TEXTO": "#121A2B", "TEXTO_SUAVE": "#55627A", "TEXTO_TENUE": "#8A95A8",
        "ORO": "#A7803A", "ORO_CLARO": "#B98F45", "TEXTO_SOBRE_ORO": "#FFFFFF",
        "ACERO": "#3F6DC4", "VERDE": "#1F9D6B", "AMBAR": "#C27C0E", "CORAL": "#D0414B",
        "PERILLA": "#FFFFFF", "INTERRUPTOR_APAGADO": "#C5CDDA",
    },
}

TEMA_ACTUAL = leer_config("tema", "marino")
if TEMA_ACTUAL not in TEMAS:
    TEMA_ACTUAL = "marino"
_paleta = TEMAS[TEMA_ACTUAL]

FONDO = _paleta["FONDO"]                      # fondo general
LATERAL = _paleta["LATERAL"]                  # barra lateral
SUPERFICIE = _paleta["SUPERFICIE"]            # tarjetas
SUPERFICIE_ALTA = _paleta["SUPERFICIE_ALTA"]  # elementos dentro de tarjetas / hover
LINEA = _paleta["LINEA"]                      # bordes y divisiones
TEXTO = _paleta["TEXTO"]
TEXTO_SUAVE = _paleta["TEXTO_SUAVE"]
TEXTO_TENUE = _paleta["TEXTO_TENUE"]
ORO = _paleta["ORO"]                          # acento principal (se usa poco, a propósito)
ORO_CLARO = _paleta["ORO_CLARO"]
TEXTO_SOBRE_ORO = _paleta["TEXTO_SOBRE_ORO"]
ACERO = _paleta["ACERO"]                      # segunda serie de los gráficos
VERDE = _paleta["VERDE"]
AMBAR = _paleta["AMBAR"]
CORAL = _paleta["CORAL"]
PERILLA = _paleta["PERILLA"]
INTERRUPTOR_APAGADO = _paleta["INTERRUPTOR_APAGADO"]
MODO = _paleta["modo"]


def mezclar(color, base, cuanto):
    """Mezcla dos colores hex. cuanto=0 -> base, cuanto=1 -> color."""
    c = [int(color[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(base[i:i + 2], 16) for i in (1, 3, 5)]
    mezcla = [round(b[i] + (c[i] - b[i]) * cuanto) for i in range(3)]
    return "#" + "".join(f"{valor:02X}" for valor in mezcla)


TINTE = 0.14 if MODO == "dark" else 0.12
FONDO_DE = {}                                  # fondos suaves para insignias de cada color
for _color in (ORO, ACERO, VERDE, AMBAR, CORAL, TEXTO_SUAVE):
    FONDO_DE[_color] = mezclar(_color, SUPERFICIE, TINTE)
RELLENO_ORO = mezclar(ORO, SUPERFICIE, 0.12)   # área bajo la línea del gráfico
BORDE_PELIGRO = mezclar(CORAL, SUPERFICIE, 0.4)
ORO_APAGADO = mezclar(TEXTO_SOBRE_ORO, ORO, 0.5)

RADIO = 12

# ============================================================
#  Tipografía
#  Títulos y números: Bahnschrift (estilo DIN, viene con Windows 10/11).
#  Texto: Segoe UI. En Mac se usan sus equivalentes.
# ============================================================

FAMILIA_TITULO = "Arial"
FAMILIA_TEXTO = "Arial"
_titulo_ya_es_negrita = False
_fuentes = {}


def elegir_fuentes():
    """Se llama una vez, después de crear la ventana: elige las fuentes instaladas."""
    global FAMILIA_TITULO, FAMILIA_TEXTO, _titulo_ya_es_negrita
    disponibles = set(tkfont.families())
    for familia in ["Bahnschrift SemiBold", "Bahnschrift", "DIN Alternate", "Avenir Next Condensed",
                    "Inter Display", "DejaVu Sans Condensed"]:
        if familia in disponibles:
            FAMILIA_TITULO = familia
            _titulo_ya_es_negrita = familia in ("Bahnschrift SemiBold", "DIN Alternate")
            break
    for familia in ["Segoe UI", "SF Pro Text", "Helvetica Neue", "Inter", "DejaVu Sans"]:
        if familia in disponibles:
            FAMILIA_TEXTO = familia
            break


def fuente(tamano, negrita=False, titulo=False):
    """Devuelve una fuente lista para usar. titulo=True usa la tipografía de títulos/números."""
    clave = (tamano, negrita, titulo)
    if clave not in _fuentes:
        if titulo:
            peso = "bold" if negrita and not _titulo_ya_es_negrita else "normal"
            _fuentes[clave] = ctk.CTkFont(family=FAMILIA_TITULO, size=tamano, weight=peso)
        else:
            _fuentes[clave] = ctk.CTkFont(family=FAMILIA_TEXTO, size=tamano,
                                          weight="bold" if negrita else "normal")
    return _fuentes[clave]


def fuente_lienzo(tamano, negrita=False, titulo=False):
    """Fuente para dibujar en un Canvas (que usa tuplas, no CTkFont)."""
    familia = FAMILIA_TITULO if titulo else FAMILIA_TEXTO
    peso = "bold" if negrita and not (titulo and _titulo_ya_es_negrita) else "normal"
    return (familia, tamano, peso)


def ruta_recurso(nombre):
    """Ruta a un archivo de /recursos (funciona también dentro del .exe)."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, "recursos", nombre)


# ============================================================
#  Colores según nivel y formatos
# ============================================================

def color_nivel(porcentaje):
    if porcentaje < 60:
        return VERDE
    if porcentaje < 85:
        return AMBAR
    return CORAL


def formato_gb(cantidad_bytes):
    if cantidad_bytes >= 1024 ** 3:
        return f"{cantidad_bytes / 1024 ** 3:.1f} GB"
    if cantidad_bytes >= 1024 ** 2:
        return f"{cantidad_bytes / 1024 ** 2:.0f} MB"
    if cantidad_bytes >= 1024:
        return f"{cantidad_bytes / 1024:.0f} KB"
    return f"{cantidad_bytes} B"


# ============================================================
#  Piezas de la interfaz
# ============================================================

PIXELES_POR_GIRO = 90   # cuánto baja la página por cada "clic" de la rueda del mouse


class PaginaDesplazable(ctk.CTkScrollableFrame):
    """Igual que CTkScrollableFrame, pero con desplazamiento suave y a buena velocidad.
    (En Windows, CustomTkinter baja solo 20 píxeles por giro: por eso se sentía trabado.)"""

    def __init__(self, *args, **kwargs):
        self._pendiente = 0.0
        self._animando = False
        super().__init__(*args, **kwargs)
        self._parent_canvas.configure(yscrollincrement=1)

    def _mouse_wheel_all(self, event):
        if not self._check_if_valid_scroll(event.widget) or self._shift_pressed:
            return
        if sys.platform.startswith("win"):
            pixeles = -event.delta / 120 * PIXELES_POR_GIRO
        elif sys.platform == "darwin":
            pixeles = -event.delta * 12          # el trackpad del Mac manda pasos pequeños
        else:
            pixeles = -PIXELES_POR_GIRO if event.num == 4 else PIXELES_POR_GIRO
        self._pendiente = self._pendiente + pixeles
        if not self._animando:
            self._animando = True
            self._paso_desplazamiento()

    def _paso_desplazamiento(self):
        """Recorre una parte de lo que falta en cada cuadro: arranca rápido y frena suave."""
        arriba, abajo = self._parent_canvas.yview()
        if (self._pendiente < 0 and arriba <= 0) or (self._pendiente > 0 and abajo >= 1):
            self._pendiente = 0
        paso = int(self._pendiente * 0.35)
        if paso == 0 and abs(self._pendiente) >= 1:
            paso = 1 if self._pendiente > 0 else -1
        if paso == 0:
            self._pendiente = 0
            self._animando = False
            return
        self._parent_canvas.yview_scroll(paso, "units")
        self._pendiente = self._pendiente - paso
        self.after(12, self._paso_desplazamiento)


def pagina_con_scroll(padre):
    """Contenedor con scroll para el contenido de una página."""
    contenido = PaginaDesplazable(
        padre, fg_color=FONDO, corner_radius=0,
        scrollbar_button_color=LINEA, scrollbar_button_hover_color=TEXTO_TENUE,
    )
    contenido.pack(fill="both", expand=True)
    padre.desplazable = contenido
    return contenido


def encabezado(padre, titulo, descripcion=""):
    """Título grande de la página. Devuelve el marco; marco.acciones es la zona de botones."""
    marco = ctk.CTkFrame(padre, fg_color="transparent", height=1)
    marco.pack(fill="x", padx=32, pady=(28, 18))
    textos = ctk.CTkFrame(marco, fg_color="transparent", height=1)
    textos.pack(side="left", fill="x", expand=True)
    ctk.CTkLabel(textos, text=titulo, font=fuente(30, True, titulo=True),
                 text_color=TEXTO, anchor="w").pack(fill="x")
    marco.descripcion = ctk.CTkLabel(textos, text=descripcion, font=fuente(13),
                                     text_color=TEXTO_SUAVE, anchor="w", justify="left")
    marco.descripcion.pack(fill="x", pady=(2, 0))
    marco.acciones = ctk.CTkFrame(marco, fg_color="transparent", width=1, height=1)
    marco.acciones.pack(side="right", anchor="e")
    return marco


def tarjeta(padre, titulo=None, descripcion=None):
    """Recuadro con borde fino. marco.cabeza queda disponible para agregar botones a la derecha."""
    marco = ctk.CTkFrame(padre, fg_color=SUPERFICIE, corner_radius=RADIO,
                         border_width=1, border_color=LINEA)
    if titulo:
        cabeza = ctk.CTkFrame(marco, fg_color="transparent", height=1)
        cabeza.pack(fill="x", padx=20, pady=(16, 4 if descripcion else 10))
        ctk.CTkLabel(cabeza, text=titulo, font=fuente(16, True, titulo=True),
                     text_color=TEXTO, anchor="w").pack(side="left")
        marco.cabeza = cabeza
        if descripcion:
            ctk.CTkLabel(marco, text=descripcion, font=fuente(12), text_color=TEXTO_SUAVE,
                         anchor="w", justify="left", wraplength=900).pack(fill="x", padx=20, pady=(0, 10))
    return marco


def separador(padre, vertical=False, **opciones):
    if vertical:
        return ctk.CTkFrame(padre, width=1, height=1, fg_color=LINEA, corner_radius=0)
    return ctk.CTkFrame(padre, height=1, width=1, fg_color=LINEA, corner_radius=0)


def boton(padre, texto, comando=None, estilo="primario", ancho=None, alto=36):
    """Estilos: primario (oro), secundario (contorno), fantasma (solo texto) y peligro (coral)."""
    opciones = {"text": texto, "command": comando, "height": alto, "corner_radius": 8,
                "font": fuente(13, True)}
    if ancho:
        opciones["width"] = ancho
    if estilo == "primario":
        opciones.update(fg_color=ORO, hover_color=ORO_CLARO, text_color=TEXTO_SOBRE_ORO,
                        text_color_disabled=TEXTO_TENUE)
    elif estilo == "secundario":
        opciones.update(fg_color=SUPERFICIE_ALTA, hover_color=LINEA, text_color=TEXTO,
                        border_width=1, border_color=LINEA, text_color_disabled=TEXTO_TENUE)
    elif estilo == "peligro":
        opciones.update(fg_color="transparent", hover_color=FONDO_DE[CORAL], text_color=CORAL,
                        border_width=1, border_color=BORDE_PELIGRO, text_color_disabled=TEXTO_TENUE)
    else:
        opciones.update(fg_color="transparent", hover_color=SUPERFICIE_ALTA, text_color=TEXTO_SUAVE,
                        text_color_disabled=TEXTO_TENUE)
        opciones["font"] = fuente(13)
    return ctk.CTkButton(padre, **opciones)


def actualizar(widget, **opciones):
    """Cambia un widget solo si algo cambió de verdad. Redibujar cuesta, sobre todo en
    Windows, y los datos en vivo muchas veces repiten el mismo valor."""
    anteriores = getattr(widget, "_ultimos_valores", None)
    if anteriores is None:
        anteriores = {}
        widget._ultimos_valores = anteriores
    cambios = {}
    for clave, valor in opciones.items():
        if clave not in anteriores or anteriores[clave] != valor:
            cambios[clave] = valor
    if cambios:
        widget.configure(**cambios)
        anteriores.update(cambios)


def mover_barra(barra, valor):
    """Como barra.set(), pero sin redibujar si el valor no cambió."""
    valor = round(max(0.0, min(1.0, valor)), 3)
    if getattr(barra, "_ultimo_valor", None) != valor:
        barra.set(valor)
        barra._ultimo_valor = valor


def activar_boton(boton, activo, texto=None):
    """Habilita o deshabilita un botón primario, cambiando también su color."""
    if activo:
        boton.configure(state="normal", fg_color=ORO, hover_color=ORO_CLARO)
    else:
        boton.configure(state="disabled", fg_color=SUPERFICIE_ALTA)
    if texto:
        boton.configure(text=texto)


def insignia(padre, texto, color=None):
    """Etiqueta pequeña con fondo de color suave (para estados y prioridades)."""
    color = color or ORO
    return ctk.CTkLabel(padre, text="  " + texto + "  ", font=fuente(11, True), text_color=color,
                        fg_color=FONDO_DE.get(color, SUPERFICIE_ALTA), corner_radius=6, height=22)


def barra(padre, color=None, alto=6):
    progreso = ctk.CTkProgressBar(padre, height=alto, corner_radius=alto // 2,
                                  fg_color=LINEA, progress_color=color or ORO)
    progreso.set(0)
    return progreso


def interruptor(padre, comando=None):
    return ctk.CTkSwitch(padre, text="", command=comando, width=46, switch_width=40, switch_height=20,
                         fg_color=INTERRUPTOR_APAGADO, progress_color=ORO, button_color=PERILLA,
                         button_hover_color=PERILLA)


def casilla(padre, texto, variable, comando=None):
    return ctk.CTkCheckBox(padre, text=texto, variable=variable, command=comando,
                           font=fuente(14, True), text_color=TEXTO, fg_color=ORO,
                           hover_color=ORO_CLARO, border_color=TEXTO_TENUE,
                           checkmark_color=TEXTO_SOBRE_ORO, corner_radius=5,
                           checkbox_width=20, checkbox_height=20)


def espacio(padre, alto=12):
    ctk.CTkFrame(padre, height=alto, fg_color="transparent").pack()


# ============================================================
#  Gráfico de líneas (actividad del último minuto)
# ============================================================

PUNTOS_GRAFICO = 60


def crear_grafico(padre, alto=170):
    return tk.Canvas(padre, height=alto, bg=SUPERFICIE, highlightthickness=0, bd=0)


def dibujar_grafico(lienzo, series):
    """series = [(lista_de_valores_0_a_100, color, color_relleno_o_None), ...]"""
    lienzo.delete("all")
    ancho = lienzo.winfo_width()
    alto = lienzo.winfo_height()
    if ancho < 50 or alto < 40:
        return
    izquierda = 48
    derecha = ancho - 6
    arriba = 8
    abajo = alto - 8

    for porcentaje in (0, 50, 100):
        y = abajo - (abajo - arriba) * porcentaje / 100
        if porcentaje == 0:
            lienzo.create_line(izquierda, y, derecha, y, fill=LINEA)
        else:
            lienzo.create_line(izquierda, y, derecha, y, fill=LINEA, dash=(2, 4))
        lienzo.create_text(izquierda - 10, y, text=f"{porcentaje}%", fill=TEXTO_TENUE,
                           anchor="e", font=fuente_lienzo(9))

    paso = (derecha - izquierda) / (PUNTOS_GRAFICO - 1)
    for valores, color, relleno in series:
        if len(valores) < 2:
            continue
        inicio = PUNTOS_GRAFICO - len(valores)
        puntos = []
        for indice, valor in enumerate(valores):
            x = izquierda + (inicio + indice) * paso
            y = abajo - (abajo - arriba) * max(0, min(valor, 100)) / 100
            puntos.append(x)
            puntos.append(y)
        if relleno:
            poligono = [puntos[0], abajo] + puntos + [puntos[-2], abajo]
            lienzo.create_polygon(poligono, fill=relleno, outline="")
        lienzo.create_line(puntos, fill=color, width=2, smooth=True)
        lienzo.create_oval(puntos[-2] - 3, puntos[-1] - 3, puntos[-2] + 3, puntos[-1] + 3,
                           fill=color, outline="")


# ============================================================
#  Dial del puntaje de salud (la pieza que distingue a RendiPlus)
# ============================================================

def estado_puntaje(puntaje):
    if puntaje >= 85:
        return "Excelente", VERDE
    if puntaje >= 70:
        return "Bien", VERDE
    if puntaje >= 50:
        return "Mejorable", AMBAR
    return "Requiere atención", CORAL


def crear_dial(padre, tamano=220):
    lienzo = tk.Canvas(padre, width=tamano, height=int(tamano * 0.86), bg=SUPERFICIE,
                       highlightthickness=0, bd=0)
    lienzo.tamano = tamano
    lienzo.valor = None
    lienzo.animacion = None
    return lienzo


def dibujar_dial(lienzo, puntaje, estado_final=None):
    """Dibuja un arco de 240° con marcas, como un instrumento de medición."""
    lienzo.delete("all")
    tamano = lienzo.tamano
    centro_x = tamano / 2
    centro_y = tamano / 2 + 6
    radio = tamano / 2 - 22
    grosor = max(8, int(tamano / 18))
    caja = (centro_x - radio, centro_y - radio, centro_x + radio, centro_y + radio)

    for marca in range(0, 101, 10):
        angulo = math.radians(210 - 240 * marca / 100)
        largo = 8 if marca % 50 == 0 else 4
        r1 = radio + grosor / 2 + 5
        r2 = r1 + largo
        lienzo.create_line(centro_x + r1 * math.cos(angulo), centro_y - r1 * math.sin(angulo),
                           centro_x + r2 * math.cos(angulo), centro_y - r2 * math.sin(angulo),
                           fill=TEXTO_TENUE if marca % 50 else TEXTO_SUAVE, width=1)

    lienzo.create_arc(caja, start=-30, extent=240, style="arc", outline=LINEA, width=grosor)
    if puntaje is None:
        lienzo.create_text(centro_x, centro_y - 4, text="—", fill=TEXTO_SUAVE,
                           font=fuente_lienzo(int(tamano / 5), True, titulo=True))
        lienzo.create_text(centro_x, centro_y + tamano / 7, text="Calculando...",
                           fill=TEXTO_TENUE, font=fuente_lienzo(10))
        return
    if puntaje > 0:
        lienzo.create_arc(caja, start=210, extent=-240 * puntaje / 100, style="arc",
                          outline=ORO, width=grosor)
    estado, color = estado_puntaje(estado_final if estado_final is not None else puntaje)
    lienzo.create_text(centro_x, centro_y - 6, text=str(round(puntaje)), fill=TEXTO,
                       font=fuente_lienzo(int(tamano / 4.4), True, titulo=True))
    lienzo.create_text(centro_x, centro_y + tamano / 6.5, text=estado, fill=color,
                       font=fuente_lienzo(max(10, int(tamano / 18)), True))


def animar_dial(lienzo, puntaje, duracion=650):
    """Lleva la aguja desde el valor anterior hasta el nuevo, frenando suave al final."""
    if lienzo.animacion:
        lienzo.after_cancel(lienzo.animacion)
    desde = lienzo.valor if lienzo.valor is not None else 0
    pasos = max(1, duracion // 16)

    def paso(numero):
        avance = numero / pasos
        suave = 1 - (1 - avance) ** 3          # empieza rápido y frena al final
        dibujar_dial(lienzo, desde + (puntaje - desde) * suave, estado_final=puntaje)
        if numero < pasos:
            lienzo.animacion = lienzo.after(16, lambda: paso(numero + 1))
        else:
            lienzo.animacion = None
            lienzo.valor = puntaje
            dibujar_dial(lienzo, puntaje)

    paso(1)
