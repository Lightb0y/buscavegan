/**
 * Borra de `out/` los payloads RSC que el build escribe pero nadie pide.
 *
 * Next 16 emite, por cada una de las ~7.500 rutas prerenderizadas, cuatro
 * archivos además del HTML: `index.txt`, `__next._tree.txt`, `__next.p/…` y
 * `__next._full.txt`. Los tres primeros los pide el router del cliente; el
 * cuarto no. Es byte a byte idéntico a `index.txt` —mismo md5— y la cadena
 * `_full` no aparece ni una vez en el JavaScript que baja el navegador,
 * mientras que `_tree` y `__next.p` sí aparecen.
 *
 * Con `output: export` tampoco hay servidor de Next que pueda consumirlo: lo
 * que se sube al CDN es exactamente esta carpeta. Así que son ~150 MB de
 * duplicado exacto que se despliegan en cada release sin que nada los lea.
 *
 * Si en alguna versión futura el router empezara a pedirlos, el peor caso es
 * que un prefetch falle y la navegación caiga a una carga de página completa:
 * el sitio no se rompe. Por las dudas, el script avisa si deja de encontrar
 * archivos para borrar, que es la señal de que Next cambió de formato.
 *
 *     node scripts/podar-salida.mjs
 */
import { readdirSync, statSync, unlinkSync, readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const RAIZ = join(dirname(fileURLToPath(import.meta.url)), '..', 'out');
const SOBRANTE = '__next._full.txt';

/** El nombre del que `__next._full.txt` es copia. Se compara antes de borrar:
 *  si algún día dejaran de ser idénticos, el archivo ya no sería un duplicado
 *  y borrarlo sí perdería información. */
const ORIGINAL = 'index.txt';

let borrados = 0;
let bytes = 0;
let distintos = 0;

function recorrer(dir) {
  for (const entrada of readdirSync(dir, { withFileTypes: true })) {
    const ruta = join(dir, entrada.name);
    if (entrada.isDirectory()) {
      recorrer(ruta);
      continue;
    }
    if (entrada.name !== SOBRANTE) continue;

    const gemelo = join(dir, ORIGINAL);
    try {
      if (!readFileSync(gemelo).equals(readFileSync(ruta))) {
        distintos++;
        continue;
      }
    } catch {
      // Sin gemelo con qué comparar, no se toca.
      distintos++;
      continue;
    }

    bytes += statSync(ruta).size;
    unlinkSync(ruta);
    borrados++;
  }
}

recorrer(RAIZ);

if (borrados === 0) {
  console.warn(
    `podar-salida: no se encontró ningún ${SOBRANTE} para borrar. ` +
      'Puede que Next haya cambiado el formato de salida: conviene revisar.',
  );
} else {
  console.log(
    `podar-salida  ${borrados} copias de ${SOBRANTE} borradas  ` +
      `${(bytes / 2 ** 20).toFixed(0)} MB`,
  );
}
if (distintos > 0) {
  console.warn(
    `podar-salida: ${distintos} no eran copia exacta de ${ORIGINAL} y se dejaron.`,
  );
}
