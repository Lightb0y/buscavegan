# Qué se corrigió en la detección de ingredientes

Este documento explica, en lenguaje llano, una revisión completa que se le hizo
al motor que decide si un producto es apto vegano. Se buscaron dos tipos de
error opuestos y se encontraron **22 fallas reales**.

## Los dos errores que se buscaron

El sistema puede equivocarse en dos direcciones, y no cuestan lo mismo:

| Error | Qué significa | Qué tan grave es |
|---|---|---|
| **Falso apto** | Decimos "es vegano" y no lo es | **Grave.** Alguien come algo que no quería comer |
| **Falso no apto** | Decimos "no es vegano" y sí lo era | Molesto. Le escondemos un producto que podía comprar |

Por eso el proyecto siempre prefiere decir "no sabemos" antes que arriesgar un
"sí". Pero un exceso de "no sabemos" también arruina la herramienta, así que la
revisión atacó las dos cosas.

## Cómo se buscaron los errores (y por qué no fue "a ojo")

En lugar de revisar el léxico por intuición, se lo cruzó contra dos fuentes que
tienen más autoridad que nuestra opinión:

1. **La taxonomía oficial de Open Food Facts.** Es la base de datos colaborativa
   de donde sacamos los ingredientes. Publica una lista de 98.314 líneas donde
   marca qué ingredientes son `vegan: no` (seguro que no) y `vegan: maybe`
   (puede ser que no). Se descargó entera y se comparó ingrediente por
   ingrediente contra lo que nuestro código detecta.
2. **El Código Alimentario Argentino (CAA).** Es la ley que define qué se puede
   llamar cómo. Sirve para los casos donde el nombre de un ingrediente ya
   implica su origen, aunque la etiqueta no lo aclare.

Después, cada error candidato se probó contra la base real antes de tocar una
sola línea de código, y se le escribió un test para que no vuelva.

---

## Los hallazgos más importantes

### 1. Oleomargarina: 24 productos se mostraban como veganos y no lo son

Esta fue la falla más cara y la que motivó toda la revisión.

**El problema:** el sistema solo reconocía la frase completa "oleomargarina
**bovina**". Cuando la etiqueta decía simplemente "oleomargarina", la palabra
pasaba de largo como si fuera un ingrediente desconocido cualquiera.

**Qué averiguamos:** el CAA, en su **artículo 545**, dice textualmente:

> "Se entiende por Oleomargarina (óleo-oil) **bovina u ovina**, según
> corresponda, el producto resultante de la separación de la mayor parte de la
> oleoestearina **a partir de grasas o primeros jugos bovinos u ovinos**"

O sea: en Argentina la oleomargarina **es, por definición, grasa de vaca u
oveja**. No existe una oleomargarina vegetal — el "bovina u ovina" no es un
calificativo opcional que distinga una versión animal de una vegetal, sino que
solo aclara de cuál de los dos animales viene. La palabra sola ya alcanza.

**Sobre la pregunta de si las fuentes lo resuelven solas: no lo hacen.** Se
revisó la taxonomía completa de Open Food Facts y el resultado es concluyente:

- La única entrada que existe es `oleomargarina bovina`, marcada `vegan: no`.
- **No hay ninguna entrada para "oleomargarina" a secas**, ni como sinónimo de
  nada. Un producto etiquetado así queda como ingrediente no identificado.
- La entrada `margarine` **no tiene propiedad `vegan` en absoluto**: OFF no
  afirma que la margarina sea vegana.

Es decir que Open Food Facts simplemente no se pronuncia, y el criterio hay que
traerlo del CAA. Eso es lo que se hizo.

**Resultado:** 24 productos (galletitas, grisines, obleas, rebozadores) pasaron
de "apto vegano" a "no apto".

### 2. Margarina y grasa hidrogenada: no se puede afirmar que sean vegetales

Dos casos más donde el CAA muestra que el nombre no alcanza:

- **Margarina (art. 551).** La ley permite explícitamente que su fase grasa sean
  "**grasas animales comestibles**", y además admite hasta 5% de grasa de leche,
  leche en polvo, suero, albúmina y caseinato. Una margarina sin el calificativo
  "vegetal" puede legalmente tener lácteos.
- **Grasa hidrogenada (art. 548).** La hidrogenación se aplica a cualquier
  aceite o grasa del Código, animal o vegetal. El nombre habla del proceso, no
  del origen.

Ninguno de los dos pasa ahora a "no apto" — pasan a **"revisar"**, que es lo
honesto: no sabemos. Si la etiqueta aclara "margarina vegetal" o "grasa vegetal
hidrogenada", se siguen aceptando como aptos sin problema.

**Resultado:** 23 productos (sobre todo tapas de empanada y galletitas) pasaron
de "apto" a "revisar".

### 3. Conservantes: solo hay uno de origen animal, y no lo detectábamos

Se revisó la familia completa de conservantes. La buena noticia es que casi
todos son sintéticos o minerales y son veganos sin discusión: sorbatos,
benzoatos, sulfitos, nitritos, propionatos, natamicina.

Hay **una sola excepción de uso corriente**: la **lisozima (INS 1105)**, que se
extrae de la clara de huevo y se usa sobre todo en quesos y vinos.

Y acá había además un bug técnico que la hacía invisible: el código que
reconoce aditivos numerados estaba escrito para códigos de **tres** dígitos.
Con "INS 1105" leía "INS 110" y descartaba el último número, con lo cual lo
tomaba por un aditivo cualquiera y lo daba por vegano.

También quedó marcada como dudosa la **nisina (INS 234)**, porque aunque es de
origen bacteriano, se cultiva habitualmente sobre un medio lácteo.

### 4. Productos veganos que estábamos rechazando

El error opuesto. La causa es siempre la misma: los productos vegetales usan las
palabras de sus equivalentes animales, y el sistema las leía literalmente.

| Producto | Antes decía | Por qué está mal |
|---|---|---|
| Crema de maní | Vegetariano | Es pasta de maní, no tiene crema |
| Miel de caña | Vegetariano | Es melaza de caña de azúcar, no tiene abeja |
| Carne de soja | No apto | Es proteína de soja texturizada |
| Manteca vegetal | Vegetariano | Es grasa vegetal |
| Cuajo vegetal / microbiano | No apto | Son los que más se usan hoy, y no son de faena |
| Aceitunas sin hueso | (riesgo) | "Hueso" acá es el carozo de la aceituna |

Se agregaron los calificativos que anulan cada término. Con un cuidado
importante: **el calificativo vale solo para su palabra**. "Miel de maple" es
vegana, pero eso no puede hacer que "helado de maple" pase por vegano — el
helado sigue teniendo leche. Hay un test específico para esto.

### 5. Un error de lógica que absolvía grasa de cerdo

Cuando un ingrediente venía escrito como una lista unida ("aceite vegetal **y**
grasa de cerdo"), el sistema veía la palabra "vegetal" y absolvía el ingrediente
**entero**, incluida la grasa de cerdo.

El arreglo distingue dos situaciones que antes se confundían:

- "leche **de coco**" → acá "coco" modifica a "leche": es una sola cosa, vegetal.
- "aceite vegetal **y** grasa de cerdo" → acá hay **dos** ingredientes distintos,
  y el calificativo del primero no dice nada del segundo.

### 6. Ingredientes animales que directamente no estaban en el léxico

Faltaban, y por eso pasaban desapercibidos: ternera, cordero, ave y menudencias,
crustáceos, moluscos, harina y caldo de hueso, proteína animal, pepsina,
oleoestearina, y "grasa láctea" en femenino (el código buscaba "lácteo" y nunca
matcheaba "láctea", así que "materia grasa láctea" pasaba como vegana).

También faltaban en inglés, porque buena parte del catálogo argentino de Open
Food Facts tiene los ingredientes en ese idioma y fallaban por una sola letra:
`carmine` (nuestro léxico buscaba "carmin"), `gelatin`, `whey`, `tallow`,
`lard`, `lysozyme`, `milkfat`. Un caso concreto que apareció: un **aceite de
hígado de bacalao** figuraba como apto vegano.

### 7. Las palabras que nombran una función, no un ingrediente

Este fue el cambio más sutil, y el que se corrigió dos veces antes de quedar
bien.

Palabras como "colorante", "conservante" o "espesante" no dicen **nada** sobre
el origen: hay colorantes vegetales (cúrcuma) y animales (carmín de cochinilla).
Contarlas como evidencia de que un producto es vegetal era un error.

Pero el primer intento de arreglo fue peor que el problema. Al dejar de
contarlas como "reconocidas", seguían pesando en el cálculo de cuánto de la
etiqueta entendimos. Resultado: **un yogur de coco 100% vegano quedó marcado
"no apto"**, porque su etiqueta prolija ("gelificante (agar)", "estabilizante
(goma xántica)") lo dejaba por debajo del umbral de comprensión, y al no poder
resolverlo por ingredientes el sistema caía en adivinar por el rubro, que era
"Lácteos".

La lección: en la etiqueta argentina la clase viene **acompañada** del aditivo
real. Castigar eso significaba premiar a la etiqueta que informa menos.

La solución final es que estas palabras **no cuentan para ningún lado**: no
suman como evidencia vegetal, pero tampoco restan. Se descartan del cálculo,
porque no son ingredientes: son el título del ingrediente que viene después.

Lo mismo pasaba con los datos de Open Food Facts, y ahí el error fue mío por
suponer sin medir: pensé que OFF ponía la etiqueta genérica solo cuando no sabía
cuál era el aditivo. Al medirlo, resultó que **el 98% de los productos traen la
etiqueta genérica junto con la específica**. Marcar la genérica como dudosa
habría mandado a "revisar" un montón de productos perfectamente identificados.

---

## Qué cambió en los números

Todo medido sobre los mismos 10.395 productos:

| | Antes | Después |
|---|---|---|
| Apto vegano | 2.553 | 2.514 |
| No apto | 2.072 | 2.244 |

- **71 productos dejaron de estar marcados como aptos.** Son los falsos aptos
  corregidos: 24 por oleomargarina, 23 por margarina o grasa hidrogenada, y el
  resto por ingredientes animales que no detectábamos.
- **32 productos pasaron a ser aptos.** Son productos veganos que estábamos
  rechazando o dejando en duda sin motivo.
- **La cobertura no empeoró**: el porcentaje de productos clasificados quedó en
  61,8%, igual que antes. Se ganó precisión sin perder alcance.

Una aclaración honesta: varias correcciones del punto 4 (crema de maní, miel de
caña, carne de soja) **no movieron ningún producto hoy**, simplemente porque no
hay productos así cargados en el catálogo actual. Son preventivas: el error
estaba, y se hubiera manifestado apenas alguien cargara uno.

## Cómo se evita que estos errores vuelvan

Se agregaron **71 tests nuevos** ([tests/test_falsos_positivos.py](tests/test_falsos_positivos.py)),
uno por cada error encontrado. Ninguno es hipotético: cada uno se verificó
contra la base real antes de escribir la corrección.

Los tests también protegen las correcciones de sí mismas. Por ejemplo, después
de arreglar "crema de maní" hay un test que verifica que "crema de leche" siga
siendo un lácteo, y después de arreglar "miel de caña" otro que verifica que
"helado de maple" siga sin ser vegano.

El total del proyecto pasó de 184 a 255 tests.

## Lo que sigue sin resolverse

- **Los cultivos bacterianos** (lactobacillus, streptococcus) no se reconocen.
  No son animales, pero suelen cultivarse sobre medios lácteos. Hoy quedan como
  desconocidos, lo que baja la comprensión de la etiqueta sin llegar a marcar
  nada.
- **Si la etiqueta dice solo "colorante"** y no aclara cuál, no hay forma de
  saber si es cúrcuma o carmín. Con los datos disponibles es un límite real, no
  un bug: nadie puede responderlo sin la información.
- **El azúcar refinada** puede filtrarse con carbón de hueso, y la etiqueta
  nunca lo aclara. Open Food Facts marca el azúcar como `vegan: maybe` por eso.
  Acá se decidió no seguir ese criterio: marcaría medio catálogo como dudoso, y
  en la práctica la mayoría de las certificaciones veganas aceptan el azúcar.
  Es una decisión discutible y queda anotada como tal.
