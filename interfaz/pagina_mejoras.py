"""
pagina_mejoras.py  -  Página "Mejoras": qué componente frena al equipo, qué comprarle y qué es compatible.
"""

import json

import customtkinter as ctk

from interfaz import tema
from motores import mejoras, sistema

COLOR_PRIORIDAD = {"alta": tema.CORAL, "media": tema.AMBAR, "baja": tema.ACERO}
TEXTO_PRIORIDAD = {"alta": "Más impacto", "media": "Recomendada", "baja": "Opcional"}
COLOR_COSTO = {"Bajo": tema.VERDE, "Medio": tema.AMBAR, "Alto": tema.CORAL}
NOMBRES_NIVEL = ["Muy básico", "Básico", "Entrada", "Medio", "Alto", "Tope"]


def construir(marco, app):
    contenido = tema.pagina_con_scroll(marco)
    cabeza = tema.encabezado(contenido, "Mejoras de hardware",
                             "Qué cambiarle a tu equipo para que rinda más, y qué es compatible con lo que ya tienes.")
    boton_manual = tema.boton(cabeza.acciones, "Buscar el manual de tu equipo", None, "secundario")
    cuerpo = ctk.CTkFrame(contenido, fg_color="transparent", height=1)
    cuerpo.pack(fill="both", expand=True, padx=32, pady=(0, 28))

    zona = ctk.CTkFrame(cuerpo, fg_color="transparent", height=1)
    zona.pack(fill="x")
    cargando = ctk.CTkLabel(zona, text="Analizando los componentes de tu equipo...", font=tema.fuente(13),
                            text_color=tema.TEXTO_SUAVE, anchor="w")
    cargando.pack(fill="x", pady=20)

    # ------------------------------------------------------------
    #  Piezas
    # ------------------------------------------------------------
    def tarjeta_equilibrio(padre, resultado):
        tarjeta = tema.tarjeta(padre, "Equilibrio de tu equipo")
        filas = ctk.CTkFrame(tarjeta, fg_color="transparent", height=1)
        filas.pack(fill="x", padx=20, pady=(4, 6))
        filas.grid_columnconfigure(1, weight=1)
        fila_numero = 0
        for clave, nombre in mejoras.NOMBRES_COMPONENTE.items():
            nivel = resultado["niveles"].get(clave)
            if nivel is None:
                continue
            frena = clave == resultado["limitante"]
            color = tema.CORAL if frena else (tema.VERDE if nivel >= 3 else tema.ORO)
            ctk.CTkLabel(filas, text=nombre, font=tema.fuente(13, frena), text_color=tema.TEXTO,
                         anchor="w", width=130).grid(row=fila_numero, column=0, sticky="w", pady=7)
            barra = tema.barra(filas, color, alto=8)
            barra.grid(row=fila_numero, column=1, sticky="ew", padx=(6, 14))
            barra.set(max(0.04, nivel / 5))
            ctk.CTkLabel(filas, text=NOMBRES_NIVEL[min(5, int(round(nivel)))], font=tema.fuente(12),
                         text_color=color if frena else tema.TEXTO_SUAVE, anchor="e",
                         width=78).grid(row=fila_numero, column=2, sticky="e")
            fila_numero = fila_numero + 1

        nota = ctk.CTkFrame(tarjeta, fg_color=tema.SUPERFICIE_ALTA, corner_radius=8)
        nota.pack(fill="x", padx=20, pady=(8, 18))
        if resultado["limitante"]:
            tema.insignia(nota, "Lo que más frena: " + mejoras.NOMBRES_COMPONENTE[resultado["limitante"]],
                          tema.CORAL).pack(anchor="w", padx=14, pady=(12, 0))
        ctk.CTkLabel(nota, text=resultado["equilibrio"], font=tema.fuente(13), text_color=tema.TEXTO_SUAVE,
                     anchor="w", justify="left", wraplength=380).pack(fill="x", padx=14, pady=(6, 12))
        return tarjeta

    def tarjeta_ficha(padre, resultado):
        tarjeta = tema.tarjeta(padre, "Ficha de compatibilidad")
        lista = ctk.CTkFrame(tarjeta, fg_color="transparent", height=1)
        lista.pack(fill="x", padx=20, pady=(0, 16))
        for indice, (etiqueta, valor) in enumerate(resultado["ficha"]):
            if indice:
                tema.separador(lista).pack(fill="x")
            fila = ctk.CTkFrame(lista, fg_color="transparent", height=1)
            fila.pack(fill="x", pady=7)
            ctk.CTkLabel(fila, text=etiqueta, font=tema.fuente(12), text_color=tema.TEXTO_TENUE,
                         anchor="w", width=120).pack(side="left", anchor="n")
            ctk.CTkLabel(fila, text=valor, font=tema.fuente(13), text_color=tema.TEXTO, anchor="w",
                         justify="left", wraplength=300).pack(side="left", fill="x", expand=True)
        return tarjeta

    def lista_con_marcas(padre, titulo, elementos, marca, color):
        bloque = ctk.CTkFrame(padre, fg_color="transparent", height=1)
        if titulo:
            ctk.CTkLabel(bloque, text=titulo, font=tema.fuente(11, True), text_color=tema.TEXTO_TENUE,
                         anchor="w").pack(fill="x", pady=(0, 4))
        for texto in elementos:
            fila = ctk.CTkFrame(bloque, fg_color="transparent", height=1)
            fila.pack(fill="x", pady=2)
            ctk.CTkLabel(fila, text=marca, font=tema.fuente(13, True), text_color=color, width=16,
                         anchor="nw").pack(side="left", anchor="n")
            ctk.CTkLabel(fila, text=texto, font=tema.fuente(13), text_color=tema.TEXTO, anchor="w",
                         justify="left", wraplength=320).pack(side="left", fill="x", expand=True, padx=(4, 0))
        return bloque

    def tarjeta_mejora(padre, numero, mejora):
        tarjeta = ctk.CTkFrame(padre, fg_color=tema.SUPERFICIE, corner_radius=tema.RADIO,
                               border_width=1, border_color=tema.LINEA)
        columna_numero = ctk.CTkFrame(tarjeta, fg_color="transparent", width=58, height=1)
        columna_numero.pack(side="left", fill="y", padx=(18, 0), pady=16)
        ctk.CTkLabel(columna_numero, text=str(numero), font=tema.fuente(30, True, titulo=True),
                     text_color=tema.ORO, width=40, anchor="nw").pack(anchor="n")

        centro = ctk.CTkFrame(tarjeta, fg_color="transparent", height=1)
        centro.pack(side="left", fill="both", expand=True, padx=(4, 20), pady=16)

        arriba = ctk.CTkFrame(centro, fg_color="transparent", height=1)
        arriba.pack(fill="x")
        ctk.CTkLabel(arriba, text=mejora["componente"].upper(), font=tema.fuente(11, True),
                     text_color=tema.TEXTO_TENUE, anchor="w").pack(side="left")
        tema.insignia(arriba, TEXTO_PRIORIDAD[mejora["prioridad"]],
                      COLOR_PRIORIDAD[mejora["prioridad"]]).pack(side="left", padx=10)
        tema.insignia(arriba, "Costo " + mejora["costo"].lower(),
                      COLOR_COSTO.get(mejora["costo"], tema.TEXTO_SUAVE)).pack(side="left")
        if mejora.get("url"):
            tema.boton(arriba, "Buscar precios", lambda u=mejora["url"]: sistema.abrir(u), "secundario",
                       alto=30).pack(side="right")

        ctk.CTkLabel(centro, text=mejora["titulo"], font=tema.fuente(18, True, titulo=True),
                     text_color=tema.TEXTO, anchor="w").pack(fill="x", pady=(8, 2))
        ctk.CTkLabel(centro, text=mejora["por_que"], font=tema.fuente(13), text_color=tema.TEXTO_SUAVE,
                     anchor="w", justify="left", wraplength=760).pack(fill="x")

        columnas = ctk.CTkFrame(centro, fg_color="transparent", height=1)
        columnas.pack(fill="x", pady=(14, 0))
        columnas.grid_columnconfigure((0, 1), weight=1, uniform="mejora")
        if mejora["comprar"]:
            lista_con_marcas(columnas, "QUÉ COMPRAR", mejora["comprar"], "›", tema.ORO).grid(
                row=0, column=0, sticky="nsew", padx=(0, 16))
        if mejora["compatibilidad"]:
            lista_con_marcas(columnas, "COMPATIBILIDAD", mejora["compatibilidad"], "✓", tema.VERDE).grid(
                row=0, column=1, sticky="nsew")

        if mejora["evitar"]:
            aviso = ctk.CTkFrame(centro, fg_color=tema.FONDO_DE[tema.AMBAR], corner_radius=8)
            aviso.pack(fill="x", pady=(14, 0))
            for texto in mejora["evitar"]:
                fila = ctk.CTkFrame(aviso, fg_color="transparent", height=1)
                fila.pack(fill="x", padx=14, pady=4)
                ctk.CTkLabel(fila, text="!", font=tema.fuente(13, True), text_color=tema.AMBAR, width=16,
                             anchor="nw").pack(side="left", anchor="n")
                ctk.CTkLabel(fila, text=texto, font=tema.fuente(13), text_color=tema.TEXTO, anchor="w",
                             justify="left", wraplength=700).pack(side="left", fill="x", expand=True, padx=(4, 0))
            tema.espacio(aviso, 4)
        return tarjeta

    # ------------------------------------------------------------
    #  Dibujar todo
    # ------------------------------------------------------------
    def dibujar(resultado):
        for widget in zona.winfo_children():
            widget.destroy()

        if resultado.get("manual"):
            boton_manual.configure(command=lambda: sistema.abrir(resultado["manual"]))
            boton_manual.pack()
        else:
            boton_manual.pack_forget()

        arriba = ctk.CTkFrame(zona, fg_color="transparent", height=1)
        arriba.pack(fill="x", pady=(0, 22))
        arriba.grid_columnconfigure((0, 1), weight=1, uniform="arriba")
        tarjeta_equilibrio(arriba, resultado).grid(row=0, column=0, sticky="nsew", padx=(0, 9))
        tarjeta_ficha(arriba, resultado).grid(row=0, column=1, sticky="nsew", padx=(9, 0))

        titulo = ctk.CTkFrame(zona, fg_color="transparent", height=1)
        titulo.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(titulo, text="Mejoras sugeridas", font=tema.fuente(20, True, titulo=True),
                     text_color=tema.TEXTO, anchor="w").pack(side="left")
        cantidad = len(resultado["mejoras"])
        if cantidad:
            ctk.CTkLabel(titulo, text="ordenadas por impacto en tu equipo", font=tema.fuente(12),
                         text_color=tema.TEXTO_TENUE).pack(side="left", padx=12, pady=(6, 0))

        if not cantidad:
            vacia = tema.tarjeta(zona)
            vacia.pack(fill="x", pady=(0, 18))
            ctk.CTkLabel(vacia, text="Tu equipo no necesita mejoras por ahora",
                         font=tema.fuente(16, True, titulo=True), text_color=tema.TEXTO,
                         anchor="w").pack(fill="x", padx=22, pady=(18, 2))
            ctk.CTkLabel(vacia, text="Sus componentes están equilibrados y no hay nada que compense comprar.",
                         font=tema.fuente(13), text_color=tema.TEXTO_SUAVE, anchor="w").pack(
                fill="x", padx=22, pady=(0, 18))
        for numero, mejora in enumerate(resultado["mejoras"], start=1):
            tarjeta_mejora(zona, numero, mejora).pack(fill="x", pady=(0, 12))

        if resultado["no_mejorables"] or resultado["positivos"]:
            abajo = ctk.CTkFrame(zona, fg_color="transparent", height=1)
            abajo.pack(fill="x", pady=(10, 0))
            abajo.grid_columnconfigure((0, 1), weight=1, uniform="abajo")
            columna = 0
            if resultado["no_mejorables"]:
                tarjeta = tema.tarjeta(abajo, "Lo que no se puede cambiar")
                tarjeta.grid(row=0, column=columna, sticky="nsew", padx=(0, 9))
                lista_con_marcas(tarjeta, "", resultado["no_mejorables"], "–", tema.TEXTO_TENUE).pack(
                    fill="x", padx=20, pady=(0, 16))
                columna = 1
            if resultado["positivos"]:
                tarjeta = tema.tarjeta(abajo, "Ya está bien")
                tarjeta.grid(row=0, column=columna, sticky="nsew", padx=(9 if columna else 0, 0))
                lista_con_marcas(tarjeta, "", resultado["positivos"], "✓", tema.VERDE).pack(
                    fill="x", padx=20, pady=(0, 16))

        ctk.CTkLabel(zona, text="Las sugerencias se basan en lo que informa tu equipo. Los modelos son de referencia: "
                                "antes de comprar, confirma en el manual de tu placa madre o notebook, y compara "
                                "precios en tu país.",
                     font=tema.fuente(11), text_color=tema.TEXTO_TENUE, anchor="w", justify="left",
                     wraplength=820).pack(fill="x", pady=(16, 0))

    # Solo se rearma cuando la página está a la vista y el análisis cambió
    estado = {"resultado": None, "dibujado": None, "calculando": False}

    def dibujar_si_hace_falta():
        resultado = estado["resultado"]
        if not resultado:
            return
        huella = json.dumps(resultado, sort_keys=True, default=str)
        if huella != estado["dibujado"]:
            estado["dibujado"] = huella
            dibujar(resultado)

    def calcular(dato=None):
        if not app["datos_pc"] or estado["calculando"]:
            return
        estado["calculando"] = True

        def listo(resultado):
            estado["calculando"] = False
            if resultado:
                estado["resultado"] = resultado
                if app["pagina"] == "mejoras":
                    dibujar_si_hace_falta()

        app["en_segundo_plano"](lambda: mejoras.analizar(app["datos_pc"], app["uso"]), listo)

    app["suscribir"]("datos", calcular)

    def al_mostrar():
        dibujar_si_hace_falta()
        calcular()          # la temperatura pudo cambiar desde la última vez

    if app["datos_pc"]:
        calcular()
    return {"al_mostrar": al_mostrar}
