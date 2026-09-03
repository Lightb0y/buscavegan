"""Cruce contra el catálogo público de las grandes cadenas de supermercado.

Por qué existe
---------------
OFF es colaborativo: el país lo carga quien sube el producto, y eso deja
ruido (ver `relevancia.py` — 20% del catálogo tenía el nombre en un alfabeto
que ningún supermercado argentino usa). El filtro de alfabeto agarra el caso
extremo, pero no confirma positivamente que un producto **se venda hoy** acá.

Carrefour, Vea, Día, Jumbo y Disco corren sobre VTEX, una plataforma de
e-commerce que expone su catálogo por una API pública y sin autenticación (es
la misma que usa el propio sitio para mostrar productos). Da EAN real, marca,
categoría y precio — evidencia directa de "esto está en la góndola", más
fuerte que cualquier inferencia sobre el tag de país de OFF.

Coto queda afuera: no corre VTEX, usa una plataforma propia.

Cómo se cosecha
----------------
Cada cadena publica su árbol de categorías completo en un solo request
(`/api/catalog_system/pub/category/tree/{profundidad}`). Se recorre en
memoria, quedándose con las ramas de alimentos (Almacén, Bebidas, Lácteos...:
ver `PALABRAS_RELEVANTES` — cada cadena nombra sus categorías distinto, así
que el filtro es por palabra clave, no por id ni nombre exacto).

Para cada nodo del árbol, el filtro de categoría de VTEX (`fq=C:...`) necesita
el camino completo de ids desde la raíz, no alcanza con el id de la hoja. Y
cada consulta tiene un tope real de 2.500 resultados: si un nodo lo supera, en
vez de cosecharlo se baja a sus hijos (la consulta en un nodo ya incluye a
todos sus descendientes, así que no hace falta bajar si entra entero).

    python ingest_vtex.py                     # las 5 cadenas
    python ingest_vtex.py --cadena carrefour   # una sola, para probar
    python ingest_vtex.py --max-nodos 5        # prueba corta
"""
from __future__ import annotations

import argparse
import time
import unicodedata

import requests

import config
import db

CADENAS = {
    "carrefour": "https://www.carrefour.com.ar",
    "vea": "https://www.vea.com.ar",
    "dia": "https://diaonline.supermercadosdia.com.ar",
    "jumbo": "https://www.jumbo.com.ar",
    "disco": "https://www.disco.com.ar",
}

NOMBRE_LEGIBLE = {"carrefour": "Carrefour", "vea": "Vea", "dia": "Día",
                  "jumbo": "Jumbo", "disco": "Disco"}

PALABRAS_RELEVANTES = [
    "almacen", "desayuno", "merienda", "bebida", "lacteo", "queso",
    "fiambre", "carne", "pescado", "marisco", "fruta", "verdura",
    "panaderia", "congelado", "fresco",
]


def _normalizar(texto: str) -> str:
    t = unicodedata.normalize("NFD", texto or "")
    return "".join(c for c in t if unicodedata.category(c) != "Mn").lower()


def es_rama_de_alimentos(nombre: str) -> bool:
    n = _normalizar(nombre)
    return any(p in n for p in PALABRAS_RELEVANTES)


def obtener_arbol(session: requests.Session, base_url: str,
                  profundidad: int = 5) -> list[dict]:
    r = session.get(f"{base_url}/api/catalog_system/pub/category/tree/{profundidad}",
                    timeout=config.VTEX_TIMEOUT)
    r.raise_for_status()
    return r.json()


def _total(session: requests.Session, base_url: str, fq: str) -> int:
    """Cuántos productos hay en total para ese filtro (sin traerlos)."""
    r = session.get(f"{base_url}/api/catalog_system/pub/products/search",
                    params={"fq": fq, "_from": 0, "_to": 0},
                    timeout=config.VTEX_TIMEOUT)
    if not r.ok:
        return 0
    rango = r.headers.get("resources", "0-0/0")
    try:
        return int(rango.rsplit("/", 1)[-1])
    except (ValueError, IndexError):
        return 0


def nodos_a_cosechar(session: requests.Session, base_url: str,
                     arbol: list[dict]) -> list[tuple[str, int]]:
    """Recorre el árbol de categorías y devuelve las unidades a paginar:
    [(filtro_vtex, total), ...]. Solo baja a los hijos de un nodo cuando su
    total supera la ventana máxima de VTEX (2500)."""
    resultado: list[tuple[str, int]] = []

    def visitar(nodo: dict, camino: list[int]) -> None:
        fq = "C:" + "/".join(str(i) for i in camino)
        total = _total(session, base_url, fq)
        if total == 0:
            return
        hijos = nodo.get("children") or []
        if total <= config.VTEX_VENTANA_MAXIMA or not hijos:
            resultado.append((fq, min(total, config.VTEX_VENTANA_MAXIMA)))
            return
        for hijo in hijos:
            visitar(hijo, camino + [hijo["id"]])

    for nodo in arbol:
        if es_rama_de_alimentos(nodo.get("name", "")):
            visitar(nodo, [nodo["id"]])

    return resultado


def extraer_items(producto: dict) -> list[dict]:
    """Un producto VTEX agrupa varias presentaciones (SKUs/`items`), cada una
    con su propio EAN — se extraen todas, no solo la primera."""
    categorias = producto.get("categories") or [""]
    categoria = categorias[-1].strip("/").split("/")[-1] or None

    filas = []
    for item in producto.get("items", []):
        ean = (item.get("ean") or "").strip()
        if not ean.isdigit():
            continue
        precio = None
        for vendedor in item.get("sellers") or []:
            oferta = vendedor.get("commertialOffer") or {}
            if oferta.get("Price"):
                precio = oferta["Price"]
                break
        filas.append({
            "ean": ean,
            "nombre": producto.get("productName"),
            "marca": producto.get("brand") or None,
            "categoria": categoria,
            "precio": precio,
        })
    return filas


def cosechar_nodo(session: requests.Session, base_url: str, cadena: str,
                  fq: str, total: int, conn, sleep: float) -> int:
    guardados = 0
    for offset in range(0, total, config.VTEX_PAGE_SIZE):
        hasta = min(offset + config.VTEX_PAGE_SIZE, total) - 1
        r = session.get(f"{base_url}/api/catalog_system/pub/products/search",
                        params={"fq": fq, "_from": offset, "_to": hasta},
                        timeout=config.VTEX_TIMEOUT)
        if r.status_code not in (200, 206):
            break
        productos = r.json()
        if not productos:
            break

        ahora = db.now_iso()
        for p in productos:
            for fila in extraer_items(p):
                conn.execute(
                    "INSERT OR REPLACE INTO vtex_catalogo"
                    " (ean, cadena, nombre, marca, categoria, precio, actualizado)"
                    " VALUES (?,?,?,?,?,?,?)",
                    (fila["ean"], cadena, fila["nombre"], fila["marca"],
                     fila["categoria"], fila["precio"], ahora))
                guardados += 1
        conn.commit()
        time.sleep(sleep)
    return guardados


def ingest(conn, cadenas: list[str] | None = None, max_nodos: int | None = None,
           sleep: float | None = None, verbose: bool = True) -> dict[str, int]:
    cadenas = cadenas or list(CADENAS)
    sleep = config.VTEX_SLEEP_SECONDS if sleep is None else sleep
    session = requests.Session()
    session.headers.update({"User-Agent": config.OFF_USER_AGENT})

    stats: dict[str, int] = {}
    for nombre in cadenas:
        base_url = CADENAS[nombre]
        if verbose:
            print(f"[{nombre}] bajando árbol de categorías...")
        arbol = obtener_arbol(session, base_url)
        nodos = nodos_a_cosechar(session, base_url, arbol)
        if max_nodos:
            nodos = nodos[:max_nodos]
        if verbose:
            estimado = sum(t for _, t in nodos)
            print(f"[{nombre}] {len(nodos)} nodos a cosechar "
                  f"(~{estimado} productos estimados)")

        guardados = 0
        for i, (fq, total) in enumerate(nodos, 1):
            guardados += cosechar_nodo(session, base_url, nombre, fq, total,
                                       conn, sleep)
            if verbose and i % 10 == 0:
                print(f"[{nombre}] {i}/{len(nodos)} nodos — {guardados} EANs")
        stats[nombre] = guardados
        if verbose:
            print(f"[{nombre}] listo: {guardados} EANs guardados")

    return stats


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cadena", choices=sorted(CADENAS), action="append",
                        dest="cadenas", help="repetible; por defecto, las 5")
    parser.add_argument("--max-nodos", type=int, default=None)
    parser.add_argument("--sleep", type=float, default=None)
    args = parser.parse_args(argv)

    conn = db.connect()
    db.init_db(conn)
    try:
        stats = ingest(conn, args.cadenas, args.max_nodos, args.sleep)
    finally:
        conn.close()

    total = sum(stats.values())
    print(f"\nTotal: {total} EANs confirmados en {len(stats)} cadena(s)")
    for cadena, n in stats.items():
        print(f"  {NOMBRE_LEGIBLE.get(cadena, cadena):10} {n:6}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
