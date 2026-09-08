/** Identidad del sitio, en un solo lugar.
 *
 *  `NEXT_PUBLIC_SITE_URL` se define en Vercel. El default sirve para que el
 *  build local y el primer deploy funcionen sin configurar nada: las URLs
 *  canónicas y el sitemap salen bien igual, y se corrigen solas cuando se
 *  conecte el dominio propio.
 */
export const SITIO = {
  nombre: 'buscavegan',
  url: (
    process.env.NEXT_PUBLIC_SITE_URL ?? 'https://buscavegan.vercel.app'
  ).replace(/\/$/, ''),
} as const;
