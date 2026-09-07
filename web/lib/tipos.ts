/** Formas de los datos que exporta `export_web.py`. */

export type Estado = 'apto' | 'vegetariano' | 'no_apto' | 'revisar';

/** Un producto completo, tal como viene en `data/productos.ndjson`.
 *  Las claves opcionales están ausentes cuando no sabemos el dato: el export
 *  omite nulos en vez de escribirlos. */
export interface Producto {
  ean: string;
  slug: string;
  nombre: string;
  estado: Estado;
  fuente: string;
  marca?: string;
  categoria?: string;
  confianza?: number;
  motivo?: string;
  ingredientes?: string;
  imagen?: string;
  cadenas?: string[];
}

export interface Categoria {
  nombre: string;
  slug: string;
  total: number;
}

export interface Meta {
  actualizado: string;
  total: number;
  por_estado: Record<Estado, number>;
  por_fuente: Record<string, number>;
  categorias: Categoria[];
  con_evidencia: number;
  con_ingredientes: number;
  confirmados: number;
  fuente_legible: Record<string, string>;
  cadena_legible: Record<string, string>;
  fuentes_con_evidencia: string[];
}

/** El índice que baja el navegador: columnar y con diccionarios, para que el
 *  catálogo entero entre en una descarga chica. Lo arma `scripts/build-index.mjs`
 *  y lo rehidrata `lib/buscar.ts`. */
export interface IndiceCrudo {
  v: number;
  estados: Estado[];
  marcas: string[];
  categorias: string[];
  fuentes: string[];
  cadenas: string[];
  /** [ean, slug, nombre, marcaIdx, categoriaIdx, estadoIdx, fuenteIdx,
   *   bitsCadenas, tieneIngredientes, motivo, imagen] — los índices valen -1
   *   cuando no hay dato, y `motivo`/`imagen` son '' cuando no hay.
   *
   *   `imagen` viaja sin el prefijo común de Open Food Facts; lo vuelve a
   *   pegar `rehidratar()`. */
  p: [
    string,
    string,
    string,
    number,
    number,
    number,
    number,
    number,
    0 | 1,
    string,
    string,
  ][];
}
