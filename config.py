"""Configuración central del pipeline.

Todo lo que se ajusta con la operación (frecuencias, TTL, umbrales, endpoints)
vive acá y se puede sobreescribir por variables de entorno / .env.
"""
from __future__ import annotations

import os
from pathlib import Path

try:  # opcional: si no está python-dotenv, se usan las env vars del sistema
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass


def _env(name: str, default: str) -> str:
    return os.getenv(name, default)


def _env_int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def _env_float(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)))


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(_env("BUSCAVEGAN_DATA_DIR", str(BASE_DIR / "data")))
RAW_DIR = DATA_DIR / "raw"
MODELS_DIR = Path(_env("BUSCAVEGAN_MODELS_DIR", str(BASE_DIR / "models")))

# SQLite: una sola base con catálogo, cache de OFF y la tabla final.
DB_PATH = Path(_env("BUSCAVEGAN_DB", str(DATA_DIR / "buscavegan.db")))

# --- Open Food Facts -------------------------------------------------------
OFF_BASE_URL = _env("OFF_BASE_URL", "https://world.openfoodfacts.org")
# OFF exige un User-Agent descriptivo y propio para lecturas anónimas.
OFF_USER_AGENT = _env(
    "OFF_USER_AGENT",
    "buscavegan/0.1 (https://github.com/Lightb0y/buscavegan)",
)
OFF_FIELDS = [
    "code",
    "product_name",
    "brands",
    "ingredients_text",
    "ingredients_analysis_tags",
    "labels_tags",
    "categories_tags",
    "image_front_small_url",
]
# Rate limit: OFF responde 503 al excederse. Un request por segundo es conservador.
OFF_SLEEP_SECONDS = _env_float("OFF_SLEEP_SECONDS", 1.0)
OFF_MAX_RETRIES = _env_int("OFF_MAX_RETRIES", 4)
OFF_BACKOFF_BASE = _env_float("OFF_BACKOFF_BASE", 2.0)
OFF_TIMEOUT = _env_float("OFF_TIMEOUT", 15.0)
# TTL del cache: pasado ese plazo el EAN se vuelve a consultar.
OFF_CACHE_TTL_DAYS = _env_int("OFF_CACHE_TTL_DAYS", 60)

# --- Sprint 0 --------------------------------------------------------------
SAMPLE_SIZE = _env_int("BUSCAVEGAN_SAMPLE_SIZE", 500)
MATCH_RATE_ML_OK = 0.25   # por encima: el training set alcanza para Capa 3
MATCH_RATE_ML_WEAK = 0.10  # por debajo: la heurística es el caballo de batalla

# --- Capa 3 / Capa 4 -------------------------------------------------------
ML_MIN_TRAIN_SAMPLES = _env_int("ML_MIN_TRAIN_SAMPLES", 200)
ML_AMBIGUOUS_LOW = _env_float("ML_AMBIGUOUS_LOW", 0.40)
ML_AMBIGUOUS_HIGH = _env_float("ML_AMBIGUOUS_HIGH", 0.60)
# Por la regla de seguridad, para marcar `apto` por ML pedimos más certeza
# que para marcar `no_apto`.
ML_APTO_MIN_PROB = _env_float("ML_APTO_MIN_PROB", 0.85)
ML_NO_APTO_MIN_PROB = _env_float("ML_NO_APTO_MIN_PROB", 0.65)

# --- Estados ---------------------------------------------------------------
APTO = "apto"
VEGETARIANO = "vegetariano"
NO_APTO = "no_apto"
REVISAR = "revisar"

for _d in (DATA_DIR, RAW_DIR, MODELS_DIR):
    _d.mkdir(parents=True, exist_ok=True)
