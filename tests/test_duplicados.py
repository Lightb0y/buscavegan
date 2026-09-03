"""Tests de `_propagar_duplicados`: el caso "Oreo" (mismo nombre y marca,
EANs distintos, veredictos que se contradicen entre sí)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import build_db  # noqa: E402
import classify_rules as cr  # noqa: E402
import config  # noqa: E402
import db as _db  # noqa: E402

APTO, NO_APTO, REVISAR, VEG = (
    config.APTO, config.NO_APTO, config.REVISAR, config.VEGETARIANO)


def _conn(tmp_path):
    conn = _db.connect(tmp_path / "dup.db")
    _db.init_db(conn)
    return conn


def _insertar(conn, ean, nombre, marca, estado, fuente):
    conn.execute(
        "INSERT INTO productos (ean, nombre, marca, categoria, estado,"
        " fuente_decision, actualizado) VALUES (?,?,?,?,?,?,?)",
        (ean, nombre, marca, "Otros", estado, fuente, _db.now_iso()))
    if estado == REVISAR:
        conn.execute(
            "INSERT INTO revision_pendiente (ean, nombre, marca, creado)"
            " VALUES (?,?,?,?)", (ean, nombre, marca, _db.now_iso()))
    conn.commit()


def test_el_caso_oreo(tmp_path):
    # Mismo nombre y marca, 4 EANs, tres veredictos distintos.
    conn = _conn(tmp_path)
    _insertar(conn, "1", "Oreo", "Oreo", APTO, "ingredientes")
    _insertar(conn, "2", "Oreo", "Oreo", VEG, "ingredientes")
    _insertar(conn, "3", "Oreo", "Oreo", REVISAR, "sin_datos")
    _insertar(conn, "4", "Oreo", "Oreo", REVISAR, "sin_datos")

    n = build_db._propagar_duplicados(conn)
    assert n == 3  # todos menos el que ya tenía el peor estado (vegetariano)

    estados = {r["ean"]: r["estado"] for r in
              conn.execute("SELECT ean, estado FROM productos")}
    # El peor estado real (vegetariano, vino con ingredientes) gana en todos.
    assert set(estados.values()) == {VEG}
    conn.close()


def test_no_apto_es_mas_restrictivo_que_vegetariano(tmp_path):
    conn = _conn(tmp_path)
    _insertar(conn, "1", "Producto X", "Marca", VEG, "ingredientes")
    _insertar(conn, "2", "Producto X", "Marca", NO_APTO, "ingredientes")

    build_db._propagar_duplicados(conn)
    estados = {r["ean"]: r["estado"] for r in
              conn.execute("SELECT ean, estado FROM productos")}
    assert estados == {"1": NO_APTO, "2": NO_APTO}
    conn.close()


def test_revisar_se_rescata_con_el_peor_de_un_hermano(tmp_path):
    conn = _conn(tmp_path)
    _insertar(conn, "1", "Producto Y", "Marca", NO_APTO, "off_label")
    _insertar(conn, "2", "Producto Y", "Marca", REVISAR, "sin_datos")

    n = build_db._propagar_duplicados(conn)
    assert n == 1
    fila = conn.execute(
        "SELECT estado, fuente_decision, motivo FROM productos WHERE ean='2'"
    ).fetchone()
    assert fila["estado"] == NO_APTO
    assert fila["fuente_decision"] == build_db.FUENTE_DUPLICADO
    assert "1" in fila["motivo"]
    # Y sale de la cola de revisión pendiente.
    assert conn.execute(
        "SELECT COUNT(*) FROM revision_pendiente WHERE ean='2'"
    ).fetchone()[0] == 0
    conn.close()


def test_apto_no_se_propaga_como_optimismo(tmp_path):
    # Si el único con evidencia real dice `apto`, NO se sube a un hermano en
    # `revisar`: propagar hacia el lado optimista violaría la regla de
    # seguridad. Un hermano en `revisar` solo se mueve si hay evidencia de
    # que el producto es riesgoso, nunca para confirmarlo como seguro.
    conn = _conn(tmp_path)
    _insertar(conn, "1", "Producto Z", "Marca", APTO, "ingredientes")
    _insertar(conn, "2", "Producto Z", "Marca", REVISAR, "sin_datos")

    n = build_db._propagar_duplicados(conn)
    assert n == 0
    estados = {r["ean"]: r["estado"] for r in
              conn.execute("SELECT ean, estado FROM productos")}
    assert estados == {"1": APTO, "2": REVISAR}
    conn.close()


def test_nombres_distintos_no_se_agrupan(tmp_path):
    conn = _conn(tmp_path)
    _insertar(conn, "1", "Mochi oreo", "Marca", REVISAR, "sin_datos")
    _insertar(conn, "2", "Oreo sabor mani", "Marca", NO_APTO, "ingredientes")

    n = build_db._propagar_duplicados(conn)
    assert n == 0  # nombres normalizados distintos: no son el mismo grupo
    conn.close()


def test_grupo_sin_ninguna_evidencia_no_se_toca(tmp_path):
    conn = _conn(tmp_path)
    _insertar(conn, "1", "Producto W", "Marca", REVISAR, "sin_datos")
    _insertar(conn, "2", "Producto W", "Marca", REVISAR, "sin_datos")

    n = build_db._propagar_duplicados(conn)
    assert n == 0
    conn.close()


def test_no_toca_al_que_ya_tiene_el_peor_estado(tmp_path):
    # El EAN que originó el peor veredicto no debe reescribirse a sí mismo
    # con fuente "duplicado": conserva su propia razón original.
    conn = _conn(tmp_path)
    _insertar(conn, "1", "Producto V", "Marca", NO_APTO, "ingredientes")
    _insertar(conn, "2", "Producto V", "Marca", REVISAR, "sin_datos")

    build_db._propagar_duplicados(conn)
    fila1 = conn.execute(
        "SELECT fuente_decision FROM productos WHERE ean='1'").fetchone()
    assert fila1["fuente_decision"] == "ingredientes"
    conn.close()


def test_normaliza_antes_de_agrupar(tmp_path):
    # Tildes/mayúsculas no deberían crear grupos falsos-negativos.
    conn = _conn(tmp_path)
    _insertar(conn, "1", "Café Cortado", "Café Martínez", NO_APTO, "ingredientes")
    _insertar(conn, "2", "café cortado", "cafe martinez", REVISAR, "sin_datos")

    assert cr.normalize("Café Martínez") == cr.normalize("cafe martinez")
    n = build_db._propagar_duplicados(conn)
    assert n == 1
    conn.close()
