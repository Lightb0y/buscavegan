'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { Ficha } from '@/components/Ficha';
import { buscar, FILTROS_INICIALES, rehidratar, type Fila } from '@/lib/buscar';
import type { Categoria, Estado, IndiceCrudo } from '@/lib/tipos';
import { numero, ORDEN_ESTADOS, VEREDICTOS } from '@/lib/veredicto';

/** Cuántos resultados se pintan de una. Con 7.397 productos, renderizar todo
 *  congelaría el navegador; de a 48 la primera pantalla entra completa y el
 *  resto se pide a demanda. */
const TANDA = 48;

export function Buscador({
  categorias,
  fuenteLegible,
}: {
  categorias: Categoria[];
  fuenteLegible: Record<string, string>;
}) {
  const [filas, setFilas] = useState<Fila[] | null>(null);
  const [error, setError] = useState(false);

  const [texto, setTexto] = useState('');
  const [estados, setEstados] = useState<Set<Estado>>(
    () => new Set(FILTROS_INICIALES.estados),
  );
  const [categoria, setCategoria] = useState<string | null>(null);
  const [soloConfirmados, setSoloConfirmados] = useState(false);
  const [soloConIngredientes, setSoloConIngredientes] = useState(false);
  const [visibles, setVisibles] = useState(TANDA);

  const campo = useRef<HTMLInputElement>(null);

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

  // Búsqueda compartible: `?q=leche+de+almendras` se lee al entrar y se
  // escribe al tipear, para que el link se pueda pasar por WhatsApp.
  useEffect(() => {
    const q = new URLSearchParams(window.location.search).get('q');
    if (q) setTexto(q);
  }, []);

  useEffect(() => {
    const id = setTimeout(() => {
      const url = new URL(window.location.href);
      if (texto.trim()) url.searchParams.set('q', texto.trim());
      else url.searchParams.delete('q');
      window.history.replaceState(null, '', url);
    }, 300);
    return () => clearTimeout(id);
  }, [texto]);

  // `/` enfoca la búsqueda desde cualquier parte de la página, como en la
  // mayoría de los buscadores. No secuestra la tecla si ya estás escribiendo.
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
        setTexto('');
      }
    };
    window.addEventListener('keydown', enTecla);
    return () => window.removeEventListener('keydown', enTecla);
  }, []);

  const resultados = useMemo(() => {
    if (!filas) return [];
    return buscar(filas, {
      texto,
      estados,
      categoria,
      soloConfirmados,
      soloConIngredientes,
    });
  }, [filas, texto, estados, categoria, soloConfirmados, soloConIngredientes]);

  // Cambió lo que se busca: volver al principio de la lista.
  useEffect(() => {
    setVisibles(TANDA);
  }, [texto, estados, categoria, soloConfirmados, soloConIngredientes]);

  const alternarEstado = useCallback((e: Estado) => {
    setEstados((previos) => {
      const proximos = new Set(previos);
      if (proximos.has(e)) proximos.delete(e);
      else proximos.add(e);
      return proximos;
    });
  }, []);

  const hayFiltro =
    texto.trim() !== '' ||
    categoria !== null ||
    soloConfirmados ||
    soloConIngredientes ||
    estados.size !== ORDEN_ESTADOS.length;

  const limpiarTodo = () => {
    setTexto('');
    setCategoria(null);
    setSoloConfirmados(false);
    setSoloConIngredientes(false);
    setEstados(new Set(ORDEN_ESTADOS));
    campo.current?.focus();
  };

  return (
    <>
      <div className="busqueda">
        <span className="busqueda__lupa" aria-hidden="true">
          <svg width="18" height="18" viewBox="0 0 20 20" fill="none">
            <circle
              cx="8.5"
              cy="8.5"
              r="5.75"
              stroke="currentColor"
              strokeWidth="1.6"
            />
            <path
              d="M13 13l4 4"
              stroke="currentColor"
              strokeWidth="1.6"
              strokeLinecap="round"
            />
          </svg>
        </span>

        <label className="solo-lectores" htmlFor="q">
          Buscar por nombre, marca o código de barras
        </label>
        <input
          id="q"
          ref={campo}
          className="busqueda__campo"
          type="search"
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          placeholder="leche de almendras, Arcor, 779004…"
          autoComplete="off"
          autoCorrect="off"
          spellCheck={false}
          enterKeyHint="search"
        />

        <span className="busqueda__atajo">
          {texto ? (
            <button
              type="button"
              className="busqueda__limpiar"
              onClick={() => {
                setTexto('');
                campo.current?.focus();
              }}
            >
              <span aria-hidden="true">×</span>
              <span className="solo-lectores">Borrar la búsqueda</span>
            </button>
          ) : (
            <kbd className="tecla" aria-hidden="true">
              /
            </kbd>
          )}
        </span>
      </div>

      <div className="filtros">
        {ORDEN_ESTADOS.map((e) => {
          const v = VEREDICTOS[e];
          return (
            <label key={e} className={`chip v v--${v.tono}`}>
              <input
                type="checkbox"
                checked={estados.has(e)}
                onChange={() => alternarEstado(e)}
              />
              <span className="chip__punto" aria-hidden="true" />
              {v.etiqueta}
            </label>
          );
        })}

        <span className="filtros__separador" aria-hidden="true" />

        <label className="solo-lectores" htmlFor="cat">
          Filtrar por categoría
        </label>
        <select
          id="cat"
          className="selector"
          value={categoria ?? ''}
          onChange={(e) => setCategoria(e.target.value || null)}
        >
          <option value="">Todas las categorías</option>
          {categorias.map((c) => (
            <option key={c.slug} value={c.nombre}>
              {c.nombre} ({numero(c.total)})
            </option>
          ))}
        </select>

        <label className="chip">
          <input
            type="checkbox"
            checked={soloConIngredientes}
            onChange={(e) => setSoloConIngredientes(e.target.checked)}
          />
          <span className="chip__punto" aria-hidden="true" />
          Con lista de ingredientes
        </label>

        <label className="chip">
          <input
            type="checkbox"
            checked={soloConfirmados}
            onChange={(e) => setSoloConfirmados(e.target.checked)}
          />
          <span className="chip__punto" aria-hidden="true" />
          En góndola hoy
        </label>
      </div>

      {/* Los cambios de cantidad se anuncian a los lectores de pantalla, que
          si no se quedarían sin saber que la lista cambió. */}
      <div className="resumen" role="status" aria-live="polite">
        <span>
          {filas === null ? (
            'Cargando el catálogo…'
          ) : (
            <>
              <strong>{numero(resultados.length)}</strong>{' '}
              {resultados.length === 1 ? 'producto' : 'productos'}
              {texto.trim() && <> para «{texto.trim()}»</>}
            </>
          )}
        </span>
        {hayFiltro && (
          <button type="button" className="busqueda__limpiar" onClick={limpiarTodo}>
            Limpiar todo
          </button>
        )}
      </div>

      {error && (
        <div className="vacio">
          <h2>No pudimos cargar el catálogo</h2>
          <p>Revisá tu conexión y volvé a cargar la página.</p>
        </div>
      )}

      {!error && filas === null && (
        <div className="cargando">Cargando {numero(7397)} productos…</div>
      )}

      {filas !== null && resultados.length === 0 && (
        <div className="vacio">
          <h2>Sin resultados</h2>
          <p>
            Probá con menos palabras, o revisá si algún filtro está dejando
            afuera lo que buscás.
          </p>
        </div>
      )}

      {resultados.length > 0 && (
        <>
          <ul className="grilla">
            {resultados.slice(0, visibles).map((p) => (
              <Ficha key={p.ean} p={p} fuenteLegible={fuenteLegible} />
            ))}
          </ul>

          {visibles < resultados.length && (
            <button
              type="button"
              className="mas"
              onClick={() => setVisibles((v) => v + TANDA)}
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
    </>
  );
}
