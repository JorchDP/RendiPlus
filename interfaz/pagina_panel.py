"""
pagina_panel.py  -  Página "Panel": resumen del equipo, salud y actividad en vivo.
"""

import customtkinter as ctk

from interfaz import tema
from motores import hardware


def construir(marco, app):
    contenido = tema.pagina_con_scroll(marco)
    cabeza = tema.encabezado(contenido, "Resumen del equipo", "Leyendo los componentes de tu PC...")
    boton_copiar = tema.boton(cabeza.acciones, "Copiar informe", None, "secundario", ancho=150)
    boton_copiar.pack()

    cuerpo = ctk.CTkFrame(contenido, fg_color="transparent", height=1)
    cuerpo.pack(fill="both", expand=True, padx=32, pady=(0, 28))
    cuerpo.grid_columnconfigure(0, weight=0, minsize=310)
    cuerpo.grid_columnconfigure(1, weight=1)

    # ------------------------------------------------------------
    #  Salud del equipo (dial)
    # ------------------------------------------------------------
    salud = tema.tarjeta(cuerpo, "Salud del equipo")
    salud.grid(row=0, column=0, sticky="nsew", padx=(0, 18), pady=(0, 18))
    dial = tema.crear_dial(salud, 236)
    dial.pack(padx=20, pady=(6, 0))
    tema.dibujar_dial(dial, None)
    resumen_salud = ctk.CTkLabel(salud, text="Revisando tu equipo...", font=tema.fuente(12),
                                 text_color=tema.TEXTO_SUAVE, wraplength=250, justify="center")
    resumen_salud.pack(padx=20, pady=(0, 14))
    tema.boton(salud, "Ver recomendaciones", lambda: app["ir_a"]("recomendaciones"),
               "secundario").pack(fill="x", padx=20, pady=(0, 20))

    # ------------------------------------------------------------
    #  Actividad en vivo: métricas + gráfico
    # ------------------------------------------------------------
    actividad = tema.tarjeta(cuerpo)
    actividad.grid(row=0, column=1, sticky="nsew", pady=(0, 18))

    metricas = ctk.CTkFrame(actividad, fg_color="transparent", height=1)
    metricas.pack(fill="x", padx=24, pady=(20, 8))

    series = []
    widgets_metrica = {}

    def agregar_metrica(clave, titulo, color, relleno):
        """Agrega una columna (Procesador, Memoria, Gráficos). La de la GPU se agrega
        cuando el driver de NVIDIA termina de iniciarse, sin hacer esperar a la ventana."""
        indice = len(series)
        series.append((clave, titulo, color, relleno))
        if indice > 0:
            tema.separador(metricas, vertical=True).grid(row=0, column=indice * 2 - 1,
                                                         sticky="ns", padx=22, pady=4)
        columna = ctk.CTkFrame(metricas, fg_color="transparent", height=1)
        columna.grid(row=0, column=indice * 2, sticky="nsew")
        metricas.grid_columnconfigure(indice * 2, weight=1)

        arriba = ctk.CTkFrame(columna, fg_color="transparent", height=1)
        arriba.pack(fill="x")
        ctk.CTkFrame(arriba, width=8, height=8, corner_radius=4, fg_color=color).pack(side="left")
        ctk.CTkLabel(arriba, text=titulo, font=tema.fuente(13), text_color=tema.TEXTO_SUAVE,
                     anchor="w").pack(side="left", padx=8)
        valor = ctk.CTkLabel(columna, text="0 %", font=tema.fuente(40, True, titulo=True),
                             text_color=tema.TEXTO, anchor="w", height=50, width=150)
        valor.pack(fill="x")
        detalle = ctk.CTkLabel(columna, text="", font=tema.fuente(12), text_color=tema.TEXTO_TENUE,
                               anchor="w", width=200)
        detalle.pack(fill="x")
        barra = tema.barra(columna, color, alto=4)
        barra.pack(fill="x", pady=(8, 0))
        widgets_metrica[clave] = {"valor": valor, "detalle": detalle, "barra": barra}

    agregar_metrica("cpu", "Procesador", tema.ORO, tema.RELLENO_ORO)
    agregar_metrica("ram", "Memoria", tema.ACERO, None)

    def revisar_gpu(dato=None):
        if hardware.NVIDIA_OK and "gpu" not in widgets_metrica:
            agregar_metrica("gpu", "Gráficos", tema.VERDE, None)

    leyenda = ctk.CTkFrame(actividad, fg_color="transparent", height=1)
    leyenda.pack(fill="x", padx=24, pady=(14, 0))
    ctk.CTkLabel(leyenda, text="Último minuto", font=tema.fuente(12, True),
                 text_color=tema.TEXTO_SUAVE, anchor="w").pack(side="left")
    grafico = tema.crear_grafico(actividad, 170)
    grafico.pack(fill="x", padx=(14, 20), pady=(6, 18))

    # ------------------------------------------------------------
    #  Apps que más memoria usan
    # ------------------------------------------------------------
    apps = tema.tarjeta(cuerpo, "Apps que más memoria usan")
    apps.grid(row=1, column=0, sticky="nsew", padx=(0, 18), pady=(0, 18))
    filas_apps = []
    for _ in range(6):
        fila = ctk.CTkFrame(apps, fg_color="transparent", height=1)
        fila.pack(fill="x", padx=20, pady=3)
        nombre = ctk.CTkLabel(fila, text="", font=tema.fuente(13), text_color=tema.TEXTO, anchor="w",
                              width=180)
        nombre.pack(side="left")
        memoria = ctk.CTkLabel(fila, text="", font=tema.fuente(13, True), text_color=tema.TEXTO_SUAVE,
                               anchor="e", width=70)
        memoria.pack(side="right")
        filas_apps.append((nombre, memoria))
    tema.boton(apps, "Administrar procesos", lambda: app["ir_a"]("inicio"), "fantasma",
               alto=32).pack(anchor="w", padx=12, pady=(6, 14))

    # ------------------------------------------------------------
    #  Almacenamiento
    # ------------------------------------------------------------
    discos = tema.tarjeta(cuerpo, "Almacenamiento")
    discos.grid(row=1, column=1, sticky="nsew", pady=(0, 18))
    lista_discos = ctk.CTkFrame(discos, fg_color="transparent", height=1)
    lista_discos.pack(fill="x", padx=20, pady=(0, 6))
    ctk.CTkLabel(lista_discos, text="Leyendo discos...", font=tema.fuente(12),
                 text_color=tema.TEXTO_TENUE).pack(anchor="w")
    tema.boton(discos, "Liberar espacio", lambda: app["ir_a"]("limpieza"), "fantasma",
               alto=32).pack(anchor="w", padx=12, pady=(0, 14))

    # ------------------------------------------------------------
    #  Especificaciones
    # ------------------------------------------------------------
    especificaciones = tema.tarjeta(cuerpo, "Especificaciones")
    especificaciones.grid(row=2, column=0, columnspan=2, sticky="nsew")
    columnas_specs = ctk.CTkFrame(especificaciones, fg_color="transparent", height=1)
    columnas_specs.pack(fill="x", padx=20, pady=(0, 18))
    for columna in range(4):
        columnas_specs.grid_columnconfigure(columna, weight=1, uniform="specs")

    # ------------------------------------------------------------
    #  Actualizar con datos
    # ------------------------------------------------------------
    def columna_specs(indice, titulo, datos):
        columna = ctk.CTkFrame(columnas_specs, fg_color="transparent", height=1)
        columna.grid(row=0, column=indice, sticky="nsew", padx=(0, 18))
        ctk.CTkLabel(columna, text=titulo, font=tema.fuente(13, True), text_color=tema.ORO,
                     anchor="w").pack(fill="x", pady=(0, 6))
        for etiqueta, valor in datos.items():
            ctk.CTkLabel(columna, text=etiqueta, font=tema.fuente(11), text_color=tema.TEXTO_TENUE,
                         anchor="w", height=16).pack(fill="x", pady=(6, 0))
            ctk.CTkLabel(columna, text=str(valor), font=tema.fuente(13), text_color=tema.TEXTO,
                         anchor="w", justify="left", wraplength=230).pack(fill="x")

    def al_tener_datos(datos):
        if not datos:
            return
        sistema_pc = datos["sistema"]
        cabeza.descripcion.configure(text=sistema_pc["_nombre_corto"] + " con " + datos["cpu"]["Modelo"])
        boton_copiar.configure(command=copiar_informe)

        # Discos
        for widget in lista_discos.winfo_children():
            widget.destroy()
        for disco in datos["discos"]:
            bloque = ctk.CTkFrame(lista_discos, fg_color="transparent", height=1)
            bloque.pack(fill="x", pady=(2, 10))
            arriba = ctk.CTkFrame(bloque, fg_color="transparent", height=1)
            arriba.pack(fill="x")
            ctk.CTkLabel(arriba, text=disco["unidad"], font=tema.fuente(14, True),
                         text_color=tema.TEXTO, anchor="w").pack(side="left")
            if disco["tipo"]:
                color = tema.AMBAR if disco["tipo"] == "HDD" else tema.VERDE
                tema.insignia(arriba, disco["tipo"], color).pack(side="left", padx=10)
            ctk.CTkLabel(arriba, text=f"{disco['libre']:.0f} GB libres de {disco['total']:.0f} GB",
                         font=tema.fuente(12), text_color=tema.TEXTO_SUAVE).pack(side="right")
            barra = tema.barra(bloque, tema.color_nivel(disco["porcentaje"]), alto=6)
            barra.pack(fill="x", pady=(6, 0))
            barra.set(disco["porcentaje"] / 100)

        # Especificaciones
        cpu = hardware.visibles(datos["cpu"])
        ram = hardware.visibles(datos["ram"])
        gpu = hardware.visibles(datos["gpus"][0])
        pantalla = datos.get("pantalla") or {}
        if pantalla:
            gpu["Pantalla"] = f"{pantalla['ancho']} x {pantalla['alto']}, {pantalla['hz']} Hz"
        if len(datos["gpus"]) > 1:
            gpu["Otra GPU"] = datos["gpus"][1]["Modelo"]
        columna_specs(0, "Procesador", cpu)
        columna_specs(1, "Memoria", ram)
        columna_specs(2, "Gráficos", gpu)
        columna_specs(3, "Sistema", hardware.visibles(sistema_pc))

    def copiar_informe():
        ventana = app["ventana"]
        ventana.clipboard_clear()
        ventana.clipboard_append(hardware.generar_informe(app["datos_pc"]))
        app["notificar"]("Informe copiado al portapapeles")

    contador = {"segundos": 0}

    def al_actualizar(uso):
        # Solo se redibuja si estás mirando el Panel: así el resto de la app va más fluido
        if app["pagina"] != "panel" or app.get("oculta"):
            return
        cpu = widgets_metrica["cpu"]
        tema.actualizar(cpu["valor"], text=f"{uso['cpu']:.0f} %")
        tema.mover_barra(cpu["barra"], uso["cpu"] / 100)
        if uso.get("cpu_temp") is not None:
            nucleos = app["datos_pc"].get("cpu", {}).get("Núcleos", "") if app["datos_pc"] else ""
            tema.actualizar(cpu["detalle"], text=f"{uso['cpu_temp']} °C, {nucleos}".rstrip(", "))
        elif app["datos_pc"]:
            tema.actualizar(cpu["detalle"], text=app["datos_pc"]["cpu"].get("Núcleos", ""))

        ram = widgets_metrica["ram"]
        tema.actualizar(ram["valor"], text=f"{uso['ram']:.0f} %")
        tema.actualizar(ram["detalle"], text=f"{uso['ram_usada']} de {uso['ram_total']} GB")
        tema.mover_barra(ram["barra"], uso["ram"] / 100)

        if "gpu" in widgets_metrica and uso.get("gpu") is not None:
            gpu = widgets_metrica["gpu"]
            tema.actualizar(gpu["valor"], text=f"{uso['gpu']} %")
            detalle = f"VRAM {uso['vram_usada']} de {uso['vram_total']} GB"
            if uso.get("gpu_temp") is not None:
                detalle = detalle + f", {uso['gpu_temp']} °C"
            tema.actualizar(gpu["detalle"], text=detalle)
            tema.mover_barra(gpu["barra"], uso["gpu"] / 100)

        lista_series = []
        for clave, titulo, color, relleno in series:
            lista_series.append((app["historia"][clave], color, relleno))
        tema.dibujar_grafico(grafico, lista_series)

        contador["segundos"] = contador["segundos"] + 1
        if contador["segundos"] % 4 == 1:
            actualizar_apps()

    def actualizar_apps():
        def trabajo():
            return hardware.procesos_que_mas_consumen(len(filas_apps))

        def listo(top):
            top = top or []
            for indice, (nombre, memoria) in enumerate(filas_apps):
                if indice < len(top):
                    texto_nombre = top[indice]["nombre"]
                    if len(texto_nombre) > 24:
                        texto_nombre = texto_nombre[:22] + "..."
                    tema.actualizar(nombre, text=texto_nombre)
                    megas = top[indice]["ram_mb"]
                    tema.actualizar(memoria, text=f"{megas / 1024:.1f} GB" if megas >= 1024 else f"{megas} MB")
                else:
                    tema.actualizar(nombre, text="")
                    tema.actualizar(memoria, text="")

        app["en_segundo_plano"](trabajo, listo)

    def al_tener_recomendaciones(resultado):
        tema.animar_dial(dial, resultado["puntaje"])
        importantes = resultado["pendientes_importantes"]
        resto = len(resultado["lista"]) - importantes
        if importantes == 0 and resto == 0:
            texto = "Todo en orden. No encontramos nada que mejorar."
        elif importantes:
            texto = f"{importantes} {'mejora importante' if importantes == 1 else 'mejoras importantes'}"
            if resto:
                texto = texto + f" y {resto} {'sugerencia' if resto == 1 else 'sugerencias'} más."
            else:
                texto = texto + "."
        else:
            texto = f"{resto} {'sugerencia' if resto == 1 else 'sugerencias'} para sacarle más provecho."
        resumen_salud.configure(text=texto)

    app["suscribir"]("datos", al_tener_datos)
    app["suscribir"]("datos", revisar_gpu)
    app["suscribir"]("gpu_lista", revisar_gpu)
    app["suscribir"]("uso", al_actualizar)
    app["suscribir"]("recomendaciones", al_tener_recomendaciones)
    if app["datos_pc"]:
        al_tener_datos(app["datos_pc"])
    if app["recomendaciones"]:
        al_tener_recomendaciones(app["recomendaciones"])

    def al_mostrar():
        contador["segundos"] = 0
        if app["uso"]:
            al_actualizar(app["uso"])   # se pone al día apenas vuelves al Panel

    return {"al_mostrar": al_mostrar}
