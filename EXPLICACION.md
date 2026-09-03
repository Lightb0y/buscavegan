# ¿Qué es "buscavegan"? — Explicación simple

## La idea en una frase

Un buscador donde escribís el nombre de un producto argentino (o lo escaneás
por su código de barras) y te dice **si es apto para veganos**, mostrándote
siempre **por qué** llegamos a esa conclusión.

---

## El problema que resolvemos

En Argentina no existe un lugar único donde buscar "¿este producto tiene algo
de origen animal?". Los ingredientes están en la etiqueta, pero hay que leerla
letra por letra, entender qué es "caseinato" o "INS 120", y muchas veces el
packaging no ayuda.

Nuestra idea fue cruzar dos tipos de información:

1. **Qué productos existen** en la Argentina (nombre, marca, código de barras).
2. **De qué están hechos** (la lista de ingredientes de cada uno).

Y a partir de ahí, decidir automáticamente si son aptos, con toda la
transparencia posible sobre cómo se decidió.

---

## De dónde sacamos los datos

### Intento 1: SEPA (el Estado argentino) — no funcionó del todo

El gobierno publica un catálogo de precios de supermercados (SEPA / Precios
Claros). Tiene nombre, marca y precio de miles de productos... pero **no tiene
ingredientes**. Sin ingredientes no podíamos clasificar nada de forma
confiable. Además, la página oficial bloquea la descarga automática.

### Intento 2 (el que usamos): Open Food Facts

Es una base de datos internacional, colaborativa y gratuita, tipo "Wikipedia
de los productos alimenticios". Cualquiera puede sacarle una foto a un
producto y cargar sus ingredientes. Tiene **más de 16.000 productos
argentinos**, y para muchos de ellos, la lista de ingredientes completa.

Fue mucho más lento de lo esperado conseguir todos esos datos (explicamos por
qué más abajo), pero es la única fuente que nos daba **catálogo argentino +
ingredientes** al mismo tiempo.

### Un tercer dato, más chico pero muy valioso: ANMAT

ANMAT (el organismo que regula alimentos en Argentina) tiene un registro
oficial de productos que se certificaron legalmente como "veganos". No es una
base de datos pública común: hay que abrir la página web, mirar "detrás de
escena" cómo carga la información (una técnica llamada inspeccionar el
tráfico de red del navegador), y ahí descubrimos que en realidad la página lee
una planilla de Google Sheets pública. Une vez encontrado ese "atajo", pudimos
bajar los 668 productos certificados de forma automática.

Este dato vale más que cualquier otro: no es "creemos que es vegano según los
ingredientes", es "el Estado argentino certificó por trámite legal que este
producto es vegano". Por eso lo pusimos como la fuente de **mayor confianza**
de todo el sistema.

También investigamos otra fuente posible (la app "Todo Vegan" / certificación
V-Label), pero resultó ser una app de celular sin ninguna forma de conectarnos
automáticamente. Quedó descartada y documentada como tal.

---

## Cómo decidimos si un producto es apto

Pensamos el sistema en "capas", como un embudo: cada capa intenta resolver lo
que la anterior no pudo, y solo si ninguna capa encuentra evidencia suficiente,
el producto queda marcado como **"a revisar"** (nunca lo marcamos "apto" por
las dudas — ver la regla de seguridad más abajo).

### Capa 0 — Certificación oficial (la más confiable)

¿Está en el registro de ANMAT? Si sí: **apto**, con la máxima confianza
posible, porque es un trámite legal, no una inferencia nuestra.

### Capa 1 — El fabricante lo dice

¿El fabricante declaró "vegano" en el packaging (y esa declaración está
cargada en Open Food Facts)? Si sí: **apto**.

### Capa 2 — Analizamos los ingredientes (la capa más importante)

Acá está el corazón del proyecto. Tomamos la lista de ingredientes del
producto y la comparamos, palabra por palabra, contra tres listas:

- **Ingredientes claramente animales**: leche, huevo, gelatina, carne, miel,
  carmín (un colorante rojo hecho de insectos), etc.
- **Ingredientes ambiguos**: cosas como "aroma natural" o el aditivo "INS
  471", que a veces son vegetales y a veces no, y la etiqueta no lo aclara.
- **Ingredientes claramente vegetales o minerales**: agua, azúcar, harina,
  sal, aceite de girasol, etc.

Reglas importantes que tuvimos que afinar:

- **"Leche de coco" no es leche animal.** Si aparece un ingrediente "de
  riesgo" pero justo al lado hay una palabra que lo aclara como vegetal
  ("coco", "soja", "almendra"...), no lo contamos como animal. Lo mismo al
  revés en inglés: "almond milk" (leche de almendra) — en inglés el orden de
  las palabras se invierte, así que tuvimos que enseñarle eso al sistema por
  separado.
- **Códigos como "INS 120"**: en Argentina los aditivos se numeran distinto
  que en Europa (acá "INS", en Europa "E"), y el 120 en particular es carmín,
  hecho de un insecto (la cochinilla). Estos códigos raros están en nuestra
  lista de "ingredientes prohibidos" aunque el nombre común no aparezca.
- **"Puede contener trazas de leche" no es lo mismo que "contiene leche".**
  Lo primero es una advertencia por contaminación en la fábrica (se fabrica en
  la misma línea que productos con leche), no un ingrediente real. Lo
  distinguimos y no afecta el veredicto.
- Si reconocemos **muy pocos** de los ingredientes de la lista (por ejemplo,
  la mitad son palabras raras que no identificamos), no nos animamos a decir
  "apto": lo mandamos a revisar. Es mejor decir "no sé" que arriesgarse.

### Capa 2.5 — El nombre del producto, cuando no hay ingredientes

Muchos productos en la base no tienen la lista de ingredientes cargada. Para
esos casos, miramos el **nombre**:

- Si el nombre dice explícitamente "vegano" o "plant based" → apto.
- Si el nombre tiene una palabra animal ("leche", "queso", "carne"...) sin
  ningún calificador vegetal cerca → no apto.
- Si el producto **es**, directamente, un ingrediente vegetal o mineral — "Sal
  Fina", "Yerba Mate", "Garbanzos", "Canela molida" — lo marcamos apto sin
  vueltas. Acá tuvimos que ser muy cuidadosos: al principio la regla marcaba
  "apto" cualquier producto que tuviera la palabra en cualquier parte del
  nombre, y eso generó errores serios, como marcar **"Yogurisimo Banana"**
  (un yogur, ¡no apto!) como apto solo porque tenía la palabra "banana". Lo
  corregimos exigiendo que esa palabra sea literalmente el producto (esté al
  principio del nombre), no un sabor o un ingrediente secundario.

### Capa 3 — Un modelo que aprende solo (inteligencia artificial)

Para los productos que ni tienen ingredientes cargados ni un nombre
suficientemente claro, entrenamos un modelo de machine learning (aprendizaje
automático). La idea: le mostramos miles de productos que **ya sabíamos**
clasificar con certeza (por las capas anteriores) y el modelo aprendió qué
palabras del nombre suelen asociarse a "apto", "no apto" o "vegetariano".

Es como si un asistente hubiera leído miles de etiquetas y, sin que se lo
digamos explícitamente, hubiera notado que "fideos", "jugo" o "mate" casi
siempre acompañan a productos aptos, y "atún", "jamón" o "gelatina" casi
siempre a productos no aptos.

Este modelo **no es perfecto**, y lo decimos explícitamente en la app:
aprende asociaciones que a veces son correctas por razones equivocadas (por
ejemplo, asoció la palabra "frutilla" con "no apto" porque en el catálogo la
mayoría de los productos con frutilla eran yogures o gelatinas, no porque la
frutilla en sí tenga algo de animal). Por eso:

- Solo confiamos en el modelo cuando está **muy seguro** (más del 85% de
  confianza para decir "apto", un poco menos exigente para "no apto", porque
  equivocarse diciendo "no apto" es un error menos grave).
- Toda predicción del modelo se muestra en la app **marcada como estimada**,
  con su porcentaje de confianza, para que quede claro que no es un dato
  verificado sino una estimación.

### Capa 4 — Revisión humana

Por más capas automáticas que tengamos, siempre va a quedar un resto de
productos sin resolver. Para esos armamos una herramienta que exporta un
listado (ordenado para que primero se revisen las marcas con más productos
pendientes, así una sola revisión resuelve muchos productos de una vez), una
persona lo completa a mano, y esa corrección **queda guardada para siempre**:
aunque se vuelva a correr todo el proceso automático, la decisión humana
manda por encima de cualquier capa.

---

## La regla de seguridad (lo más importante de todo el proyecto)

**Ante cualquier duda, el producto queda como "a revisar", nunca como
"apto".**

¿Por qué? Porque el costo de los dos errores posibles no es el mismo:

- Si decimos "no apto" y en realidad sí lo era → alguien se pierde de comprar
  un producto que sí podía comer. Molesto, pero no grave.
- Si decimos "apto" y en realidad **no** lo era → alguien come algo que no
  quería comer, quizás por convicciones muy fuertes (religiosas, éticas,
  de salud). Ese error es mucho más grave.

Por eso todo el sistema está diseñado de forma asimétrica: es mucho más fácil
que algo termine en "no apto" o "a revisar" que en "apto". Y en la app, cada
producto muestra claramente de dónde salió su veredicto, para que el usuario
pueda decidir cuánto confiar en él.

---

## Los cuatro estados posibles

| Ícono | Estado | Qué significa |
|---|---|---|
| ✅ | **Apto** | Vegano: sin nada de origen animal |
| ⚠️ | **Vegetariano** | Sin carne ni pescado, pero tiene leche, huevo o miel |
| ❌ | **No apto** | Tiene algo de origen animal |
| ❓ | **A revisar** | No tenemos evidencia suficiente todavía |

Un detalle importante que aclaramos en toda la documentación: **"apto" acá
significa vegano por ingredientes**, no "cruelty-free" (que es sobre si se
testeó en animales). Son conceptos distintos y esta base de datos solo puede
hablar del primero, porque es lo único que las fuentes de datos reportan.

---

## Los números, hoy

De **13.015 productos argentinos** que tenemos cargados:

- **6.429 (49%)** ya están clasificados con algún nivel de confianza.
- **6.586 (51%)** siguen "a revisar" porque no tenemos suficiente información
  todavía (la mayoría, porque el producto no tiene ingredientes cargados en
  Open Food Facts).

De los que sí clasificamos, así se repartieron según qué método los resolvió:

| Método | Productos resueltos |
|---|---|
| Analizando la lista de ingredientes | 3.288 |
| Por el nombre del producto | 2.345 |
| El modelo de inteligencia artificial | 549 |
| El fabricante lo declaró en el packaging | 125 |
| Certificación oficial de ANMAT | 97 |
| El propio análisis de Open Food Facts | 25 |

---

## Cosas técnicas que se resolvieron por el camino (contadas simple)

- **Bajar 16.000 productos era muy lento.** La forma "oficial" de pedirle
  datos a Open Food Facts nos daba solo 100 productos por vez y nos frenaba
  cada 10 pedidos (para evitar que la sobrecarguemos). Encontramos una forma
  más rápida de pedir de a 500 por vez, y para llegar a absolutamente todos
  los productos (algunos quedaban "escondidos" por cómo funciona el buscador
  interno de la base), terminamos usando una copia completa y oficial de
  toda la base de datos mundial, filtrándola nosotros mismos para quedarnos
  solo con lo argentino.
- **Los ingredientes vienen de dos formas distintas** según cómo se consulten
  los datos: a veces como texto libre ("harina de trigo, azúcar, sal") y a
  veces como una lista ya "traducida" a categorías estándar en inglés
  ("wheat-flour", "sugar", "salt"). Tuvimos que enseñarle a nuestro sistema a
  entender las dos formas.
- **Los aditivos numerados casi no se reconocían** por un error de
  formateo: nuestro sistema convertía "E330" en "E 330" (con espacio) antes
  de buscarlo, pero la lista de aditivos que reconocíamos todavía buscaba la
  forma sin espacio. Un típico bug chico con impacto grande, que se detectó
  revisando los resultados a mano.
- **Verificamos cada corrección revisando ejemplos reales**, no solo
  confiando en la teoría. Varias de las mejoras (como el caso de
  "Yogurisimo Banana") solo se descubrieron mirando con atención decenas de
  resultados concretos de la base, no pensando el problema en abstracto.

---

## Qué queda para más adelante

- Seguir bajando el porcentaje de "a revisar", sobre todo motivando la
  revisión manual de las marcas con más productos pendientes.
- Sumar precios de referencia desde SEPA (por ahora no lo hicimos porque el
  portal oficial bloquea la descarga automática y hay que bajarlo a mano).
- Reentrenar el modelo de inteligencia artificial periódicamente a medida que
  se sume más información de ingredientes, para que sea cada vez más preciso.
- Automatizar el refresco completo (ya está armado para correr solo, una vez
  por semana, usando GitHub Actions).
