"""Consolida todas las capas en la tabla final `productos` (+ índice FTS5).

Orden de decisión, de más a menos confiable:

  0. `certificacion_oficial` — figura en el registro de ANMAT con atributo
     vegano autorizado (Art. 229 CAA). Es un acto administrativo, no una
     inferencia: manda sobre todo lo demás.
  1. `off_label`     — el fabricante declaró "vegano" en el packaging.
  2. `ingredientes`  — nuestro analizador de la lista de ingredientes.
  3. `off_analysis`  — el análisis propio de Open Food Facts.
  4. `heuristica`    — Capa 2: nombre + marca + categoría.
  5. `revisar`       — no alcanzó la evidencia.

Cuando 2 y 3 se pronuncian y **no coinciden**, gana el veredicto más
conservador (el peor estado), nunca el más favorable: la regla de seguridad de
SPEC.md §4 pesa más que la ambición de cobertura.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter

import categorias
import classify_ingredients as ci
import classify_rules as cr
import config
import db
import ingest_anmat

SEVERIDAD = {config.APTO: 0, config.VEGETARIANO: 1, config.NO_APTO: 2}


def _peor(a: str, b: str) -> str:
    return a if SEVERIDAD[a] >= SEVERIDAD[b] else b


def decidir(nombre: str, marca: str | None, categoria: str | None,
            off: dict | None, anmat_idx: dict | None = None) -> cr.Decision:
    """Aplica las capas en orden y devuelve la decisión final del producto."""
    off = off or {}

    # 0. Certificación oficial de ANMAT (la evidencia más fuerte que existe).
    if anmat_idx:
        oficial = ingest_anmat.match_anmat(nombre, marca, anmat_idx)
        if oficial:
            return cr.Decision(
                config.APTO, ingest_anmat.FUENTE_CERTIFICACION,
                f"Registro oficial de ANMAT con atributo vegano "
                f"(RNPA {oficial['rnpa']})")

    # 1. Declaración del fabricante.
    if "en:vegan" in (off.get("labels_tags") or []):
        return cr.Decision(config.APTO, cr.FUENTE_OFF_LABEL,
                           "Declarado vegano por el fabricante")

    # 2. Ingredientes (señal principal): texto libre si lo hay, si no la
    #    taxonomía normalizada de OFF.
    ing = ci.analyze_product(off)

    # 3. Análisis propio de OFF.
    off_dec = cr.classify_off(off if off else None)

    if ing.resuelto and off_dec.resuelto:
        if ing.estado == off_dec.estado:
            return cr.Decision(
                ing.estado, ci.FUENTE_INGREDIENTES,
                f"{ing.motivo}. Coincide con el análisis de Open Food Facts.")
        # Discrepan. Regla general: gana el criterio más restrictivo.
        #
        # Excepción acotada: distinguir `vegetariano` de `no_apto` no protege a
        # nadie que busque vegano (ninguno de los dos lo es), y ahí nuestro
        # analizador sabe más, porque identificó el ingrediente concreto. Si OFF
        # además no se pronunció sobre el estado vegetariano, mantenemos el
        # nuestro en vez de degradarlo a `no_apto` y perder la información.
        tags = set(off.get("ingredients_analysis_tags") or [])
        off_sin_veg = not ({"en:vegetarian", "en:non-vegetarian"} & tags)
        if (ing.estado == config.VEGETARIANO
                and off_dec.estado == config.NO_APTO and off_sin_veg):
            return cr.Decision(
                config.VEGETARIANO, ci.FUENTE_INGREDIENTES,
                f"{ing.motivo}. Open Food Facts coincide en que no es vegano, "
                f"pero no se pronuncia sobre el estado vegetariano.")

        estado = _peor(ing.estado, off_dec.estado)
        return cr.Decision(
            estado, ci.FUENTE_INGREDIENTES,
            f"{ing.motivo}. Open Food Facts dice «{off_dec.estado}»; ante la "
            f"discrepancia se toma el criterio más restrictivo.")

    if ing.resuelto:
        return cr.Decision(ing.estado, ci.FUENTE_INGREDIENTES, ing.motivo)
    if off_dec.resuelto:
        return off_dec

    # 4. Heurística de nombre, para los que no publican ingredientes.
    heur = cr.classify_name(nombre, marca, categoria)
    if heur.resuelto:
        return heur

    # 5. Sin evidencia suficiente.
    motivo = ing.motivo if ing.n_ingredientes else heur.motivo
    return cr.Decision(config.REVISAR, cr.FUENTE_SIN_DATOS, motivo)


def build(conn, verbose: bool = True) -> dict:
    db.init_db(conn)
    anmat_idx = ingest_anmat.indexar(ingest_anmat.cargar(conn))
    if verbose and not anmat_idx:
        print("Aviso: el registro de ANMAT esta vacio. Corre ingest_anmat.py "
              "para habilitar la Capa 0.")
    filas = conn.execute(
        "SELECT c.ean, c.nombre, c.marca, c.precio_ref, o.payload"
        " FROM catalogo c LEFT JOIN off_cache o"
        " ON o.ean = c.ean AND o.found = 1"
    ).fetchall()

    conn.execute("DELETE FROM productos")
    conn.execute("DELETE FROM revision_pendiente")

    estados: Counter[str] = Counter()
    fuentes: Counter[str] = Counter()
    ahora = db.now_iso()

    for f in filas:
        off = json.loads(f["payload"]) if f["payload"] else {}
        categoria = categorias.normalizar(off.get("categories_tags"))
        d = decidir(f["nombre"], f["marca"], categoria, off, anmat_idx)

        conn.execute(
            "INSERT OR REPLACE INTO productos (ean, nombre, marca, categoria,"
            " estado, fuente_decision, confianza, ingredients_text, imagen_url,"
            " precio_ref, actualizado, motivo)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (f["ean"], f["nombre"], f["marca"], categoria, d.estado, d.fuente,
             d.confianza, off.get("ingredients_text"),
             off.get("image_front_small_url"), f["precio_ref"], ahora, d.motivo),
        )
        estados[d.estado] += 1
        fuentes[d.fuente] += 1

        if d.estado == config.REVISAR:
            conn.execute(
                "INSERT OR REPLACE INTO revision_pendiente"
                " (ean, nombre, marca, motivo, confianza, creado)"
                " VALUES (?,?,?,?,?,?)",
                (f["ean"], f["nombre"], f["marca"], d.motivo, d.confianza, ahora),
            )

    if db.has_fts5(conn):
        conn.execute("INSERT INTO productos_fts(productos_fts) VALUES('rebuild')")
    conn.commit()

    total = sum(estados.values())
    return {"total": total, "estados": dict(estados), "fuentes": dict(fuentes)}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", dest="as_json", action="store_true")
    args = parser.parse_args(argv)

    conn = db.connect()
    try:
        stats = build(conn)
    finally:
        conn.close()

    if args.as_json:
        print(json.dumps(stats, ensure_ascii=False, indent=2))
        return 0

    total = stats["total"] or 1
    print(f"\n=== productos: {stats['total']} ===")
    print("\nPor estado:")
    for estado, n in sorted(stats["estados"].items(), key=lambda x: -x[1]):
        print(f"  {estado:12} {n:6}  ({n / total:5.1%})")
    print("\nPor fuente de la decisión:")
    for fuente, n in sorted(stats["fuentes"].items(), key=lambda x: -x[1]):
        print(f"  {fuente:14} {n:6}  ({n / total:5.1%})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
