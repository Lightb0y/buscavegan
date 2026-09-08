import Link from 'next/link';

import type { DatosTira } from '@/components/Tira';
import { completitud } from '@/lib/buscar';
import { meta, productos } from '@/lib/catalogo';
import { numero, porcentaje } from '@/lib/veredicto';
import { SITIO } from '@/lib/sitio';

import { Buscador } from './Buscador';

/** Cuántas tiras se generan en el HTML del servidor.
 *
 *  Antes la home no traía ni un producto: la grilla entera dependía de bajar y
 *  parsear el índice, así que la primera pantalla era una caja vacía durante
 *  toda la cascada —HTML, JS, hidratar, fetch, parsear— y un buscador que
 *  llegara sin ejecutar JS no veía absolutamente nada. Estas primeras tiras
 *  son las mismas que mostraría el cliente sin filtros, en el mismo orden, así
 *  que cuando el índice llega no hay salto de contenido. */
const SEMILLA = 24;

export default function Home() {
  const m = meta();

  // Mismo orden que aplica el cliente sin filtros (`completitud`), o al llegar
  // el índice la lista saltaría a otro contenido.
  const semilla: DatosTira[] = productos()
    .slice()
    .sort((a, b) => {
      const ca = completitud({
        nombre: a.nombre,
        tieneIngredientes: Boolean(a.ingredientes),
        imagen: a.imagen,
        cadenas: a.cadenas ?? [],
      });
      const cb = completitud({
        nombre: b.nombre,
        tieneIngredientes: Boolean(b.ingredientes),
        imagen: b.imagen,
        cadenas: b.cadenas ?? [],
      });
      return cb - ca || a.nombre.localeCompare(b.nombre, 'es');
    })
    .slice(0, SEMILLA)
    .map((p) => ({
      slug: p.slug,
      nombre: p.nombre,
      marca: p.marca,
      categoria: p.categoria,
      estado: p.estado,
      fuente: p.fuente,
      imagen: p.imagen,
      motivo: p.motivo,
    }));

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
    <>
      {/* Sin esto el navegador recién descubre el índice después de hidratar:
          HTML, JS, hidratación y recién ahí la descarga. Declararlo acá lo
          pone en vuelo junto con el JS. */}
      <link rel="preload" as="fetch" href="/catalogo.json" crossOrigin="anonymous" />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      <div className="contenedor">
        <div className="titular">
          <h1>¿Este producto es apto vegano?</h1>
          <p className="titular__bajada">
            {numero(m.total)} productos argentinos clasificados. Y sobre todo:{' '}
            <strong>de dónde sacamos cada veredicto</strong>, producto por
            producto.
          </p>
        </div>
      </div>

      <Buscador
        categorias={m.categorias}
        fuenteLegible={m.fuente_legible}
        semilla={semilla}
        total={m.total}
      />

      <div className="contenedor">
        <p className="nota">
          {porcentaje(m.con_evidencia, m.total)} de las clasificaciones salen de
          evidencia sobre el producto real —su lista de ingredientes, un sello
          certificado o el registro de ANMAT—, no de adivinar por el nombre.{' '}
          <Link href="/como-funciona/">Cómo lo hacemos</Link>.
        </p>
      </div>
    </>
  );
}
