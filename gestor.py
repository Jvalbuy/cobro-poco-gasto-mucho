import json
import os

CARPETA_DATOS = "datos"


def cargar_datos(usuario):
    # Crear carpeta si no existe
    if not os.path.exists(CARPETA_DATOS):
        os.makedirs(CARPETA_DATOS)

    ruta = os.path.join(CARPETA_DATOS, f"{usuario}.json")

    # Si existe el archivo del usuario, cargarlo
    if os.path.exists(ruta):
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)

    # Si no existe, estructura inicial
    return {
        "mes_actual": None,
        "gastos_fijos": [],
        "meses": {}
    }


def guardar_datos(usuario, datos):
    if not os.path.exists(CARPETA_DATOS):
        os.makedirs(CARPETA_DATOS)

    ruta = os.path.join(CARPETA_DATOS, f"{usuario}.json")

    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=4, ensure_ascii=False)
