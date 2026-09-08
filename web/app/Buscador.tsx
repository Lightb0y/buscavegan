'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { IconoCruz, IconoLupa } from '@/components/Iconos';
import { Tira, type DatosTira } from '@/components/Tira';
import { buscar, rehidratar, type Fila } from '@/lib/buscar';
import type { Categoria, Estado, IndiceCrudo } from '@/lib/tipos';
import { numero, ORDEN_ESTADOS, VEREDICTOS } from '@/lib/veredicto';

/** Cuántos resultados se pintan por tanda. Con 7.397 productos, renderizar
 *  todo congelaría el navegador. */
const TANDA = 48;

/** Todo el estado de la búsqueda vive en la URL.
 *
 *  Antes solo viajaba `q`: los filtros y la tanda eran estado de componente,
 *  así que abrir un producto y volver atrás te devolvía a la lista en 48 y sin
 *  filtros, y el navegador tampoco podía restaurar el scroll porque la página
 *  había vuelto a ser corta. Con todo en la URL, volver atrás reconstruye
 *  exactamente lo que había, y además la búsqueda se puede compartir entera.
 */
interface Estado0 {
  texto: string;
  estados: Set<Estado>;
  categoria: string | null;
  soloConfirmados: boolean;
  soloConIngredientes: boolean;
  soloAnmat: boolean;
  tandas: number;
}

const TODOS = () => new Set<Estado>(ORDEN_ESTADOS);

function leerUrl(busqueda: string, categorias: Categoria[]): Estado0 {
  const p = new URLSearchParams(busqueda);

  const v = p.get('v');
  const pedidos = v
    ? (v.split(',').filter((e) => ORDEN_ESTADOS.includes(e as Estado)) as Estado[])
    : [];

  const slug = p.get('cat');
  const cat = slug ? categorias.find((c) => c.slug === slug)?.nombre : undefined;

  const n = Number(p.get('n'));

  return {
    texto: p.get('q') ?? '',
    estados: pedidos.length ? new Set(pedidos) : TODOS(),
    categoria: cat ?? null,
    soloConfirmados: p.get('gon') === '1',
    soloConIngredientes: p.get('ing') === '1',
    soloAnmat: p.get('anmat') === '1',
    tandas: Number.isInteger(n) && n > 1 ? Math.min(n, 200) : 1,
  };
}

function escribirUrl(e: Estado0, categorias: Categoria[]) {
  const p = new URLSearchParams();
  if (e.texto.trim()) p.set('q', e.texto.trim());
  if (e.estados.size !== ORDEN_ESTADOS.length) {
    p.set('v', ORDEN_ESTADOS.filter((x) => e.estados.has(x)).join(','));
  }
  if (e.categoria) {
    const slug = categorias.find((c) => c.nombre === e.categoria)?.slug;
    if (slug) p.set('cat', slug);
  }
  if (e.soloConIngredientes) p.set('ing', '1');
  if (e.soloConfirmados) p.set('gon', '1');
  if (e.soloAnmat) p.set('anmat', '1');
  if (e.tandas > 1) p.set('n', String(e.tandas));

  const q = p.toString();
  window.history.replaceState(
    null,
    '',
    q ? `${window.location.pathname}?${q}` : window.location.pathname,
  );
}

export function Buscador({
  categorias,
  fuenteLegible,
  semilla,
  total,
}: {
  categorias: Categoria[];
  fuenteLegible: Record<string, string>;
  /** Los primeros productos, ya renderizados en el servidor. Se muestran
   *  mientras baja el índice, así la primera pantalla nunca está vacía. */
  semilla: DatosTira[];
  total: number;
}) {
  const [filas, setFilas] = useState<Fila[] | null>(null);
  const [error, setError] = useState(false);
  const [hidratado, setHidratado] = useState(false);
  const [condensado, setCondensado] = useState(false);

  const [st, setSt] = useState<Estado0>(() => ({
    texto: '',
    estados: TODOS(),
    categoria: null,
    soloConfirmados: false,
    soloConIngredientes: false,
    soloAnmat: false,
    tandas: 1,
  }));

  const campo = useRef<HTMLInputElement>(null);

  // Estado inicial desde la URL, antes de cualquier otra cosa.
  useEffect(() => {
    setSt(leerUrl(window.location.search, categorias));
    setHidratado(true);
  }, [categorias]);

  // El índice se pide una sola vez y queda en memoria. A partir de acá cada
  // tecla se resuelve local: cero red, cero espera.
  useEffect(() => {
    let vigente = true;
    fetch('/catalogo.json')
      .then((r) => {
        if (!r.ok) throw new Error(String(r.status));
        return r.json() as Promise<IndiceCrudo>;
      })
      .then((crudo) => {
        if (vigente) setFilas(rehidratar(crudo));
      })
      .catch(() => {
        if (vigente) setError(true);
      });
    return () => {
      vigente = false;
    };
  }, []);

  // La URL se reescribe con un respiro, para no ensuciar el historial en cada
  // tecla. `replaceState` y no `pushState`: el botón atrás tiene que salir de
  // la búsqueda, no recorrer cada letra que se escribió.
  useEffect(() => {
    if (!hidratado) return;
    const id = setTimeout(() => escribirUrl(st, categorias), 250);
    return () => clearTimeout(id);
  }, [st, hidratado, categorias]);

  // La única transformación con movimiento del sitio: el riel se condensa al
  // barrer la corrida, para no perder de vista el filtro ni la consulta.
  useEffect(() => {
    const alScroll = () => setCondensado(window.scrollY > 120);
    alScroll();
    window.addEventListener('scroll', alScroll, { passive: true });
    return () => window.removeEventListener('scroll', alScroll);
  }, []);

  // `/` enfoca la búsqueda desde cualquier parte de la página. No secuestra la
  // tecla si ya estás escribiendo.
  useEffect(() => {
    const enTecla = (e: KeyboardEvent) => {
      const destino = e.target as HTMLElement | null;
      const escribiendo =
        destino instanceof HTMLInputElement ||
        destino instanceof HTMLTextAreaElement ||
        destino instanceof HTMLSelectElement;
      if (e.key === '/' && !escribiendo) {
        e.preventDefault();
        campo.current?.focus();
      }
      if (e.key === 'Escape' && destino === campo.current) {
        setSt((s) => ({ ...s, texto: '', tandas: 1 }));
      }
    };
    window.addEventListener('keydown', enTecla);
    return () => window.removeEventListener('keydown', enTecla);
  }, []);

  const resultados = useMemo(() => {
    if (!filas) return [];
    return buscar(filas, {
      texto: st.texto,
      estados: st.estados,
      categoria: st.categoria,
      soloConfirmados: st.soloConfirmados,
      soloConIngredientes: st.soloConIngredientes,
      soloAnmat: st.soloAnmat,
    });
  }, [filas, st]);

  // Recuento por veredicto sobre lo que pasa TODOS los filtros menos el de
  // veredicto: la leyenda tiene que decir cuántos hay de cada uno, no cuántos
  // quedaron después de esconderlos.
  const conteos = useMemo(() => {
    const c = new Map<Estado, number>(ORDEN_ESTADOS.map((e) => [e, 0]));
    if (!filas) return c;
    for (const f of buscar(filas, {
      texto: st.texto,
      estados: TODOS(),
      categoria: st.categoria,
      soloConfirmados: st.soloConfirmados,
      soloConIngredientes: st.soloConIngredientes,
      soloAnmat: st.soloAnmat,
    })) {
      c.set(f.estado, (c.get(f.estado) ?? 0) + 1);
    }
    return c;
  }, [
    filas,
    st.texto,
    st.categoria,
    st.soloConfirmados,
    st.soloConIngredientes,
    st.soloAnmat,
  ]);

  const cambiar = useCallback((parcial: Partial<Estado0>) => {
    // Cualquier cambio en lo que se busca vuelve la lista al principio.
    setSt((s) => ({ ...s, ...parcial, tandas: 1 }));
  }, []);

  const alternarEstado = useCallback((e: Estado) => {
    setSt((s) => {
      const proximos = new Set(s.estados);
      if (proximos.has(e)) proximos.delete(e);
      else proximos.add(e);
      return { ...s, estados: proximos, tandas: 1 };
    });
  }, []);

  const hayFiltro =
    st.texto.trim() !== '' ||
    st.categoria !== null ||
    st.soloConfirmados ||
    st.soloConIngredientes ||
    st.soloAnmat ||
    st.estados.size !== ORDEN_ESTADOS.length;

  const limpiarTodo = () => {
    setSt({
      texto: '',
      estados: TODOS(),
      categoria: null,
      soloConfirmados: false,
      soloConIngredientes: false,
      soloAnmat: false,
      tandas: 1,
    });
    campo.current?.focus();
  };

  const visibles = st.tandas * TANDA;
  // Mientras no bajó el índice se muestra la semilla del servidor, salvo que
  // la URL ya pidiera otra cosa: ahí sería contenido equivocado.
  const mostrarSemilla = filas === null && !error && !hayFiltro;

  return (
    <>
      <div className={`riel${condensado ? ' riel--condensado' : ''}`}>
        <div className="contenedor">
          <div className="riel__caja">
            <span className="riel__lupa">
              <IconoLupa tam={22} />
            </span>

            <label className="solo-lectores" htmlFor="q">
              Buscar por nombre, marca o código de barras
            </label>
            <input
              id="q"
              ref={campo}
              className="riel__campo"
              type="search"
              value={st.texto}
              onChange={(e) => cambiar({ texto: e.target.value })}
              placeholder="leche de almendras, Arcor, 779004…"
              autoComplete="off"
              autoCorrect="off"
              spellCheck={false}
              enterKeyHint="search"
            />

            {st.texto ? (
              <button
                type="button"
                className="riel__limpiar"
                onClick={() => {
                  cambiar({ texto: '' });
                  campo.current?.focus();
                }}
              >
                <IconoCruz tam={18} />
                <span className="solo-lectores">Borrar la búsqueda</span>
              </button>
            ) : (
              <span className="riel__tecla" aria-hidden="true">
                /
              </span>
            )}
          </div>

          <div className="leyenda">
            {ORDEN_ESTADOS.map((e) => {
              const v = VEREDICTOS[e];
              return (
                <label key={e} className={`marca-v v v--${v.tono}`}>
                  <input
                    type="checkbox"
                    checked={st.estados.has(e)}
                    onChange={() => alternarEstado(e)}
                  />
                  <span className="marca-v__muestra" aria-hidden="true" />
                  <span className="marca-v__texto">{v.etiqueta}</span>
                  {filas !== null && (
                    <span className="marca-v__conteo">
                      {numero(conteos.get(e) ?? 0)}
                    </span>
                  )}
                </label>
              );
            })}
          </div>

          <div className="tamiz">
            <label className="solo-lectores" htmlFor="cat">
              Filtrar por categoría
            </label>
            <select
              id="cat"
              className="tamiz__selector"
              value={
                categorias.find((c) => c.nombre === st.categoria)?.slug ?? ''
              }
              onChange={(e) =>
                cambiar({
                  categoria:
                    categorias.find((c) => c.slug === e.target.value)?.nombre ??
                    null,
                })
              }
            >
              <option value="">Todas las categorías</option>
              {categorias.map((c) => (
                <option key={c.slug} value={c.slug}>
                  {c.nombre} ({numero(c.total)})
                </option>
              ))}
            </select>

            <label className="tamiz__opcion">
              <input
                type="checkbox"
                checked={st.soloConIngredientes}
                onChange={(e) =>
                  cambiar({ soloConIngredientes: e.target.checked })
                }
              />
              Con lista de ingredientes
            </label>

            <label className="tamiz__opcion">
              <input
                type="checkbox"
                checked={st.soloConfirmados}
                onChange={(e) => cambiar({ soloConfirmados: e.target.checked })}
              />
              En góndola hoy
            </label>

            {/* La evidencia más fuerte que existe en el catálogo: no es lo que
                declara el fabricante ni lo que publica el supermercado, es el
                registro del Estado. Son pocos productos —92 sobre 7.397— y
                justamente por eso vale poder aislarlos. */}
            <label className="tamiz__opcion">
              <input
                type="checkbox"
                checked={st.soloAnmat}
                onChange={(e) => cambiar({ soloAnmat: e.target.checked })}
              />
              Certificado por ANMAT
            </label>
          </div>
        </div>
      </div>

      <div className="contenedor">
        <div className="recuento">
          {/* Solo el conteo es región viva: meter el botón acá adentro haría
              que cada tecla lo re-anunciara junto con el número. */}
          <span role="status" aria-live="polite">
            {filas === null && !error ? (
              `Cargando ${numero(total)} productos…`
            ) : (
              <>
                <strong>{numero(resultados.length)}</strong>{' '}
                {resultados.length === 1 ? 'producto' : 'productos'}
                {st.texto.trim() && <> para «{st.texto.trim()}»</>}
              </>
            )}
          </span>
          {hayFiltro && (
            <button type="button" className="enlace-boton" onClick={limpiarTodo}>
              Limpiar todo
            </button>
          )}
        </div>

        {error && (
          <div className="aviso-bloque">
            <h2>No pudimos cargar el catálogo</h2>
            <p>Revisá tu conexión y volvé a cargar la página.</p>
          </div>
        )}

        {filas !== null && resultados.length === 0 && (
          <div className="aviso-bloque">
            <h2>Sin resultados</h2>
            <p>
              Probá con menos palabras, o revisá si algún filtro está dejando
              afuera lo que buscás.
            </p>
          </div>
        )}

        {(mostrarSemilla || resultados.length > 0) && (
          <>
            {/* El h1 de la página es el título; sin este h2 los nombres de
                producto (h3) saltarían un nivel de encabezado. */}
            <h2 className="solo-lectores">Resultados</h2>
            <ul className="corrida">
              {mostrarSemilla
                ? semilla.map((p) => (
                    <Tira key={p.slug} p={p} fuenteLegible={fuenteLegible} />
                  ))
                : resultados
                    .slice(0, visibles)
                    .map((p) => (
                      <Tira key={p.ean} p={p} fuenteLegible={fuenteLegible} />
                    ))}
            </ul>

            {mostrarSemilla && <div className="cargando">Cargando el resto…</div>}

            {!mostrarSemilla && visibles < resultados.length && (
              <button
                type="button"
                className="mas"
                onClick={() => setSt((s) => ({ ...s, tandas: s.tandas + 1 }))}
              >
                Ver {numero(Math.min(TANDA, resultados.length - visibles))} más
                <span className="solo-lectores">
                  {' '}
                  de {numero(resultados.length)} resultados
                </span>
              </button>
            )}
          </>
        )}
      </div>
    </>
  );
}
