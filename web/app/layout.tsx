import type { Metadata, Viewport } from 'next';
import { Archivo, Chivo_Mono } from 'next/font/google';
import Link from 'next/link';

import { Isotipo } from '@/components/Iconos';
import { meta } from '@/lib/catalogo';
import { numero } from '@/lib/veredicto';
import { SITIO } from '@/lib/sitio';

import './globals.css';

// Archivo y Chivo Mono son de Omnibus-Type, fundición de Buenos Aires. La
// elección no es un guiño: Archivo es una grotesca variable pensada para
// impresión de alto rendimiento —titulares, formularios, cartelería—, que es
// exactamente el trabajo acá. Su eje de ancho es el que permite que un nombre
// de producto argentino entre entero en la tira, sin puntos suspensivos, sin
// cambiar de familia.
const sans = Archivo({
  subsets: ['latin'],
  display: 'swap',
  axes: ['wdth'],
  variable: '--fuente-sans',
});

// Solo para códigos: EAN y RNPA. No se usa para dar aire técnico a prosa.
const mono = Chivo_Mono({
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
    { media: '(prefers-color-scheme: light)', color: '#ffffff' },
    { media: '(prefers-color-scheme: dark)', color: '#0e0e0d' },
  ],
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const m = meta();

  return (
    <html lang="es-AR" className={`${sans.variable} ${mono.variable}`}>
      <body>
        <div className="sitio">
          <a className="saltar" href="#contenido">
            Saltar al contenido
          </a>

          <header className="encabezado">
            <div className="contenedor encabezado__fila">
              <Link href="/" className="marca">
                <Isotipo />
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
