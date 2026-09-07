---
name: buscavegan
description: Buscador de productos argentinos aptos veganos que muestra la evidencia detrás de cada veredicto.
colors:
  papel-kraft: "#fdfbf7"
  papel-hundido: "#f5f1e8"
  papel-elevado: "#ffffff"
  tinta: "#1a1814"
  tinta-media: "#5c5648"
  tinta-tenue: "#857e6d"
  linea: "#e2dccd"
  linea-fuerte: "#cdc5b0"
  foco: "#1b57c4"
  apto-tinta: "#1c6437"
  apto-fondo: "#e6f1e8"
  apto-linea: "#a9cfb6"
  vegetariano-tinta: "#8a5300"
  vegetariano-fondo: "#fbeed8"
  vegetariano-linea: "#e6cd9c"
  no-apto-tinta: "#a32820"
  no-apto-fondo: "#fbe9e7"
  no-apto-linea: "#eec0ba"
  revisar-tinta: "#47525f"
  revisar-fondo: "#edeff2"
  revisar-linea: "#cfd5dd"
typography:
  display:
    fontFamily: "Fraunces, Georgia, serif"
    fontSize: "clamp(1.75rem, 1.2rem + 2.2vw, 2.75rem)"
    fontWeight: 600
    lineHeight: 1.15
    letterSpacing: "-0.015em"
  headline:
    fontFamily: "Fraunces, Georgia, serif"
    fontSize: "clamp(1.3rem, 1.05rem + 1.1vw, 1.75rem)"
    fontWeight: 600
    lineHeight: 1.15
    letterSpacing: "-0.015em"
  title:
    fontFamily: "Fraunces, Georgia, serif"
    fontSize: "1.1rem"
    fontWeight: 600
    lineHeight: 1.15
  body:
    fontFamily: "IBM Plex Sans, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.55
    fontFeature: "tabular-nums"
  label:
    fontFamily: "IBM Plex Sans, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 700
    letterSpacing: "0.09em"
  mono:
    fontFamily: "IBM Plex Mono, ui-monospace, monospace"
    fontSize: "0.875em"
    fontWeight: 400
    letterSpacing: "-0.01em"
rounded:
  chico: "6px"
  base: "10px"
  pastilla: "999px"
spacing:
  e1: "0.25rem"
  e2: "0.5rem"
  e3: "0.75rem"
  e4: "1rem"
  e5: "1.5rem"
  e6: "2rem"
  e7: "3rem"
  e8: "4.5rem"
components:
  campo-busqueda:
    backgroundColor: "{colors.papel-elevado}"
    textColor: "{colors.tinta}"
    rounded: "{rounded.base}"
    padding: "0.75rem 5.5rem 0.75rem 2.75rem"
  chip:
    backgroundColor: "{colors.papel-elevado}"
    textColor: "{colors.tinta-media}"
    rounded: "{rounded.pastilla}"
    padding: "0.3rem 0.75rem"
  chip-activo:
    backgroundColor: "{colors.apto-fondo}"
    textColor: "{colors.apto-tinta}"
    rounded: "{rounded.pastilla}"
    padding: "0.3rem 0.75rem"
  sello-veredicto:
    backgroundColor: "{colors.apto-fondo}"
    textColor: "{colors.apto-tinta}"
    rounded: "{rounded.pastilla}"
    padding: "0.15rem 0.5rem 0.15rem 0.25rem"
  ficha-producto:
    backgroundColor: "{colors.papel-elevado}"
    textColor: "{colors.tinta}"
    rounded: "{rounded.base}"
    padding: "0.75rem"
  boton-ver-mas:
    backgroundColor: "{colors.papel-elevado}"
    textColor: "{colors.tinta}"
    rounded: "{rounded.pastilla}"
    padding: "0.5rem 1.5rem"
  panel:
    backgroundColor: "{colors.papel-hundido}"
    textColor: "{colors.tinta}"
    rounded: "{rounded.base}"
    padding: "1rem"
---

# Design System: buscavegan

## Overview

**Creative North Star: "El Rótulo Honesto"**

buscavegan se ve como la letra chica en la que sí se puede confiar, no como la
tapa que vende. Toda la estética viene de la ficha técnica y la etiqueta
nutricional: papel tibio, tinta casi negra, cada dato en un lugar fijo y
predecible. Es una obra de consulta, no una landing — el visitante no viene a
ser convencido de nada, viene a verificar un hecho antes de poner algo en el
changuito.

De ahí sale la decisión que gobierna todo el sistema: **el color saturado se
raciona como el sello de un inspector**. Hay exactamente cuatro colores
saturados —los cuatro veredictos— y no se usan para absolutamente nada más. Un
botón verde o un link verde harían que el verde dejara de significar "apto", y
el dato que la persona vino a buscar perdería su señal. Todo el resto del
sistema (navegación, botones, links, bordes, filtros en reposo) vive en la
escala papel/tinta.

La tipografía sostiene la misma idea: un serif con carácter (Fraunces) para
los títulos, que da autoridad de texto impreso en vez de autoridad de pantalla
de ventas, y un sans técnico (IBM Plex Sans) para el cuerpo, elegido por sus
cifras de ancho fijo — los EAN, los porcentajes y los conteos se leen en
columna. La densidad es alta pero no apretada: es un catálogo de 7.400
productos que hay que poder barrer con la vista.

**Key Characteristics:**
- Papel y tinta cálidos; nada de blanco puro ni de gris azulado.
- Cuatro colores saturados, uno por veredicto, con uso exclusivo.
- Plano por defecto: la profundidad se construye con bordes de 1px, no con sombra.
- Serif editorial en títulos, sans técnico con cifras tabulares en el cuerpo.
- El "por qué" de cada dato es contenido de primera clase, nunca letra chica.

## Colors

Una base de papel cálido casi monocroma, interrumpida solo por la familia de
cuatro colores del veredicto. La paleta no tiene "color de marca": la marca es
la ausencia de color decorativo.

### Primary

Los cuatro veredictos. Cada uno es un trío (tinta / fondo / línea) que se
aplica junto, mediante variables locales `--tinta-v` / `--fondo-v` /
`--linea-v` que un contenedor con clase `.v--<estado>` fija para su subárbol.

- **Verde Certificado** (`#1c6437`): el veredicto "apto vegano". Aparece en el
  sello, en el filo izquierdo de la tarjeta y en el bloque de dictamen de la
  ficha. Es el único verde del sistema.
- **Ocre de Cautela** (`#8a5300`): "vegetariano, no vegano". Deliberadamente
  ámbar y no amarillo brillante: es una advertencia matizada, no una alarma.
- **Bermellón de Rechazo** (`#a32820`): "no apto". Rojo profundo y apagado, con
  peso de sello de rechazo antes que de error de sistema.
- **Gris Pizarra Pendiente** (`#47525f`): "a revisar". Desaturado a propósito,
  pero **nunca desjerarquizado**: es un estado legítimo del producto, no un
  fracaso que haya que esconder.

### Neutral

- **Papel Kraft Cálido** (`#fdfbf7`): el fondo de todo el sitio. Blanco roto
  con un dejo beige, como el papel de una etiqueta o un remito.
- **Papel Hundido** (`#f5f1e8`): paneles laterales de la ficha, teclas, fondos
  de miniatura sin foto. Un escalón por debajo del papel base.
- **Papel Elevado** (`#ffffff`): tarjetas, campo de búsqueda y chips. Un
  escalón por encima; es el único blanco puro del sistema.
- **Tinta** (`#1a1814`): todo el texto principal. Negro cálido, nunca `#000`.
- **Tinta Media** (`#5c5648`): texto secundario, motivos, navegación en reposo.
- **Tinta Tenue** (`#857e6d`): placeholders, etiquetas de campo, metadatos.
- **Línea** (`#e2dccd`) y **Línea Fuerte** (`#cdc5b0`): la única herramienta de
  separación y contorno del sistema.

### Tertiary

- **Azul de Foco** (`#1b57c4`): exclusivamente el anillo de foco de teclado. Es
  azul justamente porque ningún veredicto lo es: nunca se puede confundir el
  indicador de "estás acá" con el dato del producto.

### Named Rules

**La Regla del Reactivo.** Los cuatro colores de veredicto no se usan para nada
que no sea comunicar un veredicto. Ni botones, ni links, ni encabezados, ni
estados de carga, ni acentos decorativos. Test: si un elemento saturado no
responde a la pregunta "¿esto es apto?", está mal pintado.

**La Regla del Negro Cálido.** No hay `#000000` ni grises azulados en el
sistema. Todo neutro tiene temperatura cálida (hue amarillo-marrón), incluido
el modo oscuro, donde el fondo es `#15140f` y no un carbón neutro.

**La Regla del Triple Canal.** Un veredicto se comunica siempre por tres vías
simultáneas: símbolo (`✓ ◐ ✕ ?`), palabra ("Apto vegano") y color. Quitar
cualquiera de las tres rompe el sistema — el color es el dato crítico y ~8% de
los hombres no distingue rojo de verde.

## Typography

**Display Font:** Fraunces (con Georgia, serif de respaldo)
**Body Font:** IBM Plex Sans (con ui-sans-serif, system-ui)
**Label/Mono Font:** IBM Plex Mono (con ui-monospace)

**Character:** Un serif variable con opinión contra un sans de ingeniería. La
combinación da la autoridad de un documento impreso sin caer en lo solemne:
Fraunces tiene suficiente calidez y rareza para no leerse como periódico, y
Plex aporta la precisión de una hoja de datos. Ninguna de las dos es Inter.

### Hierarchy

- **Display** (600, `clamp(1.75rem, 1.2rem + 2.2vw, 2.75rem)`, 1.15,
  `-0.015em`): el `h1` de cada página. Un solo uso por vista.
- **Headline** (600, `clamp(1.3rem, 1.05rem + 1.1vw, 1.75rem)`, 1.15): `h2`,
  incluida la frase del dictamen en la ficha de producto (1.375rem fijo ahí,
  para no competir con el nombre del producto).
- **Title** (600, `1.1rem`, 1.15): `h3`. En la tarjeta de resultado el nombre
  del producto usa el sans a 0.9375rem/600, no el serif: a ese tamaño el serif
  pierde legibilidad en una grilla densa.
- **Body** (400, `1rem`, 1.55): texto corrido, con `text-wrap: pretty` y
  `font-variant-numeric: tabular-nums` heredado del `body`.
- **Label** (700, `0.75rem`, `0.09em`, MAYÚSCULAS): los encabezados de bloque y
  de panel ("POR QUÉ", "DE DÓNDE SALE ESTE DATO"). Marcan sección sin robar
  jerarquía al contenido.
- **Mono** (400, `0.875em`, `-0.01em`): exclusivamente códigos de barras y
  teclas de atajo.

### Named Rules

**La Regla de la Cifra en Columna.** El `body` fija `font-variant-numeric:
tabular-nums` globalmente. Los EAN, conteos y porcentajes tienen que alinearse
verticalmente al comparar productos; nunca se revierte a cifras proporcionales.

**La Regla del Serif Grande.** El serif solo aparece a partir de ~1.1rem. Por
debajo de eso el sistema usa el sans, incluso en encabezados semánticos
(`.ficha__nombre` es un `h3` pintado con el sans a 0.9375rem).

## Layout

Contenedor único centrado de `68rem` máximo con `1rem` de padding lateral,
usado por todas las páginas sin excepción. La escala de espaciado es de base
4px, expuesta como `--e1`…`--e8` (0.25rem → 4.5rem) y nombrada por función, no
por medida.

La grilla de resultados es `repeat(auto-fill, minmax(21rem, 1fr))` con `0.75rem`
de gap: colapsa a una columna en móvil sin media query. La ficha de producto es
la única página con breakpoint explícito — a partir de `56rem` pasa a
`minmax(0, 1fr) 19rem`, con la evidencia en la columna lateral; por debajo, la
evidencia queda debajo del contenido principal, nunca oculta tras un acordeón.

La densidad es alta: la tarjeta de resultado tiene `0.75rem` de padding y una
miniatura de `3.25rem`. Es deliberado — quien busca "leche" espera barrer
decenas de resultados, no desplazarse por tarjetas de tamaño póster.

### Named Rules

**La Regla del Marco Fijo.** Todo producto sin foto recibe un marco del mismo
tamaño que la miniatura (`3.25rem`) con un glifo tenue. Sin esto la grilla se
desalinea producto por producto, porque solo ~82% del catálogo tiene imagen.

## Elevation & Depth

Plano por diseño, con una excepción deliberada. La profundidad se construye
casi enteramente con **capas tonales y bordes de 1px**: papel hundido → papel
base → papel elevado, separados por `--linea`. Las tarjetas de resultado, los
paneles, los chips y las píldoras no tienen sombra en ningún estado.

La única sombra del sistema está en el campo de búsqueda, y está ahí porque
es el elemento con el que hay que interactuar primero: la sombra lo levanta del
papel para que se lea como "acá se escribe".

### Shadow Vocabulary

- **Sombra de campo** (`box-shadow: 0 1px 2px rgb(26 24 20 / 6%), 0 4px 14px -6px rgb(26 24 20 / 10%)`):
  exclusiva del campo de búsqueda. En modo oscuro sube a 40%/50% de opacidad
  sobre negro puro, porque una sombra cálida tenue desaparece sobre fondo
  oscuro.

### Named Rules

**La Regla de la Sombra Única.** Hay una sola sombra en el sistema y un solo
elemento que la usa. Cualquier nuevo elemento que "necesite" sombra
probablemente necesita en realidad un borde o un cambio de capa tonal.

**La Regla del Filo Semántico.** La tarjeta de resultado lleva un borde
izquierdo de 3px con el color del veredicto. No es decoración: permite barrer
la lista y ver la distribución de veredictos sin leer una sola palabra. Ese
filo nunca cambia de color en hover.

## Shapes

Dos radios y una píldora. `10px` (`--radio`) para todo lo que es superficie
—tarjetas, paneles, el campo de búsqueda—; `6px` (`--radio-chico`) para
elementos chicos dentro de esas superficies —miniaturas, teclas, anillos de
foco—; y `999px` para todo lo que es una etiqueta o un control redondeado:
sellos de veredicto, chips de filtro, el selector de categoría y el botón "Ver
más".

Los bordes son siempre de 1px salvo el filo semántico de 3px en la tarjeta y el
borde inferior de 2px de las teclas de atajo (que imita el relieve de una
tecla real).

## Components

### Buttons

- **Shape:** píldora completa (`999px`).
- **"Ver más":** papel elevado sobre borde `--linea-fuerte` de 1px, texto en
  tinta a 0.9375rem/600, padding `0.5rem 1.5rem`. Centrado bajo la grilla.
- **Hover:** cambia el fondo a papel hundido. Sin transformación ni sombra.
- **Botones de icono** ("limpiar búsqueda", "limpiar todo"): sin borde ni
  fondo en reposo; en hover toman fondo papel hundido y tinta plena.

### Chips

- **Style:** píldora de papel elevado, borde `--linea-fuerte` de 1px, texto en
  tinta media a 0.875rem. Contienen un `<input type="checkbox">` real oculto —
  son tabulables y activables con la barra espaciadora, y los lectores de
  pantalla anuncian su estado.
- **State:** al activarse toman el trío de color de su veredicto (fondo, tinta
  y borde) **y además** ganan peso 600 y rellenan su punto indicador. Un chip
  apagado nunca depende solo del color para leerse como apagado.
- Los chips que no son de veredicto (con ingredientes, en góndola) usan los
  neutros al activarse — no toman color de veredicto.

### Cards / Containers

- **Corner Style:** `10px`.
- **Background:** papel elevado sobre el papel base de la página.
- **Shadow Strategy:** ninguna (ver Elevation).
- **Border:** 1px `--linea` en tres lados, 3px del color del veredicto a la
  izquierda.
- **Internal Padding:** `0.75rem`.
- El link del nombre cubre la tarjeta entera con un `::after` absoluto, para
  que el área de toque sea grande, pero el texto accesible del link sigue
  siendo solo el nombre del producto. El anillo de foco se pinta sobre ese
  pseudo-elemento, no sobre el texto.

### Inputs / Fields

- **Style:** campo de búsqueda de papel elevado, borde `--linea-fuerte` de 1px,
  radio `10px`, texto a 1.125rem, con lupa a la izquierda y tecla `/` a la
  derecha (que se reemplaza por un botón de limpiar cuando hay texto).
- **Focus:** anillo `2px solid #1b57c4` con `outline-offset: 1px`.
- **Selector de categoría:** píldora, mismo borde, `max-width: 14rem`.

### Navigation

- Links en tinta media a 0.9375rem, sin subrayado.
- **Hover / activo:** tinta plena más un `box-shadow: inset 0 -2px 0` que actúa
  de subrayado grueso. Nunca color de veredicto.
- El encabezado no es sticky y no colapsa en móvil: son tres links, envuelven.

### Sello de veredicto (signature component)

El componente que define el sistema. Píldora con el trío de color de su
veredicto, compuesta por un disco sólido con el símbolo en negativo más la
palabra. Existe en dos tamaños: el de tarjeta (0.8125rem, disco de 1.15rem) y
el de ficha (`--grande`: 1rem, disco de 1.6rem). El símbolo es texto (`✓ ◐ ✕
?`), no un icono, para que se copie y se lea sin depender de una fuente de
iconos.

### Resaltado de ingrediente (signature component)

Dentro de la lista de ingredientes, el que disparó el veredicto va en un
`<mark>` con el fondo y la tinta de su veredicto más un subrayado de 2px del
color pleno. Es la traducción visual del propósito del producto: no solo
decimos que contiene gelatina, señalamos dónde.

## Do's and Don'ts

### Do:

- **Do** aplicar el color de veredicto mediante la clase `.v .v--<estado>` en
  un contenedor, y consumirlo con `var(--tinta-v)` / `var(--fondo-v)` /
  `var(--linea-v)` adentro. Así un componente nuevo hereda el veredicto sin
  saber cuál es.
- **Do** dar a todo veredicto sus tres canales: símbolo, palabra y color.
- **Do** usar `--linea` y capas tonales para separar. Un borde de 1px resuelve
  casi todo lo que uno cree que necesita sombra.
- **Do** reservar un marco del tamaño de la miniatura cuando no hay foto, y
  fijar `width`/`height` en toda imagen, para que nada salte al cargar.
- **Do** mantener el anillo de foco `2px solid var(--foco)` idéntico en todo el
  sitio. Es la única señal de navegación por teclado.
- **Do** tratar "a revisar" como un veredicto de pleno derecho: mismo tamaño de
  sello, mismo lugar en la jerarquía, misma prominencia que los otros tres.

### Don't:

- **Don't** usar verde, ocre, bermellón o gris pizarra de veredicto en nada que
  no sea un veredicto — ni un botón, ni un link, ni un badge de marketing.
- **Don't** agregar sombras. Hay una sola en el sistema y ya tiene dueño.
- **Don't** usar `#000000`, `#ffffff` como fondo de página, ni grises de hue
  azul. Todos los neutros son cálidos.
- **Don't** poner el serif por debajo de 1.1rem.
- **Don't** esconder el motivo del veredicto detrás de un acordeón, un tooltip
  o un "ver más". El "por qué" es el producto.
- **Don't** ordenar los veredictos por otra cosa que apto → vegetariano →
  no apto → revisar. Ese orden es fijo en filtros, contadores y leyendas.
- **Don't** introducir una segunda familia tipográfica sin quitar una: son tres
  y ya cubren display, cuerpo y código.
