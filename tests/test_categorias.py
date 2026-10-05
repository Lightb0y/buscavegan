"""Tests de la normalización de categorías (§ D5: el 40% que caía en "Otros").

Los casos no son inventados: casi todos salieron de correr las reglas contra
el catálogo real y mirar adónde iba a parar cada cosa. Los que están acá son
los que se equivocaban.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import categorias as cat  # noqa: E402


# --- Capa 1: los tags de OFF ----------------------------------------------

def test_los_tags_de_off_siguen_mandando():
    assert cat.normalizar(["en:dairies", "en:yogurts"]) == "Lácteos"
    assert cat.normalizar(["en:biscuits"]) == "Galletitas y bizcochos"


def test_sin_ninguna_senal_es_otros():
    assert cat.normalizar(None) == "Otros"
    assert cat.normalizar([]) == "Otros"
    assert cat.normalizar([], None, None) == "Otros"


def test_los_tags_de_aditivo_no_definen_el_rubro():
    """OFF etiqueta al Mantecol `en:sweeteners` por lo que tiene adentro.

    Es una golosina, no un endulzante. Si `sweeteners` activara el rubro, se
    llevaría a cualquier producto que lleve un edulcorante.
    """
    tags = ["en:sweeteners", "en:food-additives", "en:sugar-substitutes"]
    assert cat.por_tags(tags) != "Azúcar y endulzantes"


# --- Capa 2: el nombre ----------------------------------------------------

@pytest.mark.parametrize("nombre,esperado", [
    ("Galletitas 9 de Oro Azucarados", "Galletitas y bizcochos"),
    ("Vainillas", "Galletitas y bizcochos"),
    ("Chocolinas", "Galletitas y bizcochos"),
    ("Alfajor - Cofler Block", "Golosinas y chocolates"),
    ("mantecol", "Golosinas y chocolates"),
    ("Jelly Beans", "Golosinas y chocolates"),
    ("Mayonesa", "Salsas y condimentos"),
    ("mostaza ahumada", "Salsas y condimentos"),
    ("Canela molida - Alicante", "Salsas y condimentos"),
    ("Takis Fuego", "Snacks salados"),
    ("Nachos", "Snacks salados"),
    ("Arroz Blanco Largo Fino", "Cereales, pastas y legumbres"),
    ("Ravioles", "Cereales, pastas y legumbres"),
    ("pan lacteado", "Panificados"),
    ("Atun Desmenuzado Al Natural", "Pescados y mariscos"),
    ("Aceite de oliva", "Aceites y grasas"),
    ("Edulcorante", "Azúcar y endulzantes"),
    ("Stevia", "Azúcar y endulzantes"),
    ("Cappuccino", "Infusiones"),
    ("cafe", "Infusiones"),
    ("Gaseosa Secco Lima Limón", "Bebidas sin alcohol"),
    ("Santa Ana Reserve Malbec 2014", "Bebidas alcohólicas"),
    ("flan", "Postres y helados"),
    ("Gelatina", "Postres y helados"),
    ("Aceitunas Descarozadas", "Conservas"),
    ("Puré de papas instantáneo", "Comidas preparadas"),
    ("Huevos gran estrella", "Huevos"),
])
def test_el_nombre_alcanza_cuando_off_no_tiene_tags(nombre, esperado):
    assert cat.normalizar(None, nombre) == esperado


def test_cofler_block_galletitas_es_galletita_no_golosina():
    """Dice "Cofler" y dice "galletitas": gana la regla más específica."""
    assert cat.por_nombre("Cofler block galletitas") == "Galletitas y bizcochos"


def test_chocolinas_no_matchea_chocolate():
    """El borde de palabra es lo que evita este error."""
    assert cat.por_nombre("Chocolinas") != "Golosinas y chocolates"


# --- El nombre de una fruta casi siempre es un sabor, no el producto ------

@pytest.mark.parametrize("nombre", [
    "Gatorade manzana",
    "Yogur frutilla",
    "Jugo de naranja exprimido",
    "Bálsamo hidratante labial frutas rojas",
])
def test_un_sabor_a_fruta_no_hace_del_producto_una_fruta(nombre):
    assert cat.por_nombre(nombre) != "Frutas y verduras"


@pytest.mark.parametrize("nombre", [
    "Espinaca congelada", "Lechuga mantecosa", "Pasas de uva",
    "Nueces peladas", "Semillas de chía",
])
def test_las_verduras_y_frutos_secos_de_verdad_si_entran(nombre):
    assert cat.por_nombre(nombre) == "Frutas y verduras"


# --- Con el alcohol pasa lo mismo, en los dos sentidos ----------------------

@pytest.mark.parametrize("nombre", [
    # Nombres reales de góndola: el sustantivo va primero, el sabor después.
    "Licor de chocolate Tres Plumas 700 cc",
    "Vino tinto Chocolate Dadá 750 ml",
    "Licor Cusenier café al cognac 700 cc",
    "Gin Kamlar sabor yerba mate 500 cc",
    "  Licor Polini crema al cappuccino en botella 520 ml",
])
def test_una_bebida_alcoholica_con_sabor_sigue_siendo_alcohol(nombre):
    assert cat.por_nombre(nombre) == "Bebidas alcohólicas"


@pytest.mark.parametrize("nombre,esperado", [
    # El mismo patrón con otros sustantivos: la palabra de adelante manda.
    ("Vinagre de Vino Casalta 1300 Ml", "Salsas y condimentos"),
    ("Vinagre Omega De Vino Con Albahaca X 500 Cc.", "Salsas y condimentos"),
    ("Aceto Balsamico Marolio 500ml", "Salsas y condimentos"),
    ("Salsa De Tomate Maxima Te Conviene 340 Gr", "Salsas y condimentos"),
    ("Salsa de mostaza y miel Dos Anclas 375 g.", "Salsas y condimentos"),
    ("Dulce de leche ron Doña Magdalena frasco 400 g.", "Lácteos"),
    ("Dulce de Leche Clásico 245 Grs Milkaut", "Lácteos"),
])
def test_el_sustantivo_de_adelante_define_el_rubro(nombre, esperado):
    assert cat.por_nombre(nombre) == esperado


def test_un_dulce_de_leche_vegano_no_es_lacteo():
    assert cat.por_nombre("Dulce de leche vegano de coco") != "Lácteos"


def test_dona_magdalena_es_una_marca_no_una_magdalena():
    assert cat.por_nombre("Dulce Doña Magdalena a base de coco") != (
        "Galletitas y bizcochos")
    assert cat.por_nombre("Magdalena Pozo sabor limón 200 g.") == (
        "Galletitas y bizcochos")


@pytest.mark.parametrize("nombre", [
    # Acá el alcohol es la marca o el sabor, no el producto.
    "Galletitas Vermouth sabor queso 70 g.",
    "Dulce de leche ron La Serenísima 400 g.",
    "Mejillones La Caleta al vino blanco",
    "Ginger ale Schweppes",
])
def test_el_alcohol_en_el_medio_del_nombre_no_define_el_rubro(nombre):
    assert cat.por_nombre(nombre) != "Bebidas alcohólicas"


# --- Ningún plant-based puede terminar en un rubro de origen animal -------

@pytest.mark.parametrize("nombre", [
    "Milanesa de soja napolitana",
    "Milanesas De Soja Con Espinaca",
    "Hamburguesas de soja",
    "Not Burger",
    "Medallones de legumbres",
])
def test_un_analogo_vegetal_nunca_es_carne(nombre):
    assert cat.por_nombre(nombre) != "Carnes y fiambres"


@pytest.mark.parametrize("nombre", [
    "Leche de Almendras", "Leche de Coco", "Bebida vegetal de avena",
    "Leche de soja original",
])
def test_una_leche_vegetal_nunca_es_lacteo(nombre):
    assert cat.por_nombre(nombre) == "Bebidas vegetales"


def test_la_carne_de_verdad_si_es_carne():
    """El guardapolvo plant-based no puede desactivar la regla siempre."""
    assert cat.por_nombre("Hamburguesas de carne clásicas") == "Carnes y fiambres"
    assert cat.por_nombre("Jamón cocido") == "Carnes y fiambres"


# --- "Al huevo" es una pasta, no un huevo ---------------------------------

@pytest.mark.parametrize("nombre", [
    "Fideos Al Huevo N5", "Pasta Casereccia Al Huevo", "Fusilli Al Huevo",
    "Cabellos angel con huevo",
])
def test_la_pasta_al_huevo_es_pasta(nombre):
    assert cat.por_nombre(nombre) == "Cereales, pastas y legumbres"


# --- Capa 3: la góndola del supermercado ----------------------------------

def test_la_gondola_resuelve_lo_que_el_nombre_no():
    assert cat.normalizar(None, "Cremoso Light", "Lácteos") == "Lácteos"
    assert cat.normalizar(None, "xyz sin sentido", "Congelados") == "Congelados"


def test_la_gondola_va_despues_del_nombre():
    """"Almacén" tiene 110.703 productos: el nombre siempre sabe más."""
    assert cat.normalizar(None, "Mayonesa", "Almacén") == "Salsas y condimentos"


@pytest.mark.parametrize("gondola", [
    "Almacén",              # el cajón de sastre de las cinco cadenas
    "Bebidas",              # no distingue un vino de un agua
    "Quesos y Fiambres",    # son dos rubros distintos
    "Desayuno y merienda",  # cereales, galletitas, infusiones y mermeladas
    "Frescos",
    "Libre de Gluten",      # no es un rubro, es un atributo
    "Importados",
])
def test_las_gondolas_ambiguas_no_mapean_a_nada(gondola):
    assert cat.por_gondola(gondola) is None


def test_la_gondola_ignora_mayusculas_y_tildes():
    assert cat.por_gondola("lacteos") == "Lácteos"
    assert cat.por_gondola("Panaderia y Pasteleria") == "Panificados"
    assert cat.por_gondola("Frutas y verduras") == "Frutas y verduras"


# --- Orden de precedencia -------------------------------------------------

def test_el_orden_es_tags_luego_nombre_luego_gondola():
    tags = ["en:biscuits"]
    assert cat.normalizar(tags, "Mayonesa", "Lácteos") == "Galletitas y bizcochos"
    assert cat.normalizar(None, "Mayonesa", "Lácteos") == "Salsas y condimentos"
    assert cat.normalizar(None, None, "Lácteos") == "Lácteos"


def test_todas_incluye_los_rubros_nuevos():
    todas = cat.todas()
    assert "Azúcar y endulzantes" in todas
    assert "Otros" in todas
    assert len(todas) == len(set(todas)), "no puede haber rubros repetidos"
