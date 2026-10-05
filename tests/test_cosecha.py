"""Tests de la cosecha grande de fichas (§ FODA 4.1).

Dos cosas se fijan acá, y las dos son nuevas:

1. **La cola mira todo el catálogo relevado**, no solo los productos que ya
   están clasificados. Antes arrancaba `FROM productos` y por eso devolvía 26
   fichas pendientes cuando había 87.078 sin pedir: el techo lo ponía un JOIN,
   no el presupuesto de consultas.

2. **Un producto que solo existe en la góndola entra al sitio si —y solo si—
   la ficha lo respalda.** Ese camino está escrito pero todavía vacío (hasta
   que la cosecha corra, toda ficha pertenece a un producto que OFF ya
   conocía), así que los tests son la única forma de saber que funciona antes
   de que le pasen decenas de miles de productos por encima.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import build_db  # noqa: E402
import db as _db  # noqa: E402
import ingest_fichas  # noqa: E402

EAN_OFF = "7790000002017"      # producto que OFF conoce
EAN_GONDOLA = "7790000002024"  # producto que solo publica el supermercado


def _conn(tmp_path):
    conn = _db.connect(tmp_path / "cosecha.db")
    _db.init_db(conn)
    return conn


def _en_gondola(conn, ean, nombre, cadena="disco", marca="Marca X",
                categoria="Almacén"):
    conn.execute(
        "INSERT OR REPLACE INTO vtex_catalogo"
        " (ean, cadena, nombre, marca, categoria, actualizado)"
        " VALUES (?,?,?,?,?,'2026-01-01')",
        (ean, cadena, nombre, marca, categoria))


def _con_ficha(conn, ean, ingredientes=None, sellos=None, cadena="disco"):
    conn.execute(
        "INSERT OR REPLACE INTO vtex_ficha"
        " (ean, cadena, ingredientes, trazas, sellos, actualizado)"
        " VALUES (?,?,?,NULL,?,'2026-01-01')",
        (ean, cadena, ingredientes, sellos))


# --- La cola --------------------------------------------------------------

def test_la_cola_incluye_productos_que_off_no_conoce(tmp_path):
    """El caso que la versión vieja no podía ver."""
    conn = _conn(tmp_path)
    _en_gondola(conn, EAN_GONDOLA, "Galletitas Sin Ficha")
    conn.commit()

    assert (EAN_GONDOLA, "disco") in ingest_fichas.pendientes(conn)
    conn.close()


def test_la_cola_no_repite_lo_ya_consultado(tmp_path):
    """Incluso si la ficha vino vacía: para eso se guarda vacía."""
    conn = _conn(tmp_path)
    _en_gondola(conn, EAN_GONDOLA, "Ya Consultado")
    _con_ficha(conn, EAN_GONDOLA, ingredientes=None)
    conn.commit()

    assert ingest_fichas.pendientes(conn) == []
    conn.close()


def test_la_cola_prioriza_lo_que_ya_se_muestra_sin_evidencia(tmp_path):
    """Una ficha sobre un producto del sitio que adivinó por el nombre vale
    más que una sobre un producto que todavía no está publicado."""
    conn = _conn(tmp_path)
    _en_gondola(conn, EAN_GONDOLA, "Producto Nuevo")
    _en_gondola(conn, EAN_OFF, "Producto Publicado Sin Evidencia")
    conn.execute(
        "INSERT INTO productos (ean, nombre, estado, fuente_decision,"
        " ingredients_text) VALUES (?,?,'revisar','heuristica',NULL)",
        (EAN_OFF, "Producto Publicado Sin Evidencia"))
    conn.commit()

    cola = [ean for ean, _ in ingest_fichas.pendientes(conn)]
    assert cola.index(EAN_OFF) < cola.index(EAN_GONDOLA)
    conn.close()


def test_la_cola_deja_para_el_final_lo_que_ya_tiene_evidencia(tmp_path):
    conn = _conn(tmp_path)
    _en_gondola(conn, EAN_GONDOLA, "Producto Nuevo")
    _en_gondola(conn, EAN_OFF, "Producto Ya Resuelto")
    conn.execute(
        "INSERT INTO productos (ean, nombre, estado, fuente_decision,"
        " ingredients_text) VALUES (?,?,'apto','ingredientes','agua, sal')",
        (EAN_OFF, "Producto Ya Resuelto"))
    conn.commit()

    cola = [ean for ean, _ in ingest_fichas.pendientes(conn)]
    assert cola.index(EAN_GONDOLA) < cola.index(EAN_OFF)
    conn.close()


def test_la_cola_no_gasta_consultas_en_lo_que_no_es_alimento(tmp_path):
    """`relevancia` ya sabe descartarlos; preguntar igual es tirar una
    consulta, y a 85.000 fichas eso se nota."""
    conn = _conn(tmp_path)
    _en_gondola(conn, EAN_GONDOLA, "Shampoo Anticaspa")
    _en_gondola(conn, EAN_OFF, "Galletitas de agua")
    conn.commit()

    cola = [ean for ean, _ in ingest_fichas.pendientes(conn)]
    assert EAN_GONDOLA not in cola
    assert EAN_OFF in cola
    conn.close()


def test_el_limite_corta_la_cola(tmp_path):
    conn = _conn(tmp_path)
    for i in range(10):
        _en_gondola(conn, f"779000000{i:04d}", f"Producto {i}")
    conn.commit()

    assert len(ingest_fichas.pendientes(conn, limite=3)) == 3
    conn.close()


def test_solo_se_consultan_las_cadenas_que_publican_ficha(tmp_path):
    """Carrefour y Día no exponen los campos: preguntarles es al pedo."""
    conn = _conn(tmp_path)
    _en_gondola(conn, EAN_GONDOLA, "Producto Carrefour", cadena="carrefour")
    conn.commit()

    assert ingest_fichas.pendientes(conn) == []
    conn.close()


# --- El producto que solo existe en la góndola ----------------------------

def test_una_ficha_con_ingredientes_mete_el_producto_en_el_sitio(tmp_path):
    conn = _conn(tmp_path)
    _en_gondola(conn, EAN_GONDOLA, "Fideos Tirabuzón", marca="LUCCHETTI")
    _con_ficha(conn, EAN_GONDOLA, ingredientes="Sémola de trigo, agua")
    conn.commit()

    build_db.build(conn, verbose=False)
    fila = conn.execute(
        "SELECT nombre, marca, categoria, estado, fuente_decision,"
        " ingredients_text FROM productos WHERE ean=?", (EAN_GONDOLA,)
    ).fetchone()
    assert fila is not None, "un producto con su etiqueta leída tiene que entrar"
    assert fila["ingredients_text"] == "Sémola de trigo, agua"
    assert fila["fuente_decision"] == build_db.FUENTE_INGREDIENTES_SUPER
    conn.close()


def test_una_ficha_con_sello_vegano_tambien_lo_mete(tmp_path):
    conn = _conn(tmp_path)
    _en_gondola(conn, EAN_GONDOLA, "Barra Vegana")
    _con_ficha(conn, EAN_GONDOLA, sellos="vegan")
    conn.commit()

    build_db.build(conn, verbose=False)
    fila = conn.execute(
        "SELECT estado, fuente_decision FROM productos WHERE ean=?",
        (EAN_GONDOLA,)).fetchone()
    assert fila is not None
    assert fila["fuente_decision"] == build_db.FUENTE_SELLO_SUPER
    conn.close()


def test_un_sello_que_no_es_vegano_no_alcanza_para_entrar(tmp_path):
    """Casi todos los sellos de las cadenas son de alérgenos: "sin TACC" sin
    lista de ingredientes no dice nada sobre si el producto es apto."""
    conn = _conn(tmp_path)
    _en_gondola(conn, EAN_GONDOLA, "Galletitas Sin Tacc")
    _con_ficha(conn, EAN_GONDOLA, sellos="gluten_free,kosher")
    conn.commit()

    build_db.build(conn, verbose=False)
    assert conn.execute(
        "SELECT COUNT(*) FROM productos WHERE ean=?", (EAN_GONDOLA,)
    ).fetchone()[0] == 0
    conn.close()


def test_el_sello_vegano_entra_aunque_venga_con_otros(tmp_path):
    conn = _conn(tmp_path)
    _en_gondola(conn, EAN_GONDOLA, "Barra Vegana")
    _con_ficha(conn, EAN_GONDOLA, sellos="gluten_free,vegan,vegetarian")
    conn.commit()

    build_db.build(conn, verbose=False)
    assert conn.execute(
        "SELECT fuente_decision FROM productos WHERE ean=?", (EAN_GONDOLA,)
    ).fetchone()[0] == build_db.FUENTE_SELLO_SUPER
    conn.close()


def test_sin_evidencia_el_producto_de_gondola_no_entra(tmp_path):
    """El límite que evita que la cosecha infle el catálogo con nombres.

    Se le preguntó al supermercado y no publicó ni ingredientes ni sello. De
    este producto sabemos lo mismo que antes de preguntar: el nombre. Un
    veredicto sacado de ahí es una adivinanza, y sumar decenas de miles de
    adivinanzas haría el catálogo más grande y el sitio peor.
    """
    conn = _conn(tmp_path)
    _en_gondola(conn, EAN_GONDOLA, "Producto Sin Datos")
    _con_ficha(conn, EAN_GONDOLA)  # consultada, vacía
    conn.commit()

    build_db.build(conn, verbose=False)
    assert conn.execute(
        "SELECT COUNT(*) FROM productos WHERE ean=?", (EAN_GONDOLA,)
    ).fetchone()[0] == 0
    conn.close()


def test_estar_en_la_gondola_sin_ficha_tampoco_alcanza(tmp_path):
    conn = _conn(tmp_path)
    _en_gondola(conn, EAN_GONDOLA, "Producto Nunca Consultado")
    conn.commit()

    build_db.build(conn, verbose=False)
    assert conn.execute(
        "SELECT COUNT(*) FROM productos WHERE ean=?", (EAN_GONDOLA,)
    ).fetchone()[0] == 0
    conn.close()


def test_el_producto_de_gondola_no_duplica_al_que_off_ya_tiene(tmp_path):
    """El mismo EAN en `catalogo` y en la góndola es un solo producto."""
    conn = _conn(tmp_path)
    _db.upsert_catalogo(conn, [
        {"ean": EAN_OFF, "nombre": "Producto De OFF", "marca": "Marca"}])
    _en_gondola(conn, EAN_OFF, "Producto En Góndola")
    _con_ficha(conn, EAN_OFF, ingredientes="agua, sal")
    conn.commit()

    build_db.build(conn, verbose=False)
    assert conn.execute(
        "SELECT COUNT(*) FROM productos WHERE ean=?", (EAN_OFF,)
    ).fetchone()[0] == 1
    conn.close()


def test_al_producto_de_gondola_se_le_normaliza_la_marca(tmp_path):
    """Las cadenas publican en mayúsculas; el sitio no las muestra así."""
    conn = _conn(tmp_path)
    _db.upsert_catalogo(conn, [
        {"ean": EAN_OFF, "nombre": "Fideos", "marca": "Lucchetti"}])
    _en_gondola(conn, EAN_GONDOLA, "Fideos Mostachol", marca="LUCCHETTI")
    _con_ficha(conn, EAN_GONDOLA, ingredientes="Sémola de trigo")
    conn.commit()

    build_db.build(conn, verbose=False)
    marca = conn.execute(
        "SELECT marca FROM productos WHERE ean=?", (EAN_GONDOLA,)
    ).fetchone()["marca"]
    assert marca == "Lucchetti"
    conn.close()


def test_al_producto_de_gondola_se_le_deduce_el_rubro(tmp_path):
    conn = _conn(tmp_path)
    _en_gondola(conn, EAN_GONDOLA, "Galletitas de Agua", categoria="Almacén")
    _con_ficha(conn, EAN_GONDOLA, ingredientes="Harina de trigo, agua, sal")
    conn.commit()

    build_db.build(conn, verbose=False)
    categoria = conn.execute(
        "SELECT categoria FROM productos WHERE ean=?", (EAN_GONDOLA,)
    ).fetchone()["categoria"]
    assert categoria == "Galletitas y bizcochos"
    conn.close()


def test_el_no_alimento_de_gondola_no_entra_aunque_tenga_ficha(tmp_path):
    conn = _conn(tmp_path)
    _en_gondola(conn, EAN_GONDOLA, "Shampoo Anticaspa 400ml")
    _con_ficha(conn, EAN_GONDOLA, ingredientes="Aqua, sodium laureth sulfate")
    conn.commit()

    build_db.build(conn, verbose=False)
    assert conn.execute(
        "SELECT COUNT(*) FROM productos WHERE ean=?", (EAN_GONDOLA,)
    ).fetchone()[0] == 0
    conn.close()


# --- Preguntar y no poder preguntar no son lo mismo -----------------------
#
# Es la distinción que vuelve segura una corrida de horas: guardar la ficha
# vacía es correcto cuando la cadena contestó que no tiene el producto, y es
# inventar una respuesta cuando la cadena no contestó nada.

class _Respuesta:
    def __init__(self, status_code, payload=None, rompe_json=False):
        self.status_code = status_code
        self._payload = payload
        self._rompe_json = rompe_json

    def json(self):
        if self._rompe_json:
            raise ValueError("no es json")
        return self._payload


class _Sesion:
    """Session de requests de mentira: devuelve lo que se le diga."""

    def __init__(self, respuestas):
        self._respuestas = list(respuestas)
        self.consultas = 0

    def get(self, *a, **kw):
        self.consultas += 1
        r = self._respuestas[min(self.consultas - 1, len(self._respuestas) - 1)]
        if isinstance(r, Exception):
            raise r
        return r


def test_la_cadena_contesta_con_la_ficha():
    sesion = _Sesion([_Respuesta(200, [{
        "Ingredientes": ["'harina de trigo', 'sal'"],
        "Sellos": [],
    }])])
    resultado, ficha = ingest_fichas.pedir_ficha(sesion, "http://x", "779")
    assert resultado == ingest_fichas.RESPONDIO
    assert ficha["ingredientes"] == "harina de trigo, sal"


def test_la_cadena_contesta_que_no_lo_tiene():
    sesion = _Sesion([_Respuesta(200, [])])
    resultado, ficha = ingest_fichas.pedir_ficha(sesion, "http://x", "779")
    assert resultado == ingest_fichas.NO_LA_TIENE
    assert ficha is None


def test_un_404_es_una_respuesta():
    sesion = _Sesion([_Respuesta(404)])
    resultado, _ = ingest_fichas.pedir_ficha(sesion, "http://x", "779")
    assert resultado == ingest_fichas.NO_LA_TIENE


@pytest.mark.parametrize("respuesta", [
    _Respuesta(503),                      # servicio caído
    _Respuesta(429),                      # límite de consultas
    _Respuesta(500),
    _Respuesta(200, rompe_json=True),     # contestó cualquier cosa
])
def test_un_corte_no_es_una_respuesta(respuesta):
    sesion = _Sesion([respuesta])
    resultado, _ = ingest_fichas.pedir_ficha(sesion, "http://x", "779")
    assert resultado == ingest_fichas.NO_CONTESTO


def test_un_timeout_no_es_una_respuesta():
    sesion = _Sesion([requests.Timeout("se cansó de esperar")])
    resultado, _ = ingest_fichas.pedir_ficha(sesion, "http://x", "779")
    assert resultado == ingest_fichas.NO_CONTESTO


def test_lo_que_no_contesto_no_se_guarda_y_vuelve_a_la_cola(tmp_path, monkeypatch):
    """El corte de red no puede dejar productos marcados como consultados."""
    conn = _conn(tmp_path)
    _en_gondola(conn, EAN_GONDOLA, "Galletitas de Agua")
    conn.commit()

    monkeypatch.setattr(ingest_fichas, "pedir_ficha",
                        lambda *a: (ingest_fichas.NO_CONTESTO, None))
    monkeypatch.setattr(ingest_fichas.time, "sleep", lambda *_: None)
    stats = ingest_fichas.ingest(conn, sleep=0, verbose=False)

    assert stats["sin_respuesta"] >= 1
    assert conn.execute("SELECT COUNT(*) FROM vtex_ficha").fetchone()[0] == 0
    assert ingest_fichas.pendientes(conn) != [], "tiene que seguir pendiente"
    conn.close()


def test_lo_que_la_cadena_dijo_no_tener_si_se_guarda(tmp_path, monkeypatch):
    """Para no volver a preguntar lo mismo en cada corrida."""
    conn = _conn(tmp_path)
    _en_gondola(conn, EAN_GONDOLA, "Galletitas de Agua")
    conn.commit()

    monkeypatch.setattr(ingest_fichas, "pedir_ficha",
                        lambda *a: (ingest_fichas.NO_LA_TIENE, None))
    monkeypatch.setattr(ingest_fichas.time, "sleep", lambda *_: None)
    ingest_fichas.ingest(conn, sleep=0, verbose=False)

    assert conn.execute("SELECT COUNT(*) FROM vtex_ficha").fetchone()[0] == 1
    assert ingest_fichas.pendientes(conn) == []
    conn.close()


def test_la_corrida_se_corta_si_la_cadena_dejo_de_responder(tmp_path, monkeypatch):
    """Seguir sería quemar 85.000 consultas contra un servicio que no está."""
    conn = _conn(tmp_path)
    for i in range(200):
        _en_gondola(conn, f"779000001{i:04d}", f"Galletitas {i}")
    conn.commit()

    llamadas = {"n": 0}

    def _falla(*a):
        llamadas["n"] += 1
        return ingest_fichas.NO_CONTESTO, None

    monkeypatch.setattr(ingest_fichas, "pedir_ficha", _falla)
    monkeypatch.setattr(ingest_fichas.time, "sleep", lambda *_: None)
    stats = ingest_fichas.ingest(conn, sleep=0, verbose=False)

    assert stats["cortada"] == 1
    assert llamadas["n"] == ingest_fichas.MAX_FALLOS_SEGUIDOS
    conn.close()


def test_un_corte_aislado_no_corta_la_corrida(tmp_path, monkeypatch):
    conn = _conn(tmp_path)
    for i in range(10):
        _en_gondola(conn, f"779000002{i:04d}", f"Galletitas {i}")
    conn.commit()

    estado = {"n": 0}

    def _intermitente(*a):
        estado["n"] += 1
        if estado["n"] % 3 == 0:
            return ingest_fichas.NO_CONTESTO, None
        return ingest_fichas.RESPONDIO, {
            "ingredientes": "harina, sal", "trazas": None, "sellos": None}

    monkeypatch.setattr(ingest_fichas, "pedir_ficha", _intermitente)
    monkeypatch.setattr(ingest_fichas.time, "sleep", lambda *_: None)
    stats = ingest_fichas.ingest(conn, sleep=0, verbose=False)

    assert stats["cortada"] == 0
    assert stats["con_ingredientes"] > 0
    conn.close()


def test_los_codigos_de_circulacion_restringida_van_al_final(tmp_path):
    """Prefijo GS1 2: lo que pesa o fracciona el propio súper. Medido en la
    cosecha, 0,1% trae ficha; pedirlos primero se llevó dos tercios de las
    consultas."""
    conn = _conn(tmp_path)
    _en_gondola(conn, "2000000000015", "Queso Cremoso Al Corte")
    _en_gondola(conn, EAN_GONDOLA, "Galletitas de Agua")
    conn.commit()

    cola = [ean for ean, _ in ingest_fichas.pendientes(conn)]
    assert cola == [EAN_GONDOLA, "2000000000015"]
    conn.close()


# --- La copia versionada --------------------------------------------------
#
# La base es derivada y en CI vive en un cache que vence. La cosecha completa
# son horas de consultas: lo que sobrevive es el archivo versionado.

def _cosecha(tmp_path):
    return tmp_path / "COSECHA" / "fichas.ndjson"


def test_la_copia_versionada_reconstruye_la_cosecha_en_una_base_nueva(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    origen = _conn(tmp_path / "a")
    _con_ficha(origen, EAN_GONDOLA, ingredientes="harina, sal", sellos="vegan")
    _con_ficha(origen, EAN_OFF)  # contestó que no la tiene: también cuenta
    origen.commit()
    assert ingest_fichas.exportar(origen, _cosecha(tmp_path)) == 2
    origen.close()

    destino = _conn(tmp_path / "b")
    _en_gondola(destino, EAN_GONDOLA, "Galletitas de Agua")
    _en_gondola(destino, EAN_OFF, "Producto Sin Ficha")
    destino.commit()
    st = ingest_fichas.importar(destino, _cosecha(tmp_path))

    assert st == {"leidas": 2, "nuevas": 2, "actualizadas": 0}
    fila = destino.execute(
        "SELECT ingredientes, sellos FROM vtex_ficha WHERE ean=?",
        (EAN_GONDOLA,)).fetchone()
    assert (fila["ingredientes"], fila["sellos"]) == ("harina, sal", "vegan")
    # Lo importante: la base nueva no vuelve a preguntar lo que ya se preguntó.
    assert ingest_fichas.pendientes(destino) == []
    destino.close()


def test_importar_no_pisa_una_ficha_mas_nueva(tmp_path):
    """Una máquina que cosechó después no pierde lo suyo al importar lo de
    otra."""
    ruta = _cosecha(tmp_path)
    ruta.parent.mkdir(parents=True)
    ruta.write_text(
        '{"ean":"%s","cadena":"disco","actualizado":"2026-01-01T00:00:00+00:00"}\n'
        % EAN_GONDOLA, encoding="utf-8")

    conn = _conn(tmp_path)
    conn.execute(
        "INSERT INTO vtex_ficha (ean, cadena, ingredientes, actualizado)"
        " VALUES (?, 'disco', 'harina, sal', '2026-06-01T00:00:00+00:00')",
        (EAN_GONDOLA,))
    conn.commit()

    st = ingest_fichas.importar(conn, ruta)
    assert st["nuevas"] == 0 and st["actualizadas"] == 0
    assert conn.execute(
        "SELECT ingredientes FROM vtex_ficha WHERE ean=?", (EAN_GONDOLA,)
    ).fetchone()[0] == "harina, sal"
    conn.close()


def test_importar_trae_la_version_mas_nueva(tmp_path):
    ruta = _cosecha(tmp_path)
    ruta.parent.mkdir(parents=True)
    ruta.write_text(
        '{"ean":"%s","cadena":"disco","ingredientes":"harina, sal",'
        '"actualizado":"2026-06-01T00:00:00+00:00"}\n' % EAN_GONDOLA,
        encoding="utf-8")

    conn = _conn(tmp_path)
    _con_ficha(conn, EAN_GONDOLA)  # vacía, fechada 2026-01-01
    conn.commit()

    assert ingest_fichas.importar(conn, ruta)["actualizadas"] == 1
    assert conn.execute(
        "SELECT ingredientes FROM vtex_ficha WHERE ean=?", (EAN_GONDOLA,)
    ).fetchone()[0] == "harina, sal"
    conn.close()


def test_exportar_es_estable(tmp_path):
    """Ordenado por EAN y sin nulos: dos exportaciones de la misma base dan
    el mismo archivo, y git ve solo lo que cambió de verdad."""
    conn = _conn(tmp_path)
    _con_ficha(conn, EAN_GONDOLA, ingredientes="harina")
    _con_ficha(conn, EAN_OFF)
    conn.commit()

    ruta = _cosecha(tmp_path)
    ingest_fichas.exportar(conn, ruta)
    primera = ruta.read_bytes()
    ingest_fichas.exportar(conn, ruta)
    assert ruta.read_bytes() == primera

    lineas = primera.decode("utf-8").splitlines()
    assert [l.split('"ean":"')[1][:13] for l in lineas] == [EAN_OFF, EAN_GONDOLA]
    assert "null" not in primera.decode("utf-8")
    conn.close()


def test_sin_copia_versionada_importar_no_hace_nada(tmp_path):
    conn = _conn(tmp_path)
    st = ingest_fichas.importar(conn, tmp_path / "no-existe.ndjson")
    assert st == {"leidas": 0, "nuevas": 0, "actualizadas": 0}
    conn.close()


def test_una_copia_rota_no_se_pisa(tmp_path, monkeypatch):
    """Si no se pudo leer el archivo, exportar desde la base lo reemplazaría
    por una versión con menos fichas. Mejor fallar y que alguien mire."""
    ruta = _cosecha(tmp_path)
    ruta.parent.mkdir(parents=True)
    contenido = '{"ean":"%s","cadena":"disco"\n' % EAN_GONDOLA  # JSON cortado
    ruta.write_text(contenido, encoding="utf-8")
    monkeypatch.setattr(ingest_fichas.config, "COSECHA_PATH", ruta)
    monkeypatch.setattr(ingest_fichas.config, "DB_PATH", tmp_path / "x.db")

    with pytest.raises(ValueError):
        ingest_fichas.main(["--solo-sincronizar"])
    assert ruta.read_text(encoding="utf-8") == contenido


def test_una_corrida_cortada_igual_deja_lo_cosechado_en_la_copia(
        tmp_path, monkeypatch):
    """Ctrl+C a mitad de una corrida de horas: lo pedido hasta ahí no se
    pierde."""
    ruta = _cosecha(tmp_path)
    monkeypatch.setattr(ingest_fichas.config, "COSECHA_PATH", ruta)
    monkeypatch.setattr(ingest_fichas.config, "DB_PATH", tmp_path / "x.db")
    conn = _db.connect(tmp_path / "x.db")  # la misma que abre `main`
    _db.init_db(conn)
    _con_ficha(conn, EAN_GONDOLA, ingredientes="harina")
    conn.commit()
    conn.close()

    def _cortar(*a, **kw):
        raise KeyboardInterrupt

    monkeypatch.setattr(ingest_fichas, "ingest", _cortar)
    with pytest.raises(KeyboardInterrupt):
        ingest_fichas.main([])
    assert EAN_GONDOLA in ruta.read_text(encoding="utf-8")
