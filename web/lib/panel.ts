/** Estado del panel de curaduría: las correcciones que todavía no se
 *  importaron al pipeline.
 *
 *  Por qué existe este archivo y no un endpoint: el sitio es un export
 *  estático (`output: 'export'`), o sea que en producción no hay servidor ni
 *  base de datos a los que escribir. Lo que el panel produce es el CSV que
 *  `revision.py --importar` ya sabe leer: esa es la Capa 4 del pipeline, la
 *  curaduría humana, que pisa a todas las capas automáticas y sobrevive al
 *  refresco semanal. El panel no inventa un mecanismo nuevo: le pone una
 *  pantalla al que ya estaba, que hasta ahora se completaba a mano.
 */
import type { Estado } from './tipos';

/** Una decisión humana pendiente de importar. */
export interface Correccion {
  ean: string;
  nombre: string;
  marca?: string;
  categoria?: string;
  /** Lo que dice el pipeline hoy. Se guarda para poder mostrar el antes y
   *  después sin volver a buscar la fila. */
  estadoActual: Estado;
  /** Lo que decidió la persona. */
  estadoCorregido: Estado;
  motivoActual?: string;
  revisor: string;
  /** ISO. Solo para ordenar la lista por lo último que se tocó. */
  cuando: string;
}

const CLAVE = 'buscavegan.correcciones.v1';
const CLAVE_REVISOR = 'buscavegan.revisor.v1';

/** localStorage puede tirar excepción (modo privado, cookies bloqueadas) y
 *  puede volver vacío. Nunca se cae por eso: el panel arranca sin nada. */
function leerCrudo<T>(clave: string, porDefecto: T): T {
  try {
    const s = window.localStorage.getItem(clave);
    return s ? (JSON.parse(s) as T) : porDefecto;
  } catch {
    return porDefecto;
  }
}

function escribirCrudo(clave: string, valor: unknown): boolean {
  try {
    window.localStorage.setItem(clave, JSON.stringify(valor));
    return true;
  } catch {
    return false;
  }
}

export function leerCorrecciones(): Record<string, Correccion> {
  return leerCrudo<Record<string, Correccion>>(CLAVE, {});
}

export function guardarCorrecciones(c: Record<string, Correccion>): boolean {
  return escribirCrudo(CLAVE, c);
}

export function leerRevisor(): string {
  return leerCrudo<string>(CLAVE_REVISOR, '');
}

export function guardarRevisor(r: string): void {
  escribirCrudo(CLAVE_REVISOR, r);
}

// --- el CSV que espera revision.py ----------------------------------------

/** Las columnas, en el orden exacto de `revision.COLUMNAS`. El importador
 *  lee por nombre de columna, así que el orden es por prolijidad; los
 *  nombres, en cambio, no se pueden tocar. */
const COLUMNAS = [
  'ean', 'nombre', 'marca', 'categoria', 'estado_actual', 'motivo_actual',
  'ingredientes', 'estado_corregido', 'revisor',
] as const;

/** Comilla solo cuando hace falta, como escribe el `csv` de Python. Los
 *  saltos de línea se aplanan antes: un motivo multilínea rompería la fila. */
function campo(v: string | undefined | null): string {
  const s = String(v ?? '').replace(/\r?\n/g, ' ').trim();
  return /[",]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

/** Arma el CSV listo para `python revision.py --importar`.
 *
 *  La columna `ingredientes` va vacía a propósito: el índice que baja el
 *  navegador no trae la lista completa (solo un bit de si existe), y el
 *  importador no la lee. Está para que el archivo tenga la misma forma que
 *  el que exporta `revision.py --exportar`. */
export function aCsv(correcciones: Correccion[]): string {
  const filas = [COLUMNAS.join(',')];
  for (const c of correcciones) {
    filas.push([
      campo(c.ean),
      campo(c.nombre),
      campo(c.marca),
      campo(c.categoria),
      campo(c.estadoActual),
      campo(c.motivoActual),
      '',
      campo(c.estadoCorregido),
      campo(c.revisor),
    ].join(','));
  }
  // BOM: `revision.py` abre con utf-8-sig, y además es lo que hace que Excel
  // no rompa los acentos si alguien quiere mirar el archivo antes de subirlo.
  return '﻿' + filas.join('\n') + '\n';
}

/** Nombre con fecha, para no pisar exportaciones anteriores en Descargas. */
export function nombreDeArchivo(d = new Date()): string {
  const p = (n: number) => String(n).padStart(2, '0');
  return `correcciones-${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}.csv`;
}
