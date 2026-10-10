"""
pagina_seguridad.py  -  Página "Seguridad": controla Microsoft Defender (Windows) o muestra
el estado de la protección de macOS.
"""

from tkinter import filedialog, messagebox

import customtkinter as ctk

from interfaz import tema
from motores import historial, seguridad
from motores.sistema import SISTEMA

COLOR_ESTADO = {"ok": tema.VERDE, "alerta": tema.AMBAR, "peligro": tema.CORAL, "desconocido": tema.TEXTO_SUAVE}
TEXTO_ESTADO = {"ok": "Bien", "alerta": "Revisar", "peligro": "Atención", "desconocido": "Sin datos"}


def construir(marco, app):
    estado = {"datos": None, "analizando": False}

    contenido = tema.pagina_con_scroll(marco)
    if SISTEMA == "Windows":
        descripcion = "Controla el antivirus de Windows (Microsoft Defender) sin salir de RendiPlus."
        texto_panel = "Abrir Seguridad de Windows"
    else:
        descripcion = "Revisa que la protección incluida en tu sistema esté encendida."
        texto_panel = "Abrir ajustes de seguridad"
    cabeza = tema.encabezado(contenido, "Seguridad", descripcion)
    if SISTEMA in ("Windows", "Darwin"):
        tema.boton(cabeza.acciones, texto_panel, seguridad.abrir_panel_del_sistema, "secundario").pack()
    cuerpo = ctk.CTkFrame(contenido, fg_color="transparent", height=1)
    cuerpo.pack(fill="both", expand=True, padx=32, pady=(0, 28))

    # ------------------------------------------------------------
    #  Resumen y acciones
    # ------------------------------------------------------------
    resumen = tema.tarjeta(cuerpo)
    resumen.pack(fill="x", pady=(0, 18))
    izquierda = ctk.CTkFrame(resumen, fg_color="transparent", height=1)
    izquierda.pack(side="left", fill="x", expand=True, padx=26, pady=22)
    fila_titulo = ctk.CTkFrame(izquierda, fg_color="transparent", height=1)
    fila_titulo.pack(fill="x")
    punto = ctk.CTkFrame(fila_titulo, width=12, height=12, corner_radius=6, fg_color=tema.TEXTO_TENUE)
    punto.pack(side="left", padx=(0, 12))
    titulo = ctk.CTkLabel(fila_titulo, text="Revisando la protección...", font=tema.fuente(22, True, titulo=True),
                          text_color=tema.TEXTO, anchor="w")
    titulo.pack(side="left")
    subtitulo = ctk.CTkLabel(izquierda, text="", font=tema.fuente(13), text_color=tema.TEXTO_SUAVE,
                             anchor="w", justify="left")
    subtitulo.pack(fill="x", pady=(6, 0))

    derecha = ctk.CTkFrame(resumen, fg_color="transparent", height=1)
    derecha.pack(side="right", padx=26, pady=22, before=izquierda)
    boton_rapido = tema.boton(derecha, "Análisis rápido", lambda: iniciar("rapido"), "primario", ancho=170, alto=42)
    boton_carpeta = tema.boton(derecha, "Analizar carpeta", lambda: iniciar("carpeta"), "secundario", ancho=150, alto=42)
    boton_completo = tema.boton(derecha, "Análisis completo", lambda: iniciar("completo"), "fantasma", alto=42)

    # Zona que aparece mientras se analiza
    progreso = ctk.CTkFrame(cuerpo, fg_color=tema.SUPERFICIE, corner_radius=tema.RADIO,
                            border_width=1, border_color=tema.ORO)
    fila_progreso = ctk.CTkFrame(progreso, fg_color="transparent", height=1)
    fila_progreso.pack(fill="x", padx=22, pady=(18, 8))
    texto_progreso = ctk.CTkLabel(fila_progreso, text="", font=tema.fuente(14, True), text_color=tema.TEXTO,
                                  anchor="w")
    texto_progreso.pack(side="left")
    tema.boton(fila_progreso, "Cancelar", seguridad.cancelar_analisis, "peligro", ancho=100, alto=30).pack(side="right")
    barra = ctk.CTkProgressBar(progreso, mode="indeterminate", height=4, fg_color=tema.LINEA,
                               progress_color=tema.ORO)
    barra.pack(fill="x", padx=22, pady=(0, 6))
    ctk.CTkLabel(progreso, text="Puede tardar varios minutos. Puedes seguir usando RendiPlus mientras tanto.",
                 font=tema.fuente(12), text_color=tema.TEXTO_SUAVE, anchor="w").pack(fill="x", padx=22, pady=(0, 16))

    # ------------------------------------------------------------
    #  Estado de la protección
    # ------------------------------------------------------------
    tarjeta_estado = tema.tarjeta(cuerpo, "Estado de la protección")
    tarjeta_estado.pack(fill="x", pady=(0, 18))
    lista_estado = ctk.CTkFrame(tarjeta_estado, fg_color="transparent", height=1)
    lista_estado.pack(fill="x", padx=20, pady=(0, 14))
    ctk.CTkLabel(lista_estado, text="Consultando...", font=tema.fuente(13), text_color=tema.TEXTO_TENUE,
                 anchor="w").pack(fill="x", pady=6)

    # ------------------------------------------------------------
    #  Amenazas recientes (solo Windows)
    # ------------------------------------------------------------
    lista_amenazas = None
    if SISTEMA == "Windows":
        tarjeta_amenazas = tema.tarjeta(cuerpo, "Amenazas detectadas",
                                        "Lo que Microsoft Defender encontró en este equipo, lo más reciente primero.")
        tarjeta_amenazas.pack(fill="x", pady=(0, 18))
        lista_amenazas = ctk.CTkFrame(tarjeta_amenazas, fg_color="transparent", height=1)
        lista_amenazas.pack(fill="x", padx=20, pady=(0, 14))

    nota = tema.tarjeta(cuerpo, "Sobre el antivirus")
    nota.pack(fill="x")
    if SISTEMA == "Windows":
        texto_nota = ("RendiPlus no instala un antivirus propio: usa Microsoft Defender, que ya viene con "
                      "Windows y está entre los mejor evaluados. Si instalas otro antivirus, Defender se pone "
                      "en reserva y RendiPlus te muestra cuál está protegiendo el equipo.")
    else:
        texto_nota = ("macOS incluye XProtect, que revisa las apps automáticamente al abrirlas y se actualiza "
                      "solo. RendiPlus revisa que esa protección y las demás defensas del sistema estén encendidas.")
    ctk.CTkLabel(nota, text=texto_nota, font=tema.fuente(13), text_color=tema.TEXTO_SUAVE, anchor="w",
                 justify="left", wraplength=880).pack(fill="x", padx=20, pady=(0, 18))

    # ------------------------------------------------------------
    #  Lógica
    # ------------------------------------------------------------
    def dibujar_estado(datos):
        estado["datos"] = datos
        for widget in lista_estado.winfo_children():
            widget.destroy()
        if not datos or not datos["disponible"]:
            punto.configure(fg_color=tema.TEXTO_TENUE)
            titulo.configure(text="Seguridad no disponible")
            subtitulo.configure(text="Esta función está disponible en Windows y macOS.")
            for boton in (boton_rapido, boton_carpeta, boton_completo):
                boton.pack_forget()
            return

        problemas = [c for c in datos["comprobaciones"] if c["estado"] == "peligro"]
        avisos = [c for c in datos["comprobaciones"] if c["estado"] == "alerta"]
        if problemas:
            punto.configure(fg_color=tema.CORAL)
            titulo.configure(text="Tu PC necesita atención" if len(problemas) > 1 else "Hay algo importante por revisar")
        elif avisos:
            punto.configure(fg_color=tema.AMBAR)
            titulo.configure(text="Protegido, con detalles por revisar")
        else:
            punto.configure(fg_color=tema.VERDE)
            titulo.configure(text="Tu PC está protegido")
        subtitulo.configure(text="Antivirus activo: " + datos["antivirus"] + ".")

        if datos["puede_analizar"] and not boton_rapido.winfo_ismapped():
            boton_rapido.pack(side="left", padx=(0, 8))
            boton_carpeta.pack(side="left", padx=(0, 8))
            boton_completo.pack(side="left")
        elif not datos["puede_analizar"]:
            for boton in (boton_rapido, boton_carpeta, boton_completo):
                boton.pack_forget()

        for indice, comprobacion in enumerate(datos["comprobaciones"]):
            if indice > 0:
                tema.separador(lista_estado).pack(fill="x")
            fila = ctk.CTkFrame(lista_estado, fg_color="transparent", height=1)
            fila.pack(fill="x", pady=10)
            color = COLOR_ESTADO[comprobacion["estado"]]
            if comprobacion.get("accion") == "firmas" and datos["puede_analizar"]:
                tema.boton(fila, "Actualizar", actualizar_firmas, "secundario", ancho=100, alto=30).pack(
                    side="right", padx=(12, 0))
            tema.insignia(fila, TEXTO_ESTADO[comprobacion["estado"]], color).pack(side="right")
            ctk.CTkFrame(fila, width=8, height=8, corner_radius=4, fg_color=color).pack(side="left", padx=(0, 12))
            textos = ctk.CTkFrame(fila, fg_color="transparent", height=1)
            textos.pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(textos, text=comprobacion["nombre"], font=tema.fuente(14, True), text_color=tema.TEXTO,
                         anchor="w").pack(fill="x")
            ctk.CTkLabel(textos, text=comprobacion["detalle"], font=tema.fuente(12), text_color=tema.TEXTO_SUAVE,
                         anchor="w", justify="left", wraplength=700).pack(fill="x")

    def dibujar_amenazas(lista):
        if lista_amenazas is None:
            return
        for widget in lista_amenazas.winfo_children():
            widget.destroy()
        if not lista:
            ctk.CTkLabel(lista_amenazas, text="Defender no registra amenazas detectadas en este equipo.",
                         font=tema.fuente(13), text_color=tema.VERDE, anchor="w").pack(fill="x", pady=4)
            return
        for indice, amenaza in enumerate(lista):
            if indice > 0:
                tema.separador(lista_amenazas).pack(fill="x")
            fila = ctk.CTkFrame(lista_amenazas, fg_color="transparent", height=1)
            fila.pack(fill="x", pady=8)
            if amenaza["resuelto"]:
                tema.insignia(fila, "Neutralizada", tema.VERDE).pack(side="right")
            else:
                tema.insignia(fila, "Requiere acción", tema.CORAL).pack(side="right")
            textos = ctk.CTkFrame(fila, fg_color="transparent", height=1)
            textos.pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(textos, text=amenaza["nombre"], font=tema.fuente(14, True), text_color=tema.TEXTO,
                         anchor="w").pack(fill="x")
            archivos = amenaza["archivos"]
            if len(archivos) > 110:
                archivos = archivos[:107] + "..."
            ctk.CTkLabel(textos, text=amenaza["fecha"] + "   " + archivos, font=tema.fuente(11),
                         text_color=tema.TEXTO_TENUE, anchor="w").pack(fill="x")

    def cargar(forzar=False):
        def trabajo():
            datos = seguridad.estado_seguridad(usar_cache=not forzar)
            return datos, seguridad.amenazas_recientes()

        def listo(respuesta):
            datos, amenazas = respuesta or (None, [])
            dibujar_estado(datos)
            dibujar_amenazas(amenazas)

        app["en_segundo_plano"](trabajo, listo)

    def iniciar(tipo):
        if estado["analizando"]:
            return
        ruta = None
        if tipo == "carpeta":
            ruta = filedialog.askdirectory(title="Elige la carpeta que quieres analizar")
            if not ruta:
                return
        if tipo == "completo" and not messagebox.askyesno(
                "Análisis completo", "El análisis completo revisa todo el disco y puede tardar más de una hora. "
                                     "¿Empezar ahora?"):
            return

        estado["analizando"] = True
        nombres = {"rapido": "Análisis rápido en curso...", "completo": "Análisis completo en curso...",
                   "carpeta": "Analizando la carpeta..."}
        texto_progreso.configure(text=nombres[tipo])
        progreso.pack(fill="x", pady=(0, 18), after=resumen)
        barra.start()
        for boton in (boton_rapido, boton_carpeta, boton_completo):
            boton.configure(state="disabled")

        def listo(respuesta):
            estado["analizando"] = False
            barra.stop()
            progreso.pack_forget()
            for boton in (boton_rapido, boton_carpeta, boton_completo):
                boton.configure(state="normal")
            tema.activar_boton(boton_rapido, True)
            resultado, mensaje = respuesta or ("error", "El análisis no pudo completarse.")
            if resultado == "limpio":
                app["notificar"]("Análisis terminado: no se encontraron amenazas")
                historial.registrar("Seguridad", {"rapido": "Análisis rápido", "completo": "Análisis completo",
                                                  "carpeta": "Análisis de carpeta"}[tipo] + ": sin amenazas")
            elif resultado == "amenazas":
                historial.registrar("Seguridad", "Análisis: Defender encontró amenazas")
                messagebox.showwarning("Amenazas encontradas", mensaje)
            elif resultado == "cancelado":
                app["notificar"]("Análisis cancelado", tema.TEXTO_SUAVE)
            else:
                messagebox.showerror("Análisis", mensaje)
            cargar(forzar=True)
            app["recalcular"]()

        app["en_segundo_plano"](lambda: seguridad.analizar(tipo, ruta), listo)

    def actualizar_firmas():
        app["notificar"]("Actualizando la base de amenazas...", tema.ACERO)

        def listo(respuesta):
            bien, mensaje = respuesta or (False, "No se pudo actualizar.")
            app["notificar"](mensaje, tema.VERDE if bien else tema.AMBAR)
            cargar(forzar=True)
            app["recalcular"]()

        app["en_segundo_plano"](seguridad.actualizar_firmas, listo)

    return {"al_mostrar": cargar}
