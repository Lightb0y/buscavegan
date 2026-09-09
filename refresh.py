"""Orquestador del pipeline completo, pensado para cron o GitHub Actions.

    python refresh.py                    # refresco normal
    python refresh.py --completo         # incluye el dump de OFF (lento)
    python refresh.py --sin-modelo       # sin reentrenar la Capa 3
    python refresh.py --sin-gondola      # sin tocar los supermercados

Diseño incremental
------------------
Lo caro es traer datos, no clasificar. Por eso el refresco normal usa la API
rápida de OFF (un minuto) y solo el modo `--completo` baja el dump entero, que
es lo que conviene correr semanal o mensualmente. Todo lo demás —las cinco
capas, el índice FTS5, el modelo— es cómputo local sobre la base que ya está.

El registro de ANMAT se re-descarga siempre: son 668 filas en un request.

Las dos velocidades de los supermercados
----------------------------------------
El dato de góndola son dos cosas distintas y no cuestan lo mismo:

- **El catálogo** (qué EAN se vende hoy en cada cadena) obliga a recorrer el
  árbol de categorías entero de las cinco cadenas. Es caro, cambia despacio, y
  por eso va solo en `--completo` (mensual).
- **Las fichas** (la lista de ingredientes del envase, que es la mejor
  evidencia que tiene el proyecto) se piden de a un EAN y el proceso es
  reanudable. Va en cada corrida, con un presupuesto acotado: se lleva un
  pedazo de la cola y deja el resto para la próxima.

Antes esto no corría acá: la cosecha de supermercados se había hecho a mano una
vez, así que casi una cuarta parte de los veredictos del sitio salía de datos
que ya no se actualizaban. Un refresco que no incluye su fuente más fuerte
envejece sin avisar.
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
import ingest_fichas
import ingest_off_ar
import ingest_off_dump
import ingest_vtex
import revision
import sprint0

TOTAL_PASOS = 8


def _paso(titulo: str) -> float:
    print(f"\n{'=' * 62}\n{titulo}\n{'=' * 62}", flush=True)
    return time.time()


def refresh(completo: bool = False, con_modelo: bool = True,
            con_gondola: bool = True, fichas: int | None = None,
            verbose: bool = True) -> dict:
    inicio = datetime.now(timezone.utc)
    resumen: dict = {"inicio": inicio.isoformat(timespec="seconds")}
    fichas = config.FICHAS_POR_CORRIDA if fichas is None else fichas
    conn = db.connect()
    db.init_db(conn)

    try:
        t = _paso(f"1/{TOTAL_PASOS} · Registro oficial de ANMAT (Capa 0)")
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

        t = _paso(f"2/{TOTAL_PASOS} · Catálogo argentino de Open Food Facts")
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

        t = _paso(f"3/{TOTAL_PASOS} · Catálogo de góndola (5 cadenas)")
        if not con_gondola:
            print("  Omitido (--sin-gondola)")
        elif not completo:
            print("  Omitido: el árbol de categorías se recorre entero y "
                  "cambia despacio. Va solo en --completo.")
        else:
            try:
                st = ingest_vtex.ingest(conn, verbose=False)
                resumen["gondola"] = st
                print(f"  {sum(st.values())} EANs confirmados en "
                      f"{len(st)} cadenas ({time.time() - t:.1f}s)")
            except Exception as exc:
                # Las APIs de las cadenas son públicas pero nadie se
                # comprometió a mantenerlas: si una se cae, el pipeline sigue
                # con la última cosecha buena en vez de abortar el refresco.
                resumen["gondola_error"] = str(exc)
                print(f"  Aviso: no se pudo recosechar la góndola ({exc}). "
                      f"Se usa lo que haya en la base.")

        t = _paso(f"4/{TOTAL_PASOS} · Fichas de ingredientes (Vea, Jumbo, Disco)")
        if not con_gondola:
            print("  Omitido (--sin-gondola)")
        elif fichas <= 0:
            print("  Omitido (presupuesto de fichas en 0)")
        else:
            try:
                st = ingest_fichas.ingest(conn, limite=fichas, verbose=False)
                resumen["fichas"] = st
                faltan = len(ingest_fichas.pendientes(conn))
                print(f"  {st['consultados']} fichas consultadas, "
                      f"{st['con_ingredientes']} con lista de ingredientes, "
                      f"{st['con_sello_vegano']} con sello vegano "
                      f"({time.time() - t:.1f}s)")
                print(f"  Quedan {faltan} en la cola para las próximas corridas.")
            except Exception as exc:
                resumen["fichas_error"] = str(exc)
                print(f"  Aviso: no se pudieron pedir fichas ({exc}). "
                      f"Se usa lo que haya en la base.")

        t = _paso(f"5/{TOTAL_PASOS} · Correcciones humanas versionadas")
        st = revision.importar_directorio(conn)
        resumen["correcciones"] = st
        if st["archivos"]:
            print(f"  {st['aplicadas']} correcciones de {st['archivos']} "
                  f"archivo(s) en {config.CORRECCIONES_DIR.name}/ "
                  f"({time.time() - t:.1f}s)")
            if st["invalidas"]:
                print(f"  {len(st['invalidas'])} fila(s) con estado inválido: "
                      f"{', '.join(st['invalidas'][:3])}")
        else:
            print(f"  Sin archivos en {config.CORRECCIONES_DIR.name}/: "
                  f"se usan las correcciones que ya estén en la base.")

        t = _paso(f"6/{TOTAL_PASOS} · Clasificación (Capas 0 a 2)")
        st = build_db.build(conn, verbose=False)
        resumen["clasificacion"] = st
        print(f"  {st['total']} productos clasificados ({time.time() - t:.1f}s)")
        for estado, n in sorted(st["estados"].items(), key=lambda x: -x[1]):
            print(f"    {estado:12} {n:6}")

        t = _paso(f"7/{TOTAL_PASOS} · Clasificador automático (Capa 3)")
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

        t = _paso(f"8/{TOTAL_PASOS} · Reporte de cobertura")
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
                        help="bajar el dump entero de OFF en vez de la API, "
                             "y recosechar el catálogo de góndola")
    parser.add_argument("--sin-modelo", action="store_true",
                        help="no reentrenar ni aplicar la Capa 3")
    parser.add_argument("--sin-gondola", action="store_true",
                        help="no consultar a los supermercados en esta corrida")
    parser.add_argument("--fichas", type=int, default=None,
                        metavar="N",
                        help=f"cuántas fichas pedir (por defecto "
                             f"{config.FICHAS_POR_CORRIDA}; 0 para ninguna)")
    args = parser.parse_args(argv)
    refresh(completo=args.completo, con_modelo=not args.sin_modelo,
            con_gondola=not args.sin_gondola, fichas=args.fichas)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
