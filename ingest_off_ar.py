"""Ingesta del catálogo argentino desde Open Food Facts.

SEPA dice qué se vende en Argentina pero no publica ingredientes, y su portal
bloquea la descarga automatizada. OFF, en cambio, tiene ~16k productos con
`countries_tags = en:argentina` y, en la mayoría, la lista de ingredientes: es
la única fuente que da catálogo argentino Y el dato que necesita la
clasificación por ingredientes.

Dos APIs, muy distintas en rendimiento
--------------------------------------
- `search.openfoodfacts.org` (search-a-licious, la nueva): acepta `page_size`
  de 500 y tolera requests seguidas. Baja el catálogo entero en ~1 minuto.
- `world.openfoodfacts.org/api/v2/search` (la vieja): tope de 100 por página y
  un límite de ~10 req/min que en la práctica devuelve 503 y obliga a esperar.
  Queda como fallback.

La API nueva corta en 10.000 resultados (ventana máxima de Elasticsearch), así
que el catálogo se recorre en dos pasadas ordenadas por código, ascendente y
descendente: con 16k productos, las dos mitades se solapan y cubren todo.

    python ingest_off_ar.py                 # catálogo argentino completo
    python ingest_off_ar.py --max-pages 3   # prueba rápida
    python ingest_off_ar.py --legacy        # forzar la API vieja
"""
from __future__ import annotations

import argparse
import time

import requests

import config
import db

SEARCH_URL = "https://search.openfoodfacts.org/search"
LEGACY_URL = f"{config.OFF_BASE_URL}/api/v2/search"
PAGE_SIZE = 500          # tope práctico de la API nueva
LEGACY_PAGE_SIZE = 100   # tope de la API vieja
MAX_WINDOW = 10_000      # resultados máximos que devuelve una misma consulta


def _clean(value) -> str | None:
    if value is None:
        return None
    s = " ".join(str(value).split())
    return s or None


def fetch_page(session: requests.Session, page: int, country: str,
               sort_by: str | None = None, retries: int = 5) -> tuple[list[dict], int]:
    """Una página de la API nueva. Devuelve (hits, total)."""
    params = {
        "q": f'countries_tags:"en:{country}"',
        "page_size": PAGE_SIZE,
        "page": page,
        "fields": ",".join(config.OFF_FIELDS),
    }
    if sort_by:
        params["sort_by"] = sort_by

    for attempt in range(retries):
        try:
            r = session.get(SEARCH_URL, params=params, timeout=config.OFF_TIMEOUT)
            if r.status_code in (429, 503):
                time.sleep(config.OFF_SEARCH_RETRY_WAIT * (attempt + 1))
                continue
            r.raise_for_status()
            data = r.json()
            return data.get("hits", []), int(data.get("count") or 0)
        except requests.RequestException:
            time.sleep(config.OFF_SEARCH_RETRY_WAIT * (attempt + 1))
    raise RuntimeError(f"OFF (search-a-licious) no respondió para la página {page}")


def fetch_page_legacy(session: requests.Session, page: int, country: str,
                      retries: int = 6) -> tuple[list[dict], int]:
    """Una página de la API v2 vieja. Más lenta, pero sin ventana de 10k."""
    params = {
        "countries_tags_en": country,
        "page_size": LEGACY_PAGE_SIZE,
        "page": page,
        "fields": ",".join(config.OFF_FIELDS),
    }
    for attempt in range(retries):
        try:
            r = session.get(LEGACY_URL, params=params, timeout=config.OFF_TIMEOUT)
            if r.status_code in (429, 503):
                time.sleep(config.OFF_SEARCH_RETRY_WAIT * (attempt + 1))
                continue
            r.raise_for_status()
            data = r.json()
            return data.get("products", []), int(data.get("count", 0))
        except requests.RequestException:
            time.sleep(config.OFF_SEARCH_RETRY_WAIT * (attempt + 1))
    raise RuntimeError(f"OFF (api v2) no respondió para la página {page}")


def _guardar(conn, productos: list[dict], stats: dict) -> None:
    filas = []
    for p in productos:
        ean = _clean(p.get("code"))
        nombre = _clean(p.get("product_name"))
        if not ean:
            continue
        if ean in stats["vistos"]:
            continue
        stats["vistos"].add(ean)
        if not nombre:
            # Sin nombre no hay nada que mostrar ni que buscar.
            stats["sin_nombre"] += 1
            continue
        filas.append({"ean": ean, "nombre": nombre,
                      "marca": _clean(p.get("brands")),
                      "categoria": None, "precio_ref": None})
        db.cache_put(conn, ean, p)
        if _clean(p.get("ingredients_text")):
            stats["con_ingredientes"] += 1
    db.upsert_catalogo(conn, filas)
    stats["productos"] += len(filas)


def ingest(conn, max_pages: int | None = None, country: str = "argentina",
           sleep: float = 0.5, verbose: bool = True, legacy: bool = False) -> dict:
    session = requests.Session()
    session.headers.update({"User-Agent": config.OFF_USER_AGENT})
    stats = {"productos": 0, "con_ingredientes": 0, "sin_nombre": 0,
             "paginas": 0, "vistos": set()}

    if legacy:
        page = 1
        while True:
            productos, total = fetch_page_legacy(session, page, country)
            if not productos:
                break
            _guardar(conn, productos, stats)
            stats["paginas"] = page
            if verbose:
                print(f"  [v2] página {page} — {stats['productos']} productos")
            if max_pages and page >= max_pages:
                break
            if page * LEGACY_PAGE_SIZE >= total:
                break
            page += 1
            time.sleep(config.OFF_SEARCH_SLEEP_SECONDS)
        stats.pop("vistos")
        return stats

    # Pasada ascendente y descendente por código: entre las dos se cubre todo
    # lo que la ventana de 10.000 deja afuera en una sola dirección.
    for sort_by in ("code", "-code"):
        page = 1
        while True:
            hits, total = fetch_page(session, page, country, sort_by)
            if not hits:
                break
            _guardar(conn, hits, stats)
            stats["paginas"] += 1

            if verbose and page % 5 == 0:
                print(f"  [{sort_by}] página {page} — {stats['productos']} "
                      f"productos, {stats['con_ingredientes']} con ingredientes")

            if max_pages and stats["paginas"] >= max_pages:
                break
            if page * PAGE_SIZE >= min(total, MAX_WINDOW):
                break
            page += 1
            time.sleep(sleep)

        conn.commit()
        if max_pages and stats["paginas"] >= max_pages:
            break
        # La API topea `count` en 10.000, asi que un total igual a la ventana
        # no significa "entra entero": significa "hay al menos esto". Solo se
        # saltea la segunda pasada cuando el catalogo es estrictamente menor.
        if total and total < MAX_WINDOW:
            break

    faltan = max(0, total - len(stats["vistos"])) if total else 0
    stats["total_reportado"] = total
    stats["faltantes_estimados"] = faltan
    stats.pop("vistos")
    return stats


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-pages", type=int, default=None)
    parser.add_argument("--country", default="argentina")
    parser.add_argument("--sleep", type=float, default=0.5)
    parser.add_argument("--legacy", action="store_true",
                        help="usar la API v2 vieja (lenta, sin ventana de 10k)")
    args = parser.parse_args(argv)

    conn = db.connect()
    db.init_db(conn)
    try:
        stats = ingest(conn, args.max_pages, args.country, args.sleep,
                       legacy=args.legacy)
    finally:
        conn.close()

    print(f"\nCatálogo {args.country}: {stats['productos']} productos nuevos "
          f"({stats['con_ingredientes']} con ingredientes, "
          f"{stats['sin_nombre']} sin nombre descartados)")
    if stats.get("faltantes_estimados"):
        print(f"OFF reporta {stats['total_reportado']}; quedaron "
              f"~{stats['faltantes_estimados']} fuera de las dos pasadas. "
              f"Corré con --legacy para completar.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
