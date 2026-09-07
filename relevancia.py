"""Filtro de relevancia: descarta entradas de OFF que casi seguro no se
venden en Argentina, aunque estén etiquetadas `countries_tags: en:argentina`.

Por qué hace falta
------------------
OFF es colaborativo y el tag de país lo carga quien sube el producto: alguien
puede escanear un producto en Medio Oriente y, por error o porque también se
vende ahí, dejarlo marcado como Argentina también. El síntoma es inconfundible:
**19,8% del catálogo** tenía el nombre escrito en un alfabeto que ningún
supermercado argentino usa como nombre principal (árabe, hebreo, cirílico...),
y esos productos representaban **38,6% de todo el bucket `revisar`** — no es
que falten datos, es que no correspondían a este catálogo.

Este filtro corre en `build_db.py`, antes de clasificar: los productos que no
pasan **no se borran** de `catalogo` ni de `off_cache` (siguen ahí por si el
criterio cambia), simplemente no llegan a la tabla final `productos` ni a la
búsqueda.

Deliberadamente angosto: solo se excluye por señales objetivas (alfabeto del
nombre, longitud de EAN imposible), nunca por juicios de "esto no parece
argentino". Un nombre en portugués, italiano o inglés pasa sin problema: son
alfabetos latinos y perfectamente plausibles en una góndola argentina.
"""
from __future__ import annotations

import re

# Bloques Unicode que no se usan como alfabeto principal en el comercio
# argentino. No incluye nada latino (con o sin acentos): español, portugués,
# inglés, italiano, alemán, francés pasan todos sin tocar este filtro.
_NO_LATINO_RE = re.compile(
    "["
    "֐-׿"    # hebreo
    "؀-ۿ"    # arabe
    "ݐ-ݿ"    # arabe (suplemento)
    "ﭐ-﷿"    # arabe (formas de presentacion A)
    "ﹰ-ﻼ"    # arabe (formas de presentacion B) — corta ANTES de U+FEFF: ese
              # código es el BOM (utf-8-sig), no un carácter árabe real.
    "Ѐ-ӿ"    # cirilico
    "Ԁ-ԯ"    # cirilico (suplemento)
    "԰-֏"    # armenio
    "Ⴀ-ჿ"    # georgiano
    "ऀ-ॿ"    # devanagari (hindi)
    "฀-๿"    # tailandes
    "一-鿿"    # ideogramas CJK (chino/japones)
    "぀-ゟ"    # hiragana
    "゠-ヿ"    # katakana
    "가-힣"    # hangul (coreano)
    "]"
)

# Un código de barras real tiene 8 (EAN-8), 12 (UPC-A), 13 (EAN-13) o
# 14 (GTIN-14) dígitos. Cualquier otra longitud no se puede escanear en una
# caja registradora real.
_LARGOS_EAN_VALIDOS = {8, 12, 13, 14}


def motivo_exclusion(nombre: str | None, ean: str | None) -> str | None:
    """None si el producto es relevante; si no, una razón legible."""
    if nombre and _NO_LATINO_RE.search(nombre):
        return ("nombre en un alfabeto que no se usa en el comercio "
                "argentino (posible país mal etiquetado en origen)")
    if ean and len(ean) not in _LARGOS_EAN_VALIDOS:
        return f"el código '{ean}' no tiene una longitud de EAN/UPC real"
    return None


def es_relevante(nombre: str | None, ean: str | None) -> bool:
    return motivo_exclusion(nombre, ean) is None


# --- Fichas fantasma -------------------------------------------------------
# Open Food Facts se llena escaneando códigos de barras: alguien apunta el
# teléfono a un producto y queda creada una entrada con un nombre y poco más.
# Muchas nunca se completan, y como el pool de códigos lo comparte con Open
# Beauty Facts, terminan colándose shampoos, cremas y hasta medicamentos en un
# catálogo de alimentos.
#
# Medido sobre el catálogo real: el 80% de lo que quedaba en `revisar` no tenía
# ni siquiera categoría, y solo el 35% tenía código de barras argentino (contra
# el 79% de los productos que sí se pudieron clasificar).
#
# El criterio para descartarlas es deliberadamente estrecho: hacen falta las
# CUATRO condiciones. Con que el producto tenga una sola señal —una categoría,
# una lista de ingredientes, presencia en una góndola real o un veredicto
# fundado— se queda. Cortar solo por "no tiene categoría" se llevaba puestos
# 1.608 productos bien clasificados, entre ellos 457 con sello vegano
# certificado: sería tirar evidencia por falta de una etiqueta.

# Fuentes que constituyen evidencia real, no una inferencia sobre el nombre.
FUENTES_CON_EVIDENCIA = frozenset({
    "certificacion_oficial", "off_label", "sello_super",
    "ingredientes", "ingredientes_super", "off_analysis",
})


def es_ficha_fantasma(categorias_off, ingredientes: str | None,
                      cadenas_confirmadas: str | None,
                      fuente_decision: str | None) -> bool:
    """True si de este producto no sabemos absolutamente nada.

    No es "no pudimos clasificarlo" —eso es `revisar` y se muestra igual—,
    es "no hay ninguna evidencia de que sea un alimento que se venda acá".
    """
    if categorias_off:
        return False
    if (ingredientes or "").strip():
        return False
    if cadenas_confirmadas:
        return False
    if fuente_decision in FUENTES_CON_EVIDENCIA:
        return False
    return True
