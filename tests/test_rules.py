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


# --- commodities vegetales (identidad del producto) ------------------------

@pytest.mark.parametrize("nombre", [
    "Sal Fina", "Agua Sierra de los padres 2L", "Cafe instantaneo La Morenita",
    "Canela molida Alicante", "Chickpeas Dona Pupa", "Acelga congelada",
    "Yerba mate Playadito", "Lentejas secas", "Pure de tomate Arcor",
])
def test_commodity_vegetal_es_apto(nombre):
    d = cr.classify_name(nombre)
    assert d.estado == APTO, f"{nombre} -> {d.estado} ({d.motivo})"


@pytest.mark.parametrize("nombre", [
    "Arroz con leche La Serenisima",   # la commodity va despues del blacklist
    "Cafe con leche",
    "Helado de banana",                # preparaciones que llevan lacteo
    "Flan de vainilla",
    "Alfajor de maicena",
    "Mayonesa Hellmanns",
    "Torta de manzana",
    "Aceite de pescado",
])
def test_commodity_no_pisa_al_blacklist(nombre):
    d = cr.classify_name(nombre)
    assert d.estado == NO_APTO, f"{nombre} -> {d.estado} ({d.motivo})"


@pytest.mark.parametrize("nombre", [
    "Cappuccino La Virginia",   # lleva leche en polvo: no es commodity
    "Fideos Matarazzo",         # las pastas pueden llevar huevo
])
def test_lo_dudoso_sigue_en_revisar(nombre):
    assert cr.classify_name(nombre).estado == REVISAR


def test_declaracion_vegana_gana_a_la_preparacion():
    assert cr.classify_name("Helado vegano de coco").estado == APTO


# --- la commodity tiene que encabezar el nombre, no ser el sabor -----------
# Casos encontrados revisando a mano la salida real del pipeline: todos
# habian quedado como `apto` cuando la commodity aparecia en cualquier parte.

@pytest.mark.parametrize("nombre", [
    "Yogurisimo Banana",             # lacteo: "yogur" no matchea en "Yogurisimo"
    "Galletitas avena con semillas",  # la avena es un ingrediente, no el producto
    "Spaghetti con espinaca",         # pasta: puede llevar huevo
    "Exquisita sabor limon",          # postre en polvo, el limon es el sabor
    "pan salvado el mejor",           # el pan puede llevar lacteo
    "Aperitivo de Vermut con Soda",
    "Celienergy nuez",                # "nuez" es la variedad, no el producto
])
def test_commodity_de_adorno_no_alcanza(nombre):
    d = cr.classify_name(nombre)
    assert d.estado == REVISAR, f"{nombre} -> {d.estado} ({d.motivo})"


@pytest.mark.parametrize("nombre,esperado", [
    ("Arroz Integral con sal", "arroz"),
    ("Pure De Tomate Arcor", "pure de tomate"),
    ("Yerba Mate Amanda", "yerba mate"),
    ("Agua Villa Del Sur", "agua"),
])
def test_commodity_multipalabra_y_cabeza(nombre, esperado):
    assert cr._commodity_cabeza(cr.normalize(nombre)) == esperado


# --- nombres en inglés -----------------------------------------------------
# Buena parte del catálogo argentino de OFF tiene el nombre en inglés, y el
# inglés invierte el orden: "almond milk" contra "leche de almendras".

@pytest.mark.parametrize("nombre,esperado", [
    ("Whey Protein", NO_APTO),
    ("Milk Chocolate", NO_APTO),
    ("Tuna in oil", NO_APTO),
    ("Honey roasted peanuts", NO_APTO),
    ("Almond milk unsweetened", APTO),
    ("Oat milk barista", APTO),
    ("Coconut milk", APTO),
    ("Vegan cheese spread", APTO),
])
def test_nombres_en_ingles(nombre, esperado):
    d = cr.classify_name(nombre)
    assert d.estado == esperado, f"{nombre} -> {d.estado} ({d.motivo})"


@pytest.mark.parametrize("nombre", [
    # La ventana hacia atrás vale solo en inglés: en español un vegetal previo
    # no modifica al lácteo que viene después.
    "Chocolate con almendras y leche",
    "Helado de coco con leche",
])
def test_la_ventana_hacia_atras_no_aplica_en_espanol(nombre):
    assert cr.classify_name(nombre).estado == NO_APTO
