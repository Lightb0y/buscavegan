import type { MetadataRoute } from 'next';

import { meta, productos } from '@/lib/catalogo';
import { SITIO } from '@/lib/sitio';

// Igual que robots.txt: se escribe en el build, no se responde por request.
export const dynamic = 'force-static';

/** ~7.400 URLs, bien por debajo del límite de 50.000 por sitemap, así que un
 *  solo archivo alcanza. */
export default function sitemap(): MetadataRoute.Sitemap {
  const m = meta();
  const fecha = new Date(m.actualizado + 'T00:00:00');

  const fijas: MetadataRoute.Sitemap = [
    { url: `${SITIO.url}/`, lastModified: fecha, priority: 1 },
    { url: `${SITIO.url}/categorias/`, lastModified: fecha, priority: 0.6 },
    { url: `${SITIO.url}/como-funciona/`, lastModified: fecha, priority: 0.6 },
  ];

  const categorias: MetadataRoute.Sitemap = m.categorias.map((c) => ({
    url: `${SITIO.url}/categoria/${c.slug}/`,
    lastModified: fecha,
    priority: 0.5,
  }));

  const fichas: MetadataRoute.Sitemap = productos().map((p) => ({
    url: `${SITIO.url}/p/${p.slug}/`,
    lastModified: fecha,
    priority: 0.7,
  }));

  return [...fijas, ...categorias, ...fichas];
}
