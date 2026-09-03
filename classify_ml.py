"""Capa 3 — clasificador por nombre entrenado con supervisión débil.

De dónde salen las etiquetas
----------------------------
No hay dataset etiquetado a mano: se usa como training set lo que las capas
duras ya resolvieron con evidencia real (certificación de ANMAT, declaración
del fabricante y análisis de ingredientes). El modelo aprende a reconocer, en
el nombre y la marca, los patrones que acompañan a cada estado, y con eso
opina sobre los productos que **no publican ingredientes** — que son la mayoría
del catálogo argentino en OFF.

Por qué TF-IDF con bigramas y regresión logística
-------------------------------------------------
Los nombres de supermercado tienen vocabulario corto y muy repetido
(marca + tipo + variante). El bigrama es lo que hace la diferencia: "leche de"
seguido de "de coco" separa dos productos que el unigrama "leche" confunde.
La regresión logística se elige por encima de un ensemble porque sus
coeficientes se leen: `explicar()` muestra qué palabras empujan cada clase, que
es como se detecta el leakage y el sesgo antes de publicar una predicción.

Regla de seguridad
------------------
El umbral es **asimétrico a propósito**: para marcar `apto` se exige mucha más
probabilidad que para marcar `no_apto`. Un falso "apto" hace que alguien coma
lo que no quería comer; un falso "no apto" solo le hace perderse un producto.
Todo lo que queda entre medio va a `revisar`, no a la clase más probable.

    python classify_ml.py --entrenar     # entrena, evalúa y guarda el modelo
    python classify_ml.py --explicar     # qué aprendió, por clase
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import config
import db

MODELO_PATH = config.MODELS_DIR / "clasificador.joblib"
FUENTE_ML = "ml"

# Fuentes cuya decisión es evidencia real y sirve como etiqueta de entrenamiento.
FUENTES_CONFIABLES = ("certificacion_oficial", "off_label", "ingredientes",
                      "off_analysis")


def _texto(nombre: str | None, marca: str | None) -> str:
    return f"{nombre or ''} {marca or ''}".strip().lower()


def cargar_training_set(conn) -> tuple[list[str], list[str]]:
    """Productos ya resueltos con evidencia: son las etiquetas del modelo."""
    marcadores = ",".join("?" * len(FUENTES_CONFIABLES))
    filas = conn.execute(
        f"SELECT nombre, marca, estado FROM productos"
        f" WHERE fuente_decision IN ({marcadores}) AND estado != ?",
        (*FUENTES_CONFIABLES, config.REVISAR)).fetchall()
    X = [_texto(f["nombre"], f["marca"]) for f in filas]
    y = [f["estado"] for f in filas]
    return X, y


def construir_pipeline():
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline

    return Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 2),   # el bigrama es lo que resuelve "leche de coco"
            min_df=2,             # una palabra que aparece una sola vez es ruido
            sublinear_tf=True,
            strip_accents="unicode")),
        ("clf", LogisticRegression(
            max_iter=2000,
            # El catálogo está desbalanceado y las clases chicas son las que
            # más importan: sin esto el modelo aprende a decir siempre `revisar`.
            class_weight="balanced")),
    ])


def entrenar(conn, test_size: float = 0.25, seed: int = 42) -> dict:
    from sklearn.metrics import classification_report, confusion_matrix
    from sklearn.model_selection import train_test_split

    X, y = cargar_training_set(conn)
    if len(X) < config.ML_MIN_TRAIN_SAMPLES:
        return {"error": f"Solo hay {len(X)} ejemplos etiquetados; se necesitan "
                         f"al menos {config.ML_MIN_TRAIN_SAMPLES}."}

    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=test_size, random_state=seed, stratify=y)

    modelo = construir_pipeline()
    modelo.fit(X_tr, y_tr)
    y_pred = modelo.predict(X_te)

    etiquetas = sorted(set(y))
    reporte = {
        "ejemplos": len(X),
        "entrenamiento": len(X_tr),
        "holdout": len(X_te),
        "clases": {c: y.count(c) for c in etiquetas},
        "metricas": classification_report(y_te, y_pred, output_dict=True,
                                          zero_division=0),
        "matriz_confusion": {
            "etiquetas": etiquetas,
            "matriz": confusion_matrix(y_te, y_pred, labels=etiquetas).tolist(),
        },
    }

    import joblib
    MODELO_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(modelo, MODELO_PATH)
    reporte["modelo"] = str(MODELO_PATH)
    return reporte


def cargar_modelo(path: Path | None = None):
    path = path or MODELO_PATH
    if not path.exists():
        return None
    import joblib
    return joblib.load(path)


def predecir(modelo, nombre: str, marca: str | None = None):
    """Devuelve (estado, probabilidad) aplicando el umbral asimétrico.

    Si la confianza no alcanza para el estado predicho, devuelve `revisar`:
    la regla de seguridad manda por encima de la clase más probable.
    """
    import numpy as np

    probas = modelo.predict_proba([_texto(nombre, marca)])[0]
    idx = int(np.argmax(probas))
    estado = modelo.classes_[idx]
    p = float(probas[idx])

    if estado == config.APTO and p < config.ML_APTO_MIN_PROB:
        return config.REVISAR, p
    if estado != config.APTO and p < config.ML_NO_APTO_MIN_PROB:
        return config.REVISAR, p
    return estado, p


def explicar(modelo, top: int = 12) -> dict[str, list[tuple[str, float]]]:
    """Palabras que más empujan cada clase. Sirve para auditar leakage."""
    import numpy as np

    vect = modelo.named_steps["tfidf"]
    clf = modelo.named_steps["clf"]
    vocab = np.array(vect.get_feature_names_out())

    salida = {}
    coefs = clf.coef_
    if coefs.shape[0] == 1:  # binario: una sola fila de coeficientes
        coefs = np.vstack([-coefs[0], coefs[0]])
    for i, clase in enumerate(clf.classes_):
        orden = np.argsort(coefs[i])[::-1][:top]
        salida[clase] = [(vocab[j], round(float(coefs[i][j]), 3)) for j in orden]
    return salida


def aplicar(conn, verbose: bool = True) -> dict:
    """Corre el modelo sobre los productos en `revisar` y actualiza los que resuelve."""
    modelo = cargar_modelo()
    if modelo is None:
        return {"error": "No hay modelo entrenado. Corré --entrenar primero."}

    filas = conn.execute(
        "SELECT ean, nombre, marca FROM productos WHERE estado = ?",
        (config.REVISAR,)).fetchall()

    actualizados = 0
    ahora = db.now_iso()
    for f in filas:
        estado, p = predecir(modelo, f["nombre"], f["marca"])
        if estado == config.REVISAR:
            continue
        conn.execute(
            "UPDATE productos SET estado = ?, fuente_decision = ?, confianza = ?,"
            " motivo = ?, actualizado = ? WHERE ean = ?",
            (estado, FUENTE_ML, round(p, 4),
             f"Estimado por clasificador automático a partir del nombre "
             f"(confianza {p:.0%})", ahora, f["ean"]))
        conn.execute("DELETE FROM revision_pendiente WHERE ean = ?", (f["ean"],))
        actualizados += 1

    if db.has_fts5(conn):
        conn.execute("INSERT INTO productos_fts(productos_fts) VALUES('rebuild')")
    conn.commit()
    return {"evaluados": len(filas), "resueltos": actualizados,
            "siguen_en_revisar": len(filas) - actualizados}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entrenar", action="store_true")
    parser.add_argument("--aplicar", action="store_true")
    parser.add_argument("--explicar", action="store_true")
    args = parser.parse_args(argv)

    conn = db.connect()
    db.init_db(conn)
    try:
        if args.entrenar:
            rep = entrenar(conn)
            if "error" in rep:
                print(rep["error"])
                return 1
            print(f"Entrenado con {rep['entrenamiento']} ejemplos, "
                  f"hold-out de {rep['holdout']}.")
            print(f"Clases: {rep['clases']}")
            m = rep["metricas"]
            print(f"\nAccuracy: {m['accuracy']:.3f}   "
                  f"F1 macro: {m['macro avg']['f1-score']:.3f}")
            print("\nPor clase:")
            for clase in rep["matriz_confusion"]["etiquetas"]:
                d = m[clase]
                print(f"  {clase:12} P={d['precision']:.3f} R={d['recall']:.3f} "
                      f"F1={d['f1-score']:.3f}  (n={int(d['support'])})")
            print("\nMatriz de confusión (filas = real, columnas = predicho):")
            etiquetas = rep["matriz_confusion"]["etiquetas"]
            print(f"  {'':12} " + " ".join(f"{e:>12}" for e in etiquetas))
            for e, fila in zip(etiquetas, rep["matriz_confusion"]["matriz"]):
                print(f"  {e:12} " + " ".join(f"{v:>12}" for v in fila))
            (config.DATA_DIR / "modelo_reporte.json").write_text(
                json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")

        if args.explicar:
            modelo = cargar_modelo()
            if modelo is None:
                print("No hay modelo entrenado.")
                return 1
            print("\nPalabras que más empujan cada clase:")
            for clase, palabras in explicar(modelo).items():
                print(f"\n  {clase}:")
                for palabra, peso in palabras:
                    print(f"    {peso:+.3f}  {palabra}")

        if args.aplicar:
            rep = aplicar(conn)
            if "error" in rep:
                print(rep["error"])
                return 1
            print(f"\nCapa 3: {rep['evaluados']} productos en `revisar`, "
                  f"{rep['resueltos']} resueltos por el modelo, "
                  f"{rep['siguen_en_revisar']} siguen pendientes.")

        if not (args.entrenar or args.aplicar or args.explicar):
            parser.print_help()
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
