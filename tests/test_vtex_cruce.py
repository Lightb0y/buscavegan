"""Test del cruce EAN -> supermercado dentro de build_db.build().

No depende de red: escribe filas directamente en `catalogo` y `vtex_catalogo`
sobre una base temporal y corre el pipeline completo, para asegurar que la
columna `cadenas_confirmadas` quede bien poblada sin tocar `estado` ni
`fuente_decision` (el cruce es una señal aparte, no una capa de clasificación).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import build_db  # noqa: E402
import db as _db  # noqa: E402


def _conn(tmp_path):
    conn = _db.connect(tmp_path / "vtex_cruce.db")
    _db.init_db(conn)
    return conn


def test_cruce_marca_las_cadenas_confirmadas(tmp_path):
    conn = _conn(tmp_path)
    _db.upsert_catalogo(conn, [
        {"ean": "1111111111111", "nombre": "Aceite de girasol", "marca": "X"},
        {"ean": "2222222222222", "nombre": "Producto sin confirmar", "marca": "Y"},
    ])
    conn.execute(
        "INSERT INTO vtex_catalogo (ean, cadena, nombre, actualizado)"
        " VALUES ('1111111111111','carrefour','Aceite de girasol', '2026-01-01')")
    conn.execute(
        "INSERT INTO vtex_catalogo (ean, cadena, nombre, actualizado)"
        " VALUES ('1111111111111','vea','Aceite de girasol', '2026-01-01')")
    conn.commit()

    stats = build_db.build(conn, verbose=False)
    assert stats["confirmados_supermercado"] == 1

    fila1 = conn.execute(
        "SELECT cadenas_confirmadas FROM productos WHERE ean='1111111111111'"
    ).fetchone()
    cadenas = set(fila1["cadenas_confirmadas"].split(","))
    assert cadenas == {"carrefour", "vea"}

    fila2 = conn.execute(
        "SELECT cadenas_confirmadas FROM productos WHERE ean='2222222222222'"
    ).fetchone()
    assert fila2["cadenas_confirmadas"] is None
    conn.close()


def test_el_cruce_no_toca_estado_ni_fuente(tmp_path):
    # La confirmación en un supermercado es evidencia de que el producto
    # EXISTE, no de si es vegano: no debe pisar la clasificación de ninguna
    # capa, ni siquiera para un producto que de otro modo quedaría `revisar`.
    conn = _conn(tmp_path)
    _db.upsert_catalogo(conn, [
        {"ean": "3333333333333", "nombre": "Producto Sin Pistas Xyz", "marca": "Z"},
    ])
    conn.execute(
        "INSERT INTO vtex_catalogo (ean, cadena, nombre, actualizado)"
        " VALUES ('3333333333333','disco','Producto Sin Pistas Xyz', '2026-01-01')")
    conn.commit()

    build_db.build(conn, verbose=False)
    fila = conn.execute(
        "SELECT estado, fuente_decision, cadenas_confirmadas FROM productos"
        " WHERE ean='3333333333333'").fetchone()
    assert fila["estado"] == "revisar"
    assert fila["fuente_decision"] == "sin_datos"
    assert fila["cadenas_confirmadas"] == "disco"
    conn.close()


def test_sin_datos_de_vtex_todo_queda_sin_confirmar(tmp_path):
    conn = _conn(tmp_path)
    _db.upsert_catalogo(conn, [
        {"ean": "4444444444444", "nombre": "Producto cualquiera", "marca": "W"},
    ])
    stats = build_db.build(conn, verbose=False)
    assert stats["confirmados_supermercado"] == 0
    conn.close()
