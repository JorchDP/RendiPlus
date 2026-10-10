"""
historial.py  -  Registro de todo lo que RendiPlus cambia en el PC, y cómo deshacerlo.

Cada entrada guarda una lista de "pasos para deshacer". Un paso es un diccionario simple:
  {"tipo": "inicio", "programa": {...}, "activo": True}   -> reactivar un programa de inicio
  {"tipo": "plan", "valor": "<guid>"}                      -> volver a un plan de energía
  {"tipo": "ajuste", "id": "modo_juego", "valor": True}    -> volver un ajuste a como estaba
  {"tipo": "energia_mac", "valor": 0}                      -> modo de bajo consumo en Mac
"""

import time

from motores import sistema

ARCHIVO = "historial.json"


def listar():
    return sistema.leer_json(ARCHIVO, [])


def registrar(tipo, descripcion, deshacer=None):
    entradas = listar()
    entradas.insert(0, {
        "id": int(time.time() * 1000),
        "fecha": time.strftime("%d-%m-%Y %H:%M"),
        "tipo": tipo,
        "descripcion": descripcion,
        "deshacer": deshacer or [],
        "deshecho": False,
    })
    sistema.guardar_json(ARCHIVO, entradas[:300])   # guardamos las últimas 300


def aplicar_paso(paso):
    """Ejecuta un paso de deshacer. Devuelve True si funcionó."""
    from motores import inicio, perfiles   # se importan aquí para evitar importaciones circulares
    tipo = paso.get("tipo")
    if tipo == "inicio":
        return inicio.cambiar_estado(paso["programa"], paso["activo"])
    if tipo == "plan":
        return perfiles.activar_plan(paso["valor"])
    if tipo == "ajuste":
        return perfiles.escribir_ajuste(paso["id"], paso["valor"])
    if tipo == "modo_energia":
        return perfiles.poner_modo_energia(paso["valor"])
    if tipo == "energia_mac":
        return perfiles.bajo_consumo_mac(bool(paso["valor"]))
    if tipo == "perfil":
        perfiles.guardar_perfil_activo(paso.get("valor"))
        return True
    return False


def deshacer(id_entrada):
    """Deshace una entrada. Devuelve (cuántos pasos funcionaron, cuántos fallaron)."""
    entradas = listar()
    bien = 0
    mal = 0
    for entrada in entradas:
        if entrada["id"] != id_entrada or entrada["deshecho"]:
            continue
        for paso in reversed(entrada["deshacer"]):
            try:
                if aplicar_paso(paso):
                    bien = bien + 1
                else:
                    mal = mal + 1
            except Exception:
                mal = mal + 1
        entrada["deshecho"] = True
    sistema.guardar_json(ARCHIVO, entradas)
    return bien, mal


def restaurar_todo():
    """Deshace todos los cambios reversibles, del más nuevo al más antiguo."""
    bien = 0
    mal = 0
    for entrada in listar():
        if entrada["deshacer"] and not entrada["deshecho"]:
            parcial_bien, parcial_mal = deshacer(entrada["id"])
            bien = bien + parcial_bien
            mal = mal + parcial_mal
    return bien, mal


def crear_punto_restauracion():
    """(Windows, administrador) Crea un punto de restauración del sistema.
    Devuelve (funcionó, mensaje)."""
    if sistema.SISTEMA != "Windows":
        return False, "Los puntos de restauración solo existen en Windows."
    if not sistema.es_admin():
        return False, "Necesitas abrir RendiPlus como administrador."
    script = ("Checkpoint-Computer -Description 'RendiPlus' -RestorePointType 'MODIFY_SETTINGS' "
              "-WarningVariable aviso -WarningAction SilentlyContinue; "
              "if ($aviso) { Write-Output 'AVISO' } else { Write-Output 'OK' }")
    codigo, texto = sistema.ejecutar_con_codigo(["powershell", "-NoProfile", "-Command", script], 300)
    if codigo == 0 and "AVISO" in texto:
        return False, ("Windows solo permite un punto de restauración cada 24 horas. "
                       "Ya existe uno reciente.")
    if codigo == 0 and "OK" in texto:
        registrar("Sistema", "Se creó un punto de restauración del sistema")
        return True, "Punto de restauración creado."
    return False, ("No se pudo crear. Revisa que la Protección del sistema esté activada "
                   "en el disco C: (Panel de control > Sistema > Protección del sistema).")
