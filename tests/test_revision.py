"""Tests de la Capa 4: las dos colas de curaduría y la durabilidad.

Dos cosas se fijan acá.

La primera es **qué entra en la cola de riesgo**. Es la cola corta y cara: los
productos que hoy se muestran como `apto` sin que nadie haya leído la etiqueta.
Que se cuele un `apto` con evidencia real solo hace perder tiempo, pero que se
escape uno estimado por el nombre deja sin revisar justo lo que hay que
revisar, así que los tests apuntan sobre todo a los bordes.

La segunda es que **una corrección humana no se pierda**. La tabla vive en la
base, y la base es derivada: en CI se restaura de un cache que puede vencer.
Si el único lugar donde vive una decisión humana es esa tabla, una corrida sin
cache la borra sin que nadie se entere. Por eso el refresco reimporta los CSV
versionados, y por eso reimportar tiene que ser idempotente.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config  # noqa: E402
import db as _db  # noqa: E402
import revision  # noqa: E402

APTO, NO_APTO, REVISAR, VEG = (
    config.APTO, config.NO_APTO, config.REVISAR, config.VEGETARIANO)


def _conn(tmp_path):
    conn = _db.connect(tmp_path / "rev.db")
    _db.init_db(conn)
    revision.init(conn)
    return conn


def _insertar(conn, ean, nombre, estado, fuente, marca="Marca"):
    conn.execute(
        "INSERT INTO productos (ean, nombre, marca, categoria, estado,"
        " fuente_decision, actualizado) VALUES (?,?,?,?,?,?,?)",
        (ean, nombre, marca, "Otros", estado, fuente, _db.now_iso()))
    conn.commit()


def _leer(destino: Path) -> list[dict]:
    with destino.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def _escribir_csv(destino: Path, filas: list[dict]) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=revision.COLUMNAS)
        w.writeheader()
        for f in filas:
            w.writerow({c: f.get(c, "") for c in revision.COLUMNAS})


# --- La cola de riesgo -----------------------------------------------------

def test_riesgo_saca_los_apto_estimados_por_el_nombre(tmp_path):
    conn = _conn(tmp_path)
    _insertar(conn, "1", "Aceitunas negras", APTO, "heuristica")
    _insertar(conn, "2", "Arroz Amanda", APTO, "ml")

    destino = tmp_path / "riesgo.csv"
    assert revision.exportar(conn, destino, riesgo=True) == 2
    assert {f["ean"] for f in _leer(destino)} == {"1", "2"}


def test_riesgo_no_toca_los_apto_con_evidencia_real(tmp_path):
    # El punto de la cola: un `apto` leído de la etiqueta o certificado no
    # necesita que nadie lo revise. Si entrara igual, la cola dejaría de ser
    # corta y perdería su razón de ser.
    conn = _conn(tmp_path)
    _insertar(conn, "1", "Leche de almendras", APTO, "ingredientes")
    _insertar(conn, "2", "Medallon de quinoa", APTO, "certificacion_oficial")
    _insertar(conn, "3", "Galletitas de agua", APTO, "ingredientes_super")
    _insertar(conn, "4", "Snack vegano", APTO, "sello_super")
    _insertar(conn, "5", "Barra de cereal", APTO, "off_label")

    assert revision.exportar(conn, tmp_path / "riesgo.csv", riesgo=True) == 0


def test_riesgo_ignora_los_no_apto_estimados_por_el_nombre(tmp_path):
    # Un `no_apto` adivinado por el nombre también puede estar mal, pero el
    # error barato es ese: esconde un producto bueno, no hace comer algo que
    # no se quería comer. Esta cola es solo para el error caro.
    conn = _conn(tmp_path)
    _insertar(conn, "1", "Milanesa de carne", NO_APTO, "heuristica")
    _insertar(conn, "2", "Yogur de frutilla", VEG, "ml")

    assert revision.exportar(conn, tmp_path / "riesgo.csv", riesgo=True) == 0


def test_riesgo_y_revisar_son_colas_disjuntas(tmp_path):
    conn = _conn(tmp_path)
    _insertar(conn, "1", "Aceitunas negras", APTO, "heuristica")
    _insertar(conn, "2", "Producto sin datos", REVISAR, "sin_datos")

    riesgo = tmp_path / "riesgo.csv"
    pendiente = tmp_path / "pendiente.csv"
    revision.exportar(conn, riesgo, riesgo=True)
    revision.exportar(conn, pendiente)

    assert [f["ean"] for f in _leer(riesgo)] == ["1"]
    assert [f["ean"] for f in _leer(pendiente)] == ["2"]


def test_el_csv_de_riesgo_entra_por_el_mismo_importar(tmp_path):
    # La cola nueva no trae un formato nuevo: se exporta, se completa la misma
    # columna y vuelve por el mismo camino que la cola de siempre.
    conn = _conn(tmp_path)
    _insertar(conn, "1", "Almendras con chocolate", APTO, "heuristica")

    destino = tmp_path / "riesgo.csv"
    revision.exportar(conn, destino, riesgo=True)

    filas = _leer(destino)
    filas[0]["estado_corregido"] = VEG
    filas[0]["revisor"] = "valen"
    _escribir_csv(destino, filas)

    st = revision.importar(conn, destino)
    assert st["aplicadas"] == 1
    revision.aplicar(conn)

    fila = conn.execute(
        "SELECT estado, fuente_decision FROM productos WHERE ean='1'").fetchone()
    assert fila["estado"] == VEG
    assert fila["fuente_decision"] == revision.FUENTE_CURADURIA


# --- Durabilidad de la curaduría -------------------------------------------

def test_importar_directorio_levanta_todos_los_csv(tmp_path):
    conn = _conn(tmp_path)
    _insertar(conn, "1", "Malta", REVISAR, "sin_datos")
    _insertar(conn, "2", "Paseo salvado", REVISAR, "sin_datos")

    carpeta = tmp_path / "CORRECCIONES"
    _escribir_csv(carpeta / "2026-09-08.csv",
                  [{"ean": "1", "estado_corregido": APTO, "revisor": "valen"}])
    _escribir_csv(carpeta / "2026-09-09.csv",
                  [{"ean": "2", "estado_corregido": APTO, "revisor": "joshy"}])

    st = revision.importar_directorio(conn, carpeta)
    assert st["archivos"] == 2
    assert st["aplicadas"] == 2

    assert revision.aplicar(conn) == 2
    estados = dict(conn.execute("SELECT ean, estado FROM productos"))
    assert estados == {"1": APTO, "2": APTO}


def test_reimportar_no_duplica_ni_revierte(tmp_path):
    # El refresco corre esto en cada corrida: tiene que poder leer el mismo
    # archivo cien veces y dejar la base igual que la primera vez.
    conn = _conn(tmp_path)
    _insertar(conn, "1", "Malta", REVISAR, "sin_datos")

    carpeta = tmp_path / "CORRECCIONES"
    _escribir_csv(carpeta / "correcciones.csv",
                  [{"ean": "1", "estado_corregido": APTO, "revisor": "valen"}])

    for _ in range(3):
        revision.importar_directorio(conn, carpeta)

    assert conn.execute("SELECT COUNT(*) FROM correcciones").fetchone()[0] == 1


def test_una_correccion_sobrevive_a_perder_la_base_entera(tmp_path):
    # El escenario real que esto cubre: el cache de CI vence y la base se
    # rearma de cero. Si la decisión humana solo viviera en la tabla, se
    # perdería en silencio.
    carpeta = tmp_path / "CORRECCIONES"
    _escribir_csv(carpeta / "correcciones.csv",
                  [{"ean": "1", "estado_corregido": APTO, "revisor": "valen"}])

    vieja = _conn(tmp_path)
    _insertar(vieja, "1", "Malta", REVISAR, "sin_datos")
    revision.importar_directorio(vieja, carpeta)
    revision.aplicar(vieja)
    vieja.close()
    (tmp_path / "rev.db").unlink()

    nueva = _conn(tmp_path)
    _insertar(nueva, "1", "Malta", REVISAR, "sin_datos")
    assert nueva.execute(
        "SELECT estado FROM productos WHERE ean='1'").fetchone()[0] == REVISAR

    revision.importar_directorio(nueva, carpeta)
    revision.aplicar(nueva)
    assert nueva.execute(
        "SELECT estado FROM productos WHERE ean='1'").fetchone()[0] == APTO


def test_sin_carpeta_no_es_un_error(tmp_path):
    # En una instalación limpia todavía no hay nada curado. El refresco tiene
    # que seguir de largo, no abortar.
    conn = _conn(tmp_path)
    st = revision.importar_directorio(conn, tmp_path / "no-existe")
    assert st == {"archivos": 0, "leidas": 0, "aplicadas": 0, "ignoradas": 0,
                  "invalidas": []}


def test_una_fila_con_estado_invalido_no_frena_al_resto(tmp_path):
    conn = _conn(tmp_path)
    _insertar(conn, "1", "Malta", REVISAR, "sin_datos")
    _insertar(conn, "2", "Paseo salvado", REVISAR, "sin_datos")

    carpeta = tmp_path / "CORRECCIONES"
    _escribir_csv(carpeta / "correcciones.csv", [
        {"ean": "1", "estado_corregido": "vegano", "revisor": "valen"},
        {"ean": "2", "estado_corregido": APTO, "revisor": "valen"},
    ])

    st = revision.importar_directorio(conn, carpeta)
    assert st["aplicadas"] == 1
    assert len(st["invalidas"]) == 1
    assert "correcciones.csv" in st["invalidas"][0]
