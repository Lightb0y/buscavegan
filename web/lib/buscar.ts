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
}

export const FILTROS_INICIALES: Filtros = {
  texto: '',
  estados: new Set<Estado>(['apto', 'vegetariano', 'no_apto', 'revisar']),
  categoria: null,
  soloConfirmados: false,
  soloConIngredientes: false,
};

/** Minúsculas y sin acentos: quien busca "almibar" tiene que encontrar
 *  "almíbar", y quien busca "ñoquis" tiene que encontrar "Ñoquis". */
export function normalizar(texto: string): string {
  return texto
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase();
}

export function rehidratar(crudo: IndiceCrudo): Fila[] {
  return crudo.p.map(
    ([ean, slug, nombre, mi, ci, ei, fi, bits, ingr, motivo]): Fila => {
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
        _nombre,
        _todo: marca ? _nombre + ' ' + normalizar(marca) : _nombre,
      };
    },
  );
}

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

export function buscar(filas: Fila[], filtros: Filtros): Fila[] {
  const { texto, estados, categoria, soloConfirmados, soloConIngredientes } =
    filtros;

  const q = normalizar(texto.trim());
  const porEan = SOLO_DIGITOS.test(q);
  const tokens = q ? q.split(/\s+/).filter(Boolean) : [];

  const pasaFiltros = (f: Fila) =>
    estados.has(f.estado) &&
    (categoria === null || f.categoria === categoria) &&
    (!soloConfirmados || f.cadenas.length > 0) &&
    (!soloConIngredientes || f.tieneIngredientes);

  // Un código de barras es una identidad, no una búsqueda: match exacto y
  // sin filtros, porque si alguien escaneó el producto quiere ver ESE.
  if (porEan) {
    return filas.filter((f) => f.ean === q);
  }

  if (!tokens.length) {
    return filas
      .filter(pasaFiltros)
      .sort((a, b) => a.nombre.localeCompare(b.nombre, 'es'));
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
