import Link from 'next/link';

import { claseVeredicto, Sello } from './Sello';

export interface DatosTira {
  slug: string;
  nombre: string;
  marca?: string;
  categoria?: string;
  estado: string;
  fuente: string;
  imagen?: string;
  motivo?: string;
}

/** Una tira de la corrida: el cartel de un estante.
 *
 *  El orden es el de la góndola, no el de una tarjeta de catálogo: primero el
 *  veredicto en tinta plana —lo único que se ve barriendo la lista—, después
 *  la foto para reconocer el paquete que tenés en la mano, y recién ahí el
 *  nombre. La prueba va abajo, separada por un filete, en el lugar donde el
 *  cartel real imprime el precio por unidad de medida: la letra chica que
 *  existe para que el dato grande se pueda comprobar.
 */
export function Tira({
  p,
  fuenteLegible,
}: {
  p: DatosTira;
  fuenteLegible: Record<string, string>;
}) {
  return (
    <li className={`tira ${claseVeredicto(p.estado)}`}>
      <Sello estado={p.estado} />

      <div className="tira__foto">
        {p.imagen ? (
          // Con `output: export` no hay optimizador de imágenes, así que va un
          // <img> honesto: OFF ya las sirve chicas, y con medidas fijas no hay
          // salto de layout cuando cargan.
          // eslint-disable-next-line @next/next/no-img-element
          <img
            className="tira__miniatura"
            src={p.imagen}
            alt=""
            width={40}
            height={40}
            loading="lazy"
            decoding="async"
          />
        ) : (
          <div className="tira__sinfoto" aria-hidden="true" />
        )}
      </div>

      <div className="tira__cuerpo">
        <h3 className="tira__nombre">
          <Link href={`/p/${p.slug}/`} className="tira__link">
            {p.nombre}
          </Link>
        </h3>

        {(p.marca || p.categoria) && (
          <div className="tira__meta">
            {[p.marca, p.categoria].filter(Boolean).join(' · ')}
          </div>
        )}

        <p className="tira__prueba">
          {p.motivo ?? fuenteLegible[p.fuente] ?? p.fuente}
        </p>
      </div>
    </li>
  );
}
