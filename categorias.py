"""Normalización de categorías: de los `categories_tags` de OFF a ~20 rubros limpios.

Los tags crudos de OFF son multiidioma, jerárquicos y ruidosos (un yogur trae a
la vez `en:dairies`, `en:fermented-foods` y `en:fermented-milk-products`). Para
el desplegable de la app hace falta un valor único y legible por producto.

El orden de la lista importa: se toma la **primera** regla que matchea, así que
las categorías específicas van antes que las genéricas.
"""
from __future__ import annotations

OTROS = "Otros"

# (categoría normalizada, fragmentos de tag que la activan)
REGLAS: list[tuple[str, tuple[str, ...]]] = [
    ("Bebidas vegetales", ("plant-based-beverages", "plant-based-milk",
                           "soy-milks", "almond-milks", "vegetable-milks")),
    ("Lácteos", ("dairies", "milks", "yogurts", "cheeses", "creams",
                 "fermented-milk", "dairy-desserts", "butters", "dulce-de-leche")),
    ("Carnes y fiambres", ("meats", "meat-", "hams", "sausages", "poultry",
                           "charcuteries", "prepared-meats", "beef", "pork",
                           "chicken")),
    ("Pescados y mariscos", ("fishes", "seafood", "canned-fish", "tuna",
                             "shellfish", "sardines")),
    ("Huevos", ("eggs",)),
    ("Postres y helados", ("ice-cream", "frozen-desserts", "desserts", "flans",
                           "puddings")),
    ("Golosinas y chocolates", ("confectioneries", "chocolates", "candies",
                                "alfajores", "cocoa", "sweets", "bonbons",
                                "chewing-gum", "caramels")),
    ("Galletitas y bizcochos", ("biscuits", "crackers", "cakes", "cookies",
                                "wafers")),
    ("Panificados", ("breads", "pastries", "viennoiserie", "buns", "toasts")),
    ("Snacks salados", ("salty-snacks", "chips", "crisps", "appetizers",
                        "popcorn", "extruded")),
    ("Infusiones", ("coffees", "teas", "yerba", "mate", "herbal-tea",
                    "hot-beverages")),
    ("Bebidas alcohólicas", ("alcoholic", "beers", "wines", "spirits", "ciders")),
    ("Bebidas sin alcohol", ("beverages", "sodas", "carbonated", "juices",
                             "waters", "syrups", "iced-tea", "energy-drinks")),
    ("Aceites y grasas", ("oils", "fats", "olive-oil", "margarine",
                          "vegetable-oils")),
    ("Salsas y condimentos", ("sauces", "condiments", "spices", "seasonings",
                              "vinegars", "mayonnaise", "ketchup", "mustard",
                              "salt", "herbs")),
    ("Untables y mermeladas", ("spreads", "jams", "marmalades", "honeys",
                               "nut-butters", "hazelnut-spreads")),
    ("Conservas", ("canned", "preserves", "pickles", "olives")),
    ("Congelados", ("frozen",)),
    ("Frutas y verduras", ("fruits", "vegetables", "legumes-and-derivatives",
                           "nuts", "dried-fruits", "seeds")),
    ("Cereales, pastas y legumbres", ("cereals", "pastas", "rice", "flours",
                                      "legumes", "breakfast-cereals", "grains",
                                      "noodles", "semolina")),
    ("Comidas preparadas", ("meals", "pizzas", "sandwiches", "soups",
                            "prepared-", "empanadas")),
    ("Suplementos y dietéticos", ("dietary-supplements", "specific-diets",
                                  "baby-foods", "meal-replacement",
                                  "protein-", "sports-")),
]


def normalizar(categories_tags: list[str] | None) -> str:
    """Devuelve una categoría legible única, o "Otros" si nada matchea."""
    if not categories_tags:
        return OTROS
    tags = [t.lower() for t in categories_tags]
    for categoria, fragmentos in REGLAS:
        for tag in tags:
            # Se compara sin el prefijo de idioma ("en:", "es:", "fr:").
            cuerpo = tag.split(":", 1)[-1]
            if any(f in cuerpo for f in fragmentos):
                return categoria
    return OTROS


def todas() -> list[str]:
    return [c for c, _ in REGLAS] + [OTROS]
