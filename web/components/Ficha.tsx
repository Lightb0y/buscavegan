import Link from 'next/link';

import { veredicto } from '@/lib/veredicto';

import { claseVeredicto, Sello } from './Sello';

export interface DatosFicha {
  slug: string;
  nombre: string;
  marca?: string;
  estado: string;
  fuente: string;
  imagen?: string;
  motivo?: string;
}

/** La tarjeta de resultado.
 *
 *  Jerarquía deliberada: veredicto, nombre, y después el porqué. El porqué es
 *  lo que distingue a este proyecto de cualquier lista de productos veganos,
 *  así que va en la tarjeta y no escondido detrás de un clic.
 */
export function Ficha({
  p,
  fuenteLegible,
}: {
  p: DatosFicha;
  fuenteLegible: Record<string, string>;
}) {
  return (
    <li className={`ficha ${claseVeredicto(p.estado)}`}>
      <div className="ficha__marco">
        {p.imagen ? (
          // Con `output: export` no hay optimizador de imágenes, así que va un
          // <img> honesto: OFF ya las sirve chicas y con medidas fijas no hay
          // salto de layout cuando cargan.
          // eslint-disable-next-line @next/next/no-img-element
          <img
            className="ficha__miniatura"
            src={p.imagen}
            alt=""
            width={52}
            height={52}
            loading="lazy"
            decoding="async"
          />
        ) : (
          <div className="ficha__miniatura ficha__sinfoto" aria-hidden="true">
            ❧
          </div>
        )}
        {/* Decorativo a propósito: la píldora de abajo ya dice el veredicto en
            palabras, así que repetirlo acá solo agregaría ruido al lector de
            pantalla. */}
        <span className="ficha__insignia" aria-hidden="true">
          {veredicto(p.estado).simbolo}
        </span>
      </div>

      <div className="ficha__cuerpo">
        <h3 className="ficha__nombre">
          <Link href={`/p/${p.slug}/`} className="ficha__link">
            {p.nombre}
          </Link>
        </h3>
        {p.marca && <div className="ficha__marca">{p.marca}</div>}

        <div className="ficha__pie">
          <Sello estado={p.estado} />
        </div>

        <p className="ficha__porque">
          {p.motivo ?? fuenteLegible[p.fuente] ?? p.fuente}
        </p>
      </div>
    </li>
  );
}
