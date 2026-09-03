"""Ingesta del catálogo SEPA / Precios Claros hacia la tabla `catalogo`.

El portal oficial (datos.produccion.gob.ar) bloquea acceso automatizado, así que
este módulo NO descarga: consume un CSV ya bajado a mano o vía el mirror de
Kaggle (ver SPEC.md §2.1) y lo normaliza.

    python ingest_sepa.py --csv data/raw/sepa_productos.csv
"""
from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd

import config
import db

# SEPA cambia nombres de columna entre publicaciones; se prueban alias en orden.
COLUMN_ALIASES = {
    "ean": ["producto_id", "id_producto", "ean", "codigo_barras", "productos_ean"],
    "nombre": ["productos_descripcion", "nombre", "producto_nombre", "descripcion",
               "nombre_producto"],
    "marca": ["productos_marca", "marca", "producto_marca"],
    "categoria": ["categoria", "categorias", "rubro", "productos_categoria"],
    "precio_ref": ["productos_precio_lista", "precio", "precio_lista",
                   "productos_precio_unitario_promo1"],
}

_EAN_RE = re.compile(r"^\d{8,14}$")


def strip_accents(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


def normalize_ean(value) -> str | None:
    """Devuelve el EAN como string de dígitos, o None si no es plausible.

    Los CSV suelen traer el EAN como float (7.79e+12) o con ceros a la
    izquierda comidos: se completa a 13 dígitos solo cuando tiene 11 o 12,
    para no romper los EAN-8 que son códigos válidos por sí mismos.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    s = str(value).strip()
    if s.endswith(".0"):
        s = s[:-2]
    if "e" in s.lower():  # notación científica: el EAN ya perdió precisión
        try:
            s = f"{int(float(s)):d}"
        except (ValueError, OverflowError):
            return None
    s = re.sub(r"\D", "", s)
    if not _EAN_RE.match(s):
        return None
    if len(s) in (11, 12):
        # UPC-A (12) o un EAN-13 al que le comieron el cero inicial.
        s = s.zfill(13)
    return s


def clean_text(value) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    s = re.sub(r"\s+", " ", str(value)).strip()
    return s or None


def resolve_columns(df: pd.DataFrame) -> dict[str, str]:
    """Mapea campo canónico -> nombre real de columna en el CSV."""
    lookup = {strip_accents(c).lower().strip(): c for c in df.columns}
    resolved: dict[str, str] = {}
    for field, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in lookup:
                resolved[field] = lookup[alias]
                break
    return resolved


def load_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, low_memory=False, on_bad_lines="skip")


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    cols = resolve_columns(df)
    missing = [f for f in ("ean", "nombre") if f not in cols]
    if missing:
        raise SystemExit(
            f"El CSV no tiene columnas reconocibles para: {', '.join(missing)}.\n"
            f"Columnas presentes: {list(df.columns)[:20]}"
        )

    out = pd.DataFrame()
    out["ean"] = df[cols["ean"]].map(normalize_ean)
    out["nombre"] = df[cols["nombre"]].map(clean_text)
    for field in ("marca", "categoria"):
        out[field] = df[cols[field]].map(clean_text) if field in cols else None
    if "precio_ref" in cols:
        out["precio_ref"] = pd.to_numeric(
            df[cols["precio_ref"]].astype(str).str.replace(",", ".", regex=False),
            errors="coerce",
        )
    else:
        out["precio_ref"] = None

    out = out.dropna(subset=["ean", "nombre"])
    # SEPA trae una fila por producto/sucursal/día: nos quedamos con una por EAN.
    out = out.sort_values("precio_ref").drop_duplicates(subset=["ean"], keep="first")
    return out.reset_index(drop=True)


def ingest(csv_path: Path, conn=None) -> int:
    own = conn is None
    conn = conn or db.connect()
    try:
        db.init_db(conn)
        df = normalize(load_csv(csv_path))
        return db.upsert_catalogo(conn, df.to_dict("records"))
    finally:
        if own:
            conn.close()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--csv", type=Path, required=True,
        help="CSV de SEPA ya descargado (el portal oficial bloquea bots)",
    )
    args = parser.parse_args(argv)
    if not args.csv.exists():
        print(f"No existe {args.csv}. Bajá el dataset primero (SPEC.md §2.1).",
              file=sys.stderr)
        return 1
    n = ingest(args.csv)
    print(f"Catálogo actualizado: {n} productos únicos por EAN en {config.DB_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
