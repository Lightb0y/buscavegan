"""Tests del filtro de relevancia geográfica (§ el 20% de ruido no-argentino)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import relevancia as rel  # noqa: E402

EAN_OK = "7790001234567"


@pytest.mark.parametrize("nombre", [
    "Leche de almendras", "Café La Virginia", "Açaí bowl", "Müsli integral",
    "Product Name in English", "Aceite d'oliva", "Baguette française",
    "100% Whey Protein", "Té verde", None, "",
])
def test_nombres_latinos_pasan(nombre):
    assert rel.es_relevante(nombre, EAN_OK)


@pytest.mark.parametrize("nombre", [
    "دجاج توبنغ",       # arabe
    "ونستون",            # arabe
    "כשר",               # hebreo
    "Молоко",            # cirilico
    "牛乳",               # chino
    "ミルク",             # katakana
    "우유",               # hangul
    "นม",                # tailandes
    "दूध",               # devanagari
])
def test_alfabetos_no_argentinos_se_excluyen(nombre):
    assert not rel.es_relevante(nombre, EAN_OK)
    assert rel.motivo_exclusion(nombre, EAN_OK) is not None


def test_bom_no_dispara_el_filtro():
    # utf-8-sig (el encoding de los CSV de revision.py) antepone un BOM;
    # el rango de formas árabes de presentación B no debe incluirlo.
    assert rel.es_relevante("﻿Leche de coco", EAN_OK)


@pytest.mark.parametrize("ean", ["77900012", "779000123456",
                                 "7790001234567", "77900012345678"])
def test_largos_de_ean_validos(ean):
    # 8, 12, 13 y 14 dígitos son largos reales de EAN-8/UPC-A/EAN-13/GTIN-14.
    assert len(ean) in (8, 12, 13, 14)
    assert rel.es_relevante("Producto", ean)


@pytest.mark.parametrize("ean", ["1234", "123", "12345", "123456"])
def test_eans_demasiado_cortos_se_excluyen(ean):
    assert not rel.es_relevante("Producto", ean)


def test_sin_ean_no_excluye_por_eso():
    # El chequeo de EAN es adicional al de nombre, no obligatorio por sí solo.
    assert rel.es_relevante("Producto normal", None)
