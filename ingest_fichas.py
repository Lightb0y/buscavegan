"""Ficha nutricional de las cadenas de Cencosud (Vea, Jumbo y Disco).

Por qué existe
--------------
El veredicto por lista de ingredientes es mucho mejor que el veredicto por
nombre: el nombre comercial omite y a veces miente, mientras que la lista es
la declaración legal de lo que el producto tiene adentro. Pero 6.365 de los
10.395 productos del catálogo no tienen ingredientes cargados en Open Food
Facts, y por eso miles quedan en `revisar` o se resuelven adivinando por el
nombre.

Vea, Jumbo y Disco publican en su API de VTEX la ficha completa del producto:

- `Ingredientes` — la lista real, tal como está en el envase.
- `Trazas` — en un campo **aparte**, que es justo la distinción que nos
  importa: "puede contener leche" no es lo mismo que "contiene leche".
- `Sellos` — certificaciones, entre las que hay un `vegan` y un `vegetarian`
  explícitos.

Carrefour y Día quedan afuera: se verificó que su VTEX no expone estos campos
(Carrefour solo trae una descripción comercial, Día ni eso).

Cómo se consulta
----------------
No hace falta recosechar el catálogo entero: VTEX permite filtrar por EAN
(`fq=alternateIds_Ean:<ean>`), así que se piden de a uno solo los productos
que ya sabemos que están en esas cadenas y a los que les falta información.

Se guarda también el resultado vacío (una ficha sin ingredientes) para no
volver a preguntar por lo mismo en la próxima corrida: el proceso es
reanudable y se puede cortar en cualquier momento.

    python ingest_fichas.py                # todo lo que falte
    python ingest_fichas.py --limite 200   # prueba corta
"""
from __future__ import annotations

import argparse
import ast
import re
import time

import requests

import config
import db
from ingest_vtex import CADENAS, NOMBRE_LEGIBLE

# Solo las cadenas de Cencosud publican la ficha.
CADENAS_CON_FICHA = ("disco", "jumbo", "vea")

CAMPO_INGREDIENTES = "Ingredientes"
CAMPO_TRAZAS = "Trazas"
CAMPO_SELLOS = "Sellos"

SELLO_VEGANO = "vegan"
SELLO_VEGETARIANO = "vegetarian"

# VTEX devuelve estos campos como una lista con UN string adentro, y ese string
# trae los ítems entrecomillados: ["'harina de trigo', 'sal'"].
_ENTRECOMILLADO = re.compile(r"'([^']*)'")


def texto_de_campo(celdas) -> str | None:
    """Convierte ["'harina de trigo', 'sal'"] en "harina de trigo, sal"."""
    if not celdas:
        return None
    crudo = " ".join(str(c) for c in celdas).strip()
    if not crudo:
        return None
    items = [t.strip() for t in _ENTRECOMILLADO.findall(crudo) if t.strip()]
    if items:
        return ", ".join(items)
    # Algunos productos traen el texto plano, sin comillas.
    return crudo or None


def codigos_de_sellos(celdas) -> str | None:
    """Extrae los `certification_type_code` de la estructura de sellos.

    Vienen como el `repr` de una lista de diccionarios de Python, no como
    JSON, así que hay que leerlos con `ast.literal_eval` y no con `json.loads`.
    """
    codigos: set[str] = set()
    for celda in celdas or []:
        try:
            sellos = ast.literal_eval(str(celda))
        except (ValueError, SyntaxError):
            continue
        if not isinstance(sellos, list):
            continue
        for sello in sellos:
            if isinstance(sello, dict) and sello.get("certification_type_code"):
                codigos.add(str(sello["certification_type_code"]))
    return ",".join(sorted(codigos)) or None


def extraer_ficha(producto: dict) -> dict:
    return {
        "ingredientes": texto_de_campo(producto.get(CAMPO_INGREDIENTES)),
        "trazas": texto_de_campo(producto.get(CAMPO_TRAZAS)),
        "sellos": codigos_de_sellos(producto.get(CAMPO_SELLOS)),
    }


def pedir_ficha(session: requests.Session, base_url: str, ean: str) -> dict | None:
    """Devuelve la ficha del producto en esa cadena, o None si no está."""
    try:
        r = session.get(f"{base_url}/api/catalog_system/pub/products/search",
                        params={"fq": f"alternateIds_Ean:{ean}"},
                        timeout=config.VTEX_TIMEOUT)
    except requests.RequestException:
        return None
    if r.status_code not in (200, 206):
        return None
    try:
        productos = r.json()
    except ValueError:
        return None
    if not productos:
        return None
    return extraer_ficha(productos[0])


def pendientes(conn, limite: int | None = None) -> list[tuple[str, str]]:
    """(ean, cadena) de lo que conviene consultar y todavía no se consultó.

    Se prioriza lo que más falta hace: productos sin ingredientes, o cuyo
    veredicto salió de adivinar por el nombre o del modelo automático.
    """
    marcadores = ",".join("?" * len(CADENAS_CON_FICHA))
    sql = f"""
        SELECT p.ean, MIN(v.cadena) AS cadena
        FROM productos p
        JOIN vtex_catalogo v ON v.ean = p.ean
        LEFT JOIN vtex_ficha f ON f.ean = p.ean
        WHERE v.cadena IN ({marcadores})
          AND f.ean IS NULL
          AND (p.ingredients_text IS NULL OR p.ingredients_text = ''
               OR p.fuente_decision IN ('heuristica', 'ml', 'sin_datos'))
        GROUP BY p.ean
    """
    if limite:
        sql += f" LIMIT {int(limite)}"
    return [(r["ean"], r["cadena"]) for r in conn.execute(sql, CADENAS_CON_FICHA)]


def ingest(conn, limite: int | None = None, sleep: float | None = None,
           verbose: bool = True) -> dict[str, int]:
    sleep = config.VTEX_SLEEP_SECONDS if sleep is None else sleep
    session = requests.Session()
    session.headers.update({"User-Agent": config.OFF_USER_AGENT})

    cola = pendientes(conn, limite)
    if verbose:
        print(f"{len(cola)} productos a consultar")

    stats = {"consultados": 0, "con_ingredientes": 0, "con_sello_vegano": 0,
             "sin_ficha": 0}

    for i, (ean, cadena) in enumerate(cola, 1):
        ficha = pedir_ficha(session, CADENAS[cadena], ean)
        stats["consultados"] += 1
        if ficha is None:
            ficha = {"ingredientes": None, "trazas": None, "sellos": None}
            stats["sin_ficha"] += 1
        if ficha["ingredientes"]:
            stats["con_ingredientes"] += 1
        if ficha["sellos"] and SELLO_VEGANO in ficha["sellos"].split(","):
            stats["con_sello_vegano"] += 1

        # Se guarda también la ficha vacía: así la próxima corrida no vuelve a
        # preguntar por un producto que ya sabemos que no la tiene.
        conn.execute(
            "INSERT OR REPLACE INTO vtex_ficha"
            " (ean, cadena, ingredientes, trazas, sellos, actualizado)"
            " VALUES (?,?,?,?,?,?)",
            (ean, cadena, ficha["ingredientes"], ficha["trazas"],
             ficha["sellos"], db.now_iso()))
        if i % 25 == 0:
            conn.commit()
            if verbose:
                print(f"  {i}/{len(cola)} — {stats['con_ingredientes']} con "
                      f"ingredientes, {stats['con_sello_vegano']} con sello vegano")
        time.sleep(sleep)

    conn.commit()
    return stats


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limite", type=int, default=None,
                        help="cuántos productos consultar (por defecto, todos)")
    parser.add_argument("--sleep", type=float, default=None)
    args = parser.parse_args(argv)

    conn = db.connect()
    db.init_db(conn)
    try:
        stats = ingest(conn, args.limite, args.sleep)
    finally:
        conn.close()

    print(f"\nConsultados        : {stats['consultados']}")
    print(f"Con ingredientes   : {stats['con_ingredientes']}")
    print(f"Con sello vegano   : {stats['con_sello_vegano']}")
    print(f"Sin ficha          : {stats['sin_ficha']}")
    print(f"\nCadenas con ficha: "
          f"{', '.join(NOMBRE_LEGIBLE[c] for c in CADENAS_CON_FICHA)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
