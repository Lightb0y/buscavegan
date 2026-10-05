"""Tests de la normalización de marcas (§ D6: una marca, una sola grafía)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import marcas  # noqa: E402


# --- limpiar: ruido de carga ----------------------------------------------

@pytest.mark.parametrize("crudo,esperado", [
    ("['La serenisima']", "La serenisima"),   # repr de lista de una corrida vieja
    ('["Arcor"]', "Arcor"),
    ("  Bimbo  ", "Bimbo"),
    ("Dia%", "Dia"),
    ("dia %", "dia"),
    ("Arcor,Cofler", "Arcor, Cofler"),        # separador unificado
    ("Arcor ,  Cofler", "Arcor, Cofler"),
    ("La    Virginia", "La Virginia"),
])
def test_limpiar_saca_el_ruido(crudo, esperado):
    assert marcas.limpiar(crudo) == esperado


@pytest.mark.parametrize("vacio", [None, "", "   ", ",", " - "])
def test_limpiar_devuelve_none_si_no_queda_nada(vacio):
    assert marcas.limpiar(vacio) is None


def test_limpiar_no_toca_mayusculas_ni_tildes():
    """Esa decisión es de `canonica`, que compara variantes entre sí."""
    assert marcas.limpiar("LA SERENISIMA") == "LA SERENISIMA"
    assert marcas.limpiar("Nestlé") == "Nestlé"


# --- clave: agrupar variantes ---------------------------------------------

@pytest.mark.parametrize("variantes", [
    ("La Serenisima", "La Serenísima", "LA SERENISIMA", "la serenisima",
     "['La serenisima']"),
    ("Dia", "Día", "DIA", "Dia%", "dia %"),
    ("Nestle", "Nestlé", "NESTLE"),
    ("Cuisine & Co", "Cuisine&Co", "Cuisine & Co.", "CUISINE & CO"),
    ("Hellmann's", "Hellmann´s", "HELLMANNS"),
])
def test_variantes_de_una_marca_comparten_clave(variantes):
    claves = {marcas.clave(v) for v in variantes}
    assert len(claves) == 1, claves


def test_marcas_distintas_no_comparten_clave():
    assert marcas.clave("Arcor") != marcas.clave("Bagley")


def test_clave_de_vacio_es_vacia():
    assert marcas.clave(None) == ""
    assert marcas.clave("  ") == ""


# --- canonica: elegir la grafía a mostrar ---------------------------------

def test_prefiere_forma_mixta_sobre_mayusculas_y_minusculas():
    assert marcas.canonica({"ARCOR": 3, "Arcor": 144, "arcor": 22}) == "Arcor"


def test_forma_mixta_gana_aunque_pierda_por_volumen():
    """Las cadenas publican en mayúsculas; eso no la vuelve la grafía buena."""
    assert marcas.canonica({"ARCOR": 3015, "Arcor": 10}) == "Arcor"


def test_preserva_las_marcas_en_camello():
    """Capitalizar cada palabra rompería NotCo y SanCor."""
    assert marcas.canonica({"NotCo": 20, "Notco": 2, "NOTCO": 1}) == "NotCo"
    assert marcas.canonica({"SanCor": 19, "Sancor": 12, "SANCOR": 5}) == "SanCor"


def test_el_tilde_gana_si_tiene_respaldo():
    variantes = {"La Serenisima": 68, "La Serenísima": 65, "LA SERENISIMA": 5}
    assert marcas.canonica(variantes) == "La Serenísima"


def test_el_tilde_pierde_si_es_una_errata_suelta():
    """Un solo producto con 'Alícante' contra 16 con 'Alicante' es un typo."""
    assert marcas.canonica({"Alicante": 16, "Alícante": 1}) == "Alicante"


def test_a_igualdad_de_forma_gana_la_mas_frecuente():
    assert marcas.canonica({"Molinos Ala": 16, "Molinos ala": 1}) == "Molinos Ala"


def test_canonica_es_determinista():
    """Dos corridas sobre los mismos datos tienen que dar lo mismo."""
    variantes = {"Veggie": 5, "VEGGIE": 5, "veggie": 5}
    assert len({marcas.canonica(dict(variantes)) for _ in range(10)}) == 1


def test_canonica_de_vacio():
    assert marcas.canonica({}) == ""
    assert marcas.canonica({"": 3, "  ": 1}) == ""


def test_alias_pisa_el_voto():
    """Marcas donde la grafía correcta es minoritaria en los datos."""
    assert marcas.canonica({"Aguila": 15, "Águila": 2}) == "Águila"
    assert marcas.canonica({"Dia": 100, "Día": 20}) == "Día"


# --- construir_mapa -------------------------------------------------------

def test_el_mapa_manda_todas_las_variantes_a_la_misma_grafia():
    mapa = marcas.construir_mapa([
        ("La Serenisima", 68), ("La Serenísima", 65), ("LA SERENISIMA", 5),
        ("['La serenisima']", 1),
    ])
    destinos = {marcas.normalizar(v, mapa) for v in
                ("La Serenisima", "La Serenísima", "LA SERENISIMA",
                 "['La serenisima']")}
    assert destinos == {"La Serenísima"}


def test_la_gondola_aporta_marcas_que_off_no_tiene():
    mapa = marcas.construir_mapa([("Arcor", 10)], [("Cepita", 40)])
    assert marcas.normalizar("Cepita", mapa) == "Cepita"


def test_la_gondola_no_vota_dentro_de_un_grupo_que_off_ya_conoce():
    """Si votara, 'ARCOR' ganaría por volumen sin aportar la grafía buena."""
    mapa = marcas.construir_mapa([("Arcor", 10)], [("ARCOR", 3015)])
    assert marcas.normalizar("ARCOR", mapa) == "Arcor"


def test_normalizar_sin_mapa_cae_a_alias_y_limpieza():
    assert marcas.normalizar("LA SERENISIMA") == "La Serenísima"
    assert marcas.normalizar("['Tregar']") == "Tregar"
    assert marcas.normalizar(None) is None
    assert marcas.normalizar("   ") is None


def test_normalizar_una_marca_que_no_esta_en_el_mapa():
    """No se inventa nada: se devuelve limpia y tal cual."""
    mapa = marcas.construir_mapa([("Arcor", 10)])
    assert marcas.normalizar("Marca Nueva SRL", mapa) == "Marca Nueva SRL"
