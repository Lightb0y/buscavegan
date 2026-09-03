"""Capas 1 y 2 de clasificación: match directo en OFF y heurística de nombre.

Capa 1 usa las señales de Open Food Facts (declaración del fabricante y análisis
de ingredientes). Capa 2 resuelve lo que Capa 1 dejó sin estado, mirando el
nombre comercial y la categoría de SEPA.

Regla de seguridad transversal (SPEC.md §4): ante ambigüedad se devuelve
`revisar`, nunca `apto`.

Límite conocido de la Capa 2: el patrón "<producto> de <vegetal>" se toma como
apto (ej. "milanesa de soja"), y eso puede errar cuando el producto lleva otro
ingrediente animal que el nombre no menciona ("helado de almendras" con leche).
Es el precio de los casos obligatorios de SPEC.md §7; cuando OFF tiene el
producto, la Capa 1 manda y esta heurística ni se ejecuta.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

import config

# --- vocabulario -----------------------------------------------------------

# Las frases de varias palabras van primero: se buscan todas, pero leerlas en
# este orden hace más claro el motivo que se le muestra al usuario.
BLACKLIST = [
    "crema de leche", "clara de huevo", "suero de leche", "extracto de carne",
    "caldo de carne", "caldo de ave", "manteca de cerdo", "grasa vacuna",
    "grasa porcina", "dulce de leche",
    "leche", "manteca", "mantequilla", "nata", "queso", "yogur", "yoghurt",
    "huevo", "huevos", "yema", "miel", "gelatina", "caseina", "caseinato",
    "lactosa", "colageno", "sebo", "carmin", "cochinilla", "e120",
    "jamon", "panceta", "tocino", "pollo", "carne", "pescado", "atun",
    "merluza", "salmon", "anchoa", "camaron", "langostino", "marisco",
    "chorizo", "salchicha",
    # Cortes, embutidos y achuras de góndola argentina que caían en `revisar`
    # solo por no estar nombrados. No cambian la seguridad (nadie los iba a
    # ver como aptos), pero sí sacan ruido del bucket de "no sabemos".
    "ternera", "cordero", "cabrito", "conejo", "pavo", "pato", "codorniz",
    "morcilla", "salame", "salamin", "mortadela", "bondiola", "matambre",
    "higado", "molleja", "chinchulin", "menudencias", "achuras", "mondongo",
    "oleomargarina", "lisozima",
    "mejillon", "mejillones", "ostra", "vieira", "pulpo", "calamar",
    "crustaceo", "crustaceos", "trucha", "corvina", "lenguado", "caballa",
    "sardina", "surimi",
    # Preparaciones que en Argentina llevan lácteo o huevo salvo que declaren
    # lo contrario. Sin esto, "helado de banana" o "flan de vainilla" se
    # colarían como aptos por el nombre de su fruta. Las versiones veganas
    # existen, pero se anuncian: las atrapa antes la declaración explícita.
    "helado", "flan", "postre", "mousse", "budin", "bizcochuelo", "torta",
    "alfajor", "brownie", "cheesecake", "mayonesa", "crema",
    # Buena parte del catálogo argentino de OFF tiene el nombre en inglés
    # ("Whey Protein", "Milk Chocolate"). Sin esto se escapaban enteros: el
    # léxico en español no los ve.
    "whey", "milk", "cheese", "butter", "cream", "egg", "eggs", "honey",
    "gelatin", "gelatine", "collagen", "beef", "pork", "chicken", "bacon",
    "ham", "fish", "tuna", "shrimp", "lard", "casein", "lactose", "yogurt",
    "veal", "lamb", "poultry", "turkey", "buttermilk", "ghee", "milkfat",
]

# El ingles pone el modificador ANTES del sustantivo ("almond milk") y el
# espanol despues ("leche de almendras"). Para estas keywords, entonces, hay
# que mirar tambien hacia atras.
#
# La asimetria es deliberada: aplicar la ventana hacia atras en espanol seria
# peligroso, porque "chocolate con almendras y leche" quedaria neutralizado por
# unas almendras que no modifican a la leche.
BLACKLIST_EN = {
    "whey", "milk", "cheese", "butter", "cream", "egg", "eggs", "honey",
    "gelatin", "gelatine", "collagen", "beef", "pork", "chicken", "bacon",
    "ham", "fish", "tuna", "shrimp", "lard", "casein", "lactose", "yogurt",
    "veal", "lamb", "poultry", "turkey", "buttermilk", "ghee", "milkfat",
}

# Calificadores que anulan UNA keyword puntual, y solo esa. Van aparte del
# WHITELIST general porque no son intercambiables: "miel de caña" es melaza y
# no tiene abeja, pero un "helado de caña" no deja de ser un helado con leche.
WHITELIST_POR_KEYWORD = {
    "miel": ("cana", "maple", "arce", "agave", "palma", "maiz", "abedul"),
    "honey": ("cane", "maple", "agave"),
    # El cremor tártaro es un subproducto del vino, no un lácteo.
    "cream": ("tartar",),
    "crema": ("tartaro",),
}

# Subconjunto del blacklist que no es un ingrediente animal sino una
# preparacion que suele llevarlo: cambia el texto que se le muestra al usuario.
PREPARACIONES_CON_LACTEO = {
    "helado", "flan", "postre", "mousse", "budin", "bizcochuelo", "torta",
    "alfajor", "brownie", "cheesecake", "mayonesa",
}

WHITELIST = [
    "coco", "almendra", "almendras", "soja", "soya", "avena", "arroz",
    "quinoa", "quinua", "castana de caju", "caju", "girasol", "sesamo",
    "mani", "garbanzo", "vegetal", "vegetales", "vegano", "vegana",
    "plant", "base de plantas", "anacardo", "avellana", "nuez", "nueces",
    # Equivalentes en inglés, para que "almond milk" o "soy protein" se
    # neutralicen igual que sus versiones en español.
    "almond", "coconut", "soy", "oat", "cashew", "peanut", "hazelnut",
    "vegan", "vegetable", "pea", "hemp",
]

# Declaración explícita: alcanza por sí sola para marcar apto.
VEGAN_CLAIM = [
    "vegano", "vegana", "veganos", "veganas", "vegan", "plant based",
    "100% vegetal", "apto vegano", "base de plantas",
]

# Productos que **son** un vegetal o un mineral. Para estos el nombre no es una
# pista sino la identidad: que una sal fina o un paquete de garbanzos tuviera
# origen animal sería la sorpresa, no lo esperable.
#
# Criterio de admisión, deliberadamente angosto: solo entra lo que en góndola
# argentina no tiene versión con derivado animal. Por eso NO están acá el
# cappuccino (lleva leche en polvo), las pastas (pueden llevar huevo), el pan,
# las galletitas ni el chocolate.
COMMODITIES_VEGANAS = [
    # minerales y agua
    "agua", "agua mineral", "soda", "sal", "sal fina", "sal gruesa",
    "sal marina", "bicarbonato",
    # azúcares y harinas
    "azucar", "harina", "semola", "polenta", "almidon", "fecula", "salvado",
    "levadura",
    # granos y legumbres
    "arroz", "avena", "quinoa", "cebada", "trigo", "maiz", "garbanzo",
    "garbanzos", "chickpeas", "lenteja", "lentejas", "poroto", "porotos",
    "arveja", "arvejas", "soja",
    # infusiones (el café con leche ya lo atrapa el blacklist)
    "yerba", "yerba mate", "te", "cafe",
    # aceites y vinagres
    "aceite", "aceite de oliva", "aceite de girasol", "aceite de maiz",
    "vinagre",
    # frutas, verduras y conservas vegetales
    "tomate", "pure de tomate", "choclo", "palmito", "aceituna", "aceitunas",
    "espinaca", "acelga", "brocoli", "zanahoria", "papa", "papas", "batata",
    "cebolla", "zapallo", "chaucha", "lechuga", "morron", "berenjena",
    "zucchini", "manzana", "banana", "naranja", "mandarina", "pera", "uva",
    "durazno", "ciruela", "higo", "datil", "pasas de uva", "limon",
    # frutos secos y semillas
    "mani", "almendra", "almendras", "nuez", "nueces", "castana", "caju",
    "anacardo", "avellana", "pistacho", "semillas", "chia", "lino", "sesamo",
    "girasol",
    # especias y hierbas
    "canela", "comino", "oregano", "pimienta", "pimenton", "laurel",
    "nuez moscada", "curcuma", "jengibre", "perejil", "albahaca", "romero",
    "tomillo", "curry", "aji molido", "clavo de olor",
    # conservas y untables que son la fruta o la verdura procesada
    "pure de tomate", "tomate triturado", "tomate perita", "mermelada",
]

_COMMODITIES_SIMPLES = {c for c in COMMODITIES_VEGANAS if " " not in c}

CATEGORIAS_NO_APTAS = [
    "carnes", "carniceria", "fiambres", "embutidos", "lacteos", "lacteo",
    "huevos", "pescaderia", "pescados y mariscos", "quesos",
]
CATEGORIAS_APTAS = [
    "legumbres secas", "frutas y verduras frescas", "frutas y verduras",
    "verduleria", "harinas",
]
# "Arroz y pastas secas" queda afuera a propósito: las pastas pueden llevar
# huevo, así que caen en `revisar` en vez de `apto`.

WINDOW_WORDS = 3  # ventana posterior donde un modificador vegetal anula el match

FUENTE_OFF_LABEL = "off_label"
FUENTE_OFF_ANALYSIS = "off_analysis"
FUENTE_HEURISTICA = "heuristica"
FUENTE_SIN_DATOS = "sin_datos"


@dataclass
class Decision:
    estado: str
    fuente: str
    motivo: str
    confianza: float | None = None

    @property
    def resuelto(self) -> bool:
        return self.estado != config.REVISAR


# --- normalización ---------------------------------------------------------

def normalize(text: str | None) -> str:
    """Minúsculas, sin tildes y con espacios colapsados."""
    if not text:
        return ""
    text = unicodedata.normalize("NFD", str(text))
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.lower().replace("-", " ")
    return re.sub(r"\s+", " ", text).strip()


def _contains(haystack: str, needle: str) -> bool:
    return re.search(rf"\b{re.escape(needle)}\b", haystack) is not None


def _window_after(text: str, end: int, words: int = WINDOW_WORDS) -> str:
    return " ".join(text[end:].split()[:words])


def _window_before(text: str, start: int, words: int = 2) -> str:
    return " ".join(text[:start].split()[-words:])


# Palabras de relleno que no cuentan al buscar la cabeza del nombre.
_RELLENO = {"de", "del", "la", "el", "los", "las", "con", "sin", "y", "al",
            "en", "x", "un", "una"}


def _commodity_cabeza(texto: str) -> str | None:
    """Devuelve la commodity solo si **encabeza** el nombre del producto.

    La distinción importa y no es cosmética: en "Yogurisimo banana" o
    "Galletitas de avena" la palabra vegetal es el sabor o un ingrediente
    menor, y el producto es un lácteo o una galletita que probablemente lleve
    manteca. Solo cuando la commodity es la cabeza del nombre ("Sal fina",
    "Acelga congelada") el producto *es* esa commodity.

    El blacklist no alcanza para atrapar esos casos porque busca palabras
    enteras: "yogur" no matchea dentro de "Yogurisimo".
    """
    tokens = [t for t in texto.split() if t not in _RELLENO]
    if not tokens:
        return None

    # Frases de varias palabras: tienen que abrir el nombre.
    for c in COMMODITIES_VEGANAS:
        if " " in c and texto.startswith(c):
            return c
    return tokens[0] if tokens[0] in _COMMODITIES_SIMPLES else None


# --- Capa 1: Open Food Facts ----------------------------------------------

def classify_off(product: dict | None) -> Decision:
    """Capa 1. `product` es el payload cacheado de OFF (o None si no matcheó)."""
    if not product:
        return Decision(config.REVISAR, FUENTE_SIN_DATOS,
                        "El producto no está en Open Food Facts")

    labels = set(product.get("labels_tags") or [])
    analysis = set(product.get("ingredients_analysis_tags") or [])

    # La declaración del fabricante es la señal de mayor confianza.
    if "en:vegan" in labels:
        return Decision(config.APTO, FUENTE_OFF_LABEL,
                        "Declarado vegano por el fabricante")
    if "en:non-vegan" in analysis:
        if "en:vegetarian" in analysis:
            return Decision(config.VEGETARIANO, FUENTE_OFF_ANALYSIS,
                            "Análisis de ingredientes: vegetariano, no vegano")
        return Decision(config.NO_APTO, FUENTE_OFF_ANALYSIS,
                        "Análisis de ingredientes (Open Food Facts): no vegano")
    if "en:non-vegetarian" in analysis:
        return Decision(config.NO_APTO, FUENTE_OFF_ANALYSIS,
                        "Análisis de ingredientes: contiene ingredientes animales")
    if "en:vegan" in analysis:
        return Decision(config.APTO, FUENTE_OFF_ANALYSIS,
                        "Confirmado por análisis de ingredientes (Open Food Facts)")
    if "en:vegetarian" in analysis:
        return Decision(config.VEGETARIANO, FUENTE_OFF_ANALYSIS,
                        "Análisis de ingredientes: vegetariano")
    # maybe-* y *-status-unknown no resuelven: pasa a Capa 2.
    return Decision(config.REVISAR, FUENTE_SIN_DATOS,
                    "Open Food Facts no pudo determinar el estado")


# --- Capa 2: heurística ----------------------------------------------------

def _categoria_decision(categoria: str | None) -> Decision | None:
    cat = normalize(categoria)
    if not cat:
        return None
    for c in CATEGORIAS_NO_APTAS:
        if c in cat:
            return Decision(config.NO_APTO, FUENTE_HEURISTICA,
                            f"Rubro de origen animal: {categoria}")
    for c in CATEGORIAS_APTAS:
        if c in cat:
            return Decision(config.APTO, FUENTE_HEURISTICA,
                            f"Rubro de origen vegetal: {categoria}")
    return None


def classify_name(nombre: str, marca: str | None = None,
                  categoria: str | None = None) -> Decision:
    """Capa 2. Heurística sobre nombre + marca + categoría."""
    texto = normalize(f"{nombre} {marca or ''}")

    # 1. Declaración explícita en el nombre: manda sobre todo lo demás.
    for claim in VEGAN_CLAIM:
        if _contains(texto, claim):
            return Decision(config.APTO, FUENTE_HEURISTICA,
                            f'El nombre declara "{claim}"')

    # 2. Keywords no veganas, con la ventana que las puede anular.
    hits_anulados: list[tuple[str, str]] = []
    for kw in BLACKLIST:
        for m in re.finditer(rf"\b{re.escape(kw)}\b", texto):
            ventana = _window_after(texto, m.end())
            if kw in BLACKLIST_EN:
                ventana += " " + _window_before(texto, m.start())
            candidatos = WHITELIST + list(WHITELIST_POR_KEYWORD.get(kw, ()))
            modificador = next(
                (w for w in candidatos if _contains(ventana, w)), None
            )
            if modificador is None:
                cat_dec = _categoria_decision(categoria)
                if cat_dec and cat_dec.estado == config.APTO:
                    # Nombre y rubro se contradicen: no arriesgamos un apto.
                    return Decision(
                        config.REVISAR, FUENTE_HEURISTICA,
                        f'"{kw}" en el nombre contradice el rubro "{categoria}"')
                if kw in PREPARACIONES_CON_LACTEO:
                    return Decision(
                        config.NO_APTO, FUENTE_HEURISTICA,
                        f'"{kw}" lleva lacteo o huevo salvo que declare lo '
                        f'contrario')
                return Decision(config.NO_APTO, FUENTE_HEURISTICA,
                                f'"{kw}" es de origen animal')
            hits_anulados.append((kw, modificador))

    if hits_anulados:
        kw, mod = hits_anulados[0]
        # El orden de las palabras cambia con el idioma: "almond milk" pero
        # "leche de almendras".
        frase = f"{mod} {kw}" if kw in BLACKLIST_EN else f"{kw} de {mod}"
        return Decision(config.APTO, FUENTE_HEURISTICA,
                        f'"{frase}": versión vegetal')

    # 3. Sustituto vegetal explícito sin ninguna keyword animal.
    m = re.search(r"\b(?:de|a base de|con)\s+([a-z]+(?: de [a-z]+)?)", texto)
    if m and any(_contains(m.group(1), w) for w in WHITELIST):
        return Decision(config.APTO, FUENTE_HEURISTICA,
                        f'Base vegetal declarada: "{m.group(1)}"')

    # 4. Commodity vegetal o mineral: el producto ES el ingrediente.
    #    Mismo principio que los rubros inequívocos de SPEC.md §4.4, aplicado a
    #    la identidad del producto. No es "no encontré nada animal" (eso sería
    #    `revisar`): es que la sal es un mineral y el garbanzo una legumbre.
    #    Va después del blacklist a propósito, para que "arroz con leche" o
    #    "café con leche" queden atrapados antes de llegar acá.
    commodity = _commodity_cabeza(texto)
    if commodity:
        return Decision(config.APTO, FUENTE_HEURISTICA,
                        f'"{commodity}" es de origen vegetal o mineral')

    # 4. Rubros inequívocos.
    cat_dec = _categoria_decision(categoria)
    if cat_dec:
        return cat_dec

    # 5. Sin señal: que decida la Capa 3, y si no, revisión humana.
    return Decision(config.REVISAR, FUENTE_SIN_DATOS,
                    "Sin datos suficientes para clasificar por nombre")


def classify(nombre: str, marca: str | None = None, categoria: str | None = None,
             off_product: dict | None = None) -> Decision:
    """Capa 1 y, si no resuelve, Capa 2."""
    decision = classify_off(off_product)
    if decision.resuelto:
        return decision
    return classify_name(nombre, marca, categoria)
