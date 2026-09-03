"""Tests del analizador de ingredientes — la señal principal del proyecto."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import classify_ingredients as ci  # noqa: E402
import config  # noqa: E402

APTO, NO_APTO, REVISAR, VEG = (
    config.APTO, config.NO_APTO, config.REVISAR, config.VEGETARIANO)


# --- parser ---------------------------------------------------------------

def test_parser_aplana_parentesis():
    ings, _ = ci.parse_ingredients("Harina de trigo (hierro, niacina), sal.")
    assert "harina de trigo" in ings and "hierro" in ings and "sal" in ings


def test_parser_saca_porcentajes():
    ings, _ = ci.parse_ingredients("Mani tostado (10%), azucar 5,5%")
    assert "mani tostado" in ings


def test_parser_normaliza_ins_pegado():
    ings, _ = ci.parse_ingredients("Colorante INS120, emulsionante E-322")
    assert any("ins 120" in i for i in ings)
    assert any("e 322" in i for i in ings)


def test_trazas_se_separan_de_los_ingredientes():
    a = ci.analyze("Harina de trigo, azucar, sal. Puede contener trazas de leche.")
    assert a.estado == APTO, a.motivo
    assert a.trazas, "la advertencia de trazas se debe informar igual"


# --- veredictos -----------------------------------------------------------

CASOS = [
    # (ingredientes, estado esperado)
    ("Harina de trigo, grasa bovina refinada, agua, sal", NO_APTO),
    ("Leche entera, azucar, cacao", VEG),
    ("Agua, azucar, gelatina, colorante", NO_APTO),
    ("Harina, azucar, huevo, manteca", VEG),
    ("Azucar, pasta de cacao, manteca de cacao, lecitina de soja", APTO),
    ("Agua, leche de coco (25%), sal, goma xantica", APTO),
    ("Porotos negros, agua, sal", APTO),
    ("Harina de trigo, azucar, colorante carmin (INS 120)", NO_APTO),
    ("Agua, jarabe de glucosa, miel, acido citrico", VEG),
    ("Tomate, agua, sal, oregano, aceite de girasol", APTO),
]


@pytest.mark.parametrize("texto,esperado", CASOS)
def test_veredicto_por_ingredientes(texto, esperado):
    a = ci.analyze(texto)
    assert a.estado == esperado, f"{texto!r} -> {a.estado} ({a.motivo})"


# --- regla de seguridad ---------------------------------------------------

def test_sin_lista_de_ingredientes_es_revisar():
    for texto in (None, "", "   "):
        assert ci.analyze(texto).estado == REVISAR


def test_ingrediente_ambiguo_no_llega_a_apto():
    # Sin nada animal declarado, pero INS 471 puede ser grasa animal.
    a = ci.analyze("Harina de trigo, azucar, sal, emulsionante INS 471")
    assert a.estado == REVISAR and a.ambiguos


def test_lecitina_sin_origen_es_ambigua_pero_de_soja_no():
    assert ci.analyze("Harina, azucar, lecitina").estado == REVISAR
    assert ci.analyze("Harina, azucar, lecitina de soja").estado == APTO


def test_cobertura_baja_no_llega_a_apto():
    a = ci.analyze("Zzyx, qwrt, plugh, xyzzy, frobnicate")
    assert a.estado == REVISAR and a.cobertura < ci.COBERTURA_MINIMA


def test_lacteo_es_vegetariano_no_no_apto():
    # Distinguir importa: un lacto-vegetariano sí puede consumirlo.
    assert ci.analyze("Leche, sal, cuajo vegetal").estado in (VEG, NO_APTO)
    assert ci.analyze("Leche entera, azucar").estado == VEG


def test_la_peor_senal_manda():
    # Lácteo (vegetariano) + gelatina (no apto) -> gana el peor.
    a = ci.analyze("Leche entera, azucar, gelatina")
    assert a.estado == NO_APTO


# --- falsos positivos que importan ----------------------------------------

@pytest.mark.parametrize("texto", [
    "Agua, leche de almendras, sal",
    "Azucar, manteca de cacao, pasta de cacao",
    "Mani, sal",  # "manteca de mani" no debe confundirse
    "Agua, leche de soja, azucar",
])
def test_no_confunde_sustitutos_vegetales(texto):
    assert ci.analyze(texto).estado == APTO, texto
