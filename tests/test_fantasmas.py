"""Tests del descarte de fichas fantasma.

El riesgo de este filtro no es dejar entrar basura sino sacar productos
buenos: cortar solo por "no tiene categoría" se llevaba puestos 1.608
productos bien clasificados. Por eso casi todos los tests de acá verifican
lo que NO se debe excluir.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import build_db  # noqa: E402
import db as _db  # noqa: E402
import relevancia  # noqa: E402


# --- el criterio, aislado -------------------------------------------------

def test_sin_ninguna_senal_es_fantasma():
    assert relevancia.es_ficha_fantasma([], None, None, "sin_datos") is True
    assert relevancia.es_ficha_fantasma(None, "", None, "heuristica") is True


@pytest.mark.parametrize("cats,ingr,cadenas,fuente,por_que", [
    (["en:snacks"], None, None, "sin_datos", "tiene categoría"),
    ([], "harina de trigo, sal", None, "sin_datos", "tiene ingredientes"),
    ([], None, "disco", "sin_datos", "está en una góndola real"),
    ([], None, None, "ingredientes", "veredicto por ingredientes"),
    ([], None, None, "sello_super", "sello vegano certificado"),
    ([], None, None, "certificacion_oficial", "certificación de ANMAT"),
    ([], None, None, "off_label", "declarado por el fabricante"),
])
def test_una_sola_senal_alcanza_para_quedarse(cats, ingr, cadenas, fuente, por_que):
    assert relevancia.es_ficha_fantasma(cats, ingr, cadenas, fuente) is False, por_que


def test_adivinar_por_el_nombre_no_es_evidencia():
    # Un veredicto sacado del nombre comercial no alcanza para afirmar que el
    # producto exista: si no hay ninguna otra señal, sigue siendo una ficha
    # fantasma sobre la que opinamos.
    assert relevancia.es_ficha_fantasma([], None, None, "heuristica") is True
    assert relevancia.es_ficha_fantasma([], None, None, "ml") is True


# --- integrado en el pipeline --------------------------------------------

def _conn(tmp_path):
    conn = _db.connect(tmp_path / "fantasmas.db")
    _db.init_db(conn)
    return conn


def _con_payload(conn, ean, cats):
    conn.execute(
        "INSERT OR REPLACE INTO off_cache (ean, found, payload, consultado)"
        " VALUES (?,1,?,?)",
        (ean, json.dumps({"code": ean, "categories_tags": cats}), "2026-01-01"))


def test_el_pipeline_saca_la_ficha_fantasma(tmp_path):
    conn = _conn(tmp_path)
    _db.upsert_catalogo(conn, [
        {"ean": "7790000001017", "nombre": "Xyzzy Qwerty", "marca": "Nadie"},
    ])
    conn.commit()

    build_db.build(conn, verbose=False)
    assert conn.execute(
        "SELECT COUNT(*) FROM productos WHERE ean='7790000001017'"
    ).fetchone()[0] == 0
    # Tampoco queda en la cola de revisión manual: no tiene sentido pedirle a
    # una persona que investigue un producto del que no sabemos nada.
    assert conn.execute(
        "SELECT COUNT(*) FROM revision_pendiente WHERE ean='7790000001017'"
    ).fetchone()[0] == 0
    conn.close()


def test_el_pipeline_conserva_al_que_esta_en_gondola(tmp_path):
    # Sin categoría ni ingredientes, pero confirmado en un supermercado real:
    # que no sepamos qué tiene adentro no lo vuelve inexistente.
    conn = _conn(tmp_path)
    _db.upsert_catalogo(conn, [
        {"ean": "7790000001024", "nombre": "Producto Misterioso", "marca": "M"},
    ])
    conn.execute(
        "INSERT INTO vtex_catalogo (ean, cadena, nombre, actualizado)"
        " VALUES ('7790000001024','disco','Producto Misterioso','2026-01-01')")
    conn.commit()

    build_db.build(conn, verbose=False)
    assert conn.execute(
        "SELECT COUNT(*) FROM productos WHERE ean='7790000001024'"
    ).fetchone()[0] == 1
    conn.close()


def test_el_pipeline_conserva_al_que_tiene_categoria(tmp_path):
    conn = _conn(tmp_path)
    _db.upsert_catalogo(conn, [
        {"ean": "7790000001031", "nombre": "Producto Con Rubro", "marca": "M"},
    ])
    _con_payload(conn, "7790000001031", ["en:snacks"])
    conn.commit()

    build_db.build(conn, verbose=False)
    assert conn.execute(
        "SELECT COUNT(*) FROM productos WHERE ean='7790000001031'"
    ).fetchone()[0] == 1
    conn.close()


def test_el_pipeline_conserva_al_que_tiene_ingredientes(tmp_path):
    conn = _conn(tmp_path)
    _db.upsert_catalogo(conn, [
        {"ean": "7790000001048", "nombre": "Snack Sin Rubro", "marca": "M"},
    ])
    conn.execute(
        "INSERT INTO vtex_ficha (ean, cadena, ingredientes, trazas, sellos,"
        " actualizado) VALUES ('7790000001048','disco',"
        " 'harina de maiz, aceite de girasol, sal', NULL, NULL, '2026-01-01')")
    conn.commit()

    build_db.build(conn, verbose=False)
    fila = conn.execute(
        "SELECT estado FROM productos WHERE ean='7790000001048'").fetchone()
    assert fila is not None and fila["estado"] == "apto"
    conn.close()


def test_el_dato_crudo_sobrevive_a_la_purga(tmp_path):
    # Se excluye de la búsqueda, no se destruye: si mañana OFF completa la
    # ficha, el producto vuelve solo en el próximo refresco.
    conn = _conn(tmp_path)
    _db.upsert_catalogo(conn, [
        {"ean": "7790000001055", "nombre": "Fantasma Total", "marca": None},
    ])
    conn.commit()
    build_db.build(conn, verbose=False)

    assert conn.execute(
        "SELECT COUNT(*) FROM productos WHERE ean='7790000001055'"
    ).fetchone()[0] == 0
    assert conn.execute(
        "SELECT COUNT(*) FROM catalogo WHERE ean='7790000001055'"
    ).fetchone()[0] == 1
    conn.close()
