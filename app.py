"""App Streamlit: buscar un producto argentino y ver si es apto vegano.

El diferencial no es el veredicto sino **por qué**: cada resultado muestra de
dónde salió la clasificación y, cuando la decisión vino de la lista de
ingredientes, qué ingrediente concreto la disparó.

    streamlit run app.py
"""
from __future__ import annotations

import math
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


def _armar_consulta(texto: str, estados: list[str], categoria: str | None):
    """Arma (sql_base, params, usa_fts) sin LIMIT ni SELECT, para reusar en
    la búsqueda paginada y en el conteo total."""
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
        return f"FROM productos p WHERE {' AND '.join(where)}", params, False
    if texto:
        cond = (" AND " + " AND ".join(where)) if where else ""
        sql = (f"FROM productos_fts f JOIN productos p"
               f" ON p.rowid = f.rowid WHERE productos_fts MATCH ?{cond}")
        return sql, [_fts_query(texto)] + params, True

    cond = f"WHERE {' AND '.join(where)}" if where else ""
    return f"FROM productos p {cond}", params, False


def contar(texto: str, estados: list[str], categoria: str | None) -> int:
    """Total de resultados que matchean, sin el LIMIT de la página."""
    conn = get_conn()
    sql, params, _ = _armar_consulta(texto, estados, categoria)
    try:
        return conn.execute(f"SELECT COUNT(*) {sql}", params).fetchone()[0]
    except sqlite3.OperationalError:
        return 0


def buscar(texto: str, estados: list[str], categoria: str | None,
           limite: int = PAGE_SIZE, offset: int = 0) -> list[sqlite3.Row]:
    conn = get_conn()
    sql, params, usa_fts = _armar_consulta(texto, estados, categoria)
    orden = " ORDER BY rank" if usa_fts else " ORDER BY p.nombre"
    try:
        return conn.execute(
            f"SELECT p.* {sql}{orden} LIMIT {int(limite)} OFFSET {int(offset)}",
            params).fetchall()
    except sqlite3.OperationalError:
        # Consulta FTS inválida (comillas sueltas, etc.): caemos a LIKE.
        where, params2 = [], []
        if estados:
            where.append(f"p.estado IN ({','.join('?' * len(estados))})")
            params2 += estados
        if categoria and categoria != "Todas":
            where.append("p.categoria = ?")
            params2.append(categoria)
        like = f"%{(texto or '').strip()}%"
        where.append("(p.nombre LIKE ? OR p.marca LIKE ?)")
        params2 += [like, like]
        cond = f"WHERE {' AND '.join(where)}" if where else ""
        return conn.execute(
            f"SELECT p.* FROM productos p {cond} ORDER BY p.nombre"
            f" LIMIT {int(limite)} OFFSET {int(offset)}", params2).fetchall()


def total_paginas(total: int, limite: int) -> int:
    return max(1, math.ceil(total / limite)) if limite else 1


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


def _ir_a_pagina(nueva: int) -> None:
    """Cambia de página y fuerza el rerun antes de que se dibuje el
    number_input de abajo — evita el error de Streamlit por escribir en
    session_state después de instanciar el widget que usa esa misma key."""
    st.session_state.pagina = nueva
    st.rerun()


def controles_paginacion(pagina: int, n_paginas: int, key_prefix: str,
                         con_salto: bool) -> None:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c1:
        if st.button("⬅ Anterior", disabled=pagina <= 1,
                    key=f"{key_prefix}_ant", use_container_width=True):
            _ir_a_pagina(pagina - 1)
    with c3:
        if st.button("Siguiente ➡", disabled=pagina >= n_paginas,
                    key=f"{key_prefix}_sig", use_container_width=True):
            _ir_a_pagina(pagina + 1)
    with c2:
        if con_salto and n_paginas > 1:
            st.number_input(
                "Ir a la página", min_value=1, max_value=n_paginas, step=1,
                key="pagina", label_visibility="collapsed")
        else:
            st.markdown(
                f"<div style='text-align:center;padding-top:0.4rem'>"
                f"Página {pagina} de {n_paginas}</div>", unsafe_allow_html=True)


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
        limite = st.slider("Resultados por página", 6, 300, PAGE_SIZE, step=6)

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

    # Si cambió la búsqueda o algún filtro, la página vieja ya no tiene
    # sentido (podría quedar más allá del final) — se vuelve a la 1.
    firma = (texto, tuple(sorted(elegidos)), categoria, limite)
    if st.session_state.get("firma_filtros") != firma:
        st.session_state.firma_filtros = firma
        st.session_state.pagina = 1
    st.session_state.setdefault("pagina", 1)

    total = contar(texto, elegidos, categoria)
    if not total:
        st.info("Sin resultados. Probá con menos filtros o menos palabras.")
        return

    n_paginas = total_paginas(total, limite)
    # Clamp antes de crear el number_input(key="pagina"): así el ajuste
    # queda dentro de rango en el mismo run en el que se instancia el widget.
    st.session_state.pagina = min(max(st.session_state.pagina, 1), n_paginas)
    pagina = st.session_state.pagina
    offset = (pagina - 1) * limite

    resultados = buscar(texto, elegidos, categoria, limite, offset)

    desde, hasta = offset + 1, offset + len(resultados)
    st.caption(f"Mostrando {desde:,}–{hasta:,} de **{total:,}** resultados"
              .replace(",", "."))

    if n_paginas > 1:
        controles_paginacion(pagina, n_paginas, "top", con_salto=True)

    columnas = st.columns(3)
    for i, p in enumerate(resultados):
        with columnas[i % 3]:
            card(p)

    if n_paginas > 1:
        st.divider()
        controles_paginacion(pagina, n_paginas, "bottom", con_salto=False)


if __name__ == "__main__":
    main()
