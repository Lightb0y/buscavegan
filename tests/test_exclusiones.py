"""Tests de la lista de exclusión manual.

Son cosméticos, remedios y artículos de limpieza que se colaron desde el pool
de códigos que OFF comparte con Open Beauty Facts. El filtro de fichas
fantasma no los agarra porque traen marca —y a veces categoría—, así que van
en una lista a mano (`exclusiones.EXCLUIDOS`).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import build_db  # noqa: E402
import db as _db  # noqa: E402
import exclusiones  # noqa: E402


# --- la lista, aislada --------------------------------------------------------

def test_todos_los_eans_tienen_largo_real():
    # 8, 12, 13 o 14 dígitos: si me equivoqué tipeando un EAN, que salte acá
    # antes de que quede una línea muerta que no saca nada.
    for ean in exclusiones.EXCLUIDOS:
        assert ean.isdigit(), ean
        assert len(ean) in (8, 12, 13, 14), f"{ean}: {len(ean)} dígitos"


def test_cada_exclusion_trae_su_motivo():
    for ean, por_que in exclusiones.EXCLUIDOS.items():
        assert por_que and por_que.strip(), ean
        assert exclusiones.motivo(ean) == por_que
        assert exclusiones.es_excluido(ean)


def test_un_ean_cualquiera_no_esta_excluido():
    assert not exclusiones.es_excluido("7790001234567")
    assert exclusiones.motivo("7790001234567") is None
    assert not exclusiones.es_excluido(None)


# --- integrado en el pipeline ----------------------------------------------

def _conn(tmp_path):
    conn = _db.connect(tmp_path / "excl.db")
    _db.init_db(conn)
    return conn


def test_el_pipeline_saca_la_ficha_excluida(tmp_path):
    conn = _conn(tmp_path)
    ean = next(iter(exclusiones.EXCLUIDOS))
    _db.upsert_catalogo(conn, [
        {"ean": ean, "nombre": "Cosmético Cualquiera", "marca": "Marca"},
    ])
    # Con categoría de OFF alcanza para pasar el filtro de fichas fantasma:
    # sin la lista de exclusión, este producto llegaría a la búsqueda.
    conn.execute(
        "INSERT OR REPLACE INTO off_cache (ean, found, payload, consultado)"
        " VALUES (?,1,?,?)",
        (ean, json.dumps({"code": ean, "categories_tags": ["en:cosmetics"]}),
         "2026-01-01"))
    conn.commit()

    build_db.build(conn, verbose=False)

    assert conn.execute(
        "SELECT COUNT(*) FROM productos WHERE ean=?", (ean,)).fetchone()[0] == 0
    # Tampoco queda pendiente de revisión manual.
    assert conn.execute(
        "SELECT COUNT(*) FROM revision_pendiente WHERE ean=?", (ean,)
    ).fetchone()[0] == 0
    # El dato crudo sobrevive: si mañana se saca de la lista, vuelve solo.
    assert conn.execute(
        "SELECT COUNT(*) FROM catalogo WHERE ean=?", (ean,)).fetchone()[0] == 1
    conn.close()


def test_un_alimento_normal_no_se_ve_afectado(tmp_path):
    conn = _conn(tmp_path)
    _db.upsert_catalogo(conn, [
        {"ean": "7790001234567", "nombre": "Fideos Tirabuzón", "marca": "Marca"},
    ])
    conn.execute(
        "INSERT INTO vtex_ficha (ean, cadena, ingredientes, trazas, sellos,"
        " actualizado) VALUES ('7790001234567','disco',"
        " 'sémola de trigo candeal, agua', NULL, NULL, '2026-01-01')")
    conn.commit()

    stats = build_db.build(conn, verbose=False)

    assert conn.execute(
        "SELECT COUNT(*) FROM productos WHERE ean='7790001234567'"
    ).fetchone()[0] == 1
    assert stats["excluidos_manual"] == 0
    conn.close()
