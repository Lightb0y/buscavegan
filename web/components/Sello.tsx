import { IconoVeredicto } from './Iconos';
import { veredicto } from '@/lib/veredicto';
import type { Estado } from '@/lib/tipos';

/** El bloque de veredicto: tinta plana, icono dibujado y palabra.
 *
 *  No es una pastilla flotando sobre la tarjeta sino un campo lleno que ocupa
 *  el filo izquierdo de la tira, como la bandera de un cartel de góndola. Por
 *  eso tiene ancho fijo: apilados en la corrida forman una columna de color
 *  continua que se barre con la vista sin leer una sola palabra.
 *
 *  Las tres señales —icono, palabra y color— viajan siempre juntas. Ninguna
 *  variante puede quitar una.
 */
export function Sello({
  estado,
  forma = 'bloque',
}: {
  estado: string;
  forma?: 'bloque' | 'linea';
}) {
  const v = veredicto(estado);
  return (
    <span className={`sello sello--${forma} ${claseVeredicto(estado)}`}>
      <IconoVeredicto estado={v.estado} tam={forma === 'bloque' ? 20 : 15} />
      <span className="sello__palabra">{v.etiqueta}</span>
    </span>
  );
}

/** Fija las variables del veredicto para todo un subárbol: `--campo` es la
 *  tinta plana, `--sobre` lo que se imprime encima. Un componente nuevo
 *  hereda el veredicto sin saber cuál es. */
export function claseVeredicto(estado: string): string {
  return `v v--${veredicto(estado).tono}`;
}

/** El nombre del estado, para atributos y clases. */
export function tono(estado: string): Estado {
  return veredicto(estado).estado;
}
