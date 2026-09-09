"""Lista de exclusión manual: fichas que no son alimentos y no van en el sitio.

Por qué hace falta una lista a mano
-----------------------------------
Open Food Facts comparte el pool de códigos de barras con Open Beauty Facts y
Open Products Facts: alguien escanea un esmalte de uñas, un desodorante o un
jabón y queda una ficha creada en la misma base. El filtro de
`relevancia.es_ficha_fantasma` saca las que no tienen ninguna señal, pero
varias traen marca —y a veces categoría de OFF—, lo suficiente para pasarlo, y
aun así son un cosmético, un medicamento o un artículo de limpieza. Ningún
criterio automático los separa de un alimento sin arriesgarse a llevarse
productos buenos, así que se los saca uno por uno, con nombre y motivo a la
vista.

Igual que `relevancia`: no se borra nada de `catalogo` ni de `off_cache`. El
producto simplemente no llega a la tabla final `productos` ni a la búsqueda. Si
mañana se decide que corresponde, se saca de esta lista y vuelve solo en el
próximo refresco.

Cada EAN se verificó por nombre contra la base publicada antes de agregarlo.
"""
from __future__ import annotations

# EAN -> por qué no es un alimento. El motivo es para la próxima persona que
# lea esta lista; no se muestra en ningún lado.
EXCLUIDOS: dict[str, str] = {
    "7791905023623": "alcohol en aerosol (artículo de limpieza)",
    "7791293033198": "antibacterial fresh Rexona (desodorante)",
    "0650240004643": "asepxia (dermocosmética)",
    "7798140259459": "asepxia Genomma (dermocosmética)",
    "7909189091874": "esmalte (cosmético para uñas)",
    "2002138100001": "esmalte para uñas Allegro (cosmético)",
    "7793008005063": "Issue (tintura para el cabello)",
    "26130351000126": "Macaroni (ficha sin marca, categoría ni ingredientes)",
    "6260480121013": "Manizan (crema medicinal)",
    "7506339356939": "Always (artículo de higiene femenina)",
    "7791984000614": "Oralsone Max (medicamento de venta libre)",
    "7891150034075": "jabón (artículo de higiene)",
    "7790990586983": "jabón Limol (artículo de limpieza)",
    "77913104": "jabón de glicerina Farmacity (cosmético)",
    "7891010669843": "jabón glicerinado Johnson's (cosmético)",
    "8480017134073": "jabón Bonté natural glycerin (cosmético)",
}


def es_excluido(ean: str | None) -> bool:
    return ean in EXCLUIDOS


def motivo(ean: str | None) -> str | None:
    """El motivo legible de la exclusión, o None si el EAN no está en la lista."""
    return EXCLUIDOS.get(ean or "")
