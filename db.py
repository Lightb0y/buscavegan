"""Acceso a SQLite: esquema, conexión y helpers de cache."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS catalogo (
    ean         TEXT PRIMARY KEY,
    nombre      TEXT NOT NULL,
    marca       TEXT,
    categoria   TEXT,
    precio_ref  REAL,
    actualizado TEXT
);

CREATE TABLE IF NOT EXISTS off_cache (
    ean         TEXT PRIMARY KEY,
    found       INTEGER NOT NULL,   -- 1 si OFF conoce el producto
    payload     TEXT,               -- JSON con los fields pedidos
    consultado  TEXT NOT NULL       -- ISO-8601 UTC
);

CREATE TABLE IF NOT EXISTS productos (
    ean              TEXT PRIMARY KEY,
    nombre           TEXT NOT NULL,
    marca            TEXT,
    categoria        TEXT,
    estado           TEXT NOT NULL,
    fuente_decision  TEXT NOT NULL,
    confianza        REAL,
    ingredients_text TEXT,
    imagen_url       TEXT,
    precio_ref       REAL,
    actualizado      TEXT,
    motivo           TEXT      -- explicacion legible que se muestra en la app
);

CREATE TABLE IF NOT EXISTS revision_pendiente (
    ean       TEXT PRIMARY KEY,
    nombre    TEXT,
    marca     TEXT,
    motivo    TEXT,
    confianza REAL,
    creado    TEXT
);

CREATE INDEX IF NOT EXISTS idx_productos_estado ON productos(estado);
CREATE INDEX IF NOT EXISTS idx_productos_categoria ON productos(categoria);
"""

FTS_SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS productos_fts
USING fts5(nombre, marca, content='productos', content_rowid='rowid');
"""


def connect(path=None) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path or config.DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    _migrar(conn)
    try:
        conn.executescript(FTS_SCHEMA)
    except sqlite3.OperationalError:
        # SQLite compilado sin FTS5: la app cae a LIKE. No es fatal.
        pass
    conn.commit()


def _migrar(conn: sqlite3.Connection) -> None:
    """Altas de columnas sobre bases ya creadas por una version anterior."""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(productos)")}
    if "motivo" not in cols:
        conn.execute("ALTER TABLE productos ADD COLUMN motivo TEXT")


def has_fts5(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE name='productos_fts'"
    ).fetchone()
    return row is not None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --- cache de OFF ----------------------------------------------------------

def cache_get(conn: sqlite3.Connection, ean: str, ttl_days: int | None = None):
    """Devuelve el payload cacheado si existe y no venció, si no None.

    Un miss de OFF (found=0) también se cachea: evita repreguntar por EANs que
    OFF no conoce en cada refresco.
    """
    ttl = config.OFF_CACHE_TTL_DAYS if ttl_days is None else ttl_days
    row = conn.execute(
        "SELECT found, payload, consultado FROM off_cache WHERE ean = ?", (ean,)
    ).fetchone()
    if row is None:
        return None
    try:
        consultado = datetime.fromisoformat(row["consultado"])
    except ValueError:
        return None
    if datetime.now(timezone.utc) - consultado > timedelta(days=ttl):
        return None
    if not row["found"]:
        return {"found": False, "product": None}
    return {"found": True, "product": json.loads(row["payload"] or "{}")}


def cache_put(conn: sqlite3.Connection, ean: str, product: dict | None) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO off_cache (ean, found, payload, consultado)"
        " VALUES (?, ?, ?, ?)",
        (
            ean,
            1 if product else 0,
            json.dumps(product, ensure_ascii=False) if product else None,
            now_iso(),
        ),
    )


def upsert_catalogo(conn: sqlite3.Connection, rows: Iterable[dict[str, Any]]) -> int:
    n = 0
    for r in rows:
        conn.execute(
            "INSERT OR REPLACE INTO catalogo"
            " (ean, nombre, marca, categoria, precio_ref, actualizado)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (
                r["ean"],
                r["nombre"],
                r.get("marca"),
                r.get("categoria"),
                r.get("precio_ref"),
                now_iso(),
            ),
        )
        n += 1
    conn.commit()
    return n
