import type { Metadata } from 'next';
import Link from 'next/link';

import { meta } from '@/lib/catalogo';
import { numero } from '@/lib/veredicto';

export const metadata: Metadata = {
  title: 'Categorías',
  description:
    'Recorré los productos argentinos clasificados por rubro: lácteos, ' +
    'galletitas, golosinas, bebidas vegetales y más.',
  alternates: { canonical: '/categorias/' },
};

export default function PaginaCategorias() {
  const m = meta();
  // De mayor a menor: quien entra acá busca dónde hay más para mirar.
  const orden = [...m.categorias].sort((a, b) => b.total - a.total);

  return (
    <div className="contenedor">
      <div className="hero">
        <h1>Categorías</h1>
        <p className="hero__bajada">
          {numero(m.total)} productos repartidos en {orden.length} rubros.
        </p>
      </div>

      <ul className="indice-categorias">
        {orden.map((c) => (
          <li key={c.slug}>
            <Link href={`/categoria/${c.slug}/`}>
              <span>{c.nombre}</span>
              <span>{numero(c.total)}</span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
