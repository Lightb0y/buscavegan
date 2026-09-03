"""Tests del análisis sobre `ingredients_tags` (la taxonomía normalizada de OFF)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import classify_ingredients as ci  # noqa: E402
import config  # noqa: E402

APTO, NO_APTO, REVISAR, VEG = (
    config.APTO, config.NO_APTO, config.REVISAR, config.VEGETARIANO)


CASOS = [
    (["en:water", "en:coconut-milk", "en:salt", "en:xanthan-gum"], APTO),
    (["en:sugar", "en:cocoa-butter", "en:soya-lecithin", "en:vanilla"], APTO),
    (["en:rice-flour", "en:sunflower-oil", "es:azucar-organica", "en:salt"], APTO),
    (["en:milk", "en:dairy", "en:sugar"], VEG),
    (["en:wheat-flour", "en:butter", "en:egg", "en:sugar"], VEG),
    (["en:gelatin", "en:sugar", "en:water"], NO_APTO),
    (["es:grasa-bovina", "en:wheat-flour", "en:salt"], NO_APTO),
    (["en:carmine", "en:sugar", "en:water"], NO_APTO),
]


@pytest.mark.parametrize("tags,esperado", CASOS)
def test_veredicto_por_tags(tags, esperado):
    a = ci.analyze_tags(tags)
    assert a.estado == esperado, f"{tags} -> {a.estado} ({a.motivo})"


def test_sin_tags_es_revisar():
    assert ci.analyze_tags(None).estado == REVISAR
    assert ci.analyze_tags([]).estado == REVISAR


def test_tag_ambiguo_no_llega_a_apto():
    a = ci.analyze_tags(["en:wheat-flour", "en:sugar", "en:e471", "en:salt"])
    assert a.estado == REVISAR and a.ambiguos


def test_calificador_vegetal_dentro_del_tag():
    # El tag es un solo ingrediente: "coconut-milk" no es leche animal.
    assert ci._clasificar_tag("en:coconut-milk") is None
    assert ci._clasificar_tag("en:almond-milk") is None
    assert ci._clasificar_tag("en:vegetable-fat") is None
    # Pero la leche pelada sí.
    assert ci._clasificar_tag("en:milk")[0] == "animal"


def test_tag_a_texto():
    assert ci.tag_a_texto("en:wheat-flour") == "wheat flour"
    assert ci.tag_a_texto("es:azucar-organica") == "azucar organica"


# --- analyze_product: texto y tags juntos ---------------------------------

def test_prefiere_el_mas_restrictivo_entre_texto_y_tags():
    # El texto ve la gelatina; los tags solo azúcar y agua.
    off = {"ingredients_text": "Azucar, agua, gelatina",
           "ingredients_tags": ["en:sugar", "en:water"]}
    assert ci.analyze_product(off).estado == NO_APTO


def test_usa_tags_cuando_no_hay_texto():
    off = {"ingredients_tags": ["en:milk", "en:sugar"]}
    assert ci.analyze_product(off).estado == VEG


def test_producto_sin_ingredientes_es_revisar():
    assert ci.analyze_product({}).estado == REVISAR
    assert ci.analyze_product(None).estado == REVISAR
