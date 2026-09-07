import type { Metadata, Viewport } from 'next';
import { Fraunces, IBM_Plex_Mono, IBM_Plex_Sans } from 'next/font/google';
import Link from 'next/link';

import { meta } from '@/lib/catalogo';
import { numero } from '@/lib/veredicto';
import { SITIO } from '@/lib/sitio';

import './globals.css';

// Un serif con carácter para los títulos y un sans técnico para el cuerpo.
// La elección no es decorativa: los EAN, los porcentajes y los conteos se leen
// mejor con las cifras de ancho fijo que trae Plex.
const titulo = Fraunces({
  subsets: ['latin'],
  display: 'swap',
  variable: '--fuente-titulo',
});

const texto = IBM_Plex_Sans({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  display: 'swap',
  variable: '--fuente-texto',
});

const mono = IBM_Plex_Mono({
  subsets: ['latin'],
  weight: ['400', '500'],
  display: 'swap',
  variable: '--fuente-mono',
});

export const metadata: Metadata = {
  metadataBase: new URL(SITIO.url),
  title: {
    default: `${SITIO.nombre} — ¿este producto argentino es apto vegano?`,
    template: `%s · ${SITIO.nombre}`,
  },
  description:
    'Buscá cualquier producto argentino y enterate si es apto vegano, ' +
    'vegetariano o no apto. Y sobre todo: de dónde sacamos ese dato.',
  applicationName: SITIO.nombre,
  authors: [{ name: 'Josias Segovia' }],
  openGraph: {
    type: 'website',
    locale: 'es_AR',
    siteName: SITIO.nombre,
    title: `${SITIO.nombre} — ¿este producto argentino es apto vegano?`,
    description:
      'Miles de productos argentinos clasificados, con la evidencia a la vista.',
  },
  twitter: { card: 'summary_large_image' },
  robots: { index: true, follow: true },
};

export const viewport: Viewport = {
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#fdfbf7' },
    { media: '(prefers-color-scheme: dark)', color: '#15140f' },
  ],
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const m = meta();
  const clases = `${titulo.variable} ${texto.variable} ${mono.variable}`;

  return (
    <html lang="es-AR" className={clases}>
      <body>
        <div className="sitio">
          <a className="saltar" href="#contenido">
            Saltar al contenido
          </a>

          <header className="encabezado">
            <div className="contenedor encabezado__fila">
              <Link href="/" className="marca">
                <span className="marca__brote" aria-hidden="true">
                  ❧
                </span>
                buscavegan
              </Link>
              <nav className="navegacion" aria-label="Principal">
                <Link href="/">Buscar</Link>
                <Link href="/categorias/">Categorías</Link>
                <Link href="/como-funciona/">Cómo funciona</Link>
              </nav>
            </div>
          </header>

          <main id="contenido">{children}</main>

          <footer className="pie">
            <div className="contenedor pie__grilla">
              <div>
                <p>
                  <strong>buscavegan</strong> — {numero(m.total)} productos
                  argentinos clasificados, con la evidencia a la vista.
                </p>
                <p>
                  Datos actualizados al{' '}
                  {new Date(m.actualizado + 'T00:00:00').toLocaleDateString(
                    'es-AR',
                    { day: 'numeric', month: 'long', year: 'numeric' },
                  )}
                  .
                </p>
              </div>
              <div>
                <p>
                  <strong>«Apto» quiere decir vegano</strong>, es decir sin
                  ingredientes de origen animal. No quiere decir{' '}
                  <em>cruelty-free</em>: si la marca testea en animales no
                  figura en estas fuentes de datos.
                </p>
              </div>
              <div>
                <p>
                  Fuentes: Open Food Facts, el registro de ANMAT y las fichas
                  publicadas por Carrefour, Vea, Día, Jumbo y Disco.
                </p>
                <p>
                  <a href={SITIO.repo}>Código abierto en GitHub</a>
                </p>
              </div>
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
