/** El vocabulario del veredicto, en un solo lugar.
 *
 *  Regla de accesibilidad que no se negocia: el veredicto NUNCA se comunica
 *  solo con color. Cada uno lleva además un símbolo y una palabra, porque un
 *  8% de los varones no distingue rojo de verde y este dato es justamente el
 *  que la persona vino a buscar.
 *
 *  El símbolo no vive acá: lo dibuja `components/Iconos.tsx` como SVG sobre
 *  una grilla de 16 con trazo de 2. Antes era un glifo Unicode por veredicto
 *  (`✓ ◐ ✕ ?`), que se ve distinto en cada plataforma y no comparte ni grosor
 *  ni caja óptica con los demás: era tipografía haciendo de sistema de
 *  iconos. Los cuatro campos quedaron sin uso al migrar y se borraron, para
 *  que nadie vuelva a tomarlos de acá por costumbre.
 */
import type { Estado } from './tipos';

export interface Veredicto {
  estado: Estado;
  /** Lo que se lee en la tarjeta: corto, sin ambigüedad. */
  etiqueta: string;
  /** Título de la ficha del producto y del <title> de la página. */
  titular: string;
  /** Qué significa exactamente, en una frase. */
  explicacion: string;
  /** Sufijo de las variables CSS: --v-apto-tinta, --v-apto-fondo, etc. */
  tono: string;
}

export const VEREDICTOS: Record<Estado, Veredicto> = {
  apto: {
    estado: 'apto',
    etiqueta: 'Apto vegano',
    titular: 'es apto vegano',
    explicacion:
      'No encontramos ningún ingrediente de origen animal en su lista.',
    tono: 'apto',
  },
  vegetariano: {
    estado: 'vegetariano',
    etiqueta: 'Vegetariano',
    titular: 'es vegetariano, pero no vegano',
    explicacion:
      'Tiene ingredientes de origen animal que no implican matar al animal ' +
      '(leche, huevo, miel), pero no es vegano.',
    tono: 'vegetariano',
  },
  no_apto: {
    estado: 'no_apto',
    etiqueta: 'No apto',
    titular: 'no es apto vegano',
    explicacion:
      'Tiene al menos un ingrediente de origen animal incompatible con una ' +
      'dieta vegana.',
    tono: 'no-apto',
  },
  revisar: {
    estado: 'revisar',
    etiqueta: 'A revisar',
    titular: 'no lo sabemos todavía',
    explicacion:
      'No tenemos datos suficientes, o la lista de ingredientes tiene algo ' +
      'ambiguo que puede ser de origen animal o vegetal. Preferimos decirte ' +
      'que no sabemos antes que arriesgar.',
    tono: 'revisar',
  },
};

export const ORDEN_ESTADOS: Estado[] = [
  'apto',
  'vegetariano',
  'no_apto',
  'revisar',
];

export function veredicto(estado: string): Veredicto {
  return VEREDICTOS[estado as Estado] ?? VEREDICTOS.revisar;
}

/** Miles con punto, como se escribe en Argentina. */
export function numero(n: number): string {
  return n.toLocaleString('es-AR');
}

export function porcentaje(parte: number, total: number): string {
  if (!total) return '0%';
  return `${((100 * parte) / total).toFixed(1).replace('.', ',')}%`;
}
