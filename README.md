# buscavegan

Buscador de productos **aptos veganos** que se venden en Argentina, con
transparencia sobre **cómo se determinó** cada clasificación.

La clasificación se apoya, en este orden, en:

1. El **registro oficial de ANMAT** de productos con atributo vegano autorizado.
2. La **declaración del fabricante** en el packaging.
3. El **análisis de la lista de ingredientes** — la señal principal.
4. Un **clasificador entrenado sobre nombres**, para lo que no publica ingredientes.

La especificación completa está en [SPEC.md](SPEC.md).

## Qué significa "apto" acá

**"Apto" = vegano**: sin ingredientes ni derivados de origen animal.

**No** significa *cruelty-free* en sentido estricto. "Cruelty-free" (no testeado
en animales) es un atributo de cosmética y **no está presente en ninguna de las
fuentes de datos de alimentos que usa este proyecto**. Si un producto aparece
como `apto`, eso dice algo sobre sus ingredientes, no sobre la política de
testeo del fabricante.

## Estados

| Estado | Significado |
|---|---|
| `apto` | Vegano según la certificación, el fabricante, los ingredientes o el modelo |
| `vegetariano` | Sin carne, pero con derivados animales (lácteos, huevo, miel) |
| `no_apto` | Contiene ingredientes de origen animal |
| `revisar` | **Sin datos suficientes.** No es "no apto": es "no sabemos" |

**Regla de seguridad:** ante cualquier ambigüedad se asigna `revisar`, nunca
`apto`. Un falso positivo (marcar vegano algo que no lo es) es mucho más grave
que un falso negativo, y por eso el umbral para afirmar `apto` es más exigente
que el de cualquier otro estado.

## Estado actual de los datos

Números de la última corrida completa (`python sprint0.py`):

| Métrica | Valor |
|---|---|
| Productos argentinos en la base | **13.015** |
| Con lista de ingredientes | 4.161 (32,0%) |
| **Clasificados** | **5.202 (40,0%)** |
| En `revisar` | 7.813 (60,0%) |

Por fuente de la decisión:

| Fuente | Productos |
|---|---|
| Análisis de ingredientes | 3.073 |
| Heurística de nombre | 1.149 |
| Clasificador automático | 702 |
| Declarado por el fabricante | 125 |
| Certificación oficial de ANMAT | 97 |
| Análisis propio de Open Food Facts | 56 |

## Fuentes

| Fuente | Qué aporta | Estado |
|---|---|---|
| **Open Food Facts** | Catálogo argentino + ingredientes | ✅ Automatizada |
| **ANMAT / INAL** | Registro oficial de atributo vegano (668 productos) | ✅ Automatizada |
| **SEPA / Precios Claros** | Precios de góndola | ⏸️ Sin ingredientes; el portal bloquea bots |
| **Todo Vegan / V-Label** | Catálogo certificado V-Label | ❌ App-only, sin API pública |

El detalle de cómo se llega al endpoint de ANMAT y por qué V-Label quedó
descartada está en [SPEC.md](SPEC.md) §2.3.

## Limitaciones conocidas

- **El 60% del catálogo queda en `revisar`**, casi siempre porque el producto no
  tiene ingredientes cargados en Open Food Facts. Se muestran igual: la
  incompletitud es parte de lo que hay que comunicar, no algo a esconder.
- **El clasificador automático memoriza marcas.** Al entrenarse con nombres,
  aprende que ciertas marcas hacen ciertos productos; una marca que fabrica
  tanto veganos como no veganos le sale mal. También arrastra correlaciones
  espurias del catálogo (por ejemplo, asocia "frutilla" con `no_apto` porque
  casi toda la frutilla que hay son yogures y gelatinas). Por eso sus
  predicciones se muestran siempre marcadas como estimadas y con su confianza.
- **La certificación de ANMAT no trae EAN**, así que el cruce es por marca +
  nombre y es deliberadamente estricto: prefiere no matchear antes que matchear
  de más.
- La heurística de nombre trabaja sobre el nombre comercial, que suele ser
  incompleto. No reemplaza leer la etiqueta.

## Uso

```bash
pip install -r requirements.txt

# 1. Catálogo argentino completo desde el dump de OFF (1,3 GB en streaming)
python ingest_off_dump.py
# ...o la vía rápida, menos completa (~1 min)
python ingest_off_ar.py

# 2. Registro oficial de ANMAT (Capa 0)
python ingest_anmat.py

# 3. Clasificar (Capas 0 a 2) y armar la base final con su índice de búsqueda
python build_db.py

# 4. Capa 3: entrenar el clasificador, auditarlo y aplicarlo
python classify_ml.py --entrenar --explicar --aplicar

# 5. Ver la cobertura conseguida
python sprint0.py

# 6. Levantar la app
streamlit run app.py
```

Todo el pipeline de una sola vez:

```bash
python refresh.py              # refresco normal (API rápida)
python refresh.py --completo   # incluye el dump entero de OFF
```

## Frecuencia de refresco

`refresh.py` está pensado para cron o un workflow programado de GitHub Actions.
Lo caro es traer datos, no clasificar: el refresco normal usa la API rápida y
tarda un par de minutos, mientras que `--completo` baja el dump entero y
conviene semanal o mensual. Las respuestas de OFF se cachean en SQLite con un
TTL de 60 días (`OFF_CACHE_TTL_DAYS`), así que los refrescos posteriores solo
consultan por productos nuevos o vencidos. Todo se configura en
[config.py](config.py) o por variables de entorno.

## Tests

```bash
python -m pytest tests -q
```

72 tests, incluidos los 11 casos obligatorios de [SPEC.md](SPEC.md) §7 y los que
verifican que la regla de seguridad no se pueda violar por ninguna capa.
