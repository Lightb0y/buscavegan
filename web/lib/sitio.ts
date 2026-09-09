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
  /** Por acá entran los reportes de error, que son la vía más barata de
   *  corregir la base. Está en un solo lugar para poder mudarlo a una casilla
   *  del proyecto sin buscarlo por el código. */
  contacto: process.env.NEXT_PUBLIC_CONTACTO ?? 'josiassegovia29@gmail.com',
} as const;
