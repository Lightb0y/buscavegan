"""App Streamlit: buscar un producto argentino y ver si es apto vegano.

El diferencial no es el veredicto sino **por qué**: cada resultado muestra de
dónde salió la clasificación y, cuando la decisión vino de la lista de
ingredientes, qué ingrediente concreto la disparó.

    streamlit run app.py
"""
from __future__ import annotations

import sqlite3

import streamlit as st

import categorias
import config
import db

VEREDICTO = {
    config.APTO: ("✅", "Apto vegano", "#1a7f37"),
    config.VEGETARIANO: ("⚠️", "Vegetariano (no vegano)", "#9a6700"),
    config.NO_APTO: ("❌", "No apto", "#cf222e"),
    config.REVISAR: ("❓", "A revisar", "#57606a"),
}

FUENTE_LEGIBLE = {
    "off_label": "Declarado vegano por el fabricante",
    "ingredientes": "Analizado desde la lista de ingredientes",
    "off_analysis": "Análisis de ingredientes de Open Food Facts",
    "heuristica": "Estimado por reglas sobre el nombre del producto",
    "ml": "Estimado por clasificador automático",
    "sin_datos": "Sin datos suficientes",
}

PAGE_SIZE = 24


@st.cache_resource
def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(config.DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


@st.cache_data(ttl=300)
def stats() -> dict:
    conn = get_conn()
    total = conn.execute("SELECT COUNT(*) FROM productos").fetchone()[0]
    por_estado = {
        r["estado"]: r["n"] for r in
        conn.execute("SELECT estado, COUNT(*) n FROM productos GROUP BY estado")
    }
    ingr = conn.execute(
        "SELECT COUNT(*) FROM productos WHERE fuente_decision='ingredientes'"
    ).fetchone()[0]
    return {"total": total, "por_estado": por_estado, "por_ingredientes": ingr}


@st.cache_data(ttl=300)
def categorias_disponibles() -> list[str]:
    conn = get_conn()
    return [r[0] for r in conn.execute(
        "SELECT DISTINCT categoria FROM productos WHERE categoria IS NOT NULL"
        " ORDER BY categoria")]


def _fts_query(texto: str) -> str:
    """Prefijo por token: "leche coc" matchea "leche de coco"."""
    tokens = [t for t in "".join(
        c if c.isalnum() or c.isspace() else " " for c in texto).split() if t]
    return " ".join(f"{t}*" for t in tokens)


def buscar(texto: str, estados: list[str], categoria: str | None,
           limite: int = PAGE_SIZE) -> list[sqlite3.Row]:
    conn = get_conn()
    where, params = [], []

    if estados:
        where.append(f"p.estado IN ({','.join('?' * len(estados))})")
        params += estados
    if categoria and categoria != "Todas":
        where.append("p.categoria = ?")
        params.append(categoria)

    texto = (texto or "").strip()
    if texto.isdigit() and len(texto) >= 8:
        # Búsqueda por código de barras: match exacto.
        where.append("p.ean = ?")
        params.append(texto)
        sql = f"SELECT p.* FROM productos p WHERE {' AND '.join(where)}"
    elif texto:
        cond = (" AND " + " AND ".join(where)) if where else ""
        sql = ("SELECT p.* FROM productos_fts f JOIN productos p"
               " ON p.rowid = f.rowid"
               f" WHERE productos_fts MATCH ?{cond} ORDER BY rank")
        params = [_fts_query(texto)] + params
    else:
        cond = f"WHERE {' AND '.join(where)}" if where else ""
        sql = f"SELECT p.* FROM productos p {cond} ORDER BY p.nombre"

    sql += f" LIMIT {int(limite)}"
    try:
        return conn.execute(sql, params).fetchall()
    except sqlite3.OperationalError:
        # Consulta FTS inválida (comillas sueltas, etc.): caemos a LIKE.
        like = f"%{texto}%"
        cond = (" AND " + " AND ".join(where)) if where else ""
        return conn.execute(
            f"SELECT p.* FROM productos p WHERE (p.nombre LIKE ? OR p.marca LIKE ?)"
            f"{cond} ORDER BY p.nombre LIMIT {int(limite)}",
            [like, like] + params[1:] if texto else params).fetchall()


def card(p: sqlite3.Row) -> None:
    icono, etiqueta, color = VEREDICTO.get(p["estado"], VEREDICTO[config.REVISAR])
    with st.container(border=True):
        cols = st.columns([1, 5]) if p["imagen_url"] else [None, st.container()]
        if p["imagen_url"]:
            with cols[0]:
                st.image(p["imagen_url"], width=80)
            cuerpo = cols[1]
        else:
            cuerpo = st.container()

        with cuerpo:
            st.markdown(f"**{p['nombre']}**"
                        + (f"  \n*{p['marca']}*" if p["marca"] else ""))
            st.markdown(
                f"<span style='color:{color};font-weight:600'>{icono} {etiqueta}"
                "</span>", unsafe_allow_html=True)

            fuente = FUENTE_LEGIBLE.get(p["fuente_decision"], p["fuente_decision"])
            if p["confianza"] is not None:
                fuente += f" (confianza {p['confianza']:.0%})"
            st.caption(f"{fuente} · EAN {p['ean']}")

            if p["motivo"]:
                st.caption(f"↳ {p['motivo']}")

            if p["ingredients_text"]:
                with st.expander("Ver ingredientes"):
                    st.write(p["ingredients_text"])


def main() -> None:
    st.set_page_config(page_title="buscavegan", page_icon="🌱", layout="wide")
    st.title("🌱 buscavegan")
    st.caption("¿Este producto argentino es apto vegano? Y sobre todo: "
               "**cómo lo sabemos**.")

    if not config.DB_PATH.exists():
        st.error("No existe la base. Corré `python ingest_off_ar.py` y "
                 "`python build_db.py` primero.")
        return

    s = stats()
    if not s["total"]:
        st.warning("La base está vacía. Corré `python build_db.py`.")
        return

    with st.sidebar:
        st.subheader("Filtros")
        elegidos = [e for e, (ic, lbl, _) in VEREDICTO.items()
                    if st.checkbox(f"{ic} {lbl}", value=True, key=f"f_{e}")]
        categoria = st.selectbox(
            "Categoría", ["Todas"] + categorias_disponibles())
        limite = st.slider("Resultados", 6, 96, PAGE_SIZE, step=6)

        st.divider()
        st.caption(f"**{s['total']:,}** productos argentinos".replace(",", "."))
        st.caption(f"**{s['por_ingredientes']:,}** clasificados por su lista "
                   "de ingredientes".replace(",", "."))
        st.divider()
        st.caption("«Apto» = **vegano** (sin ingredientes de origen animal). "
                   "No significa *cruelty-free*: el testeo en animales no está "
                   "en estas fuentes de datos.")

    texto = st.text_input(
        "Buscar", placeholder="Nombre, marca o código de barras — ej. "
        "«leche de almendras», «Arcor», «7790040...»",
        label_visibility="collapsed")

    resultados = buscar(texto, elegidos, categoria, limite)

    if not resultados:
        st.info("Sin resultados. Probá con menos filtros o menos palabras.")
        return

    st.caption(f"{len(resultados)} resultado(s)")
    columnas = st.columns(3)
    for i, p in enumerate(resultados):
        with columnas[i % 3]:
            card(p)


if __name__ == "__main__":
    main()
