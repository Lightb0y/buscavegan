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


# --- Lo que no es un alimento ---------------------------------------------

@pytest.mark.parametrize("nombre", [
    "shampoo", "Agua micelar", "Gel exfoliante facial micelar",
    "fructis hair food coco reparación", "hair food manteca de cacao",
    "Bálsamo hidratante labial frutas rojas", "Crema colorante capilar",
    "Bath and body body lotion", "toallitas húmedas", "pañuelos papel",
    "Desinfectante", "Detergente Ala concentrado", "Rexona Antibacterial",
    "cigarrillos rubios", "SÉRUM RELLENADOR OJOS",
    "jabón de glicerina", "esmalte para uñas", "protector solar",
    "pasta dental", "papel higiénico",
])
def test_la_cosmetica_y_la_limpieza_se_excluyen(nombre):
    assert rel.es_no_alimento(nombre)
    assert not rel.es_relevante(nombre, EAN_OK)


@pytest.mark.parametrize("nombre", [
    # El caso que obligó a poner el borde de palabra a la derecha: sin él,
    # "colonia" matchea dentro de "Colonial" y se lleva cuatro dulces de
    # leche y un chocolate.
    "Dulce de Leche Estilo Colonial",
    "Chocolate colonial",
    "Colonial Style Milk Caramel",
    # Las tres palabras que salieron de la lista porque nombran comida: el
    # salame tipo colonia, la miel en panal y una marca de aderezos. Juntas
    # se llevaban 176 alimentos del catálogo de góndola.
    "Salame tipo Colonia",
    "Queso Colonia",
    "Miel en panal",
    "Galletitas Okebón Panal",
    "Ketchup Dermaty",
    # Palabras que son comida bastante más seguido que cosmética.
    "Crema de leche La Serenísima",
    "Leche entera",
    "Manteca sin sal",
    "Queso crema",
    "Aceite de oliva extra virgen",
    "Pasta de maní",
    "Agua mineral sin gas",
    "Sal fina",
    "Leche de almendras",
    "Yogur natural",
    "Miel pura de abejas",
    "Pan lactal",
    "Manteca de cacao",
    "Barra de cereal",
])
def test_ningun_alimento_se_confunde_con_un_no_alimento(nombre):
    assert not rel.es_no_alimento(nombre), nombre
    assert rel.es_relevante(nombre, EAN_OK)


def test_sin_nombre_no_se_excluye_por_este_criterio():
    assert not rel.es_no_alimento(None)
    assert not rel.es_no_alimento("")


def test_el_motivo_dice_por_que():
    motivo = rel.motivo_exclusion("shampoo", EAN_OK)
    assert motivo is not None and "no es un alimento" in motivo
