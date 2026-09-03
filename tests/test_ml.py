"""Tests de la Capa 3: sobre todo, que el umbral asimétrico proteja el `apto`."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import classify_ml  # noqa: E402
import config  # noqa: E402


class ModeloFalso:
    """Modelo mínimo con probabilidades fijas, para probar solo el umbral."""

    def __init__(self, clases, probas):
        self.classes_ = clases
        self._probas = probas

    def predict_proba(self, _textos):
        return [self._probas]


def test_apto_necesita_mucha_confianza():
    # 0.70 alcanzaría para la clase más probable, pero no para afirmar `apto`.
    modelo = ModeloFalso([config.APTO, config.NO_APTO], [0.70, 0.30])
    estado, p = classify_ml.predecir(modelo, "Galletitas Xyz")
    assert estado == config.REVISAR and p == 0.70


def test_apto_con_confianza_suficiente_pasa():
    modelo = ModeloFalso([config.APTO, config.NO_APTO], [0.92, 0.08])
    estado, _ = classify_ml.predecir(modelo, "Fideos secos Xyz")
    assert estado == config.APTO


def test_no_apto_tiene_umbral_mas_bajo():
    # El mismo 0.70 que no alcanza para `apto` sí alcanza para `no_apto`:
    # equivocarse hacia el lado restrictivo es el error barato.
    modelo = ModeloFalso([config.APTO, config.NO_APTO], [0.30, 0.70])
    estado, _ = classify_ml.predecir(modelo, "Salchichas Xyz")
    assert estado == config.NO_APTO


def test_umbral_apto_es_mas_exigente_que_el_otro():
    assert config.ML_APTO_MIN_PROB > config.ML_NO_APTO_MIN_PROB


def test_baja_confianza_siempre_es_revisar():
    modelo = ModeloFalso([config.APTO, config.NO_APTO, config.VEGETARIANO],
                         [0.34, 0.33, 0.33])
    estado, _ = classify_ml.predecir(modelo, "Producto ambiguo")
    assert estado == config.REVISAR


def test_texto_junta_nombre_y_marca():
    assert classify_ml._texto("Leche", "Ades") == "leche ades"
    assert classify_ml._texto("Leche", None) == "leche"


def test_no_entrena_con_pocos_ejemplos(tmp_path):
    import db as _db

    conn = _db.connect(tmp_path / "vacia.db")
    _db.init_db(conn)
    rep = classify_ml.entrenar(conn)
    conn.close()
    assert "error" in rep
