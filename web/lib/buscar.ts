/** Búsqueda del lado del cliente sobre los 7.397 productos.
 *
 *  Con el catálogo entero en memoria (197 KB comprimidos) un recorrido lineal
 *  por cada tecla tarda menos de lo que tarda React en pintar, así que no hace
 *  falta ningún índice invertido ni dependencia de búsqueda: menos código,
 *  cero milisegundos de red y control total sobre el ranking.
 */
import type { Estado, IndiceCrudo } from './tipos';

export interface Fila {
  ean: string;
  slug: string;
  nombre: string;
  marca?: string;
  categoria?: string;
  estado: Estado;
  fuente: string;
  cadenas: string[];
  tieneIngredientes: boolean;
  motivo?: string;
  imagen?: string;
  /** Nombre normalizado, con un espacio al principio para poder preguntar
   *  "¿empieza alguna palabra con esto?" con un simple `includes`. */
  _nombre: string;
  /** Nombre + marca, mismo truco. */
  _todo: string;
}

export interface Filtros {
  texto: string;
  estados: Set<Estado>;
  categoria: string | null;
  soloConfirmados: boolean;
  soloConIngredientes: boolean;
  soloAnmat: boolean;
}

export const FILTROS_INICIALES: Filtros = {
  texto: '',
  estados: new Set<Estado>(['apto', 'vegetariano', 'no_apto', 'revisar']),
  categoria: null,
  soloConfirmados: false,
  soloConIngredientes: false,
  soloAnmat: false,
};

/** Minúsculas y sin acentos: quien busca "almibar" tiene que encontrar
 *  "almíbar", y quien busca "ñoquis" tiene que encontrar "Ñoquis". */
export function normalizar(texto: string): string {
  return texto
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase();
}

/** El índice guarda las fotos sin el prefijo, que es siempre el mismo.
 *  Debe coincidir con el de `scripts/build-index.mjs`. */
const PREFIJO_IMAGEN = 'https://images.openfoodfacts.org/images/products/';

export function rehidratar(crudo: IndiceCrudo): Fila[] {
  return crudo.p.map(
    ([ean, slug, nombre, mi, ci, ei, fi, bits, ingr, motivo, imagen]): Fila => {
      const marca = mi >= 0 ? crudo.marcas[mi] : undefined;
      const cadenas: string[] = [];
      for (let i = 0; i < crudo.cadenas.length; i++) {
        if (bits & (1 << i)) cadenas.push(crudo.cadenas[i]);
      }
      const _nombre = ' ' + normalizar(nombre);
      return {
        ean,
        slug,
        nombre,
        marca,
        categoria: ci >= 0 ? crudo.categorias[ci] : undefined,
        estado: crudo.estados[ei],
        fuente: crudo.fuentes[fi],
        cadenas,
        tieneIngredientes: ingr === 1,
        motivo: motivo || undefined,
        imagen: imagen ? PREFIJO_IMAGEN + imagen : undefined,
        _nombre,
        _todo: marca ? _nombre + ' ' + normalizar(marca) : _nombre,
      };
    },
  );
}

/** La fuente que marca "figura en el registro de ANMAT con atributo vegano".
 *  El nombre lo escribe `ingest_anmat.py` y viaja tal cual en el índice: si
 *  cambia allá, hay que cambiarlo acá. Es la única de las tres capas de
 *  certificación que es un registro del Estado; `off_label` es la declaración
 *  del fabricante y `sello_super` es lo que publica el supermercado. */
export const FUENTE_ANMAT = 'certificacion_oficial';

const SOLO_DIGITOS = /^\d{8,14}$/;

/** Puntaje de relevancia. Más alto es mejor; 0 significa "no matchea".
 *
 *  El orden que importa: lo que la persona escribió tal cual, después lo que
 *  empieza con eso, después lo que lo contiene, y recién al final lo que
 *  matchea por marca. Entre dos con el mismo puntaje gana el nombre más corto,
 *  porque "Leche de almendras" es mejor respuesta a "leche almendras" que
 *  "Leche de almendras con cacao y vainilla edición limitada". */
function puntaje(f: Fila, q: string, tokens: string[]): number {
  const nombre = f._nombre;

  if (nombre === ' ' + q) return 10000;

  let p = 0;
  if (nombre.startsWith(' ' + q)) p += 500;
  else if (nombre.includes(' ' + q)) p += 250;

  for (const t of tokens) {
    if (nombre.includes(' ' + t)) p += 60;
    else if (f._todo.includes(' ' + t)) p += 25;
    else return 0; // un token que no aparece en ningún lado descarta la fila
  }

  // Desempate: entre dos igual de relevantes, el nombre más corto es la
  // respuesta más probable. Acotado para que nunca domine al match real.
  return p + Math.max(0, 40 - f.nombre.length / 4);
}

/** Cuánto sabemos de un producto, de 0 a 4.
 *
 *  Ordena la vista por defecto —la que ve alguien que entra sin buscar nada—.
 *  Con orden alfabético la portada del sitio abría con las filas más rotas del
 *  catálogo: productos llamados «1», «1001843» o «1X 906K 216KCAL = 45G
 *  CHOCOLATE MA 100G: 2014/480», que son ruido de las fuentes y la peor cara
 *  posible del proyecto.
 *
 *  El puntaje es deliberadamente ciego al veredicto: mide cuánta evidencia
 *  hay, no si esa evidencia es buena noticia. Un «a revisar» con foto y lista
 *  de ingredientes rankea por encima de un «apto» sin nada, porque lo que se
 *  premia es tener con qué respaldar el dato. La distribución de veredictos de
 *  la primera pantalla sigue siendo la real. */
export function completitud(f: {
  nombre: string;
  tieneIngredientes: boolean;
  imagen?: string;
  cadenas: string[];
}): number {
  // Un nombre que casi no tiene letras es un código que se coló como nombre.
  const letras = (f.nombre.match(/\p{L}/gu) ?? []).length;
  return (
    (letras >= 3 ? 1 : 0) +
    (f.tieneIngredientes ? 2 : 0) +
    (f.imagen ? 1 : 0) +
    (f.cadenas.length > 0 ? 1 : 0)
  );
}

export function buscar(filas: Fila[], filtros: Filtros): Fila[] {
  const {
    texto,
    estados,
    categoria,
    soloConfirmados,
    soloConIngredientes,
    soloAnmat,
  } = filtros;

  const q = normalizar(texto.trim());
  const porEan = SOLO_DIGITOS.test(q);
  const tokens = q ? q.split(/\s+/).filter(Boolean) : [];

  const pasaFiltros = (f: Fila) =>
    estados.has(f.estado) &&
    (categoria === null || f.categoria === categoria) &&
    (!soloConfirmados || f.cadenas.length > 0) &&
    (!soloConIngredientes || f.tieneIngredientes) &&
    (!soloAnmat || f.fuente === FUENTE_ANMAT);

  // Un código de barras es una identidad, no una búsqueda: match exacto y
  // sin filtros, porque si alguien escaneó el producto quiere ver ESE.
  if (porEan) {
    return filas.filter((f) => f.ean === q);
  }

  // Sin texto no hay relevancia que medir, así que manda la evidencia
  // disponible y después el alfabeto.
  if (!tokens.length) {
    return filas
      .filter(pasaFiltros)
      .sort(
        (a, b) =>
          completitud(b) - completitud(a) ||
          a.nombre.localeCompare(b.nombre, 'es'),
      );
  }

  const conPuntaje: { f: Fila; p: number }[] = [];
  for (const f of filas) {
    if (!pasaFiltros(f)) continue;
    const p = puntaje(f, q, tokens);
    if (p > 0) conPuntaje.push({ f, p });
  }
  conPuntaje.sort(
    (a, b) => b.p - a.p || a.f.nombre.localeCompare(b.f.nombre, 'es'),
  );
  return conPuntaje.map((x) => x.f);
}
