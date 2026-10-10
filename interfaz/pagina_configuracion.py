"""
pagina_configuracion.py  -  Página "Configuración": tema, inicio con el sistema, bandeja y sensores.
"""

from tkinter import messagebox

import customtkinter as ctk

from interfaz import tema
from motores import escritorio, hardware, sistema


def construir(marco, app):
    contenido = tema.pagina_con_scroll(marco)
    tema.encabezado(contenido, "Configuración", "Apariencia y cómo se comporta RendiPlus en tu equipo.")
    cuerpo = ctk.CTkFrame(contenido, fg_color="transparent", height=1)
    cuerpo.pack(fill="both", expand=True, padx=32, pady=(0, 28))

    # ------------------------------------------------------------
    #  Apariencia: una muestra de cada tema
    # ------------------------------------------------------------
    apariencia = tema.tarjeta(cuerpo, "Apariencia", "Elige un tema. RendiPlus se vuelve a abrir para aplicarlo.")
    apariencia.pack(fill="x", pady=(0, 18))
    fila_temas = ctk.CTkFrame(apariencia, fg_color="transparent", height=1)
    fila_temas.pack(fill="x", padx=20, pady=(0, 20))

    for indice, (clave, datos) in enumerate(tema.TEMAS.items()):
        fila_temas.grid_columnconfigure(indice, weight=1, uniform="temas")
        actual = clave == tema.TEMA_ACTUAL
        muestra = ctk.CTkFrame(fila_temas, fg_color=tema.SUPERFICIE_ALTA, corner_radius=10,
                               border_width=2 if actual else 1, border_color=tema.ORO if actual else tema.LINEA)
        muestra.grid(row=0, column=indice, sticky="nsew", padx=(0 if indice == 0 else 8, 0))

        # Miniatura de la app con los colores del tema
        mini = ctk.CTkFrame(muestra, fg_color=datos["FONDO"], corner_radius=8, height=92)
        mini.pack(fill="x", padx=14, pady=(14, 10))
        mini.pack_propagate(False)
        ctk.CTkFrame(mini, fg_color=datos["LATERAL"], corner_radius=0, width=46).pack(side="left", fill="y")
        interior = ctk.CTkFrame(mini, fg_color="transparent", height=1)
        interior.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        ctk.CTkFrame(interior, fg_color=datos["SUPERFICIE"], corner_radius=6, height=40).pack(fill="x")
        acentos = ctk.CTkFrame(interior, fg_color="transparent", height=1)
        acentos.pack(fill="x", pady=(8, 0))
        ctk.CTkFrame(acentos, fg_color=datos["ORO"], corner_radius=4, width=44, height=14).pack(side="left")
        ctk.CTkFrame(acentos, fg_color=datos["ACERO"], corner_radius=4, width=26, height=14).pack(
            side="left", padx=6)

        arriba = ctk.CTkFrame(muestra, fg_color="transparent", height=1)
        arriba.pack(fill="x", padx=14)
        ctk.CTkLabel(arriba, text=datos["nombre"], font=tema.fuente(15, True), text_color=tema.TEXTO,
                     anchor="w").pack(side="left")
        if actual:
            tema.insignia(arriba, "En uso", tema.ORO).pack(side="right")
        ctk.CTkLabel(muestra, text=datos["descripcion"], font=tema.fuente(12), text_color=tema.TEXTO_SUAVE,
                     anchor="w", justify="left", wraplength=240).pack(fill="x", padx=14, pady=(2, 10))
        if not actual:
            tema.boton(muestra, "Usar este tema", lambda c=clave: cambiar_tema(c), "secundario",
                       alto=32).pack(fill="x", padx=14, pady=(0, 14))
        else:
            tema.espacio(muestra, 10)

    def cambiar_tema(clave):
        sistema.guardar_config("tema", clave)
        if messagebox.askyesno("Cambiar tema", "Para aplicar el tema, RendiPlus se va a volver a abrir. "
                                               "¿Hacerlo ahora?"):
            app["reiniciar"]()
        else:
            app["notificar"]("El tema se aplicará la próxima vez que abras RendiPlus", tema.ACERO)

    # ------------------------------------------------------------
    #  Inicio y bandeja
    # ------------------------------------------------------------
    tarjeta_inicio = tema.tarjeta(cuerpo, "Al prender el equipo")
    tarjeta_inicio.pack(fill="x", pady=(0, 18))
    contenedor = ctk.CTkFrame(tarjeta_inicio, fg_color="transparent", height=1)
    contenedor.pack(fill="x", padx=20, pady=(0, 14))

    def fila_opcion(titulo, descripcion, valor, al_cambiar, habilitado=True, nota=None, primera=False):
        if not primera:
            tema.separador(contenedor).pack(fill="x")
        fila = ctk.CTkFrame(contenedor, fg_color="transparent", height=1)
        fila.pack(fill="x", pady=12)
        interruptor = tema.interruptor(fila)
        interruptor.pack(side="right")
        if valor:
            interruptor.select()
        interruptor.configure(command=lambda: al_cambiar(bool(interruptor.get()), interruptor))
        if not habilitado:
            interruptor.configure(state="disabled")
        textos = ctk.CTkFrame(fila, fg_color="transparent", height=1)
        textos.pack(side="left", fill="x", expand=True)
        arriba = ctk.CTkFrame(textos, fg_color="transparent", height=1)
        arriba.pack(fill="x")
        ctk.CTkLabel(arriba, text=titulo, font=tema.fuente(14, True), text_color=tema.TEXTO,
                     anchor="w").pack(side="left")
        if nota:
            tema.insignia(arriba, nota, tema.TEXTO_SUAVE).pack(side="left", padx=10)
        ctk.CTkLabel(textos, text=descripcion, font=tema.fuente(12), text_color=tema.TEXTO_SUAVE,
                     anchor="w", justify="left", wraplength=720).pack(fill="x", pady=(2, 0))

    def cambiar_inicio(activar, interruptor):
        if escritorio.cambiar_inicio_con_sistema(activar):
            if activar and escritorio.bandeja_disponible():
                sistema.guardar_config("bandeja", True)
                app["activar_bandeja"]()
            app["notificar"]("RendiPlus se abrirá al prender el PC" if activar
                             else "RendiPlus ya no se abrirá al prender el PC")
        else:
            app["notificar"]("No se pudo cambiar el inicio automático", tema.CORAL)
            if activar:
                interruptor.deselect()
            else:
                interruptor.select()

    def cambiar_bandeja(activar, interruptor):
        sistema.guardar_config("bandeja", activar)
        if activar:
            app["activar_bandeja"]()
            app["notificar"]("Al cerrar la ventana, RendiPlus seguirá junto al reloj")
        else:
            app["notificar"]("Al cerrar la ventana, RendiPlus se cerrará por completo")

    nota_windows = None if sistema.SISTEMA == "Windows" else "Solo en Windows"
    fila_opcion("Abrir RendiPlus al prender el PC",
                "Se abre minimizado junto al reloj, listo para cambiar de perfil antes de jugar.",
                escritorio.inicia_con_sistema(), cambiar_inicio, escritorio.inicio_disponible(),
                nota_windows, primera=True)
    nota_bandeja = nota_windows
    if sistema.SISTEMA == "Windows" and not escritorio.bandeja_disponible():
        nota_bandeja = "Falta instalar pystray"
    fila_opcion("Seguir funcionando al cerrar la ventana",
                "La ventana se esconde en la bandeja (junto al reloj). Desde el ícono puedes abrirla, "
                "cambiar de perfil o salir.",
                sistema.leer_config("bandeja", False), cambiar_bandeja, escritorio.bandeja_disponible(),
                nota_bandeja)

    # ------------------------------------------------------------
    #  Sensores de temperatura
    # ------------------------------------------------------------
    sensores = tema.tarjeta(cuerpo, "Temperatura del procesador")
    sensores.pack(fill="x", pady=(0, 18))
    fila_sensor = ctk.CTkFrame(sensores, fg_color="transparent", height=1)
    fila_sensor.pack(fill="x", padx=20, pady=(0, 18))
    texto_sensor = ctk.CTkLabel(fila_sensor, text="", font=tema.fuente(13), text_color=tema.TEXTO_SUAVE,
                                anchor="w", justify="left", wraplength=700)
    texto_sensor.pack(side="left", fill="x", expand=True)
    insignia_sensor = tema.insignia(fila_sensor, "", tema.TEXTO_SUAVE)
    boton_sensor = tema.boton(fila_sensor, "Descargar LibreHardwareMonitor",
                              lambda: sistema.abrir(hardware.URL_LHM), "secundario", alto=32)

    def actualizar_sensor():
        estado = hardware.estado_sensores()
        insignia_sensor.pack_forget()
        boton_sensor.pack_forget()
        if estado["estado"] == "activo":
            texto_sensor.configure(text=f"Leyendo la temperatura desde {estado['fuente']}. Mientras ese programa "
                                        "esté abierto, la verás en el Panel.")
            insignia_sensor.configure(text="  Conectado  ", text_color=tema.VERDE, fg_color=tema.FONDO_DE[tema.VERDE])
            insignia_sensor.pack(side="right")
        elif estado["estado"] == "no_aplica":
            texto_sensor.configure(text="En este sistema la temperatura se lee directamente cuando está disponible.")
        else:
            texto_sensor.configure(
                text="Windows no muestra la temperatura del procesador por sí solo. Abre LibreHardwareMonitor "
                     "como administrador y déjalo abierto (puede estar minimizado). Si igual no conecta, "
                     "actívale Opciones > Remote Web Server > Run: RendiPlus también lo lee por ahí."
                     + ("\nFalta el componente pywin32: instálalo con  python -m pip install pywin32"
                        if estado["estado"] == "falta_pywin32" else ""))
            boton_sensor.pack(side="right", padx=(16, 0))

    # ------------------------------------------------------------
    #  Acerca de
    # ------------------------------------------------------------
    acerca = tema.tarjeta(cuerpo, "Acerca de RendiPlus")
    acerca.pack(fill="x")
    fila_acerca = ctk.CTkFrame(acerca, fg_color="transparent", height=1)
    fila_acerca.pack(fill="x", padx=20, pady=(0, 18))
    ctk.CTkLabel(fila_acerca, text=f"Versión {tema.VERSION}. Tus datos (historial y configuración) se guardan "
                                   "solo en este equipo.", font=tema.fuente(13), text_color=tema.TEXTO_SUAVE,
                 anchor="w").pack(side="left")
    tema.boton(fila_acerca, "Abrir carpeta de datos", lambda: sistema.abrir(sistema.carpeta_datos()),
               "fantasma", alto=30).pack(side="right")

    def revisar_sensor_seguido():
        if app["pagina"] == "configuracion":
            actualizar_sensor()
            app["ventana"].after(3000, revisar_sensor_seguido)

    return {"al_mostrar": revisar_sensor_seguido}
