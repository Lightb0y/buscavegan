"""Exporta la base a los archivos que consume la web estática de `web/`.

Por qué NDJSON y no un JSON grande
----------------------------------
El catálogo entero pesa ~5 MB y se versiona en git para que lo que está
publicado sea exactamente lo que está commiteado. Un único array JSON se vería
como *un solo renglón cambiado* en cada refresco y git guardaría los 5 MB de
nuevo; con un objeto por línea y ordenado por EAN, un refresco que toca 200
productos produce un diff de 200 líneas y git guarda solo eso.

Qué NO se exporta
-----------------
La cola de revisión manual, el cache de OFF y las 262.035 filas de góndola de
VTEX: son insumos del pipeline, no del sitio.

    python export_web.py
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import unicodedata
from collections import Counter
from datetime import date
from pathlib import Path

import config
from ingest_vtex import NOMBRE_LEGIBLE as CADENA_LEGIBLE

WEB_DIR = Path(__file__).resolve().parent / "web"
DATA_DIR = WEB_DIR / "data"

# Los mismos textos que muestra la app de Streamlit: una sola verdad sobre
# cómo se le explica al usuario de dónde salió cada veredicto.
FUENTE_LEGIBLE = {
    "certificacion_oficial": "Certificado en el registro oficial de ANMAT",
    "off_label": "Declarado vegano por el fabricante",
    "sello_super": "Sello de certificación en la ficha del supermercado",
    "ingredientes": "Analizado desde la lista de ingredientes",
    "ingredientes_super": "Analizado desde los ingredientes que publica el supermercado",
    "off_analysis": "Análisis de ingredientes de Open Food Facts",
    "duplicado": "Mismo producto que otro código de barras ya resuelto",
    "heuristica": "Estimado por reglas sobre el nombre del producto",
    "ml": "Estimado por clasificador automático",
    "sin_datos": "Sin datos suficientes",
}

# Fuentes que se apoyan en evidencia sobre el producto real (una lista de
# ingredientes, un sello, un registro oficial) y no en adivinar por el nombre.
# Es la métrica honesta del proyecto y la web la muestra como tal.
FUENTES_CON_EVIDENCIA = frozenset({
    "certificacion_oficial", "off_label", "sello_super",
    "ingredientes", "ingredientes_super", "off_analysis", "duplicado",
})

ESTADOS = ["apto", "vegetariano", "no_apto", "revisar"]

_NO_ALFANUM = re.compile(r"[^a-z0-9]+")


def slugify(texto: str) -> str:
    """`Leche de Almendras Ades 1L` -> `leche-de-almendras-ades-1l`.

    Sin acentos ni eñes: una URL con %C3%B1 se rompe al copiarla y pegarla.
    """
    plano = unicodedata.normalize("NFKD", texto or "")
    plano = plano.encode("ascii", "ignore").decode("ascii").lower()
    return _NO_ALFANUM.sub("-", plano).strip("-")[:70] or "producto"


def ruta_producto(ean: str, nombre: str) -> str:
    """El EAN va al final y es lo que identifica: el slug es decorativo y
    puede cambiar si se corrige el nombre, sin romper el link."""
    return f"{slugify(nombre)}-{ean}"


def _fila_a_producto(f: sqlite3.Row) -> dict:
    cadenas = [c for c in (f["cadenas_confirmadas"] or "").split(",") if c]
    p = {
        "ean": f["ean"],
        "slug": ruta_producto(f["ean"], f["nombre"]),
        "nombre": f["nombre"],
        "estado": f["estado"],
        "fuente": f["fuente_decision"],
    }
    # Las claves ausentes pesan menos que las nulas y el front ya trata
    # `undefined` como "no sabemos"; sobre 7.400 productos la diferencia es real.
    if f["marca"]:
        p["marca"] = f["marca"]
    if f["categoria"]:
        p["categoria"] = f["categoria"]
    if f["confianza"] is not None:
        p["confianza"] = round(float(f["confianza"]), 3)
    if f["motivo"]:
        p["motivo"] = f["motivo"]
    if f["ingredients_text"]:
        p["ingredientes"] = f["ingredients_text"]
    if f["imagen_url"]:
        p["imagen"] = f["imagen_url"]
    if cadenas:
        p["cadenas"] = cadenas
    return p


def exportar(conn: sqlite3.Connection, destino: Path = DATA_DIR) -> dict:
    destino.mkdir(parents=True, exist_ok=True)
    conn.row_factory = sqlite3.Row

    filas = conn.execute(
        "SELECT ean, nombre, marca, categoria, estado, fuente_decision,"
        " confianza, ingredients_text, imagen_url, motivo, cadenas_confirmadas"
        " FROM productos ORDER BY ean").fetchall()
    if not filas:
        raise SystemExit(
            "La tabla `productos` está vacía: corré `python build_db.py` antes.")

    productos = [_fila_a_producto(f) for f in filas]

    # Un objeto por línea, sin espacios, ordenado por EAN: diffs chicos en git.
    ndjson = destino / "productos.ndjson"
    with ndjson.open("w", encoding="utf-8", newline="\n") as fh:
        for p in productos:
            fh.write(json.dumps(p, ensure_ascii=False, separators=(",", ":")))
            fh.write("\n")

    por_estado = Counter(p["estado"] for p in productos)
    por_fuente = Counter(p["fuente"] for p in productos)
    por_categoria = Counter(
        p["categoria"] for p in productos if p.get("categoria"))
    con_evidencia = sum(
        n for f, n in por_fuente.items() if f in FUENTES_CON_EVIDENCIA)

    meta = {
        "actualizado": date.today().isoformat(),
        "total": len(productos),
        "por_estado": {e: por_estado.get(e, 0) for e in ESTADOS},
        "por_fuente": dict(por_fuente.most_common()),
        "categorias": [
            {"nombre": c, "slug": slugify(c), "total": n}
            for c, n in sorted(por_categoria.items())
        ],
        "con_evidencia": con_evidencia,
        "con_ingredientes": sum(1 for p in productos if p.get("ingredientes")),
        "confirmados": sum(1 for p in productos if p.get("cadenas")),
        "fuente_legible": FUENTE_LEGIBLE,
        "cadena_legible": dict(CADENA_LEGIBLE),
        "fuentes_con_evidencia": sorted(FUENTES_CON_EVIDENCIA),
    }
    (destino / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "productos": len(productos),
        "bytes_ndjson": ndjson.stat().st_size,
        "con_evidencia": con_evidencia,
        "categorias": len(meta["categorias"]),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--destino", type=Path, default=DATA_DIR)
    args = ap.parse_args()

    conn = sqlite3.connect(f"file:{config.DB_PATH}?mode=ro", uri=True)
    try:
        stats = exportar(conn, args.destino)
    finally:
        conn.close()

    pct = 100 * stats["con_evidencia"] / stats["productos"]
    print(f"{stats['productos']:,} productos -> {args.destino}".replace(",", "."))
    print(f"  productos.ndjson  {stats['bytes_ndjson'] / 1e6:.2f} MB")
    print(f"  categorias        {stats['categorias']}")
    print(f"  con evidencia     {stats['con_evidencia']:,} ({pct:.1f}%)"
          .replace(",", "."))


if __name__ == "__main__":
    main()
