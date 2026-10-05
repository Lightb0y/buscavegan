"""Normalización de marcas: una marca, una sola grafía.

Por qué existe
--------------
El campo `brands` de Open Food Facts lo carga la comunidad a mano, y el
resultado medido sobre el catálogo argentino es que **399 marcas se escriben de
más de una forma, y entre todas se llevan 3.751 productos**: la mitad del
catálogo. Los casos no son exóticos:

    La Serenisima   68      Dia     100      Arcor   144
    La Serenísima   65      Día      20      ARCOR     3
    LA SERENISIMA    5      DIA      10      arcor    22
    ...y 7 variantes más    ...y 7 más

El costo es directo y se paga en la búsqueda: quien escribe "La Serenísima"
con tilde ve 65 productos en vez de 169. La marca es, después del nombre, el
segundo término por el que la gente busca, así que una marca partida en diez
pedazos es una función rota, no una prolijidad pendiente.

Además, **1.258 productos (17%) no tienen marca cargada**. Para 860 de ellos
el supermercado sí la publica: se completa desde ahí (ver `build_db`).

Cómo se elige la grafía buena
-----------------------------
Se agrupan las variantes por una clave que ignora mayúsculas, tildes y
puntuación (`clave`), y dentro de cada grupo se elige una grafía para mostrar
(`canonica`), con este orden de preferencia:

1. **Ni todo mayúsculas ni todo minúsculas.** "ARCOR" y "arcor" son artefactos
   de carga; "Arcor" es cómo se escribe la marca. Esto también preserva las
   marcas en camello —"NotCo", "SanCor"— que cualquier regla de "capitalizar
   cada palabra" rompería.
2. **Con tilde antes que sin tilde**, si la variante acentuada tiene respaldo
   real (al menos 3 productos y el 10% del grupo). El tilde es información que
   la grafía sin tilde perdió, pero un solo producto con "Alícante" contra 16
   con "Alicante" es una errata, no la grafía correcta: de ahí el piso.
3. A igualdad, **la más frecuente**.

El voto se hace sobre las grafías de OFF, no sobre las del supermercado: las
cadenas publican casi todo en mayúsculas (3.015 "ARCOR", 1.746 "LA
SERENISIMA") y ganarían siempre por volumen sin aportar la grafía correcta.
Las marcas que OFF no tiene sí se toman de la góndola, porque ahí son la única
fuente que hay.

`ALIAS` corrige a mano lo que el voto no puede saber: marcas donde la grafía
correcta es minoritaria en los datos. Se agrega solo con el caso a la vista.
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter
from typing import Iterable, Mapping

# Alguna corrida vieja guardó el `repr` de la lista de OFF en vez de su
# contenido: la marca quedó como "['La serenisima']". Son pocos productos,
# pero ensucian el agrupamiento y se ven en la app.
_REPR_DE_LISTA = re.compile(r"^\[\s*(['\"])(.*)\1\s*\]$", re.DOTALL)

_ESPACIOS = re.compile(r"\s+")
_NO_ALFANUM = re.compile(r"[^a-z0-9]+")
# El apóstrofo se borra en vez de volverse separador: "Hellmann's" y
# "HELLMANNS" son la misma marca, y partirla en "hellmann s" las separaría.
_APOSTROFOS = re.compile(r"['´’ʼ`]")

# Piso para que una grafía acentuada le gane a la sin acento.
_MIN_ACENTO_ABS = 3
_MIN_ACENTO_REL = 0.10

# Marcas donde la grafía correcta es minoritaria en los datos y el voto no
# alcanza. Se indexan por `clave`, así cubren todas las variantes de una vez.
ALIAS: dict[str, str] = {
    "aguila": "Águila",
    "taragui": "Taragüí",
    "nestle": "Nestlé",
    "dia": "Día",
    "la serenisima": "La Serenísima",
    "sancor": "SanCor",
    "notco": "NotCo",
    "hellmann s": "Hellmann's",
    "la campagnola": "La Campagnola",
}


def limpiar(marca: str | None) -> str | None:
    """Saca la basura de carga y deja la grafía tal como se va a mostrar.

    No toca mayúsculas ni tildes: eso lo decide `canonica` comparando
    variantes. Acá solo se arregla lo que es inequívocamente ruido.
    """
    if marca is None:
        return None
    texto = str(marca).strip()
    m = _REPR_DE_LISTA.match(texto)
    if m:
        texto = m.group(2).strip()
    # OFF separa varias marcas con coma ("Arcor,Cofler"). No se parten en
    # marcas distintas —"BC,La Campagnola" es una línea de La Campagnola, no
    # dos marcas sueltas— pero sí se unifica el separador.
    texto = re.sub(r"\s*,\s*", ", ", texto)
    # "Dia%" / "Dia %": el símbolo es del logo, no del nombre.
    texto = re.sub(r"\s*%\s*$", "", texto)
    texto = _ESPACIOS.sub(" ", texto).strip(" ,-")
    return texto or None


def clave(marca: str | None) -> str:
    """Clave de agrupación: sin tildes, sin mayúsculas, sin puntuación.

    Es también la clave con la que conviene buscar: hace que "serenisima"
    encuentre "La Serenísima".
    """
    texto = limpiar(marca) or ""
    texto = _APOSTROFOS.sub("", texto)
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return _ESPACIOS.sub(" ", _NO_ALFANUM.sub(" ", texto.lower())).strip()


def _tiene_acento(texto: str) -> bool:
    return any(unicodedata.combining(c)
               for c in unicodedata.normalize("NFKD", texto))


def _forma_mixta(texto: str) -> bool:
    """True si la grafía no es ni TODO MAYÚSCULAS ni todo minúsculas."""
    letras = [c for c in texto if c.isalpha()]
    if not letras:
        return False
    return any(c.isupper() for c in letras) and any(c.islower() for c in letras)


def canonica(variantes: Mapping[str, int]) -> str:
    """Elige la grafía a mostrar entre las variantes de una misma marca."""
    limpias: Counter[str] = Counter()
    for variante, n in variantes.items():
        texto = limpiar(variante)
        if texto:
            limpias[texto] += n
    if not limpias:
        return ""

    alias = ALIAS.get(clave(next(iter(limpias))))
    if alias:
        return alias

    # 1. Grafías ni todo-mayúsculas ni todo-minúsculas, si las hay.
    mixtas = {v: n for v, n in limpias.items() if _forma_mixta(v)}
    candidatas = mixtas or dict(limpias)

    # 2. Con tilde, si tiene respaldo suficiente dentro de ese grupo.
    total = sum(candidatas.values())
    piso = max(_MIN_ACENTO_ABS, int(total * _MIN_ACENTO_REL))
    acentuadas = {v: n for v, n in candidatas.items()
                  if _tiene_acento(v) and n >= piso}
    if acentuadas:
        candidatas = acentuadas

    # 3. La más frecuente; la más corta y el orden alfabético solo desempatan,
    #    para que dos corridas sobre los mismos datos den el mismo resultado.
    return max(candidatas, key=lambda v: (candidatas[v], -len(v), v))


def construir_mapa(marcas: Iterable[tuple[str | None, int]],
                   extra: Iterable[tuple[str | None, int]] = ()) -> dict[str, str]:
    """Devuelve {grafía cruda -> grafía canónica} para todas las variantes.

    `marcas` son las grafías que mandan (las de OFF, con su conteo). `extra`
    son las de la góndola: aportan las marcas que OFF no tiene, pero no votan
    dentro de un grupo que OFF ya conoce, porque casi siempre vienen en
    mayúsculas y ganarían por volumen sin aportar la grafía buena.

    Ojo con la distinción: no votar no es quedarse afuera. Una grafía de la
    góndola igual tiene que **resolver** a la canónica, porque es la que llega
    cuando a un producto sin marca se le completa desde el supermercado: si
    "ARCOR" no estuviera en el mapa, esos productos quedarían en un grupo
    aparte y la marca seguiría partida, que es justo lo que se vino a arreglar.
    """
    votos: dict[str, Counter[str]] = {}
    for marca, n in marcas:
        k = clave(marca)
        if k:
            votos.setdefault(k, Counter())[str(marca)] += n

    # Las claves que OFF ya conoce. Se congela **antes** de mirar la góndola:
    # si se consultara `votos` sobre la marcha, la primera grafía de góndola de
    # una marca nueva entraría y a partir de ahí la clave ya existiría, así que
    # las demás grafías de esa misma marca no votarían nunca. Y como SQLite
    # ordena en BINARY, la primera siempre es la de mayúsculas: el resultado
    # medido era que 5.037 de 8.364 marcas quedaban canonizadas GRITANDO, justo
    # las marcas para las que la góndola es la única fuente.
    propias = set(votos)

    # Todas las grafías conocidas de cada clave, voten o no.
    miembros: dict[str, set[str]] = {k: set(v) for k, v in votos.items()}
    for marca, n in extra:
        k = clave(marca)
        if not k:
            continue
        miembros.setdefault(k, set()).add(str(marca))
        if k not in propias:
            votos.setdefault(k, Counter())[str(marca)] += n

    mapa: dict[str, str] = {}
    for k, variantes in votos.items():
        buena = canonica(variantes)
        if not buena:
            continue
        for variante in miembros.get(k, set()) | set(variantes):
            mapa[variante] = buena
    return mapa


def normalizar(marca: str | None, mapa: Mapping[str, str] | None = None) -> str | None:
    """La grafía canónica de una marca suelta.

    Con `mapa` (el de `construir_mapa`) usa lo que votó el catálogo entero.
    Sin él cae a `ALIAS` y a la limpieza básica, que es lo correcto cuando se
    normaliza una marca que no está en la base.
    """
    if marca is None:
        return None
    if mapa:
        directa = mapa.get(str(marca))
        if directa:
            return directa
    limpia = limpiar(marca)
    if not limpia:
        return None
    if mapa:
        por_limpia = mapa.get(limpia)
        if por_limpia:
            return por_limpia
    return ALIAS.get(clave(limpia), limpia)
