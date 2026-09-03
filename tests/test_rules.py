"""Casos obligatorios de SPEC.md §7 para la Capa 2, más la regla de seguridad."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import classify_rules as cr  # noqa: E402
import config  # noqa: E402

APTO, NO_APTO, REVISAR, VEG = (
    config.APTO, config.NO_APTO, config.REVISAR, config.VEGETARIANO)

# (nombre, estados aceptables) — SPEC.md §7
CASOS_SPEC = [
    ("Leche de coco Vitacoco 1L", {APTO, REVISAR}),
    ("Leche entera La Serenísima 1L", {NO_APTO}),
    ("Milanesa de soja Granja del Sol", {APTO}),
    ("Milanesa de carne vacuna", {NO_APTO}),
    ("Queso untable vegano NotCo", {APTO}),
    ("Queso cremoso Tregar", {NO_APTO}),
    ("Manteca de maní Naturalia", {APTO, REVISAR}),
    ("Manteca La Paulina 200g", {NO_APTO}),
    ("Hamburguesa plant based", {APTO}),
    ("Yogur de soja Ades", {APTO}),
    ("Fideos al huevo Matarazzo", {NO_APTO}),
]


@pytest.mark.parametrize("nombre,esperados", CASOS_SPEC)
def test_casos_obligatorios_spec(nombre, esperados):
    d = cr.classify_name(nombre)
    assert d.estado in esperados, f"{nombre!r} -> {d.estado} ({d.motivo})"


def test_normalize_saca_tildes():
    assert cr.normalize("Caseína  Húmeda") == "caseina humeda"


def test_ventana_no_alcanza_a_otra_frase():
    # "coco" está demasiado lejos como para estar modificando a "leche".
    d = cr.classify_name("Leche entera con chips de chocolate y coco rallado")
    assert d.estado == NO_APTO


def test_marca_tambien_se_mira():
    d = cr.classify_name("Hamburguesa clásica", marca="NotCo Vegano")
    assert d.estado == APTO


# --- Capa 1 ---------------------------------------------------------------

def test_label_del_fabricante_gana():
    d = cr.classify_off({"labels_tags": ["en:vegan"],
                         "ingredients_analysis_tags": ["en:vegan-status-unknown"]})
    assert (d.estado, d.fuente) == (APTO, cr.FUENTE_OFF_LABEL)


def test_analysis_no_vegano():
    d = cr.classify_off({"ingredients_analysis_tags": ["en:non-vegan",
                                                       "en:vegetarian"]})
    assert d.estado == VEG


def test_analysis_desconocido_no_resuelve():
    d = cr.classify_off({"ingredients_analysis_tags": ["en:vegan-status-unknown"]})
    assert d.estado == REVISAR and not d.resuelto


# --- regla de seguridad ---------------------------------------------------

def test_sin_datos_nunca_es_apto():
    for nombre in ("Producto Xyz 500g", "Snack surtido", "Bebida Zzz"):
        assert cr.classify(nombre, off_product=None).estado == REVISAR


def test_nombre_animal_contra_rubro_vegetal_queda_en_revisar():
    d = cr.classify_name("Milanesa de carne", categoria="Frutas y verduras frescas")
    assert d.estado == REVISAR


def test_capa1_tiene_prioridad_sobre_heuristica():
    # El nombre dice "vegano" pero OFF vio un ingrediente animal: gana OFF.
    d = cr.classify("Queso vegano Marca X",
                    off_product={"ingredients_analysis_tags": ["en:non-vegan"]})
    assert d.estado == NO_APTO and d.fuente == cr.FUENTE_OFF_ANALYSIS
