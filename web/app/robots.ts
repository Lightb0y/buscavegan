import type { MetadataRoute } from 'next';

import { SITIO } from '@/lib/sitio';

// Con `output: export` no hay servidor que responda esta ruta al vuelo: hay
// que decirle a Next que la escriba como archivo en el build.
export const dynamic = 'force-static';

export default function robots(): MetadataRoute.Robots {
  return {
    rules: { userAgent: '*', allow: '/' },
    sitemap: `${SITIO.url}/sitemap.xml`,
  };
}
