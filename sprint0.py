"""SPRINT 0 — medir el match rate de Open Food Facts antes de construir el resto.

El riesgo principal del proyecto es que la cobertura de productos argentinos en
OFF sea baja. Este script toma una muestra del catálogo, la enriquece y reporta
qué fracción tiene respuesta útil, con la lectura que corresponde según SPEC.md §3:

    > 25%  -> hay training set para el clasificador ML (Capa 3 fuerte)
    < 10%  -> la heurística (Capa 2) pasa a ser el caballo de batalla

    python sprint0.py --sample 500
"""
from __future__ import annotations

import argparse
import json
import random

import config
import db
import enrich_off


def sample_eans(conn, n: int, seed: int = 42) -> list[str]:
    eans = [r["ean"] for r in conn.execute("SELECT ean FROM catalogo")]
    random.Random(seed).shuffle(eans)
    return eans[:n]


def measure(conn, eans: list[str]) -> dict:
    """Mide, sobre los EANs cacheados, cuántos traen señal utilizable."""
    total = len(eans)
    encontrados = con_analysis = con_label = con_ingredientes = 0

    for ean in eans:
        cached = db.cache_get(conn, ean)
        if not cached or not cached["found"]:
            continue
        encontrados += 1
        p = cached["product"] or {}
        analysis = p.get("ingredients_analysis_tags") or []
        # "útil" = el tag resuelve el estado; los *-status-unknown no cuentan.
        if any(t in ("en:vegan", "en:non-vegan", "en:vegetarian", "en:non-vegetarian")
               for t in analysis):
            con_analysis += 1
        if "en:vegan" in (p.get("labels_tags") or []):
            con_label += 1
        if (p.get("ingredients_text") or "").strip():
            con_ingredientes += 1

    def pct(x: int) -> float:
        return round(100 * x / total, 2) if total else 0.0

    return {
        "muestra": total,
        "encontrados_en_off": encontrados,
        "match_rate_pct": pct(encontrados),
        "con_analysis_resuelto": con_analysis,
        "analysis_rate_pct": pct(con_analysis),
        "con_label_vegan": con_label,
        "con_ingredients_text": con_ingredientes,
        "ingredientes_rate_pct": pct(con_ingredientes),
    }


def interpretar(match_rate: float) -> str:
    if match_rate > config.MATCH_RATE_ML_OK * 100:
        return ("Match rate alto: hay training set suficiente para la Capa 3 (ML). "
                "Seguir con el pipeline completo.")
    if match_rate < config.MATCH_RATE_ML_WEAK * 100:
        return ("Match rate bajo: la Capa 2 (heurística) es el caballo de batalla. "
                "Invertir ahí antes que en el modelo, y esperar mucho `revisar`.")
    return ("Match rate intermedio: el ML es viable pero con poco dato. "
            "Priorizar la heurística y reentrenar a medida que OFF gane cobertura AR.")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=int, default=config.SAMPLE_SIZE)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no-fetch", action="store_true",
                        help="medir solo con lo que ya está en cache")
    parser.add_argument("--json", dest="as_json", action="store_true")
    args = parser.parse_args(argv)

    conn = db.connect()
    db.init_db(conn)
    try:
        eans = sample_eans(conn, args.sample, args.seed)
        if not eans:
            print("El catálogo está vacío. Corré ingest_sepa.py primero.")
            return 1
        if not args.no_fetch:
            stats = enrich_off.enrich(conn, eans)
            print(f"Enriquecimiento: {stats['consultados']} consultados, "
                  f"{stats['cacheados']} desde cache, {stats['errores']} errores")
        report = measure(conn, eans)
    finally:
        conn.close()

    report["interpretacion"] = interpretar(report["match_rate_pct"])
    out = config.DATA_DIR / "sprint0_report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"\n=== SPRINT 0 — muestra de {report['muestra']} EANs ===")
        print(f"Match rate OFF:          {report['match_rate_pct']}% "
              f"({report['encontrados_en_off']})")
        print(f"Con análisis resuelto:   {report['analysis_rate_pct']}% "
              f"({report['con_analysis_resuelto']})")
        print(f"Con label vegan:         {report['con_label_vegan']}")
        print(f"Con ingredientes:        {report['ingredientes_rate_pct']}%")
        print(f"\n{report['interpretacion']}")
        print(f"\nReporte guardado en {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
