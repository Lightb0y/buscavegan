"""Tests de la Capa 0: cruce contra el registro oficial de ANMAT.

Sin EAN el cruce es por marca + nombre, así que lo que se prueba acá es sobre
todo lo que NO debe matchear: un falso positivo marcaría "apto" un producto que
nadie certificó.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import ingest_anmat  # noqa: E402

# --- Capa 0: cruce con el registro de ANMAT --------------------------------

REGISTRO = [
    {"marca": "Bien Plantados", "producto": "Medallones a base de choclo, "
     "quinoa y calabaza - Libre de Gluten / Andino", "rnpa": "02-729883",
     "marca_norm": "bien plantados",
     "producto_tokens": ingest_anmat.tokens(
         "Medallones a base de choclo, quinoa y calabaza - Libre de Gluten / Andino")},
    {"marca": "Felices Las Vacas", "producto": "Queso untable sabor natural",
     "rnpa": "02-123456", "marca_norm": "felices las vacas",
     "producto_tokens": ingest_anmat.tokens("Queso untable sabor natural")},
]
INDICE = ingest_anmat.indexar(REGISTRO)


def test_match_anmat_encuentra_el_producto():
    m = ingest_anmat.match_anmat(
        "Medallones de choclo, quinoa y calabaza", "Bien Plantados", INDICE)
    assert m and m["rnpa"] == "02-729883"


def test_match_anmat_ignora_tildes_y_mayusculas():
    m = ingest_anmat.match_anmat(
        "QUESO UNTABLE SABOR NATURAL", "felices las vacas", INDICE)
    assert m is not None


def test_match_anmat_no_cruza_marcas_distintas():
    # Mismo nombre, otra marca: no es el producto certificado.
    assert ingest_anmat.match_anmat(
        "Queso untable sabor natural", "La Serenisima", INDICE) is None


def test_match_anmat_no_cruza_por_nombre_flojo():
    # La marca coincide pero el producto es otro.
    assert ingest_anmat.match_anmat(
        "Hamburguesa de lentejas", "Bien Plantados", INDICE) is None


def test_match_anmat_sin_marca_no_arriesga():
    assert ingest_anmat.match_anmat("Queso untable sabor natural", None,
                                    INDICE) is None


def test_match_anmat_con_marca_multiple_de_off():
    # OFF suele traer "Marca, Submarca".
    m = ingest_anmat.match_anmat("Queso untable sabor natural",
                                 "Felices Las Vacas, Vegan Line", INDICE)
    assert m is not None
