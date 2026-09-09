/** Medición de uso. Lo mínimo para dejar de trabajar a ciegas.
 *
 *  POR QUÉ EXISTE
 *  --------------
 *  Hasta ahora el proyecto no tenía forma de saber si alguien lo usaba. Se
 *  podía discutir qué producto agregar, qué filtro sobra o si conviene seguir
 *  invirtiendo, siempre sin un solo dato. Esto responde tres preguntas y
 *  ninguna más:
 *
 *    1. ¿Entra alguien?          → páginas vistas (automático)
 *    2. ¿Vuelve?                 → visitantes vs. visitas (automático)
 *    3. ¿Qué busca y no está?    → `busqueda_sin_resultados` (acá abajo)
 *
 *  La tercera es la que más vale y la que ninguna herramienta trae de fábrica:
 *  es, literalmente, la lista de qué productos hay que cargar, escrita por la
 *  gente que los fue a buscar.
 *
 *  QUÉ NO SE MIDE, A PROPÓSITO
 *  ---------------------------
 *  Vercel Analytics no usa cookies ni huella de dispositivo, así que no hace
 *  falta un cartel de consentimiento y no hay nada que asociar a una persona.
 *  Acá además:
 *
 *  - No se manda una búsqueda que SÍ tuvo resultados. Saber que alguien buscó
 *    "oreo" y lo encontró no cambia ninguna decisión; saber que buscó algo y
 *    no estaba, sí.
 *  - No se manda cuando el vacío lo causó un filtro puesto por la persona
 *    (eso ya lo detecta el "rescate" de la pantalla). Sería ruido: el producto
 *    puede estar en la base perfectamente.
 *  - No se manda nada mientras se tipea, solo cuando la persona frenó.
 *  - El texto se recorta y se normaliza: es un término de góndola, no un campo
 *    libre donde alguien vaya a escribir un dato personal, pero se limita
 *    igual por las dudas.
 *
 *  EL TOPE DEL PLAN
 *  ----------------
 *  El plan gratuito de Vercel corta en unos pocos miles de eventos por mes.
 *  Para la pregunta de esta etapa —¿lo usa alguien?— sobra: si se llega al
 *  tope, esa es justamente la respuesta que hacía falta. Por eso los eventos
 *  se cuidan tanto: cada uno tiene que valer su lugar.
 */
import { track } from '@vercel/analytics';

/** Términos ya reportados en esta pestaña. Alguien que corrige una letra por
 *  vez generaría un evento por intento; solo interesa el término, una vez. */
const YA_CONTADO = new Set<string>();

/** Tope de largo del término. Una búsqueda de góndola real no pasa de esto. */
const LARGO_MAXIMO = 60;

function normalizar(texto: string): string {
  return texto.trim().toLowerCase().replace(/\s+/g, ' ').slice(0, LARGO_MAXIMO);
}

/** Alguien buscó algo que no está en el catálogo.
 *
 *  Solo se llama cuando el vacío es del catálogo y no de un filtro: quien
 *  llama tiene que haber descartado ese caso antes (ver `rescate` en el
 *  buscador).
 */
export function busquedaSinResultados(termino: string): void {
  const q = normalizar(termino);
  // Menos de tres letras es alguien a mitad de escribir, no una búsqueda.
  if (q.length < 3 || YA_CONTADO.has(q)) return;
  YA_CONTADO.add(q);

  try {
    track('busqueda_sin_resultados', { termino: q });
  } catch {
    // Medir nunca puede romper la pantalla. Si el script no cargó —un
    // bloqueador, una red caída, un build fuera de Vercel— la búsqueda tiene
    // que seguir funcionando igual.
  }
}
