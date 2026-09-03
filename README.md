# buscavegan

Buscador de productos **aptos veganos** que se venden en Argentina, con
transparencia sobre **cómo se determinó** cada clasificación.

La clasificación se apoya, en este orden, en:

1. El **registro oficial de ANMAT** de productos con atributo vegano autorizado.
2. La **declaración del fabricante** en el packaging.
3. El **análisis de la lista de ingredientes** — la señal principal.
4. Un **clasificador entrenado sobre nombres**, para lo que no publica ingredientes.

Y por encima de todo eso, la **corrección humana**: lo que una persona revisa a
mano queda guardado aparte y sobrevive a los refrescos, así que curar la base no
es trabajo que se pierda en la próxima corrida.

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
| Productos argentinos en la base | **10.395** |
| **Clasificados** | **6.426 (61,8%)** |
| En `revisar` | 3.969 (38,2%) |
| Confirmados en algún supermercado | 5.581 (53,7%) |

De un total de 13.015 entradas de OFF etiquetadas "Argentina", se excluyeron
**2.620 (20,1%)** por no ser relevantes: 2.583 con el nombre en un alfabeto
que ningún supermercado argentino usa (probable país mal cargado en origen) y
37 con un código que no tiene longitud de EAN/UPC real. No se borran de la
base interna — solo no llegan a la búsqueda. Ver
[relevancia.py](relevancia.py).

Por fuente de la decisión:

| Fuente | Productos |
|---|---|
| Análisis de ingredientes | 3.247 |
| Heurística de nombre | 2.335 |
| Clasificador automático | 497 |
| Declarado por el fabricante | 121 |
| Mismo producto que otro EAN ya resuelto | 106 |
| Certificación oficial de ANMAT | 97 |
| Análisis propio de Open Food Facts | 23 |

## Fuentes

| Fuente | Qué aporta | Estado |
|---|---|---|
| **Open Food Facts** | Catálogo argentino + ingredientes | ✅ Automatizada |
| **ANMAT / INAL** | Registro oficial de atributo vegano (668 productos) | ✅ Automatizada |
| **Carrefour / Vea / Día / Jumbo / Disco** | Confirmación de EAN real en góndola | ✅ Automatizada ([ingest_vtex.py](ingest_vtex.py)) |
| **SEPA / Precios Claros** | Precios de góndola | ⏸️ Portal bloquea bots; la API en vivo del gobierno está caída |
| **Todo Vegan / V-Label** | Catálogo certificado V-Label | ❌ App-only, sin API pública |

El detalle de cómo se llega al endpoint de ANMAT y por qué V-Label quedó
descartada está en [SPEC.md](SPEC.md) §2.3.

### Confirmación cruzada con supermercados

Carrefour, Vea, Día, Jumbo y Disco corren todos sobre VTEX, una plataforma de
e-commerce que expone su catálogo por una API pública y sin autenticación (la
misma que usa su propio sitio). [ingest_vtex.py](ingest_vtex.py) recorre el
árbol de categorías de alimentos de cada cadena y guarda qué EAN están
realmente en góndola hoy, con marca, categoría y precio.

Esto **no cambia ningún veredicto**: es una señal aparte, mostrada en la app
como "🛒 Confirmado en: Carrefour, Vea". Confirmar presencia es evidencia
fuerte de que el producto existe; su ausencia en estas 5 cadenas **no**
implica que no se venda en Argentina (hay miles de comercios más, empezando
por Coto, que no corre VTEX). Por eso queda como filtro opcional en la app
("Solo confirmados en supermercados conocidos"), no como exclusión automática.

De la última cosecha completa: **5.581 de los 10.395 productos (53,7%)**
quedaron confirmados en al menos una de las 5 cadenas.

## Calidad de los datos: filtrado y deduplicación

Dos correcciones que corren dentro de `build_db.py`, no como pasos aparte:

- **Relevancia geográfica** ([relevancia.py](relevancia.py)): OFF es
  colaborativo y el tag de país lo carga quien sube el producto, así que
  aparecen productos que casi seguro no se venden en Argentina. La señal más
  clara: el nombre en un alfabeto que ningún supermercado argentino usa
  (árabe, hebreo, cirílico...). Antes de este filtro, esas entradas eran el
  **20% del catálogo** y explicaban el **39% de todo el bucket `revisar`** —
  no era falta de datos, era que no correspondían a este catálogo. Se
  excluyen de la búsqueda pero no se borran de la base interna: si el
  criterio cambia, el dato sigue disponible.
- **Duplicados por EAN** ([build_db.\_propagar_duplicados](build_db.py)): OFF
  no fuerza un EAN único por producto, así que el mismo producto puede
  aparecer varias veces con códigos distintos — a veces con los ingredientes
  cargados en una entrada y no en la otra. El caso que lo dejó en evidencia:
  buscar "Oreo" devolvía EANs con veredictos contradictorios (`apto`,
  `vegetariano` y `revisar` al mismo tiempo para el mismo producto). Ahora,
  dentro de un mismo nombre + marca, todos los EANs quedan en el estado más
  restrictivo que tenga evidencia real — con una regla explícitamente
  asimétrica: un `apto` nunca se contagia hacia un hermano en `revisar` (eso
  sería inventar un veredicto positivo de la nada), pero un `no_apto` o
  `vegetariano` sí, porque ahí equivocarse para el lado cauto es el error
  barato.

## Auditoría del léxico contra las fuentes oficiales

El léxico de ingredientes se auditó cruzándolo contra dos fuentes que mandan
sobre nuestra opinión: la **taxonomía oficial de Open Food Facts** (de donde
salen los ingredientes) y el **Código Alimentario Argentino**. Aparecieron 22
errores reales, corregidos y fijados con tests en
[tests/test_falsos_positivos.py](tests/test_falsos_positivos.py). El detalle
en lenguaje llano está en [CORRECCIONES.md](CORRECCIONES.md).

Los tres hallazgos que más movieron la aguja:

- **Oleomargarina.** El CAA (art. 545) la define *únicamente* como bovina u
  ovina: es una fracción de la grasa de faena y no existe versión vegetal del
  término. Nosotros solo detectábamos "oleomargarina **bovina**", así que la
  palabra a secas pasaba de largo: **24 productos se estaban mostrando como
  aptos veganos** cuando no lo son.
- **Margarina y grasa hidrogenada.** El CAA (arts. 551 y 548) permite que
  ambas lleven grasa animal — la margarina admite además hasta 5% de grasa de
  leche, leche en polvo, suero y caseinato. Sin el calificativo "vegetal" no
  se puede afirmar nada: pasaron a `revisar`.
- **Lisozima (INS 1105).** Es el único conservante de uso corriente de origen
  animal (se extrae de la clara de huevo). Además, el código de 4 dígitos se
  truncaba a 3 y matcheaba como si fuera "INS 110", con lo cual se contaba
  como aditivo vegano reconocido.

Sobre la pregunta de si las fuentes resuelven el caso de la oleomargarina a
secas: **no**. La taxonomía de OFF tiene una sola entrada, `oleomargarina
bovina` (marcada `vegan:no`), y no define nada para el término sin
calificativo; `en:margarine` directamente no tiene propiedad `vegan`. Es decir
que OFF no se pronuncia y el criterio hay que ponerlo desde el CAA.

## Limitaciones conocidas

- **Sigue quedando un 38% del catálogo en `revisar`**, casi siempre porque el
  producto no tiene ingredientes cargados en Open Food Facts. Se muestran
  igual: la incompletitud es parte de lo que hay que comunicar, no algo a
  esconder. Para bajar ese número está la cola de revisión manual (ver abajo).
- **La búsqueda todavía puede mostrar varias tarjetas para el mismo producto**
  (EANs distintos de "Oreo", por ejemplo). Desde esta corrida ya no se
  contradicen entre sí, pero agruparlas en una sola tarjeta por producto es
  un cambio de interfaz que todavía no se hizo.
- El filtro de relevancia es deliberadamente conservador: solo excluye por
  señales objetivas (alfabeto del nombre, longitud de EAN imposible), nunca
  por una sospecha de "esto no parece argentino". Puede dejar pasar ruido más
  sutil (ej. un producto europeo con nombre en español que nunca se
  distribuyó acá).
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

# 3. Confirmación cruzada con supermercados (opcional, tarda: ~275k productos)
python ingest_vtex.py

# 4. Clasificar (Capas 0 a 2) y armar la base final con su índice de búsqueda
python build_db.py

# 5. Capa 3: entrenar el clasificador, auditarlo y aplicarlo
python classify_ml.py --entrenar --explicar --aplicar

# 6. Ver la cobertura conseguida
python sprint0.py

# 7. Capa 4: curar a mano lo que quedó pendiente
python revision.py --exportar               # CSV ordenado por impacto
python revision.py --importar data/revision_pendiente.csv

# 8. Levantar la app
streamlit run app.py
```

Todo el pipeline de una sola vez:

```bash
python refresh.py              # refresco normal (API rápida)
python refresh.py --completo   # incluye el dump entero de OFF
```

## Frecuencia de refresco

`refresh.py` está pensado para cron o un workflow programado de GitHub Actions;
hay uno listo en [.github/workflows/refresh.yml](.github/workflows/refresh.yml),
con refresco semanal por API y completo el día 1 de cada mes.
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

255 tests, incluidos los 11 casos obligatorios de [SPEC.md](SPEC.md) §7, los que
verifican que la regla de seguridad no se pueda violar por ninguna capa, y los
falsos positivos concretos que fueron apareciendo al revisar a mano la salida
real del pipeline (por ejemplo "Yogurisimo Banana", que llegó a clasificarse
como apto porque el blacklist busca palabras enteras y "yogur" no matchea
dentro de "Yogurisimo").

Los 71 de [tests/test_falsos_positivos.py](tests/test_falsos_positivos.py) son
todos errores reales que el clasificador cometía, no casos hipotéticos: cada uno
se verificó contra la base antes de escribir la corrección.
