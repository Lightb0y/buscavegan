# Análisis FODA — buscavegan

**Fecha del análisis:** 9 de septiembre de 2026
**Estado del proyecto:** prototipo funcional con datos reales, sin usuarios medidos
**Destinatario:** inversores / evaluación de rumbo

---

## Estado de ejecución

*Actualizado el 9 de septiembre de 2026, el mismo día del análisis.*

**La Fase 1 está implementada.** Es la fase de "antes de crecer": cuatro
cambios baratos que cierran los riesgos que no convenía arrastrar. Lo que
cambió:

| Punto | Qué se hizo | Estado |
|---|---|---|
| Analítica (D8) | El sitio mide visitas y, sobre todo, **qué se buscó sin encontrar** — que es la lista de qué falta cargar, escrita por quien lo fue a buscar. Sin cookies y sin identificar a nadie. | Listo en código; falta activarlo en el panel de Vercel |
| Aviso legal (D10, A3) | Página `/legal` con límite de responsabilidad, el alcance real de "apto", la advertencia para alergias y celiaquía, la licencia de las fuentes, el canal de reporte de errores y qué se mide de la visita. Enlazada desde el pie y desde cada ficha. | Listo |
| Los 385 `apto` por nombre (D7) | `revision.py --exportar --riesgo` saca esa cola priorizada por marca, lista para curar. La revisión en sí es trabajo humano y queda pendiente. | Herramienta lista; la curaduría, pendiente |
| Góndola en el refresco (D2) | El relevamiento de supermercados dejó de ser una cosecha manual: las fichas de ingredientes entran en cada corrida con un presupuesto acotado, y el catálogo de góndola en la corrida mensual. | Listo |

Se agregó además una quinta cosa que apareció al implementar la cuarta y que
no estaba en el análisis original: **las correcciones humanas no eran
durables**. Vivían solo en la base, que no se versiona y que en la
automatización se restaura de un cache que puede vencer. Una corrida sin cache
las habría borrado en silencio —lo contrario de lo que promete la Capa 4, y
justo el activo que el punto F10 cuenta como capitalizable—. Ahora los CSV
curados se versionan y el refresco los reimporta en cada corrida.

Lo que **no** cambió: la cobertura sigue en ~5,5% y sigue sin haber un solo
dato de uso real. La Fase 1 no era para mover esos números, era para poder
medirlos y para no crecer con los riesgos abiertos. **La jugada que mueve la
aguja es la Fase 2**, y está intacta.

---

## Cómo leer este documento

Este análisis no es una presentación de venta. Es una auditoría honesta, hecha
sobre el código y sobre la base de datos real del proyecto —no sobre lo que la
documentación dice que el proyecto hace—. Cada número que aparece acá se midió
consultando directamente la base, corriendo los tests y leyendo el código.

Cuando algo es una estimación y no una medición, está marcado como tal.

Hay dos tipos de conclusiones mezcladas a propósito:

- **La idea**: si el problema vale la pena, si la solución propuesta es la
  correcta, y si hay lugar en el mercado.
- **El código**: si lo construido aguanta, si escala, y qué tan lejos está de
  ser un producto y no un experimento.

Están juntas porque en este proyecto no se pueden separar: el diferencial de la
idea *es* una decisión de ingeniería, y el techo del negocio *es* un límite
técnico.

---

## 0. Resumen ejecutivo

**Qué es:** un buscador de productos argentinos que responde "¿esto es apto
vegano?" y —lo distintivo— muestra siempre de dónde salió esa respuesta:
certificación del Estado, lista de ingredientes del envase, sello del
supermercado, o una estimación (marcada como tal).

**Lo bueno, en una línea:** el motor de clasificación es serio, está auditado
contra la ley alimentaria argentina, tiene 333 tests que pasan, y su disciplina
de "ante la duda, no afirmo" es exactamente la postura correcta para un
producto donde equivocarse tiene consecuencias reales sobre una persona.

**Lo malo, en una línea:** el catálogo cubre aproximadamente **el 5% de lo que
hay hoy en la góndola** de las cinco cadenas que el propio proyecto ya relevó.
Un usuario que busque un producto al azar, lo más probable es que no lo
encuentre.

**Lo que falta, en una línea:** no hay ninguna evidencia de demanda. Cero
analítica, cero usuarios medidos, cero validación con personas reales, y
ningún modelo de ingresos escrito en ningún lado.

**La buena noticia dentro de la mala:** la brecha de cobertura no es un
problema conceptual. El proyecto ya demostró técnicamente cómo cerrarla —solo
que todavía no lo hizo a escala—. Está explicado en la sección 4.1, y es, con
diferencia, la palanca más importante que tiene este proyecto por delante.

**Edad del proyecto:** 7 días. El primer commit es del 2 de septiembre de 2026
y hay 34 commits en total. Esto contextualiza todo lo demás: no es un producto
maduro con problemas, es un prototipo muy avanzado para su edad.

---

## 1. Fotografía del proyecto hoy (números verificados)

### 1.1 El catálogo publicado

| Métrica | Valor | Comentario |
|---|---|---|
| Productos en el sitio | **7.381** | Después de filtrar ruido |
| Apto vegano | 2.790 (37,8%) | |
| No apto | 1.776 (24,1%) | |
| Vegetariano | 1.623 (22,0%) | Sin carne, pero con lácteos/huevo |
| A revisar | 1.192 (16,1%) | "No sabemos", no "no apto" |

### 1.2 De dónde sale cada veredicto

Este es el número que el proyecto considera su métrica central, y con razón:

| Tipo de evidencia | Productos | % |
|---|---|---|
| **Evidencia real sobre el producto** | **5.180** | **70,2%** |
| — Lista de ingredientes (Open Food Facts) | 3.248 | 44,0% |
| — Lista de ingredientes (ficha de supermercado) | 999 | 13,5% |
| — Sello vegano del supermercado | 682 | 9,2% |
| — Declaración del fabricante | 121 | 1,6% |
| — Certificación oficial ANMAT | 91 | 1,2% |
| — Análisis propio de Open Food Facts | 25 | 0,3% |
| — Corrección humana | 14 | 0,2% |
| Heredado de otro código del mismo producto | 79 | 1,1% |
| **Inferido del nombre comercial** | **939** | **12,7%** |
| — Reglas sobre el nombre | 793 | 10,7% |
| — Clasificador automático | 146 | 2,0% |
| Sin datos suficientes | 1.183 | 16,0% |

**Traducción:** en 7 de cada 10 productos, la respuesta se apoya en algo que
alguien declaró legalmente (la etiqueta, un certificado). En 1 de cada 8, se
apoya en adivinar por el nombre. En el resto, el sistema dice honestamente que
no sabe.

### 1.3 El código

| Métrica | Valor |
|---|---|
| Líneas de Python (motor de datos) | ~4.980 |
| Líneas de tests | ~2.240 (45% del código productivo) |
| Tests automáticos | **333, todos pasando en 2,7 segundos** |
| Líneas del sitio web (TypeScript/React) | ~3.040 |
| Fuentes de datos automatizadas | 4 (Open Food Facts, ANMAT, catálogo de 5 cadenas, fichas de 3 cadenas) |
| Costo de infraestructura en producción | **$0** (sitio estático, sin servidor) |

### 1.4 El clasificador automático (la parte de "inteligencia artificial")

Medido sobre 886 productos que el modelo no vio durante el entrenamiento:

| Métrica | Valor | Qué significa |
|---|---|---|
| Aciertos generales | 76,9% | Se equivoca en 1 de cada 4 |
| Precisión al decir "apto" | 80,9% | **1 de cada 5 "apto" del modelo está mal** |
| Productos donde efectivamente se usa | 146 (2,0%) | Uso deliberadamente acotado |

**Lectura honesta:** el modelo es el componente más débil del sistema, y el
proyecto ya lo sabe: lo usa en apenas el 2% del catálogo, siempre marcado como
estimación. Está bien manejado, pero no es un activo. Nadie debería invertir en
este proyecto por su "IA".

---

## 2. FORTALEZAS

### 2.1 De la idea

**F1 — El problema existe, es concreto y es cotidiano.**
Hoy, una persona vegana parada frente a la góndola tiene que leer la etiqueta
letra por letra y saber qué es "caseinato", "INS 471" o "lecitina". No hay en
Argentina un lugar único donde consultar eso. No es un problema inventado para
justificar un producto.

**F2 — El posicionamiento es defendible y difícil de copiar de palabra.**
Cualquiera puede publicar una lista de productos veganos —hay decenas de
cuentas de Instagram que lo hacen—. Lo que casi nadie puede publicar es **de
dónde salió cada veredicto**. Esa trazabilidad es el producto, no un adorno. Y
es verificable: un usuario escéptico puede auditar el sistema producto por
producto, algo que ninguna lista curada permite.

**F3 — La regla de seguridad está bien elegida y bien defendida.**
El sistema nunca dice "apto" ante la duda: dice "a revisar". Esto suena a
detalle técnico y es en realidad la decisión de producto más importante que se
tomó. Un falso "es vegano" hace que una persona coma algo que no quería comer,
y destruye la confianza de forma irreversible. Un "no sé" solo molesta. El
proyecto entendió esa asimetría y la protegió con tests que verifican que
ninguna capa del sistema pueda violarla.

**F4 — Hay una fuente de autoridad legal que casi nadie está usando.**
El proyecto encontró y automatizó el registro de ANMAT de productos con
atributo vegano (668 productos certificados por trámite regulatorio, artículo
229 del Código Alimentario Argentino). No es "creemos que es vegano": es el
Estado argentino certificándolo. Llegar a ese dato requirió trabajo de
investigación real —la página lo carga por detrás desde una planilla de Google
que no está documentada en ningún lado—.

**F5 — Honestidad estructural como estrategia.**
El producto muestra su propia incompletitud en vez de esconderla. Los 1.192
productos "a revisar" se muestran, no se ocultan para que el catálogo se vea
más resuelto. En una categoría donde la confianza es todo, esto es un activo,
no una debilidad de presentación.

### 2.2 Del código y los datos

**F6 — El léxico de ingredientes está auditado contra fuentes con autoridad.**
No se armó "a ojo". Se cruzó contra la taxonomía oficial de Open Food Facts
(98.314 líneas) y contra el Código Alimentario Argentino. Aparecieron **22
errores reales** que ya estaban afectando la base publicada. El más caro:
"oleomargarina" —que por el artículo 545 del CAA es, por definición, grasa
bovina u ovina, sin versión vegetal posible— no se estaba detectando, y **24
productos se mostraban como aptos veganos sin serlo**. Cada corrección quedó
fijada con un test para que no vuelva.

Este hallazgo importa para un inversor por una razón que va más allá del caso
puntual: demuestra que el proyecto **busca activamente sus propios errores** en
vez de esperar a que un usuario los encuentre.

**F7 — La suite de tests es real, no decorativa.**
333 tests que corren en menos de 3 segundos. Y lo más valioso: los tests de
falsos positivos son **errores que el sistema efectivamente cometió** sobre la
base real, no casos hipotéticos. Ejemplo documentado: "Yogurisimo Banana" se
clasificaba como apto porque el filtro buscaba la palabra entera "yogur" y no
la encontraba dentro de "Yogurisimo".

**F8 — El costo de operación es cero y eso no es casualidad.**
El catálogo entero pesa 236 KB comprimidos. Esa sola medición define toda la
arquitectura: en vez de montar una base en la nube y una API, el navegador se
baja el catálogo completo y busca en memoria. No hay servidor que pagar ni que
mantener. Un proyecto en etapa temprana con costo de infraestructura cero puede
sobrevivir indefinidamente sin financiamiento. **Es opcionalidad pura.**

**F9 — Cada ficha de producto es una página propia, indexable por Google.**
7.538 páginas estáticas generadas. Alguien que googlea "¿el alfajor Guaymallén
es vegano?" puede caer directamente en una página con la respuesta ya escrita.
Es el canal de adquisición más barato que existe para este tipo de producto, y
está construido, no planeado.

**F10 — El trabajo humano de curaduría no se pierde.**
Las correcciones que una persona hace a mano se guardan aparte y sobreviven a
cada actualización automática. Es una decisión de arquitectura chica con una
consecuencia grande: el esfuerzo de curación **se acumula** en vez de
evaporarse en la próxima corrida. Es lo que convierte la curaduría manual en un
activo capitalizable y no en un gasto recurrente.

**F11 — Calidad de datos tratada como problema de primera clase.**
Tres correcciones no obvias que ya están funcionando: descarte de "fichas
fantasma" (Open Food Facts comparte los códigos de barra con la base de
cosmética, así que se colaban shampoos y hasta un medicamento cardíaco), filtro
de relevancia geográfica, y deduplicación de productos con varios códigos de
barra. En los tres casos el criterio elegido fue el conservador: por ejemplo, la
versión ingenua del filtro de fantasmas se llevaba puestos 1.608 productos bien
clasificados, incluidos 457 con sello vegano certificado.

**F12 — Velocidad de ejecución excepcional.**
34 commits, 4 fuentes de datos automatizadas, un pipeline completo, un sitio
público y 333 tests **en 7 días**. Sea quien sea que esté ejecutando esto, la
capacidad de entrega no está en duda.

---

## 3. DEBILIDADES

### 3.1 La debilidad central: el catálogo es chico

Esta es la conclusión más importante del análisis, y merece su propia sección.

El proyecto ya relevó automáticamente el catálogo de Carrefour, Vea, Día, Jumbo
y Disco. Ese relevamiento encontró **101.828 códigos de barra distintos** en
góndola.

De esos, el sitio hoy clasifica **5.581**.

| | |
|---|---|
| Productos distintos relevados en las 5 cadenas | 101.828 |
| Productos del sitio confirmados en esas cadenas | 5.581 |
| **Cobertura de góndola** | **~5,5%** |
| Productos en góndola que el sitio no conoce | 96.247 |

*(Nota metodológica: el relevamiento recorre el árbol de categorías de
alimentos de cada cadena, pero puede colarse algún artículo no alimenticio, así
que el denominador real podría ser algo menor. Aun corrigiendo generosamente,
la cobertura queda por debajo del 10%.)*

**Qué significa esto en la práctica:** una persona parada en la góndola con el
celular en una mano y un producto cualquiera en la otra tiene alrededor de **1
chance en 18** de que ese producto esté en el sitio. Ese número determina si la
herramienta se usa dos veces o una sola.

Todo lo demás que hace bien este proyecto —la trazabilidad, la auditoría del
léxico, la regla de seguridad— **solo importa si el producto que la persona
busca está adentro**. La calidad por producto es alta; la probabilidad de
encontrar el producto es baja. Hoy, el proyecto tiene un problema de alcance,
no de calidad.

### 3.2 Las demás debilidades

**D1 — La fuente de datos más rica está prácticamente sin explotar.**
Vea, Jumbo y Disco publican la lista de ingredientes real del envase. El
proyecto ya sabe leerla. Pero solo consultó **2.608 productos de los 101.828**
que tiene relevados: el 2,6%. Es la debilidad de ejecución más grande y, a la
vez, la mayor oportunidad (ver 4.1).

**D2 — Ese dato, además, no se actualiza solo.**
La actualización automática semanal corre Open Food Facts, ANMAT, la
clasificación y la publicación del sitio. **No corre el relevamiento de
supermercados ni la lectura de fichas.** Es decir: el 22,8% de los veredictos
del sitio (los 1.681 que salen de fichas y sellos de supermercado) provienen de
una cosecha manual que se hizo una vez y que se va a ir desactualizando. Es una
deuda operativa concreta y arreglable, pero hoy está abierta.

**D3 — La certificación oficial se está desaprovechando en un 86%.**
ANMAT tiene 668 productos certificados. El sistema solo logra vincular 91 con
su catálogo (13,6%). El motivo es real y está bien documentado: el registro de
ANMAT no publica el código de barras, así que el cruce se hace por marca +
nombre y es deliberadamente estricto para no certificar de más. Pero el
resultado es que **577 productos con certificación estatal no la están
mostrando**. Es evidencia de la máxima calidad quedando sin usar.

**D4 — La curaduría humana no escala como está.**
El total de correcciones humanas aplicadas hasta hoy es **14**. Existe un panel
web para hacerlas y funciona, pero el circuito completo es: una persona marca en
el panel → baja un archivo → alguien con acceso al repositorio lo importa a mano
→ vuelve a publicar el sitio. Con 1.192 productos esperando revisión, y a este
ritmo, la cola no se vacía. Sin un circuito donde una persona no técnica pueda
corregir y ver el cambio publicado sin intervención de un programador, la
curaduría es un cuello de botella permanente.

**D5 — El 40% del catálogo no tiene categoría útil.**
2.962 de 7.381 productos caen en "Otros". Eso rompe la navegación por rubro: la
categoría más grande del sitio es la que no dice nada. Para alguien que quiere
explorar —en vez de buscar un producto puntual— la experiencia se degrada
bastante.

**D6 — Los datos de marca están sucios.**
"La Serenisima" y "La Serenísima" figuran como dos marcas distintas (68 y 65
productos). 1.258 productos (17%) directamente no tienen marca cargada. Es un
problema chico de arreglar y con impacto directo en la búsqueda: quien escribe
la marca con tilde ve la mitad de los resultados.

**D7 — Hay 385 productos marcados "apto" que se apoyan solo en su nombre.**
Son el 13,8% de todos los "apto" del sitio. No violan formalmente la regla de
seguridad —el sitio los muestra marcados como estimación— pero son, por lejos,
el lugar donde puede aparecer el error más caro del producto: afirmar que algo
es vegano cuando no lo es. Recomendación concreta: someter esos 385 a revisión
prioritaria antes que a los 1.192 de la cola de "a revisar", porque un "no sé"
que debería ser "apto" cuesta mucho menos que un "apto" que debería ser otra
cosa.

**D8 — Cero evidencia de demanda.**
No hay analítica instalada. No hay usuarios medidos. No hay una sola
conversación documentada con una persona vegana usando esto. **Todo lo que
sabemos hoy sobre si a alguien le sirve este producto es una hipótesis.** Para
un inversor, esta es la incógnita más grande del proyecto, más que cualquier
tema técnico.

**D9 — No hay modelo de ingresos, ni escrito ni insinuado.**
La documentación es exhaustiva sobre metodología y no dice una palabra sobre
cómo el proyecto genera dinero. El costo cero permite esperar, pero esperar no
es una respuesta.

**D10 — Faltaba una página de términos.** *(resuelto — ver «Estado de
ejecución»)*
Cada ficha de producto ya traía la advertencia correcta —"el envase manda", y
un aviso extra sobre alérgenos en los productos marcados `apto`—, y el pie
aclaraba que "apto" no significa *cruelty-free*. Lo que no existía era una
página de términos: sin límite de responsabilidad declarado, sin licencia de
las fuentes de datos, sin canal para reportar un error y sin decir qué se mide
de la visita. Para un producto que informa sobre lo que una persona ingiere,
era una falta que convenía cubrir antes de crecer.

**D11 — Riesgo de una sola persona.**
Todo el proyecto —7 días, 34 commits— tiene un solo autor. La documentación es
excelente y eso mitiga bastante, pero hoy no hay una segunda persona que pueda
sostener el sistema.

**D12 — El acceso al panel de curaduría no es seguridad real.**
La contraseña se valida en el navegador de quien entra, con código que esa
persona puede leer. El propio código lo documenta con total franqueza y
argumenta —correctamente— que hoy es aceptable porque el panel no escribe nada:
solo genera un archivo. Lo anoto no como una falla actual, sino como una
frontera: el día que el panel escriba de verdad, esto deja de alcanzar.

**D13 — Falta lo que originalmente motivó el proyecto: los precios.**
La especificación arranca con la idea de cruzar catálogo con precios de góndola.
La base tiene la columna de precio y está **vacía en los 7.381 productos**. La
fuente oficial (SEPA / Precios Claros) bloquea el acceso automatizado. Se puede
vivir sin precios, pero conviene decidirlo explícitamente en vez de dejarlo como
una promesa pendiente.

**D14 — Tensión no resuelta entre "abierto" y "defendible".**
El proyecto declara como principio "abierto por diseño: código y metodología
públicos". Al mismo tiempo, uno de los últimos cambios fue quitar del sitio los
enlaces al repositorio. No es una contradicción grave, pero señala una decisión
estratégica sin tomar: **si el código es público, el foso competitivo no puede
ser el código** —tiene que ser la base curada, la marca o la comunidad—. Vale la
pena definirlo antes de hablar con inversores, porque cambia la respuesta a
"¿qué impide que alguien lo copie?".

---

## 4. OPORTUNIDADES

### 4.1 La palanca principal: multiplicar el catálogo por diez, con lo ya construido

Esta es la oportunidad más importante, y la razón por la que la debilidad
central (sección 3.1) es un problema de ejecución y no de concepto.

Los números medidos:

| | |
|---|---|
| Fichas de supermercado consultadas hasta hoy | 2.608 |
| De esas, con lista de ingredientes real | 1.888 (**72,4%**) |
| De esas, con sello de certificación | 1.855 (71,1%) |
| Códigos de barra ya relevados y **todavía sin consultar** | 99.220 |

**La proyección** (estimación, no medición): si se aplicara la misma consulta
que ya funciona a los 99.220 productos restantes, manteniendo la tasa de éxito
del 72%, se obtendrían del orden de **70.000 listas de ingredientes reales**. Es
decir, aproximadamente **diez veces el catálogo actual**, con la clase de
evidencia más fuerte que el proyecto sabe procesar —la etiqueta— y sin inventar
absolutamente nada nuevo.

Vale ser prudente: a esa escala aparecen fricciones que hoy no se ven (límites
de consulta de las cadenas, tiempos de corrida, productos que no cruzan con el
catálogo base). Pero el mecanismo está probado, es reanudable y ya funciona. La
diferencia entre el proyecto de hoy y un proyecto con 60-70 mil productos
clasificados con evidencia real **es tiempo de máquina, no investigación**.

Si hay una sola cosa que este proyecto debería hacer a continuación, es esta.

### 4.2 Otras oportunidades

**O1 — El escaneo de código de barras cierra el círculo de uso.**
El caso de uso natural es alguien parado en la góndola con el producto en la
mano. El teléfono ya puede leer códigos de barras desde el navegador. El
proyecto ya indexa por código de barras. Es una función chica con un efecto
desproporcionado sobre cuántas veces alguien vuelve a usar la herramienta.

**O2 — Google como canal de adquisición gratuito, ya construido.**
Las 7.538 páginas estáticas ya están. Cada producto nuevo que entra al catálogo
suma una página que puede captar búsquedas del tipo "¿X es vegano?". Con el
catálogo multiplicado por diez, esto pasa de ser un detalle técnico a ser un
canal de tráfico de verdad. **Es la sinergia directa entre 4.1 y el
crecimiento.**

**O3 — El mismo motor sirve para otras dietas, casi gratis.**
La arquitectura ya distingue "vegano" de "vegetariano". El mismo léxico de
ingredientes y la misma trazabilidad responden preguntas de mercados adyacentes
y más grandes: **sin gluten (celiaquía), sin lácteos (intolerancia a la
lactosa), kosher, halal**. Especialmente celiaquía: en Argentina tiene marco
legal propio, una comunidad organizada y una necesidad médica —no electiva— de
verificar el envase. Cada una de esas expansiones reutiliza la infraestructura
completa y solo pide extender el léxico.

**O4 — Los datos ya son un activo vendible, aunque el sitio no monetice.**
Un catálogo argentino con ingredientes normalizados, veredicto trazable y
presencia en góndola de 5 cadenas no existe públicamente hoy. Tiene compradores
potenciales concretos: marcas plant-based que quieren saber dónde están paradas,
retailers que quieren etiquetar su góndola, aplicaciones de nutrición. Es un
camino de ingresos que no depende de conseguir usuarios masivos.

**O5 — Fuentes adicionales ya identificadas y sin explotar.**
Las notas internas del proyecto señalan pistas concretas: fabricantes que
publican su propio etiquetado vegano en su sitio (Granix, con 43 productos en la
base; plant.com.ar). Cada fabricante que publique su información de forma
estructurada es una fuente de evidencia de alta calidad y bajo costo.

**O6 — Consultar directamente al fabricante, de forma sistemática.**
Idea que aparece en las notas del proyecto y que merece rescatarse: automatizar
la consulta a atención al consumidor sobre el origen de un ingrediente ambiguo.
Es exactamente la respuesta al cuello de botella de los productos "a revisar"
por lecitina, INS 471 o margarina —donde ningún dato público resuelve la duda—.
Y tiene un efecto secundario valioso: cada respuesta es evidencia documental que
**nadie más tiene**, y que no se puede copiar de ninguna fuente pública. Es el
camino más claro hacia un foso competitivo real.

**O7 — Momento de mercado favorable.**
La categoría plant-based creció fuerte en Argentina y la certificación de ANMAT
—el artículo 229 del CAA— es reciente. El registro de certificados va a crecer, y
el proyecto ya está enchufado a él. Ese activo mejora solo con el tiempo.

---

## 5. AMENAZAS

**A1 — Dependencia de fuentes que no controlamos y que pueden cerrarse.**
El 22,8% de los veredictos actuales, y **todo el plan de crecimiento de la
sección 4.1**, dependen de que las APIs de los supermercados sigan abiertas y sin
autenticación. Ninguna cadena se comprometió a nada. Pueden cerrarlas, ponerles
límites o bloquear el tráfico automatizado, mañana y sin aviso. Ya pasó con la
fuente oficial de precios (SEPA), que bloquea el acceso automatizado, y con
V-Label, que resultó ser solo una app sin forma de conectarse.
*Mitigación:* la evidencia ya cosechada queda guardada; un cierre frena el
crecimiento pero no destruye lo acumulado. Razón de más para hacer la cosecha
grande **ahora** y no dentro de seis meses.

**A2 — Un solo falso "apto" difundido puede costar la confianza entera.**
Es el riesgo existencial del producto. Alguien publica en redes "buscavegan me
dijo que esto era vegano y tenía leche", y el daño reputacional supera largamente
cualquier métrica de precisión. El proyecto lo tiene bien identificado y bien
defendido —la regla de seguridad, los tests, la auditoría del léxico— pero el
riesgo no se elimina: se administra. Los 385 productos marcados "apto" solo por
su nombre (D7) son donde ese riesgo está concentrado.

**A3 — Riesgo de responsabilidad legal, hoy sin cubrir.**
Dar información sobre lo que una persona ingiere, sin aviso legal (D10), es una
exposición innecesaria. Especialmente si el proyecto se expande a alergias o
celiaquía (O3), donde el error deja de ser una molestia ética y pasa a ser un
problema de salud. **Esto se resuelve con una página de términos y una línea en
cada ficha, y debería resolverse antes de cualquier campaña de crecimiento.**

**A4 — Un competidor con más recursos, no con mejor idea.**
Nada impide que un supermercado, una app de nutrición establecida o el propio
Open Food Facts agreguen un filtro "vegano" a lo que ya tienen, con una
distribución que este proyecto no tiene. El diferencial defendible no es hacer la
clasificación —eso se copia— sino la **profundidad de la evidencia argentina
curada**: el cruce con ANMAT, el léxico auditado contra el CAA y las correcciones
humanas acumuladas. Ese activo hay que engordarlo rápido.

**A5 — Calidad heredada de una fuente colaborativa.**
Open Food Facts es la columna vertebral del catálogo y lo carga cualquiera. Un
error en el origen se propaga. El proyecto ya construyó defensas serias (fichas
fantasma, relevancia geográfica, deduplicación, exclusiones manuales) y está
reemplazando progresivamente esa dependencia por las fichas de supermercado —que
vienen del retailer y son más confiables—. Es la dirección correcta; conviene
acelerarla.

**A6 — La ventana de tiempo se cierra sola.**
Un proyecto de 7 días con costo cero puede esperar. Pero el valor de haber
resuelto el acceso a ANMAT, a las fichas de Cencosud y el léxico auditado es
mayor **hoy** que dentro de un año, cuando alguien más lo haya resuelto o las
fuentes se hayan cerrado. La ventaja actual es de conocimiento, y ese tipo de
ventaja se evapora.

**A7 — Concentración en una sola persona (ver D11).**
Si esa persona se detiene, el proyecto se detiene. Para un inversor es la
pregunta obligada, y la respuesta hoy es incómoda.

---

## 6. Cruce del FODA: qué hacer con esto

El valor de un FODA no está en las cuatro listas, sino en cruzarlas.

| Cruce | Lectura |
|---|---|
| **Fortaleza + Oportunidad** (ofensivo) | El mecanismo de lectura de fichas ya funciona (F6, F11) y hay 99.220 productos esperando (4.1). **Multiplicar el catálogo por diez es la única jugada que hay que hacer ahora.** Todo lo demás puede esperar. |
| **Debilidad + Oportunidad** (reorientar) | La curaduría no escala (D4) justo cuando el catálogo va a crecer diez veces. Hay que arreglar el circuito de corrección humana **antes** de la cosecha grande, no después. |
| **Fortaleza + Amenaza** (defensivo) | La disciplina de trazabilidad (F2, F3, F5) es la mejor defensa contra el riesgo reputacional (A2) y contra un competidor grande (A4). Hay que hacerla visible como marca, no solo implementarla. |
| **Debilidad + Amenaza** (crítico) | Sin aviso legal (D10) + expansión a temas de salud (O3) = exposición seria (A3). Y sin analítica (D8) + una sola persona (D11) = se puede invertir mucho esfuerzo en algo que nadie usa, sin enterarse. **Estos dos son los que hay que cerrar primero, y son baratos.** |

---

## 7. Rumbo sugerido

Ordenado por relación entre impacto y esfuerzo, no por preferencia.

### Fase 1 — Antes de crecer (bajo esfuerzo, alto impacto)

1. **Instalar analítica.** Sin esto, todo lo demás es a ciegas. Es la decisión
   más barata y la más importante del documento: qué se busca, qué no se
   encuentra, si alguien vuelve.
2. **Publicar un aviso legal** y un recordatorio de verificar la etiqueta.
   Cierra A3 en una tarde.
3. **Revisar los 385 "apto" que se apoyan solo en el nombre** (D7). Es donde
   está concentrado el riesgo del producto.
4. **Automatizar el relevamiento de supermercados** dentro de la actualización
   semanal (D2), para que el 23% del catálogo deje de envejecer.

### Fase 2 — La jugada principal

5. **La cosecha grande de fichas** (4.1). Es *el* proyecto. Todo lo demás es
   preparación para esto o consecuencia de esto.
6. **En paralelo, arreglar el circuito de curaduría humana** (D4): que una
   persona no técnica pueda corregir y ver el cambio publicado sin pedirle nada
   a un programador.
7. **Normalizar marcas y categorías** (D5, D6). Con diez veces más productos, la
   búsqueda y la navegación pasan a ser el producto.

### Fase 3 — Validar que esto es un negocio

8. **Escaneo de código de barras** (O1): cierra el caso de uso real.
9. **Ponerlo delante de usuarios reales** y mirar los números de la Fase 1.
10. **Recién ahí**, elegir camino: expansión a celiaquía/alergias (O3),
    licenciamiento de datos (O4), o comunidad. Los tres son viables; elegir antes
    de tener datos de uso sería adivinar.

---

## 8. Las preguntas que este proyecto todavía no responde

Un inversor va a preguntar esto. Conviene tener la respuesta antes:

1. **¿Alguien lo usa?** Hoy: no se sabe. No es que sea bajo, es que no se mide.
2. **¿Cómo gana dinero?** Hoy: no está definido en ningún lado.
3. **¿Qué impide que lo copien?** Hoy la respuesta honesta es "el trabajo
   acumulado de investigación y curaduría", no la tecnología. Y ese foso todavía
   es finito. Hay que definir además si el código es público o no (D14).
4. **¿Qué pasa si mañana los supermercados cierran su API?** Hoy: el crecimiento
   se frena; lo cosechado sobrevive.
5. **¿Qué pasa si la persona que lo construyó se detiene?** Hoy: el proyecto se
   detiene.

Ninguna de estas cinco es un defecto del código. Las cinco son de estrategia y se
responden con decisiones, no con más programación.

---

## 9. Veredicto honesto

**Lo que hay acá es un motor excelente dentro de un auto todavía chico.**

La ingeniería está por encima de lo que corresponde a un proyecto de 7 días: la
auditoría del léxico contra el Código Alimentario Argentino, los 333 tests
construidos sobre errores reales, la regla de seguridad protegida
estructuralmente, y la decisión de mostrar la incertidumbre en vez de esconderla.
Eso no es lo habitual, y es el tipo de rigor que no se improvisa después.

La debilidad es igual de clara y no hay que suavizarla: **el catálogo cubre
alrededor del 5% de la góndola, y no hay una sola medición de que a alguien le
sirva.** Ese 5% es lo que hoy separa a este proyecto de ser una herramienta que
se usa todos los días.

Lo que hace que la conclusión sea optimista y no lo contrario es que **la brecha
ya tiene un camino probado**: 99.220 productos relevados esperando una consulta
que ya funciona, con 72% de éxito medido. No es una apuesta a descubrir algo. Es
tiempo de máquina sobre un mecanismo que ya anda.

**La recomendación en una línea:** instalar analítica y el aviso legal esta
semana, hacer la cosecha grande de fichas el mes que viene, y volver a evaluar
con un catálogo diez veces más grande y con datos reales de uso sobre la mesa.
Ahí sí se puede decidir si esto es un producto, un activo de datos, o las dos
cosas.

Hoy no alcanza la información para afirmarlo. Y decirlo es parte de aplicarle al
proyecto el mismo estándar que el proyecto se aplica a sí mismo: **ante la duda,
no se afirma.**

---

### Anexo — Cómo se hizo este análisis

Todos los números provienen de mediciones directas hechas el 9 de septiembre de
2026:

- Conteos del catálogo, veredictos, fuentes de decisión, marcas y categorías:
  consultas directas a la base `data/buscavegan.db`.
- Cobertura de góndola: comparación entre la tabla de catálogo de supermercados
  (101.828 códigos distintos) y el catálogo publicado.
- Rendimiento de las fichas: 2.608 consultadas, 1.888 con ingredientes.
- Métricas del clasificador: reporte de evaluación del modelo sobre 886 productos
  no vistos durante el entrenamiento.
- Tests: ejecución completa de la suite (333 pasando, 2,7 segundos).
- Tamaño del código, historial y automatizaciones: repositorio git y
  configuración de la actualización automática.

Las únicas cifras estimadas, y señaladas como tales, son la proyección de la
cosecha completa de fichas (sección 4.1) y la probabilidad de encontrar un
producto en góndola (sección 3.1).
