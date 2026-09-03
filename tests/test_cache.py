"""Tests del cache de OFF y de la cola de revisión (checklist de SPEC.md §9).

El punto del cache: la 2ª corrida no puede volver a preguntarle a OFF por EANs
que ya conoce. Sin eso, cada refresco tardaría horas y agotaría el rate limit.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config  # noqa: E402
import db as _db  # noqa: E402
import enrich_off  # noqa: E402
import revision  # noqa: E402


class ClienteFalso:
    """Cliente de OFF que cuenta las consultas en vez de salir a la red."""

    def __init__(self, respuestas=None, falla=()):
        self.respuestas = respuestas or {}
        self.falla = set(falla)
        self.consultas = []

    def fetch(self, ean):
        self.consultas.append(ean)
        if ean in self.falla:
            raise RuntimeError(f"OFF no responde para {ean}")
        return self.respuestas.get(ean)


def conexion(tmp_path):
    conn = _db.connect(tmp_path / "test.db")
    _db.init_db(conn)
    return conn


# --- cache ----------------------------------------------------------------

def test_segunda_corrida_no_reconsulta(tmp_path):
    conn = conexion(tmp_path)
    eans = ["7790001", "7790002"]
    cliente = ClienteFalso({"7790001": {"code": "7790001"}})

    primera = enrich_off.enrich(conn, eans, cliente, verbose=False)
    assert primera["consultados"] == 2 and len(cliente.consultas) == 2

    cliente.consultas.clear()
    segunda = enrich_off.enrich(conn, eans, cliente, verbose=False)
    assert cliente.consultas == [], "no debe volver a preguntarle a OFF"
    assert segunda["cacheados"] == 2 and segunda["consultados"] == 0
    conn.close()


def test_los_misses_tambien_se_cachean(tmp_path):
    # Un EAN que OFF no conoce no se vuelve a preguntar en cada refresco.
    conn = conexion(tmp_path)
    cliente = ClienteFalso({})
    enrich_off.enrich(conn, ["7790003"], cliente, verbose=False)
    assert enrich_off.pending_eans(conn, ["7790003"]) == []
    conn.close()


def test_un_error_de_servicio_no_se_cachea(tmp_path):
    # Un 503 no es evidencia de que el producto no exista: hay que reintentar.
    conn = conexion(tmp_path)
    cliente = ClienteFalso({}, falla={"7790004"})
    stats = enrich_off.enrich(conn, ["7790004"], cliente, verbose=False)
    assert stats["errores"] == 1
    assert enrich_off.pending_eans(conn, ["7790004"]) == ["7790004"]
    conn.close()


def test_cache_vencido_se_reconsulta(tmp_path):
    conn = conexion(tmp_path)
    cliente = ClienteFalso({"7790005": {"code": "7790005"}})
    enrich_off.enrich(conn, ["7790005"], cliente, verbose=False)
    # Con TTL de 0 días, lo guardado ya está vencido.
    assert enrich_off.pending_eans(conn, ["7790005"], ttl_days=0) == ["7790005"]
    conn.close()


def test_no_repite_eans_duplicados(tmp_path):
    conn = conexion(tmp_path)
    cliente = ClienteFalso({})
    enrich_off.enrich(conn, ["7790006", "7790006", "7790006"], cliente,
                      verbose=False)
    assert len(cliente.consultas) == 1
    conn.close()


# --- Capa 4: cola de revisión ---------------------------------------------

def _producto(conn, ean, nombre, estado):
    conn.execute(
        "INSERT OR REPLACE INTO productos (ean, nombre, marca, categoria,"
        " estado, fuente_decision, actualizado) VALUES (?,?,?,?,?,?,?)",
        (ean, nombre, "Marca", "Otros", estado, "sin_datos", _db.now_iso()))
    conn.commit()


def test_exporta_solo_lo_pendiente(tmp_path):
    conn = conexion(tmp_path)
    _producto(conn, "1", "Pendiente", config.REVISAR)
    _producto(conn, "2", "Resuelto", config.APTO)

    salida = tmp_path / "revision.csv"
    n = revision.exportar(conn, salida)
    assert n == 1

    with salida.open(encoding="utf-8-sig") as fh:
        filas = list(csv.DictReader(fh))
    assert len(filas) == 1 and filas[0]["ean"] == "1"
    assert filas[0]["estado_corregido"] == ""
    conn.close()


def test_la_correccion_humana_pisa_a_la_automatica(tmp_path):
    conn = conexion(tmp_path)
    _producto(conn, "1", "Pendiente", config.REVISAR)

    entrada = tmp_path / "curado.csv"
    with entrada.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(revision.COLUMNAS)
        w.writerow(["1", "Pendiente", "", "", "revisar", "", "", "apto", "ana"])

    revision.importar(conn, entrada)
    assert revision.aplicar(conn) == 1

    fila = conn.execute("SELECT * FROM productos WHERE ean='1'").fetchone()
    assert fila["estado"] == config.APTO
    assert fila["fuente_decision"] == revision.FUENTE_CURADURIA
    assert "ana" in fila["motivo"]
    conn.close()


def test_ignora_estados_invalidos(tmp_path):
    conn = conexion(tmp_path)
    _producto(conn, "1", "Pendiente", config.REVISAR)

    entrada = tmp_path / "curado.csv"
    with entrada.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(revision.COLUMNAS)
        w.writerow(["1", "Pendiente", "", "", "revisar", "", "", "vegano", ""])

    stats = revision.importar(conn, entrada)
    assert stats["aplicadas"] == 0 and stats["invalidas"]
    assert conn.execute(
        "SELECT estado FROM productos WHERE ean='1'").fetchone()[0] == config.REVISAR
    conn.close()


def test_filas_sin_completar_se_ignoran(tmp_path):
    conn = conexion(tmp_path)
    entrada = tmp_path / "curado.csv"
    with entrada.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(revision.COLUMNAS)
        w.writerow(["1", "Pendiente", "", "", "revisar", "", "", "", ""])

    stats = revision.importar(conn, entrada)
    assert stats["ignoradas"] == 1 and stats["aplicadas"] == 0
    conn.close()
