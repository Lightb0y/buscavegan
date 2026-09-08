/** La tranca del panel de curaduría.
 *
 *  QUÉ ES Y QUÉ NO ES
 *  ------------------
 *  Esto NO es seguridad. El sitio es un export estático: no hay servidor que
 *  valide nada, así que toda la comprobación pasa en el navegador de quien
 *  entra, con código que esa misma persona puede leer. Cualquiera con la
 *  consola abierta entra al panel sin la clave. Guardar el hash en vez de la
 *  contraseña en claro evita que se lea de un vistazo en el bundle, y nada
 *  más que eso.
 *
 *  Es aceptable acá por una razón concreta: el panel no puede romper nada.
 *  No escribe en la base, no publica, no borra: junta decisiones en el
 *  localStorage de quien lo usa y las baja como CSV. El daño máximo de que
 *  alguien entre es que se descargue un archivo con sus propias ediciones.
 *  El momento en que una corrección afecta al sitio de verdad es cuando una
 *  persona corre `revision.py --importar` en su máquina y redeploya, y ese
 *  paso sí está protegido por el acceso al repositorio.
 *
 *  Si algún día el panel escribe de verdad (una API, una base), esta tranca
 *  no alcanza y hay que reemplazarla por autenticación del lado del servidor.
 *
 *  PARA CAMBIAR LA CLAVE
 *  ---------------------
 *      python -c "import hashlib; print(hashlib.sha256(b'usuario:clave').hexdigest())"
 *
 *  y se pega el resultado acá abajo.
 */

/** Huella de las credenciales vigentes, como `usuario:clave`. */
const HUELLA = '499927e1f958fe37416e1bd8a60cab6b702bbaec944f372825c42d80e35fd9c5';

/** Dura lo que dura la pestaña: cerrar el navegador cierra la sesión. Para un
 *  panel de administración es lo correcto, y además evita dejar la sesión
 *  abierta en una máquina prestada. */
const CLAVE_SESION = 'buscavegan.panel.abierto';

async function huellaDe(usuario: string, clave: string): Promise<string> {
  const datos = new TextEncoder().encode(`${usuario}:${clave}`);
  const buf = await crypto.subtle.digest('SHA-256', datos);
  return [...new Uint8Array(buf)]
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
}

export async function verificar(usuario: string, clave: string) {
  // `crypto.subtle` solo existe en contexto seguro (https o localhost). En
  // producción y en desarrollo se cumple; si no, hay que decirlo en vez de
  // fallar como si la clave estuviera mal.
  if (typeof crypto === 'undefined' || !crypto.subtle) {
    return { ok: false as const, motivo: 'sin-cripto' as const };
  }
  const h = await huellaDe(usuario.trim(), clave);
  return h === HUELLA
    ? { ok: true as const }
    : { ok: false as const, motivo: 'credenciales' as const };
}

export function estaAbierto(): boolean {
  try {
    return window.sessionStorage.getItem(CLAVE_SESION) === '1';
  } catch {
    return false;
  }
}

export function abrir(): void {
  try {
    window.sessionStorage.setItem(CLAVE_SESION, '1');
  } catch {
    // Sin sessionStorage el panel sigue funcionando: solo va a volver a
    // pedir la clave si se recarga la página.
  }
}

export function cerrar(): void {
  try {
    window.sessionStorage.removeItem(CLAVE_SESION);
  } catch {
    /* nada que limpiar */
  }
}
