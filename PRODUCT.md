# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Personas veganas o vegetarianas en Argentina que necesitan saber, producto por
producto, si algo es apto para su dieta — en la góndola física o mirando el
carrito de un supermercado online, con el celular en la mano. Buscan una
respuesta rápida pero verificable, no una lista de marketing curada por una
marca.

## Product Purpose

Clasificar productos argentinos como aptos veganos, vegetarianos, no aptos o
"a revisar", mostrando siempre de dónde sale el veredicto. Éxito no es "tener
un veredicto para todo": es que cada veredicto tenga una fuente que se pueda
señalar, y que la incertidumbre real se muestre como incertidumbre en vez de
disfrazarse de certeza.

## Positioning

Cualquiera puede publicar una lista de productos veganos. La diferencia de
buscavegan es que cada resultado expone su evidencia — certificación oficial,
lectura de la lista de ingredientes, sello del supermercado, o (marcado como
tal) una estimación por el nombre — y nunca colapsa un ingrediente ambiguo en
un "apto" para parecer más completo. Ningún competidor conocido publica ese
nivel de trazabilidad por producto.

## Operating Context

El dato final sale de un pipeline en Python (Open Food Facts, el registro de
ANMAT, y las fichas públicas de ingredientes de Carrefour, Vea, Día, Jumbo y
Disco) que corre semanalmente vía GitHub Actions y exporta a un catálogo
estático que consume el sitio web. El sitio (`web/`, Next.js con export
estático en Vercel) es la cara pública; una app interna en Streamlit
(`app.py`) sirve para auditar la cola de revisión manual y no es visible al
usuario final.

## Capabilities and Constraints

- El catálogo completo (~7.400 productos) se baja entero al navegador
  (~236 KB comprimidos) y la búsqueda corre en memoria del lado del cliente:
  sin backend, sin base de datos en producción, sin costo por request.
- Cada ficha de producto se pre-genera como página estática en el build —
  necesario para que el motivo del veredicto sea indexable por buscadores.
- "Apto" significa **vegano** (sin ingredientes de origen animal). No implica
  *cruelty-free*: el testeo en animales no está en ninguna de las fuentes de
  datos, y el sitio lo aclara explícitamente para no generar una lectura
  errónea.
- Un ingrediente ambiguo (puede ser animal o vegetal según el fabricante,
  p. ej. margarina a secas, lecitina, INS 471) nunca produce "apto": produce
  "a revisar". Esta regla de seguridad es una decisión de producto, no solo
  técnica, y ninguna iteración de diseño debe ocultar o suavizar el estado "a
  revisar" para que el catálogo se vea más resuelto de lo que está.
- Los datos se actualizan semanalmente vía un workflow automático; el sitio no
  tiene ni necesita un panel de administración.

## Brand Commitments

El nombre "buscavegan" es lo único fijado. No hay logo, paleta ni tono de voz
preexistentes: el sistema visual actual (papel/tinta, tipografía serif para
títulos, colores de veredicto reservados exclusivamente a ese uso) es una
propuesta de diseño, no un compromiso — Impeccable puede refinarlo o
reemplazarlo libremente.

## Evidence on Hand

- 7.397 productos clasificados; 71,8% con evidencia real sobre el producto
  (certificación, ingredientes leídos, sello), no una estimación por nombre.
- Léxico de clasificación auditado a mano contra el Código Alimentario
  Argentino y las fuentes de datos.
- No hay imágenes de marca propias; las fotos de producto vienen de Open Food
  Facts cuando existen (~82% de cobertura) y no siempre están.
- No fabricar testimonios, reseñas, precios ni cifras de uso: el proyecto es
  de código y datos abiertos, sin analítica de usuarios implementada todavía.

## Product Principles

1. **Nunca mentir hacia "apto".** Ante la duda, el sistema se equivoca hacia
   "a revisar", nunca hacia afirmar que algo es vegano sin evidencia.
2. **La evidencia es el producto, no un detalle.** El "por qué" de cada
   veredicto va tan visible como el veredicto mismo — nunca detrás de un clic
   opcional ni relegado a letra chica.
3. **El dato manda sobre la estética.** Cualquier decisión visual que oscurezca
   de dónde sale un veredicto, o que haga que "a revisar" se lea como un
   estado menor o vergonzoso, va en contra del propósito del producto.
4. **Costo de operación cero.** El sitio público no depende de un servidor
   que alguien tenga que pagar o mantener corriendo.
5. **Abierto por diseño.** Código y metodología públicos; un error se corrige
   señalándolo, no ocultándolo.

## Accessibility & Inclusion

Estándar fijo, no negociable: contraste AA (4.5:1) en todo texto, foco de
teclado visible en todo elemento interactivo, y el veredicto (apto/no
apto/vegetariano/a revisar) **nunca se comunica solo con color** — siempre
lleva además un símbolo y una palabra, porque es el dato crítico que la
persona vino a buscar y aproximadamente 8% de los hombres no distingue rojo de
verde.
