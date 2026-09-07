/** @type {import('next').NextConfig} */
const nextConfig = {
  // Export estático: el catálogo solo cambia cuando se vuelve a correr el
  // pipeline y se redeploya, así que no hay nada que calcular por request.
  // Todo sale del CDN: sin funciones serverless, sin cold starts, sin costo
  // por visita.
  output: 'export',

  // Con `output: export` no hay servidor que optimice imágenes al vuelo. Las
  // fotos vienen de los servidores de Open Food Facts, que ya las sirve
  // redimensionadas (`image_front_small_url`).
  images: { unoptimized: true },

  // `/p/algo/` en vez de `/p/algo` — cada ruta es una carpeta con su
  // index.html, que es como un hosting estático resuelve sin ambigüedad.
  trailingSlash: true,

  // Un error de tipos no debe llegar a producción disfrazado de deploy
  // exitoso. (Next 16 ya no acepta la clave `eslint` acá: el lint se corre
  // aparte, con `npm run lint`.)
  typescript: { ignoreBuildErrors: false },
};

export default nextConfig;
