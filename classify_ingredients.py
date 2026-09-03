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
    # Los calificadores vegetales ("leche de coco") van como lookahead: sin
    # eso, todo producto vegetal que use la palabra del análogo animal —y son
    # cada vez más— cae en un falso `vegetariano`.
    # El calificador vegetal no siempre viene pegado: "leche CONCENTRADA de
    # coco" es igual de vegetal que "leche de coco". Se admiten hasta dos
    # palabras en el medio, pero no más, para no absolver a "postre de coco
    # con leche", donde la leche no está calificada por nada.
    (r"\bleche(s)?\b(?! vegetal)(?!(?: \w+){0,2} de (coco|almendra|soja|soya|avena|arroz|mani|cacahuete|castana|caju|quinoa|nuez|nueces|anacardo|avellana|pistacho|macadamia|alpiste|girasol|sesamo|canamo|tigre|vegetal|origen vegetal))",
     (config.VEGETARIANO, "leche")),
    (r"\bleche en polvo\b", (config.VEGETARIANO, "leche en polvo")),
    (r"\b(suero|lactosuero|suero de leche)\b(?! de (soja|soya|vegetal))",
     (config.VEGETARIANO, "suero lácteo")),
    (r"\blactosa\b", (config.VEGETARIANO, "lactosa")),
    (r"\bcase[ií]n(a|ato)?", (config.VEGETARIANO, "caseína")),
    # "láctea" en femenino ("materia grasa láctea") no matcheaba con l[aá]cteo?s?
    (r"\bl[aá]cte[oa]s?\b", (config.VEGETARIANO, "derivado lácteo")),
    (r"\bcrema\b(?! vegetal)(?!(?: \w+){0,2} de (coco|soja|soya|almendra|mani|cacahuete|avellana|castana|caju|anacardo|nuez|nueces|arroz|avena|girasol|sesamo|cacao|verdura|choclo|maiz|zapallo|calabaza|espinaca|tomate|hongo|champinon|arveja|lenteja|garbanzo))",
     (config.VEGETARIANO, "crema")),
    (r"\bnata\b(?! vegetal| de (coco|soja|almendra))", (config.VEGETARIANO, "nata")),
    (r"\bqueso\b(?! vegano| vegetal)(?!(?: \w+){0,2} de (almendra|castana|caju|anacardo|soja|soya|coco|nuez|nueces))",
     (config.VEGETARIANO, "queso")),
    (r"\bricota\b(?! vegana| vegetal| de (almendra|soja|caju))", (config.VEGETARIANO, "ricota")),
    (r"\byog(ur|hurt|urt)\b(?! vegano| vegetal)(?!(?: \w+){0,2} de (coco|soja|soya|almendra|avena|anacardo|caju|castana))",
     (config.VEGETARIANO, "yogur")),
    (r"\bmante(ca|quilla)\b(?! vegetal| vegana)(?!(?: \w+){0,2} de (mani|cacahuete|cacao|coco|almendra|castana|caju|anacardo|nuez|nueces|avellana|pistacho|semillas|girasol|sesamo|karite|murumuru|cupuacu))",
     (config.VEGETARIANO, "manteca")),
    (r"\bgrasa but[ií]rica\b|\bbutter ?oil\b", (config.VEGETARIANO, "grasa butírica")),
    (r"\bdulce de leche\b", (config.VEGETARIANO, "dulce de leche")),
    (r"\bkefir\b(?! de agua| vegetal| de coco)", (config.VEGETARIANO, "kéfir")),
    # El cuajo microbiano y el vegetal (cardo, higuera) son los que más se usan
    # hoy en la industria: condenar "cuajo" a secas marcaba veganos como faena.
    (r"\bcuajo\b(?! vegetal| vegetariano| microbiano| microbiologico| de cardo| de higuera)",
     (config.NO_APTO, "cuajo (enzima animal)")),

    # --- huevo -----------------------------------------------------------
    (r"\bhuevo?s?\b", (config.VEGETARIANO, "huevo")),
    (r"\b(clara|yema)s? de huevo\b", (config.VEGETARIANO, "huevo")),
    (r"\bovo(albumina|producto)", (config.VEGETARIANO, "derivado de huevo")),
    (r"\balb[uú]mina\b", (config.VEGETARIANO, "albúmina")),
    (r"\blecitina de huevo\b|\bins 322 de huevo\b", (config.VEGETARIANO, "lecitina de huevo")),
    # Único conservante de uso corriente que es de origen animal: se extrae de
    # la clara. Aparece sobre todo en quesos y en vinos.
    (r"\blisozima\b|\bins 1105\b|\be ?1105\b", (config.VEGETARIANO, "lisozima (clara de huevo)")),

    # --- miel y abejas ---------------------------------------------------
    # "Miel de caña" es melaza y "miel de maple" es savia: ninguna es de abeja.
    (r"\bmiel\b(?! de (cana|maple|arce|agave|palma|maiz|abedul|dat[ie]l|manzana|coco))",
     (config.VEGETARIANO, "miel")),
    (r"\bjalea real\b", (config.VEGETARIANO, "jalea real")),
    (r"\bpropoleo\b", (config.VEGETARIANO, "propóleo")),
    (r"\bcera de abejas?\b|\bins 901\b|\be ?901\b", (config.VEGETARIANO, "cera de abejas")),

    # --- carne, pescado y faena -----------------------------------------
    (r"\bgelatina\b(?! vegetal| vegana| de (algas?|agar))|\bins 441\b|\be ?441\b",
     (config.NO_APTO, "gelatina")),
    (r"\bcol[aá]geno\b(?! vegetal| vegano)", (config.NO_APTO, "colágeno")),
    (r"\bcarne\b(?! vegetal| vegana| de (soja|soya|garbanzo|arveja|trigo|lenteja|coco|seitan|hongo|champinon))|\bextracto de carne\b",
     (config.NO_APTO, "carne")),
    (r"\bgrasa (bovina|vacuna|porcina|animal|ovina|de cerdo|de vaca|de ave|de aves|de pollo|de oveja|de cordero|de pella)\b",
     (config.NO_APTO, "grasa animal")),
    # CAA art. 545: la oleomargarina (óleo-oil) se define SOLO como bovina u
    # ovina, obtenida de los primeros jugos de faena. No existe una versión
    # vegetal del término: a secas ya es grasa animal.
    (r"\boleomargarina\b", (config.NO_APTO, "oleomargarina (grasa bovina u ovina, CAA art. 545)")),
    (r"\boleoestearina\b", (config.NO_APTO, "oleoestearina (grasa bovina u ovina, CAA art. 547)")),
    (r"\bsebo\b(?! vegetal)", (config.NO_APTO, "sebo")),
    (r"\bmanteca de cerdo\b|\bchicharron", (config.NO_APTO, "manteca de cerdo")),
    (r"\b(pollo|cerdo|vacuno|bovino|porcino|jamon|panceta|tocino|chorizo|ternera|cordero|cabrito|conejo|pavo|pato|codorniz)\b(?! vegetal| vegano| de soja)",
     (config.NO_APTO, "carne")),
    (r"\bave(s)?\b(?! de corral vegana)|\bmenudencias?\b|\bvisceras?\b|\bmondongo\b|\bh[ií]gado\b",
     (config.NO_APTO, "carne o menudencia")),
    (r"\b(carne|grasa|caldo|extracto|sabor|higado|menudencia) de res\b|\bsabor res\b",
     (config.NO_APTO, "carne vacuna")),
    (r"\b(pescado|atun|merluza|salmon|anchoa|sardina|camaron|langostino|marisco|calamar|crustaceos?|molusco|mejillon|ostra|vieira|pulpo|krill|caracol|surimi)\b(?! vegetal| vegano| de soja)",
     (config.NO_APTO, "pescado o marisco")),
    (r"\baceite de pescado\b|\bomega ?3 de pescado\b", (config.NO_APTO, "aceite de pescado")),
    (r"\bcaldo de (carne|ave|pollo|pescado|hueso)\b", (config.NO_APTO, "caldo de origen animal")),
    (r"\bproteina animal\b|\bproteinas animales\b", (config.NO_APTO, "proteína animal")),
    # "hueso" solo, no: "aceituna sin hueso" y "durazno sin hueso" son vegetales.
    (r"\bfosfato de hueso\b|\bins 542\b|\be ?542\b|\b(harina|polvo|carbon|extracto|gelatina) de huesos?\b",
     (config.NO_APTO, "derivado de hueso")),
    (r"\bpepsina\b", (config.NO_APTO, "pepsina (estómago porcino)")),

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
    (r"\bins 570\b|\bacido (estearico|oleico|palmitico|laurico|miristico)\b|\bestearato\b",
     "ácidos grasos / estearatos: pueden ser de sebo animal"),
    (r"\bins 4(3[2-6]|9[1-5])\b|\bpolisorbato\b|\bmonoestearato de sorbitan\b|\bsorbitan\b",
     "polisorbatos y ésteres de sorbitán: derivan de ácidos grasos que pueden ser animales"),
    # CAA art. 551: la fase grasa de la margarina puede ser "grasas animales
    # comestibles" y admite hasta 5% de grasa de leche, más leche en polvo,
    # suero, albúmina y caseinato. Sin el calificador "vegetal" no se sabe.
    (r"\bmargarina\b(?! vegetal| vegana)", "margarina sin aclarar: el CAA (art. 551) "
     "permite grasa animal y hasta 5% de grasa de leche"),
    # CAA art. 548: la hidrogenación se aplica a cualquier aceite o grasa del
    # Código, animal o vegetal. "Grasa vegetal hidrogenada" sí queda excluida
    # porque no matchea la frase exacta.
    (r"\bgrasa (parcialmente )?hidrogenada\b|\baceite (parcialmente )?hidrogenado\b",
     "grasa hidrogenada sin aclarar el origen: el CAA (art. 548) admite hidrogenar grasas animales"),
    (r"\btransglutaminasa\b", "transglutaminasa: puede ser microbiana o de plasma animal"),
    (r"\bnisina\b|\bins 234\b", "nisina: se cultiva habitualmente sobre un medio lácteo"),
    (r"\blipasa\b|\bproteasa\b", "lipasas y proteasas: pueden ser de origen animal"),
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

# Los mismos ambiguos, en inglés. Buena parte del catálogo argentino de OFF
# trae la lista en inglés, y sin esto "natural flavouring" pasaba como
# desconocido mientras su equivalente español ya se marcaba como ambiguo.
# Los lookbehind son fijos y encadenados a propósito: Python no admite
# lookbehind de ancho variable, pero sí varios seguidos.
AMBIGUO_EN: list[tuple[str, str]] = [
    (r"\bnatural (flavou?r|flavou?ring)s?\b|\bflavou?ring\b",
     "aroma natural sin origen declarado"),
    (r"(?<!soy )(?<!soya )(?<!sunflower )(?<!rapeseed )\blecithin\b",
     "lecitina sin origen declarado (suele ser de soja, pero no está aclarado)"),
    (r"\bmono ?and ?diglycerides\b|\bmonoglycerides\b|\bdiglycerides\b",
     "mono y diglicéridos: pueden ser de grasa animal o vegetal"),
    (r"\bglycerin[e]?\b|\bglycerol\b", "glicerina: puede ser animal o vegetal"),
    (r"\bstearic acid\b|\bstearate\b", "ácido esteárico: puede ser de sebo animal"),
    (r"\bvitamin d3?\b|\bcholecalciferol\b", "vitamina D3: suele venir de lanolina"),
    (r"(?<!vegetable )(?<!palm )\bshortening\b",
     "shortening sin origen declarado: puede ser grasa de cerdo"),
    (r"\benzymes?\b", "enzimas de origen no declarado"),
]
AMBIGUO += AMBIGUO_EN

# Animales inequívocos en inglés que el léxico español no alcanza a ver por una
# letra: "carmin" no matchea dentro de "carmine", ni "gelatina" en "gelatin".
ANIMAL_EN: list[tuple[str, tuple[str, str]]] = [
    (r"\bcarmine\b|\bcochineal\b|\bcarminic acid\b",
     (config.NO_APTO, "carmín (cochinilla)")),
    (r"\bshellac\b", (config.NO_APTO, "goma laca")),
    (r"\bgelatine?\b", (config.NO_APTO, "gelatina")),
    (r"\btallow\b|\blard\b|\bsuet\b", (config.NO_APTO, "grasa animal")),
    (r"\bwhey\b", (config.VEGETARIANO, "suero lácteo")),
    (r"\bcasein(ate)?\b", (config.VEGETARIANO, "caseína")),
    (r"\bmilkfat\b|\bbutterfat\b|\bbuttermilk\b|\bghee\b",
     (config.VEGETARIANO, "derivado lácteo")),
    (r"\blysozyme\b", (config.VEGETARIANO, "lisozima (clara de huevo)")),
    (r"\b(veal|lamb|poultry|turkey|venison)\b", (config.NO_APTO, "carne")),
    (r"\b(crustacean|mollusc|mussel|oyster|squid|octopus|krill)\b",
     (config.NO_APTO, "pescado o marisco")),
    (r"\bbone (meal|powder|char|broth)\b", (config.NO_APTO, "derivado de hueso")),
    (r"\banimal (fat|protein)\b", (config.NO_APTO, "derivado animal")),
    (r"\boleomargarine\b", (config.NO_APTO, "oleomargarina (grasa bovina u ovina)")),
]
ANIMAL += ANIMAL_EN

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
    r"\bsacarina\b", r"\bciclamato\b", r"\bglicosidos de esteviol\b",
    r"\bpolidextrosa\b", r"\binulina\b", r"\bcarboximetilcelulosa\b",
    # Aditivos sintéticos o vegetales inequívocos que aparecían como
    # "desconocidos" y bajaban la cobertura de productos que sí son veganos.
    r"\bvainillina\b", r"\bvanillin\b", r"\bcurcumina\b", r"\btartrazina\b",
    r"\bamarillo (ocaso|crepusculo)\b", r"\bazul brillante\b", r"\brojo allura\b",
    r"\bindigotina\b", r"\beritrosina\b", r"\bcaroteno", r"\bcarotene",
    r"\bantocianina", r"\bclorofila\b", r"\bpoliglicerol\b",
    r"\bpolirricinoleato\b", r"\bdioxido de (silicio|titanio|carbono)\b",
    r"\bgoma gelan\b", r"\btripolifosfato\b", r"\bpirofosfato\b",
    r"\bacido (sorbico|benzoico|acetico|adipico|fumarico|gluconico)\b",
    r"\bsorbico\b", r"\bnitrito\b", r"\bsulfito\b", r"\bmetabisulfito\b",
    r"\bpropionato\b", r"\bnatamicina\b", r"\bpimaricina\b",
    # Clases de aditivo que SÍ se pueden dar por vegetales: no existe un aditivo
    # de origen animal de uso corriente que cumpla estas funciones.
    r"\bacidulante\b", r"\bantioxidante\b", r"\bhumectante\b",
    r"\bregulador de acidez\b", r"\bleudante\b", r"\bedulcorante\b",
    # NO se listan acá "colorante", "conservante", "emulsionante", "espesante",
    # "estabilizante" ni "gelificante": nombran una función, no un origen, y en
    # cada una hay un aditivo animal de uso corriente (carmín, lisozima, INS 471
    # de sebo, gelatina). Quedan sin reconocer a propósito: no cuentan como
    # evidencia vegetal, pero tampoco fuerzan `revisar`, porque el rótulo
    # argentino casi siempre los acompaña del aditivo concreto ("conservante:
    # sorbato de potasio"), y ese sí se reconoce y aporta cobertura.
]

# Palabras que nombran la FUNCIÓN de un aditivo, no un ingrediente. En el rótulo
# argentino encabezan al aditivo real ("gelificante (agar)", "conservante: INS
# 202") y el parser las deja como un token aparte.
#
# No son evidencia de nada: "colorante" no dice si es cúrcuma o carmín. Por eso
# no cuentan como reconocidas... pero tampoco pueden pesar en el denominador de
# la cobertura, porque entonces un rótulo prolijo —que declara la clase Y el
# aditivo— quedaría castigado por ser más explícito que uno que solo pone el
# código. Se descartan del cálculo por completo.
#
# Solo aplica cuando el token es ÚNICAMENTE la palabra de clase: "conservante
# INS 202" viene junto en un mismo token y ahí sí se reconoce por el código.
CLASES_DE_ADITIVO = re.compile(
    r"^(colorantes?|conservantes?|emulsionantes?|emulsificantes?|espesantes?|"
    r"estabilizantes?|gelificantes?|acidulantes?|antioxidantes?|humectantes?|"
    r"antihumectantes?|leudantes?|gasificantes?|edulcorantes?|espumantes?|"
    r"secuestrantes?|antiaglutinantes?|antiespumantes?|resaltadores? del sabor|"
    r"reguladores? de (la )?acidez|agentes? de brillo|"
    r"colours?|colors?|preservatives?|emulsifiers?|thickeners?|stabilis?ers?|"
    r"gelling agents?|glazing agents?|raising agents?|anti caking agents?|"
    r"acidity regulators?|firming agents?|flavour enhancers?)$")

# Los mismos, en la taxonomía de OFF. OFF emite el tag de la clase ADEMÁS del
# tag del aditivo concreto en el 98% de los casos, así que tratarlos como
# ambiguos mandaría a `revisar` productos que sí declaran todo.
CLASES_TAGS = {
    "colour", "color", "preservative", "emulsifier", "thickener", "stabiliser",
    "stabilizer", "gelling-agent", "glazing-agent", "raising-agent",
    "acidity-regulator", "anti-caking-agent", "firming-agent",
    "flavour-enhancer", "antioxidant", "acidifier", "humectant", "sweetener",
    "thickening-agent",
}

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
    r"\bacidifier\b", r"\bantioxidant\b",
    r"\bhumectant\b", r"\braising agent\b", r"\bacidity regulator\b",
    # Sin "emulsifier", "thickener", "stabiliser", "preservative" ni "colour",
    # por el mismo motivo que sus equivalentes en español. Tampoco "acid",
    # "extract", "concentrate" ni "powder": son tan genéricos que daban por
    # vegetales a "acid whey", "poultry extract" y "bone powder".
    r"\bspice", r"\bherb", r"\bpuree\b",
    r"\bjuice\b", r"\bpaste\b", r"\bfibre\b", r"\bfiber\b",
    r"\bbran\b", r"\bgerm\b", r"\bsemolina\b", r"\bcereal", r"\bgrain",
    r"\blegume", r"\bmushroom", r"\balgae\b", r"\bseaweed\b", r"\bcaffeine\b",
    # Los aditivos numerados de riesgo (120, 441, 471, 542, 901, 904, 920...)
    # ya estan enumerados en ANIMAL_TAGS y AMBIGUO_TAGS, asi que el resto de la
    # serie E/INS se cuenta como reconocido para no castigar la cobertura.
    # El espacio importa: normalize() reescribe "e330" como "e 330".
    # El (?!\d) es imprescindible: sin el, "ins 1105" (lisozima, de clara de
    # huevo) matcheaba como si fuera "ins 110" y se daba por vegano.
    r"\b(?:e|ins) ?\d{3}(?!\d)",
    # Clases genericas de la taxonomia de OFF. Son categorias padre, y cuando
    # el aditivo concreto importa OFF agrega ademas su tag especifico, que ya
    # cubren los otros lexicos. Las que si esconden un origen animal posible
    # (oil-and-fat, gelling-agent, glazing-agent) estan en AMBIGUO_TAGS.
    r"\bminerals?\b", r"\bvitamins?\b", r"\bdisaccharide\b",
    r"\bmonosaccharide\b", r"\bsweetener\b", r"\banti caking agent\b",
    r"\bfirming agent\b", r"\bcondiment\b",
    r"\bstarches\b", r"\bsyrups\b",
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
    # "INS322" / "E-322" -> "ins 322" / "e 322". Los de 4 dígitos existen
    # (INS 1105 es la lisozima) y hay que normalizarlos completos, no truncados.
    text = re.sub(r"\b(ins|e)[\s.-]*(\d{3,4})\b", r"\1 \2", text)
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
    evaluados = 0
    peor = config.APTO
    motivo_peor = ""

    for ing in ingredientes:
        # Las palabras de clase no son ingredientes: no suman ni restan.
        if CLASES_DE_ADITIVO.match(ing):
            continue
        evaluados += 1

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

    cobertura = reconocidos / evaluados if evaluados else 0.0
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
    "milkfat": (config.VEGETARIANO, "grasa láctea"),
    "acid-whey": (config.VEGETARIANO, "suero lácteo ácido"),
    "sweet-whey": (config.VEGETARIANO, "suero lácteo dulce"),
    "whey-protein": (config.VEGETARIANO, "proteína de suero"),
    "lysozyme": (config.VEGETARIANO, "lisozima (clara de huevo)"),
    "e1105": (config.VEGETARIANO, "lisozima (INS 1105, clara de huevo)"),
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
    "poultry": (config.NO_APTO, "ave de corral"),
    "poultry-fat": (config.NO_APTO, "grasa de ave"),
    "poultry-extract": (config.NO_APTO, "extracto de ave"),
    "veal": (config.NO_APTO, "ternera"),
    "crustacean": (config.NO_APTO, "crustáceo"),
    "mollusc": (config.NO_APTO, "molusco"),
    "animal-protein": (config.NO_APTO, "proteína animal"),
    "beef-heart": (config.NO_APTO, "corazón vacuno"),
    "beef-flavouring": (config.NO_APTO, "saborizante de carne vacuna"),
    "bone": (config.NO_APTO, "hueso"),
    "pepsin": (config.NO_APTO, "pepsina"),
    "oleomargarine": (config.NO_APTO, "oleomargarina (grasa bovina u ovina)"),
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
    # Categorias padre que abarcan tanto opciones vegetales como animales. Si
    # el ingrediente concreto estuviera declarado, OFF traeria su tag propio.
    # "oil-and-fat" sí se queda: no es una clase de aditivo sino una grasa real
    # sin origen declarado, que es exactamente lo que hay que marcar. Las clases
    # de aditivo (gelling-agent, colour...) se fueron a CLASES_TAGS: OFF emite
    # el tag de la clase junto con el del aditivo concreto casi siempre, así que
    # tratarlas como ambiguas castigaba al rótulo que declara de más.
    "oil-and-fat": "grasa sin origen declarado (puede ser vegetal o animal)",
    "margarine": ("margarina sin aclarar: el CAA (art. 551) permite grasa animal "
                  "y hasta 5% de grasa de leche"),
    "hydrogenated-fat": "grasa hidrogenada sin aclarar si el origen es vegetal o animal",
    "transglutaminase": "transglutaminasa: puede ser microbiana o de plasma animal",
    "nisin": "nisina: se cultiva habitualmente sobre un medio lácteo",
    "e234": "nisina (INS 234): se cultiva habitualmente sobre un medio lácteo",
    "lipase": "lipasa: puede ser de origen animal",
    "protease": "proteasa: puede ser de origen animal",
}


def tag_a_texto(tag: str) -> str:
    """Convierte "en:wheat-flour" en "wheat flour"."""
    cuerpo = tag.split(":", 1)[-1]
    return normalize(cuerpo.replace("-", " "))


def _clasificar_tag(tag: str):
    """Devuelve ("animal", (estado, etiqueta)) | ("ambiguo", motivo) | None."""
    cuerpo = tag.split(":", 1)[-1].lower()

    # El match exacto va primero: los compuestos que la taxonomía ya define
    # ("mono-and-diglycerides-of-fatty-acids") se resuelven enteros, antes de
    # que la partición por "and" los desarme.
    if cuerpo in ANIMAL_TAGS:
        return ("animal", ANIMAL_TAGS[cuerpo])
    if cuerpo in AMBIGUO_TAGS:
        return ("ambiguo", AMBIGUO_TAGS[cuerpo])

    # "x-and-y" enumera DOS ingredientes, no uno calificando al otro. Sin esto,
    # el calificador vegetal de "vegetable-oil-and-lard" absolvía también a la
    # grasa de cerdo, que es justo lo que había que detectar.
    if "-and-" in cuerpo:
        peor = None
        for parte in cuerpo.split("-and-"):
            res = _clasificar_tag(tag.split(":", 1)[0] + ":" + parte)
            if res is None:
                continue
            if res[0] == "animal":
                if peor is None or peor[0] != "animal" or (
                        SEVERIDAD[res[1][0]] > SEVERIDAD[peor[1][0]]):
                    peor = res
            elif peor is None:
                peor = res
        if peor is not None:
            return peor

    # Un calificador vegetal dentro del mismo tag lo resuelve: "coconut-milk",
    # "leche-de-almendras" o "vegetable-fat" no son de origen animal.
    if any(c in cuerpo for c in CALIFICADORES_VEGETALES):
        return None

    # Cola larga (sobre todo tags "es:" que la taxonomía no normalizó): se
    # reusa el léxico de texto libre, que ya sabe leer español.
    texto = tag_a_texto(tag)
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
    evaluados = 0
    peor = config.APTO
    motivo_peor = ""

    for tag in tags:
        if tag.split(":", 1)[-1].lower() in CLASES_TAGS:
            continue
        evaluados += 1

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

    cobertura = reconocidos / evaluados if evaluados else 0.0
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
