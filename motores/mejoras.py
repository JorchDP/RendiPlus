"""
mejoras.py  -  Motor de mejoras de hardware de RendiPlus

Mira los componentes del equipo y responde tres preguntas:
  1. ¿Qué componente frena a los demás? (equilibrio del equipo)
  2. ¿Qué conviene comprarle, y qué es compatible con lo que ya tiene?
  3. ¿Qué NO se puede (o no vale la pena) cambiar?

Todo se deduce de lo que informa el sistema (modelo del procesador, tipo de RAM, ranuras,
discos...). No se envía nada a internet. Los modelos sugeridos son de referencia: el botón
"Buscar precios" abre una búsqueda para que el usuario compare en su país.
"""

import re
import urllib.parse

from motores import recomendaciones
from motores.sistema import SISTEMA

ORDEN_PRIORIDAD = {"alta": 0, "media": 1, "baja": 2}


def url_busqueda(texto):
    return "https://www.google.com/search?tbm=shop&q=" + urllib.parse.quote_plus(texto)


def url_manual(modelo):
    return "https://www.google.com/search?q=" + urllib.parse.quote_plus(
        modelo + " manual especificaciones memoria máxima M.2")


# ============================================================
#  1. Plataforma del procesador (se deduce del nombre del modelo)
# ============================================================

# Generación de Intel -> socket y versión de PCIe de la ranura de la tarjeta gráfica
SOCKET_INTEL = {
    2: ("LGA1155", 2), 3: ("LGA1155", 3), 4: ("LGA1150", 3), 5: ("LGA1150", 3),
    6: ("LGA1151", 3), 7: ("LGA1151", 3), 8: ("LGA1151 v2", 3), 9: ("LGA1151 v2", 3),
    10: ("LGA1200", 3), 11: ("LGA1200", 4), 12: ("LGA1700", 4), 13: ("LGA1700", 4), 14: ("LGA1700", 4),
}
NIVEL_GEN_INTEL = {2: 0.5, 3: 0.6, 4: 1.0, 5: 1.0, 6: 1.4, 7: 1.5, 8: 2.0, 9: 2.3, 10: 2.5, 11: 2.8,
                   12: 3.5, 13: 3.8, 14: 4.0}
AJUSTE_CLASE_INTEL = {3: -0.8, 5: 0.0, 7: 0.4, 9: 0.7}

NIVEL_SERIE_RYZEN = {1: 1.0, 2: 1.5, 3: 2.2, 4: 2.0, 5: 3.2, 7: 4.0, 8: 3.4, 9: 4.3}
AJUSTE_CLASE_RYZEN = {3: -0.8, 5: 0.0, 7: 0.3, 9: 0.5}


def _limitar(valor):
    return round(max(0.0, min(5.0, valor)), 1)


def plataforma_cpu(nombre):
    """Analiza el nombre del procesador. Devuelve un diccionario con:
    marca, movil (soldado a la placa), socket, pcie, nivel (0 a 5), generacion, descripcion,
    rebar (si soporta Resizable BAR) y x3d."""
    texto = recomendaciones.normalizar(nombre)
    info = {"marca": "", "movil": False, "socket": None, "pcie": None, "pcie_max": None, "nivel": None,
            "generacion": None, "descripcion": "", "rebar": None, "x3d": False}

    if texto.startswith("apple"):
        info.update(marca="Apple", movil=True, descripcion="Chip Apple (todo integrado)", rebar=True)
        if "max" in texto or "ultra" in texto:
            info["nivel"] = 4.5
        elif "pro" in texto:
            info["nivel"] = 4.0
        else:
            info["nivel"] = 3.3
        return info

    # --- Intel Core Ultra (Serie 1 y 2) ---
    encontrado = re.search(r"ultra\s+([579])\s+(\d{3})([a-z]{0,2})", texto)
    if encontrado:
        clase, numero, sufijo = int(encontrado.group(1)), encontrado.group(2), encontrado.group(3)
        escritorio = numero.startswith("2") and sufijo in ("", "k", "kf", "f", "t")
        info.update(marca="Intel", rebar=True, generacion=int(numero[0]))
        if escritorio:
            info.update(socket="LGA1851", pcie=5, pcie_max=5, nivel=_limitar(3.9 + {5: 0.0, 7: 0.4, 9: 0.6}[clase]),
                        descripcion=f"Intel Core Ultra {clase} Serie 2 de escritorio")
        else:
            castigo = 0.3 if sufijo.startswith("h") else 0.8
            info.update(movil=True, nivel=_limitar(3.3 + {5: 0.0, 7: 0.3, 9: 0.5}[clase] - castigo),
                        descripcion=f"Intel Core Ultra {clase} para notebook")
        return info

    # --- Intel Core i3/i5/i7/i9 ---
    encontrado = re.search(r"\bi([3579])[\s-]+(\d{4,5})([a-z]{0,2}\d?)", texto)
    if encontrado:
        clase, numero, sufijo = int(encontrado.group(1)), encontrado.group(2), encontrado.group(3)
        if len(numero) == 5 or numero.startswith("1"):
            generacion = int(numero[:2])
        else:
            generacion = int(numero[0])
        movil = bool(sufijo) and sufijo[0] in "uhpygm"
        nivel = NIVEL_GEN_INTEL.get(generacion, 0.5) + AJUSTE_CLASE_INTEL[clase]
        info.update(marca="Intel", generacion=generacion, rebar=generacion >= 10)
        if movil:
            nivel = nivel - (1.0 if sufijo[0] in "uyg" else 0.5)
            info.update(movil=True, nivel=_limitar(nivel),
                        descripcion=f"Intel Core i{clase} de {generacion}.ª generación para notebook")
            return info
        socket, pcie = SOCKET_INTEL.get(generacion, (None, None))
        info["pcie_max"] = 5 if generacion >= 12 else pcie
        if generacion == 11:
            pcie = 3                      # 11.ª gen en placa serie 400: 3.0; en serie 500: 4.0
            info["pcie_max"] = 4
        if sufijo in ("x", "xe") and generacion in (7, 9, 10):
            socket, pcie = "LGA2066", 3
            info["pcie_max"] = 3
        info.update(socket=socket, pcie=pcie, nivel=_limitar(nivel),
                    descripcion=f"Intel Core i{clase} de {generacion}.ª generación")
        return info

    # --- Intel Core 3/5/7 (Serie 1 y 2, sin la "i") ---
    encontrado = re.search(r"\bcore\s+([357])\s+(\d{3})([a-z]{0,2})", texto)
    if encontrado:
        clase, sufijo = int(encontrado.group(1)), encontrado.group(3)
        info.update(marca="Intel", rebar=True)
        if sufijo in ("", "f"):
            info.update(socket="LGA1700", pcie=4, pcie_max=5, generacion=14,
                        nivel=_limitar(3.6 + {3: -0.8, 5: 0.0, 7: 0.4}[clase]),
                        descripcion=f"Intel Core {clase} de escritorio")
        else:
            info.update(movil=True, nivel=_limitar(2.8 + {3: -0.8, 5: 0.0, 7: 0.3}[clase]),
                        descripcion=f"Intel Core {clase} para notebook")
        return info

    # --- AMD Ryzen AI (solo notebooks) ---
    encontrado = re.search(r"ryzen\s+ai\s+(?:max\+?\s+)?([579])", texto)
    if encontrado:
        clase = int(encontrado.group(1))
        info.update(marca="AMD", movil=True, rebar=True, nivel=_limitar(3.3 + AJUSTE_CLASE_RYZEN[clase]),
                    descripcion=f"AMD Ryzen AI {clase} para notebook")
        return info

    # --- AMD Ryzen 3/5/7/9 ---
    encontrado = re.search(r"ryzen\s+([3579])\s+(?:pro\s+)?(\d{4})(x3d|xt|x|ge|g|f|hx3d|hx|hs|h|u|e)?\b", texto)
    if encontrado:
        clase, numero, sufijo = int(encontrado.group(1)), encontrado.group(2), encontrado.group(3) or ""
        serie = int(numero[0])
        movil = sufijo.startswith(("h", "u")) or (sufijo == "e" and serie != 5)
        x3d = "x3d" in sufijo
        nivel = NIVEL_SERIE_RYZEN.get(serie, 1.0) + AJUSTE_CLASE_RYZEN[clase] + (0.8 if x3d else 0.0)
        info.update(marca="AMD", generacion=serie, x3d=x3d, rebar=serie >= 3)
        if movil:
            info.update(movil=True, nivel=_limitar(nivel - 0.5),
                        descripcion=f"AMD Ryzen {clase} {serie}000 para notebook")
            return info
        if sufijo == "g" and serie <= 5:
            nivel = nivel - 0.4          # los Ryzen "G" traen menos caché
        if serie <= 5:
            socket = "AM4"
            pcie = 3
            info["pcie_max"] = 3 if serie <= 2 or sufijo in ("g", "ge") else 4   # B450: 3.0, B550: 4.0
        else:
            socket, pcie = "AM5", 4
            info["pcie_max"] = 5
        info.update(socket=socket, pcie=pcie, nivel=_limitar(nivel),
                    descripcion=f"AMD Ryzen {clase} serie {serie}000")
        return info

    # --- Procesadores básicos o antiguos ---
    if any(palabra in texto for palabra in ("celeron", "pentium", "atom", "athlon", " fx-", "a4-", "a6-",
                                            "a8-", "a10-", "a12-", "intel processor n", " n100", " n200")):
        es_amd = "amd" in texto or "athlon" in texto or "fx-" in texto
        info.update(marca="AMD" if es_amd else "Intel",
                    nivel=0.5, descripcion="Procesador de gama básica o antiguo")
        return info
    return info


CHIPSETS_PCIE3 = ("a320", "b350", "x370", "b450", "x470", "a520", "h410", "b460", "h470", "z490",
                  "h310", "b360", "b365", "h370", "z370", "z390")
CHIPSETS_PCIE4 = ("b550", "x570", "b560", "h570", "z590", "h610", "b660", "h670", "b760", "h770")


def afinar_pcie(plataforma, placa):
    """Con el modelo de la placa (por ejemplo "B450M") se sabe qué PCIe tiene la ranura de la GPU."""
    texto = (placa or "").lower()
    if not texto or plataforma["pcie"] is None or plataforma["pcie"] == plataforma["pcie_max"]:
        return
    if any(chipset in texto for chipset in CHIPSETS_PCIE3):
        plataforma["pcie"] = plataforma["pcie_max"] = 3
    elif any(chipset in texto for chipset in CHIPSETS_PCIE4):
        plataforma["pcie"] = plataforma["pcie_max"] = 4


# Lo mejor que se le puede poner a cada socket sin cambiar la placa madre
TECHO_SOCKET = {
    "AM4": {"tope": "Ryzen 7 5700X3D o Ryzen 7 5800X3D", "economico": "Ryzen 5 5600", "nivel": 4.2,
            "nota": "Las placas serie 300 y 400 (A320, B350, B450, X470) necesitan actualizar la BIOS "
                    "antes de poner un Ryzen 5000. Hazlo con tu procesador actual todavía instalado."},
    "AM5": {"tope": "Ryzen 7 9800X3D", "economico": "Ryzen 5 9600X", "nivel": 5.0,
            "nota": "Actualiza la BIOS antes de cambiarlo, sobre todo para la serie 9000."},
    "LGA1851": {"tope": "Core Ultra 9 285K", "economico": "Core Ultra 5 245K", "nivel": 4.6, "nota": ""},
    "LGA1700": {"tope": "Core i7-14700K", "economico": "Core i5-14400F", "nivel": 4.4,
                "nota": "Si tu placa es serie 600 (H610, B660, Z690), actualiza la BIOS antes de poner un "
                        "procesador de 13.ª o 14.ª generación. Con esas generaciones, mantén la BIOS al día: "
                        "las versiones nuevas corrigen un problema de estabilidad que tuvieron."},
    "LGA1200": {"tope": "Core i7-11700F o Core i9-10900", "economico": "Core i5-11400F", "nivel": 3.2,
                "nota": "Los de 11.ª generación funcionan en placas serie 500 (B560, H570, Z590) y en algunas "
                        "Z490 o H470 con la BIOS al día. Las placas H410 y B460 solo aceptan 10.ª generación "
                        "(hasta el Core i9-10900)."},
    "LGA1151 v2": {"tope": "Core i7-9700 o Core i9-9900K", "economico": "Core i5-9400F", "nivel": 2.9,
                   "nota": "Solo en placas serie 300 (H310, B360, B365, H370, Z370, Z390)."},
    "LGA1151": {"tope": "Core i7-7700K", "economico": "Core i5-7500", "nivel": 1.9,
                "nota": "Las placas serie 100 y 200 llegan hasta la 7.ª generación."},
    "LGA1150": {"tope": "Core i7-4790K", "economico": "Core i5-4690", "nivel": 1.3, "nota": ""},
    "LGA1155": {"tope": "Core i7-3770", "economico": "Core i5-3570", "nivel": 0.9, "nota": ""},
}


# ============================================================
#  2. Niveles de cada componente (0 a 5) para ver el equilibrio
# ============================================================

def nivel_ram(ram):
    total = ram.get("_total_gb") or 0
    modulos = ram.get("_modulos") or []
    soldada = ram.get("_soldada") or str(ram.get("_tipo", "")).startswith("LPDDR")
    doble = len(modulos) >= 2 or soldada or not modulos
    if total < 7.5:
        nivel = 1.0
    elif total < 15:
        nivel = 2.0
    elif total < 31:
        nivel = 3.5
    elif total < 63:
        nivel = 4.5
    else:
        nivel = 5.0
    if not doble:
        nivel = nivel - 1.0
    return _limitar(nivel)


def disco_sistema(datos_pc):
    """Tipo de disco donde está instalado el sistema: 'HDD', 'SSD', 'SSD NVMe' o ''."""
    if SISTEMA == "Darwin":
        return "SSD NVMe"
    import os
    letra = (os.environ.get("SystemDrive") or "C:")[0].upper()
    return (datos_pc.get("tipo_por_unidad") or {}).get(letra, "")


def nivel_disco(tipo):
    if tipo == "HDD":
        return 0.5
    if "NVMe" in tipo:
        return 4.5
    if "SSD" in tipo:
        return 3.5
    return None


NOMBRES_COMPONENTE = {"cpu": "Procesador", "gpu": "Tarjeta gráfica", "ram": "Memoria RAM",
                      "disco": "Almacenamiento"}


def equilibrio(niveles, portatil=False):
    """Busca el componente que frena a los demás."""
    conocidos = {clave: valor for clave, valor in niveles.items() if valor is not None}
    if len(conocidos) < 2:
        return None, "No hay datos suficientes para comparar los componentes."
    fijos = ("cpu", "gpu") if portatil else ()
    ordenados = sorted(conocidos.items(), key=lambda par: (par[1], par[0] in fijos))
    peor, valor_peor = ordenados[0]
    segundo = ordenados[1][1]
    promedio_resto = sum(v for c, v in ordenados[1:]) / (len(ordenados) - 1)
    if segundo - valor_peor < 0.8 and promedio_resto - valor_peor < 1.2:
        return None, "Tu equipo está equilibrado: ningún componente frena demasiado a los demás."
    textos = {
        "disco": "El disco duro es lo que más frena tu equipo: hace que todo arranque y cargue lento, "
                 "aunque el resto de los componentes sea bueno.",
        "ram": "La memoria RAM es el punto más débil: se llena rápido y obliga a Windows a usar el disco, "
               "lo que provoca tirones.",
        "cpu": "El procesador se queda atrás frente al resto: en juegos, la tarjeta gráfica no alcanza "
               "a trabajar al 100 % porque el procesador no le entrega los cuadros a tiempo.",
        "gpu": "La tarjeta gráfica es la que limita en juegos: el resto del equipo tiene margen para "
               "una más potente.",
    }
    if portatil:
        textos["gpu"] = ("La tarjeta gráfica es lo que más limita en juegos. En un notebook no se puede cambiar: "
                         "lo que más ayuda es ajustar la calidad gráfica (mira Recomendaciones) y mantener el "
                         "equipo fresco.")
        textos["cpu"] = ("El procesador es lo que más limita. En un notebook no se puede cambiar: juega "
                         "enchufado, con el perfil Rendimiento y cerrando apps en segundo plano.")
    return peor, textos[peor]


# ============================================================
#  3. Reglas de cada mejora
# ============================================================

GPUS_SUGERIDAS = {
    3: {"modelos": "RTX 5060, RX 9060 XT de 16 GB o Arc B580", "fuente": 550, "ocho_lineas": True,
        "arc": True},
    4: {"modelos": "RTX 5070, RX 9070 o RX 9070 XT", "fuente": 650, "ocho_lineas": False, "arc": False},
    5: {"modelos": "RTX 5070 Ti o RTX 5080", "fuente": 850, "ocho_lineas": False, "arc": False},
}


def analizar(datos_pc, uso=None):
    uso = uso or {}
    sistema_pc = datos_pc.get("sistema", {})
    cpu = datos_pc.get("cpu", {})
    ram = datos_pc.get("ram", {})
    gpus = datos_pc.get("gpus", [])
    pantalla = datos_pc.get("pantalla") or {}
    fisicos = datos_pc.get("discos_fisicos", [])
    portatil = bool(sistema_pc.get("_portatil"))
    es_mac = SISTEMA == "Darwin"

    plataforma = plataforma_cpu(cpu.get("Modelo", ""))
    afinar_pcie(plataforma, sistema_pc.get("_placa"))
    if plataforma["movil"] and not portatil and plataforma["marca"] != "Apple":
        portatil = True            # un procesador de notebook siempre va soldado
    gpu, nivel_gpu_actual = recomendaciones.gpu_principal(gpus)
    nombre_gpu = gpu.get("Modelo", "")
    tipo_disco = disco_sistema(datos_pc)
    hay_nvme = es_mac or any("NVMe" in d.get("Tipo", "") for d in fisicos)

    niveles = {
        "cpu": plataforma["nivel"],
        "gpu": float(nivel_gpu_actual) if nivel_gpu_actual is not None else None,
        "ram": nivel_ram(ram) if ram.get("_total_gb") else None,
        "disco": nivel_disco(tipo_disco),
    }
    limitante, texto_equilibrio = equilibrio(niveles, portatil)

    mejoras = []
    no_mejorables = []
    positivos = []

    def agregar(**datos):
        datos.setdefault("comprar", [])
        datos.setdefault("compatibilidad", [])
        datos.setdefault("evitar", [])
        datos.setdefault("busqueda", None)
        mejoras.append(datos)

    # ------------------------------------------------------------
    #  Memoria RAM
    # ------------------------------------------------------------
    total = ram.get("_total_gb") or 0
    modulos = ram.get("_modulos") or []
    tipo_ram = ram.get("_tipo", "")
    soldada = bool(ram.get("_soldada")) or tipo_ram.startswith("LPDDR")
    formato = ram.get("_formato") or ("SO-DIMM" if portatil else "DIMM")
    texto_formato = "SO-DIMM (formato de notebook)" if formato == "SO-DIMM" else "DIMM (formato de escritorio)"
    velocidad = ram.get("_velocidad_nominal") or ram.get("_velocidad") or 0
    ranuras = ram.get("_ranuras")
    maximo = ram.get("_maximo_gb")
    libres = (ranuras - len(modulos)) if ranuras else None
    mismo_modelo = (" ".join(x for x in (ram.get("_fabricante"), ram.get("_parte")) if x)
                    if ram.get("_parte") else "")

    if soldada:
        no_mejorables.append("La memoria RAM viene soldada a la placa (" + (tipo_ram or "memoria unificada")
                             + "): no se puede ampliar.")
    elif modulos and total:
        compatibilidad = []
        if tipo_ram:
            compatibilidad.append(f"Tipo: {tipo_ram}. Otro tipo de memoria no entra físicamente en la ranura.")
        compatibilidad.append(f"Formato: {texto_formato}.")
        if velocidad:
            compatibilidad.append(f"Velocidad: {velocidad} MT/s o más. Si compras una más rápida, "
                                  f"funcionará a {velocidad} MT/s junto con la que ya tienes.")
        if ranuras:
            compatibilidad.append(f"Ranuras: {len(modulos)} de {ranuras} en uso.")
        if maximo and maximo >= 8:
            compatibilidad.append(f"Tu placa acepta hasta {maximo} GB en total.")

        etiqueta = " ".join(x for x in (tipo_ram, formato) if x)
        texto_velocidad = f" a {velocidad} MT/s" if velocidad else ""

        def cabe(cantidad):
            return not maximo or cantidad <= maximo

        if len(modulos) == 1:
            actual = modulos[0]
            if actual >= 8 and (libres is None or libres >= 1) and cabe(actual * 2):
                comprar = [f"1 módulo de {actual} GB {etiqueta}{texto_velocidad}, igual al que tienes."]
                if mismo_modelo:
                    comprar.append(f"Lo ideal es el mismo modelo: {mismo_modelo}.")
                titulo = f"Agrega un segundo módulo de {actual} GB"
                busqueda = f"memoria RAM {actual}GB {etiqueta} {velocidad or ''}".strip()
                resultado_total = actual * 2
            else:
                comprar = [f"Un kit de 2 x 8 GB {etiqueta}{texto_velocidad} (16 GB en doble canal)."]
                if libres is not None and libres >= 1:
                    comprar.append(f"Tu módulo actual de {actual} GB quedaría de sobra: mejor no mezclarlo.")
                titulo = "Cambia a dos módulos de 8 GB"
                busqueda = f"kit memoria RAM 2x8GB {etiqueta} {velocidad or ''}".strip()
                resultado_total = 16
            if libres is None and portatil:
                compatibilidad.append("Revisa en el manual de tu notebook que tenga una segunda ranura: "
                                      "algunos traen solo una, o la otra memoria soldada.")
            agregar(id="ram", componente="Memoria RAM", prioridad="alta", costo="Bajo",
                    titulo=titulo,
                    por_que=f"Tienes un solo módulo de {actual} GB, así que la memoria trabaja en un solo "
                            f"canal. Con dos módulos se activa el doble canal: la memoria entrega el doble de "
                            f"datos por segundo y los juegos ganan FPS, sobre todo los que exigen al "
                            f"procesador. Quedarías con {resultado_total} GB.",
                    comprar=comprar, compatibilidad=compatibilidad, busqueda=busqueda)

        elif total < 15:
            if libres and libres >= 2 and len(set(modulos)) == 1 and cabe(total * 2):
                comprar = [f"{len(modulos)} módulos más de {modulos[0]} GB {etiqueta}{texto_velocidad}, "
                           "iguales a los que tienes."]
                if mismo_modelo:
                    comprar.append(f"Mismo modelo que ya tienes: {mismo_modelo}.")
                busqueda = f"memoria RAM {modulos[0]}GB {etiqueta} {velocidad or ''}".strip()
            else:
                comprar = [f"Un kit de 2 x 8 GB {etiqueta}{texto_velocidad}, reemplazando los módulos actuales."]
                busqueda = f"kit memoria RAM 2x8GB {etiqueta} {velocidad or ''}".strip()
            agregar(id="ram", componente="Memoria RAM", prioridad="alta" if total < 7.5 else "media",
                    costo="Bajo", titulo="Sube a 16 GB de RAM",
                    por_que=f"Con {total:.0f} GB, Windows, el navegador y un juego no caben a la vez y el "
                            "sistema termina usando el disco como memoria, que es mucho más lento. "
                            "16 GB es lo recomendado hoy para jugar.",
                    comprar=comprar, compatibilidad=compatibilidad, busqueda=busqueda)

        elif total < 31 and len(modulos) >= 2 and cabe(32) and not portatil:
            if libres and libres >= 2 and len(set(modulos)) == 1 and tipo_ram != "DDR5":
                comprar = [f"Otros 2 módulos de {modulos[0]} GB {etiqueta}{texto_velocidad} iguales a los tuyos."]
                busqueda = f"memoria RAM {modulos[0]}GB {etiqueta} {velocidad or ''}".strip()
            else:
                comprar = [f"Un kit de 2 x 16 GB {etiqueta}{texto_velocidad}, reemplazando el actual."]
                busqueda = f"kit memoria RAM 2x16GB {etiqueta} {velocidad or ''}".strip()
            evitar = []
            if tipo_ram == "DDR5":
                evitar.append("Con DDR5, usar 4 módulos suele obligar a bajar la velocidad: mejor 2 módulos "
                              "más grandes.")
            agregar(id="ram", componente="Memoria RAM", prioridad="baja", costo="Medio",
                    titulo="32 GB si haces más que jugar",
                    por_que=f"Con {total:.0f} GB en doble canal ya estás bien para jugar. 32 GB solo vale la "
                            "pena si transmites, editas video o dejas muchas cosas abiertas mientras juegas.",
                    comprar=comprar, compatibilidad=compatibilidad, evitar=evitar, busqueda=busqueda)
        else:
            positivos.append(f"Memoria: {total:.0f} GB" + (" en doble canal." if len(modulos) >= 2 else "."))

    # ------------------------------------------------------------
    #  Almacenamiento
    # ------------------------------------------------------------
    modelo_m2 = ("SSD NVMe M.2 de 1 TB" if hay_nvme or plataforma["pcie"] in (4, 5)
                 else "SSD SATA de 2,5\" de 1 TB")
    compatibilidad_ssd = []
    if hay_nvme:
        compatibilidad_ssd.append("Tu equipo ya usa un disco NVMe, así que tiene ranura M.2. Revisa en el "
                                  "manual si queda una libre o si tendrías que reemplazar el actual.")
        compatibilidad_ssd.append("Un SSD PCIe 4.0 funciona también en ranuras PCIe 3.0 (a la velocidad de la ranura).")
    else:
        compatibilidad_ssd.append("No detectamos discos NVMe. Si tu placa o notebook tiene ranura M.2 "
                                  "(revisa el manual), un NVMe es más rápido; si no, un SSD SATA de 2,5\" "
                                  "funciona en cualquier equipo con conector SATA.")
    if not es_mac and tipo_disco == "HDD":
        agregar(id="ssd", componente="Almacenamiento", prioridad="alta", costo="Bajo",
                titulo="Instala Windows en un SSD",
                por_que="Tu sistema está en un disco duro mecánico. Es la mejora más notoria que existe: el PC "
                        "arranca en segundos, las apps abren al instante y los juegos cargan mucho más rápido.",
                comprar=[modelo_m2 + " (de 500 GB como mínimo, si el presupuesto es justo).",
                         "Para pasar Windows: el programa de migración que entrega la marca del SSD "
                         "(Samsung, Crucial, Kingston y otras lo tienen) o una instalación limpia."],
                compatibilidad=compatibilidad_ssd, busqueda=modelo_m2.replace(" de 2,5\"", ""))
    else:
        principal = None
        for disco in datos_pc.get("discos", []):
            if disco["unidad"].upper().startswith("C:") or disco["unidad"] in ("/", "Macintosh HD"):
                principal = disco
        hdds = sorted(letra for letra, tipo in (datos_pc.get("tipo_por_unidad") or {}).items() if tipo == "HDD")
        if principal and principal["total"] < 600 and principal["libre"] / max(principal["total"], 1) < 0.25:
            if es_mac:
                agregar(id="ssd", componente="Almacenamiento", prioridad="media", costo="Medio",
                        titulo="Un SSD externo para tus juegos y archivos",
                        por_que=f"Tu disco es de {principal['total']:.0f} GB y queda poco espacio. En un Mac "
                                "el disco interno no se puede cambiar, pero un SSD externo rápido funciona muy bien.",
                        comprar=["SSD externo USB-C de 1 TB (o un NVMe dentro de una carcasa USB 3.2 o Thunderbolt)."],
                        busqueda="SSD externo USB-C 1TB")
            else:
                agregar(id="ssd", componente="Almacenamiento", prioridad="media", costo="Bajo",
                        titulo="Más espacio: un segundo SSD",
                        por_que=f"Tu disco principal es de {principal['total']:.0f} GB y le queda poco espacio. "
                                "Los juegos actuales ocupan entre 50 y 150 GB cada uno; un segundo SSD para "
                                "juegos deja respirar a Windows.",
                        comprar=[modelo_m2 + " para instalar los juegos."],
                        compatibilidad=compatibilidad_ssd, busqueda=modelo_m2.replace(" de 2,5\"", ""))
        elif hdds and not portatil:
            agregar(id="ssd", componente="Almacenamiento", prioridad="baja", costo="Bajo",
                    titulo="Un SSD para los juegos",
                    por_que=f"Tienes un disco duro mecánico ({', '.join(l + ':' for l in hdds)}). Si instalas "
                            "juegos ahí, cargan lento y algunos juegos nuevos dan tirones al cargar el mapa. "
                            "Deja el disco duro para fotos, videos y respaldos.",
                    comprar=[modelo_m2 + " para los juegos."],
                    compatibilidad=compatibilidad_ssd, busqueda=modelo_m2.replace(" de 2,5\"", ""))
        elif tipo_disco:
            positivos.append(f"El sistema está en un {tipo_disco} con espacio suficiente.")

    # ------------------------------------------------------------
    #  Procesador
    # ------------------------------------------------------------
    nivel_cpu = plataforma["nivel"]
    socket = plataforma["socket"]
    if es_mac or plataforma["marca"] == "Apple":
        no_mejorables.append("En un Mac el procesador, la memoria, los gráficos y el SSD vienen integrados: "
                             "las mejoras posibles son externas (SSD externo, monitor).")
    elif portatil:
        no_mejorables.append("El procesador y la tarjeta gráfica de un notebook vienen soldados a la placa: "
                             "no se pueden cambiar. Lo que sí se puede mejorar es la RAM y el SSD.")
    elif nivel_cpu is None:
        no_mejorables.append("No pudimos identificar la plataforma de tu procesador. Para saber qué procesador "
                             "le puedes poner, busca el modelo de tu placa madre y su lista de CPUs compatibles.")
    elif socket in TECHO_SOCKET:
        techo = TECHO_SOCKET[socket]
        ganancia = techo["nivel"] - nivel_cpu
        frena = limitante == "cpu" or (niveles["gpu"] or 0) - nivel_cpu >= 1.2
        if ganancia >= 0.9:
            prioridad = "alta" if frena else ("media" if nivel_cpu < 2.5 else "baja")
            comprar = [f"Para jugar: {techo['tope']}.", f"Opción económica: {techo['economico']}."]
            compatibilidad = [f"Tu placa usa el socket {socket}: estos procesadores entran sin cambiarla.",
                              "Usa pasta térmica nueva al instalarlo."]
            if techo["nota"]:
                compatibilidad.append(techo["nota"])
            if socket in ("AM4", "AM5"):
                compatibilidad.append("Los modelos X3D son los mejores para juegos gracias a su caché extra.")
            evitar = []
            if niveles["gpu"] == 0:
                prioridad = "baja"
                evitar.append("Hoy usas los gráficos del procesador. Los modelos sugeridos no traen gráficos "
                              "integrados (o traen unos muy básicos): compra primero la tarjeta gráfica.")
            agregar(id="cpu", componente="Procesador", prioridad=prioridad, costo="Medio",
                    titulo=f"Un procesador más potente para tu placa {socket}",
                    por_que=(f"Tu {plataforma['descripcion']} está lejos del máximo que acepta tu placa. "
                             + ("Hoy es lo que más frena a tu tarjeta gráfica. " if frena else "")
                             + "Cambiarlo es de las mejoras con más impacto en FPS sin tocar el resto del equipo."),
                    comprar=comprar, compatibilidad=compatibilidad, evitar=evitar,
                    busqueda=techo["tope"].split(" o ")[-1])
        elif techo["nivel"] < 3.0 and (frena or nivel_cpu < 2.3):
            reusar = tipo_ram == "DDR4"
            comprar = ["Moderno: Ryzen 5 7600 o 9600X + placa B650 + 2 x 16 GB DDR5 (socket AM5, con camino "
                       "para futuras mejoras)."]
            if reusar:
                comprar.append("Económico: Ryzen 5 5600 + placa B550: puedes reutilizar tu RAM DDR4 actual.")
            else:
                comprar.append("Económico: Ryzen 5 5600 + placa B550 + 2 x 8 GB DDR4.")
            agregar(id="plataforma", componente="Procesador y placa", prioridad="alta" if frena else "media",
                    costo="Alto", titulo="Renovar procesador y placa madre",
                    por_que=f"Tu placa ({socket}) ya no tiene procesadores mucho mejores que el tuyo. Para dar "
                            "un salto real hay que cambiar procesador y placa madre juntos"
                            + (", y también la RAM." if not reusar else "."),
                    comprar=comprar,
                    compatibilidad=["Tu fuente, gabinete, tarjeta gráfica y discos se pueden seguir usando.",
                                    "Revisa que el disipador del procesador sea compatible con el socket nuevo "
                                    "(la mayoría trae soportes para AM4 y AM5)."],
                    busqueda="Ryzen 5 7600 placa B650")
        else:
            positivos.append(f"Tu procesador ({plataforma['descripcion']}) está cerca del máximo de su placa.")

    # ------------------------------------------------------------
    #  Tarjeta gráfica (solo escritorio)
    # ------------------------------------------------------------
    nivel_g = niveles["gpu"]
    if not portatil and not es_mac and nivel_g is not None:
        objetivo = max(int(nivel_g) + 2, 3)
        if (pantalla.get("alto") or 1080) > 1080:
            objetivo = max(objetivo, 4)
        if nivel_cpu is not None:
            objetivo = min(objetivo, int(nivel_cpu + 1.3))
        objetivo = min(objetivo, 5)
        if objetivo > nivel_g and objetivo >= 3:
            sugerida = GPUS_SUGERIDAS[objetivo]
            comprar = [f"Alguna de estas: {sugerida['modelos']}."]
            compatibilidad = [f"Fuente de poder: al menos {sugerida['fuente']} W de una marca reconocida, con "
                              "certificación 80 Plus y los conectores que pida la tarjeta.",
                              "Mide el espacio en tu gabinete: algunas tarjetas pasan los 30 cm de largo."]
            evitar = []
            if sugerida["ocho_lineas"] and plataforma["pcie"] == 3:
                inicio_texto = ("Tu placa es PCIe 3.0" if plataforma["pcie_max"] == 3
                                else "Si tu placa es PCIe 3.0 (por ejemplo B450, A520 o serie 400 de Intel)")
                evitar.append(inicio_texto + ": las tarjetas de esta gama usan 8 líneas y pierden rendimiento "
                              "cuando se les acaba la VRAM. Si eliges una, que sea de 16 GB.")
            if sugerida["arc"] and plataforma["rebar"] is False:
                evitar.append("Evita las Intel Arc: necesitan Resizable BAR y tu plataforma no lo tiene; "
                              "rinden muy por debajo de lo esperado.")
            if nivel_g == 0:
                prioridad = "alta"
                por_que = ("Estás usando los gráficos integrados del procesador. Una tarjeta gráfica dedicada "
                           "multiplica los FPS y permite jugar títulos actuales.")
            else:
                prioridad = "alta" if limitante == "gpu" else ("media" if nivel_g <= 2 else "baja")
                por_que = (f"Tu {nombre_gpu} es de {recomendaciones.NOMBRE_NIVEL[int(nivel_g)]}. "
                           f"Tu procesador aguanta una tarjeta de {recomendaciones.NOMBRE_NIVEL[objetivo]} "
                           "sin quedarse atrás.")
            agregar(id="gpu", componente="Tarjeta gráfica", prioridad=prioridad, costo="Alto",
                    titulo="Una tarjeta gráfica más potente", por_que=por_que, comprar=comprar,
                    compatibilidad=compatibilidad, evitar=evitar,
                    busqueda=sugerida["modelos"].split(",")[0].replace("Alguna de estas: ", ""))
        elif objetivo <= nivel_g and nivel_cpu is not None and nivel_g - nivel_cpu >= 1:
            positivos.append("Tu tarjeta gráfica ya es más potente que tu procesador: no conviene cambiarla "
                             "antes que el procesador.")
        elif nivel_g >= 3:
            positivos.append(f"Tarjeta gráfica: {nombre_gpu}, bien equilibrada con tu procesador.")

    # ------------------------------------------------------------
    #  Monitor
    # ------------------------------------------------------------
    hz_max = pantalla.get("hz_max") or 0
    if hz_max and hz_max <= 75 and (nivel_g or 0) >= 2:
        alto_pantalla = pantalla.get("alto") or 1080
        if (nivel_g or 0) >= 4 and alto_pantalla <= 1080:
            modelo_monitor = "Monitor 1440p de 144 a 180 Hz, panel IPS"
        else:
            modelo_monitor = "Monitor 1080p de 144 a 180 Hz, panel IPS"
        agregar(id="monitor", componente="Monitor", prioridad="media", costo="Medio",
                titulo="Un monitor de alta frecuencia",
                por_que=f"Tu pantalla llega a {hz_max} Hz, así que aunque tu equipo saque más FPS, solo ves "
                        f"{hz_max}. Con 144 Hz o más, los juegos se ven y se sienten mucho más fluidos.",
                comprar=[modelo_monitor + ", con FreeSync o G-Sync Compatible."],
                compatibilidad=["Conéctalo por DisplayPort o por HDMI 2.0 o superior: con cables más antiguos "
                                "no llega a los Hz altos.",
                                "En un notebook, conéctalo al puerto que salga de la tarjeta gráfica dedicada "
                                "(suele ser el HDMI o el USB-C con DisplayPort)." if portatil else
                                "Conéctalo a la tarjeta gráfica, no a la salida de la placa madre."],
                busqueda=modelo_monitor.replace(", panel IPS", ""))

    # ------------------------------------------------------------
    #  Refrigeración (notebooks calientes)
    # ------------------------------------------------------------
    temperatura = max(uso.get("cpu_temp") or 0, uso.get("gpu_temp") or 0)
    if portatil and not es_mac and temperatura >= 88:
        agregar(id="frio", componente="Refrigeración", prioridad="media", costo="Bajo",
                titulo="Bajarle la temperatura al notebook",
                por_que=f"Tu equipo llega a {temperatura} °C. Al calentarse tanto, baja su velocidad para "
                        "protegerse y pierdes FPS.",
                comprar=["Una base refrigerante con ventiladores.",
                         "Una mantención: limpieza de ventiladores y cambio de pasta térmica (si tu equipo "
                         "tiene más de 2 años, suele hacer una gran diferencia)."],
                busqueda="base refrigerante notebook gamer")

    componente_de = {"ram": "ram", "ssd": "disco", "cpu": "cpu", "plataforma": "cpu", "gpu": "gpu"}
    orden_costo = {"Bajo": 0, "Medio": 1, "Alto": 2}
    mejoras.sort(key=lambda m: (ORDEN_PRIORIDAD[m["prioridad"]],
                                not (limitante and componente_de.get(m["id"]) == limitante),
                                orden_costo.get(m["costo"], 1)))
    for mejora in mejoras:
        if mejora["busqueda"]:
            mejora["url"] = url_busqueda(mejora["busqueda"])

    # ------------------------------------------------------------
    #  Ficha de compatibilidad
    # ------------------------------------------------------------
    ficha = []
    ficha.append(("Equipo", ("Mac" if es_mac else ("Notebook" if portatil else "PC de escritorio"))
                  + (" · " + sistema_pc["_modelo"] if sistema_pc.get("_modelo") and (portatil or es_mac) else "")))
    if sistema_pc.get("_placa") and not portatil:
        ficha.append(("Placa madre", sistema_pc["_placa"]))
    if plataforma["descripcion"]:
        texto = plataforma["descripcion"]
        if socket:
            texto = texto + " · socket " + socket
        elif plataforma["movil"]:
            texto = texto + " · soldado"
        ficha.append(("Procesador", texto))
    if ram.get("_total_gb"):
        partes = [f"{ram['_total_gb']:.0f} GB"]
        if tipo_ram:
            partes.append(tipo_ram)
        if soldada:
            partes.append("soldada")
        else:
            if ram.get("_formato") or modulos:
                partes.append(formato)
            if ranuras:
                partes.append(f"{len(modulos)} de {ranuras} ranuras en uso")
            if maximo and maximo >= 8:
                partes.append(f"máximo {maximo} GB")
        ficha.append(("Memoria", " · ".join(partes)))
    if not es_mac:
        ficha.append(("Almacenamiento", "Tiene ranura M.2 (usa NVMe)" if hay_nvme else "No se detectó NVMe"))
    if plataforma["pcie"] and not portatil:
        if plataforma["pcie_max"] and plataforma["pcie_max"] > plataforma["pcie"]:
            texto_pcie = f"PCIe {plataforma['pcie']}.0 o {plataforma['pcie_max']}.0, según la placa"
        else:
            texto_pcie = f"PCIe {plataforma['pcie']}.0"
        ficha.append(("Ranura de la GPU", texto_pcie))
    if nombre_gpu:
        ficha.append(("Gráficos", nombre_gpu))

    modelo_para_manual = sistema_pc.get("_modelo") if portatil else sistema_pc.get("_placa")
    return {
        "portatil": portatil,
        "mac": es_mac,
        "niveles": niveles,
        "limitante": limitante,
        "equilibrio": texto_equilibrio,
        "mejoras": mejoras,
        "no_mejorables": no_mejorables,
        "positivos": positivos,
        "ficha": ficha,
        "manual": url_manual(modelo_para_manual) if modelo_para_manual else None,
        "modelo_manual": modelo_para_manual,
    }
