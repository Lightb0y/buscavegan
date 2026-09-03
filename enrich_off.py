"""Enriquecimiento contra Open Food Facts, con cache persistente y backoff.

OFF no pide API key para lectura, pero sí un User-Agent propio y descriptivo, y
responde 503 cuando se abusa del rate limit. Este módulo:

  - consulta solo EANs que no están en cache o cuyo cache venció (TTL),
  - duerme entre requests y reintenta con backoff exponencial ante 503/429,
  - cachea también los misses, para no repreguntar en cada refresco.

    python enrich_off.py --limit 500
"""
from __future__ import annotations

import argparse
import time
from typing import Iterable, Sequence

import requests

import config
import db


class OFFClient:
    def __init__(self, session: requests.Session | None = None, sleep: float | None = None):
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": config.OFF_USER_AGENT})
        self.sleep = config.OFF_SLEEP_SECONDS if sleep is None else sleep
        self.requests_made = 0

    def fetch(self, ean: str) -> dict | None:
        """Devuelve el producto de OFF, o None si OFF no lo conoce.

        Lanza RuntimeError si tras los reintentos el servicio sigue caído: es
        distinto de "no existe" y no se debe cachear como miss.
        """
        url = f"{config.OFF_BASE_URL}/api/v2/product/{ean}.json"
        params = {"fields": ",".join(config.OFF_FIELDS)}
        last_error: str | None = None

        for attempt in range(config.OFF_MAX_RETRIES):
            if self.sleep:
                time.sleep(self.sleep)
            try:
                resp = self.session.get(url, params=params, timeout=config.OFF_TIMEOUT)
            except requests.RequestException as exc:
                last_error = str(exc)
            else:
                self.requests_made += 1
                if resp.status_code == 404:
                    return None
                if resp.status_code in (429, 503):
                    last_error = f"HTTP {resp.status_code}"
                elif resp.ok:
                    payload = resp.json()
                    if payload.get("status") == 1 and payload.get("product"):
                        return payload["product"]
                    return None
                else:
                    last_error = f"HTTP {resp.status_code}"
            time.sleep(config.OFF_BACKOFF_BASE ** attempt)

        raise RuntimeError(f"OFF no responde para {ean}: {last_error}")


def pending_eans(conn, eans: Sequence[str], ttl_days: int | None = None) -> list[str]:
    """EANs que hay que consultar: sin cache o con cache vencido."""
    return [e for e in eans if db.cache_get(conn, e, ttl_days) is None]


def enrich(conn, eans: Iterable[str], client: OFFClient | None = None,
           ttl_days: int | None = None, verbose: bool = True) -> dict[str, int]:
    """Puebla `off_cache` para los EANs dados. Devuelve un resumen de la corrida."""
    eans = list(dict.fromkeys(eans))  # dedup preservando orden
    client = client or OFFClient()
    todo = pending_eans(conn, eans, ttl_days)
    stats = {"total": len(eans), "cacheados": len(eans) - len(todo),
             "consultados": 0, "encontrados": 0, "errores": 0}

    for i, ean in enumerate(todo, 1):
        try:
            product = client.fetch(ean)
        except RuntimeError as exc:
            # No se cachea: un fallo de servicio no es evidencia de ausencia.
            stats["errores"] += 1
            if verbose:
                print(f"  ! {exc}")
            continue
        db.cache_put(conn, ean, product)
        stats["consultados"] += 1
        stats["encontrados"] += 1 if product else 0
        if verbose and i % 25 == 0:
            conn.commit()
            print(f"  {i}/{len(todo)} consultados, {stats['encontrados']} encontrados")
    conn.commit()
    return stats


def catalog_eans(conn, limit: int | None = None) -> list[str]:
    sql = "SELECT ean FROM catalogo ORDER BY ean"
    if limit:
        sql += f" LIMIT {int(limit)}"
    return [r["ean"] for r in conn.execute(sql)]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None,
                        help="máximo de EANs del catálogo a enriquecer")
    parser.add_argument("--ttl-days", type=int, default=None,
                        help=f"TTL del cache (default {config.OFF_CACHE_TTL_DAYS})")
    args = parser.parse_args(argv)

    conn = db.connect()
    db.init_db(conn)
    try:
        eans = catalog_eans(conn, args.limit)
        if not eans:
            print("El catálogo está vacío. Corré ingest_sepa.py primero.")
            return 1
        stats = enrich(conn, eans, ttl_days=args.ttl_days)
    finally:
        conn.close()
    print(f"OFF: {stats['consultados']} consultados "
          f"({stats['cacheados']} servidos desde cache), "
          f"{stats['encontrados']} encontrados, {stats['errores']} errores")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
