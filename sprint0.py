"""SPRINT 0 — medir la evidencia disponible antes de construir las capas caras.

Qué se mide y por qué cambió respecto de SPEC.md §3
---------------------------------------------------
El SPEC planteaba medir el **match rate SEPA → OFF**: cuántos EANs del catálogo
argentino tienen ficha en Open Food Facts. Esa pregunta tenía sentido mientras
SEPA era la fuente de catálogo; al pasar a OFF como catálogo (SEPA no publica
ingredientes y su portal bloquea la descarga automatizada), el match rate da
100% por construcción y deja de informar nada.

La pregunta equivalente, y la que realmente decide qué construir, es:

    de los productos argentinos que tenemos, ¿cuántos traen evidencia
    suficiente para clasificarlos, y cuántos quedan en `revisar`?

Se conservan los umbrales de SPEC.md §3, aplicados a la cobertura de
ingredientes, porque cumplen la misma función: decidir si hay training set para
el clasificador de la Capa 3 o si la heurística tiene que ser el caballo de
batalla.

    python sprint0.py                 # sobre todo el catálogo
    python sprint0.py --sample 500    # sobre una muestra
"""
from __future__ import annotations

import argparse
import json
import random
from collections import Counter

import categorias
import config
import db
import ingest_anmat

TAGS_RESUELVEN = {"en:vegan", "en:non-vegan", "en:vegetarian", "en:non-vegetarian"}


def cargar_muestra(conn, n: int | None, seed: int = 42) -> list[dict]:
    filas = conn.execute(
        "SELECT c.ean, c.nombre, c.marca, o.payload FROM catalogo c"
        " LEFT JOIN off_cache o ON o.ean = c.ean AND o.found = 1").fetchall()
    datos = [{"ean": f["ean"], "nombre": f["nombre"], "marca": f["marca"],
              "off": json.loads(f["payload"]) if f["payload"] else {}}
             for f in filas]
    if n and n < len(datos):
        random.Random(seed).shuffle(datos)
        datos = datos[:n]
    return datos


def medir(conn, datos: list[dict]) -> dict:
    total = len(datos) or 1
    anmat_idx = ingest_anmat.indexar(ingest_anmat.cargar(conn))

    # Import local: build_db es quien orquesta las capas, y traerlo arriba
    # crearía un ciclo cuando build_db quiera reportar con este módulo.
    import build_db

    con_texto = con_tags = con_analysis = con_label = certificados = 0
    estados: Counter[str] = Counter()
    fuentes: Counter[str] = Counter()

    for d in datos:
        off = d["off"]
        if (off.get("ingredients_text") or "").strip():
            con_texto += 1
        if off.get("ingredients_tags"):
            con_tags += 1
        if TAGS_RESUELVEN & set(off.get("ingredients_analysis_tags") or []):
            con_analysis += 1
        if "en:vegan" in (off.get("labels_tags") or []):
            con_label += 1
        if anmat_idx and ingest_anmat.match_anmat(d["nombre"], d["marca"],
                                                  anmat_idx):
            certificados += 1

        categoria = categorias.normalizar(off.get("categories_tags"))
        dec = build_db.decidir(d["nombre"], d["marca"], categoria, off, anmat_idx)
        estados[dec.estado] += 1
        fuentes[dec.fuente] += 1

    con_ingredientes = sum(
        1 for d in datos
        if (d["off"].get("ingredients_text") or "").strip()
        or d["off"].get("ingredients_tags"))

    def pct(x: int) -> float:
        return round(100 * x / total, 2)

    resueltos = total - estados.get(config.REVISAR, 0)
    return {
        "muestra": len(datos),
        "con_ingredientes": con_ingredientes,
        "cobertura_ingredientes_pct": pct(con_ingredientes),
        "con_texto_ingredientes": con_texto,
        "con_taxonomia": con_tags,
        "con_analysis_off_resuelto": con_analysis,
        "con_label_vegan": con_label,
        "certificados_anmat": certificados,
        "resueltos": resueltos,
        "tasa_resolucion_pct": pct(resueltos),
        "estados": dict(estados),
        "fuentes": dict(fuentes),
    }


def interpretar(rep: dict) -> list[str]:
    """Lee los números contra los umbrales de SPEC.md §3."""
    cob = rep["cobertura_ingredientes_pct"]
    notas = []

    if cob > config.MATCH_RATE_ML_OK * 100:
        notas.append(
            f"Cobertura de ingredientes {cob}% (> {config.MATCH_RATE_ML_OK:.0%}): "
            "alcanza para entrenar la Capa 3. El training set sale de los "
            "productos ya resueltos por ingredientes y certificación.")
    elif cob < config.MATCH_RATE_ML_WEAK * 100:
        notas.append(
            f"Cobertura de ingredientes {cob}% (< {config.MATCH_RATE_ML_WEAK:.0%}): "
            "la heurística de nombre es el caballo de batalla; el ML no tiene "
            "de dónde aprender.")
    else:
        notas.append(
            f"Cobertura de ingredientes {cob}%: el ML es viable pero con poco "
            "dato. Priorizar heurística y reentrenar cuando OFF gane cobertura.")

    revisar = rep["estados"].get(config.REVISAR, 0)
    notas.append(
        f"Quedan {revisar} productos en `revisar` "
        f"({100 * revisar / (rep['muestra'] or 1):.1f}%). Es el techo que la "
        "Capa 3 puede intentar bajar, y el piso de honestidad de la app: se "
        "muestran, no se esconden.")

    if rep["certificados_anmat"]:
        notas.append(
            f"La Capa 0 (ANMAT) cubre {rep['certificados_anmat']} productos. "
            "Baja como se esperaba, pero es la única evidencia no inferida.")
    return notas


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=int, default=None,
                        help="tamaño de muestra (por defecto, todo el catálogo)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--json", dest="as_json", action="store_true")
    args = parser.parse_args(argv)

    conn = db.connect()
    db.init_db(conn)
    try:
        datos = cargar_muestra(conn, args.sample, args.seed)
        if not datos:
            print("El catálogo está vacío. Corré ingest_off_dump.py primero.")
            return 1
        rep = medir(conn, datos)
    finally:
        conn.close()

    rep["interpretacion"] = interpretar(rep)
    salida = config.DATA_DIR / "sprint0_report.json"
    salida.write_text(json.dumps(rep, ensure_ascii=False, indent=2),
                      encoding="utf-8")

    if args.as_json:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return 0

    n = rep["muestra"]
    print(f"\n=== SPRINT 0 — {n} productos argentinos ===\n")
    print(f"  Con ingredientes (texto o taxonomía) {rep['con_ingredientes']:6}"
          f"  ({rep['cobertura_ingredientes_pct']:5}%)")
    print(f"    · texto de ingredientes            {rep['con_texto_ingredientes']:6}")
    print(f"    · taxonomía de OFF                 {rep['con_taxonomia']:6}")
    print(f"  Con análisis de OFF resuelto         {rep['con_analysis_off_resuelto']:6}")
    print(f"  Declarados vegan por el fabricante   {rep['con_label_vegan']:6}")
    print(f"  Certificados por ANMAT (Capa 0)      {rep['certificados_anmat']:6}")
    print(f"\n  Clasificados                         {rep['resueltos']:6}"
          f"  ({rep['tasa_resolucion_pct']:5}%)")

    print("\nPor estado:")
    for estado, k in sorted(rep["estados"].items(), key=lambda x: -x[1]):
        print(f"  {estado:12} {k:6}  ({100 * k / n:5.1f}%)")
    print("\nPor fuente de la decisión:")
    for fuente, k in sorted(rep["fuentes"].items(), key=lambda x: -x[1]):
        print(f"  {fuente:22} {k:6}  ({100 * k / n:5.1f}%)")

    print("\nLectura:")
    for nota in rep["interpretacion"]:
        print(f"  · {nota}")
    print(f"\nReporte guardado en {salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
