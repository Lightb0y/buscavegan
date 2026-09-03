"""Tests de la ficha del supermercado: parseo y uso en la decisión.

No dependen de red: el parseo se prueba con las respuestas reales de VTEX
(copiadas tal cual, con su formato raro) y la decisión sobre una base temporal.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import build_db  # noqa: E402
import config  # noqa: E402
import db as _db  # noqa: E402
import ingest_fichas as fi  # noqa: E402

APTO, NO_APTO, REVISAR, VEG = (
    config.APTO, config.NO_APTO, config.REVISAR, config.VEGETARIANO)


# --- parseo de los campos, tal como los devuelve VTEX ---------------------

def test_lista_de_ingredientes_entrecomillada():
    # VTEX manda una lista con UN string adentro, y los items entrecomillados.
    crudo = ["'harina de trigo', 'hierro', 'grasa vacuna refinada', 'gelatina'"]
    assert fi.texto_de_campo(crudo) == (
        "harina de trigo, hierro, grasa vacuna refinada, gelatina")


def test_campo_vacio_o_ausente():
    assert fi.texto_de_campo(None) is None
    assert fi.texto_de_campo([]) is None
    assert fi.texto_de_campo([""]) is None


def test_texto_plano_sin_comillas():
    # Algunos productos no vienen entrecomillados: se devuelve tal cual.
    assert fi.texto_de_campo(["harina de trigo, sal"]) == "harina de trigo, sal"


def test_sellos_son_repr_de_python_no_json():
    # Vienen como el repr de una lista de dicts, con comillas simples: hay que
    # leerlos con ast.literal_eval, json.loads falla.
    crudo = ["[{'certification_type_code': 'vegan', 'certification_type_name': "
             "'Vegano'}, {'certification_type_code': 'gluten_free'}]"]
    assert fi.codigos_de_sellos(crudo) == "gluten_free,vegan"


def test_sellos_rotos_no_rompen():
    assert fi.codigos_de_sellos(["esto no es una lista"]) is None
    assert fi.codigos_de_sellos(None) is None


def test_extraer_ficha_completa():
    producto = {
        "Ingredientes": ["'agua', 'azucar'"],
        "Trazas": ["'leche'"],
        "Sellos": ["[{'certification_type_code': 'vegan'}]"],
    }
    ficha = fi.extraer_ficha(producto)
    assert ficha == {"ingredientes": "agua, azucar", "trazas": "leche",
                     "sellos": "vegan"}


# --- uso en la decisión ---------------------------------------------------

def _conn(tmp_path):
    conn = _db.connect(tmp_path / "fichas.db")
    _db.init_db(conn)
    return conn


def test_la_ficha_resuelve_lo_que_off_no_tiene():
    # El caso que motivó todo: OFF no trae ingredientes y el producto quedaba
    # en `revisar` o se adivinaba por el nombre.
    d = build_db.decidir(
        "Producto Cualquiera Xyz", "Marca", None, off={},
        ficha={"ingredientes": "harina de maiz, aceite de girasol, sal, azucar"})
    assert d.estado == APTO
    assert d.fuente == build_db.FUENTE_INGREDIENTES_SUPER


def test_la_ficha_detecta_lo_que_el_nombre_esconde():
    # Takis Fuego: el nombre no dice nada, pero la ficha declara INS 120
    # (carmín de cochinilla). Es un caso real del catálogo.
    d = build_db.decidir(
        "Takis Fuego", "Takis", None, off={},
        ficha={"ingredientes": "harina de maiz, aceite vegetal, sal, "
                               "col ins 120, col ins 129"})
    assert d.estado == NO_APTO
    assert "carmin" in d.motivo.lower() or "carmín" in d.motivo.lower()


def test_ante_discrepancia_gana_la_mas_restrictiva():
    off = {"ingredients_text": "agua, azucar, sal, harina"}
    ficha = {"ingredientes": "agua, azucar, sal, harina, leche en polvo"}
    d = build_db.decidir("X", "M", None, off=off, ficha=ficha)
    assert d.estado == VEG
    assert d.fuente == build_db.FUENTE_INGREDIENTES_SUPER


def test_el_sello_vegano_alcanza_para_apto():
    d = build_db.decidir("Producto Xyz", "M", None, off={},
                         ficha={"sellos": "gluten_free,vegan"})
    assert d.estado == APTO
    assert d.fuente == build_db.FUENTE_SELLO_SUPER


def test_el_sello_vegano_no_le_gana_a_los_ingredientes():
    # Si el sello dice vegano pero la lista declara leche, alguien se
    # equivocó: no es momento de afirmar `apto`.
    d = build_db.decidir(
        "Producto Xyz", "M", None, off={},
        ficha={"sellos": "vegan",
               "ingredientes": "agua, azucar, leche en polvo, harina"})
    assert d.estado == REVISAR
    assert d.fuente == build_db.FUENTE_SELLO_SUPER


def test_sin_ficha_todo_sigue_igual():
    off = {"ingredients_text": "agua, azucar, sal, harina de trigo"}
    con = build_db.decidir("X", "M", None, off=off, ficha={})
    sin = build_db.decidir("X", "M", None, off=off)
    assert con.estado == sin.estado == APTO
    assert con.fuente == sin.fuente == "ingredientes"


def test_build_guarda_los_ingredientes_del_super_para_mostrarlos(tmp_path):
    conn = _conn(tmp_path)
    _db.upsert_catalogo(conn, [
        {"ean": "7790000000017", "nombre": "Snack Xyz", "marca": "M"},
    ])
    conn.execute(
        "INSERT INTO vtex_ficha (ean, cadena, ingredientes, trazas, sellos,"
        " actualizado) VALUES ('7790000000017','disco',"
        " 'harina de maiz, aceite de girasol, sal', 'leche', NULL, '2026-01-01')")
    conn.commit()

    build_db.build(conn, verbose=False)
    fila = conn.execute(
        "SELECT estado, fuente_decision, ingredients_text FROM productos"
        " WHERE ean='7790000000017'").fetchone()
    assert fila["estado"] == APTO
    assert fila["fuente_decision"] == build_db.FUENTE_INGREDIENTES_SUPER
    # Se guardan para que la app los muestre, aclarando de dónde salieron.
    assert "harina de maiz" in fila["ingredients_text"]
    assert "Disco" in fila["ingredients_text"]
    conn.close()


def test_pendientes_no_repite_lo_ya_consultado(tmp_path):
    conn = _conn(tmp_path)
    _db.upsert_catalogo(conn, [
        {"ean": "7790000000024", "nombre": "Producto A", "marca": "M"},
    ])
    conn.execute(
        "INSERT INTO vtex_catalogo (ean, cadena, nombre, actualizado)"
        " VALUES ('7790000000024','disco','Producto A','2026-01-01')")
    conn.commit()
    build_db.build(conn, verbose=False)

    assert [e for e, _ in fi.pendientes(conn)] == ["7790000000024"]

    # Una ficha vacía también cuenta como consultada: no se vuelve a preguntar.
    conn.execute(
        "INSERT INTO vtex_ficha (ean, cadena, ingredientes, trazas, sellos,"
        " actualizado) VALUES ('7790000000024','disco',NULL,NULL,NULL,'2026-01-01')")
    conn.commit()
    assert fi.pendientes(conn) == []
    conn.close()


def test_solo_se_consultan_las_cadenas_que_publican_ficha(tmp_path):
    # Carrefour y Día no exponen los campos: pedirles la ficha sería gastar
    # requests al pedo.
    conn = _conn(tmp_path)
    _db.upsert_catalogo(conn, [
        {"ean": "7790000000031", "nombre": "Solo En Carrefour", "marca": "M"},
    ])
    conn.execute(
        "INSERT INTO vtex_catalogo (ean, cadena, nombre, actualizado)"
        " VALUES ('7790000000031','carrefour','Solo En Carrefour','2026-01-01')")
    conn.commit()
    build_db.build(conn, verbose=False)

    assert fi.pendientes(conn) == []
    conn.close()
