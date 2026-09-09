"""Capa 4 — cola de revisión manual y correcciones humanas.

Dos operaciones, pensadas para que una persona pueda mejorar la base sin tocar
código ni SQL:

    python revision.py --exportar          # saca un CSV con lo pendiente
    python revision.py --exportar --riesgo # los `apto` que solo se apoyan en el nombre
    python revision.py --importar fix.csv  # mete las decisiones humanas

El CSV exportado sale ordenado por **impacto**: primero las marcas con más
productos pendientes, porque resolver una marca suele resolver decenas de
productos de una sentada.

Dos colas, no una
-----------------
La cola por defecto son los `revisar`: productos donde el sistema no se animó a
decidir. Es la más larga y la más visible.

Pero no es la más urgente. `--riesgo` saca la otra: los productos que hoy se
muestran como **apto** apoyados únicamente en su nombre comercial —la heurística
o el modelo—, sin haber leído la etiqueta. Son muchos menos y valen más por
cabeza: un `revisar` que debería ser `apto` solo esconde un producto bueno,
mientras que un `apto` que debería ser otra cosa es exactamente el error que
la regla de seguridad existe para evitar. Si hay una tarde para curar, va acá.

Las correcciones humanas se guardan en su propia tabla y **sobreviven al
refresco**: `build_db` las aplica al final de todo, por encima de cualquier
capa automática. Es la única forma de que curar la base no sea trabajo que se
pierde en la siguiente corrida.

Y para que sobrevivan también a perder la base entera, el refresco reimporta en
cada corrida los CSV curados que estén en `CORRECCIONES/` (ver
`importar_directorio`). La base se puede rearmar de cero; esos archivos son la
copia de la que se rearma.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import config
import db

FUENTE_CURADURIA = "curaduria_humana"

SCHEMA = """
CREATE TABLE IF NOT EXISTS correcciones (
    ean       TEXT PRIMARY KEY,
    estado    TEXT NOT NULL,
    motivo    TEXT,
    revisor   TEXT,
    creado    TEXT
);
"""

COLUMNAS = ["ean", "nombre", "marca", "categoria", "estado_actual",
            "motivo_actual", "ingredientes", "estado_corregido", "revisor"]

ESTADOS_VALIDOS = {config.APTO, config.VEGETARIANO, config.NO_APTO,
                   config.REVISAR}


def init(conn) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


# Las dos fuentes que deciden sin leer la etiqueta: reglas sobre el nombre
# comercial y el modelo entrenado sobre nombres. Un `apto` que salga de acá es
# una estimación, no una lectura.
FUENTES_POR_NOMBRE = ("heuristica", "ml")


def exportar(conn, destino: Path, limite: int | None = None,
             riesgo: bool = False) -> int:
    """Escribe el CSV de revisión, priorizando las marcas de mayor impacto.

    Con `riesgo=True` cambia la cola: en vez de lo que quedó sin resolver,
    saca los `apto` que se apoyan solo en el nombre comercial. Ver el docstring
    del módulo para por qué esa cola va primero.
    """
    init(conn)
    if riesgo:
        marcadores = ",".join("?" * len(FUENTES_POR_NOMBRE))
        donde = f"p.estado = ? AND p.fuente_decision IN ({marcadores})"
        params: tuple = (config.APTO, *FUENTES_POR_NOMBRE)
    else:
        donde = "p.estado = ?"
        params = (config.REVISAR,)

    sql = f"""
        SELECT p.ean, p.nombre, p.marca, p.categoria, p.estado, p.motivo,
               p.ingredients_text,
               COUNT(*) OVER (PARTITION BY COALESCE(p.marca, '')) AS peso
        FROM productos p
        WHERE {donde}
        ORDER BY peso DESC, p.marca, p.nombre
    """
    if limite:
        sql += f" LIMIT {int(limite)}"

    filas = conn.execute(sql, params).fetchall()
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(COLUMNAS)
        for f in filas:
            w.writerow([
                f["ean"], f["nombre"], f["marca"] or "", f["categoria"] or "",
                f["estado"], f["motivo"] or "",
                (f["ingredients_text"] or "")[:300],
                "",  # estado_corregido: lo completa la persona
                "",  # revisor
            ])
    return len(filas)


def importar(conn, origen: Path, revisor_default: str = "manual") -> dict:
    """Lee un CSV curado y guarda las decisiones humanas."""
    init(conn)
    stats = {"leidas": 0, "aplicadas": 0, "ignoradas": 0, "invalidas": []}
    ahora = db.now_iso()

    with origen.open(encoding="utf-8-sig", newline="") as fh:
        for fila in csv.DictReader(fh):
            stats["leidas"] += 1
            ean = (fila.get("ean") or "").strip()
            estado = (fila.get("estado_corregido") or "").strip().lower()
            if not ean or not estado:
                stats["ignoradas"] += 1
                continue
            if estado not in ESTADOS_VALIDOS:
                stats["invalidas"].append(f"{ean}: '{estado}'")
                continue
            conn.execute(
                "INSERT OR REPLACE INTO correcciones"
                " (ean, estado, motivo, revisor, creado) VALUES (?,?,?,?,?)",
                (ean, estado,
                 (fila.get("motivo_actual") or "").strip() or None,
                 (fila.get("revisor") or "").strip() or revisor_default,
                 ahora))
            stats["aplicadas"] += 1
    conn.commit()
    return stats


def importar_directorio(conn, carpeta: Path | None = None) -> dict:
    """Reimporta todos los CSV curados de una carpeta, en orden de nombre.

    Es lo que corre el refresco automático. La tabla `correcciones` vive en la
    base, y la base es derivada: en CI se restaura de un cache que puede
    vencer, y en cualquier máquina se puede borrar y rearmar. Si las decisiones
    humanas vivieran solo ahí, una corrida sin cache las perdería todas sin que
    nadie se entere —justo lo contrario de lo que promete la Capa 4—.

    Los CSV versionados son entonces la copia de referencia, y esta función el
    camino de vuelta. Reimportar es barato e idempotente: `importar` hace
    INSERT OR REPLACE por EAN, así que volver a leer lo mismo no duplica nada.
    """
    carpeta = carpeta or config.CORRECCIONES_DIR
    total = {"archivos": 0, "leidas": 0, "aplicadas": 0, "ignoradas": 0,
             "invalidas": []}
    if not carpeta.is_dir():
        return total

    for csv_path in sorted(carpeta.glob("*.csv")):
        st = importar(conn, csv_path)
        total["archivos"] += 1
        for clave in ("leidas", "aplicadas", "ignoradas"):
            total[clave] += st[clave]
        total["invalidas"].extend(f"{csv_path.name} — {x}"
                                  for x in st["invalidas"])
    return total


def aplicar(conn) -> int:
    """Pisa la clasificación automática con las correcciones humanas.

    Se llama al final de `build_db`: una persona que miró la etiqueta sabe más
    que cualquiera de las capas, así que su decisión va por encima de todas.
    """
    init(conn)
    filas = conn.execute(
        "SELECT c.ean, c.estado, c.revisor FROM correcciones c"
        " JOIN productos p ON p.ean = c.ean").fetchall()
    ahora = db.now_iso()

    for f in filas:
        conn.execute(
            "UPDATE productos SET estado = ?, fuente_decision = ?,"
            " confianza = NULL, motivo = ?, actualizado = ? WHERE ean = ?",
            (f["estado"], FUENTE_CURADURIA,
             f"Revisado y corregido a mano por {f['revisor']}", ahora,
             f["ean"]))
        conn.execute("DELETE FROM revision_pendiente WHERE ean = ?", (f["ean"],))
    conn.commit()
    return len(filas)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exportar", action="store_true")
    parser.add_argument("--riesgo", action="store_true",
                        help="exportar los `apto` que solo se apoyan en el "
                             "nombre, en vez de la cola de `revisar`")
    parser.add_argument("--importar", type=Path, metavar="CSV")
    parser.add_argument("--salida", type=Path, default=None)
    parser.add_argument("--limite", type=int, default=None)
    args = parser.parse_args(argv)

    salida = args.salida or config.DATA_DIR / (
        "apto_por_nombre.csv" if args.riesgo else "revision_pendiente.csv")

    conn = db.connect()
    db.init_db(conn)
    try:
        if args.exportar:
            n = exportar(conn, salida, args.limite, riesgo=args.riesgo)
            que = ("productos marcados `apto` solo por su nombre"
                   if args.riesgo else "productos pendientes")
            print(f"{n} {que} exportados a {salida}")
            if args.riesgo:
                print("Cada uno se muestra hoy como apto sin que nadie haya "
                      "leído la etiqueta: es la cola más cara de dejar sin "
                      "revisar.")
            print("Completá la columna `estado_corregido` "
                  f"({', '.join(sorted(ESTADOS_VALIDOS))}) y volvé con "
                  "--importar.")
        elif args.importar:
            if not args.importar.exists():
                print(f"No existe {args.importar}")
                return 1
            st = importar(conn, args.importar)
            n = aplicar(conn)
            print(f"{st['leidas']} filas leídas, {st['aplicadas']} correcciones "
                  f"guardadas, {st['ignoradas']} sin completar.")
            if st["invalidas"]:
                print(f"  {len(st['invalidas'])} con estado inválido: "
                      f"{', '.join(st['invalidas'][:5])}")
            print(f"{n} productos actualizados en la base.")
        else:
            parser.print_help()
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
