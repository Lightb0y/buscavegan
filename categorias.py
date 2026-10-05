"""Normalización de categorías: de lo que hay a ~22 rubros limpios.

El problema medido
------------------
**2.962 de 7.381 productos (40%) caían en "Otros"**: la categoría más grande
del sitio era la que no dice nada. Para quien quiere explorar por rubro en vez
de buscar un producto puntual, eso es la navegación rota.

De dónde sale la categoría, en orden
------------------------------------
1. **Los `categories_tags` de Open Food Facts.** Es una taxonomía curada y es
   la mejor señal cuando está. Pero son multiidioma, jerárquicos y ruidosos
   (un yogur trae a la vez `en:dairies`, `en:fermented-foods` y
   `en:fermented-milk-products`), así que hay que colapsarlos a un valor único.

2. **El nombre del producto** (`REGLAS_NOMBRE`). Es lo que rescata la mayoría
   de los "Otros": OFF no tiene tags para ellos, pero el nombre dice
   "Galletitas 9 de Oro", "Mantecol" o "Mayonesa" y eso alcanza.

3. **El rubro de góndola del supermercado** (`RUBRO_POR_GONDOLA`), como último
   recurso. Va al final a propósito: es mucho más grueso que el nombre.
   **110.703 productos están en "Almacén"**, que es el cajón de sastre de las
   cinco cadenas y no significa nada; "Bebidas" no distingue un vino de un
   agua; "Quesos y Fiambres" mezcla dos rubros distintos. Solo se mapean las
   góndolas que designan un rubro sin ambigüedad.

4. Si nada de eso resuelve, "Otros" — que ahora sí quiere decir "no sabemos",
   y no "no miramos".

El orden de las reglas importa: se toma la **primera** que matchea, así que lo
específico va antes que lo genérico. Los casos que lo obligan están anotados
donde ocurren; el más importante es que este es un sitio vegano y un
"hamburguesa de soja" no puede terminar en "Carnes y fiambres".
"""
from __future__ import annotations

import re
import unicodedata

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
    # Ojo con los fragmentos de esta regla: OFF mete tags de **aditivo** en
    # `categories_tags`, y `en:sweeteners` le toca a cualquier producto que
    # lleve un edulcorante adentro. El Mantecol viene etiquetado
    # `en:sweeteners, en:food-additives, en:sugar-substitutes` y no es un
    # endulzante: es una golosina. Solo se usan fragmentos que nombren el
    # producto, no lo que tiene adentro; el resto lo resuelve el nombre.
    ("Azúcar y endulzantes", ("sugars", "table-sugar")),
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

# --- Capa 2: el nombre del producto ---------------------------------------
#
# Palabras tal como las escribe una góndola argentina. Se comparan sin tildes
# y con borde de palabra, así que "mana" no matchea dentro de "manzana" y
# "chocolate" no matchea dentro de "Chocolinas" (que son galletitas, no un
# chocolate: exactamente el tipo de error que el borde de palabra evita).
#
# El orden es el de la lista y gana la primera regla que matchea.

# Un producto plant-based no puede caer en "Carnes y fiambres" ni en
# "Lácteos" por decir "hamburguesa" o "leche": en un sitio vegano ese error se
# ve de lejos. Estas palabras desactivan las reglas de origen animal.
_PLANT_BASED = (
    r"vegana?s?|vegetariana?s?|vegetal(?:es)?|plant\s*based|de\s+soja|"
    r"a\s+base\s+de\s+soja|de\s+almendras?|de\s+castanas?|de\s+arroz|"
    r"de\s+avena|de\s+coco|not\s*\w+|sin\s+tacc\s*vegana?"
)

REGLAS_NOMBRE: list[tuple[str, str]] = [
    # Bebidas vegetales antes que Lácteos: "leche de almendras" es lo primero
    # que hay que sacar del camino de la regla de "leche".
    ("Bebidas vegetales",
     r"leche\s+(?:de\s+)?(?:almendra|soja|coco|arroz|avena|castana|quinoa|mani)|"
     r"bebida\s+(?:vegetal|de\s+almendra|de\s+soja|de\s+arroz|de\s+avena|de\s+coco)|"
     r"leche\s+vegetal|alimento\s+a\s+base\s+de\s+soja"),

    # --- El sustantivo del producto va primero ---------------------------
    #
    # En la góndola el nombre arranca por lo que el producto **es** y sigue
    # por el sabor, la marca o el uso: "Licor de chocolate Tres Plumas",
    # "Vinagre de vino Casalta", "Dulce de leche ron". Las reglas de abajo
    # buscan la palabra en cualquier lugar y gana la primera de la lista, así
    # que una palabra del medio le ganaba al sustantivo de adelante. Medido
    # sobre los nombres de góndola: ~120 licores, vinos y gins repartidos
    # entre Golosinas e Infusiones por decir "chocolate" o "café", y el
    # vinagre de vino y las salsas al vino en "Bebidas alcohólicas".
    #
    # Estas reglas van ancladas al principio a propósito, y solo con
    # sustantivos que no admiten otra lectura como primera palabra. En
    # cualquier otro lugar del nombre la palabra casi siempre es el sabor o la
    # marca —"Galletitas Vermouth" (una marca), "Mejillones al vino blanco"—, y
    # eso lo siguen resolviendo las reglas generales. Por eso tampoco está
    # "vermouth": como primera palabra puede ser la marca de galletitas.
    ("Bebidas alcohólicas",
     r"^(?:licor|vino|gin|vodka|whisky|whiskey|ron|fernet|aperitivo|"
     r"espumante|champagne|sidra|cerveza|tequila)\b"),
    ("Salsas y condimentos", r"^(?:vinagre|aceto|salsa)\b"),
    # Un dulce de leche vegano no llega acá: el rubro es de origen animal y
    # `por_nombre` lo saltea si el nombre es plant-based.
    ("Lácteos", r"^dulce\s+de\s+leche\b"),

    # Los análogos plant-based necesitan un rubro propio y temprano. Saltear
    # la regla de carne (ver `_ANIMAL`) evita que una milanesa de soja quede
    # en "Carnes y fiambres", pero no alcanza: sin esta regla, "Milanesas de
    # soja con espinaca" seguía de largo hasta "Frutas y verduras" por decir
    # espinaca.
    ("Comidas preparadas",
     r"(?:milanesas?|hamburguesas?|medallones?|nuggets?|salchichas?|"
     r"chorizos?|fiambres?|bastones?)\s+(?:de\s+|a\s+base\s+de\s+)?"
     r"(?:soja|vegetal(?:es)?|vegana?s?|seitan|legumbres|garbanzo|lenteja)|"
     r"not\s*(?:burger|chicken|meat|milanesa|pollo)"),

    # "Huevo de pascua" es una golosina, no un huevo: va antes.
    ("Golosinas y chocolates",
     r"huevo[s]?\s+de\s+pascua|conejo\s+de\s+chocolate"),

    # Galletitas antes que Golosinas: "Cofler block galletitas" es galletita.
    # "Doña Magdalena" es una marca de dulces, no una magdalena: el texto
    # llega sin tildes, de ahí el "dona".
    ("Galletitas y bizcochos",
     r"galletit|galleta|bizcoch|cracker|vainillas|chocolinas|coquitas|"
     r"hogarenas|mellizas|criollitas|polvorita|tostada|grisin|bay\s*biscuit|"
     r"sonrisas|merengada|pepas|scons|(?<!dona )magdalena|budin|bizcochuelo|"
     r"pan\s+dulce|budines|obleas?"),

    ("Golosinas y chocolates",
     r"alfajor|chocolate|bombon|caramelo|chupetin|chicle|gomitas?|turron|"
     r"mantecol|marroc|garrapinada|jelly\s*bean|halls|beldent|milka|cofler|"
     r"cadbury|confite|tita|rhodesia|bon\s*o\s*bon|nugaton|mentita|"
     r"golosina|barra\s+de\s+cereal|pastillas?\s+de|dulce\s+de\s+batata|"
     r"dulce\s+de\s+membrillo|gatitos|shot\b"),

    ("Postres y helados",
     r"helado|postre|flan|gelatina|mousse|chantilly|cassata|"
     r"bombon\s+helado|palito\s+helado"),

    ("Infusiones",
     r"\bcafe\b|cappuccino|capuchino|yerba|mate\s+cocido|"
     r"\bte\b|te\s+(?:verde|negro|rojo|en\s+saquitos)|tisana|nescafe|"
     r"cafe\s+instantaneo|saquitos\s+de\s+te|torrado"),

    ("Snacks salados",
     r"snack|papas\s+fritas|palitos|chizitos|nachos|takis|saladix|"
     r"pochoclo|pop\s*corn|conitos|doritos|cheetos|mani\s+(?:salado|tostado)|"
     r"chips\s+de|papa\s+frita|tostaditas|bastoncitos"),

    ("Pescados y mariscos",
     r"\batun\b|caballa|sardina|merluza|salmon|anchoa|calamar|langostino|"
     r"camaron|mejillon|surimi|filet\s+de\s+pescado"),

    # "Levadura de cerveza" es un suplemento, no una bebida: de ahí el
    # lookbehind. Es el único caso medido, pero aparecía como vino.
    ("Bebidas alcohólicas",
     r"\bvino\b|(?<!levadura de )cerveza|fernet|whisky|whiskey|vodka|\bgin\b|"
     r"\bron\b|aperitivo|champagne|espumante|sidra|licor|malbec|cabernet|"
     r"tequila|vermouth|\bcava\b"),

    ("Bebidas sin alcohol",
     r"gaseosa|\bagua\b|\bjugo\b|\bsoda\b|coca\s*cola|pepsi|sprite|fanta|"
     r"seven\s*up|7\s*up|agua\s+saborizada|isotonic|energizante|exprimido|"
     r"nectar|tonica|limonada|amargo\s+serrano|bebida\s+cola"),

    ("Azúcar y endulzantes",
     r"azucar|edulcorante|stevia|sacarina|endulzante|sucralosa|"
     r"jarabe\s+de\s+maiz"),

    ("Aceites y grasas",
     r"aceite|margarina|oleomargarina|rocio\s+vegetal|grasa\s+(?:bovina|vacuna)|"
     r"manteca\s+de\s+cerdo"),

    ("Untables y mermeladas",
     r"mermelada|jalea|\bmiel\b|pasta\s+de\s+mani|mantequilla\s+de\s+mani|"
     r"nutella|crema\s+de\s+avellana|untable\s+dulce"),

    ("Salsas y condimentos",
     r"mayonesa|ketchup|mostaza|\bsalsa\b|pure\s+de\s+tomate|"
     r"tomate\s+(?:triturado|perita|cubeteado)|aderezo|vinagre|condimento|"
     r"oregano|pimienta|canela|comino|pimenton|\bsal\s+(?:fina|gruesa|entrefina)|"
     r"\bcaldo\b|aji\s+molido|\bcurry\b|laurel|provenzal|chimichurri|savora|"
     r"nuez\s+moscada|azafran|especias?"),

    # Lácteos, después de todo lo que puede decir "leche" o "crema" sin serlo.
    ("Lácteos",
     r"yogur|yoghurt|\bqueso|ricota|muzzarella|mozzarella|provolone|"
     r"roquefort|dulce\s+de\s+leche|\bleche\b|\bcrema\b|\bmanteca\b|"
     r"kesitas|casancrem|serenito|yogurisimo|cuajada|queso\s+untable|"
     r"leche\s+(?:en\s+polvo|condensada|chocolatada)|postre\s+lacteo"),

    ("Carnes y fiambres",
     r"jamon|salame|mortadela|bondiola|panceta|chorizo|salchicha|"
     r"\bcarne\b|\bpollo\b|\bcerdo\b|pechuga|\bnalga\b|\basado\b|matambre|"
     r"\bpaleta\b|\blomo\b|hamburguesa|milanesa|morcilla|\bpata\s+muslo|"
     r"peceto|vacio|costeleta|churrasco|bife"),

    ("Panificados",
     r"\bpan\b|pan\s+(?:lactal|rallado|de\s+molde|arabe|frances)|factura|"
     r"medialuna|prepizza|tapas?\s+de\s+(?:empanada|tarta)|chipa|"
     r"\bbaguette\b|panes\b|churro"),

    ("Cereales, pastas y legumbres",
     r"fideo|spaghetti|spagueti|tallarin|mostachol|ravioles?|noquis|"
     r"sorrentinos|\barroz\b|harina|polenta|avena|cereal|granola|copos|"
     r"lenteja|poroto|garbanzo|arveja|soja\s+texturizada|semola|quinoa|"
     r"salvado|fecula|almidon|chickpeas|zucaritas|froot\s*loops|"
     r"\bpastas?\b|codito|municion|tirabuzon|penne|farfalle|casereccia|"
     r"fusilli|fideo|cabellos?\s+(?:de\s+)?angel|dedalito|monos\s+de\s+pasta|cintas"),

    # Huevos va **después** de las pastas, y además descarta "al huevo" y
    # "con huevo": ahí el huevo es un ingrediente de la pasta, no el producto.
    # Enumerar formas de fideo no alcanzaba —"Fusilli al huevo", "cabello de
    # ángel con huevo"— y siempre iba a faltar una.
    ("Huevos", r"(?<!al )(?<!con )\bhuevos?\b|clara\s+de\s+huevo|\byema\b"),

    ("Comidas preparadas",
     r"pizza|sandwich|\bsopa\b|empanada|tarta\s+(?:de|salada)|canelones|"
     r"lasagna|lasana|guiso|pure\s+de\s+papa|nuggets|bocaditos|"
     r"comida\s+lista|plato\s+listo|rebozado"),

    ("Conservas",
     r"aceituna|palmito|\bchoclo\b|pickles|conserva|encurtido|"
     r"al\s+natural\s+lata|\bescabeche\b"),

    # Ojo: **el nombre de una fruta casi nunca es el producto, es el sabor.**
    # "Gatorade manzana", "yogur frutilla", "bálsamo labial frutas rojas".
    # Medido: la versión con nombres sueltos de fruta se llevaba bebidas y
    # hasta cosmética a este rubro. Quedan solo las palabras que nombran el
    # producto en sí —verduras que nadie usa como sabor, y frutos secos, que
    # sí se venden como tales—; la fruta fresca de verdad la recupera la
    # góndola "Frutas y Verduras", que para eso existe.
    ("Frutas y verduras",
     r"\bverduras?\b|hortaliza|lechuga|cebolla|zanahoria|zapallo|zapallito|"
     r"brocoli|espinaca|acelga|champinon|\bhongos\b|\bensalada\b|"
     r"pasas\s+de\s+uva|\bnuez\b|\bnueces\b|almendras\b|castanas\b|"
     r"semillas?\s+de|frutos\s+secos|\bfruta\s+fresca"),

    ("Suplementos y dietéticos",
     r"proteina|\bwhey\b|suplemento|colageno|vitamina|papilla|\bnestum\b|"
     r"compota|alimento\s+infantil|leche\s+de\s+formula|creatina|"
     r"barrita\s+proteica"),

    ("Congelados", r"congelad|\bfreezer\b|ultracongelad"),
]

# --- Capa 3: la góndola del supermercado ----------------------------------
#
# Solo las que designan un rubro sin ambigüedad. Quedan deliberadamente
# afuera: "Almacén" (110.703 productos, el cajón de sastre de las cinco
# cadenas), "Bebidas" (no distingue vino de agua), "Quesos y Fiambres" (son
# dos rubros), "Desayuno y merienda" (cereales, galletitas, infusiones y
# mermeladas a la vez), "Frescos", "Carnes y pescados", "Libre de Gluten" e
# "Importados" (que no son rubros, son atributos).
RUBRO_POR_GONDOLA: dict[str, str] = {
    "lacteos": "Lácteos",
    "lacteos y productos frescos": "Lácteos",
    "carnes": "Carnes y fiambres",
    "pescados y mariscos": "Pescados y mariscos",
    "frutas y verduras": "Frutas y verduras",
    "panaderia": "Panificados",
    "panaderia y pasteleria": "Panificados",
    "congelados": "Congelados",
    "isotonicas": "Bebidas sin alcohol",
    "aguas saborizadas": "Bebidas sin alcohol",
}

_ANIMAL = {"Carnes y fiambres", "Lácteos", "Huevos", "Pescados y mariscos"}

_REGLAS_NOMBRE_COMPILADAS = [
    (rubro, re.compile(rf"\b(?:{patron})", re.IGNORECASE))
    for rubro, patron in REGLAS_NOMBRE
]
_PLANT_BASED_RE = re.compile(rf"\b(?:{_PLANT_BASED})", re.IGNORECASE)


def _sin_tildes(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in descompuesto if not unicodedata.combining(c))


def por_nombre(nombre: str | None) -> str | None:
    """El rubro que se deduce del nombre comercial, o None."""
    if not nombre:
        return None
    texto = _sin_tildes(str(nombre)).lower().strip()
    plant_based = bool(_PLANT_BASED_RE.search(texto))
    for rubro, patron in _REGLAS_NOMBRE_COMPILADAS:
        if not patron.search(texto):
            continue
        # "Hamburguesas de soja" dice "hamburguesa" y no es carne; "leche de
        # almendras" dice "leche" y no es un lácteo. En un sitio vegano ese
        # error se ve de lejos, así que la regla de origen animal se saltea y
        # sigue buscando una que sí corresponda.
        if plant_based and rubro in _ANIMAL:
            continue
        return rubro
    return None


def por_gondola(categoria_super: str | None) -> str | None:
    """El rubro que se deduce de la góndola del supermercado, o None."""
    if not categoria_super:
        return None
    clave = _sin_tildes(str(categoria_super)).strip().lower()
    return RUBRO_POR_GONDOLA.get(clave)


def por_tags(categories_tags: list[str] | None) -> str | None:
    """El rubro que sale de los `categories_tags` de OFF, o None."""
    if not categories_tags:
        return None
    tags = [t.lower() for t in categories_tags]
    for categoria, fragmentos in REGLAS:
        for tag in tags:
            # Se compara sin el prefijo de idioma ("en:", "es:", "fr:").
            cuerpo = tag.split(":", 1)[-1]
            if any(f in cuerpo for f in fragmentos):
                return categoria
    return None


def normalizar(categories_tags: list[str] | None, nombre: str | None = None,
               gondola: str | None = None) -> str:
    """Devuelve una categoría legible única, o "Otros" si nada resuelve.

    Las tres señales se consultan en orden de precisión: la taxonomía de OFF,
    el nombre del producto y —solo al final— la góndola del supermercado.
    """
    return (por_tags(categories_tags)
            or por_nombre(nombre)
            or por_gondola(gondola)
            or OTROS)


def todas() -> list[str]:
    rubros = [c for c, _ in REGLAS]
    for rubro, _ in REGLAS_NOMBRE:
        if rubro not in rubros:
            rubros.append(rubro)
    return rubros + [OTROS]
