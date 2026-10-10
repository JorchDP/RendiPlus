"""
pagina_recomendaciones.py  -  Página "Recomendaciones": puntaje, mejoras y calidad gráfica sugerida.
"""

import json

import customtkinter as ctk

from interfaz import tema
from motores import historial, recomendaciones

COLOR_PRIORIDAD = {"alta": tema.CORAL, "media": tema.AMBAR, "baja": tema.ACERO}
TEXTO_PRIORIDAD = {"alta": "Importante", "media": "Recomendado", "baja": "Sugerencia"}


def construir(marco, app):
    contenido = tema.pagina_con_scroll(marco)
    cabeza = tema.encabezado(contenido, "Recomendaciones",
                             "Sugerencias basadas en los componentes y la configuración de tu PC.")
    boton_analizar = tema.boton(cabeza.acciones, "Analizar de nuevo", lambda: analizar_de_nuevo(),
                                "secundario", ancho=160)
    boton_analizar.pack()
    cuerpo = ctk.CTkFrame(contenido, fg_color="transparent", height=1)
    cuerpo.pack(fill="both", expand=True, padx=32, pady=(0, 28))

    # ------------------------------------------------------------
    #  Resumen con el dial
    # ------------------------------------------------------------
    resumen = tema.tarjeta(cuerpo)
    resumen.pack(fill="x", pady=(0, 18))
    dial = tema.crear_dial(resumen, 190)
    dial.pack(side="left", padx=(24, 10), pady=18)
    tema.dibujar_dial(dial, None)
    textos = ctk.CTkFrame(resumen, fg_color="transparent", height=1)
    textos.pack(side="left", fill="both", expand=True, padx=(10, 24), pady=24)
    titulo_resumen = ctk.CTkLabel(textos, text="Revisando tu equipo...", font=tema.fuente(22, True, titulo=True),
                                  text_color=tema.TEXTO, anchor="w", justify="left")
    titulo_resumen.pack(fill="x")
    texto_resumen = ctk.CTkLabel(textos, text="", font=tema.fuente(13), text_color=tema.TEXTO_SUAVE,
                                 anchor="w", justify="left", wraplength=640)
    texto_resumen.pack(fill="x", pady=(6, 12))
    conteos = ctk.CTkFrame(textos, fg_color="transparent", height=1)
    conteos.pack(fill="x")

    zona_lista = ctk.CTkFrame(cuerpo, fg_color="transparent", height=1)
    zona_lista.pack(fill="x")
    zona_positivos = ctk.CTkFrame(cuerpo, fg_color="transparent", height=1)
    zona_positivos.pack(fill="x")
    zona_graficos = ctk.CTkFrame(cuerpo, fg_color="transparent", height=1)
    zona_graficos.pack(fill="x")

    # ------------------------------------------------------------
    #  Dibujar
    # ------------------------------------------------------------
    def ejecutar(accion, boton):
        if accion["tipo"] == "pagina":
            app["ir_a"](accion["pagina"])
            return
        if accion["tipo"] == "ajuste":
            from motores import perfiles
            antes = perfiles.leer_ajuste(accion["id"])
            if recomendaciones.ejecutar_accion(accion):
                nombre = next(a["nombre"] for a in perfiles.AJUSTES if a["id"] == accion["id"])
                historial.registrar("Ajuste", nombre + ": activado",
                                    [{"tipo": "ajuste", "id": accion["id"], "valor": antes}])
                app["notificar"](nombre + " activado")
                boton.configure(state="disabled", text="Listo")
                app["recalcular"]()
            else:
                app["notificar"]("No se pudo aplicar el cambio", tema.CORAL)
            return
        recomendaciones.ejecutar_accion(accion)

    def dibujar(resultado):
        tema.animar_dial(dial, resultado["puntaje"])
        lista = resultado["lista"]
        importantes = len([r for r in lista if r["prioridad"] == "alta"])
        if not lista:
            titulo_resumen.configure(text="Tu PC está en excelente forma")
            texto_resumen.configure(text="No encontramos nada que mejorar. Vuelve a revisar después de "
                                         "instalar programas o cambiar componentes.")
        elif importantes:
            titulo_resumen.configure(text=f"{importantes} cosas importantes por mejorar"
                                     if importantes > 1 else "Una cosa importante por mejorar")
            texto_resumen.configure(text="Empieza por las marcadas como Importante: son las que más "
                                         "se notan en el día a día.")
        else:
            titulo_resumen.configure(text="Tu PC está bien configurado")
            texto_resumen.configure(text="Quedan algunos detalles que pueden darle un poco más de rendimiento.")

        for widget in conteos.winfo_children():
            widget.destroy()
        for prioridad in ("alta", "media", "baja"):
            cantidad = len([r for r in lista if r["prioridad"] == prioridad])
            if cantidad:
                tema.insignia(conteos, f"{cantidad} {TEXTO_PRIORIDAD[prioridad].lower()}"
                              + ("s" if cantidad > 1 else ""), COLOR_PRIORIDAD[prioridad]).pack(side="left", padx=(0, 8))
        if resultado["positivos"]:
            tema.insignia(conteos, f"{len(resultado['positivos'])} en orden", tema.VERDE).pack(side="left")

        # Lista de recomendaciones
        for widget in zona_lista.winfo_children():
            widget.destroy()
        for recomendacion in lista:
            color = COLOR_PRIORIDAD[recomendacion["prioridad"]]
            tarjeta = ctk.CTkFrame(zona_lista, fg_color=tema.SUPERFICIE, corner_radius=tema.RADIO,
                                   border_width=1, border_color=tema.LINEA)
            tarjeta.pack(fill="x", pady=(0, 10))
            franja = ctk.CTkFrame(tarjeta, width=4, height=10, fg_color=color, corner_radius=2)
            franja.pack(side="left", fill="y", padx=(10, 0), pady=14)
            centro = ctk.CTkFrame(tarjeta, fg_color="transparent", height=1)
            centro.pack(side="left", fill="both", expand=True, padx=16, pady=14)
            arriba = ctk.CTkFrame(centro, fg_color="transparent", height=1)
            arriba.pack(fill="x")
            ctk.CTkLabel(arriba, text=recomendacion["titulo"], font=tema.fuente(15, True),
                         text_color=tema.TEXTO, anchor="w").pack(side="left")
            tema.insignia(arriba, TEXTO_PRIORIDAD[recomendacion["prioridad"]], color).pack(side="left", padx=10)
            ctk.CTkLabel(arriba, text=recomendacion["categoria"], font=tema.fuente(11),
                         text_color=tema.TEXTO_TENUE).pack(side="left")
            ctk.CTkLabel(centro, text=recomendacion["detalle"], font=tema.fuente(13),
                         text_color=tema.TEXTO_SUAVE, anchor="w", justify="left",
                         wraplength=720).pack(fill="x", pady=(4, 0))
            accion = recomendacion["accion"]
            if accion:
                estilo = "primario" if recomendacion["prioridad"] == "alta" else "secundario"
                boton = tema.boton(tarjeta, accion["texto"], None, estilo, alto=34)
                boton.configure(command=lambda a=accion, b=boton: ejecutar(a, b))
                boton.pack(side="right", padx=18)

        # Lo que está bien
        for widget in zona_positivos.winfo_children():
            widget.destroy()
        if resultado["positivos"]:
            tarjeta = tema.tarjeta(zona_positivos, "Lo que ya está bien")
            tarjeta.pack(fill="x", pady=(8, 18))
            for texto in resultado["positivos"]:
                fila = ctk.CTkFrame(tarjeta, fg_color="transparent", height=1)
                fila.pack(fill="x", padx=20, pady=3)
                ctk.CTkLabel(fila, text="✓", font=tema.fuente(14, True), text_color=tema.VERDE,
                             width=20).pack(side="left")
                ctk.CTkLabel(fila, text=texto, font=tema.fuente(13), text_color=tema.TEXTO,
                             anchor="w").pack(side="left", padx=6)
            tema.espacio(tarjeta, 10)

        # Calidad gráfica sugerida
        for widget in zona_graficos.winfo_children():
            widget.destroy()
        graficos = resultado.get("graficos")
        if graficos:
            dibujar_graficos(graficos)

    def dibujar_graficos(graficos):
        tarjeta = tema.tarjeta(
            zona_graficos, "Calidad gráfica sugerida para tus juegos",
            f"Para tu {graficos['gpu']} ({graficos['nombre_nivel']}) en una pantalla de "
            f"{graficos['resolucion']} a {graficos['hz']} Hz. Úsalo como punto de partida en el menú "
            "de gráficos de cada juego.")
        tarjeta.pack(fill="x", pady=(0, 18))
        columnas = ctk.CTkFrame(tarjeta, fg_color="transparent", height=1)
        columnas.pack(fill="x", padx=20, pady=(4, 16))
        for indice, preset in enumerate(graficos["presets"]):
            columnas.grid_columnconfigure(indice, weight=1, uniform="presets")
            bloque = ctk.CTkFrame(columnas, fg_color=tema.SUPERFICIE_ALTA, corner_radius=10)
            bloque.grid(row=0, column=indice, sticky="nsew", padx=(0 if indice == 0 else 6, 0 if indice == 2 else 6))
            ctk.CTkLabel(bloque, text=preset["nombre"], font=tema.fuente(18, True, titulo=True),
                         text_color=tema.ORO, anchor="w").pack(fill="x", padx=18, pady=(16, 0))
            ctk.CTkLabel(bloque, text=preset["para"], font=tema.fuente(12), text_color=tema.TEXTO_SUAVE,
                         anchor="w", justify="left", wraplength=230).pack(fill="x", padx=18, pady=(2, 10))
            for etiqueta, valor in preset["ajustes"]:
                fila = ctk.CTkFrame(bloque, fg_color="transparent", height=1)
                fila.pack(fill="x", padx=18, pady=2)
                ctk.CTkLabel(fila, text=etiqueta, font=tema.fuente(12), text_color=tema.TEXTO_SUAVE,
                             anchor="w").pack(side="left")
                ctk.CTkLabel(fila, text=valor, font=tema.fuente(12, True), text_color=tema.TEXTO,
                             anchor="e").pack(side="right")
            tema.espacio(bloque, 14)

        if graficos["consejos"]:
            ctk.CTkLabel(tarjeta, text="Consejos para tu equipo", font=tema.fuente(14, True),
                         text_color=tema.TEXTO, anchor="w").pack(fill="x", padx=20, pady=(4, 4))
            for consejo in graficos["consejos"]:
                fila = ctk.CTkFrame(tarjeta, fg_color="transparent", height=1)
                fila.pack(fill="x", padx=20, pady=3)
                ctk.CTkFrame(fila, width=10, height=2, fg_color=tema.ORO, corner_radius=1).pack(
                    side="left", padx=(0, 10), pady=9, anchor="n")
                ctk.CTkLabel(fila, text=consejo, font=tema.fuente(13), text_color=tema.TEXTO_SUAVE,
                             anchor="w", justify="left", wraplength=820).pack(side="left", fill="x")
            tema.espacio(tarjeta, 14)

    def analizar_de_nuevo():
        boton_analizar.configure(state="disabled", text="Analizando...")
        app["recalcular"]()

    # Rearmar esta página crea muchos elementos. Para no trabar la app, solo se rearma
    # cuando la estás mirando y cuando el resultado de verdad cambió.
    pendiente = {"resultado": app["recomendaciones"], "dibujado": None}

    def huella(resultado):
        return json.dumps([resultado["puntaje"], resultado["lista"], resultado["positivos"],
                           resultado.get("graficos")], sort_keys=True, default=str)

    def dibujar_si_hace_falta():
        resultado = pendiente["resultado"]
        if not resultado:
            return
        nueva = huella(resultado)
        if nueva != pendiente["dibujado"]:
            pendiente["dibujado"] = nueva
            dibujar(resultado)

    def al_tener(resultado):
        boton_analizar.configure(state="normal", text="Analizar de nuevo")
        pendiente["resultado"] = resultado
        if app["pagina"] == "recomendaciones":
            dibujar_si_hace_falta()

    app["suscribir"]("recomendaciones", al_tener)
    return {"al_mostrar": dibujar_si_hace_falta}
