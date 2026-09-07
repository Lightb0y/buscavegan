/** Lectura del catálogo en tiempo de build.
 *
 *  Solo lo usan Server Components: el navegador nunca ve este módulo ni el
 *  NDJSON de 4,4 MB. Lo que baja el cliente es el índice chico que arma
 *  `scripts/build-index.mjs`.
 */
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import type { Categoria, Meta, Producto } from './tipos';

const DATA = join(process.cwd(), 'data');

/** Next construye ~7.400 páginas en el mismo proceso; parsear el NDJSON una
 *  sola vez y cachearlo en el módulo es la diferencia entre un build de dos
 *  minutos y uno de media hora. */
let cache: Producto[] | null = null;
let porSlug: Map<string, Producto> | null = null;

export function productos(): Producto[] {
  if (!cache) {
    const crudo = readFileSync(join(DATA, 'productos.ndjson'), 'utf8');
    cache = crudo
      .split('\n')
      .filter((l) => l.length > 0)
      .map((l) => JSON.parse(l) as Producto);
  }
  return cache;
}

export function producto(slug: string): Producto | undefined {
  if (!porSlug) {
    porSlug = new Map(productos().map((p) => [p.slug, p]));
  }
  return porSlug.get(slug);
}

let metaCache: Meta | null = null;

export function meta(): Meta {
  if (!metaCache) {
    metaCache = JSON.parse(
      readFileSync(join(DATA, 'meta.json'), 'utf8'),
    ) as Meta;
  }
  return metaCache;
}

export function categoria(slug: string): Categoria | undefined {
  return meta().categorias.find((c) => c.slug === slug);
}

/** El slug de una categoría se lee del export en vez de recalcularse acá: si
 *  el `slugify` de Python y el de TypeScript se separaran aunque sea en un
 *  caso, quedarían links rotos que nadie va a notar hasta que sea tarde. */
export function slugCategoria(nombre: string): string | undefined {
  return meta().categorias.find((c) => c.nombre === nombre)?.slug;
}

export function deCategoria(nombre: string): Producto[] {
  return productos()
    .filter((p) => p.categoria === nombre)
    .sort((a, b) => a.nombre.localeCompare(b.nombre, 'es'));
}
