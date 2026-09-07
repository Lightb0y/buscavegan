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

def _registro(marca: str, producto: str, rnpa: str) -> dict:
    """Arma una fila como la deja `cargar()`, con los tokens ya calculados."""
    return {"marca": marca, "producto": producto, "rnpa": rnpa,
            "marca_norm": ingest_anmat.normalizar(marca),
            "producto_tokens": ingest_anmat.tokens(producto),
            "sabor_tokens": ingest_anmat.tokens_de_sabor(producto)}


REGISTRO = [
    _registro("Bien Plantados", "Medallones a base de choclo, quinoa y "
              "calabaza - Libre de Gluten / Andino", "02-729883"),
    _registro("Felices Las Vacas", "Queso untable sabor natural", "02-123456"),
    # El caso Doña Magdalena: La Retama certificó el postre de coco, y la
    # misma marca vende un dulce de leche con leche de verdad.
    _registro("Dona Magdalena", "Producto dietético a base de coco sabor "
              "dulce de leche - Libre de Gluten", "02-714087"),
    # El nombre comercial va DESPUÉS de la cláusula de sabor: acotarla mal
    # dejaría a este producto sin los tokens por los que realmente matchea.
    _registro("Granix", "Alimento texturizado a base de harina de maíz y de "
              "avena, sabor barbacoa - Veggie snacks con zapallo", "02-999111"),
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


# --- la cláusula de sabor no puede sostener un cruce sola -------------------

def test_tokens_de_sabor_acota_la_clausula():
    # Corta en el guión: el nombre comercial que viene después es identidad,
    # no sabor, y varios productos matchean justamente por ahí.
    assert ingest_anmat.tokens_de_sabor(
        "Alimento texturizado, sabor barbacoa - Veggie snacks con zapallo"
    ) == {"barbacoa"}


def test_tokens_de_sabor_toma_la_frase_entera():
    assert ingest_anmat.tokens_de_sabor(
        "Producto dietético a base de coco sabor dulce de leche - Libre de "
        "Gluten") == {"dulce", "leche"}


def test_no_cruza_cuando_lo_unico_en_comun_es_el_sabor():
    # El bug de Doña Magdalena: {dulce, leche} daba 0.67 de solapamiento
    # contra "a base de coco sabor dulce de leche" y certificaba como vegano
    # un dulce de leche que arranca con "leche parcialmente descremada".
    assert ingest_anmat.match_anmat(
        "Dulce de Leche Sin Azucar", "Dona Magdalena", INDICE) is None


def test_sigue_cruzando_por_el_nombre_comercial_posterior_al_sabor():
    m = ingest_anmat.match_anmat("veggie snacks", "Granix", INDICE)
    assert m and m["rnpa"] == "02-999111"


def test_el_sabor_suma_al_score_si_hay_composicion_en_comun():
    # "queso" y "untable" son composición; que además coincida el sabor no
    # molesta. Lo que se prohíbe es que el sabor sea lo ÚNICO compartido.
    m = ingest_anmat.match_anmat(
        "Queso untable sabor natural", "Felices Las Vacas", INDICE)
    assert m and m["rnpa"] == "02-123456"
