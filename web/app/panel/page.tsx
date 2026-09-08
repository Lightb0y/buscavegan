import type { Metadata } from 'next';

import { Panel } from './Panel';

export const metadata: Metadata = {
  title: 'Panel',
  description: 'Corrección manual de la clasificación de un producto.',
  // No es contenido público: no va al índice de nadie. `robots.ts` además lo
  // deja fuera del rastreo, y no está en el sitemap.
  robots: { index: false, follow: false },
};

export default function PaginaPanel() {
  return <Panel />;
}
