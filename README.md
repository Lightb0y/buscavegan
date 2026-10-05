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
| Productos argentinos en la base | **7.397** |
| **Clasificados** | **6.221 (84,1%)** |
| Resueltos con **evidencia real**, no inferida del nombre | 5.231 (70,7%) |
| En `revisar` | 1.176 (15,9%) |
| Confirmados en algún supermercado | 5.581 |

De un total de 13.015 entradas de OFF etiquetadas "Argentina", se excluyeron
**5.618 (43,2%)** por no ser aprovechables: 2.583 con el nombre en un alfabeto
que ningún supermercado argentino usa, 37 con un código que no tiene longitud
de EAN/UPC real, y **2.998 fichas fantasma** (ver abajo). Ninguna se borra de
la base interna — solo no llegan a la búsqueda. Ver
[relevancia.py](relevancia.py).

Por fuente de la decisión:

| Fuente | Productos |
|---|---|
| Análisis de ingredientes (Open Food Facts) | 3.301 |
| Análisis de ingredientes (ficha del supermercado) | 1.007 |
| Heurística de nombre | 770 |
| Sello vegano de la ficha del supermercado | 682 |
| Clasificador automático | 144 |
| Declarado por el fabricante | 121 |
| Certificación oficial de ANMAT | 97 |
| Mismo producto que otro EAN ya resuelto | 81 |
| Análisis propio de Open Food Facts | 23 |

El **70,7% del catálogo se resuelve con evidencia real** —certificación,
declaración del fabricante o lista de ingredientes—, y solo el 10,4% se apoya
en adivinar por el nombre comercial. Es la métrica que más importa: el nombre
omite lo que no conviene decir, la lista de ingredientes es la declaración
legal.

## Fuentes

| Fuente | Qué aporta | Estado |
|---|---|---|
| **Open Food Facts** | Catálogo argentino + ingredientes | ✅ Automatizada |
| **ANMAT / INAL** | Registro oficial de atributo vegano (668 productos) | ✅ Automatizada |
| **Carrefour / Vea / Día / Jumbo / Disco** | Confirmación de EAN real en góndola | ✅ Automatizada ([ingest_vtex.py](ingest_vtex.py)) |
| **Vea / Jumbo / Disco** (Cencosud) | **Lista de ingredientes**, trazas y sello vegano | ✅ Automatizada ([ingest_fichas.py](ingest_fichas.py)) |
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

De la última cosecha completa, **5.581 productos** quedaron confirmados en
al menos una de las 5 cadenas.

### Ingredientes de la ficha del supermercado

La confirmación de góndola resultó ser solo la mitad del hallazgo. **Vea, Jumbo
y Disco** (las tres de Cencosud) publican en la misma API la ficha completa del
producto, y ahí está lo que más falta hacía:

- **`Ingredientes`** — la lista real del envase. Es la señal más confiable que
  tiene el proyecto, y dos tercios del catálogo no la tenían en OFF.
- **`Trazas`** — en un campo aparte, que es justo la distinción que importa:
  "puede contener leche" no es lo mismo que "contiene leche".
- **`Sellos`** — certificaciones, entre ellas un `vegan` explícito.

Carrefour y Día no exponen estos campos: se verificó producto por producto.

[ingest_fichas.py](ingest_fichas.py) las consulta por EAN (no hace falta
recosechar el catálogo entero) y es reanudable: guarda también la ficha vacía,
así una corrida cortada no vuelve a preguntar lo mismo.

Esa memoria de "ya pregunté" distingue **la cadena contestó que no lo tiene**
de **no se pudo preguntar**. Solo lo primero se guarda. Anotar "no tiene ficha"
porque se cortó la red sería escribir una conclusión que nadie sacó, y en una
corrida de horas contra 85.000 productos un corte de un minuto dejaría cientos
marcados así para siempre, sin forma de distinguirlos después. Si la cadena
deja de responder 25 veces seguidas, la corrida se corta sola: lo cosechado
queda y la próxima sigue donde esta terminó.

El sello vegano se acepta como `apto` **solo si la lista de ingredientes de esa
misma ficha no lo contradice**. Si se contradicen, alguien se equivocó y el
producto va a `revisar`: la regla de seguridad pesa más que una etiqueta.

**Un producto que solo existe en la góndola** —de los 96.247 códigos que las
cadenas publican y OFF nunca vio— entra al catálogo si, y solo si, su ficha lo
respalda con una lista de ingredientes o un sello. Estar en una góndola no
alcanza: de un producto del que solo se sabe el nombre, el veredicto sería una
adivinanza, y sumar decenas de miles de adivinanzas haría el catálogo más
grande y el sitio peor.

Cuánto rinde depende casi por completo de **quién imprimió el código**. Medido
sobre las primeras 27.206 fichas de la cosecha:

| Código | Consultadas | Con ingredientes |
|---|---|---|
| De fabricante (prefijo 7, casi todos 779 = Argentina) | 8.931 | **37,1%** |
| De circulación restringida (prefijo 2) | 18.366 | **0,1%** |

Los de prefijo 2 los imprime el propio supermercado para lo que pesa o
fracciona —fiambre al corte, verdura suelta—: no tienen fabricante, y casi
nunca ficha. La cola los pedía primero solo porque estaba ordenada por EAN, y se
llevaron dos tercios de las consultas. Ahora van al final. (Dos estimaciones
anteriores, 72% y 18,4%, estaban sacadas de poblaciones que no eran la cola:
la primera, de productos que OFF ya conocía; la segunda, de una muestra que
mezclaba los dos tipos de código.)

**Lo cosechado se versiona** en [COSECHA/fichas.ndjson](COSECHA/fichas.ndjson),
vacías incluidas. La base es derivada —en CI vive en un cache que vence— y la
cosecha completa son horas de consultas: si viviera solo ahí, perderla sería
rehacerla, y lo cosechado en una máquina nunca llegaría al refresco de CI, que
es el que publica el sitio. Cada corrida de `ingest_fichas.py` o de
`refresh.py` arranca cargando ese archivo y termina reescribiéndolo, y el
workflow lo commitea junto con los datos del sitio.

## Marcas y categorías

Dos arreglos que no cambian ningún veredicto pero sí lo que se encuentra y lo
que se puede explorar.

**Marcas** ([marcas.py](marcas.py)). El campo `brands` de OFF lo carga la
comunidad a mano: 399 marcas se escribían de más de una forma y entre todas se
llevaban 3.751 productos, la mitad del catálogo. "La Serenísima" tenía diez
grafías, incluida una donde alguien guardó el `repr` de una lista de Python.
Quien buscaba la marca con tilde veía la mitad de los resultados.

Las variantes se agrupan ignorando mayúsculas, tildes y puntuación, y se elige
una grafía para mostrar: ni todo mayúsculas ni todo minúsculas (eso además
preserva "NotCo" y "SanCor", que una regla de capitalizar cada palabra
rompería), y con tilde antes que sin tilde cuando la acentuada tiene respaldo
real — un solo producto con "Alícante" contra 16 con "Alicante" es una errata,
no la grafía correcta.

El voto se hace sobre las grafías de OFF y no sobre las del supermercado: las
cadenas publican casi todo en mayúsculas (3.015 "ARCOR") y ganarían por volumen
sin aportar nada. Lo que sí aporta la góndola es la marca de los productos que
no la tenían: la publica para el 100% de lo suyo, contra el 83% de OFF.

Resultado: **2.461 marcas → 2.043**, y los productos sin marca **de 1.258 a
396**.

**Categorías** ([categorias.py](categorias.py)). El 40% del catálogo caía en
"Otros" — la categoría más grande del sitio era la que no dice nada. El rubro
salía de una sola fuente, los `categories_tags` de OFF, que para ese 40% están
vacíos. Ahora sale de tres, en orden de precisión:

1. Los tags de OFF, que es una taxonomía curada.
2. **El nombre del producto**, que es lo que rescata la mayoría.
3. El rubro de góndola del supermercado, como último recurso.

El orden no es el obvio: **el nombre le gana a la góndola**. 110.703 productos
están en "Almacén", que es el cajón de sastre de las cinco cadenas y no
significa nada, mientras que el nombre dice "Galletitas 9 de Oro" o "Mayonesa"
y con eso alcanza. Solo se mapean las góndolas que designan un rubro sin
ambigüedad: "Bebidas" no distingue un vino de un agua y queda afuera.

Resultado: **"Otros" pasó de 40,1% a 11,7%**.

Dos reglas que la medición contra el catálogo real obligó a escribir:

- **El nombre de una fruta casi nunca es el producto, es el sabor.** La primera
  versión mandaba "Gatorade manzana" y "yogur frutilla" a "Frutas y verduras".
- **Ningún plant-based puede caer en un rubro de origen animal.** Una milanesa
  de soja no va a "Carnes y fiambres" ni una leche de almendras a "Lácteos":
  en este sitio ese error se ve de lejos.

## Calidad de los datos: filtrado y deduplicación

Tres correcciones que corren dentro de `build_db.py`, no como pasos aparte:

- **Fichas fantasma** ([relevancia.es_ficha_fantasma](relevancia.py)): Open
  Food Facts se llena escaneando códigos de barras, y muchas entradas quedan
  con un nombre y nada más. Como comparte el pool de códigos con Open Beauty
  Facts, terminaban colándose shampoos, cremas, cigarrillos y hasta un
  medicamento cardíaco en un catálogo de alimentos. Medido: el **80% de lo que
  quedaba en `revisar` no tenía ni siquiera categoría**, y de ese grupo solo el
  35% tenía código de barras argentino (contra el 79% de los productos que sí
  se podían clasificar).

  El criterio para descartarlas exige las **cuatro** condiciones a la vez: sin
  categoría, sin ingredientes, sin presencia en ninguna góndola real y sin
  veredicto fundado. Con que el producto tenga **una sola** señal, se queda.
  La versión ingenua —cortar solo por "no tiene categoría"— se llevaba puestos
  1.608 productos bien clasificados, entre ellos 457 con sello vegano
  certificado: sería tirar evidencia por falta de una etiqueta. Con el criterio
  estrecho se excluyen 2.998 productos y **no se pierde ninguno con evidencia
  real**.

- **Relevancia geográfica** ([relevancia.py](relevancia.py)): OFF es
  colaborativo y el tag de país lo carga quien sube el producto, así que
  aparecen productos que casi seguro no se venden en Argentina. La señal más
  clara: el nombre en un alfabeto que ningún supermercado argentino usa
  (árabe, hebreo, cirílico...). Antes de este filtro, esas entradas eran el
  **20% del catálogo** y explicaban el **39% de todo el bucket `revisar`** —
  no era falta de datos, era que no correspondían a este catálogo. Se
  excluyen de la búsqueda pero no se borran de la base interna: si el
  criterio cambia, el dato sigue disponible.
- **Lo que no es un alimento**
  ([relevancia.es_no_alimento](relevancia.py)): OFF comparte el pool de códigos
  con Open Beauty Facts, así que un shampoo entra a la base igual que un yogur.
  Mientras todo eso caía en "Otros" molestaba poco; desde que el rubro se
  deduce también del nombre, "Agua micelar" se iba a "Bebidas sin alcohol" y un
  bálsamo labial figuraba como `apto`. Un cosmético disfrazado de alimento
  clasificado es peor que un cosmético sin clasificar.

  El criterio es angosto a propósito: solo palabras que **nunca** nombran un
  alimento. Nada de "crema", "leche" o "manteca" sueltas, que son comida
  bastante más seguido que cosmética; y tampoco marcas, porque Dove también es
  una marca de chocolate. Corriendo el filtro contra el catálogo entero antes
  de activarlo apareció el error que ninguna lectura del código iba a mostrar:
  "colonia" matcheaba dentro de "Dulce de Leche Estilo **Colonial**" y se
  llevaba puestos cuatro dulces de leche y un chocolate. Con los dos bordes de
  palabra puestos, el filtro saca **70 fichas y ningún alimento**.

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
[tests/test_falsos_positivos.py](tests/test_falsos_positivos.py).

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

- **Queda un 16% del catálogo en `revisar`**, y buena parte ya no se arregla
  con más datos: de los que sí tienen ingredientes cargados, la mitad está ahí
  por un ingrediente genuinamente ambiguo (lecitina, INS 471, margarina,
  vitamina D3), donde afirmar `apto` violaría la regla de seguridad. Se
  muestran igual: la incompletitud es parte de lo que hay que comunicar, no
  algo a esconder. Para el resto está la cola de revisión manual (ver abajo).
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

# 3b. Ficha con la lista de ingredientes que publican Vea, Jumbo y Disco.
#     Es la cosecha grande: ~85.000 fichas, ~12 h a 0,49 s por consulta.
#     Es reanudable de verdad — se puede cortar en cualquier momento y seguir
#     después, y se corta sola si la cadena deja de responder. Arranca
#     cargando COSECHA/fichas.ndjson y termina reescribiéndolo: commitealo.
python ingest_fichas.py
#     Para probar sin comprometerse a la corrida entera:
python ingest_fichas.py --limite 200
#     Para cargar en una base nueva lo ya cosechado, sin consultar a nadie:
python ingest_fichas.py --solo-sincronizar

# 4. Clasificar (Capas 0 a 2) y armar la base final con su índice de búsqueda
python build_db.py

# 5. Capa 3: entrenar el clasificador, auditarlo y aplicarlo
python classify_ml.py --entrenar --explicar --aplicar

# 6. Ver la cobertura conseguida
python sprint0.py

# 7. Capa 4: curar a mano. Dos colas, y la segunda es la que más urge.
python revision.py --exportar               # los `revisar`, ordenados por impacto
python revision.py --exportar --riesgo      # los `apto` que solo se apoyan en el nombre
python revision.py --importar data/revision_pendiente.csv

#    El CSV también lo puede armar el panel del sitio (/panel/), buscando el
#    producto y eligiéndole el veredicto. Baja el archivo con estas mismas
#    columnas y entra por el mismo --importar.

# 8. Levantar la app interna de revisión
streamlit run app.py

# 9. Exportar lo que consume el sitio público
python export_web.py
```

Todo el pipeline de una sola vez:

```bash
python refresh.py              # refresco normal (API rápida + un pedazo de fichas)
python refresh.py --completo   # además: dump entero de OFF y catálogo de góndola
python refresh.py --fichas 0   # sin pedir fichas en esta corrida
python refresh.py --sin-gondola  # sin tocar a los supermercados
```

### Las dos colas de curaduría

`--exportar` saca los `revisar`: lo que el sistema no pudo decidir. Es la cola
larga, y la que se ve en el sitio.

`--exportar --riesgo` saca la otra, que es más corta y más cara de dejar sin
mirar: los productos que hoy se muestran como **apto** apoyados únicamente en
su nombre comercial —la heurística o el modelo—, sin que nadie haya leído la
etiqueta. Son 385. Un `revisar` que en realidad era `apto` solo esconde un
producto bueno; un `apto` que en realidad era otra cosa es exactamente el error
que la regla de seguridad existe para evitar. Si hay una tarde para curar, va
en esta cola.

### Por qué las correcciones se versionan

La tabla `correcciones` vive en la base, y la base es derivada: no se versiona,
y en CI se restaura de un cache que puede vencer. Si una decisión humana
viviera solo ahí, una corrida sin cache la borraría sin que nadie se entere.

Por eso los CSV curados se guardan en [CORRECCIONES/](CORRECCIONES/) y
`refresh.py` los reimporta en **cada** corrida. Reimportar es idempotente, así
que el archivo se puede leer cien veces sin efecto. La base se puede tirar
entera y rearmar: esos archivos son la copia de la que se rearma.

## Las dos caras del proyecto

| | Para qué | Cómo se levanta |
|---|---|---|
| **[web/](web/)** — sitio público | Buscar un producto y ver el veredicto con su evidencia. Next.js estático en Vercel. | `cd web && npm run dev` |
| **[app.py](app.py)** — herramienta interna | Auditar la cola de `revisar`, probar cambios del léxico contra la base real sin republicar nada. | `streamlit run app.py` |

El sitio no consulta la base: `export_web.py` escribe `web/data/` y el build
genera una página estática por producto. El catálogo entero pesa 236 KB
comprimidos, así que la búsqueda corre en el navegador sin backend. El detalle
está en [web/README.md](web/README.md).

## Frecuencia de refresco

`refresh.py` está pensado para cron o un workflow programado de GitHub Actions;
hay uno listo en [.github/workflows/refresh.yml](.github/workflows/refresh.yml),
con refresco semanal por API y completo el día 1 de cada mes.
Lo caro es traer datos, no clasificar: el refresco normal usa la API rápida y
tarda un par de minutos, mientras que `--completo` baja el dump entero y
conviene semanal o mensual.

El dato de góndola entra en dos velocidades, porque son dos cosas distintas y
no cuestan lo mismo. **El catálogo** (qué EAN se vende hoy en cada cadena)
obliga a recorrer el árbol de categorías entero de las cinco cadenas: es caro,
cambia despacio, y va solo en `--completo`. **Las fichas** (la lista de
ingredientes del envase) se piden de a un EAN y el proceso es reanudable, así
que van en cada corrida con un presupuesto acotado —`FICHAS_POR_CORRIDA`, por
defecto 1.500— que se lleva un pedazo de la cola y deja el resto para la
próxima. Si una cadena se cae, el paso avisa y el refresco sigue con la última
cosecha buena. Las respuestas de OFF se cachean en SQLite con un
TTL de 60 días (`OFF_CACHE_TTL_DAYS`), así que los refrescos posteriores solo
consultan por productos nuevos o vencidos. Todo se configura en
[config.py](config.py) o por variables de entorno.

## Tests

```bash
python -m pytest tests -q
```

343 tests, incluidos los 11 casos obligatorios de [SPEC.md](SPEC.md) §7, los que
verifican que la regla de seguridad no se pueda violar por ninguna capa, y los
falsos positivos concretos que fueron apareciendo al revisar a mano la salida
real del pipeline (por ejemplo "Yogurisimo Banana", que llegó a clasificarse
como apto porque el blacklist busca palabras enteras y "yogur" no matchea
dentro de "Yogurisimo").

Los de [tests/test_falsos_positivos.py](tests/test_falsos_positivos.py) son
todos errores reales que el clasificador cometía, no casos hipotéticos: cada uno
se verificó contra la base antes de escribir la corrección. Los de
[tests/test_fantasmas.py](tests/test_fantasmas.py) verifican sobre todo lo que
el filtro NO debe excluir, que es donde está el riesgo.
