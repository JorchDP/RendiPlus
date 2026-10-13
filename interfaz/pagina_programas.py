"""
pagina_programas.py  -  Página "Programas y discos": qué hay instalado en cada disco, cuánto ocupa
y un acceso directo al desinstalador oficial de cada programa.
"""

from tkinter import messagebox

import customtkinter as ctk
import psutil

from interfaz import tema
from motores import historial, programas
from motores.sistema import SISTEMA

FILAS_POR_TANDA = 25
COLOR_ORIGEN = {"Steam": tema.ACERO, "Epic Games": tema.TEXTO_SUAVE, "Xbox": tema.VERDE}


def nombre_unidad(unidad):
    """'C:\\' -> 'C:' ; en Mac se deja igual."""
    if SISTEMA == "Windows":
        return unidad.rstrip("\\/").upper()
    return unidad


def construir(marco, app):
    estado = {"programas": [], "unidad": None, "filtro": "todo", "orden": "tamano", "busqueda": "",
              "mostrar": FILAS_POR_TANDA, "medicion": None, "cargando": False, "cargado": False,
              "terminados": [], "esperando": set(), "buscar_tarea": None, "ultimos_cambios": -1}

    contenido = tema.pagina_con_scroll(marco)
    cabeza = tema.encabezado(contenido, "Programas y discos",
                             "Qué hay instalado en cada disco y cuánto ocupa. Desinstala con el desinstalador "
                             "oficial de cada programa.")
    boton_actualizar = tema.boton(cabeza.acciones, "Actualizar lista", lambda: cargar(), "secundario", ancho=150)
    boton_actualizar.pack()
    cuerpo = ctk.CTkFrame(contenido, fg_color="transparent", height=1)
    cuerpo.pack(fill="both", expand=True, padx=32, pady=(0, 28))

    # ------------------------------------------------------------
    #  Tarjetas de cada disco (se pueden elegir para filtrar)
    # ------------------------------------------------------------
    fila_discos = ctk.CTkFrame(cuerpo, fg_color="transparent", height=1)
    fila_discos.pack(fill="x", pady=(0, 18))
    tarjetas_disco = {}

    def leer_discos():
        tipos = (app["datos_pc"] or {}).get("tipo_por_unidad", {})
        discos = []
        for disco in (app["datos_pc"] or {}).get("discos", []):
            unidad = disco["unidad"]
            punto = unidad
            if SISTEMA == "Darwin":
                punto = "/" if unidad == "Macintosh HD" else "/Volumes/" + unidad
            try:
                uso = psutil.disk_usage(punto)
                libre, total = uso.free, uso.total
            except Exception:
                libre, total = disco["libre"] * 1024 ** 3, disco["total"] * 1024 ** 3
            discos.append({"clave": nombre_unidad(unidad), "libre": libre, "total": total,
                           "tipo": disco.get("tipo") or tipos.get(unidad[:1].upper(), "")})
        return discos

    def crear_tarjeta_disco(columna, clave):
        tarjeta = ctk.CTkFrame(fila_discos, fg_color=tema.SUPERFICIE, corner_radius=tema.RADIO,
                               border_width=1, border_color=tema.LINEA, cursor="hand2")
        tarjeta.grid(row=0, column=columna, sticky="nsew", padx=(0 if columna == 0 else 6, 6))
        arriba = ctk.CTkFrame(tarjeta, fg_color="transparent", height=1)
        arriba.pack(fill="x", padx=18, pady=(14, 0))
        titulo = ctk.CTkLabel(arriba, text="", font=tema.fuente(18, True, titulo=True), text_color=tema.TEXTO,
                              anchor="w")
        titulo.pack(side="left")
        insignia = tema.insignia(arriba, "", tema.VERDE)
        barra = tema.barra(tarjeta, tema.VERDE, alto=6)
        barra.pack(fill="x", padx=18, pady=(10, 0))
        libre = ctk.CTkLabel(tarjeta, text="", font=tema.fuente(12), text_color=tema.TEXTO_SUAVE, anchor="w")
        libre.pack(fill="x", padx=18, pady=(6, 0))
        instalado = ctk.CTkLabel(tarjeta, text="", font=tema.fuente(12, True), text_color=tema.TEXTO, anchor="w")
        instalado.pack(fill="x", padx=18, pady=(0, 14))
        elementos = {"tarjeta": tarjeta, "titulo": titulo, "insignia": insignia, "barra": barra,
                     "libre": libre, "instalado": instalado}
        for widget in (tarjeta, arriba, titulo, libre, instalado, barra):
            widget.bind("<Button-1>", lambda evento, c=clave: elegir_unidad(c))
        return elementos

    def dibujar_discos():
        discos = leer_discos()
        claves = [None] + [d["clave"] for d in discos]
        if list(tarjetas_disco) != claves:
            for elementos in tarjetas_disco.values():
                elementos["tarjeta"].destroy()
            tarjetas_disco.clear()
            for columna in range(6):
                fila_discos.grid_columnconfigure(columna, weight=0, uniform="")
            for columna, clave in enumerate(claves[:6]):
                fila_discos.grid_columnconfigure(columna, weight=1, uniform="discos")
                tarjetas_disco[clave] = crear_tarjeta_disco(columna, clave)

        lista = estado["programas"]
        total_todo = sum(p["bytes"] or 0 for p in lista)
        todos = tarjetas_disco[None]
        tema.actualizar(todos["titulo"], text="Todos los discos")
        tema.actualizar(todos["libre"], text=f"{len(lista)} programas y juegos" if lista else "Revisando...")
        tema.actualizar(todos["instalado"], text=tema.formato_gb(total_todo) + " en total" if lista else "")
        todos["barra"].pack_forget()

        for disco in discos:
            elementos = tarjetas_disco.get(disco["clave"])
            if not elementos:
                continue
            porcentaje = 1 - disco["libre"] / disco["total"] if disco["total"] else 0
            color = tema.color_nivel(porcentaje * 100)
            tema.actualizar(elementos["titulo"], text=disco["clave"])
            if disco["tipo"]:
                color_tipo = tema.AMBAR if disco["tipo"] == "HDD" else tema.VERDE
                elementos["insignia"].configure(text="  " + disco["tipo"] + "  ", text_color=color_tipo,
                                                fg_color=tema.FONDO_DE[color_tipo])
                elementos["insignia"].pack(side="left", padx=10)
            elementos["barra"].configure(progress_color=color)
            tema.mover_barra(elementos["barra"], porcentaje)
            tema.actualizar(elementos["libre"], text=f"{tema.formato_gb(disco['libre'])} libres de "
                                                     f"{tema.formato_gb(disco['total'])}")
            del_disco = [p for p in lista if p["unidad"] == disco["clave"]]
            ocupado = sum(p["bytes"] or 0 for p in del_disco)
            tema.actualizar(elementos["instalado"],
                            text=f"{len(del_disco)} instalados · {tema.formato_gb(ocupado)}" if del_disco
                            else ("Sin programas" if lista else ""))

        for clave, elementos in tarjetas_disco.items():
            elegida = clave == estado["unidad"]
            elementos["tarjeta"].configure(border_width=2 if elegida else 1,
                                           border_color=tema.ORO if elegida else tema.LINEA)

    def elegir_unidad(clave):
        estado["unidad"] = clave
        estado["mostrar"] = FILAS_POR_TANDA
        dibujar_discos()
        dibujar_lista()

    # ------------------------------------------------------------
    #  Lista: filtros
    # ------------------------------------------------------------
    tabla = tema.tarjeta(cuerpo)
    tabla.pack(fill="x")
    barra_filtros = ctk.CTkFrame(tabla, fg_color="transparent", height=1)
    barra_filtros.pack(fill="x", padx=20, pady=(14, 6))

    botones_filtro = {}
    for clave, texto in [("todo", "Todo"), ("programas", "Programas"), ("juegos", "Juegos")]:
        bloque = ctk.CTkFrame(barra_filtros, fg_color="transparent", height=1)
        bloque.pack(side="left", padx=(0, 18))
        boton = ctk.CTkButton(bloque, text=texto, fg_color="transparent", hover_color=tema.SUPERFICIE,
                              text_color=tema.TEXTO_SUAVE, font=tema.fuente(14, True), height=28,
                              width=tema.fuente(14, True).measure(texto) + 16,
                              command=lambda c=clave: elegir_filtro(c))
        boton.pack()
        linea = ctk.CTkFrame(bloque, height=2, width=1, fg_color=tema.SUPERFICIE, corner_radius=1)
        linea.pack(fill="x", padx=4)
        botones_filtro[clave] = (boton, linea)

    buscador = ctk.CTkEntry(barra_filtros, placeholder_text="Buscar programa o juego", width=230, height=32,
                            corner_radius=8, fg_color=tema.SUPERFICIE_ALTA, border_color=tema.LINEA,
                            text_color=tema.TEXTO, placeholder_text_color=tema.TEXTO_TENUE,
                            font=tema.fuente(13))
    buscador.pack(side="right")
    boton_orden = tema.boton(barra_filtros, "Más pesados primero", lambda: cambiar_orden(), "fantasma", alto=32)
    boton_orden.pack(side="right", padx=8)

    # Progreso de la medición
    zona_progreso = ctk.CTkFrame(tabla, fg_color="transparent", height=1)
    texto_progreso = ctk.CTkLabel(zona_progreso, text="", font=tema.fuente(12), text_color=tema.TEXTO_SUAVE,
                                  anchor="w")
    texto_progreso.pack(side="left")
    barra_progreso = tema.barra(zona_progreso, tema.ORO, alto=4)
    barra_progreso.pack(side="left", fill="x", expand=True, padx=(14, 0))

    resumen = ctk.CTkLabel(tabla, text="", font=tema.fuente(12), text_color=tema.TEXTO_TENUE, anchor="w")
    resumen.pack(fill="x", padx=20, pady=(4, 6))
    tema.separador(tabla).pack(fill="x", padx=20)

    contenedor = ctk.CTkFrame(tabla, fg_color="transparent", height=1)
    contenedor.pack(fill="x", padx=20)
    vacio = ctk.CTkLabel(tabla, text="Revisando lo que hay instalado...", font=tema.fuente(13),
                         text_color=tema.TEXTO_SUAVE, anchor="w")
    vacio.pack(fill="x", padx=20, pady=16)
    boton_mas = tema.boton(tabla, "Mostrar más", lambda: mostrar_mas(), "secundario", alto=32)
    pie = ctk.CTkFrame(tabla, fg_color="transparent", height=10)
    pie.pack(fill="x")

    def elegir_filtro(clave):
        estado["filtro"] = clave
        estado["mostrar"] = FILAS_POR_TANDA
        for clave_boton, (boton, linea) in botones_filtro.items():
            activo = clave_boton == clave
            boton.configure(text_color=tema.TEXTO if activo else tema.TEXTO_SUAVE)
            linea.configure(fg_color=tema.ORO if activo else tema.SUPERFICIE)
        dibujar_lista()

    def cambiar_orden():
        estado["orden"] = "nombre" if estado["orden"] == "tamano" else "tamano"
        boton_orden.configure(text="Por nombre (A-Z)" if estado["orden"] == "nombre" else "Más pesados primero")
        dibujar_lista()

    def al_escribir(evento=None):
        if estado["buscar_tarea"]:
            app["ventana"].after_cancel(estado["buscar_tarea"])

        def aplicar():
            estado["buscar_tarea"] = None
            estado["busqueda"] = buscador.get().strip().lower()
            estado["mostrar"] = FILAS_POR_TANDA
            dibujar_lista()
        estado["buscar_tarea"] = app["ventana"].after(250, aplicar)

    buscador.bind("<KeyRelease>", al_escribir)

    def mostrar_mas():
        estado["mostrar"] = estado["mostrar"] + FILAS_POR_TANDA
        dibujar_lista()

    # ------------------------------------------------------------
    #  Lista: filas reutilizables (se crean una vez y solo se cambia su contenido)
    # ------------------------------------------------------------
    filas = []

    def crear_fila():
        fila = ctk.CTkFrame(contenedor, fg_color="transparent", height=1)
        if filas:
            tema.separador(fila).pack(fill="x")
        interior = ctk.CTkFrame(fila, fg_color="transparent", height=1)
        interior.pack(fill="x", pady=9)
        desinstalar = tema.boton(interior, "Desinstalar", None, "peligro", ancho=104, alto=30)
        desinstalar.pack(side="right", padx=(10, 0))
        carpeta = tema.boton(interior, "Carpeta", None, "fantasma", ancho=74, alto=30)
        carpeta.pack(side="right", padx=(6, 0))
        zona_tamano = ctk.CTkFrame(interior, fg_color="transparent", width=130, height=1)
        zona_tamano.pack(side="right", padx=(12, 0))
        tamano = ctk.CTkLabel(zona_tamano, text="", font=tema.fuente(14, True, titulo=True),
                              text_color=tema.TEXTO, anchor="e", width=130, height=20)
        tamano.pack(fill="x")
        proporcion = tema.barra(zona_tamano, tema.ORO, alto=4)
        proporcion.configure(width=130)
        proporcion.pack(fill="x", pady=(4, 0))
        textos = ctk.CTkFrame(interior, fg_color="transparent", height=1)
        textos.pack(side="left", fill="x", expand=True)
        arriba = ctk.CTkFrame(textos, fg_color="transparent", height=1)
        arriba.pack(fill="x")
        nombre = ctk.CTkLabel(arriba, text="", font=tema.fuente(14, True), text_color=tema.TEXTO, anchor="w")
        nombre.pack(side="left")
        origen = tema.insignia(arriba, "", tema.ACERO)
        necesario = tema.insignia(arriba, "Lo usan otros programas", tema.AMBAR)
        detalle = ctk.CTkLabel(textos, text="", font=tema.fuente(11), text_color=tema.TEXTO_TENUE, anchor="w")
        detalle.pack(fill="x")
        filas.append({"fila": fila, "nombre": nombre, "origen": origen, "necesario": necesario,
                      "detalle": detalle, "tamano": tamano, "proporcion": proporcion, "carpeta": carpeta,
                      "desinstalar": desinstalar, "id": None, "visible": False,
                      "con_origen": False, "con_necesario": False, "con_carpeta": True})

    def recortar(texto, largo):
        return texto if len(texto) <= largo else texto[:largo - 3] + "..."

    def filtrados():
        lista = estado["programas"]
        if estado["unidad"] is not None:
            lista = [p for p in lista if p["unidad"] == estado["unidad"]]
        if estado["filtro"] == "juegos":
            lista = [p for p in lista if p["juego"]]
        elif estado["filtro"] == "programas":
            lista = [p for p in lista if not p["juego"]]
        if estado["busqueda"]:
            buscado = estado["busqueda"]
            lista = [p for p in lista if buscado in p["nombre"].lower() or buscado in p["editor"].lower()]
        if estado["orden"] == "nombre":
            return sorted(lista, key=lambda p: p["nombre"].lower())
        return sorted(lista, key=lambda p: (-(p["bytes"] or 0), p["nombre"].lower()))

    def llenar_fila(fila, programa, mayor):
        nuevo = fila["id"] != programa["id"]
        fila["id"] = programa["id"]
        fila["programa"] = programa
        tema.actualizar(fila["nombre"], text=recortar(programa["nombre"], 58))

        mostrar_origen = programa["origen"] != "Programa"
        if mostrar_origen:
            color = COLOR_ORIGEN.get(programa["origen"], tema.ACERO)
            tema.actualizar(fila["origen"], text="  " + programa["origen"] + "  ", text_color=color,
                            fg_color=tema.FONDO_DE.get(color, tema.SUPERFICIE_ALTA))
        if mostrar_origen != fila["con_origen"] or nuevo:
            fila["origen"].pack_forget()
            fila["necesario"].pack_forget()
            if mostrar_origen:
                fila["origen"].pack(side="left", padx=(10, 0))
            fila["con_origen"] = mostrar_origen
            fila["con_necesario"] = False
        if programa["necesario"] and not fila["con_necesario"]:
            fila["necesario"].pack(side="left", padx=(8, 0))
            fila["con_necesario"] = True
        elif not programa["necesario"] and fila["con_necesario"]:
            fila["necesario"].pack_forget()
            fila["con_necesario"] = False

        partes = []
        if programa["editor"]:
            partes.append(programa["editor"])
        if programa["version"]:
            partes.append("v" + programa["version"])
        if programa.get("comparte_con"):
            partes.append("Comparte carpeta con " + programa["comparte_con"])
        else:
            partes.append(programa["carpeta"] or "Ubicación no registrada")
        tema.actualizar(fila["detalle"], text=recortar("  ·  ".join(partes), 110))

        if programa["bytes"]:
            texto = tema.formato_gb(programa["bytes"])
            if programa["estimado"]:
                texto = "≈ " + texto
            tema.actualizar(fila["tamano"], text=texto, text_color=tema.TEXTO)
            tema.mover_barra(fila["proporcion"], max(0.02, programa["bytes"] / mayor) if mayor else 0)
        elif programa.get("comparte_con"):
            tema.actualizar(fila["tamano"], text="Ya contado", text_color=tema.TEXTO_TENUE)
            tema.mover_barra(fila["proporcion"], 0)
        else:
            tema.actualizar(fila["tamano"], text="—", text_color=tema.TEXTO_TENUE)
            tema.mover_barra(fila["proporcion"], 0)

        if nuevo:
            fila["carpeta"].configure(state="normal" if programa["carpeta"] else "disabled",
                                      command=lambda p=programa: programas.abrir_carpeta(p))
            if programa["id"] in estado["esperando"]:
                fila["desinstalar"].configure(state="disabled", text="Esperando...", command=None)
            elif programa.get("desinstalar"):
                fila["desinstalar"].configure(state="normal", text="Desinstalar",
                                              command=lambda p=programa: desinstalar(p))
            else:
                fila["desinstalar"].configure(state="disabled", text="Desinstalar", command=None)

    def dibujar_lista():
        if not estado["cargado"]:
            return
        lista = filtrados()
        visibles = lista[:estado["mostrar"]]
        while len(filas) < len(visibles):
            crear_fila()
        mayor = max((p["bytes"] or 0 for p in lista), default=0)
        for indice, fila in enumerate(filas):
            if indice < len(visibles):
                llenar_fila(fila, visibles[indice], mayor)
                if not fila["visible"]:
                    fila["fila"].pack(fill="x")
                    fila["visible"] = True
            elif fila["visible"]:
                fila["fila"].pack_forget()
                fila["visible"] = False
                fila["id"] = None

        total = sum(p["bytes"] or 0 for p in lista)
        donde = "en todos los discos" if estado["unidad"] is None else "en " + estado["unidad"]
        if lista:
            texto = f"{len(lista)} instalados {donde} · {tema.formato_gb(total)}"
            if any(p["estimado"] for p in lista):
                texto = texto + "  ·  ≈ tamaño informado por el programa (aproximado)"
            tema.actualizar(resumen, text=texto)
            vacio.pack_forget()
        else:
            tema.actualizar(resumen, text="")
            vacio.configure(text="No hay nada que coincida con el filtro." if estado["programas"]
                            else "No encontramos programas instalados.")
            vacio.pack(fill="x", padx=20, pady=16, before=pie)
        if len(lista) > len(visibles):
            boton_mas.configure(text=f"Mostrar más ({len(lista) - len(visibles)} restantes)")
            boton_mas.pack(pady=(10, 4), before=pie)
        else:
            boton_mas.pack_forget()

    # ------------------------------------------------------------
    #  Cargar y medir
    # ------------------------------------------------------------
    def cargar():
        if estado["cargando"]:
            return
        estado["cargando"] = True
        boton_actualizar.configure(state="disabled", text="Revisando...")
        if estado["medicion"]:
            estado["medicion"].cancelar()

        def listo(lista):
            estado["cargando"] = False
            estado["cargado"] = True
            boton_actualizar.configure(state="normal", text="Actualizar lista")
            estado["programas"] = [p for p in (lista or []) if p["id"] not in estado["esperando"]
                                   or programas.sigue_instalado(p)]
            for fila in filas:
                fila["id"] = None
            dibujar_discos()
            dibujar_lista()
            estado["medicion"] = programas.Medicion(estado["programas"]).iniciar()
            estado["ultimos_cambios"] = -1
            seguir_medicion()

        app["en_segundo_plano"](programas.listar, listo)

    def seguir_medicion():
        medicion = estado["medicion"]
        if not medicion or app["pagina"] != "programas":
            return
        if medicion.listo:
            zona_progreso.pack_forget()
            if medicion.cambios != estado["ultimos_cambios"]:
                estado["ultimos_cambios"] = medicion.cambios
                dibujar_discos()
                dibujar_lista()        # orden final, con los tamaños reales
            return
        if medicion.total:
            zona_progreso.pack(fill="x", padx=20, pady=(2, 0), before=resumen)
            tema.actualizar(texto_progreso, text=f"Midiendo el tamaño real de cada carpeta... "
                                                 f"{medicion.avance} de {medicion.total}")
            tema.mover_barra(barra_progreso, medicion.avance / medicion.total)
        # Mientras mide se actualizan los números, pero el orden se mantiene (para que la lista no salte)
        if medicion.cambios != estado["ultimos_cambios"]:
            estado["ultimos_cambios"] = medicion.cambios
            mayor = max((p["bytes"] or 0 for p in estado["programas"]), default=0)
            for fila in filas:
                if fila["visible"] and fila.get("programa"):
                    llenar_fila(fila, fila["programa"], mayor)
        app["ventana"].after(700, seguir_medicion)

    # ------------------------------------------------------------
    #  Desinstalar
    # ------------------------------------------------------------
    def desinstalar(programa):
        tamano = f"\nOcupa {tema.formato_gb(programa['bytes'])}." if programa["bytes"] else ""
        if programa["origen"] == "Steam":
            texto = f"¿Desinstalar {programa['nombre']}?{tamano}\n\nSteam te pedirá que lo confirmes."
        elif programa["origen"] == "Epic Games":
            texto = (f"¿Desinstalar {programa['nombre']}?{tamano}\n\nEpic Games no permite desinstalar desde "
                     "otras apps: se abrirá Epic y lo desinstalas desde tu Biblioteca (botón ··· > Desinstalar).")
        elif programa["origen"] == "Xbox":
            texto = (f"¿Desinstalar {programa['nombre']}?{tamano}\n\nSe abrirá Aplicaciones instaladas de Windows: "
                     "búscalo ahí y elige Desinstalar.")
        elif SISTEMA == "Darwin":
            texto = f"¿Mover {programa['nombre']} a la Papelera?{tamano}\n\nPodrás sacarlo de la Papelera si te arrepientes."
        else:
            texto = (f"¿Desinstalar {programa['nombre']}?{tamano}\n\nSe abrirá el desinstalador oficial del "
                     "programa: sigue sus pasos. RendiPlus no borra archivos por su cuenta.")
        if programa["necesario"]:
            texto = texto + ("\n\nOjo: otros programas o juegos pueden necesitarlo para funcionar (por ejemplo, "
                             "Visual C++, .NET o un controlador). Desinstálalo solo si estás seguro.")
        if not messagebox.askyesno("Desinstalar", texto, icon="warning" if programa["necesario"] else "question"):
            return

        def listo(respuesta):
            ok, mensaje = respuesta or (False, "No se pudo abrir el desinstalador")
            app["notificar"](mensaje, tema.ACERO if ok else tema.CORAL)
            if not ok:
                return
            estado["esperando"].add(programa["id"])
            for fila in filas:
                if fila["id"] == programa["id"]:
                    fila["desinstalar"].configure(state="disabled", text="Esperando...", command=None)
            programas.esperar_desinstalacion(programa, lambda p: estado["terminados"].append(p))
            revisar_terminados()

        app["en_segundo_plano"](lambda: programas.desinstalar(programa), listo)

    def revisar_terminados():
        """Los avisos de 'ya se desinstaló' llegan desde otro hilo; aquí se atienden con calma."""
        while estado["terminados"]:
            programa = estado["terminados"].pop(0)
            estado["esperando"].discard(programa["id"])
            estado["programas"] = [p for p in estado["programas"] if p["id"] != programa["id"]]
            liberado = f" y liberaste {tema.formato_gb(programa['bytes'])}" if programa["bytes"] else ""
            historial.registrar("Programas", f"Se desinstaló {programa['nombre']}"
                                + (f" ({tema.formato_gb(programa['bytes'])})" if programa["bytes"] else ""))
            app["notificar"](f"Se desinstaló {programa['nombre']}{liberado}")
            for fila in filas:
                fila["id"] = None
            dibujar_discos()
            dibujar_lista()
        if estado["esperando"]:
            app["ventana"].after(1500, revisar_terminados)

    elegir_filtro("todo")

    def al_mostrar():
        if not estado["cargado"] and app["datos_pc"]:
            cargar()
        elif estado["cargado"]:
            dibujar_discos()          # el espacio libre pudo cambiar (por ejemplo, después de limpiar)
            seguir_medicion()

    def al_tener_datos(datos):
        if app["pagina"] == "programas" and not estado["cargado"]:
            cargar()

    app["suscribir"]("datos", al_tener_datos)
    return {"al_mostrar": al_mostrar}
