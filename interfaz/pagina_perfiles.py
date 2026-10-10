"""
pagina_perfiles.py  -  Página "Perfiles": tres perfiles y ajustes individuales.
"""

from tkinter import messagebox

import customtkinter as ctk

from interfaz import tema
from motores import historial, perfiles
from motores.sistema import SISTEMA

COLOR_IMPACTO = {"Alto": tema.ORO, "Medio": tema.ACERO, "Bajo": tema.TEXTO_SUAVE,
                 "Puntería": tema.ACERO, "Variable": tema.AMBAR}


def construir(marco, app):
    contenido = tema.pagina_con_scroll(marco)
    tema.encabezado(contenido, "Perfiles",
                    "Cambia varios ajustes de Windows de una vez según lo que vayas a hacer."
                    if SISTEMA == "Windows" else
                    "Cambia varios ajustes de una vez según lo que vayas a hacer.")
    cuerpo = ctk.CTkFrame(contenido, fg_color="transparent", height=1)
    cuerpo.pack(fill="both", expand=True, padx=32, pady=(0, 28))

    # ------------------------------------------------------------
    #  Las tres tarjetas de perfil
    # ------------------------------------------------------------
    fila_perfiles = ctk.CTkFrame(cuerpo, fg_color="transparent", height=1)
    fila_perfiles.pack(fill="x", pady=(0, 18))
    tarjetas = {}
    for indice, (clave, perfil) in enumerate(perfiles.PERFILES.items()):
        fila_perfiles.grid_columnconfigure(indice, weight=1, uniform="perfiles")
        tarjeta = ctk.CTkFrame(fila_perfiles, fg_color=tema.SUPERFICIE, corner_radius=tema.RADIO,
                               border_width=1, border_color=tema.LINEA)
        tarjeta.grid(row=0, column=indice, sticky="nsew", padx=(0 if indice == 0 else 9, 0 if indice == 2 else 9))

        arriba = ctk.CTkFrame(tarjeta, fg_color="transparent", height=1)
        arriba.pack(fill="x", padx=22, pady=(22, 0))
        ctk.CTkLabel(arriba, text=perfil["nombre"], font=tema.fuente(24, True, titulo=True),
                     text_color=tema.TEXTO, anchor="w").pack(side="left")
        insignia = tema.insignia(arriba, "Activo", tema.ORO)
        ctk.CTkLabel(tarjeta, text=perfil["para"], font=tema.fuente(13), text_color=tema.TEXTO_SUAVE,
                     anchor="w").pack(fill="x", padx=22, pady=(2, 14))
        tema.separador(tarjeta).pack(fill="x", padx=22, pady=(0, 10))
        for cambio in perfil["cambios"]:
            linea = ctk.CTkFrame(tarjeta, fg_color="transparent", height=1)
            linea.pack(fill="x", padx=22, pady=3)
            ctk.CTkFrame(linea, width=10, height=2, fg_color=tema.ORO, corner_radius=1).pack(
                side="left", padx=(0, 10))
            ctk.CTkLabel(linea, text=cambio, font=tema.fuente(13), text_color=tema.TEXTO,
                         anchor="w", justify="left", wraplength=230).pack(side="left", fill="x")
        boton = tema.boton(tarjeta, "Activar " + perfil["nombre"], lambda c=clave: activar(c),
                           "secundario", alto=40)
        boton.pack(side="bottom", fill="x", padx=22, pady=22)
        tarjetas[clave] = {"tarjeta": tarjeta, "insignia": insignia, "boton": boton}

    # ------------------------------------------------------------
    #  Ajustes individuales (solo Windows)
    # ------------------------------------------------------------
    tarjeta_ajustes = None
    contenedor_ajustes = None
    if SISTEMA == "Windows":
        tarjeta_ajustes = tema.tarjeta(cuerpo, "Ajustes individuales",
                                       "Cambia cada ajuste por separado. Todo queda en el Historial "
                                       "para que puedas deshacerlo.")
        tarjeta_ajustes.pack(fill="x", pady=(0, 18))
        contenedor_ajustes = ctk.CTkFrame(tarjeta_ajustes, fg_color="transparent", height=1)
        contenedor_ajustes.pack(fill="x", padx=20, pady=(0, 14))

        fila_plan = ctk.CTkFrame(tarjeta_ajustes, fg_color="transparent", height=1)
        tema.separador(tarjeta_ajustes).pack(fill="x", padx=20)
        fila_plan.pack(fill="x", padx=20, pady=16)
        ctk.CTkLabel(fila_plan, text="Plan de energía", font=tema.fuente(14, True),
                     text_color=tema.TEXTO, anchor="w").pack(side="left")
        menu_planes = ctk.CTkOptionMenu(
            fila_plan, values=["Cargando..."], width=260, height=34, corner_radius=8,
            fg_color=tema.SUPERFICIE_ALTA, button_color=tema.LINEA, button_hover_color=tema.TEXTO_TENUE,
            dropdown_fg_color=tema.SUPERFICIE_ALTA, dropdown_hover_color=tema.LINEA,
            text_color=tema.TEXTO, dropdown_text_color=tema.TEXTO, font=tema.fuente(13),
            dropdown_font=tema.fuente(13),
        )
        menu_planes.pack(side="right")
    else:
        menu_planes = None

    # ------------------------------------------------------------
    #  Apps que se cierran con "Rendimiento"
    # ------------------------------------------------------------
    tarjeta_apps = tema.tarjeta(cuerpo, "Apps que se cierran al activar Rendimiento",
                                "Marca las apps que no necesitas abiertas mientras juegas. "
                                "Solo se cierran si están abiertas en ese momento.")
    tarjeta_apps.pack(fill="x")
    grilla_apps = ctk.CTkFrame(tarjeta_apps, fg_color="transparent", height=1)
    grilla_apps.pack(fill="x", padx=20, pady=(0, 18))
    elegidas = perfiles.apps_a_cerrar()
    variables_apps = {}

    def guardar_apps():
        lista = [proceso for proceso, variable in variables_apps.items() if variable.get()]
        perfiles.guardar_apps_a_cerrar(lista)

    for indice, (proceso, nombre, marcada) in enumerate(perfiles.APPS_CANDIDATAS):
        grilla_apps.grid_columnconfigure(indice % 3, weight=1, uniform="apps")
        variable = ctk.BooleanVar(value=proceso in elegidas)
        caja = tema.casilla(grilla_apps, nombre, variable, guardar_apps)
        caja.configure(font=tema.fuente(13))
        caja.grid(row=indice // 3, column=indice % 3, sticky="w", pady=6)
        variables_apps[proceso] = variable

    # ------------------------------------------------------------
    #  Lógica
    # ------------------------------------------------------------
    def marcar_activo():
        activo = perfiles.perfil_activo()
        for clave, partes in tarjetas.items():
            if clave == activo:
                partes["tarjeta"].configure(border_color=tema.ORO, border_width=2)
                partes["insignia"].pack(side="right")
                partes["boton"].configure(text="Volver a aplicar")
                tema_boton(partes["boton"], "secundario")
            else:
                partes["tarjeta"].configure(border_color=tema.LINEA, border_width=1)
                partes["insignia"].pack_forget()
                partes["boton"].configure(text="Activar " + perfiles.PERFILES[clave]["nombre"])
                tema_boton(partes["boton"], "primario" if clave == "rendimiento" and not activo else "secundario")

    def tema_boton(boton, estilo):
        if estilo == "primario":
            boton.configure(fg_color=tema.ORO, hover_color=tema.ORO_CLARO, text_color=tema.TEXTO_SOBRE_ORO,
                            border_width=0)
        else:
            boton.configure(fg_color=tema.SUPERFICIE_ALTA, hover_color=tema.LINEA, text_color=tema.TEXTO,
                            border_width=1)

    def activar(clave):
        perfil = perfiles.PERFILES[clave]
        for partes in tarjetas.values():
            partes["boton"].configure(state="disabled")
        tarjetas[clave]["boton"].configure(text="Aplicando...")

        def listo(respuesta):
            for partes in tarjetas.values():
                partes["boton"].configure(state="normal")
            if not respuesta:
                app["notificar"]("No se pudo aplicar el perfil", tema.CORAL)
                marcar_activo()
                return
            resultados, deshacer = respuesta
            historial.registrar("Perfil", "Se activó el perfil " + perfil["nombre"], deshacer)
            fallidos = [texto for texto, bien in resultados if not bien]
            if fallidos:
                messagebox.showwarning("Perfil " + perfil["nombre"],
                                       "El perfil se aplicó, pero algunas cosas no se pudieron cambiar:\n\n"
                                       + "\n".join("  • " + t for t in fallidos))
            app["notificar"]("Perfil " + perfil["nombre"] + " activado")
            marcar_activo()
            cargar_ajustes()
            app["emitir"]("perfil")
            app["recalcular"]()

        app["en_segundo_plano"](lambda: perfiles.aplicar_perfil(clave), listo)

    def cambiar_ajuste(ajuste, interruptor):
        nuevo = bool(interruptor.get())
        if perfiles.escribir_ajuste(ajuste["id"], nuevo):
            historial.registrar("Ajuste", ajuste["nombre"] + (": activado" if nuevo else ": desactivado"),
                                [{"tipo": "ajuste", "id": ajuste["id"], "valor": not nuevo}])
            texto = ajuste["nombre"] + (" activado" if nuevo else " desactivado")
            if ajuste["requiere_reinicio"]:
                texto = texto + ". Reinicia el PC para aplicarlo"
            app["notificar"](texto)
            app["recalcular"]()
        else:
            app["notificar"]("No se pudo cambiar " + ajuste["nombre"], tema.CORAL)
            if nuevo:
                interruptor.deselect()
            else:
                interruptor.select()

    def cargar_ajustes():
        if contenedor_ajustes is None:
            return

        def trabajo():
            return perfiles.ajustes_disponibles(), perfiles.planes_energia()

        def listo(respuesta):
            if not respuesta:
                return
            ajustes, planes = respuesta
            for widget in contenedor_ajustes.winfo_children():
                widget.destroy()
            for indice, ajuste in enumerate(ajustes):
                if indice > 0:
                    tema.separador(contenedor_ajustes).pack(fill="x")
                fila = ctk.CTkFrame(contenedor_ajustes, fg_color="transparent", height=1)
                fila.pack(fill="x", pady=12)
                interruptor = tema.interruptor(fila)
                interruptor.pack(side="right")
                if ajuste["valor"]:
                    interruptor.select()
                interruptor.configure(command=lambda a=ajuste, i=interruptor: cambiar_ajuste(a, i))
                if ajuste["bloqueado"] or ajuste["valor"] is None:
                    interruptor.configure(state="disabled")
                textos = ctk.CTkFrame(fila, fg_color="transparent", height=1)
                textos.pack(side="left", fill="x", expand=True)
                arriba = ctk.CTkFrame(textos, fg_color="transparent", height=1)
                arriba.pack(fill="x")
                ctk.CTkLabel(arriba, text=ajuste["nombre"], font=tema.fuente(14, True),
                             text_color=tema.TEXTO, anchor="w").pack(side="left")
                tema.insignia(arriba, "Impacto: " + ajuste["impacto"],
                              COLOR_IMPACTO.get(ajuste["impacto"], tema.TEXTO_SUAVE)).pack(side="left", padx=10)
                if ajuste["bloqueado"]:
                    tema.insignia(arriba, "Requiere administrador", tema.TEXTO_SUAVE).pack(side="left")
                elif ajuste["requiere_reinicio"]:
                    tema.insignia(arriba, "Requiere reiniciar", tema.TEXTO_SUAVE).pack(side="left")
                ctk.CTkLabel(textos, text=ajuste["descripcion"], font=tema.fuente(12),
                             text_color=tema.TEXTO_SUAVE, anchor="w", justify="left",
                             wraplength=720).pack(fill="x", pady=(2, 0))

            nombres = [plan["nombre"] for plan in planes]
            if nombres:
                menu_planes.configure(values=nombres, command=lambda nombre: elegir_plan(nombre, planes))
                for plan in planes:
                    if plan["activo"]:
                        menu_planes.set(plan["nombre"])
            else:
                menu_planes.configure(values=["No disponible"])
                menu_planes.set("No disponible")

        app["en_segundo_plano"](trabajo, listo)

    def elegir_plan(nombre, planes):
        anterior = next((p for p in planes if p["activo"]), None)
        elegido = next((p for p in planes if p["nombre"] == nombre), None)
        if not elegido or (anterior and anterior["guid"] == elegido["guid"]):
            return
        if perfiles.activar_plan(elegido["guid"]):
            pasos = [{"tipo": "plan", "valor": anterior["guid"]}] if anterior else []
            historial.registrar("Ajuste", "Plan de energía: " + nombre, pasos)
            app["notificar"]("Plan de energía: " + nombre)
            cargar_ajustes()
            app["recalcular"]()
        else:
            app["notificar"]("No se pudo cambiar el plan de energía", tema.CORAL)

    app["suscribir"]("perfil", lambda dato: marcar_activo())   # por si se cambió desde la bandeja

    def al_mostrar():
        marcar_activo()     # por si se deshizo un perfil desde el Historial
        cargar_ajustes()

    return {"al_mostrar": al_mostrar}
