"""Falsos `apto` y falsos `no_apto` encontrados auditando el léxico contra la
taxonomía oficial de Open Food Facts y el Código Alimentario Argentino.

Cada test de acá corresponde a un error real que el clasificador cometía antes,
no a un caso hipotético. Los dos grupos tienen costos distintos y por eso se
separan: un falso `apto` manda a alguien a comer un producto animal, un falso
`no_apto` solo le esconde un producto que sí podía comer.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import classify_ingredients as ci  # noqa: E402
import config  # noqa: E402

APTO, NO_APTO, REVISAR, VEG = (
    config.APTO, config.NO_APTO, config.REVISAR, config.VEGETARIANO)


# --- Falsos NO APTO: productos veganos que quedaban marcados como animales ---
# Casi todos son el mismo error: la palabra del análogo animal usada por un
# producto vegetal ("carne de soja", "crema de maní", "leche de almendras").

@pytest.mark.parametrize("texto", [
    "Crema de mani, azucar, sal",
    "Carne de soja, agua, sal",
    "Proteina vegetal texturizada, carne vegetal, sal",
    "Harina de trigo, manteca vegetal, azucar, sal",
    "Miel de cana, agua, sal",
    "Agua, azucar, miel de maple, harina",
    "Leche de anacardo, agua, sal",
    "Queso vegano, agua, almidon, sal",
    "Yogur de coco, azucar, almidon, agua",
    "Agua, sal, sebo vegetal, harina, azucar",
    "Agua, harina, gelatina vegetal, azucar, sal",
])
def test_no_marca_como_animal_un_producto_vegetal(texto):
    assert ci.analyze(texto).estado == APTO


def test_cuajo_microbiano_no_es_faena():
    # El cuajo microbiano y el vegetal son los que más se usan hoy: condenar
    # "cuajo" a secas marcaba como faena a quesos que no la tienen.
    assert ci.analyze("Agua, cuajo vegetal, sal").estado != NO_APTO
    assert ci.analyze("Agua, cuajo microbiano, sal").estado != NO_APTO
    # ...pero el cuajo sin aclarar sigue siendo de faena.
    assert ci.analyze("Agua, cuajo, sal").estado == NO_APTO


def test_crema_de_leche_sigue_siendo_lactea():
    # La corrección de "crema de maní" no puede haber abierto la puerta a que
    # la crema láctea pase como vegana.
    assert ci.analyze("Crema de leche, azucar").estado == VEG
    assert ci.analyze("Crema, azucar, harina").estado == VEG


def test_miel_de_abeja_sigue_siendo_animal():
    assert ci.analyze("Miel, agua, sal").estado == VEG
    assert ci.analyze("Miel de abeja, agua").estado == VEG


# --- Falsos APTO: lo caro. Cosas animales o dudosas que salían aprobadas ----

def test_oleomargarina_a_secas_es_animal():
    # CAA art. 545: la oleomargarina (óleo-oil) se define SOLO como bovina u
    # ovina, obtenida de los primeros jugos de faena. No hay versión vegetal.
    # OFF no ayuda acá: su taxonomía solo tiene "oleomargarina bovina" y no
    # define nada para el término a secas.
    for texto in ("Harina de trigo, oleomargarina, azucar, sal, agua",
                  "Harina de trigo, oleomargarina ovina, azucar, sal",
                  "Harina de trigo, oleomargarina bovina, azucar, sal"):
        r = ci.analyze(texto)
        assert r.estado == NO_APTO, texto


def test_margarina_sin_aclarar_no_se_afirma_vegana():
    # CAA art. 551: la fase grasa de la margarina puede ser "grasas animales
    # comestibles" y admite hasta 5% de grasa de leche.
    assert ci.analyze("Aceite, margarina, azucar, sal, agua, harina").estado == REVISAR
    # Con el calificativo sí se puede afirmar.
    assert ci.analyze("Aceite, margarina vegetal, azucar, sal, agua").estado == APTO


def test_grasa_hidrogenada_sin_origen_no_se_afirma_vegana():
    # CAA art. 548: se hidrogena cualquier grasa del Código, animal o vegetal.
    assert ci.analyze("Harina, grasa hidrogenada, azucar, sal, agua").estado == REVISAR
    assert ci.analyze("Harina, grasa vegetal hidrogenada, azucar, sal").estado == APTO


def test_lisozima_es_de_clara_de_huevo():
    # Único conservante de uso corriente de origen animal.
    assert ci.analyze("Agua, azucar, sal, lisozima, harina").estado == VEG
    assert ci.analyze("Agua, azucar, sal, INS 1105, harina, aceite").estado == VEG


def test_codigo_ins_de_cuatro_digitos_no_se_trunca():
    # "ins 1105" matcheaba como "ins 110" contra la regla de aditivos genéricos
    # y se contaba como reconocido-vegano.
    assert ci.normalize("INS1105") == "ins 1105"
    assert ci.normalize("INS-330") == "ins 330"


def test_lacteo_en_femenino():
    # `l[aá]cteo?s?` nunca matcheaba "láctea": "materia grasa láctea" pasaba.
    assert ci.analyze("Agua, harina, grasa lactea, azucar, sal").estado == VEG
    assert ci.analyze("Agua, harina, materia grasa lactea, sal").estado == VEG


@pytest.mark.parametrize("texto,esperado", [
    ("Agua, azucar, extracto de ave, sal, harina", NO_APTO),
    ("Agua, sal, ternera, harina, aceite", NO_APTO),
    ("Agua, sal, crustaceos, harina, aceite", NO_APTO),
    ("Agua, sal, harina de hueso, aceite, azucar", NO_APTO),
    ("Agua, sal, proteina animal, harina, aceite", NO_APTO),
    ("Agua, sal, sabor res, harina, aceite", NO_APTO),
    ("Agua, sal, grasa de ave, harina, aceite", NO_APTO),
    ("Agua, sal, pepsina, harina, aceite", NO_APTO),
    ("Agua, sal, transglutaminasa, harina, aceite", REVISAR),
    ("Agua, sal, nisina, harina, aceite", REVISAR),
])
def test_ingredientes_animales_que_faltaban(texto, esperado):
    assert ci.analyze(texto).estado == esperado


def test_hueso_solo_no_condena_una_aceituna():
    # "sin hueso" es lo que dice una aceituna descarozada, no un derivado de
    # faena: por eso la regla pide "harina/polvo/caldo/carbón de hueso".
    assert ci.analyze("Aceitunas sin hueso, agua, sal").estado == APTO
    assert ci.analyze("Duraznos sin hueso, agua, azucar").estado == APTO


# --- Clases de aditivo: nombran una función, no un origen ------------------

def test_clase_de_aditivo_no_penaliza_al_rotulo_explicito():
    # El rótulo argentino declara la clase Y el aditivo ("gelificante (agar)").
    # Si la clase contara en el denominador de la cobertura, declarar de más
    # saldría más caro que declarar de menos, que es exactamente al revés de
    # lo que queremos premiar.
    con_clase = ci.analyze("Agua, coco, gelificante (agar), "
                           "estabilizante (goma xantica), sal")
    sin_clase = ci.analyze("Agua, coco, agar, goma xantica, sal")
    assert con_clase.cobertura == sin_clase.cobertura
    assert con_clase.estado == APTO


def test_clase_de_aditivo_no_tapa_al_aditivo_animal():
    # Lo que no puede pasar: que descartar la palabra de clase haga perder de
    # vista el aditivo concreto, que es el que manda.
    assert ci.analyze("Agua, azucar, colorante: carmin").estado == NO_APTO
    assert ci.analyze("Agua, azucar, colorante (INS 120)").estado == NO_APTO
    assert ci.analyze("Agua, queso, conservante: lisozima").estado == VEG


def test_una_lista_de_puras_clases_no_alcanza_para_afirmar_nada():
    assert ci.analyze("colorante, conservante, estabilizante").estado == REVISAR


# --- Listas en inglés -----------------------------------------------------
# Buena parte del catálogo argentino de OFF trae los ingredientes en inglés y
# el léxico español no los ve por una letra ("carmin" no matchea en "carmine").

@pytest.mark.parametrize("texto,esperado", [
    ("Sugar, rice flour, natural flavouring, water", REVISAR),
    ("Sugar, water, salt, carmine, flour", NO_APTO),
    ("Sugar, water, salt, gelatin, flour", NO_APTO),
    ("Sugar, water, salt, whey, flour", VEG),
    ("Sugar, water, salt, tallow, flour", NO_APTO),
    ("Sugar, water, salt, lysozyme, flour", VEG),
    ("Sugar, water, salt, shortening, flour", REVISAR),
    ("Sugar, water, salt, bone meal, flour", NO_APTO),
    ("Sugar, water, salt, buttermilk, flour", VEG),
])
def test_ingredientes_en_ingles(texto, esperado):
    assert ci.analyze(texto).estado == esperado


def test_lecitina_de_soja_en_ingles_no_es_ambigua():
    # "lecithin" sin aclarar sí es ambigua, pero "soy lecithin" no.
    assert ci.analyze("Sugar, water, soy lecithin, flour, salt").estado == APTO
    assert ci.analyze("Sugar, water, lecithin, flour, salt").estado == REVISAR


def test_vegetable_shortening_no_es_grasa_de_cerdo():
    assert ci.analyze("Flour, vegetable shortening, sugar, salt").estado == APTO


def test_clase_de_aditivo_con_el_codigo_pegado_sigue_reconociendose():
    r = ci.analyze("Harina de trigo, aceite de girasol, sal, conservante INS 202, "
                   "acidulante INS 330")
    assert r.estado == APTO


# --- Tags de OFF ----------------------------------------------------------

def test_enumeracion_and_no_se_absuelve_por_un_calificador_vegetal():
    # "vegetable-oil-and-lard" son DOS ingredientes: el calificador vegetal
    # del primero no puede absolver a la grasa de cerdo del segundo.
    assert ci.analyze_tags(["en:vegetable-oil-and-lard", "en:water"]).estado == NO_APTO
    assert ci.analyze_tags(
        ["en:lard-and-vegetable-oil-shortening", "en:water", "en:salt"]).estado == NO_APTO


def test_compuestos_definidos_se_resuelven_enteros():
    # La partición por "and" no puede romper los tags que la taxonomía ya
    # define como una sola cosa.
    r = ci.analyze_tags(["en:mono-and-diglycerides-of-fatty-acids", "en:water"])
    assert r.estado == REVISAR
    assert r.ambiguos


def test_leche_vegetal_en_tags_sigue_siendo_vegetal():
    assert ci.analyze_tags(["en:coconut-milk", "en:water"]).estado == APTO
    assert ci.analyze_tags(["es:leche-de-almendras", "en:water"]).estado == APTO


@pytest.mark.parametrize("tag,esperado", [
    ("en:acid-whey", VEG),
    ("en:milkfat", VEG),
    ("en:poultry-extract", NO_APTO),
    ("en:veal", NO_APTO),
    ("en:crustacean", NO_APTO),
    ("es:oleomargarina", NO_APTO),
])
def test_tags_animales_que_faltaban(tag, esperado):
    assert ci.analyze_tags([tag, "en:water", "en:salt"]).estado == esperado


def test_margarina_en_tags_no_se_afirma_vegana():
    assert ci.analyze_tags(
        ["en:margarine", "en:wheat-flour", "en:sugar", "en:salt"]).estado == REVISAR


# --- Capa 2: heurística de nombre -----------------------------------------

import classify_rules as cr  # noqa: E402


@pytest.mark.parametrize("nombre", [
    "Miel de cana", "Miel de maple", "Miel de agave organica",
])
def test_miel_vegetal_no_es_de_abeja(nombre):
    # La melaza y la savia de arce se llaman "miel" pero no tienen abeja.
    # El calificador va aparte del WHITELIST general: "helado de maple" tiene
    # que seguir siendo un helado con leche.
    assert cr.classify_name(nombre).estado == APTO


def test_la_miel_de_abeja_sigue_siendo_animal_por_nombre():
    assert cr.classify_name("Miel pura de abeja").estado == NO_APTO
    assert cr.classify_name("Miel").estado == NO_APTO


def test_el_calificador_puntual_no_se_filtra_a_otras_keywords():
    # "maple" anula a "miel", pero no puede anular a "helado".
    assert cr.classify_name("Helado de maple").estado == NO_APTO


@pytest.mark.parametrize("nombre", [
    "Milanesa de ternera", "Cordero patagonico", "Salame tandilero",
    "Mortadela", "Morcilla", "Bondiola braseada", "Mejillones al natural",
    "Calamar en su tinta", "Higado de novillo", "Pavo trozado",
])
def test_cortes_y_embutidos_argentinos_que_faltaban(nombre):
    # Antes caían en `revisar` solo por no estar nombrados en el léxico.
    assert cr.classify_name(nombre).estado == NO_APTO
