"""Tests del orden de capas: qué fuente gana cuando varias se pronuncian.

Es la lógica que decide el veredicto final de cada producto, así que conviene
fijarla acá antes que descubrir un cambio de prioridad mirando la app.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import build_db  # noqa: E402
import classify_ingredients as ci  # noqa: E402
import classify_rules as cr  # noqa: E402
import config  # noqa: E402
import ingest_anmat  # noqa: E402

APTO, NO_APTO, REVISAR, VEG = (
    config.APTO, config.NO_APTO, config.REVISAR, config.VEGETARIANO)

ANMAT_IDX = ingest_anmat.indexar([{
    "marca": "Felices Las Vacas", "producto": "Queso untable sabor natural",
    "rnpa": "02-123456", "marca_norm": "felices las vacas",
    "producto_tokens": ingest_anmat.tokens("Queso untable sabor natural"),
}])


def test_certificacion_gana_a_todo():
    # El nombre dice "queso" y OFF lo llama no vegano, pero ANMAT lo certificó.
    d = build_db.decidir(
        "Queso untable sabor natural", "Felices Las Vacas", None,
        {"ingredients_text": "Agua, castanas de caju, sal",
         "ingredients_analysis_tags": ["en:non-vegan"]},
        ANMAT_IDX)
    assert d.estado == APTO
    assert d.fuente == ingest_anmat.FUENTE_CERTIFICACION
    assert "02-123456" in d.motivo


def test_label_del_fabricante_gana_a_los_ingredientes():
    d = build_db.decidir("Snack Xyz", "Marca", None,
                         {"labels_tags": ["en:vegan"],
                          "ingredients_tags": ["en:sugar", "en:water"]})
    assert d.fuente == cr.FUENTE_OFF_LABEL


def test_ingredientes_ganan_a_la_heuristica_de_nombre():
    # El nombre sugiere lácteo, pero la lista de ingredientes es vegetal.
    d = build_db.decidir(
        "Queso untable", "Marca X", None,
        {"ingredients_text": "Agua, castanas de caju, sal, jugo de limon"})
    assert d.estado == APTO and d.fuente == ci.FUENTE_INGREDIENTES


def test_heuristica_solo_cuando_no_hay_ingredientes():
    d = build_db.decidir("Leche entera La Serenisima", "La Serenisima", None, {})
    assert d.estado == NO_APTO and d.fuente == cr.FUENTE_HEURISTICA


def test_sin_nada_queda_en_revisar():
    d = build_db.decidir("Producto Xyz 500g", "Marca", None, {})
    assert d.estado == REVISAR and d.fuente == cr.FUENTE_SIN_DATOS


# --- resolución de discrepancias ------------------------------------------

def test_ante_discrepancia_gana_el_mas_restrictivo():
    # Nuestros ingredientes ven gelatina; OFF dice que es vegano.
    d = build_db.decidir(
        "Gomitas", "Marca", None,
        {"ingredients_text": "Azucar, agua, gelatina",
         "ingredients_analysis_tags": ["en:vegan", "en:vegetarian"]})
    assert d.estado == NO_APTO


def test_lacteo_no_se_degrada_a_no_apto_si_off_no_opina_de_vegetariano():
    # La excepción acotada: los dos coinciden en que no es vegano, y el
    # ingrediente concreto que identificamos dice que sí es vegetariano.
    d = build_db.decidir(
        "Yogur natural", "Marca", None,
        {"ingredients_text": "Leche entera, azucar",
         "ingredients_analysis_tags": ["en:non-vegan",
                                       "en:vegetarian-status-unknown"]})
    assert d.estado == VEG


def test_si_off_dice_no_vegetariano_no_se_ablanda():
    d = build_db.decidir(
        "Producto", "Marca", None,
        {"ingredients_text": "Leche entera, azucar",
         "ingredients_analysis_tags": ["en:non-vegan", "en:non-vegetarian"]})
    assert d.estado == NO_APTO


# --- regla de seguridad ----------------------------------------------------

def test_ninguna_combinacion_sin_datos_llega_a_apto():
    for off in ({}, None, {"ingredients_tags": []},
                {"ingredients_analysis_tags": ["en:vegan-status-unknown"]}):
        d = build_db.decidir("Producto Sin Pistas 123", "Marca Xyz", None, off)
        assert d.estado != APTO, f"{off} -> {d.estado}"
