# SPEC — Buscador de productos Plant-Based / Cruelty-Free (Argentina)

## 0. Objetivo

Aplicación web donde un usuario busca un producto que se vende en supermercados
argentinos y descubre **si es apto vegano / vegetariano**, con transparencia sobre
**cómo se determinó** esa clasificación.

Fuentes cruzadas:

- **SEPA / Precios Claros** — catálogo real de lo que se vende en Argentina (marca, nombre, EAN, precio).
- **Open Food Facts (OFF)** — análisis de ingredientes que determina el estado vegano/vegetariano.

**Aclaración de terminología:** "cruelty-free" en sentido estricto aplica a cosmética
(no testeo en animales) y NO está en fuentes de alimentos. Acá "apto" = **vegano**
(sin ingredientes ni derivados animales) según el análisis de OFF.

---

## 1. Alcance

| Decisión | Valor |
|---|---|
| Cobertura geográfica | Catálogo nacional completo |
| Actualización | Refresco periódico (pipeline reproducible) |
| Fuente de catálogo | SEPA |
| Fuente de clasificación | Open Food Facts API v2 |
| Clave de cruce | EAN (`producto_id` en SEPA == `code` en OFF) |
| Regla de seguridad | Ante duda → `revisar`, nunca `apto` |

---

## 2. Fuentes de datos

### 2.1 SEPA / Precios Claros
- Dataset oficial: `datos.produccion.gob.ar/dataset/sepa-precios` — el portal bloquea acceso
  automatizado (bot detection). Descarga manual o vía mirror. NO scrapear el portal directo.
- Scraper open source: `github.com/OpenDataCordoba/precios_claros`
- Mirror Kaggle: `tinnqn/precios-claros-precios-de-argentina`
- Provee: `producto_id` (EAN), marca, nombre, categorías (a veces), precio, cadena, provincia.
- NO provee: ingredientes ni tabla nutricional → por eso se cruza con OFF.

### 2.2 Open Food Facts API v2
- Base URL: `https://world.openfoodfacts.org`
- `GET /api/v2/product/{ean}.json?fields=...`
- Sin API key para lectura. Requiere `User-Agent` descriptivo propio.
- Rate limit: HTTP 503 al excederse → cachear obligatorio.
- Campos: `code`, `ingredients_analysis_tags`, `labels_tags`, `ingredients_text`,
  `categories_tags`, `product_name`, `brands`, `image_front_small_url`.

---

## 3. Sprint 0 (obligatorio)

Medir el **match rate** OFF sobre una muestra de ~500 EANs antes de construir las 4 capas.

- match rate > 25% → buen training set para el clasificador ML (Capa 3 fuerte)
- match rate < 10% → la heurística (Capa 2) es el caballo de batalla

---

## 4. Pipeline de clasificación (4 capas)

### Capa 1 — Match directo por EAN
- `labels_tags` contiene `en:vegan` → **apto** (`off_label`, confianza máxima)
- `ingredients_analysis_tags` contiene `en:vegan` → **apto** (`off_analysis`)
- contiene `en:non-vegan` → **no_apto**
- `en:vegetarian` (sin vegan) → **vegetariano**
- unknown / maybe / sin match → Capa 2

### Capa 2 — Heurística nombre + categoría
Blacklist de keywords no-veganas, whitelist de modificadores vegetales que anulan el match
dentro de una ventana de ~3 palabras. Normalizar a minúsculas y sin tildes. Límites de palabra.
Rubros inequívocos se clasifican por categoría. Sin match claro → Capa 3.

### Capa 3 — Clasificador ML (weak supervision)
TF-IDF (`ngram_range=(1,2)`) sobre nombre + marca, LogisticRegression, entrenado con lo
etiquetado con alta confianza en Capa 1. Output: predicción + probabilidad.

### Capa 4 — Cola de revisión manual
Probabilidad ambigua (0.4 ≤ p ≤ 0.6) → tabla `revision_pendiente`, mostrado como `revisar`.

**Regla de seguridad transversal:** ante ambigüedad → `revisar`, nunca `apto`.

---

## 5. Refresco

SEPA se re-descarga por corrida; cache OFF persistente en SQLite (`off_cache`, PK = EAN,
TTL configurable 30–90 días); reclasificación local barata; reentrenamiento cada N refrescos.
Orquestación por cron / APScheduler / GitHub Actions.

---

## 6. UX (Streamlit)

Campo único (nombre / marca / EAN), búsqueda con SQLite FTS5, filtros por estado y categoría,
card por producto con veredicto visual y **fuente de la decisión** (transparencia).
Productos sin datos se muestran como `revisar`, no se ocultan.

---

## 7. Casos de test obligatorios (Capa 2)

| Input | Esperado |
|---|---|
| Leche de coco Vitacoco 1L | apto / revisar (no no_apto) |
| Leche entera La Serenísima 1L | no_apto |
| Milanesa de soja Granja del Sol | apto |
| Milanesa de carne vacuna | no_apto |
| Queso untable vegano NotCo | apto |
| Queso cremoso Tregar | no_apto |
| Manteca de maní Naturalia | apto / revisar |
| Manteca La Paulina 200g | no_apto |
| Hamburguesa plant based | apto |
| Yogur de soja Ades | apto |
| Fideos al huevo Matarazzo | no_apto |

---

## 8. Módulos

```
config.py  ingest_sepa.py  enrich_off.py  classify_rules.py
classify_ml.py  build_db.py  refresh.py  app.py  tests/  data/
```

### Esquema `productos`
`ean` PK, `nombre`, `marca`, `categoria`, `estado`, `fuente_decision`, `confianza`,
`ingredients_text`, `imagen_url`, `precio_ref`, `actualizado`. Más FTS5 sobre (nombre, marca).

---

## 9. Checklist de calidad

- [ ] Sprint 0: match rate medido antes del pipeline completo.
- [ ] `enrich_off.py` respeta rate limit (backoff ante 503) y usa User-Agent propio.
- [ ] Cache OFF: 2ª corrida no re-consulta EANs cacheados.
- [ ] `test_rules.py` pasa todos los casos de §7.
- [ ] Ningún producto llega a `apto` por ausencia de datos.
- [ ] Modelo: matriz de confusión + revisión de coeficientes.
- [ ] App muestra `fuente_decision` en cada resultado.
- [ ] README documenta el alcance de "apto", cobertura y frecuencia de refresco.
