"""Ingesta desde el dump completo de Open Food Facts (la vía más completa).

Por qué existe, si ya hay dos ingestores por API
------------------------------------------------
Las dos APIs de OFF dejan afuera cosas distintas:

- `search.openfoodfacts.org` (rápida) indexa ~9.700 productos argentinos y
  **no expone `ingredients_text`**, solo la taxonomía `ingredients_tags`.
- `world.openfoodfacts.org/api/v2` reporta ~16.000, pero su límite de ~10
  req/min hace que bajar el catálogo entero lleve horas.

El dump oficial resuelve las dos cosas de una: trae **todos** los productos y
el texto de ingredientes tal cual lo cargó quien subió el producto, que es la
mejor materia prima para clasificar (incluye los códigos INS y el detalle entre
paréntesis que la taxonomía pierde).

Son 1,3 GB comprimidos que se procesan **en streaming**: se descomprime y se
filtra por país sobre la marcha, sin escribir el archivo completo en disco.

    python ingest_off_dump.py                 # catálogo argentino completo
    python ingest_off_dump.py --pais chile
    python ingest_off_dump.py --limite 1000   # prueba corta
"""
from __future__ import annotations

import argparse
import csv
import gzip
import io
import sys

import requests

import config
import db

DUMP_URL = ("https://static.openfoodfacts.org/data/"
            "en.openfoodfacts.org.products.csv.gz")

# El "csv" de OFF es en realidad TSV, y trae campos larguísimos.
DELIMITADOR = "\t"
csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

COLUMNAS = {
    "code": "code",
    "product_name": "product_name",
    "brands": "brands",
    "countries_tags": "countries_tags",
    "ingredients_text": "ingredients_text",
    "ingredients_tags": "ingredients_tags",
    "ingredients_analysis_tags": "ingredients_analysis_tags",
    "labels_tags": "labels_tags",
    "categories_tags": "categories_tags",
    "image_small_url": "image_front_small_url",
}


def _clean(value) -> str | None:
    if value is None:
        return None
    s = " ".join(str(value).split())
    return s or None


def _lista(value) -> list[str]:
    """Los campos *_tags del dump vienen separados por coma."""
    if not value:
        return []
    return [t.strip() for t in str(value).split(",") if t.strip()]


def stream_filas(url: str = DUMP_URL, chunk: int = 1 << 20):
    """Itera el dump como diccionarios, descomprimiendo en streaming."""
    session = requests.Session()
    session.headers.update({"User-Agent": config.OFF_USER_AGENT})
    with session.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        crudo = gzip.GzipFile(fileobj=r.raw)
        texto = io.TextIOWrapper(crudo, encoding="utf-8", errors="replace",
                                 newline="")
        lector = csv.DictReader(texto, delimiter=DELIMITADOR)
        for fila in lector:
            yield fila


def ingest(conn, pais: str = "argentina", limite: int | None = None,
           verbose: bool = True, url: str = DUMP_URL) -> dict:
    objetivo = f"en:{pais}".lower()
    stats = {"leidas": 0, "del_pais": 0, "guardados": 0,
             "con_texto": 0, "con_tags": 0, "sin_nombre": 0}
    lote: list[dict] = []

    for fila in stream_filas(url):
        stats["leidas"] += 1
        if verbose and stats["leidas"] % 250_000 == 0:
            print(f"  {stats['leidas']:,} filas leídas — "
                  f"{stats['del_pais']} argentinas", flush=True)

        paises = (fila.get("countries_tags") or "").lower()
        if objetivo not in paises:
            continue
        stats["del_pais"] += 1

        ean = _clean(fila.get("code"))
        nombre = _clean(fila.get("product_name"))
        if not ean:
            continue
        if not nombre:
            stats["sin_nombre"] += 1
            continue

        producto = {
            "code": ean,
            "product_name": nombre,
            "brands": _clean(fila.get("brands")),
            "ingredients_text": _clean(fila.get("ingredients_text")),
            "ingredients_tags": _lista(fila.get("ingredients_tags")),
            "ingredients_analysis_tags": _lista(
                fila.get("ingredients_analysis_tags")),
            "labels_tags": _lista(fila.get("labels_tags")),
            "categories_tags": _lista(fila.get("categories_tags")),
            "image_front_small_url": _clean(fila.get("image_small_url")),
        }
        if producto["ingredients_text"]:
            stats["con_texto"] += 1
        if producto["ingredients_tags"]:
            stats["con_tags"] += 1

        db.cache_put(conn, ean, producto)
        lote.append({"ean": ean, "nombre": nombre,
                     "marca": producto["brands"],
                     "categoria": None, "precio_ref": None})

        if len(lote) >= 500:
            stats["guardados"] += db.upsert_catalogo(conn, lote)
            lote.clear()
        if limite and stats["del_pais"] >= limite:
            break

    if lote:
        stats["guardados"] += db.upsert_catalogo(conn, lote)
    conn.commit()
    return stats


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pais", default="argentina")
    parser.add_argument("--limite", type=int, default=None)
    parser.add_argument("--url", default=DUMP_URL)
    args = parser.parse_args(argv)

    conn = db.connect()
    db.init_db(conn)
    try:
        stats = ingest(conn, args.pais, args.limite, url=args.url)
    finally:
        conn.close()

    print(f"\nDump procesado: {stats['leidas']:,} filas leídas, "
          f"{stats['del_pais']:,} de {args.pais}.")
    print(f"Guardados {stats['guardados']:,} productos "
          f"({stats['con_texto']:,} con texto de ingredientes, "
          f"{stats['con_tags']:,} con taxonomía, "
          f"{stats['sin_nombre']:,} descartados sin nombre).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
