import { veredicto } from '@/lib/veredicto';

/** El veredicto en una pastilla. Símbolo + palabra + color, nunca color solo. */
export function Sello({
  estado,
  grande = false,
}: {
  estado: string;
  grande?: boolean;
}) {
  const v = veredicto(estado);
  return (
    <span className={`sello${grande ? ' sello--grande' : ''}`}>
      <span className="sello__simbolo" aria-hidden="true">
        {v.simbolo}
      </span>
      {v.etiqueta}
    </span>
  );
}

/** La clase que fija las variables de color del veredicto para todo un
 *  subárbol: la usan la tarjeta, el dictamen y los chips del filtro. */
export function claseVeredicto(estado: string): string {
  return `v v--${veredicto(estado).tono}`;
}
