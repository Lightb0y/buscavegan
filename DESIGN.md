---
name: buscavegan
description: Buscador de productos argentinos aptos veganos que muestra la evidencia detrás de cada veredicto, con la estética de un cartel de zócalo de góndola.
colors:
  stock: "#ffffff"
  stock-hundido: "#f1f1ef"
  stock-borde: "#e7e7e4"
  tinta: "#111111"
  tinta-media: "#5a5a57"
  tinta-tenue: "#6e6e6a"
  filete: "#d9d9d5"
  filete-fuerte: "#111111"
  foco: "#1b57c4"
  apto-campo: "#0b6b34"
  apto-sobre: "#ffffff"
  apto-tinta: "#0b6b34"
  vegetariano-campo: "#f0b323"
  vegetariano-sobre: "#1a1200"
  vegetariano-tinta: "#8a5a00"
  no-apto-campo: "#b4231a"
  no-apto-sobre: "#ffffff"
  no-apto-tinta: "#b4231a"
  revisar-campo: "#3f4a56"
  revisar-sobre: "#ffffff"
  revisar-tinta: "#3f4a56"
typography:
  display:
    fontFamily: "Archivo (var. wdth 75%), ui-sans-serif, system-ui, sans-serif"
    fontSize: "clamp(1.875rem, 1.3rem + 2.4vw, 3.25rem)"
    fontWeight: 700
    lineHeight: 1.05
    letterSpacing: "-0.02em"
    fontVariation: "font-stretch: 75%; text-transform: uppercase"
  headline:
    fontFamily: "Archivo (var. wdth 75%), ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.375rem"
    fontWeight: 700
    lineHeight: 1.05
    fontVariation: "font-stretch: 75%; text-transform: uppercase"
  title:
    fontFamily: "Archivo (var. wdth 75%), ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.0625rem"
    fontWeight: 700
    lineHeight: 1.15
    letterSpacing: "0.005em"
    fontVariation: "font-stretch: 75%; text-transform: uppercase"
  body:
    fontFamily: "Archivo, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
    fontFeature: "tabular-nums"
  label:
    fontFamily: "Archivo (var. wdth 87.5%), ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 700
    letterSpacing: "0.09em"
    fontVariation: "font-stretch: 87.5%; text-transform: uppercase"
  mono:
    fontFamily: "Chivo Mono, ui-monospace, monospace"
    fontSize: "0.8125em"
    fontWeight: 400
    letterSpacing: "-0.02em"
rounded:
  ninguno: "0px"
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
  riel-campo:
    backgroundColor: "transparent"
    textColor: "{colors.tinta}"
    rounded: "{rounded.ninguno}"
    padding: "0"
  sello-apto:
    backgroundColor: "{colors.apto-campo}"
    textColor: "{colors.apto-sobre}"
    rounded: "{rounded.ninguno}"
    padding: "0.75rem 0.25rem"
  sello-vegetariano:
    backgroundColor: "{colors.vegetariano-campo}"
    textColor: "{colors.vegetariano-sobre}"
    rounded: "{rounded.ninguno}"
    padding: "0.75rem 0.25rem"
  sello-no-apto:
    backgroundColor: "{colors.no-apto-campo}"
    textColor: "{colors.no-apto-sobre}"
    rounded: "{rounded.ninguno}"
    padding: "0.75rem 0.25rem"
  sello-revisar:
    backgroundColor: "{colors.revisar-campo}"
    textColor: "{colors.revisar-sobre}"
    rounded: "{rounded.ninguno}"
    padding: "0.75rem 0.25rem"
  marca-v:
    backgroundColor: "transparent"
    textColor: "{colors.tinta-media}"
    rounded: "{rounded.ninguno}"
    padding: "0.5rem 0.75rem"
  boton-mas:
    backgroundColor: "{colors.stock-hundido}"
    textColor: "{colors.tinta}"
    rounded: "{rounded.ninguno}"
    padding: "1rem"
  boton-mas-hover:
    backgroundColor: "{colors.tinta}"
    textColor: "{colors.stock}"
  dictamen:
    backgroundColor: "{colors.apto-campo}"
    textColor: "{colors.apto-sobre}"
    rounded: "{rounded.ninguno}"
    padding: "2rem 1.5rem"
---

# Design System: buscavegan

## Overview

**Creative North Star: "Zócalo de Góndola"**

buscavegan se ve como el cartel que un supermercado argentino cuelga del filo
del estante: cartón de imprenta bajo tubo fluorescente, tinta plana, y la
letra chica que la ley obliga a poner para que el número grande se pueda
comprobar. No es una landing que convence — es el dato que alguien lee
caminando, con el celular en una mano y el paquete en la otra. Este mundo
reemplazó por completo a un sistema anterior de papel kraft tibio y esquinas
curvas ("El Rótulo Honesto"); no queda nada de ese vocabulario en el código
servido y este archivo ya no lo describe.

De la tesis del cartel de zócalo sale todo lo demás. Los resultados no son
tarjetas flotando sobre un fondo: son tiras a sangre pegadas una contra otra
por un filete de 1px, como una corrida real de góndola. Nada tiene radio,
nada tiene sombra, y el color existe únicamente donde codifica uno de los
cuatro veredictos — ni el cromo, ni la navegación, ni un botón lo toman
prestado, tampoco en modo oscuro. La escena decide la luz: el modo claro es
el principal, sobre un stock blanco frío, porque la persona que esto sirve
está parada en un pasillo iluminado por tubos, no leyendo un libro a la luz
de una lámpara cálida.

La tipografía es una sola familia variable (Archivo, de la fundición
porteña Omnibus-Type) usada en dos anchos: condensada para todo lo que hay
que leer barriendo con la vista — nombres de producto, la palabra del
veredicto, la consulta de búsqueda —, y ancho normal para el texto corrido.
Una mono (Chivo Mono) aparece solo en códigos: EAN y RNPA. La densidad es
alta — 7.397 productos que hay que poder recorrer sin fatiga — y la única
concesión de espacio es la ficha de un solo producto, donde el veredicto se
queda con el frame entero en vez de ser una pastilla en un rincón.

**Key Characteristics:**
- Cero radio, cero sombra decorativa: el filete de 1px es el único separador.
- Stock blanco frío y tinta neutra; ningún neutro tiene temperatura cálida.
- Cuatro tintas planas de veredicto, únicas cromáticas del sistema, en modo claro y oscuro.
- Una sola familia tipográfica variable, condensada para lo que se barre, normal para lo que se lee.
- El motivo del veredicto ("la letra chica") es contenido de primera clase, nunca oculto.

## Colors

Una base casi acromática — blanco, tinta y filete — interrumpida solo por
los cuatro veredictos. No hay color de marca: el isotipo y la navegación
viven enteramente en la escala de tinta.

### Primary

Los cuatro veredictos. Cada uno es un **trío** de variables CSS que un
contenedor con clase `.v--<estado>` fija para todo su subárbol —
`--campo` (la tinta plana del bloque), `--sobre` (lo que se imprime encima
del campo) y `--tinta-v` (el mismo veredicto usado como texto sobre el
stock). Son tres valores y no uno porque el ámbar no puede servir a los dos
usos con el mismo hex: como campo lleva tinta encima y llega a 11:1; como
texto sobre blanco tiene que bajar a `#8a5a00` para llegar a 5,9:1.

- **Verde Apto** (`#0b6b34` campo / `#ffffff` sobre / `#0b6b34` tinta): el
  veredicto "apto vegano". Sello de tira, dictamen de ficha, ícono de
  fuente con evidencia.
- **Ámbar Vegetariano** (`#f0b323` campo / `#1a1200` sobre / `#8a5a00`
  tinta): "vegetariano, no vegano". El campo es un amarillo saturado —
  necesita tinta casi negra encima para leerse — pero como texto baja a un
  ocre oscuro para no perder contraste sobre blanco.
- **Rojo No Apto** (`#b4231a` campo / `#ffffff` sobre / `#b4231a` tinta):
  "no apto". Rojo de sello de rechazo, no de error de sistema.
- **Gris Revisar** (`#3f4a56` campo / `#ffffff` sobre / `#3f4a56` tinta):
  "a revisar". Desaturado a propósito, pero nunca desjerarquizado: mismo
  tamaño de sello, mismo lugar, misma prominencia que los otros tres.

**En modo oscuro** los cuatro campos se aclaran para sostener el contraste
(`#2f9c58`, `#e0a520`, `#e35a4e`, `#7c8794`), pero la ley de paleta rige
igual: ningún tono de veredicto se filtra al cromo. El campo de "no apto"
se movió de `#d94236` a `#e35a4e` porque el primero daba 4,48:1 contra su
tinta de encima — por debajo del piso de 4,5:1 que el proyecto se fijó — y
un escalón más claro lo lleva a 5,47:1.

### Neutral

- **Stock** (`#ffffff` / oscuro `#0e0e0d`): el fondo de todo el sitio.
  Blanco frío de cartón de imprenta, no papel tibio.
- **Stock Hundido** (`#f1f1ef` / oscuro `#171716`): miniaturas sin foto,
  fondo del pie, fila de "ver más", fondo de la fila al pasar el mouse.
- **Stock Borde** (`#e7e7e4` / oscuro `#232322`): reservado en el token
  pero sin uso propio distinto de `--filete` en el CSS actual.
- **Tinta** (`#111111` / oscuro `#f4f4f2`): texto principal, fondos
  invertidos (botón "ver más" en hover, "saltar al contenido").
- **Tinta Media** (`#5a5a57` / oscuro `#a8a8a3`): navegación en reposo,
  metadatos de marca/categoría, texto del pie.
- **Tinta Tenue** (`#6e6e6a` / oscuro `#8e8e89`): la letra chica —
  `.tira__prueba`, placeholders, teclas de atajo. Se verificó a 5,3:1 sobre
  el stock porque acá la letra chica es contenido de primera clase: si no
  llega a AA, el argumento del producto no se lee.
- **Filete** (`#d9d9d5` / oscuro `#2b2b29`): el único separador del
  sistema — entre tiras, entre bloques de datos, bajo inputs.
- **Filete Fuerte** (`#111111` / oscuro `#f4f4f2`): el borde de 2px del
  encabezado, el riel de búsqueda, el pie y los títulos de sección
  (`.bloque`, `.prosa h2`) — el filo del estante, no una línea cualquiera.

### Tertiary

- **Foco** (`#1b57c4` / oscuro `#8fb2ff`): exclusivamente el anillo de
  `:focus-visible`. Es azul justamente porque ningún veredicto lo es: el
  indicador de "estás acá" no se puede confundir nunca con el dato del
  producto.

### Named Rules

**La Ley de Paleta.** Un color no puede aparecer si no codifica un
veredicto. Los cuatro campos de apto/vegetariano/no_apto/revisar son las
únicas cromáticas del sistema, en modo claro y en modo oscuro. Test: si un
elemento saturado no responde a "¿esto es apto?", está mal pintado.

**La Regla del Trío.** Cada veredicto se declara una sola vez, como trío
`--campo` / `--sobre` / `--tinta-v`, mediante una clase `.v--<estado>` en
un ancestro. Un componente nuevo consume las tres variables sin saber cuál
veredicto le tocó; nunca se hardcodea un hex de veredicto en un componente.

**El Piso AA.** Todo par tinta/fondo del sistema se verificó contra 4,5:1.
No es una aspiración: es la razón por la que la letra chica sube a
`#6e6e6a` en vez de quedarse en un gris más liviano, y por la que el rojo
oscuro de "no apto" se movió de hex apenas por debajo del piso a uno que lo
supera. Un color nuevo que no llegue a 4,5:1 contra su fondo no entra al
sistema, sea cual sea su rol.

## Typography

**Display / Body Font:** Archivo (variable, eje `wdth`), con `ui-sans-serif,
system-ui, sans-serif` de respaldo.
**Label/Mono Font:** Chivo Mono, con `ui-monospace, monospace` de respaldo.

**Character:** Una sola grotesca condensable haciendo dos trabajos. Al 75%
de ancho y en mayúsculas es la voz de todo lo que se barre con la vista —el
nombre de un producto argentino entero, sin puntos suspensivos, el
veredicto, la consulta de búsqueda—; al 100% es la voz neutra del texto
corrido. La mono aparece solo donde el contenido es literalmente un código,
nunca para dar aire "técnico" a prosa que no lo es.

### Hierarchy

- **Display** (700, `clamp(1.875rem, 1.3rem + 2.4vw, 3.25rem)`, 1.05,
  condensada 75%, mayúsculas): el `h1` de cada página (`.titular h1`). La
  frase del dictamen de ficha usa la misma voz a una escala propia
  (`clamp(1.5rem, 1.1rem + 1.7vw, 2.5rem)`), porque ahí compite con un
  ícono de 32px y no con el resto de la página.
- **Headline** (700, `1.375rem`, 1.05, condensada 75%, mayúsculas): los
  `h2` de aviso y de sección de prosa (`.aviso-bloque h2`, `.prosa h2`,
  con filete superior de 2px).
- **Title** (700, `1.0625rem`, 1.15, condensada 75%, mayúsculas): el
  nombre de producto en la tira y en el índice de categorías
  (`.tira__nombre`, `.indice__nombre`).
- **Body** (400, `1rem`, 1.5): texto corrido, con `font-variant-numeric:
  tabular-nums` heredado del `body` — los EAN, los conteos y los
  porcentajes se comparan en columna.
- **Label** (700, `0.75rem`, `0.09em`, condensada 87,5%, mayúsculas):
  encabezados de bloque en la ficha ("POR QUÉ", "DE DÓNDE SALE ESTE
  DATO"), la palabra del sello (`.sello__palabra`), la etiqueta de la
  cifra (`.cifra__etiqueta`).
- **Mono** (400, `0.8125em`, `-0.02em`): exclusivamente `.codigo` — el EAN
  en la ficha de producto. No se usa en ningún otro lugar del sitio.

### Named Rules

**La Regla de la Condensada Legible.** El eje `wdth` de Archivo comprime al
75% únicamente títulos, nombres de producto y la palabra del veredicto —
nunca párrafos. Es lo que permite que un nombre de producto argentino entre
entero, en mayúsculas, sin recortarse ni encogerse fuera de escala.

**La Regla de la Cifra en Columna.** `font-variant-numeric: tabular-nums`
es global en `body`. Los EAN, conteos y porcentajes tienen que poder
compararse en columna; nunca se revierte a cifras proporcionales.

## Layout

Un contenedor único (`.contenedor`) de `72rem` máximo con `1rem` de padding
lateral, usado por todas las páginas. La escala de espaciado es de base
4px, expuesta como `--e1`…`--e8` (`0.25rem` → `4.5rem`) y nombrada por
función, no por medida.

El riel de búsqueda es *sticky* y a sangre completa (`position: sticky;
top: 0`), con un módulo propio, `--riel` (`5.5rem`, `4.25rem` bajo
`34rem`), que además fija el ancho del bloque de veredicto en la corrida:
toda la tira deriva sus columnas de ese único módulo, así la corrida entera
es un sistema reglado y no una pila de cajas sueltas. Al scrollear más de
120px el riel se condensa a una banda fina que conserva la consulta y la
leyenda de filtro — la única transformación con movimiento del sitio, para
no perder el filtro de vista mientras se barre la lista.

La corrida de resultados es una lista (`.corrida`) de tiras (`.tira`) en
grid de tres columnas (`--riel` / `3.25rem` / resto), sin gap: se pegan una
contra otra por un filete de 1px inferior. Bajo `34rem` la columna de foto
se oculta y la tira pasa a dos columnas. La leyenda de veredictos es grilla
de 2 columnas en móvil y 4 desde `46rem` — nunca flex, porque
"VEGETARIANO" es una sola palabra que no puede encogerse por debajo de su
ancho mínimo sin desbordar. En la ficha de producto, a partir de `60rem` el
cuerpo pasa a `minmax(0, 1fr) 20rem` con la evidencia secundaria en la
columna lateral; por debajo, la evidencia queda debajo del contenido
principal.

### Named Rules

**La Regla del Riel Único.** Toda medida de la corrida —ancho del bloque
de veredicto, columnas de la tira— deriva del módulo `--riel`. Cambiarlo
en un solo lugar reordena la corrida entera sin tocar cada componente.

**La Regla del Marco Fijo.** Todo producto sin foto recibe un marco del
mismo tamaño que la miniatura (`2.5rem` en la tira, `5rem` en la cabecera
de ficha), con un patrón rayado tenue en vez de vacío. Sin esto la corrida
se desalinea producto por producto, porque solo ~82% del catálogo tiene
imagen.

## Elevation & Depth

Plano, sin excepción. No hay ni una sola sombra decorativa en el
sistema — ni en la corrida, ni en el riel, ni en los botones. La
profundidad y la separación se construyen enteramente con **filetes de
1px** y dos capas de stock (stock / stock hundido). El único
`box-shadow` del CSS es funcional, no decorativo: el anillo de foco
(`:focus-visible`) y el subrayado grueso de navegación activa
(`inset 0 -2px 0`).

### Named Rules

**La Regla de Cero Sombra.** Ningún elemento del sistema —tira, sello,
input, botón, panel de ficha— usa `box-shadow` para levantarse del stock.
Todo elemento nuevo que "necesite" profundidad recibe un filete o un
cambio de capa tonal, nunca una sombra.

**La Regla del Frame Entero.** En la corrida el veredicto es una columna
angosta de ancho fijo (`--riel`) porque compite con miles de filas. En la
ficha de un solo producto no hay esa competencia: el `.dictamen` toma el
color del veredicto como fondo de la sección entera, ocupando todo el
ancho del frame. Este contraste de escala —columna en la lista, banda
completa en la ficha— es la firma del sistema y no se ablanda a una
pastilla ni en un lugar ni en el otro.

## Shapes

Cero radio en todo el sistema (`border-radius: 0` implícito; ningún
componente lo declara). No hay esquinas curvas en ningún elemento: tiras,
sellos, inputs, botones, chips de filtro y el marco de "ver más" son todos
rectángulos de filo vivo. Los únicos bordes del sistema son filetes de
1px, salvo el filete fuerte de 2px que marca los umbrales estructurales
(encabezado, riel, pie, títulos de sección de prosa) y el borde inferior
de 2px de la tecla de atajo, que imita el relieve de una tecla real.

## Components

### Buttons

- **Shape:** rectángulo de filo vivo, sin radio ni borde propio.
- **"Ver más" (`.mas`):** fondo stock hundido, texto en tinta, condensada
  87,5%, `0.875rem`, mayúsculas, ancho completo, padding `1rem`. En hover
  invierte a fondo tinta / texto stock.
- **Botones de icono** ("limpiar búsqueda", `.riel__limpiar`): sin fondo
  ni borde en reposo; en hover toman fondo tinta y texto stock, igual que
  "ver más" — la misma inversión tinta/stock es el único feedback de hover
  del sistema.
- **Enlace-botón** (`.enlace-boton`, "Limpiar todo"): sin fondo, subrayado
  con `--filete`, pasa a `currentColor` en hover.

### Chips

- **Marca de veredicto (`.marca-v`):** checkbox real oculto detrás de una
  etiqueta con borde de 1px `--filete` y un cuadrito indicador
  (`.marca-v__muestra`) con borde del color del veredicto. Tabulable,
  activable con espacio, anunciado por lectores de pantalla.
- **State:** activo (`input:checked`) toma el trío completo del veredicto
  — fondo `--campo`, texto `--sobre`, y el cuadrito se rellena con
  `--sobre`. Apagado queda en filete con el cuadrito vacío: el estado
  nunca depende solo del color.
- **Filtros secundarios (`.tamiz__opcion`):** checkbox nativo con
  `accent-color: var(--ink)`, sin trío de veredicto — son filtros de
  atributo del producto, no de veredicto, y usan la escala neutra.

### Cards / Containers — la Tira

- **Corner Style:** ninguno.
- **Background:** stock; stock hundido en hover.
- **Shadow Strategy:** ninguna (ver Elevation).
- **Border:** filete de 1px inferior únicamente; no hay borde lateral ni
  superior propio — el filete superior de la primera tira lo pone
  `.corrida`.
- **Internal Padding:** `0.75rem 1rem` (`0.75rem` bajo `34rem`).
- El link del nombre cubre la tira entera con un `::after` absoluto para
  que el área de toque sea grande, pero el texto accesible del link sigue
  siendo solo el nombre del producto. El anillo de foco se pinta sobre la
  tira entera (`outline-offset: -2px`), no sobre el texto del link.

### Inputs / Fields

- **Riel de búsqueda (`.riel__campo`):** sin borde ni fondo propios —
  vive directamente sobre el stock del riel. Condensada 75%,
  `clamp(1.5rem, 1.05rem + 1.9vw, 2.5rem)`, mayúsculas; se achica a
  `clamp(1.125rem, 1rem + 0.6vw, 1.375rem)` cuando el riel está
  condensado.
- **Focus:** el anillo se pinta sobre el riel entero
  (`box-shadow: inset 0 0 0 2px var(--foco)`), no sobre el input — el
  campo no tiene borde propio, así que un anillo ceñido al texto no se
  vería.
- **Selector de categoría (`.tamiz__selector`):** borde de 1px `--filete`,
  fondo stock, `0.8125rem`, sin radio.

### Navigation

- Links en tinta media, `0.875rem`, peso 500, sin subrayado.
- **Hover / activo:** tinta plena más `box-shadow: inset 0 -2px 0
  var(--filete-fuerte)` — un subrayado grueso, nunca color de veredicto.
- El encabezado no es sticky ni colapsa en móvil: envuelve (`flex-wrap`).

### El Sello (signature component)

El bloque de veredicto que define el sistema. Dos formas: `sello--bloque`
(columna en la tira, ancho fijo `--riel`, icono + palabra apilados) y
`sello--linea` (icono + palabra en línea, para usos secundarios). Las tres
señales —**icono dibujado, palabra y color de campo**— viajan siempre
juntas; ninguna variante puede quitar una. Los iconos son SVG propios
(`Iconos.tsx`) sobre grilla de 16, trazo de 2px, terminaciones redondeadas
— reemplazaron a glifos Unicode (`✓ ◐ ✕ ?`) que se veían distinto por
plataforma y no compartían ni grosor ni caja óptica entre sí; el código
deja constancia explícita de por qué no vuelven.

### El Dictamen (signature component)

En la ficha de un solo producto, el veredicto deja de ser una columna
angosta y se convierte en una sección (`.dictamen`) que toma el color de
campo del veredicto como fondo de todo el ancho del frame, con la frase en
escala de titular y un icono de 32px. "A revisar" ocupa exactamente el
mismo espacio, con el mismo tratamiento, que los otros tres estados.

### Resaltado de ingrediente

Dentro de la lista de ingredientes de la ficha, el ingrediente que
disparó el veredicto va en un `<mark>` con el fondo `--campo` y el texto
`--sobre` del veredicto activo, en negrita. Es la traducción visual del
propósito del producto: no solo se dice que contiene gelatina, se señala
dónde.

## Do's and Don'ts

### Do:

- **Do** aplicar el veredicto con una clase `.v--<estado>` en un
  contenedor ancestro y consumirlo adentro con `var(--campo)` /
  `var(--sobre)` / `var(--tinta-v)`. Ningún componente hardcodea un hex de
  veredicto.
- **Do** dar a todo veredicto sus tres canales a la vez: icono dibujado,
  palabra y color de campo.
- **Do** tratar "a revisar" como un veredicto de pleno derecho: mismo
  tamaño de sello, mismo lugar en la jerarquía, misma prominencia — nunca
  una versión apagada o más chica de los otros tres.
- **Do** dejar que el dictamen de la ficha ocupe el ancho completo del
  frame; no reducirlo a una pastilla ni a un badge de esquina.
- **Do** usar filetes de 1px (2px en los umbrales estructurales) y capas
  de stock para separar. Nunca sombra.
- **Do** reservar un marco del tamaño de la miniatura cuando no hay foto,
  y fijar `width`/`height` en toda imagen, para que nada salte al cargar.
- **Do** mantener el anillo de foco `2px solid var(--foco)` como única
  señal de navegación por teclado en todo el sitio.
- **Do** verificar cualquier color nuevo de veredicto contra 4,5:1 en
  ambos usos (campo con tinta encima, texto sobre stock) antes de sumarlo.

### Don't:

- **Don't** usar verde, ámbar, rojo o gris de veredicto en nada que no
  sea un veredicto — ni un botón, ni un link, ni un acento decorativo, ni
  en modo oscuro.
- **Don't** agregar `border-radius` ni `box-shadow` decorativo a ningún
  elemento. El sistema es de filo vivo y plano por invariante, no por
  omisión temporal.
- **Don't** ablandar "a revisar" — ni en tamaño, ni en color, ni en orden
  — porque es un estado legítimo del producto, no un error a esconder.
- **Don't** reintroducir glifos Unicode (`✓ ◐ ✕ ?`) como símbolo de
  veredicto. El código los sacó a propósito porque no comparten trazo ni
  caja óptica entre plataformas; el icono dibujado es el sistema.
- **Don't** esconder el motivo del veredicto detrás de un acordeón, un
  tooltip o un "ver más". La letra chica es el producto.
- **Don't** ordenar los veredictos por otra cosa que apto → vegetariano →
  no apto → revisar. Ese orden es fijo en filtros, contadores y leyendas.
- **Don't** introducir una segunda familia tipográfica. Archivo cubre
  título, cuerpo y label en sus dos anchos; Chivo Mono cubre el código.
