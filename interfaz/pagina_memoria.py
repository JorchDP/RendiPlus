"""
pagina_memoria.py  -  Página "Memoria RAM": liberar memoria, liberarla sola cuando se llena,
ver qué la está usando y mantener cerradas las apps que se abren solas.
"""

import time
from tkinter import messagebox

import customtkinter as ctk

from interfaz import tema
from motores import historial, inicio, memoria, sistema
from motores.sistema import SISTEMA

FILAS = 14
LIMITES = [75, 80, 85, 90]


def construir(marco, app):
    estado = {"liberando": False, "ultima": None, "filas": [], "refrescando": False}

    contenido = tema.pagina_con_scroll(marco)
    cabeza = tema.encabezado(contenido, "Memoria RAM",
                             "Libera la RAM que los programas no están usando y mantén cerradas las apps "
                             "que se abren solas.")
    boton_liberar = tema.boton(cabeza.acciones, "Liberar memoria ahora", lambda: liberar_ahora(), "primario",
                               ancho=190, alto=40)
    boton_liberar.pack()
    cuerpo = ctk.CTkFrame(contenido, fg_color="transparent", height=1)
    cuerpo.pack(fill="both", expand=True, padx=32, pady=(0, 28))

    # ------------------------------------------------------------
    #  Estado de la memoria
    # ------------------------------------------------------------
    resumen = tema.tarjeta(cuerpo)
    resumen.pack(fill="x", pady=(0, 18))
    fila_resumen = ctk.CTkFrame(resumen, fg_color="transparent", height=1)
    fila_resumen.pack(fill="x", padx=24, pady=(20, 0))

    izquierda = ctk.CTkFrame(fila_resumen, fg_color="transparent", height=1)
    izquierda.pack(side="left")
    texto_porcentaje = ctk.CTkLabel(izquierda, text="—", font=tema.fuente(52, True, titulo=True),
                                    text_color=tema.TEXTO, anchor="w", width=170)
    texto_porcentaje.pack(anchor="w")
    texto_uso = ctk.CTkLabel(izquierda, text="", font=tema.fuente(13), text_color=tema.TEXTO_SUAVE,
                             anchor="w")
    texto_uso.pack(anchor="w")

    datos_derecha = ctk.CTkFrame(fila_resumen, fg_color="transparent", height=1)
    datos_derecha.pack(side="right", anchor="n", pady=(6, 0))
    cifras = {}
    for clave, titulo, ayuda in [
        ("disponible", "Disponible", "Lo que pueden usar las apps nuevas"),
        ("cache", "En caché", "Archivos recientes guardados por Windows; se suelta sola si hace falta"),
        ("comprometida", "Comprometida", "RAM + archivo de paginación que las apps tienen reservado"),
    ]:
        bloque = ctk.CTkFrame(datos_derecha, fg_color="transparent", height=1, width=150)
        bloque.pack(side="left", padx=(28, 0), anchor="n")
        ctk.CTkLabel(bloque, text=titulo.upper(), font=tema.fuente(11, True), text_color=tema.TEXTO_TENUE,
                     anchor="w").pack(anchor="w")
        valor = ctk.CTkLabel(bloque, text="—", font=tema.fuente(20, True, titulo=True), text_color=tema.TEXTO,
                             anchor="w", width=130)
        valor.pack(anchor="w")
        ctk.CTkLabel(bloque, text=ayuda, font=tema.fuente(11), text_color=tema.TEXTO_TENUE, anchor="w",
                     justify="left", wraplength=150).pack(anchor="w")
        cifras[clave] = (bloque, valor)

    barra_ram = tema.barra(resumen, tema.VERDE, alto=14)
    barra_ram.pack(fill="x", padx=24, pady=(18, 0))
    texto_ultima = ctk.CTkLabel(resumen, text="", font=tema.fuente(12, True), text_color=tema.VERDE, anchor="w")
    nota = ("Liberar no cierra nada: cada programa devuelve la memoria que no está usando y sigue abierto. "
            "Si después la necesita, la vuelve a tomar. Sirve sobre todo justo antes de abrir un juego. "
            "El programa que tienes en primer plano (por ejemplo, tu juego) nunca se toca.")
    if SISTEMA == "Darwin":
        nota = ("En Mac, liberar vacía la memoria en caché con el comando purge (te pedirá tu contraseña). "
                "macOS administra muy bien la memoria por su cuenta, así que úsalo solo si notas tirones.")
    texto_nota = ctk.CTkLabel(resumen, text=nota, font=tema.fuente(12), text_color=tema.TEXTO_TENUE, anchor="w",
                              justify="left", wraplength=880)
    texto_nota.pack(fill="x", padx=24, pady=(12, 20))

    def mostrar_estado():
        datos = memoria.estado_memoria()
        porcentaje = datos["porcentaje"]
        color = tema.color_nivel(porcentaje)
        tema.actualizar(texto_porcentaje, text=f"{porcentaje:.0f} %", text_color=color)
        tema.actualizar(texto_uso, text=f"{tema.formato_gb(datos['en_uso'])} en uso de "
                                        f"{tema.formato_gb(datos['total'])}")
        tema.actualizar(barra_ram, progress_color=color)
        tema.mover_barra(barra_ram, porcentaje / 100)
        valores = {"disponible": datos["disponible"], "cache": datos.get("cache"),
                   "comprometida": datos.get("comprometida")}
        for clave, (bloque, etiqueta) in cifras.items():
            valor = valores.get(clave)
            if valor is None:
                bloque.pack_forget()
                continue
            texto = tema.formato_gb(valor)
            if clave == "comprometida" and datos.get("limite_comprometida"):
                texto = texto + f" / {tema.formato_gb(datos['limite_comprometida'])}"
            tema.actualizar(etiqueta, text=texto)
        if estado["ultima"]:
            gb, momento = estado["ultima"]
            minutos = int((time.time() - momento) // 60)
            hace = "recién" if minutos < 1 else (f"hace {minutos} min" if minutos < 60
                                                 else f"hace {minutos // 60} h")
            tema.actualizar(texto_ultima, text=f"Última liberación: {gb} ({hace})")
            if not texto_ultima.winfo_ismapped():
                texto_ultima.pack(fill="x", padx=24, pady=(12, 0), before=texto_nota)

    # ------------------------------------------------------------
    #  Liberar ahora
    # ------------------------------------------------------------
    def liberar_ahora():
        if estado["liberando"]:
            return
        estado["liberando"] = True
        tema.activar_boton(boton_liberar, False, "Liberando...")

        def listo(resultado):
            estado["liberando"] = False
            tema.activar_boton(boton_liberar, True, "Liberar memoria ahora")
            if not resultado:
                app["notificar"]("No se pudo liberar memoria", tema.CORAL)
                return
            liberado = tema.formato_gb(resultado["liberado"])
            estado["ultima"] = (liberado, time.time())
            partes = [f"Liberaste {liberado} de RAM"]
            if resultado["cerradas"]:
                partes.append("y cerré " + ", ".join(memoria.nombre_amigable(n) for n in resultado["cerradas"]))
            historial.registrar("Memoria", " ".join(partes))
            app["notificar"](" ".join(partes))
            if SISTEMA == "Windows" and not sistema.es_admin() and resultado["liberado"] < 300 * 1024 ** 2:
                app["notificar"]("Abre RendiPlus como administrador para liberar también la memoria de "
                                 "los servicios de Windows", tema.ACERO)
            mostrar_estado()
            refrescar_apps()

        app["en_segundo_plano"](lambda: memoria.liberar(cerrar_lista=bool(sistema.leer_config("ram_vigilar", False))),
                                listo)

    # ------------------------------------------------------------
    #  Automático + apps cerradas
    # ------------------------------------------------------------
    opciones = ctk.CTkFrame(cuerpo, fg_color="transparent", height=1)
    opciones.pack(fill="x", pady=(0, 18))
    opciones.grid_columnconfigure((0, 1), weight=1, uniform="opciones")

    auto = tema.tarjeta(opciones, "Liberar automáticamente")
    auto.grid(row=0, column=0, sticky="nsew", padx=(0, 9))
    interruptor_auto = tema.interruptor(auto.cabeza)
    interruptor_auto.pack(side="right")
    ctk.CTkLabel(auto, text="Cuando la RAM pase del límite, RendiPlus la libera solo (como máximo una vez cada "
                            "5 minutos). Funciona también con la ventana cerrada, si RendiPlus sigue en la "
                            "bandeja junto al reloj.",
                 font=tema.fuente(12), text_color=tema.TEXTO_SUAVE, anchor="w", justify="left",
                 wraplength=380).pack(fill="x", padx=20)
    fila_limites = ctk.CTkFrame(auto, fg_color="transparent", height=1)
    fila_limites.pack(fill="x", padx=20, pady=(14, 20))
    ctk.CTkLabel(fila_limites, text="Límite", font=tema.fuente(13, True), text_color=tema.TEXTO).pack(
        side="left", padx=(0, 12))
    botones_limite = {}
    for limite in LIMITES:
        botones_limite[limite] = tema.boton(fila_limites, f"{limite} %", lambda l=limite: elegir_limite(l),
                                            "secundario", ancho=58, alto=30)
        botones_limite[limite].pack(side="left", padx=(0, 6))

    def pintar_limites():
        actual = int(sistema.leer_config("ram_umbral", 85))
        for limite, boton in botones_limite.items():
            elegido = limite == actual
            boton.configure(fg_color=tema.ORO if elegido else tema.SUPERFICIE_ALTA,
                            hover_color=tema.ORO_CLARO if elegido else tema.LINEA,
                            text_color=tema.TEXTO_SOBRE_ORO if elegido else tema.TEXTO,
                            border_color=tema.ORO if elegido else tema.LINEA)

    def elegir_limite(limite):
        sistema.guardar_config("ram_umbral", limite)
        pintar_limites()

    def cambiar_auto():
        activo = bool(interruptor_auto.get())
        sistema.guardar_config("ram_auto", activo)
        if activo:
            limite = int(sistema.leer_config("ram_umbral", 85))
            app["notificar"](f"RendiPlus liberará la RAM cuando pase del {limite} %")
        else:
            app["notificar"]("Liberación automática desactivada", tema.ACERO)

    if sistema.leer_config("ram_auto", False):
        interruptor_auto.select()
    interruptor_auto.configure(command=cambiar_auto)
    pintar_limites()

    cerradas = tema.tarjeta(opciones, "Mantener cerradas")
    cerradas.grid(row=0, column=1, sticky="nsew", padx=(9, 0))
    interruptor_vigilar = tema.interruptor(cerradas.cabeza)
    interruptor_vigilar.pack(side="right")
    ctk.CTkLabel(cerradas, text="Las apps de esta lista se cierran solas cada vez que se abren mientras esto "
                                "esté activo. Agrégalas desde la lista de abajo con \"Mantener cerrada\".",
                 font=tema.fuente(12), text_color=tema.TEXTO_SUAVE, anchor="w", justify="left",
                 wraplength=380).pack(fill="x", padx=20)
    lista_cerradas = ctk.CTkFrame(cerradas, fg_color="transparent", height=1)
    lista_cerradas.pack(fill="x", padx=20, pady=(10, 16))

    def dibujar_cerradas():
        for widget in lista_cerradas.winfo_children():
            widget.destroy()
        vigiladas = memoria.leer_vigiladas()
        if not vigiladas:
            ctk.CTkLabel(lista_cerradas, text="Todavía no hay apps en la lista.", font=tema.fuente(12),
                         text_color=tema.TEXTO_TENUE, anchor="w").pack(fill="x", pady=4)
            return
        for nombre in vigiladas:
            fila = ctk.CTkFrame(lista_cerradas, fg_color=tema.SUPERFICIE_ALTA, corner_radius=8, height=1)
            fila.pack(fill="x", pady=3)
            ctk.CTkLabel(fila, text=memoria.nombre_amigable(nombre), font=tema.fuente(13, True),
                         text_color=tema.TEXTO, anchor="w").pack(side="left", padx=(12, 6), pady=6)
            ctk.CTkLabel(fila, text=nombre, font=tema.fuente(11), text_color=tema.TEXTO_TENUE,
                         anchor="w").pack(side="left")
            tema.boton(fila, "Quitar", lambda n=nombre: quitar_de_lista(n), "fantasma", ancho=64,
                       alto=26).pack(side="right", padx=6)

    def cambiar_vigilar():
        activo = bool(interruptor_vigilar.get())
        sistema.guardar_config("ram_vigilar", activo)
        if activo and not memoria.leer_vigiladas():
            app["notificar"]("Activado. Agrega apps desde la lista de abajo", tema.ACERO)
        elif activo:
            app["notificar"]("RendiPlus mantendrá cerradas las apps de tu lista")
        else:
            app["notificar"]("Ya no se cierran solas las apps de tu lista", tema.ACERO)

    if sistema.leer_config("ram_vigilar", False):
        interruptor_vigilar.select()
    interruptor_vigilar.configure(command=cambiar_vigilar)

    def agregar_a_lista(grupo):
        nombre = grupo["nombre"]
        titulo = grupo["titulo"]
        if not messagebox.askyesno(
                "Mantener cerrada",
                f"¿Agregar {titulo} a la lista de apps cerradas?\n\nMientras \"Mantener cerradas\" esté activo, "
                f"RendiPlus la cerrará cada vez que se abra (incluso si la abres tú). Puedes quitarla de la "
                f"lista cuando quieras.\n\nSi tienes algo sin guardar en {titulo}, guárdalo antes."):
            return
        if not memoria.agregar_vigilada(nombre):
            app["notificar"](f"{titulo} es parte de Windows y no se puede cerrar", tema.CORAL)
            return
        if not interruptor_vigilar.get():
            interruptor_vigilar.select()
            sistema.guardar_config("ram_vigilar", True)
        dibujar_cerradas()

        def cerrar_y_revisar_inicio():
            cerrados, _ = inicio.cerrar_proceso(nombre)
            return cerrados, memoria.inicio_de(nombre)

        def listo(resultado):
            cerrados, entrada_inicio = resultado or (0, None)
            historial.registrar("Memoria", f"{titulo} agregada a las apps que se mantienen cerradas")
            app["notificar"](f"{titulo} se mantendrá cerrada" + (" (la cerré ahora)" if cerrados else ""))
            refrescar_apps()
            # Si además se abre sola al prender el PC, conviene quitarla del inicio
            if entrada_inicio and messagebox.askyesno(
                    "También al prender el PC",
                    f"{titulo} también se abre sola cada vez que prendes el PC.\n\n"
                    "¿Quitarla del inicio? Así ni siquiera se abre (puedes volver a activarla desde "
                    "Inicio y procesos)."):
                quitar_del_inicio(entrada_inicio, titulo)

        app["en_segundo_plano"](cerrar_y_revisar_inicio, listo)

    def quitar_del_inicio(programa, titulo):
        def listo(funciono):
            if funciono:
                historial.registrar("Inicio", f"Se desactivó \"{programa['nombre']}\" al iniciar",
                                    [{"tipo": "inicio", "programa": programa, "activo": True}])
                app["notificar"](f"{titulo} ya no se abrirá al prender el PC")
            else:
                app["notificar"](f"No se pudo quitar {titulo} del inicio", tema.CORAL)
        app["en_segundo_plano"](lambda: inicio.cambiar_estado(programa, False), listo)

    def quitar_de_lista(nombre):
        memoria.quitar_vigilada(nombre)
        dibujar_cerradas()
        app["notificar"](f"{memoria.nombre_amigable(nombre)} ya no se cerrará sola", tema.ACERO)
        refrescar_apps()

    dibujar_cerradas()

    # ------------------------------------------------------------
    #  Qué está usando la RAM
    # ------------------------------------------------------------
    tabla = tema.tarjeta(cuerpo, "Qué está usando tu RAM",
                         "Agrupado por app: Chrome, por ejemplo, abre un proceso por pestaña.")
    tabla.pack(fill="x")
    contenedor = ctk.CTkFrame(tabla, fg_color="transparent", height=1)
    contenedor.pack(fill="x", padx=20, pady=(0, 14))

    def crear_fila():
        fila = ctk.CTkFrame(contenedor, fg_color="transparent", height=1)
        if estado["filas"]:
            tema.separador(fila).pack(fill="x")
        interior = ctk.CTkFrame(fila, fg_color="transparent", height=1)
        interior.pack(fill="x", pady=8)
        mantener = tema.boton(interior, "Mantener cerrada", None, "secundario", ancho=140, alto=30)
        mantener.pack(side="right", padx=(8, 0))
        cerrar = tema.boton(interior, "Cerrar", None, "peligro", ancho=74, alto=30)
        cerrar.pack(side="right", padx=(8, 0))
        zona_ram = ctk.CTkFrame(interior, fg_color="transparent", width=130, height=1)
        zona_ram.pack(side="right", padx=(12, 0))
        ram = ctk.CTkLabel(zona_ram, text="", font=tema.fuente(14, True, titulo=True), text_color=tema.TEXTO,
                           anchor="e", width=130, height=20)
        ram.pack(fill="x")
        proporcion = tema.barra(zona_ram, tema.ORO, alto=4)
        proporcion.configure(width=130)
        proporcion.pack(fill="x", pady=(4, 0))
        textos = ctk.CTkFrame(interior, fg_color="transparent", height=1)
        textos.pack(side="left", fill="x", expand=True)
        arriba = ctk.CTkFrame(textos, fg_color="transparent", height=1)
        arriba.pack(fill="x")
        titulo = ctk.CTkLabel(arriba, text="", font=tema.fuente(14, True), text_color=tema.TEXTO, anchor="w")
        titulo.pack(side="left")
        insignia = tema.insignia(arriba, "", tema.ACERO)
        detalle = ctk.CTkLabel(textos, text="", font=tema.fuente(11), text_color=tema.TEXTO_TENUE, anchor="w")
        detalle.pack(fill="x")
        estado["filas"].append({"fila": fila, "titulo": titulo, "insignia": insignia, "detalle": detalle,
                                "ram": ram, "proporcion": proporcion, "cerrar": cerrar, "mantener": mantener,
                                "clave": None, "visible": False, "con_insignia": False})

    def llenar_fila(fila, grupo, mayor):
        tema.actualizar(fila["titulo"], text=grupo["titulo"])
        procesos = "1 proceso" if grupo["cantidad"] == 1 else f"{grupo['cantidad']} procesos"
        tema.actualizar(fila["detalle"], text=f"{grupo['nombre']}  ·  {procesos}")
        tema.actualizar(fila["ram"], text=tema.formato_gb(grupo["ram"]))
        tema.mover_barra(fila["proporcion"], grupo["ram"] / mayor if mayor else 0)

        if grupo["protegido"]:
            texto_insignia, color = "Parte de Windows", tema.TEXTO_SUAVE
        elif grupo["vigilada"]:
            texto_insignia, color = "En tu lista", tema.ORO
        else:
            texto_insignia, color = None, None
        if texto_insignia:
            tema.actualizar(fila["insignia"], text="  " + texto_insignia + "  ", text_color=color,
                            fg_color=tema.FONDO_DE.get(color, tema.SUPERFICIE_ALTA))
            if not fila["con_insignia"]:
                fila["insignia"].pack(side="left", padx=(10, 0))
                fila["con_insignia"] = True
        elif fila["con_insignia"]:
            fila["insignia"].pack_forget()
            fila["con_insignia"] = False

        clave = (grupo["nombre"].lower(), grupo["protegido"], grupo["vigilada"])
        if fila["clave"] != clave:
            fila["clave"] = clave
            if grupo["protegido"]:
                fila["cerrar"].configure(state="disabled", command=None)
                fila["mantener"].configure(state="disabled", text="Mantener cerrada", command=None)
            else:
                fila["cerrar"].configure(state="normal", command=lambda g=grupo: cerrar_app(g))
                if grupo["vigilada"]:
                    fila["mantener"].configure(state="normal", text="Quitar de la lista",
                                               command=lambda n=grupo["nombre"]: quitar_de_lista(n))
                else:
                    fila["mantener"].configure(state="normal", text="Mantener cerrada",
                                               command=lambda g=grupo: agregar_a_lista(g))

    def dibujar_apps(grupos):
        while len(estado["filas"]) < len(grupos):
            crear_fila()
        mayor = max((g["ram"] for g in grupos), default=0)
        for indice, fila in enumerate(estado["filas"]):
            if indice < len(grupos):
                llenar_fila(fila, grupos[indice], mayor)
                if not fila["visible"]:
                    fila["fila"].pack(fill="x")
                    fila["visible"] = True
            elif fila["visible"]:
                fila["fila"].pack_forget()
                fila["visible"] = False

    def cerrar_app(grupo):
        if not messagebox.askyesno("Cerrar app", f"¿Cerrar {grupo['titulo']} ({grupo['cantidad']} procesos)?\n\n"
                                                 "Si tienes algo sin guardar en esa app, se puede perder."):
            return

        def listo(resultado):
            cerrados, _ = resultado or (0, 0)
            if cerrados:
                historial.registrar("Procesos", f"Se cerró {grupo['titulo']} ({cerrados} procesos)")
                app["notificar"](f"Se cerró {grupo['titulo']} y liberó cerca de {tema.formato_gb(grupo['ram'])}")
            else:
                app["notificar"](f"No se pudo cerrar {grupo['titulo']}", tema.CORAL)
            refrescar_apps()

        app["en_segundo_plano"](lambda: inicio.cerrar_proceso(grupo["nombre"]), listo)

    def refrescar_apps():
        if estado["refrescando"]:
            return
        estado["refrescando"] = True

        def listo(grupos):
            estado["refrescando"] = False
            if grupos is not None:
                dibujar_apps(grupos)

        app["en_segundo_plano"](lambda: memoria.apps_en_memoria(FILAS), listo)

    # ------------------------------------------------------------
    #  Actualización mientras la página está a la vista
    # ------------------------------------------------------------
    def seguir():
        if app["pagina"] != "memoria":
            return
        mostrar_estado()
        refrescar_apps()
        app["ventana"].after(3000, seguir)

    def al_mostrar():
        dibujar_cerradas()          # la lista pudo cambiar desde otra parte (por ejemplo, otra ventana)
        seguir()

    return {"al_mostrar": al_mostrar}
