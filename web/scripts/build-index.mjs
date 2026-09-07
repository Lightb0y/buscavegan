/**
 * Deriva `public/catalogo.json` —lo único que descarga el navegador— desde
 * `data/productos.ndjson`.
 *
 * El NDJSON pesa 4,4 MB porque incluye la lista de ingredientes de cada
 * producto, y esa lista solo hace falta en la ficha, que se genera estática en
 * build. Para buscar alcanzan nombre, marca, categoría y veredicto: columnar y
 * con diccionarios, el índice queda en el orden de los 150 KB comprimidos, y
 * con eso la búsqueda corre entera en el navegador sin ida y vuelta al
 * servidor por cada tecla.
 *
 *     node scripts/build-index.mjs
 */
import { readFileSync, writeFileSync, mkdirSync, statSync } from 'node:fs';
import { gzipSync } from 'node:zlib';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const raiz = join(dirname(fileURLToPath(import.meta.url)), '..');
const ENTRADA = join(raiz, 'data', 'productos.ndjson');
const SALIDA = join(raiz, 'public', 'catalogo.json');

const ESTADOS = ['apto', 'vegetariano', 'no_apto', 'revisar'];

// Las 6.030 fotos salen todas del mismo lugar, así que se guarda solo lo que
// cambia. Repetir el prefijo 6.030 veces suma medio mega de JSON que el
// navegador tiene que parsear al arrancar.
const PREFIJO_IMAGEN = 'https://images.openfoodfacts.org/images/products/';

/** Un diccionario por columna: los 6.129 valores de marca son ~1.900 marcas
 *  distintas, así que guardar el índice en vez del texto ahorra de verdad. */
function diccionario() {
  const indices = new Map();
  const valores = [];
  return {
    valores,
    idx(v) {
      if (v == null) return -1;
      let i = indices.get(v);
      if (i === undefined) {
        i = valores.length;
        indices.set(v, i);
        valores.push(v);
      }
      return i;
    },
  };
}

const marcas = diccionario();
const categorias = diccionario();
const fuentes = diccionario();
const cadenas = diccionario();

const lineas = readFileSync(ENTRADA, 'utf8').split('\n').filter(Boolean);
const filas = lineas.map((linea) => {
  const p = JSON.parse(linea);
  // Las cadenas van como bitmask: son 5 y un entero se compara más rápido que
  // un array, además de ocupar menos.
  let bits = 0;
  for (const c of p.cadenas ?? []) bits |= 1 << cadenas.idx(c);
  return [
    p.ean,
    p.slug,
    p.nombre,
    marcas.idx(p.marca),
    categorias.idx(p.categoria),
    ESTADOS.indexOf(p.estado),
    fuentes.idx(p.fuente),
    bits,
    p.ingredientes ? 1 : 0,
    // El "por qué" viaja con cada resultado aunque engorde el índice: es lo
    // que distingue a este buscador de una lista cualquiera, y esconderlo
    // detrás de un clic sería tirar el diferencial del producto. Se repite
    // mucho entre productos, así que gzip lo deja casi gratis.
    p.motivo ?? '',
    // Sin esto la grilla de búsqueda —la pantalla principal del sitio— mostraba
    // el marco vacío en todos los productos, aunque el 82% tiene foto.
    p.imagen?.startsWith(PREFIJO_IMAGEN)
      ? p.imagen.slice(PREFIJO_IMAGEN.length)
      : (p.imagen ?? ''),
  ];
});

const indice = {
  v: 1,
  estados: ESTADOS,
  marcas: marcas.valores,
  categorias: categorias.valores,
  fuentes: fuentes.valores,
  cadenas: cadenas.valores,
  p: filas,
};

mkdirSync(dirname(SALIDA), { recursive: true });
writeFileSync(SALIDA, JSON.stringify(indice));

const crudo = statSync(SALIDA).size;
const comprimido = gzipSync(readFileSync(SALIDA), { level: 9 }).length;
console.log(
  `catalogo.json  ${filas.length} productos  ` +
    `${(crudo / 1e6).toFixed(2)} MB  ->  ${(comprimido / 1e3).toFixed(0)} KB gzip`,
);
