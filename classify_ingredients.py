"""Clasificación vegana por **lista de ingredientes** (señal principal del proyecto).

Es la capa que más pesa: el nombre comercial miente u omite, pero la lista de
ingredientes es la declaración legal de lo que el producto tiene adentro.

Cómo funciona
-------------
1. Se parte el texto en ingredientes individuales (comas, punto y coma, paréntesis).
2. Cada ingrediente se compara contra tres léxicos:
   - `ANIMAL`: de origen animal cierto → `no_apto` o `vegetariano` según el caso.
   - `AMBIGUO`: puede ser animal o vegetal (INS 471, aroma natural...) → `revisar`.
   - `VEGANO`: reconocido como vegetal/mineral/sintético → suma cobertura.
3. El veredicto sale de la peor señal encontrada, y `apto` exige además que se
   haya reconocido una fracción mínima de la lista (`COBERTURA_MINIMA`): si media
   lista son ingredientes que no conocemos, no afirmamos nada.

Particularidades argentinas
---------------------------
- El código de aditivos que se usa acá es **INS**, no la E europea: se aceptan
  ambas formas ("INS 120", "E120").
- Se distingue "contiene leche" (declaración de contenido, cuenta) de
  "puede contener trazas de leche" (contaminación cruzada, no cuenta como
  ingrediente: se informa aparte y no cambia el veredicto).
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

import config

FUENTE_INGREDIENTES = "ingredientes"

# Fracción mínima de ingredientes reconocidos para animarse a decir `apto`.
COBERTURA_MINIMA = 0.60
# Listas muy cortas ("Maní") son válidas aunque la fracción sea sensible.
MIN_INGREDIENTES = 1


# --- léxicos ---------------------------------------------------------------
# Cada entrada: patrón (regex sobre el ingrediente normalizado) -> (estado, etiqueta)
# `vegetariano` = sin carne pero con derivado animal (lácteo, huevo, miel).
# `no_apto` = carne, pescado, gelatina, insectos y derivados de faena.

ANIMAL: list[tuple[str, tuple[str, str]]] = [
    # --- lácteos ---------------------------------------------------------
    (r"\bleche(s)?\b(?! de (coco|almendra|soja|soya|avena|arroz|mani|castana|caju|quinoa|nuez|anacardo|girasol|sesamo|vegetal))",
     (config.VEGETARIANO, "leche")),
    (r"\bleche en polvo\b", (config.VEGETARIANO, "leche en polvo")),
    (r"\b(suero|lactosuero|suero de leche)\b", (config.VEGETARIANO, "suero lácteo")),
    (r"\blactosa\b", (config.VEGETARIANO, "lactosa")),
    (r"\bcase[ií]n(a|ato)?", (config.VEGETARIANO, "caseína")),
    (r"\bl[aá]cteo?s?\b", (config.VEGETARIANO, "derivado lácteo")),
    (r"\bcrema\b(?! vegetal| de (coco|soja|almendra))", (config.VEGETARIANO, "crema")),
    (r"\bnata\b", (config.VEGETARIANO, "nata")),
    (r"\bqueso\b(?! vegano| vegetal)", (config.VEGETARIANO, "queso")),
    (r"\bricota\b", (config.VEGETARIANO, "ricota")),
    (r"\byog(ur|hurt|urt)\b", (config.VEGETARIANO, "yogur")),
    (r"\bmante(ca|quilla)\b(?! de (mani|cacao|coco|almendra|castana|caju|nuez|semillas))",
     (config.VEGETARIANO, "manteca")),
    (r"\bgrasa but[ií]rica\b|\bbutter ?oil\b", (config.VEGETARIANO, "grasa butírica")),
    (r"\bdulce de leche\b", (config.VEGETARIANO, "dulce de leche")),
    (r"\bkefir\b", (config.VEGETARIANO, "kéfir")),
    (r"\bcuajo\b", (config.NO_APTO, "cuajo (enzima animal)")),

    # --- huevo -----------------------------------------------------------
    (r"\bhuevo?s?\b", (config.VEGETARIANO, "huevo")),
    (r"\b(clara|yema)s? de huevo\b", (config.VEGETARIANO, "huevo")),
    (r"\bovo(albumina|producto)", (config.VEGETARIANO, "derivado de huevo")),
    (r"\balb[uú]mina\b", (config.VEGETARIANO, "albúmina")),
    (r"\blecitina de huevo\b|\bins 322 de huevo\b", (config.VEGETARIANO, "lecitina de huevo")),

    # --- miel y abejas ---------------------------------------------------
    (r"\bmiel\b", (config.VEGETARIANO, "miel")),
    (r"\bjalea real\b", (config.VEGETARIANO, "jalea real")),
    (r"\bpropoleo\b", (config.VEGETARIANO, "propóleo")),
    (r"\bcera de abejas?\b|\bins 901\b|\be ?901\b", (config.VEGETARIANO, "cera de abejas")),

    # --- carne, pescado y faena -----------------------------------------
    (r"\bgelatina\b(?! vegetal)|\bins 441\b|\be ?441\b", (config.NO_APTO, "gelatina")),
    (r"\bcol[aá]geno\b", (config.NO_APTO, "colágeno")),
    (r"\bcarne\b|\bextracto de carne\b", (config.NO_APTO, "carne")),
    (r"\bgrasa (bovina|vacuna|porcina|animal|de cerdo|de vaca)\b",
     (config.NO_APTO, "grasa animal")),
    (r"\boleomargarina bovina\b", (config.NO_APTO, "oleomargarina bovina")),
    (r"\bsebo\b", (config.NO_APTO, "sebo")),
    (r"\bmanteca de cerdo\b", (config.NO_APTO, "manteca de cerdo")),
    (r"\b(pollo|cerdo|vacuno|bovino|porcino|jamon|panceta|tocino|chorizo)\b",
     (config.NO_APTO, "carne")),
    (r"\b(pescado|atun|merluza|salmon|anchoa|sardina|camaron|langostino|marisco|calamar)\b",
     (config.NO_APTO, "pescado o marisco")),
    (r"\baceite de pescado\b|\bomega ?3 de pescado\b", (config.NO_APTO, "aceite de pescado")),
    (r"\bcaldo de (carne|ave|pollo|pescado)\b", (config.NO_APTO, "caldo de origen animal")),
    (r"\bfosfato de hueso\b|\bins 542\b|\be ?542\b", (config.NO_APTO, "fosfato de hueso")),

    # --- insectos ---------------------------------------------------------
    (r"\bcarmin\b|\bcochinilla\b|\bins 120\b|\be ?120\b|\bacido carminico\b",
     (config.NO_APTO, "carmín (cochinilla)")),
    (r"\bgoma laca\b|\bshellac\b|\bins 904\b|\be ?904\b", (config.NO_APTO, "goma laca")),
]

# Puede ser de origen animal o vegetal: no alcanza para condenar ni para absolver.
AMBIGUO: list[tuple[str, str]] = [
    (r"\bins 471\b|\be ?471\b|\bmono ?y ?diglic[eé]ridos\b|\bmonogliceridos\b",
     "INS 471 (mono y diglicéridos): puede ser de grasa animal o vegetal"),
    (r"\bins 472\b|\be ?472", "INS 472: puede derivar de grasa animal o vegetal"),
    (r"\bins 570\b|\bacido estearico\b|\bestearato\b",
     "ácido esteárico / estearatos: pueden ser de sebo animal"),
    (r"\bins 631\b|\binosinato\b|\bins 627\b|\bguanilato\b",
     "inosinato/guanilato: suelen obtenerse de pescado o carne"),
    (r"\bins 920\b|\bl-?cisteina\b", "L-cisteína: puede provenir de plumas o pelo"),
    (r"\blecitina\b(?! de (soja|soya|girasol))|\bins 322\b|\be ?322\b",
     "lecitina sin origen declarado (suele ser de soja, pero no está aclarado)"),
    (r"\baroma(s|tizante)? natural(es)?\b", "aroma natural sin origen declarado"),
    (r"\bsaborizante(s)? natural(es)?\b", "saborizante natural sin origen declarado"),
    (r"\bvitamina d3?\b|\bcolecalciferol\b", "vitamina D3: suele venir de lanolina"),
    (r"\bglicerina\b|\bglicerol\b|\bins 422\b", "glicerina: puede ser animal o vegetal"),
    (r"\bfermento(s)?\b|\bcultivos? l[aá]ctico", "fermentos de origen no declarado"),
    (r"\benzimas?\b", "enzimas de origen no declarado"),
    (r"\bazucar\b.*\brefinad", "azúcar refinada: puede filtrarse con carbón de hueso"),
]

# Reconocidos como vegetales, minerales o sintéticos: suman cobertura y permiten
# afirmar `apto` con fundamento en vez de por ausencia de evidencia.
VEGANO = [
    r"\bagua\b", r"\bazucar\b", r"\bsal\b", r"\bharina", r"\btrigo\b", r"\bmaiz\b",
    r"\barroz\b", r"\bavena\b", r"\bcebada\b", r"\bcenteno\b", r"\bquinoa\b",
    r"\bsoja\b", r"\bsoya\b", r"\bgarbanzo", r"\blenteja", r"\bporoto",
    r"\barveja", r"\bmani\b", r"\balmendra", r"\bnuez\b", r"\bnueces\b",
    r"\bcastana", r"\bcaju\b", r"\banacardo", r"\bavellana", r"\bpistacho",
    r"\bsemillas?\b", r"\bgirasol\b", r"\bsesamo\b", r"\bchia\b", r"\blino\b",
    r"\baceite vegetal\b", r"\baceite de (girasol|maiz|soja|oliva|canola|algodon|palma|coco)\b",
    r"\bgrasa vegetal\b", r"\bmargarina vegetal\b", r"\bcacao\b", r"\bchocolate\b",
    r"\bcafe\b", r"\bte\b", r"\byerba\b", r"\bfrutas?\b", r"\bverduras?\b",
    r"\btomate", r"\bpapa\b", r"\bcebolla\b", r"\bajo\b", r"\bmorron",
    r"\bzanahoria", r"\bespinaca", r"\bnaranja", r"\blimon\b", r"\bmanzana",
    r"\bbanana", r"\bfrutilla", r"\bdurazno", r"\bpera\b", r"\buva\b",
    r"\baceituna", r"\bpalta\b", r"\bcoco\b", r"\bvainilla\b", r"\bcanela\b",
    r"\bpimienta\b", r"\boregano\b", r"\bcomino\b", r"\bperejil\b", r"\balbahaca\b",
    r"\bvinagre\b", r"\balcohol\b", r"\bmalta\b", r"\blevadura\b",
    r"\balmidon", r"\bfecula", r"\bglucosa\b", r"\bfructosa\b", r"\bdextrosa\b",
    r"\bjarabe\b", r"\bmaltodextrina\b", r"\bgoma (xantica|guar|arabiga|garrofin)\b",
    r"\bpectina\b", r"\bcarragenina\b", r"\bagar\b", r"\bcelulosa\b",
    r"\bacido (citrico|ascorbico|malico|tartarico|lactico|folico|fosforico)\b",
    r"\bcitrato\b", r"\bbicarbonato\b", r"\bcarbonato\b", r"\bsulfato\b",
    r"\bfosfato de (sodio|potasio|calcio)\b", r"\bcloruro\b", r"\bnitrato\b",
    r"\bhierro\b", r"\bzinc\b", r"\bcalcio\b", r"\bpotasio\b", r"\bsodio\b",
    r"\bmagnesio\b", r"\bniacina\b", r"\btiamina\b", r"\briboflavina\b",
    r"\bvitamina [abce]\d*\b", r"\bacido pantotenico\b", r"\bpiridoxina\b",
    r"\bcianocobalamina\b", r"\bbetacaroteno\b", r"\bcurcuma\b", r"\bannato\b",
    r"\burucu\b", r"\bcaramelo\b", r"\bproteina (vegetal|de soja|de arveja|de trigo)\b",
    r"\bgluten\b", r"\bsorbato\b", r"\bbenzoato\b", r"\bsorbitol\b", r"\bmanitol\b",
    r"\bstevia\b", r"\bsucralosa\b", r"\baspartamo\b", r"\bacesulfamo\b",
    r"\bsacarina\b", r"\bciclamato\b", r"\bemulsionante\b", r"\bespesante\b",
    r"\bestabilizante\b", r"\bconservante\b", r"\bacidulante\b", r"\bantioxidante\b",
    r"\bcolorante\b", r"\bhumectante\b", r"\bregulador de acidez\b", r"\bleudante\b",
]

# Frases que hablan de contaminación cruzada, no de composición.
TRAZAS_RE = re.compile(
    r"(puede(n)? contener|elaborado en (una )?(linea|planta|establecimiento)|"
    r"trazas de|contiene trazas)[^.;]*", re.IGNORECASE)

ANIMAL_RE = [(re.compile(p), v) for p, v in ANIMAL]
AMBIGUO_RE = [(re.compile(p), v) for p, v in AMBIGUO]
VEGANO_RE = [re.compile(p) for p in VEGANO]


# Vocabulario en inglés: los `ingredients_tags` de OFF vienen mayormente en
# inglés ("en:wheat-flour"), así que sin esto la cobertura se desploma y todo
# termina en `revisar` por no reconocer ingredientes que son obviamente
# vegetales. Los de origen animal ya están cubiertos por ANIMAL_TAGS.
VEGANO_EN = [
    r"\bwater\b", r"\bsugar\b", r"\bsalt\b", r"\bflour\b", r"\bwheat\b",
    r"\bcorn\b", r"\bmaize\b", r"\brice\b", r"\boat", r"\bbarley\b",
    r"\brye\b", r"\bsoy", r"\bbean", r"\bpea\b", r"\bpeas\b", r"\blentil",
    r"\bchickpea", r"\bpeanut", r"\balmond", r"\bnut\b", r"\bnuts\b",
    r"\bcashew", r"\bhazelnut", r"\bwalnut", r"\bpistachio", r"\bseed",
    r"\bsunflower", r"\bsesame", r"\bchia\b", r"\bflax", r"\bquinoa\b",
    r"\bvegetable oil\b", r"\bvegetable fat\b", r"\bsunflower oil\b",
    r"\bpalm oil\b", r"\bolive oil\b", r"\bcanola\b", r"\brapeseed\b",
    r"\bcocoa\b", r"\bcocoa butter\b", r"\bchocolate\b", r"\bcoffee\b",
    r"\btea\b", r"\bfruit", r"\bvegetable", r"\btomato", r"\bpotato",
    r"\bonion", r"\bgarlic\b", r"\bcarrot", r"\bspinach\b", r"\bpepper",
    r"\borange", r"\blemon\b", r"\bapple", r"\bbanana", r"\bstrawberr",
    r"\bpeach", r"\bpear\b", r"\bgrape", r"\bolive", r"\bavocado\b",
    r"\bcoconut", r"\bvanilla\b", r"\bcinnamon\b", r"\boregano\b",
    r"\bcumin\b", r"\bparsley\b", r"\bbasil\b", r"\bmint\b", r"\bginger\b",
    r"\bvinegar\b", r"\balcohol\b", r"\bmalt\b", r"\byeast\b", r"\bstarch\b",
    r"\bglucose\b", r"\bfructose\b", r"\bdextrose\b", r"\bsyrup\b",
    r"\bmaltodextrin\b", r"\bxanthan\b", r"\bguar\b", r"\bgum arabic\b",
    r"\bpectin\b", r"\bcarrageenan\b", r"\bagar\b", r"\bcellulose\b",
    r"\bcitric acid\b", r"\bascorbic acid\b", r"\bmalic acid\b",
    r"\btartaric acid\b", r"\blactic acid\b", r"\bfolic acid\b",
    r"\bphosphoric acid\b", r"\bcitrate\b", r"\bbicarbonate\b",
    r"\bcarbonate\b", r"\bsulphate\b", r"\bsulfate\b", r"\bchloride\b",
    r"\biron\b", r"\bzinc\b", r"\bcalcium\b", r"\bpotassium\b", r"\bsodium\b",
    r"\bmagnesium\b", r"\bniacin\b", r"\bthiamin", r"\briboflavin\b",
    r"\bvitamin [abce]\d*\b", r"\bfolate\b", r"\bpyridoxine\b",
    r"\bbeta carotene\b", r"\bturmeric\b", r"\bannatto\b", r"\bcaramel\b",
    r"\bvegetable protein\b", r"\bsoy protein\b", r"\bpea protein\b",
    r"\bwheat protein\b", r"\bgluten\b", r"\bsorbate\b", r"\bbenzoate\b",
    r"\bsorbitol\b", r"\bmannitol\b", r"\bstevia\b", r"\bsucralose\b",
    r"\baspartame\b", r"\bacesulfame\b", r"\bsaccharin\b", r"\bcyclamate\b",
    r"\bemulsifier\b", r"\bthickener\b", r"\bstabiliser\b", r"\bstabilizer\b",
    r"\bpreservative\b", r"\bacidifier\b", r"\bantioxidant\b", r"\bcolour\b",
    r"\bcolor\b", r"\bhumectant\b", r"\braising agent\b", r"\bacidity regulator\b",
    r"\bspice", r"\bherb", r"\bextract\b", r"\bconcentrate\b", r"\bpuree\b",
    r"\bjuice\b", r"\bpowder\b", r"\bpaste\b", r"\bfibre\b", r"\bfiber\b",
    r"\bbran\b", r"\bgerm\b", r"\bsemolina\b", r"\bcereal", r"\bgrain",
    r"\blegume", r"\bmushroom", r"\balgae\b", r"\bseaweed\b", r"\bcaffeine\b",
    # Los aditivos numerados de riesgo (120, 441, 471, 542, 901, 904, 920...)
    # ya estan enumerados en ANIMAL_TAGS y AMBIGUO_TAGS, asi que el resto de la
    # serie E/INS se cuenta como reconocido para no castigar la cobertura.
    r"\be\d{3}[a-z]?\b",
]

VEGANO_RE += [re.compile(p) for p in VEGANO_EN]

SEVERIDAD = {config.APTO: 0, config.VEGETARIANO: 1, config.NO_APTO: 2}


@dataclass
class AnalisisIngredientes:
    estado: str
    motivo: str
    detectados: list[str] = field(default_factory=list)
    ambiguos: list[str] = field(default_factory=list)
    cobertura: float = 0.0
    n_ingredientes: int = 0
    trazas: list[str] = field(default_factory=list)
    fuente: str = FUENTE_INGREDIENTES

    @property
    def resuelto(self) -> bool:
        return self.estado != config.REVISAR


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFD", str(text))
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.lower().replace("_", " ")
    # "INS322" / "E-322" -> "ins 322" / "e 322"
    text = re.sub(r"\b(ins|e)[\s.-]*(\d{3})\b", r"\1 \2", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_ingredients(text: str) -> tuple[list[str], list[str]]:
    """Devuelve (ingredientes, frases_de_trazas).

    Los paréntesis se aplanan: "harina (hierro, niacina)" son tres ingredientes,
    porque cualquiera de ellos puede ser el que delate un origen animal.
    """
    if not text:
        return [], []
    norm = normalize(text)

    trazas = [m.group(0).strip() for m in TRAZAS_RE.finditer(norm)]
    norm = TRAZAS_RE.sub(" ", norm)

    plano = re.sub(r"[()\[\]{}]", ",", norm)
    partes = re.split(r"[,;:.]|\band\b|\by\b(?= )", plano)

    out = []
    for p in partes:
        p = re.sub(r"\d+([.,]\d+)?\s*%", " ", p)  # porcentajes
        p = re.sub(r"\s+", " ", p).strip(" -*·•")
        if len(p) >= 2 and not p.isdigit():
            out.append(p)
    return out, trazas


def _match(ingrediente: str) -> tuple[str, str] | None:
    for rx, val in ANIMAL_RE:
        if rx.search(ingrediente):
            return val
    return None


def analyze(text: str | None) -> AnalisisIngredientes:
    """Clasifica un producto a partir de su lista de ingredientes."""
    ingredientes, trazas = parse_ingredients(text or "")
    if len(ingredientes) < MIN_INGREDIENTES:
        return AnalisisIngredientes(
            config.REVISAR, "El producto no publica su lista de ingredientes",
            fuente="sin_datos")

    detectados: list[str] = []
    ambiguos: list[str] = []
    reconocidos = 0
    peor = config.APTO
    motivo_peor = ""

    for ing in ingredientes:
        hit = _match(ing)
        if hit:
            estado, etiqueta = hit
            if etiqueta not in detectados:
                detectados.append(etiqueta)
            if SEVERIDAD[estado] > SEVERIDAD[peor]:
                peor, motivo_peor = estado, etiqueta
            reconocidos += 1
            continue

        amb = next((msg for rx, msg in AMBIGUO_RE if rx.search(ing)), None)
        if amb:
            if amb not in ambiguos:
                ambiguos.append(amb)
            reconocidos += 1
            continue

        if any(rx.search(ing) for rx in VEGANO_RE):
            reconocidos += 1

    cobertura = reconocidos / len(ingredientes)
    base = dict(detectados=detectados, ambiguos=ambiguos, cobertura=round(cobertura, 2),
                n_ingredientes=len(ingredientes), trazas=trazas)

    if peor == config.NO_APTO:
        return AnalisisIngredientes(
            config.NO_APTO, f"Contiene {motivo_peor}, de origen animal", **base)

    if peor == config.VEGETARIANO:
        return AnalisisIngredientes(
            config.VEGETARIANO,
            f"Contiene {motivo_peor}: es vegetariano pero no vegano", **base)

    # Sin ingrediente animal. Antes de decir `apto`, exigimos entender la lista.
    if ambiguos:
        return AnalisisIngredientes(
            config.REVISAR,
            f"Sin ingredientes animales claros, pero hay {len(ambiguos)} de origen "
            f"no declarado: {ambiguos[0]}", **base)

    if cobertura < COBERTURA_MINIMA:
        return AnalisisIngredientes(
            config.REVISAR,
            f"Solo se reconoció el {cobertura:.0%} de los ingredientes: "
            "no alcanza para afirmar que sea vegano", **base)

    return AnalisisIngredientes(
        config.APTO,
        f"Ningún ingrediente de origen animal en los {len(ingredientes)} "
        f"declarados (se reconoció el {cobertura:.0%})", **base)


# ---------------------------------------------------------------------------
# Análisis sobre `ingredients_tags` (taxonomía normalizada de OFF)
# ---------------------------------------------------------------------------
# La API nueva de OFF (search-a-licious) no expone `ingredients_text`, pero sí
# `ingredients_tags`: la lista de ingredientes ya parseada y mapeada a su
# taxonomía ("en:milk", "en:wheat-flour", "es:azucar-organica"). Para clasificar
# es mejor materia prima que el texto crudo: viene sin erratas, sin
# abreviaturas y con un ingrediente por entrada.
#
# Al ser un tag = un ingrediente, el calificador vegetal se busca dentro del
# propio tag ("en:coconut-milk" es leche de coco), sin necesidad de la ventana
# de palabras que usa el texto libre.

CALIFICADORES_VEGETALES = [
    "coconut", "soy", "soya", "almond", "oat", "rice", "hazelnut", "cashew",
    "peanut", "walnut", "sesame", "sunflower", "hemp", "pea-", "quinoa",
    "vegetable", "vegetal", "plant", "coco", "soja", "almendra", "avena",
    "arroz", "mani", "castana", "caju", "girasol", "sesamo", "vegana",
    "vegano", "avellana", "nuez", "arveja",
]

ANIMAL_TAGS: dict[str, tuple[str, str]] = {
    # lácteos
    "milk": (config.VEGETARIANO, "leche"),
    "dairy": (config.VEGETARIANO, "lácteos"),
    "whey": (config.VEGETARIANO, "suero lácteo"),
    "whey-powder": (config.VEGETARIANO, "suero lácteo en polvo"),
    "casein": (config.VEGETARIANO, "caseína"),
    "caseinate": (config.VEGETARIANO, "caseinato"),
    "lactose": (config.VEGETARIANO, "lactosa"),
    "butter": (config.VEGETARIANO, "manteca"),
    "butterfat": (config.VEGETARIANO, "grasa butírica"),
    "cream": (config.VEGETARIANO, "crema"),
    "cheese": (config.VEGETARIANO, "queso"),
    "yogurt": (config.VEGETARIANO, "yogur"),
    "milk-fat": (config.VEGETARIANO, "grasa láctea"),
    "milk-powder": (config.VEGETARIANO, "leche en polvo"),
    "milk-proteins": (config.VEGETARIANO, "proteínas lácteas"),
    "skimmed-milk": (config.VEGETARIANO, "leche descremada"),
    "whole-milk": (config.VEGETARIANO, "leche entera"),
    "condensed-milk": (config.VEGETARIANO, "leche condensada"),
    "sweetened-condensed-milk": (config.VEGETARIANO, "leche condensada"),
    "dulce-de-leche": (config.VEGETARIANO, "dulce de leche"),
    # huevo
    "egg": (config.VEGETARIANO, "huevo"),
    "eggs": (config.VEGETARIANO, "huevo"),
    "egg-white": (config.VEGETARIANO, "clara de huevo"),
    "egg-yolk": (config.VEGETARIANO, "yema de huevo"),
    "albumin": (config.VEGETARIANO, "albúmina"),
    # abejas
    "honey": (config.VEGETARIANO, "miel"),
    "royal-jelly": (config.VEGETARIANO, "jalea real"),
    "beeswax": (config.VEGETARIANO, "cera de abejas"),
    "propolis": (config.VEGETARIANO, "propóleo"),
    # faena
    "gelatin": (config.NO_APTO, "gelatina"),
    "gelatine": (config.NO_APTO, "gelatina"),
    "collagen": (config.NO_APTO, "colágeno"),
    "meat": (config.NO_APTO, "carne"),
    "beef": (config.NO_APTO, "carne vacuna"),
    "pork": (config.NO_APTO, "cerdo"),
    "chicken": (config.NO_APTO, "pollo"),
    "bacon": (config.NO_APTO, "panceta"),
    "ham": (config.NO_APTO, "jamón"),
    "lard": (config.NO_APTO, "grasa de cerdo"),
    "tallow": (config.NO_APTO, "sebo"),
    "animal-fat": (config.NO_APTO, "grasa animal"),
    "beef-fat": (config.NO_APTO, "grasa vacuna"),
    "rennet": (config.NO_APTO, "cuajo animal"),
    "fish": (config.NO_APTO, "pescado"),
    "tuna": (config.NO_APTO, "atún"),
    "anchovy": (config.NO_APTO, "anchoa"),
    "salmon": (config.NO_APTO, "salmón"),
    "shrimp": (config.NO_APTO, "camarón"),
    "shellfish": (config.NO_APTO, "marisco"),
    "fish-oil": (config.NO_APTO, "aceite de pescado"),
    "carmine": (config.NO_APTO, "carmín (cochinilla)"),
    "cochineal": (config.NO_APTO, "cochinilla"),
    "e120": (config.NO_APTO, "carmín (INS 120)"),
    "shellac": (config.NO_APTO, "goma laca"),
    "e904": (config.NO_APTO, "goma laca (INS 904)"),
    "bone-phosphate": (config.NO_APTO, "fosfato de hueso"),
}

AMBIGUO_TAGS: dict[str, str] = {
    "e471": "INS 471 (mono y diglicéridos): puede ser de grasa animal o vegetal",
    "e472": "INS 472: puede derivar de grasa animal o vegetal",
    "e472e": "INS 472e: puede derivar de grasa animal o vegetal",
    "mono-and-diglycerides-of-fatty-acids":
        "mono y diglicéridos: pueden ser de grasa animal o vegetal",
    "e570": "ácido esteárico: puede ser de sebo animal",
    "stearic-acid": "ácido esteárico: puede ser de sebo animal",
    "e631": "inosinato: suele obtenerse de pescado o carne",
    "e627": "guanilato: suele obtenerse de pescado o carne",
    "e920": "L-cisteína: puede provenir de plumas o pelo",
    "l-cysteine": "L-cisteína: puede provenir de plumas o pelo",
    "lecithin": "lecitina sin origen declarado (suele ser de soja)",
    "e322": "lecitina (INS 322) sin origen declarado",
    "natural-flavouring": "aroma natural sin origen declarado",
    "natural-flavour": "aroma natural sin origen declarado",
    "flavouring": "aromatizante sin origen declarado",
    "glycerol": "glicerina: puede ser animal o vegetal",
    "e422": "glicerina (INS 422): puede ser animal o vegetal",
    "vitamin-d": "vitamina D: la D3 suele venir de lanolina",
    "vitamin-d3": "vitamina D3: suele venir de lanolina",
    "cholecalciferol": "colecalciferol (D3): suele venir de lanolina",
    "ferment": "fermentos de origen no declarado",
    "enzyme": "enzimas de origen no declarado",
}


def tag_a_texto(tag: str) -> str:
    """Convierte "en:wheat-flour" en "wheat flour"."""
    cuerpo = tag.split(":", 1)[-1]
    return normalize(cuerpo.replace("-", " "))


def _clasificar_tag(tag: str):
    """Devuelve ("animal", (estado, etiqueta)) | ("ambiguo", motivo) | None."""
    cuerpo = tag.split(":", 1)[-1].lower()
    texto = tag_a_texto(tag)

    # Un calificador vegetal dentro del mismo tag lo resuelve: "coconut-milk",
    # "leche-de-almendras" o "vegetable-fat" no son de origen animal.
    if any(c in cuerpo for c in CALIFICADORES_VEGETALES):
        return None

    if cuerpo in ANIMAL_TAGS:
        return ("animal", ANIMAL_TAGS[cuerpo])
    if cuerpo in AMBIGUO_TAGS:
        return ("ambiguo", AMBIGUO_TAGS[cuerpo])

    # Cola larga (sobre todo tags "es:" que la taxonomía no normalizó): se
    # reusa el léxico de texto libre, que ya sabe leer español.
    hit = _match(texto)
    if hit:
        return ("animal", hit)
    amb = next((msg for rx, msg in AMBIGUO_RE if rx.search(texto)), None)
    if amb:
        return ("ambiguo", amb)
    return None


def analyze_tags(tags: list[str] | None) -> AnalisisIngredientes:
    """Clasifica a partir de `ingredients_tags` de Open Food Facts."""
    tags = [t for t in (tags or []) if t]
    if not tags:
        return AnalisisIngredientes(
            config.REVISAR,
            "El producto no tiene ingredientes cargados en Open Food Facts",
            fuente="sin_datos")

    detectados: list[str] = []
    ambiguos: list[str] = []
    reconocidos = 0
    peor = config.APTO
    motivo_peor = ""

    for tag in tags:
        res = _clasificar_tag(tag)
        if res is None:
            texto = tag_a_texto(tag)
            if any(rx.search(texto) for rx in VEGANO_RE) or any(
                    c in tag.lower() for c in CALIFICADORES_VEGETALES):
                reconocidos += 1
            continue
        tipo, valor = res
        reconocidos += 1
        if tipo == "animal":
            estado, etiqueta = valor
            if etiqueta not in detectados:
                detectados.append(etiqueta)
            if SEVERIDAD[estado] > SEVERIDAD[peor]:
                peor, motivo_peor = estado, etiqueta
        elif valor not in ambiguos:
            ambiguos.append(valor)

    cobertura = reconocidos / len(tags)
    base = dict(detectados=detectados, ambiguos=ambiguos,
                cobertura=round(cobertura, 2), n_ingredientes=len(tags))

    if peor == config.NO_APTO:
        return AnalisisIngredientes(
            config.NO_APTO, f"Contiene {motivo_peor}, de origen animal", **base)
    if peor == config.VEGETARIANO:
        return AnalisisIngredientes(
            config.VEGETARIANO,
            f"Contiene {motivo_peor}: es vegetariano pero no vegano", **base)
    if ambiguos:
        return AnalisisIngredientes(
            config.REVISAR,
            f"Sin ingredientes animales, pero hay {len(ambiguos)} de origen no "
            f"declarado: {ambiguos[0]}", **base)
    if cobertura < COBERTURA_MINIMA:
        return AnalisisIngredientes(
            config.REVISAR,
            f"Solo se reconoció el {cobertura:.0%} de los {len(tags)} "
            "ingredientes: no alcanza para afirmar que sea vegano", **base)
    return AnalisisIngredientes(
        config.APTO,
        f"Ningún ingrediente de origen animal entre los {len(tags)} "
        f"declarados (se reconoció el {cobertura:.0%})", **base)


def analyze_product(off: dict | None) -> AnalisisIngredientes:
    """Analiza un producto de OFF con la mejor señal de ingredientes que tenga.

    Se prefiere el texto libre cuando existe (trae los códigos INS y el detalle
    entre paréntesis que la taxonomía pierde) y se cae a los tags si no.
    Cuando los dos se pronuncian, gana el más restrictivo: son la misma
    evidencia leída de dos maneras, y una discrepancia significa que a una de
    las dos se le escapó algo.
    """
    off = off or {}
    por_texto = analyze(off.get("ingredients_text"))
    por_tags = analyze_tags(off.get("ingredients_tags"))

    if por_texto.resuelto and por_tags.resuelto:
        if SEVERIDAD[por_texto.estado] >= SEVERIDAD[por_tags.estado]:
            return por_texto
        return por_tags
    if por_texto.resuelto:
        return por_texto
    if por_tags.resuelto:
        return por_tags
    # Ninguno resolvió: se informa el que más evidencia tenía.
    if por_texto.n_ingredientes >= por_tags.n_ingredientes:
        return por_texto
    return por_tags
