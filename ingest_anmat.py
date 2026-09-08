"""Capa 0 — registro oficial de ANMAT de productos con atributo vegano.

Fuente
------
ANMAT/INAL publica los productos que obtuvieron el atributo "vegano" por
trámite regulatorio (Art. 229 del Código Alimentario Argentino). Es la señal de
mayor confianza que existe para el mercado argentino: no es una inferencia
sobre ingredientes, es un acto administrativo.

La página del buscador (`argentina.gob.ar/anmat/.../productos-con-atributo-vegano`)
trae la `<table>` vacía en el HTML: la puebla por JavaScript el componente
"ponchoTable" del tema de gob.ar, que lee una **planilla de Google pública**
cuyo id está en el propio script de la página. Esa planilla es el endpoint real
y se consulta con el API `gviz`, que devuelve JSON.

Limitaciones de la fuente
-------------------------
- **No trae EAN.** El cruce con el catálogo es por marca + nombre, con las
  precauciones de `match_anmat()`.
- Cobertura baja: la certificación es voluntaria y reciente, así que cubre una
  porción chica del mercado. Es un enriquecimiento, no una dependencia.

    python ingest_anmat.py
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata

import requests

import config
import db

SPREADSHEET_ID = "1djonldqe0ayRxGel2OjnoEHy3MrIKEMzIkmmjM7rZqc"
SHEET_NAME = "29 productos atributo vegano"
GVIZ_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq"
FUENTE_CERTIFICACION = "certificacion_oficial"

# Palabras que no aportan a la identidad del producto al comparar nombres.
#
# "untable" es el caso que obligó a sumar la categoría: describe la
# consistencia del producto (se puede untar), no de qué está hecho, y sin
# esto alcanzaba para certificar como vegano un "Queso untable salame" de Día
# —un fiambre untable de verdad— contra un registro de ANMAT que es otra
# cosa: "Producto vegetal a base de aceite de coco... sabor queso blanco...
# Veggie - untable clásico". Ahí "queso" ya quedaba afuera por ser sabor
# (`tokens_de_sabor`), y "untable" era el único token que sostenía el cruce.
STOPWORDS = {
    "de", "del", "la", "el", "los", "las", "con", "sin", "y", "a", "al", "en",
    "para", "por", "sabor", "gr", "grs", "g", "kg", "ml", "cc", "lt", "l",
    "x", "un", "una", "libre", "gluten", "tacc", "apto", "producto",
    "untable",
}


def normalizar(texto: str | None) -> str:
    if not texto:
        return ""
    t = unicodedata.normalize("NFD", str(texto))
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"[^a-z0-9\s]", " ", t.lower())
    return re.sub(r"\s+", " ", t).strip()


def tokens(texto: str | None) -> set[str]:
    return {w for w in normalizar(texto).split()
            if len(w) > 2 and w not in STOPWORDS}


def descargar(session: requests.Session | None = None) -> list[dict]:
    """Baja la planilla oficial y devuelve las filas como diccionarios."""
    session = session or requests.Session()
    session.headers.update({"User-Agent": config.OFF_USER_AGENT})
    r = session.get(GVIZ_URL, params={"tqx": "out:json", "sheet": SHEET_NAME},
                    timeout=config.OFF_TIMEOUT)
    r.raise_for_status()

    # gviz envuelve el JSON en una llamada JS: /*O_o*/ google...setResponse({...});
    m = re.search(r"setResponse\((.*)\);?\s*$", r.text, re.S)
    if not m:
        raise RuntimeError("La planilla de ANMAT no devolvió el JSON esperado")
    tabla = json.loads(m.group(1))["table"]

    filas = []
    for fila in tabla["rows"]:
        celdas = [(c or {}).get("v") for c in fila["c"]]
        celdas += [None] * (4 - len(celdas))
        razon, marca, producto, rnpa = celdas[:4]
        # Las dos primeras filas de la planilla son encabezados.
        if not producto or normalizar(producto) in (
                "identificacion del producto", "identificacion"):
            continue
        filas.append({
            "razon_social": (razon or "").strip() or None,
            "marca": (marca or "").strip() or None,
            "producto": producto.strip(),
            "rnpa": (rnpa or "").strip() or None,
        })
    return filas


def guardar(conn, filas: list[dict]) -> int:
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS anmat_vegano (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        razon_social TEXT,
        marca        TEXT,
        producto     TEXT NOT NULL,
        rnpa         TEXT,
        marca_norm   TEXT,
        producto_norm TEXT,
        actualizado  TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_anmat_marca ON anmat_vegano(marca_norm);
    """)
    conn.execute("DELETE FROM anmat_vegano")
    ahora = db.now_iso()
    for f in filas:
        conn.execute(
            "INSERT INTO anmat_vegano (razon_social, marca, producto, rnpa,"
            " marca_norm, producto_norm, actualizado) VALUES (?,?,?,?,?,?,?)",
            (f["razon_social"], f["marca"], f["producto"], f["rnpa"],
             normalizar(f["marca"]), normalizar(f["producto"]), ahora))
    conn.commit()
    return len(filas)


# Donde termina la cláusula de sabor: la puntuación que abre la frase
# siguiente, o la conjunción que la encadena. Acotarla importa: los nombres de
# ANMAT son "descripción técnica, sabor X - Nombre Comercial", así que cortar
# desde el primer "sabor" hasta el final se comería el nombre comercial, que
# es justo por donde matchean varios productos ("Veggie snacks", "Rallado Veg").
CORTE_DE_CLAUSULA = re.compile(
    r"[,.;:()/\-–—]"
    r"|\b(con|para|libre|sin|adicionad|fortificad|recubiert|relleno)\b",
    re.IGNORECASE)


def tokens_de_sabor(producto: str | None) -> set[str]:
    """Tokens de las cláusulas «sabor X»: nombran lo que el producto imita.

    Un producto certificado "a base de coco **sabor dulce de leche**" no lleva
    leche: `dulce` y `leche` describen a qué sabe, no de qué está hecho. Si
    esos tokens pueden sostener un cruce por sí solos, el registro termina
    certificando el producto equivocado — que es exactamente lo que pasó con
    el dulce de leche de Doña Magdalena, donde `{dulce, leche}` alcanzaba el
    0.67 de solapamiento contra un postre de coco.

    `match_anmat` los sigue contando para el score, pero exige que el cruce se
    apoye además en al menos un token de la composición.
    """
    if not producto:
        return set()
    out: set[str] = set()
    for m in re.finditer(r"\bsabor(?:es)?\b\s*(?:a\s+)?", producto, re.IGNORECASE):
        resto = producto[m.end():]
        corte = CORTE_DE_CLAUSULA.search(resto)
        out |= tokens(resto[:corte.start()] if corte else resto)
    return out


def cargar(conn) -> list[dict]:
    """Lee el registro ya guardado, listo para matchear."""
    try:
        filas = conn.execute(
            "SELECT marca, producto, rnpa, marca_norm, producto_norm"
            " FROM anmat_vegano").fetchall()
    except Exception:
        return []
    return [{"marca": f["marca"], "producto": f["producto"], "rnpa": f["rnpa"],
             "marca_norm": f["marca_norm"],
             "producto_tokens": tokens(f["producto_norm"]),
             # Sobre el nombre crudo, no el normalizado: `normalizar()` borra
             # la puntuación, que es lo que delimita la cláusula de sabor.
             "sabor_tokens": tokens_de_sabor(f["producto"])} for f in filas]


def indexar(registros: list[dict]) -> dict[str, list[dict]]:
    """Agrupa el registro por marca normalizada, que es la clave del cruce."""
    idx: dict[str, list[dict]] = {}
    for r in registros:
        if r["marca_norm"]:
            idx.setdefault(r["marca_norm"], []).append(r)
    return idx


# Solapamiento mínimo de tokens del nombre para aceptar el cruce. No alcanza
# por sí solo: `match_anmat` exige además que los tokens compartidos no sean
# todos de la cláusula de sabor.
UMBRAL_SOLAPAMIENTO = 0.6


def match_anmat(nombre: str, marca: str | None,
                indice: dict[str, list[dict]]) -> dict | None:
    """Busca el producto en el registro oficial. Devuelve la fila o None.

    El cruce es deliberadamente estricto: sin EAN, un match flojo marcaría
    "apto" un producto que no lo es, que es justo el error que la regla de
    seguridad prohíbe. Se exige que la marca coincida y que los tokens
    significativos del nombre se solapen fuerte.
    """
    if not marca or not normalizar(marca):
        return None

    # La marca de OFF puede traer varias separadas por coma ("Arcor, Bagley").
    # El corte va ANTES de normalizar, porque normalizar() borra la puntuacion.
    candidatas = [normalizar(m) for m in str(marca).split(",")]
    filas: list[dict] = []
    for m in candidatas:
        if m:
            filas += indice.get(m, [])
    if not filas:
        return None

    tn = tokens(nombre)
    if not tn:
        return None

    mejor, mejor_score = None, 0.0
    for f in filas:
        tp = f["producto_tokens"]
        if not tp:
            continue
        comunes = tn & tp
        # El cruce tiene que apoyarse en la composición, no solo en el sabor:
        # "sabor dulce de leche" describe a qué sabe un postre de coco, no de
        # qué está hecho, y sin esto alcanzaba para certificar como vegano al
        # dulce de leche con leche de la misma marca (ver `tokens_de_sabor`).
        if not (comunes - f.get("sabor_tokens", set())):
            continue
        # Se mide contra el conjunto más chico: el nombre de ANMAT es
        # descriptivo y largo ("Medallones a base de choclo, quinoa y
        # calabaza"), el de OFF suele ser corto.
        score = len(comunes) / min(len(tn), len(tp))
        if score > mejor_score:
            mejor, mejor_score = f, score

    if mejor and mejor_score >= UMBRAL_SOLAPAMIENTO:
        return {**mejor, "score": round(mejor_score, 2)}
    return None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", dest="as_json", action="store_true")
    args = parser.parse_args(argv)

    filas = descargar()
    conn = db.connect()
    db.init_db(conn)
    try:
        n = guardar(conn, filas)
    finally:
        conn.close()

    marcas = len({f["marca"] for f in filas if f["marca"]})
    if args.as_json:
        print(json.dumps({"registros": n, "marcas": marcas}, ensure_ascii=False))
    else:
        print(f"Registro ANMAT: {n} productos con atributo vegano oficial, "
              f"{marcas} marcas.")
        for f in filas[:5]:
            print(f"  · {f['marca']} — {f['producto'][:60]} (RNPA {f['rnpa']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
