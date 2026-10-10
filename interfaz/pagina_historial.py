"""
pagina_historial.py  -  Página "Historial": lo que RendiPlus cambió y cómo deshacerlo.
"""

from tkinter import messagebox

import customtkinter as ctk

from interfaz import tema
from motores import historial, sistema

COLOR_TIPO = {"Perfil": tema.ORO, "Ajuste": tema.ACERO, "Inicio": tema.ACERO, "Limpieza": tema.VERDE,
              "Procesos": tema.TEXTO_SUAVE, "Sistema": tema.VERDE}


def construir(marco, app):
    contenido = tema.pagina_con_scroll(marco)
    cabeza = tema.encabezado(contenido, "Historial",
                             "Todo lo que RendiPlus cambió en tu PC, y cómo deshacerlo.")
    tema.boton(cabeza.acciones, "Restaurar todo", lambda: restaurar_todo(), "peligro",
               ancho=150).pack(side="right")
    cuerpo = ctk.CTkFrame(contenido, fg_color="transparent", height=1)
    cuerpo.pack(fill="both", expand=True, padx=32, pady=(0, 28))

    # ------------------------------------------------------------
    #  Protección
    # ------------------------------------------------------------
    if sistema.SISTEMA == "Windows":
        proteccion = tema.tarjeta(cuerpo, "Punto de restauración",
                                  "Una copia de la configuración de Windows a la que puedes volver si algo "
                                  "sale mal. Recomendado antes de activar perfiles por primera vez.")
        proteccion.pack(fill="x", pady=(0, 18))
        boton_punto = tema.boton(proteccion.cabeza, "Crear punto de restauración", None, "secundario", alto=32)
        boton_punto.pack(side="right")
        if not sistema.es_admin():
            boton_punto.configure(state="disabled")
            ctk.CTkLabel(proteccion, text="Necesitas abrir RendiPlus como administrador para crearlo.",
                         font=tema.fuente(12), text_color=tema.AMBAR, anchor="w").pack(
                fill="x", padx=20, pady=(0, 14))
        else:
            tema.espacio(proteccion, 4)

        def crear_punto():
            boton_punto.configure(state="disabled", text="Creando...")

            def listo(respuesta):
                boton_punto.configure(state="normal", text="Crear punto de restauración")
                bien, mensaje = respuesta or (False, "No se pudo crear el punto de restauración.")
                app["notificar"](mensaje, tema.VERDE if bien else tema.AMBAR)
                cargar()

            app["en_segundo_plano"](historial.crear_punto_restauracion, listo)

        boton_punto.configure(command=crear_punto)

    # ------------------------------------------------------------
    #  Lista de cambios
    # ------------------------------------------------------------
    tarjeta = tema.tarjeta(cuerpo, "Cambios")
    tarjeta.pack(fill="x")
    tema.boton(tarjeta.cabeza, "Abrir carpeta de datos", lambda: sistema.abrir(sistema.carpeta_datos()),
               "fantasma", alto=30).pack(side="right")
    lista = ctk.CTkFrame(tarjeta, fg_color="transparent", height=1)
    lista.pack(fill="x", padx=20, pady=(0, 14))

    def deshacer(entrada):
        if not messagebox.askyesno("Deshacer cambio", "¿Deshacer este cambio?\n\n" + entrada["descripcion"]):
            return
        def listo(resultado):
            bien, mal = resultado or (0, 1)
            if mal:
                app["notificar"](f"Se deshizo en parte: {mal} pasos no se pudieron revertir", tema.AMBAR)
            else:
                app["notificar"]("Cambio deshecho")
            terminar_cambio()

        app["en_segundo_plano"](lambda: historial.deshacer(entrada["id"]), listo)

    def restaurar_todo():
        if not messagebox.askyesno("Restaurar todo",
                                   "Se van a deshacer todos los cambios de perfiles, ajustes y programas "
                                   "de inicio que hizo RendiPlus.\n\nLo que se limpió no se puede recuperar. "
                                   "¿Continuar?"):
            return
        def listo(resultado):
            bien, mal = resultado or (0, 1)
            if bien == 0 and mal == 0:
                app["notificar"]("No había cambios que deshacer", tema.TEXTO_SUAVE)
            elif mal:
                app["notificar"](f"Restaurado en parte: {mal} pasos no se pudieron revertir", tema.AMBAR)
            else:
                app["notificar"]("Todo volvió a como estaba")
            terminar_cambio()

        app["en_segundo_plano"](historial.restaurar_todo, listo)

    def terminar_cambio():
        cargar()
        app["emitir"]("perfil")
        app["recalcular"]()

    def cargar():
        for widget in lista.winfo_children():
            widget.destroy()
        entradas = historial.listar()
        if not entradas:
            ctk.CTkLabel(lista, text="Todavía no hay cambios. Cuando actives un perfil, limpies o "
                                     "desactives programas de inicio, aparecerán aquí.",
                         font=tema.fuente(13), text_color=tema.TEXTO_SUAVE, anchor="w",
                         justify="left", wraplength=800).pack(fill="x", pady=6)
            return
        for indice, entrada in enumerate(entradas[:120]):
            if indice > 0:
                tema.separador(lista).pack(fill="x")
            fila = ctk.CTkFrame(lista, fg_color="transparent", height=1)
            fila.pack(fill="x", pady=8)
            ctk.CTkLabel(fila, text=entrada["fecha"], font=tema.fuente(12), text_color=tema.TEXTO_TENUE,
                         width=128, anchor="w").pack(side="left")
            tema.insignia(fila, entrada["tipo"], COLOR_TIPO.get(entrada["tipo"], tema.TEXTO_SUAVE)).pack(
                side="left", padx=(0, 12))
            color_texto = tema.TEXTO_TENUE if entrada["deshecho"] else tema.TEXTO
            ctk.CTkLabel(fila, text=entrada["descripcion"], font=tema.fuente(13), text_color=color_texto,
                         anchor="w").pack(side="left", fill="x", expand=True)
            if entrada["deshecho"]:
                ctk.CTkLabel(fila, text="Deshecho", font=tema.fuente(12), text_color=tema.TEXTO_TENUE).pack(
                    side="right", padx=8)
            elif entrada["deshacer"]:
                tema.boton(fila, "Deshacer", lambda e=entrada: deshacer(e), "secundario",
                           ancho=96, alto=28).pack(side="right")
            else:
                ctk.CTkLabel(fila, text="No reversible", font=tema.fuente(12),
                             text_color=tema.TEXTO_TENUE).pack(side="right", padx=8)

    return {"al_mostrar": cargar}
