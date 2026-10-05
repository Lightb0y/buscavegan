"""El reporte de cobertura mide lo mismo que se publica.

`sprint0` armaba su propia consulta: el catálogo de OFF solo, sin las fichas
del supermercado y sin el filtro de relevancia. Con la cosecha grande eso
dejaba afuera del reporte a decenas de miles de productos del sitio, y a los
que sí contaba los clasificaba sin la mejor evidencia que tienen.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import build_db  # noqa: E402
import db as _db  # noqa: E402
import sprint0  # noqa: E402

EAN_OFF = "7790000003014"
EAN_GONDOLA = "7790000003021"
EAN_GONDOLA_VACIA = "7790000003038"
EAN_ALFABETO = "7790000003045"


def _base(tmp_path):
    conn = _db.connect(tmp_path / "s0.db")
    _db.init_db(conn)
    _db.upsert_catalogo(conn, [
        {"ean": EAN_OFF, "nombre": "Galletitas de agua", "marca": "Marca"},
        {"ean": EAN_ALFABETO, "nombre": "بسكويت", "marca": "Marca"},
    ])
    for ean in (EAN_OFF, EAN_ALFABETO):
        _db.cache_put(conn, ean, {
            "ingredients_text": "harina de trigo, agua, sal",
            "categories_tags": ["en:biscuits"]})
    for ean, nombre in ((EAN_GONDOLA, "Fideos tirabuzón"),
                        (EAN_GONDOLA_VACIA, "Producto sin ficha")):
        conn.execute(
            "INSERT INTO vtex_catalogo (ean, cadena, nombre, marca, categoria)"
            " VALUES (?, 'disco', ?, 'LUCCHETTI', 'Almacén')", (ean, nombre))
    conn.execute(
        "INSERT INTO vtex_ficha (ean, cadena, ingredientes, actualizado)"
        " VALUES (?, 'disco', 'sémola de trigo, agua', '2026-01-01')",
        (EAN_GONDOLA,))
    conn.execute(
        "INSERT INTO vtex_ficha (ean, cadena, actualizado)"
        " VALUES (?, 'disco', '2026-01-01')", (EAN_GONDOLA_VACIA,))
    conn.commit()
    return conn


def test_el_reporte_cuenta_los_mismos_productos_que_publica_el_sitio(tmp_path):
    conn = _base(tmp_path)
    build_db.build(conn, verbose=False)
    publicados = {r[0] for r in conn.execute("SELECT ean FROM productos")}
    medidos = {d["ean"] for d in sprint0.cargar_muestra(conn, None)}

    assert medidos == publicados == {EAN_OFF, EAN_GONDOLA}
    conn.close()


def test_el_reporte_clasifica_con_la_ficha_del_supermercado(tmp_path):
    conn = _base(tmp_path)
    rep = sprint0.medir(conn, sprint0.cargar_muestra(conn, None))

    assert rep["con_ingredientes"] == 2
    assert rep["con_ingredientes_super"] == 1
    assert rep["fuentes"].get(build_db.FUENTE_INGREDIENTES_SUPER) == 1
    json.dumps(rep)  # el reporte se guarda como JSON
    conn.close()
