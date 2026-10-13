"""
pagina_inicio.py  -  Página "Inicio y procesos".
"""

from tkinter import messagebox

import customtkinter as ctk

from interfaz import tema
from motores import historial, inicio

TEXTO_RECOMENDACION = {
    "desactivar": ("Puedes desactivarlo", tema.AMBAR),
    "mantener": ("Mejor mantener", tema.VERDE),
    "neutral": ("", tema.TEXTO_SUAVE),
}


def construir(marco, app):
    estado = {"vista": "inicio", "programas": [], "refrescando": False, "bucle": False}

    contenido = tema.pagina_con_scroll(marco)
    tema.encabezado(contenido, "Inicio y procesos",
                    "Decide qué programas arrancan con tu PC y cierra los que consumen de más.")
    cuerpo = ctk.CTkFrame(contenido, fg_color="transparent", height=1)
    cuerpo.pack(fill="both", expand=True, padx=32, pady=(0, 28))

    # ------------------------------------------------------------
    #  Selector de vista (dos "pestañas" con subrayado dorado)
    # ------------------------------------------------------------
    selector = ctk.CTkFrame(cuerpo, fg_color="transparent", height=1)
    selector.pack(fill="x", pady=(0, 16))
    botones_vista = {}
    for clave, texto in [("inicio", "Programas de inicio"), ("procesos", "Procesos activos")]:
        bloque = ctk.CTkFrame(selector, fg_color="transparent", height=1)
        bloque.pack(side="left", padx=(0, 26))
        boton = ctk.CTkButton(bloque, text=texto, fg_color="transparent", hover_color=tema.FONDO,
                              text_color=tema.TEXTO_SUAVE, font=tema.fuente(15, True), height=30,
                              anchor="w", width=10, command=lambda c=clave: mostrar_vista(c))
        boton.pack(anchor="w")
        linea = ctk.CTkFrame(bloque, height=2, width=1, fg_color=tema.FONDO, corner_radius=1)
        linea.pack(fill="x", padx=4)
        botones_vista[clave] = (boton, linea)
    tema.separador(cuerpo).pack(fill="x", pady=(0, 18))

    vista_inicio = ctk.CTkFrame(cuerpo, fg_color="transparent", height=1)
    vista_procesos = ctk.CTkFrame(cuerpo, fg_color="transparent", height=1)

    # ------------------------------------------------------------
    #  Vista: programas de inicio
    # ------------------------------------------------------------
    resumen = tema.tarjeta(vista_inicio)
    resumen.pack(fill="x", pady=(0, 18))
    textos_resumen = ctk.CTkFrame(resumen, fg_color="transparent", height=1)
    textos_resumen.pack(side="left", fill="x", expand=True, padx=24, pady=20)
    numero_activos = ctk.CTkLabel(textos_resumen, text="—", font=tema.fuente(40, True, titulo=True),
                                  text_color=tema.TEXTO, anchor="w", height=48)
    numero_activos.pack(fill="x")
    texto_resumen = ctk.CTkLabel(textos_resumen, text="Revisando programas de inicio...",
                                 font=tema.fuente(13), text_color=tema.TEXTO_SUAVE, anchor="w",
                                 justify="left")
    texto_resumen.pack(fill="x")
    boton_recomendados = tema.boton(resumen, "Desactivar recomendados", None, "primario", alto=42)
    boton_recomendados.pack(side="right", padx=24)

    lista_programas = tema.tarjeta(vista_inicio, "Programas que arrancan con tu PC",
                                   "Desactivarlos no los desinstala: solo dejan de abrirse solos. "
                                   "Puedes volver a activarlos cuando quieras.")
    lista_programas.pack(fill="x")
    contenedor_programas = ctk.CTkFrame(lista_programas, fg_color="transparent", height=1)
    contenedor_programas.pack(fill="x", padx=20, pady=(0, 14))

    def dibujar_programas():
        for widget in contenedor_programas.winfo_children():
            widget.destroy()
        programas = estado["programas"]
        activos = [p for p in programas if p["activo"]]
        sugeridos = [p for p in activos if p["recomendacion"] == "desactivar" and not p["bloqueado"]]

        numero_activos.configure(text=str(len(activos)))
        texto = "programas arrancan solos al prender tu PC."
        if len(activos) == 1:
            texto = "programa arranca solo al prender tu PC."
        if len(sugeridos) == 1:
            texto = texto + " 1 se puede desactivar sin problema."
        elif sugeridos:
            texto = texto + f" {len(sugeridos)} se pueden desactivar sin problema."
        texto_resumen.configure(text=texto)
        if sugeridos:
            plural = "recomendado" if len(sugeridos) == 1 else "recomendados"
            tema.activar_boton(boton_recomendados, True, f"Desactivar {len(sugeridos)} {plural}")
        else:
            tema.activar_boton(boton_recomendados, False, "Nada que desactivar")

        if not programas:
            ctk.CTkLabel(contenedor_programas, text="No hay programas configurados para arrancar solos.",
                         font=tema.fuente(13), text_color=tema.TEXTO_SUAVE, anchor="w").pack(fill="x")
            return

        for indice, programa in enumerate(programas):
            if indice > 0:
                tema.separador(contenedor_programas).pack(fill="x")
            fila = ctk.CTkFrame(contenedor_programas, fg_color="transparent", height=1)
            fila.pack(fill="x", pady=10)

            interruptor = tema.interruptor(fila)
            interruptor.pack(side="right")
            if programa["activo"]:
                interruptor.select()
            interruptor.configure(command=lambda p=programa, i=interruptor: alternar(p, i))
            if programa["bloqueado"]:
                interruptor.configure(state="disabled")
                tema.insignia(fila, "Requiere administrador", tema.TEXTO_SUAVE).pack(side="right", padx=14)

            texto_rec, color_rec = TEXTO_RECOMENDACION[programa["recomendacion"]]
            if texto_rec and programa["activo"]:
                tema.insignia(fila, texto_rec, color_rec).pack(side="right", padx=14)

            textos = ctk.CTkFrame(fila, fg_color="transparent", height=1)
            textos.pack(side="left", fill="x", expand=True)
            color_nombre = tema.TEXTO if programa["activo"] else tema.TEXTO_TENUE
            ctk.CTkLabel(textos, text=programa["nombre"], font=tema.fuente(14, True),
                         text_color=color_nombre, anchor="w").pack(fill="x")
            ruta = programa["comando"]
            if len(ruta) > 95:
                ruta = ruta[:92] + "..."
            ctk.CTkLabel(textos, text=programa["ubicacion"] + "   " + ruta, font=tema.fuente(11),
                         text_color=tema.TEXTO_TENUE, anchor="w").pack(fill="x")

    def alternar(programa, interruptor):
        activo = bool(interruptor.get())
        if inicio.cambiar_estado(programa, activo):
            accion = "Se activó" if activo else "Se desactivó"
            historial.registrar("Inicio", f"{accion} \"{programa['nombre']}\" al iniciar",
                                [{"tipo": "inicio", "programa": programa, "activo": not activo}])
            app["notificar"](f"{programa['nombre']}: {'activado' if activo else 'desactivado'} al iniciar")
            cargar_programas()
            app["recalcular"]()
        else:
            app["notificar"]("No se pudo cambiar " + programa["nombre"], tema.CORAL)
            if activo:
                interruptor.deselect()
            else:
                interruptor.select()

    def desactivar_recomendados():
        sugeridos = [p for p in estado["programas"]
                     if p["activo"] and p["recomendacion"] == "desactivar" and not p["bloqueado"]]
        if not sugeridos:
            return
        nombres = "".join("  • " + p["nombre"] + "\n" for p in sugeridos)
        if not messagebox.askyesno("Desactivar programas de inicio",
                                   "Estos programas dejarán de abrirse solos al prender el PC:\n\n"
                                   + nombres + "\nPodrás volver a activarlos cuando quieras."):
            return
        pasos = []
        for programa in sugeridos:
            if inicio.cambiar_estado(programa, False):
                pasos.append({"tipo": "inicio", "programa": programa, "activo": True})
        if pasos:
            if len(pasos) == 1:
                texto = "Se desactivó " + pasos[0]["programa"]["nombre"] + " al iniciar"
            else:
                texto = f"Se desactivaron {len(pasos)} programas de inicio"
            historial.registrar("Inicio", texto, pasos)
            app["notificar"](texto)
        else:
            app["notificar"]("No se pudo desactivar ningún programa", tema.CORAL)
        cargar_programas()
        app["recalcular"]()

    boton_recomendados.configure(command=desactivar_recomendados)

    def cargar_programas():
        def listo(programas):
            estado["programas"] = programas or []
            dibujar_programas()
        app["en_segundo_plano"](inicio.programas_inicio, listo)

    # ------------------------------------------------------------
    #  Vista: procesos activos
    # ------------------------------------------------------------
    tabla = tema.tarjeta(vista_procesos, "Apps abiertas ahora",
                         "Agrupadas por nombre y ordenadas por memoria. Se actualiza cada 3 segundos. "
                         "Los procesos del sistema no se pueden cerrar desde aquí.")
    tabla.pack(fill="x")
    cabecera = ctk.CTkFrame(tabla, fg_color="transparent", height=1)
    cabecera.pack(fill="x", padx=20, pady=(0, 4))
    for texto, ancho in [("Cerrar", 92), ("Memoria", 100), ("CPU", 80)]:
        ctk.CTkLabel(cabecera, text=texto if texto != "Cerrar" else "", font=tema.fuente(11, True),
                     text_color=tema.TEXTO_TENUE, width=ancho, anchor="e").pack(side="right")
    ctk.CTkLabel(cabecera, text="Aplicación", font=tema.fuente(11, True), text_color=tema.TEXTO_TENUE,
                 anchor="w").pack(side="left")
    tema.separador(tabla).pack(fill="x", padx=20)

    filas_procesos = []

    def crear_filas_procesos():
        """Las filas se crean recién la primera vez que abres "Procesos activos":
        así la página se arma más rápido al iniciar."""
        if filas_procesos:
            return
        for _ in range(18):
            fila = ctk.CTkFrame(tabla, fg_color="transparent", height=1)
            fila.pack(fill="x", padx=20, pady=2)
            boton_cerrar = tema.boton(fila, "Cerrar", None, "peligro", ancho=80, alto=26)
            boton_cerrar.pack(side="right", padx=(12, 0))
            ram = ctk.CTkLabel(fila, text="", font=tema.fuente(13, True), text_color=tema.TEXTO,
                               width=100, anchor="e")
            ram.pack(side="right")
            cpu = ctk.CTkLabel(fila, text="", font=tema.fuente(13), text_color=tema.TEXTO_SUAVE,
                               width=80, anchor="e")
            cpu.pack(side="right")
            nombre = ctk.CTkLabel(fila, text="", font=tema.fuente(13), text_color=tema.TEXTO, anchor="w",
                                  width=320)
            nombre.pack(side="left")
            cantidad = ctk.CTkLabel(fila, text="", font=tema.fuente(11), text_color=tema.TEXTO_TENUE,
                                    anchor="w", width=90)
            cantidad.pack(side="left", padx=8)
            filas_procesos.append({"fila": fila, "nombre": nombre, "cantidad": cantidad, "cpu": cpu,
                                   "ram": ram, "cerrar": boton_cerrar, "app": ""})
        tema.espacio(tabla, 10)

    def cerrar(nombre_proceso):
        if not messagebox.askyesno("Cerrar aplicación",
                                   f"¿Cerrar todas las ventanas y procesos de {nombre_proceso}?\n\n"
                                   "Si tienes algo sin guardar en esa app, se puede perder."):
            return

        def listo(resultado):
            cerrados, fallidos = resultado or (0, 0)
            if cerrados:
                historial.registrar("Procesos", f"Se cerró {nombre_proceso} ({cerrados} procesos)")
                app["notificar"](f"Se cerró {nombre_proceso}")
            else:
                app["notificar"](f"No se pudo cerrar {nombre_proceso}", tema.CORAL)
            refrescar_procesos()

        app["en_segundo_plano"](lambda: inicio.cerrar_proceso(nombre_proceso), listo)

    def refrescar_procesos():
        def listo(lista):
            lista = lista or []
            # Solo se toca lo que cambió: redibujar 18 filas cada 3 segundos se nota en Windows
            for indice, fila in enumerate(filas_procesos):
                if indice >= len(lista):
                    for clave in ("nombre", "cantidad", "cpu", "ram"):
                        tema.actualizar(fila[clave], text="")
                    if fila.get("app") is not None:
                        fila["cerrar"].pack_forget()
                        fila["app"] = None
                    continue
                grupo = lista[indice]
                if fila.get("app") is None:
                    fila["cerrar"].pack(side="right", padx=(12, 0), before=fila["ram"])
                tema.actualizar(fila["nombre"], text=grupo["nombre"])
                tema.actualizar(fila["cantidad"],
                                text=f"{grupo['cantidad']} procesos" if grupo["cantidad"] > 1 else "")
                tema.actualizar(fila["cpu"], text=f"{grupo['cpu']:.1f} %")
                megas = grupo["ram"] / 1024 ** 2
                tema.actualizar(fila["ram"], text=f"{megas / 1024:.1f} GB" if megas >= 1024 else f"{megas:.0f} MB")
                if fila.get("app") != grupo["nombre"]:
                    fila["app"] = grupo["nombre"]
                    if grupo["protegido"]:
                        fila["cerrar"].configure(state="disabled", text="Sistema", command=None,
                                                 border_color=tema.LINEA)
                    else:
                        fila["cerrar"].configure(state="normal", text="Cerrar", border_color=tema.BORDE_PELIGRO,
                                                 command=lambda n=grupo["nombre"]: cerrar(n))
            estado["refrescando"] = False

        if not estado["refrescando"]:
            estado["refrescando"] = True
            app["en_segundo_plano"](inicio.procesos_activos, listo)

    def bucle_procesos():
        """Se repite cada 3 s mientras estés mirando la vista de procesos."""
        if app["pagina"] == "inicio" and estado["vista"] == "procesos":
            refrescar_procesos()
            app["ventana"].after(3000, bucle_procesos)
        else:
            estado["bucle"] = False

    def iniciar_bucle():
        if not estado["bucle"]:
            estado["bucle"] = True
            bucle_procesos()

    # ------------------------------------------------------------
    #  Cambio de vista
    # ------------------------------------------------------------
    def mostrar_vista(clave):
        estado["vista"] = clave
        for clave_boton, (boton, linea) in botones_vista.items():
            activo = clave_boton == clave
            boton.configure(text_color=tema.TEXTO if activo else tema.TEXTO_SUAVE)
            linea.configure(fg_color=tema.ORO if activo else tema.FONDO)
        vista_inicio.pack_forget()
        vista_procesos.pack_forget()
        if clave == "inicio":
            vista_inicio.pack(fill="both", expand=True)
        else:
            vista_procesos.pack(fill="both", expand=True)
            crear_filas_procesos()
            iniciar_bucle()

    mostrar_vista("inicio")
    cargar_programas()

    def al_mostrar():
        if estado["vista"] == "procesos":
            iniciar_bucle()

    return {"al_mostrar": al_mostrar}
