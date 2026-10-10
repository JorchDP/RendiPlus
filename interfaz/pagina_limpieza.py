"""
pagina_limpieza.py  -  Página "Limpieza". El trabajo lo hace motores/limpieza.py.
"""

from tkinter import messagebox

import customtkinter as ctk

from interfaz import tema
from motores import historial, limpieza


def construir(marco, app):
    categorias = limpieza.obtener_categorias()
    estado = {"resultados": {}, "aviso_admin": ""}
    filas = {}

    contenido = tema.pagina_con_scroll(marco)
    tema.encabezado(contenido, "Limpieza",
                    "Borra archivos temporales y cachés que tu PC ya no necesita.")
    cuerpo = ctk.CTkFrame(contenido, fg_color="transparent", height=1)
    cuerpo.pack(fill="both", expand=True, padx=32, pady=(0, 28))

    # ------------------------------------------------------------
    #  Resumen: cuánto se puede liberar
    # ------------------------------------------------------------
    resumen = tema.tarjeta(cuerpo)
    resumen.pack(fill="x", pady=(0, 18))
    izquierda = ctk.CTkFrame(resumen, fg_color="transparent", height=1)
    izquierda.pack(side="left", fill="x", expand=True, padx=26, pady=22)
    ctk.CTkLabel(izquierda, text="Espacio que puedes liberar", font=tema.fuente(13),
                 text_color=tema.TEXTO_SUAVE, anchor="w").pack(fill="x")
    numero = ctk.CTkLabel(izquierda, text="Sin analizar", font=tema.fuente(44, True, titulo=True),
                          text_color=tema.TEXTO, anchor="w", height=56)
    numero.pack(fill="x")
    detalle = ctk.CTkLabel(izquierda, text="", font=tema.fuente(12), text_color=tema.TEXTO_TENUE,
                           anchor="w")
    detalle.pack(fill="x")
    resultado = ctk.CTkLabel(izquierda, text="", font=tema.fuente(13, True), text_color=tema.VERDE,
                             anchor="w", justify="left")

    derecha = ctk.CTkFrame(resumen, fg_color="transparent", height=1)
    derecha.pack(side="right", padx=26, pady=22, before=izquierda)
    boton_analizar = tema.boton(derecha, "Analizar", None, "secundario", ancho=130, alto=42)
    boton_analizar.pack(side="left", padx=(0, 10))
    boton_limpiar = tema.boton(derecha, "Limpiar seleccionado", None, "primario", ancho=200, alto=42)
    boton_limpiar.pack(side="left")
    tema.activar_boton(boton_limpiar, False)

    barra = ctk.CTkProgressBar(resumen, mode="indeterminate", height=3, corner_radius=0,
                               fg_color=tema.SUPERFICIE, progress_color=tema.ORO)

    aviso = ctk.CTkLabel(cuerpo, text="", font=tema.fuente(12), text_color=tema.AMBAR,
                         anchor="w", justify="left")

    def poner_aviso(texto):
        if texto:
            aviso.configure(text=texto)
            aviso.pack(fill="x", padx=4, pady=(0, 14), after=resumen)
        else:
            aviso.pack_forget()

    # ------------------------------------------------------------
    #  Categorías
    # ------------------------------------------------------------
    tarjeta = tema.tarjeta(cuerpo, "Qué limpiar")
    tarjeta.pack(fill="x", pady=(0, 18))

    for indice, categoria in enumerate(categorias):
        if indice > 0:
            tema.separador(tarjeta).pack(fill="x", padx=20, pady=4)
        fila = ctk.CTkFrame(tarjeta, fg_color="transparent", height=1)
        fila.pack(fill="x", padx=20, pady=(8, 0))
        marcado = ctk.BooleanVar(value=categoria["recomendado"] and categoria["disponible"])
        caja = tema.casilla(fila, categoria["nombre"], marcado)
        caja.pack(side="left")
        if not categoria["disponible"]:
            caja.configure(state="disabled", text_color=tema.TEXTO_TENUE)
            tema.insignia(fila, "Requiere administrador", tema.TEXTO_SUAVE).pack(side="left", padx=12)
            estado["aviso_admin"] = ("Algunas categorías necesitan permisos de administrador. "
                                     "Usa \"Abrir como administrador\" en el menú lateral.")
        elif not categoria["recomendado"]:
            tema.insignia(fila, "Opcional", tema.AMBAR).pack(side="left", padx=12)
        tamano = ctk.CTkLabel(fila, text="", font=tema.fuente(15, True, titulo=True),
                              text_color=tema.TEXTO, width=110, anchor="e")
        tamano.pack(side="right")
        ctk.CTkLabel(tarjeta, text=categoria["descripcion"], font=tema.fuente(12),
                     text_color=tema.TEXTO_SUAVE, anchor="w", justify="left",
                     wraplength=760).pack(fill="x", padx=(52, 20), pady=(0, 8))
        filas[categoria["id"]] = {"categoria": categoria, "marcado": marcado, "caja": caja,
                                  "tamano": tamano}
    tema.espacio(tarjeta, 8)

    # ------------------------------------------------------------
    #  Archivos grandes
    # ------------------------------------------------------------
    grandes = tema.tarjeta(cuerpo, "Archivos grandes",
                           "Archivos de más de 500 MB en Descargas, Escritorio, Documentos y Videos. "
                           "RendiPlus no los borra: te muestra dónde están para que decidas tú.")
    grandes.pack(fill="x")
    boton_buscar = tema.boton(grandes.cabeza, "Buscar archivos grandes", None, "secundario", alto=32)
    boton_buscar.pack(side="right")
    lista_grandes = ctk.CTkFrame(grandes, fg_color="transparent", height=1)
    lista_grandes.pack(fill="x", padx=20, pady=(0, 16))

    # ------------------------------------------------------------
    #  Lógica
    # ------------------------------------------------------------
    def mostrar_espacio_libre():
        detalle.configure(text="Espacio libre en tu disco principal: "
                               + tema.formato_gb(limpieza.espacio_libre_principal()))

    def seleccionadas():
        lista = []
        for datos in filas.values():
            if datos["marcado"].get() and datos["categoria"]["disponible"]:
                lista.append(datos["categoria"])
        return lista

    def mostrar_apps_abiertas(abiertas):
        estado["abiertas"] = abiertas or []
        texto = estado["aviso_admin"]
        if abiertas:
            if texto:
                texto = texto + "\n"
            texto = texto + "Cierra " + ", ".join(abiertas) + \
                " para limpiar su caché completa. Si siguen abiertos, se saltan los archivos en uso."
        poner_aviso(texto)

    def revisar_apps_abiertas():
        """Revisa en segundo plano qué apps están abiertas (recorrer procesos es lento)."""
        procesos = []
        for categoria in seleccionadas():
            procesos = procesos + categoria["procesos"]
        app["en_segundo_plano"](lambda: limpieza.apps_abiertas(procesos), mostrar_apps_abiertas)

    def actualizar_total():
        if not estado["resultados"]:
            return
        total = 0
        hay_desconocidos = False
        for categoria in seleccionadas():
            info = estado["resultados"].get(categoria["id"], {})
            total = total + info.get("bytes", 0)
            if info.get("error"):
                hay_desconocidos = True
        numero.configure(text=tema.formato_gb(total) if total else "Nada pendiente",
                         text_color=tema.ORO if total else tema.TEXTO)
        tema.activar_boton(boton_limpiar, total > 0 or hay_desconocidos)
        revisar_apps_abiertas()

    for datos in filas.values():
        datos["caja"].configure(command=actualizar_total)

    def ocupado(si):
        if si:
            boton_analizar.configure(state="disabled")
            tema.activar_boton(boton_limpiar, False)
            barra.place(relx=0, rely=1.0, relwidth=1, anchor="sw")
            barra.start()
        else:
            barra.stop()
            barra.place_forget()
            boton_analizar.configure(state="normal")

    def analizar():
        ocupado(True)
        numero.configure(text="Analizando...", text_color=tema.TEXTO_SUAVE)
        for datos in filas.values():
            datos["tamano"].configure(text="...", text_color=tema.TEXTO_TENUE)

        def trabajo():
            resultados = {}
            for categoria in categorias:
                try:
                    resultados[categoria["id"]] = limpieza.analizar_categoria(categoria)
                except Exception as error:
                    resultados[categoria["id"]] = {"bytes": 0, "archivos": 0, "error": str(error)}
            return resultados

        def terminado(resultados):
            estado["resultados"] = resultados or {}
            ocupado(False)
            for id_categoria, datos in filas.items():
                info = estado["resultados"].get(id_categoria, {"bytes": 0})
                if info.get("error") and info["bytes"] == 0:
                    datos["tamano"].configure(text="?", text_color=tema.TEXTO_TENUE)
                elif info["bytes"] >= 1024 ** 3:
                    datos["tamano"].configure(text=tema.formato_gb(info["bytes"]), text_color=tema.ORO)
                else:
                    datos["tamano"].configure(text=tema.formato_gb(info["bytes"]), text_color=tema.TEXTO)
            mostrar_espacio_libre()
            actualizar_total()

        app["en_segundo_plano"](trabajo, terminado)

    def limpiar():
        lista = seleccionadas()
        if not lista:
            return
        nombres = ""
        for categoria in lista:
            nombres = nombres + "  • " + categoria["nombre"] + "\n"
        mensaje = "Se va a limpiar:\n\n" + nombres + "\nEsto no se puede deshacer. ¿Continuar?"
        abiertas = estado.get("abiertas", [])
        if abiertas:
            mensaje = mensaje + "\n\n" + ", ".join(abiertas) + \
                " está abierto: algunos archivos se van a saltar."
        if not messagebox.askyesno("Confirmar limpieza", mensaje):
            return

        ocupado(True)
        numero.configure(text="Limpiando...", text_color=tema.TEXTO_SUAVE)
        resultado.pack_forget()

        def trabajo():
            total = {"liberado": 0, "borrados": 0, "fallidos": 0}
            for categoria in lista:
                try:
                    parcial = limpieza.limpiar_categoria(categoria)
                except Exception:
                    continue
                for clave in total:
                    total[clave] = total[clave] + parcial[clave]
            return total

        def terminado(total):
            total = total or {"liberado": 0, "borrados": 0, "fallidos": 0}
            texto = "Liberaste " + tema.formato_gb(total["liberado"]) + " (" + \
                str(total["borrados"]) + " archivos)."
            if total["fallidos"]:
                texto = texto + " " + str(total["fallidos"]) + " archivos estaban en uso y se dejaron."
            resultado.configure(text=texto)
            resultado.pack(fill="x", pady=(8, 0))
            historial.registrar("Limpieza", "Limpieza: se liberaron " + tema.formato_gb(total["liberado"]))
            app["notificar"]("Liberaste " + tema.formato_gb(total["liberado"]))
            app["recalcular"]()
            analizar()

        app["en_segundo_plano"](trabajo, terminado)

    def buscar_grandes():
        boton_buscar.configure(state="disabled", text="Buscando...")
        for widget in lista_grandes.winfo_children():
            widget.destroy()

        def terminado(encontrados):
            boton_buscar.configure(state="normal", text="Buscar de nuevo")
            if not encontrados:
                ctk.CTkLabel(lista_grandes, text="No hay archivos de más de 500 MB en esas carpetas.",
                             font=tema.fuente(13), text_color=tema.VERDE, anchor="w").pack(fill="x")
                return
            for indice, archivo in enumerate(encontrados):
                if indice > 0:
                    tema.separador(lista_grandes).pack(fill="x", pady=2)
                fila = ctk.CTkFrame(lista_grandes, fg_color="transparent", height=1)
                fila.pack(fill="x", pady=4)
                tema.boton(fila, "Mostrar", lambda ruta=archivo["ruta"]: limpieza.mostrar_en_carpeta(ruta),
                           "secundario", ancho=86, alto=28).pack(side="right")
                ctk.CTkLabel(fila, text=tema.formato_gb(archivo["tamano"]), width=90, anchor="e",
                             font=tema.fuente(14, True, titulo=True),
                             text_color=tema.TEXTO).pack(side="right", padx=14)
                if archivo["dias"] == 0:
                    antiguedad = "hoy"
                elif archivo["dias"] == 1:
                    antiguedad = "ayer"
                else:
                    antiguedad = "hace " + str(archivo["dias"]) + " días"
                ctk.CTkLabel(fila, text=antiguedad, font=tema.fuente(12), text_color=tema.TEXTO_TENUE,
                             width=110, anchor="e").pack(side="right")
                nombre = archivo["nombre"]
                if len(nombre) > 64:
                    nombre = nombre[:61] + "..."
                ctk.CTkLabel(fila, text=nombre, font=tema.fuente(13), text_color=tema.TEXTO,
                             anchor="w").pack(side="left")

        app["en_segundo_plano"](limpieza.buscar_archivos_grandes, terminado)

    boton_analizar.configure(command=analizar)
    boton_limpiar.configure(command=limpiar)
    boton_buscar.configure(command=buscar_grandes)
    mostrar_espacio_libre()
    poner_aviso(estado["aviso_admin"])

    primera_vez = {"si": True}

    def al_mostrar():
        if primera_vez["si"]:
            primera_vez["si"] = False
            analizar()   # la primera vez que entras, analiza solo

    return {"al_mostrar": al_mostrar}
