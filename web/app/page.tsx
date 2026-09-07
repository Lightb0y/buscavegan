import Link from 'next/link';

import { meta } from '@/lib/catalogo';
import { numero, porcentaje } from '@/lib/veredicto';
import { SITIO } from '@/lib/sitio';

import { Buscador } from './Buscador';

export default function Home() {
  const m = meta();

  // Buscador de sitio: le dice a Google que puede ofrecer la búsqueda
  // directamente desde la página de resultados.
  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'WebSite',
    name: SITIO.nombre,
    url: SITIO.url + '/',
    inLanguage: 'es-AR',
    potentialAction: {
      '@type': 'SearchAction',
      target: {
        '@type': 'EntryPoint',
        urlTemplate: `${SITIO.url}/?q={search_term_string}`,
      },
      'query-input': 'required name=search_term_string',
    },
  };

  return (
    <div className="contenedor">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      <section className="hero">
        <h1>¿Este producto es apto vegano?</h1>
        <p className="hero__bajada">
          {numero(m.total)} productos argentinos clasificados. Y sobre todo:{' '}
          <strong>de dónde sacamos cada veredicto</strong>, producto por
          producto.
        </p>

        <Buscador categorias={m.categorias} fuenteLegible={m.fuente_legible} />
      </section>

      <section className="aviso">
        <p>
          {porcentaje(m.con_evidencia, m.total)} de las clasificaciones salen de
          evidencia sobre el producto real —su lista de ingredientes, un sello
          certificado o el registro de ANMAT—, no de adivinar por el nombre.{' '}
          <Link href="/como-funciona/">Cómo lo hacemos</Link>.
        </p>
      </section>
    </div>
  );
}
