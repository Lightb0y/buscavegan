"""Ficha nutricional de las cadenas de Cencosud (Vea, Jumbo y Disco).

Por qué existe
--------------
El veredicto por lista de ingredientes es mucho mejor que el veredicto por
nombre: el nombre comercial omite y a veces miente, mientras que la lista es
la declaración legal de lo que el producto tiene adentro. Pero 6.365 de los
10.395 productos del catálogo no tienen ingredientes cargados en Open Food
Facts, y por eso miles quedan en `revisar` o se resuelven adivinando por el
nombre.

Vea, Jumbo y Disco publican en su API de VTEX la ficha completa del producto:

- `Ingredientes` — la lista real, tal como está en el envase.
- `Trazas` — en un campo **aparte**, que es justo la distinción que nos
  importa: "puede contener leche" no es lo mismo que "contiene leche".
- `Sellos` — certificaciones, entre las que hay un `vegan` y un `vegetarian`
  explícitos.

Carrefour y Día quedan afuera: se verificó que su VTEX no expone estos campos
(Carrefour solo trae una descripción comercial, Día ni eso).

Cómo se consulta
----------------
No hace falta recosechar el catálogo entero: VTEX permite filtrar por EAN
(`fq=alternateIds_Ean:<ean>`), así que se piden de a uno solo los productos
que ya sabemos que están en esas cadenas y a los que les falta información.

Se guarda también el resultado vacío (una ficha sin ingredientes) para no
volver a preguntar por lo mismo en la próxima corrida: el proceso es
reanudable y se puede cortar en cualquier momento.

Todo lo pedido se versiona en `COSECHA/fichas.ndjson` (ver `exportar`): cada
corrida arranca cargando ese archivo y termina reescribiéndolo, así que lo
cosechado en una máquina sigue en la próxima, sea cual sea.

    python ingest_fichas.py                     # todo lo que falte
    python ingest_fichas.py --limite 200        # prueba corta
    python ingest_fichas.py --solo-sincronizar  # sin consultar: base <-> archivo
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import time
from pathlib import Path

import requests

import config
import db
import relevancia
from ingest_vtex import CADENAS, NOMBRE_LEGIBLE

# Solo las cadenas de Cencosud publican la ficha.
CADENAS_CON_FICHA = ("disco", "jumbo", "vea")

CAMPO_INGREDIENTES = "Ingredientes"
CAMPO_TRAZAS = "Trazas"
CAMPO_SELLOS = "Sellos"

SELLO_VEGANO = "vegan"
SELLO_VEGETARIANO = "vegetarian"

# VTEX devuelve estos campos como una lista con UN string adentro, y ese string
# trae los ítems entrecomillados: ["'harina de trigo', 'sal'"].
_ENTRECOMILLADO = re.compile(r"'([^']*)'")


def texto_de_campo(celdas) -> str | None:
    """Convierte ["'harina de trigo', 'sal'"] en "harina de trigo, sal"."""
    if not celdas:
        return None
    crudo = " ".join(str(c) for c in celdas).strip()
    if not crudo:
        return None
    items = [t.strip() for t in _ENTRECOMILLADO.findall(crudo) if t.strip()]
    if items:
        return ", ".join(items)
    # Algunos productos traen el texto plano, sin comillas.
    return crudo or None


def codigos_de_sellos(celdas) -> str | None:
    """Extrae los `certification_type_code` de la estructura de sellos.

    Vienen como el `repr` de una lista de diccionarios de Python, no como
    JSON, así que hay que leerlos con `ast.literal_eval` y no con `json.loads`.
    """
    codigos: set[str] = set()
    for celda in celdas or []:
        try:
            sellos = ast.literal_eval(str(celda))
        except (ValueError, SyntaxError):
            continue
        if not isinstance(sellos, list):
            continue
        for sello in sellos:
            if isinstance(sello, dict) and sello.get("certification_type_code"):
                codigos.add(str(sello["certification_type_code"]))
    return ",".join(sorted(codigos)) or None


def extraer_ficha(producto: dict) -> dict:
    return {
        "ingredientes": texto_de_campo(producto.get(CAMPO_INGREDIENTES)),
        "trazas": texto_de_campo(producto.get(CAMPO_TRAZAS)),
        "sellos": codigos_de_sellos(producto.get(CAMPO_SELLOS)),
    }


# Resultados posibles de una consulta, que NO son lo mismo:
RESPONDIO = "respondio"      # la cadena contestó; la ficha es lo que contestó
NO_LA_TIENE = "no_la_tiene"  # contestó que ese producto no está en su catálogo
NO_CONTESTO = "no_contesto"  # no se pudo preguntar: timeout, corte, 503...


def pedir_ficha(session: requests.Session, base_url: str,
                ean: str) -> tuple[str, dict | None]:
    """Consulta la ficha y devuelve (resultado, ficha).

    La distinción entre los tres resultados es lo que hace segura la cosecha
    grande. Guardar la ficha vacía es deliberado —así la próxima corrida no
    vuelve a preguntar por algo que ya sabemos que no está— pero eso vale
    **solo si la cadena contestó**. Si no se pudo preguntar, anotar "no tiene
    ficha" es escribir una conclusión que nunca se sacó.

    Con 2.608 consultas la diferencia no se notaba. Con 85.000 repartidas en
    una corrida de horas, un corte de red de un minuto dejaría cientos de
    productos marcados para siempre como "ya consultado, no tiene nada", sin
    ninguna forma de distinguirlos después de los que de verdad no la tienen.
    """
    try:
        r = session.get(f"{base_url}/api/catalog_system/pub/products/search",
                        params={"fq": f"alternateIds_Ean:{ean}"},
                        timeout=config.VTEX_TIMEOUT)
    except requests.RequestException:
        return NO_CONTESTO, None
    if r.status_code in (429, 500, 502, 503, 504):
        return NO_CONTESTO, None
    if r.status_code not in (200, 206):
        # Un 404 o un 400 sí son una respuesta: ese EAN no está acá.
        return NO_LA_TIENE, None
    try:
        productos = r.json()
    except ValueError:
        return NO_CONTESTO, None
    if not productos:
        return NO_LA_TIENE, None
    return RESPONDIO, extraer_ficha(productos[0])


def pendientes(conn, limite: int | None = None) -> list[tuple[str, str]]:
    """(ean, cadena) de lo que conviene consultar y todavía no se consultó.

    Hasta la cosecha grande esta consulta arrancaba `FROM productos`, y por eso
    solo podía pedir la ficha de un producto **que ya estaba clasificado**: los
    7.381 que OFF conocía. Los otros 96.247 códigos que las cadenas publican y
    OFF nunca vio eran invisibles para ella. El síntoma era que la cola
    devolvía 26 productos cuando había 87.078 fichas sin pedir; el diagnóstico
    de "hay que subir el límite" era falso, porque el techo lo ponía el JOIN y
    no el presupuesto.

    Ahora arranca `FROM vtex_catalogo`, que es donde están todos los códigos
    relevados, y ordena la cola por cuánto aporta cada ficha:

    0. **Producto del sitio al que le falta evidencia** — sin ingredientes, o
       con un veredicto adivinado por el nombre. Cada ficha acá mejora algo
       que ya se está mostrando: es lo más valioso por consulta.
    1. **Producto que todavía no está en el sitio.** Es el grueso de la
       cosecha y lo que hace crecer el catálogo.
    2. **Producto del sitio que ya tiene evidencia propia.** La ficha igual
       sirve —son dos lecturas de la misma etiqueta, y `build_db` se queda con
       la más restrictiva cuando discrepan— pero es lo que menos urge.
    3. **Código de circulación restringida** (prefijo GS1 2): los que imprime
       el propio supermercado para lo que pesa o fracciona —fiambre al corte,
       verdura suelta—. No tienen fabricante y casi nunca ficha: medido en la
       cosecha, **20 con ingredientes de 18.366 consultados (0,1%)**, contra
       el 37% de los códigos de fabricante. Ordenada solo por EAN, la cola los
       ponía primero y se llevaron dos tercios de las consultas. No se
       descartan —es la regla del módulo: nada se excluye por intuición—, se
       piden al final.

    Los nombres que `relevancia` ya sabe descartar (cosmética, alfabeto que no
    corresponde) se filtran **antes** de gastar una consulta en ellos.
    """
    marcadores = ",".join("?" * len(CADENAS_CON_FICHA))
    sql = f"""
        SELECT v.ean,
               MIN(v.cadena) AS cadena,
               MIN(v.nombre) AS nombre,
               MIN(CASE
                   WHEN substr(v.ean, 1, 1) = '2' THEN 3
                   WHEN p.ean IS NULL THEN 1
                   WHEN p.ingredients_text IS NULL OR p.ingredients_text = ''
                        OR p.fuente_decision IN ('heuristica', 'ml', 'sin_datos')
                   THEN 0
                   ELSE 2
               END) AS prioridad
        FROM vtex_catalogo v
        LEFT JOIN vtex_ficha f ON f.ean = v.ean
        LEFT JOIN productos p ON p.ean = v.ean
        WHERE v.cadena IN ({marcadores})
          AND f.ean IS NULL
        GROUP BY v.ean
        ORDER BY prioridad, v.ean
    """
    cola: list[tuple[str, str]] = []
    for r in conn.execute(sql, CADENAS_CON_FICHA):
        if relevancia.motivo_exclusion(r["nombre"], r["ean"]):
            continue
        cola.append((r["ean"], r["cadena"]))
        if limite and len(cola) >= limite:
            break
    return cola


# Si la cadena deja de contestar tantas veces seguidas, se corta la corrida.
# No es una pérdida: la cosecha es reanudable y lo ya guardado queda. Seguir
# sería quemar el resto de la cola contra un servicio que no está.
MAX_FALLOS_SEGUIDOS = 25


def ingest(conn, limite: int | None = None, sleep: float | None = None,
           verbose: bool = True) -> dict[str, int]:
    sleep = config.VTEX_SLEEP_SECONDS if sleep is None else sleep
    session = requests.Session()
    session.headers.update({"User-Agent": config.OFF_USER_AGENT})

    cola = pendientes(conn, limite)
    # `flush` en cada aviso: una corrida de horas se manda a un log, y con
    # stdout redirigido Python guarda todo en un buffer hasta el final. Si el
    # proceso muere antes —y en horas, algo lo mata— el log queda vacío aunque
    # se hayan guardado 27.000 fichas. Pasó.
    if verbose:
        print(f"{len(cola)} productos a consultar", flush=True)

    stats = {"consultados": 0, "con_ingredientes": 0, "con_sello_vegano": 0,
             "sin_ficha": 0, "sin_respuesta": 0, "cortada": 0}
    fallos_seguidos = 0
    arranque = time.time()

    for i, (ean, cadena) in enumerate(cola, 1):
        resultado, ficha = pedir_ficha(session, CADENAS[cadena], ean)

        if resultado == NO_CONTESTO:
            # No se guarda nada: no sabemos si tiene ficha o no, y anotar que
            # no la tiene sería inventar una respuesta que nadie dio. Queda en
            # la cola para la próxima corrida.
            stats["sin_respuesta"] += 1
            fallos_seguidos += 1
            if fallos_seguidos >= MAX_FALLOS_SEGUIDOS:
                stats["cortada"] = 1
                if verbose:
                    print(f"  La cadena dejó de responder ({fallos_seguidos} "
                          f"consultas seguidas sin respuesta). Se corta acá; "
                          f"lo cosechado queda guardado y la próxima corrida "
                          f"sigue donde esta terminó.", flush=True)
                break
            # Un respiro antes de insistir, por si es un límite de consultas.
            time.sleep(min(sleep * 10, 5.0))
            continue

        fallos_seguidos = 0
        stats["consultados"] += 1
        if ficha is None:
            ficha = {"ingredientes": None, "trazas": None, "sellos": None}
            stats["sin_ficha"] += 1
        if ficha["ingredientes"]:
            stats["con_ingredientes"] += 1
        if ficha["sellos"] and SELLO_VEGANO in ficha["sellos"].split(","):
            stats["con_sello_vegano"] += 1

        # Se guarda también la ficha vacía: así la próxima corrida no vuelve a
        # preguntar por un producto que ya sabemos que no la tiene. Solo se
        # llega acá si la cadena contestó (ver `pedir_ficha`).
        conn.execute(
            "INSERT OR REPLACE INTO vtex_ficha"
            " (ean, cadena, ingredientes, trazas, sellos, actualizado)"
            " VALUES (?,?,?,?,?,?)",
            (ean, cadena, ficha["ingredientes"], ficha["trazas"],
             ficha["sellos"], db.now_iso()))
        if i % 25 == 0:
            conn.commit()
        if verbose and i % 250 == 0:
            print(f"  {i}/{len(cola)} — {stats['con_ingredientes']} con "
                  f"ingredientes, {stats['con_sello_vegano']} con sello vegano"
                  f"{_falta(arranque, i, len(cola))}", flush=True)
        time.sleep(sleep)

    conn.commit()
    return stats


def _falta(arranque: float, hechas: int, total: int) -> str:
    """" — faltan ~2 h 15 m", para no mirar a ciegas una corrida de horas."""
    if hechas <= 0:
        return ""
    restantes = (time.time() - arranque) / hechas * (total - hechas)
    if restantes < 90:
        return f" — faltan ~{int(restantes)} s"
    if restantes < 5400:
        return f" — faltan ~{int(restantes / 60)} min"
    return f" — faltan ~{restantes / 3600:.1f} h"


# --- La copia versionada --------------------------------------------------
#
# La base es derivada: en CI se restaura de un cache que vence, y en cualquier
# máquina se puede borrar y rearmar. Eso está bien para lo que es barato de
# recalcular, pero la cosecha completa son horas de consultas. Si viviera solo
# en la base, perder el cache sería rehacerla, y —peor— lo cosechado en una
# máquina no llegaría nunca al refresco de CI, que es el que publica el sitio.
#
# Es el mismo arreglo que ya tienen las correcciones humanas (ver
# `revision.importar_directorio`): el archivo versionado es la copia de
# referencia, y la base se sincroniza con él al empezar y al terminar.

_CAMPOS = ("ean", "cadena", "ingredientes", "trazas", "sellos", "actualizado")


def exportar(conn, ruta: Path | None = None) -> int:
    """Escribe todas las fichas pedidas, vacías incluidas, una por línea.

    Ordenadas por EAN y con las claves siempre en el mismo orden: una corrida
    que pide 1.500 fichas cambia 1.500 líneas y git guarda solo eso (el mismo
    razonamiento que `export_web`). Las vacías también van, porque son la
    mitad del valor: "la cadena contestó que no la tiene" es lo que evita
    volver a preguntar. Los campos nulos no se escriben; en esas fichas serían
    tres `null` por línea.

    Se escribe a un temporal y se renombra al final, para que un corte a mitad
    de camino no deje truncada la copia de referencia.
    """
    ruta = ruta or config.COSECHA_PATH
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_name(ruta.name + ".tmp")
    n = 0
    with temporal.open("w", encoding="utf-8", newline="\n") as fh:
        for fila in conn.execute(
                f"SELECT {', '.join(_CAMPOS)} FROM vtex_ficha ORDER BY ean"):
            datos = {k: v for k, v in zip(_CAMPOS, fila) if v not in (None, "")}
            fh.write(json.dumps(datos, ensure_ascii=False, separators=(",", ":")))
            fh.write("\n")
            n += 1
    temporal.replace(ruta)
    return n


def importar(conn, ruta: Path | None = None) -> dict[str, int]:
    """Carga en la base las fichas de la copia versionada que le falten.

    Una ficha del archivo entra si la base no la tiene, o si la tiene con una
    fecha anterior. Nunca pisa una más nueva: una máquina que cosechó después
    no pierde lo suyo al importar lo de otra, y reimportar lo mismo no cambia
    nada.
    """
    ruta = ruta or config.COSECHA_PATH
    st = {"leidas": 0, "nuevas": 0, "actualizadas": 0}
    if not ruta.is_file():
        return st

    previas = {ean: fecha for ean, fecha in conn.execute(
        "SELECT ean, actualizado FROM vtex_ficha")}
    with ruta.open(encoding="utf-8") as fh:
        for linea in fh:
            if not linea.strip():
                continue
            ficha = json.loads(linea)
            st["leidas"] += 1
            previa = previas.get(ficha["ean"])
            # Las fechas son ISO-8601 en UTC (`db.now_iso`): como texto se
            # ordenan igual que como fecha.
            if previa is not None and previa >= ficha["actualizado"]:
                continue
            conn.execute(
                "INSERT OR REPLACE INTO vtex_ficha"
                f" ({', '.join(_CAMPOS)}) VALUES (?,?,?,?,?,?)",
                tuple(ficha.get(k) for k in _CAMPOS))
            st["nuevas" if previa is None else "actualizadas"] += 1
    conn.commit()
    return st


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limite", type=int, default=None,
                        help="cuántos productos consultar (por defecto, todos)")
    parser.add_argument("--sleep", type=float, default=None)
    parser.add_argument("--solo-sincronizar", action="store_true",
                        help="no consultar a nadie: solo cargar la copia "
                             "versionada en la base y reescribirla")
    args = parser.parse_args(argv)

    conn = db.connect()
    db.init_db(conn)
    stats = None
    try:
        imp = importar(conn)
        if imp["nuevas"] or imp["actualizadas"]:
            print(f"{imp['nuevas']} fichas nuevas y {imp['actualizadas']} "
                  f"actualizadas desde {config.COSECHA_PATH.name}", flush=True)
        # El `finally` interno corre recién después de importar: si el archivo
        # estuviera roto, exportar desde una base que no lo leyó lo pisaría
        # con menos fichas de las que tenía.
        try:
            if not args.solo_sincronizar:
                stats = ingest(conn, args.limite, args.sleep)
        finally:
            # Aunque la corrida se corte —Ctrl+C, un error—, lo cosechado
            # hasta ahí pasa a la copia versionada.
            n = exportar(conn)
            print(f"\n{n} fichas en {config.COSECHA_PATH}", flush=True)
    finally:
        conn.close()

    if stats:
        print(f"\nConsultados        : {stats['consultados']}")
        print(f"Con ingredientes   : {stats['con_ingredientes']}")
        print(f"Con sello vegano   : {stats['con_sello_vegano']}")
        print(f"Sin ficha          : {stats['sin_ficha']}")
        print(f"Sin respuesta      : {stats['sin_respuesta']}"
              f"{' (corrida cortada)' if stats['cortada'] else ''}")
        print(f"\nCadenas con ficha: "
              f"{', '.join(NOMBRE_LEGIBLE[c] for c in CADENAS_CON_FICHA)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
