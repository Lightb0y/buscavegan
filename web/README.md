# web — el sitio público

Next.js 16 con **export estático**. No hay servidor, ni base de datos, ni
funciones serverless: el build escribe HTML y el CDN lo sirve.

## Por qué así

El catálogo entero pesa **236 KB comprimidos**. Ese solo número decide toda la
arquitectura: en vez de montar una base en la nube y una API que la consulte,
el navegador se baja el catálogo completo una vez y busca en memoria. La
búsqueda responde mientras se tipea, sin ida y vuelta al servidor por cada
tecla, y el costo de operación es cero.

Las fichas de producto sí se generan una por una en el build (7.397 páginas),
porque son lo que indexa Google: alguien que busca «¿el alfajor Guaymallén es
vegano?» tiene que caer en una página con la respuesta ya escrita en el HTML,
no en un cascarón que la pide por JavaScript.

## Cómo se mueven los datos

```
data/buscavegan.db          (SQLite del pipeline, no se versiona)
        │
        │  python export_web.py
        ▼
web/data/productos.ndjson   4,4 MB — se versiona: lo publicado es lo commiteado
web/data/meta.json          conteos, categorías y textos legibles
        │
        ├─ npm run prebuild ─► web/public/catalogo.json   índice del navegador
        │                                                  (derivado, no se versiona)
        └─ next build ───────► web/out/   7.538 páginas estáticas
```

`productos.ndjson` es un objeto JSON por línea, ordenado por EAN. No es
capricho: un array único se vería como *un solo renglón cambiado* en cada
refresco y git guardaría los 4,4 MB de nuevo. Un objeto por línea hace que un
refresco que toca 200 productos produzca un diff de 200 líneas.

## Comandos

```bash
npm install
npm run dev      # http://localhost:3000
npm test         # tests de búsqueda y resaltado (Node corre el TS directo)
npm run build    # export estático completo en out/
```

`prebuild` y `predev` regeneran `public/catalogo.json` solos, así que nunca se
desincroniza del NDJSON.

## Decisiones que conviene no revertir sin pensarlo

- **El color nunca comunica solo.** Cada veredicto lleva símbolo, palabra y
  color. Un 8% de los varones no distingue rojo de verde, y acá el color *es*
  el dato que la persona vino a buscar.
- **La familia de colores del veredicto no se usa para nada más.** Si el verde
  apareciera en un botón o en un link, dejaría de significar «apto».
- **El «por qué» viaja en el índice** aunque lo engorde 39 KB. Es lo que
  distingue a este buscador de una lista cualquiera; esconderlo detrás de un
  clic sería tirar el diferencial del producto.
- **Los slugs de categoría se leen de `meta.json`**, no se recalculan en
  TypeScript. Si el `slugify` de Python y el de acá se separaran en un solo
  caso, quedarían links rotos que nadie notaría hasta que fuera tarde.
- **`dynamic = 'force-static'`** en `sitemap.ts` y `robots.ts`: sin eso el
  build con `output: export` falla.

## Deploy

Vercel, conectado al repo con **Root Directory = `web`**. Cada push a `main`
redeploya.

El workflow `refresh.yml` corre el pipeline una vez por semana y, si los tests
pasan, commitea `web/data/` — con lo cual Vercel redeploya solo. Nadie tiene
que acordarse de republicar.
