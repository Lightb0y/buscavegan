---
version: 1
slug: "web-app-page-tsx"
primary_target: "web/app/page.tsx"
related_targets: ["web/app/globals.css","web/components/Ficha.tsx","web/app/p/[slug]/page.tsx","web/app/categoria/[...ruta]/page.tsx"]
---

Scope: el sitio público de buscavegan (home/buscador, ficha de producto, listado
de categoría, cómo funciona). Modo del visitante: Operate.

Audiencia: persona vegana o vegetariana parada en la góndola, celular en una
mano y el paquete en la otra, luz fluorescente y quince segundos.
Trabajo: saber si eso es apto vegano y poder verificar por qué.
Acción: leer el veredicto, leer la evidencia, abrir la ficha o filtrar.
Prueba: el motivo real de cada veredicto, ya calculado por el pipeline.
Restricciones: export estático, sin backend; catálogo de 7.397 productos que
baja entero al navegador; AA como piso; el veredicto siempre con símbolo,
palabra y color.

Momento memorable: la corrida de tiras deja una columna de veredicto que se
barre a velocidad de caminata, y en la ficha el veredicto se queda con el
frame entero.

Decisiones abiertas: ninguna bloqueante.

## Direction contract

THESIS: el resultado es el cartel del estante — un dato que se lee caminando y
la letra chica obligatoria que lo hace auditable, en el lugar donde el cartel
real pone el precio por unidad. Rechaza el grid SaaS de tarjetas flotantes con
sidebar de filtros.

OWN-WORLD: stock blanco frío y tinta neutra casi negra, filete de 1px, cero
sombra y cero radio. Cuatro tintas planas de veredicto, únicas cromáticas del
sistema. Archivo variable (eje de ancho) condensada para nombres; Chivo Mono
para la letra chica. Tiras a sangre pegadas una contra otra.

STORY: entiende el veredicto de un vistazo, cree porque la evidencia va pegada
abajo y no detrás de un clic, y abre la ficha o filtra.

FIRST VIEWPORT: riel de búsqueda a sangre arriba con la consulta en condensada
grande; debajo la leyenda-filtro de los cuatro veredictos; después la corrida
de tiras: bloque de veredicto a la izquierda en tinta plana con símbolo y
palabra, nombre en condensada de caja alta, marca y categoría en la línea
secundaria, y el motivo en mono bajo un filete.

FORM: Zócalo de Góndola, candidato 4 de mi lista ordenada, seed f0f3166a.

FINISH: unreviewed and undocumented is unfinished; this build ends with the
finish review, the verdict, DESIGN.md, and every shipping raster carrying its
provenance
