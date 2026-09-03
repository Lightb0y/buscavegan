"""Orquestador del pipeline completo, pensado para cron o GitHub Actions.

    python refresh.py                    # refresco normal
    python refresh.py --completo         # incluye el dump de OFF (lento)
    python refresh.py --sin-modelo       # sin reentrenar la Capa 3

Diseño incremental
------------------
Lo caro es traer datos, no clasificar. Por eso el refresco normal usa la API
rápida de OFF (un minuto) y solo el modo `--completo` baja el dump entero, que
es lo que conviene correr semanal o mensualmente. Todo lo demás —las cinco
capas, el índice FTS5, el modelo— es cómputo local sobre la base que ya está.

El registro de ANMAT se re-descarga siempre: son 668 filas en un request.
"""
from __future__ import annotations

import argparse
import time
from datetime import datetime, timezone

import build_db
import classify_ml
import config
import db
import ingest_anmat
import ingest_off_ar
import ingest_off_dump
import sprint0


def _paso(titulo: str) -> float:
    print(f"\n{'=' * 62}\n{titulo}\n{'=' * 62}", flush=True)
    return time.time()


def refresh(completo: bool = False, con_modelo: bool = True,
            verbose: bool = True) -> dict:
    inicio = datetime.now(timezone.utc)
    resumen: dict = {"inicio": inicio.isoformat(timespec="seconds")}
    conn = db.connect()
    db.init_db(conn)

    try:
        t = _paso("1/5 · Registro oficial de ANMAT (Capa 0)")
        try:
            filas = ingest_anmat.descargar()
            resumen["anmat"] = ingest_anmat.guardar(conn, filas)
            print(f"  {resumen['anmat']} productos certificados "
                  f"({time.time() - t:.1f}s)")
        except Exception as exc:
            # ANMAT es un enriquecimiento: si falla, el pipeline sigue con lo
            # que ya tenga cacheado en la base.
            resumen["anmat_error"] = str(exc)
            print(f"  Aviso: no se pudo actualizar ANMAT ({exc}). "
                  f"Se usa lo que haya en la base.")

        t = _paso("2/5 · Catálogo argentino de Open Food Facts")
        if completo:
            st = ingest_off_dump.ingest(conn)
            resumen["catalogo"] = st["guardados"]
            print(f"  {st['guardados']} productos desde el dump "
                  f"({st['con_texto']} con ingredientes, "
                  f"{time.time() - t:.1f}s)")
        else:
            st = ingest_off_ar.ingest(conn)
            resumen["catalogo"] = st["productos"]
            print(f"  {st['productos']} productos desde la API "
                  f"({time.time() - t:.1f}s)")

        t = _paso("3/5 · Clasificación (Capas 0 a 2)")
        st = build_db.build(conn, verbose=False)
        resumen["clasificacion"] = st
        print(f"  {st['total']} productos clasificados ({time.time() - t:.1f}s)")
        for estado, n in sorted(st["estados"].items(), key=lambda x: -x[1]):
            print(f"    {estado:12} {n:6}")

        t = _paso("4/5 · Clasificador automático (Capa 3)")
        if con_modelo:
            rep = classify_ml.entrenar(conn)
            if "error" in rep:
                print(f"  {rep['error']}")
                resumen["modelo"] = rep
            else:
                acc = rep["metricas"]["accuracy"]
                f1 = rep["metricas"]["macro avg"]["f1-score"]
                print(f"  Entrenado con {rep['entrenamiento']} ejemplos "
                      f"(accuracy {acc:.3f}, F1 macro {f1:.3f})")
                aplicado = classify_ml.aplicar(conn)
                resumen["modelo"] = {"accuracy": acc, "f1_macro": f1, **aplicado}
                print(f"  {aplicado['resueltos']} de {aplicado['evaluados']} "
                      f"productos en `revisar` resueltos por el modelo "
                      f"({time.time() - t:.1f}s)")
        else:
            print("  Omitido (--sin-modelo)")

        t = _paso("5/5 · Reporte de cobertura")
        datos = sprint0.cargar_muestra(conn, None)
        rep = sprint0.medir(conn, datos)
        resumen["cobertura"] = {
            "total": rep["muestra"],
            "con_ingredientes_pct": rep["cobertura_ingredientes_pct"],
            "clasificados_pct": rep["tasa_resolucion_pct"],
        }
        print(f"  {rep['muestra']} productos, "
              f"{rep['cobertura_ingredientes_pct']}% con ingredientes, "
              f"{rep['tasa_resolucion_pct']}% clasificados "
              f"({time.time() - t:.1f}s)")
    finally:
        conn.close()

    duracion = (datetime.now(timezone.utc) - inicio).total_seconds()
    resumen["duracion_segundos"] = round(duracion, 1)
    print(f"\nRefresco completo en {duracion / 60:.1f} min. "
          f"Base: {config.DB_PATH}")
    return resumen


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--completo", action="store_true",
                        help="bajar el dump entero de OFF en vez de la API")
    parser.add_argument("--sin-modelo", action="store_true",
                        help="no reentrenar ni aplicar la Capa 3")
    args = parser.parse_args(argv)
    refresh(completo=args.completo, con_modelo=not args.sin_modelo)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
