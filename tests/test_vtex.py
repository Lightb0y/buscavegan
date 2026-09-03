"""Tests de ingest_vtex: parseo de productos VTEX y recorrido del árbol de
categorías, todo sin red (se mockea la sesión HTTP)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import ingest_vtex as iv  # noqa: E402


# --- clasificación de ramas de alimentos -----------------------------------

def test_ramas_de_alimentos_reconocidas():
    for nombre in ("Almacén", "Desayuno y merienda", "Bebidas",
                   "Lácteos y productos frescos", "Carnes y pescados",
                   "Pescados y Mariscos", "Frutas y Verduras", "Panadería",
                   "Congelados", "Frescos", "Quesos y Fiambres"):
        assert iv.es_rama_de_alimentos(nombre), nombre


def test_ramas_no_alimenticias_descartadas():
    for nombre in ("Electro y tecnología", "Hogar", "Limpieza",
                   "Perfumería y farmacia", "Mundo Bebé", "Mascotas",
                   "Indumentaria", "Gift Cards", "Juguetería y Librería",
                   "Automotor"):
        assert not iv.es_rama_de_alimentos(nombre), nombre


# --- extracción de items ----------------------------------------------------

def _producto(ean="7790001234567", nombre="Yogur entero", marca="Tregar",
             precio=1150.0, categorias=None, items_extra=None):
    items = [{
        "ean": ean,
        "sellers": [{"commertialOffer": {"Price": precio}}] if precio else [],
    }]
    if items_extra:
        items += items_extra
    if categorias is None:
        categorias = ["/Lácteos y productos frescos/Yogures/"]
    return {
        "productName": nombre,
        "brand": marca,
        "categories": categorias,
        "items": items,
    }


def test_extrae_ean_nombre_marca_categoria_precio():
    filas = iv.extraer_items(_producto())
    assert len(filas) == 1
    f = filas[0]
    assert f["ean"] == "7790001234567"
    assert f["nombre"] == "Yogur entero"
    assert f["marca"] == "Tregar"
    assert f["categoria"] == "Yogures"
    assert f["precio"] == 1150.0


def test_producto_con_varios_skus_da_varias_filas():
    # Un producto VTEX agrupa presentaciones (tamaños/variantes); cada una
    # tiene su propio EAN y hay que guardarlas todas.
    p = _producto(ean="1111111111111",
                 items_extra=[{"ean": "2222222222222",
                              "sellers": [{"commertialOffer": {"Price": 500}}]}])
    filas = iv.extraer_items(p)
    assert {f["ean"] for f in filas} == {"1111111111111", "2222222222222"}


def test_sku_sin_ean_se_descarta():
    p = _producto()
    p["items"].append({"ean": "", "sellers": []})
    p["items"].append({"sellers": []})  # ni siquiera trae la clave
    filas = iv.extraer_items(p)
    assert len(filas) == 1  # solo el que sí tenía EAN


def test_ean_no_numerico_se_descarta():
    p = _producto(ean="ABC123")
    assert iv.extraer_items(p) == []


def test_sin_precio_no_rompe():
    p = _producto(precio=None)
    filas = iv.extraer_items(p)
    assert filas[0]["precio"] is None


def test_sin_categorias_no_rompe():
    p = _producto(categorias=[])
    filas = iv.extraer_items(p)
    assert filas[0]["categoria"] is None


# --- recorrido del árbol: bajar a hijos solo si supera la ventana ---------

class _SesionFalsa:
    """Simula las respuestas de `/products/search` para `_total()`, sin red."""

    def __init__(self, totales: dict[str, int]):
        self.totales = totales
        self.pedidos: list[str] = []

    def get(self, url, params=None, timeout=None):
        fq = (params or {}).get("fq", "")
        self.pedidos.append(fq)
        total = self.totales.get(fq, 0)
        return _RespuestaFalsa(total)


class _RespuestaFalsa:
    def __init__(self, total):
        self.ok = True
        self.status_code = 200
        self.headers = {"resources": f"0-0/{total}"}


def test_nodo_chico_se_cosecha_sin_bajar_a_hijos():
    arbol = [{"id": 1, "name": "Almacén", "children": [
        {"id": 2, "name": "Aceites", "children": []},
    ]}]
    sesion = _SesionFalsa({"C:1": 100})  # entra entero, no hace falta bajar
    nodos = iv.nodos_a_cosechar(sesion, "http://x", arbol)
    assert nodos == [("C:1", 100)]
    assert "C:1/2" not in sesion.pedidos  # nunca preguntó por el hijo


def test_nodo_grande_baja_a_los_hijos():
    arbol = [{"id": 1, "name": "Almacén", "children": [
        {"id": 2, "name": "Aceites", "children": []},
        {"id": 3, "name": "Harinas", "children": []},
    ]}]
    sesion = _SesionFalsa({
        "C:1": 6000,       # supera la ventana de 2500: hay que bajar
        "C:1/2": 400,
        "C:1/3": 2600,     # este hijo TAMBIÉN supera la ventana, pero no
    })                     # tiene hijos propios: se cosecha igual, con tope
    nodos = iv.nodos_a_cosechar(sesion, "http://x", arbol)
    assert ("C:1/2", 400) in nodos
    assert ("C:1/3", 2500) in nodos  # capado a la ventana máxima
    assert ("C:1", 6000) not in nodos  # el padre no se cosecha directamente


def test_rama_no_alimenticia_no_se_visita():
    arbol = [{"id": 9, "name": "Electro y tecnología", "children": []}]
    sesion = _SesionFalsa({"C:9": 5000})
    nodos = iv.nodos_a_cosechar(sesion, "http://x", arbol)
    assert nodos == []
    assert sesion.pedidos == []  # ni siquiera consultó el total


def test_nodo_sin_productos_se_descarta():
    arbol = [{"id": 1, "name": "Almacén", "children": []}]
    sesion = _SesionFalsa({"C:1": 0})
    assert iv.nodos_a_cosechar(sesion, "http://x", arbol) == []
