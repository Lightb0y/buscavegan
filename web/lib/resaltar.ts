/** Señala, dentro de la lista de ingredientes, el que disparó el veredicto.
 *
 *  Sin esto la persona lee «Contiene gelatina» y después tiene que buscar
 *  "gelatina" a ojo entre cuarenta ingredientes en letra chica. Con esto, ve
 *  exactamente dónde está.
 *
 *  El término sale del texto del `motivo`, que el pipeline escribe con una
 *  forma estable: «Contiene X: …» o «Contiene X, de origen animal», a veces
 *  con una aclaración entre paréntesis que acá se descarta.
 *
 *  Es deliberadamente conservador: si el patrón no calza exacto o el término
 *  no aparece en la lista, no resalta nada. Preferimos no señalar antes que
 *  señalar mal.
 */

/** «Contiene carmín (cochinilla), de origen animal» -> «carmín» */
const DISPARADOR = /^Contiene\s+([^:(,]+?)\s*(?:[:(,]|$)/u;

export function ingredienteDisparador(motivo?: string): string | null {
  if (!motivo) return null;
  const m = DISPARADOR.exec(motivo.trim());
  const termino = m?.[1]?.trim();
  // «Contiene ingredientes de origen animal» no nombra a ninguno en
  // particular: no hay nada que señalar.
  if (!termino || termino.length < 3 || /^ingrediente/i.test(termino)) {
    return null;
  }
  return termino;
}

function sinTildes(s: string): string {
  return s.normalize('NFD').replace(/[̀-ͯ]/g, '');
}

/** Mapa posición-en-el-texto-sin-tildes -> posición-en-el-texto-original.
 *  Quitar diacríticos solo borra caracteres, nunca agrega, así que el mapa se
 *  arma carácter por carácter sin ambigüedad. */
function mapaDePosiciones(original: string): { plano: string; pos: number[] } {
  let plano = '';
  const pos: number[] = [];
  for (let i = 0; i < original.length; i++) {
    const trozo = sinTildes(original[i]).toLowerCase();
    for (const c of trozo) {
      plano += c;
      pos.push(i);
    }
  }
  return { plano, pos };
}

export interface Trozo {
  texto: string;
  resaltado: boolean;
}

/** Parte el texto en trozos alternando normal/resaltado, para que el
 *  componente los pinte sin tener que inyectar HTML. */
export function partirResaltando(
  texto: string,
  termino: string | null,
): Trozo[] {
  if (!termino) return [{ texto, resaltado: false }];

  const { plano, pos } = mapaDePosiciones(texto);
  const aguja = sinTildes(termino).toLowerCase().trim();
  if (!aguja) return [{ texto, resaltado: false }];

  const esLetra = (c: string | undefined) => !!c && /[a-z0-9]/.test(c);

  const trozos: Trozo[] = [];
  let cursorOriginal = 0;
  let desde = 0;

  for (;;) {
    const i = plano.indexOf(aguja, desde);
    if (i === -1) break;
    desde = i + aguja.length;

    // Solo palabras completas: "leche" no debe resaltar dentro de "lechera".
    if (esLetra(plano[i - 1]) || esLetra(plano[i + aguja.length])) continue;

    const inicio = pos[i];
    const fin = pos[i + aguja.length - 1] + 1;
    if (inicio > cursorOriginal) {
      trozos.push({ texto: texto.slice(cursorOriginal, inicio), resaltado: false });
    }
    trozos.push({ texto: texto.slice(inicio, fin), resaltado: true });
    cursorOriginal = fin;
  }

  if (!trozos.length) return [{ texto, resaltado: false }];
  if (cursorOriginal < texto.length) {
    trozos.push({ texto: texto.slice(cursorOriginal), resaltado: false });
  }
  return trozos;
}
