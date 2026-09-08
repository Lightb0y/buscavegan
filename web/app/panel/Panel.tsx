'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { IconoCruz, IconoLupa, IconoVeredicto } from '@/components/Iconos';
import { claseVeredicto } from '@/components/Sello';
import { abrir, cerrar, estaAbierto, verificar } from '@/lib/acceso';
import { buscar, rehidratar, type Fila } from '@/lib/buscar';
import {
  aCsv,
  guardarCorrecciones,
  guardarRevisor,
  leerCorrecciones,
  leerRevisor,
  nombreDeArchivo,
  type Correccion,
} from '@/lib/panel';
import type { Estado, IndiceCrudo } from '@/lib/tipos';
import { numero, ORDEN_ESTADOS, VEREDICTOS } from '@/lib/veredicto';

/** Cuántos resultados se pintan de una. Acá no hace falta paginar como en el
 *  buscador público: se llega por búsqueda, no por barrido. */
const TOPE = 60;

export function Panel() {
  const [abierta, setAbierta] = useState(false);
  const [listo, setListo] = useState(false);

  // Se resuelve en el cliente: en el HTML del build nadie está logueado.
  useEffect(() => {
    setAbierta(estaAbierto());
    setListo(true);
  }, []);

  if (!listo) return null;
  return abierta ? (
    <Curaduria alSalir={() => setAbierta(false)} />
  ) : (
    <Puerta alEntrar={() => setAbierta(true)} />
  );
}

// --- la puerta -------------------------------------------------------------

function Puerta({ alEntrar }: { alEntrar: () => void }) {
  const [usuario, setUsuario] = useState('');
  const [clave, setClave] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [probando, setProbando] = useState(false);

  const enviar = async (e: React.FormEvent) => {
    e.preventDefault();
    setProbando(true);
    setError(null);
    const r = await verificar(usuario, clave);
    setProbando(false);
    if (r.ok) {
      abrir();
      alEntrar();
      return;
    }
    setError(
      r.motivo === 'sin-cripto'
        ? 'Este navegador no expone Web Crypto, que es lo que compara la ' +
          'clave. Suele pasar al abrir el sitio por http en vez de https.'
        : 'Usuario o contraseña incorrectos.',
    );
  };

  return (
    <div className="contenedor">
      <div className="puerta">
        <h1>Panel de curaduría</h1>
        <p className="puerta__bajada">
          Para corregir a mano la clasificación de un producto cuando el
          pipeline se equivoca.
        </p>

        <form className="puerta__form" onSubmit={enviar}>
          <label className="campo">
            <span className="campo__rotulo">Usuario</span>
            <input
              className="campo__caja"
              type="text"
              value={usuario}
              onChange={(e) => setUsuario(e.target.value)}
              autoComplete="username"
              autoCapitalize="none"
              spellCheck={false}
              required
            />
          </label>

          <label className="campo">
            <span className="campo__rotulo">Contraseña</span>
            <input
              className="campo__caja"
              type="password"
              value={clave}
              onChange={(e) => setClave(e.target.value)}
              autoComplete="current-password"
              required
            />
          </label>

          <button className="boton" type="submit" disabled={probando}>
            {probando ? 'Verificando…' : 'Entrar'}
          </button>
        </form>

        {error && (
          <p className="puerta__error" role="alert">
            {error}
          </p>
        )}
      </div>
    </div>
  );
}

// --- el panel --------------------------------------------------------------

function Curaduria({ alSalir }: { alSalir: () => void }) {
  const [filas, setFilas] = useState<Fila[] | null>(null);
  const [error, setError] = useState(false);
  const [texto, setTexto] = useState('');
  const [correcciones, setCorrecciones] = useState<Record<string, Correccion>>(
    {},
  );
  const [revisor, setRevisor] = useState('');
  const [soloCorregidos, setSoloCorregidos] = useState(false);
  const [sinGuardar, setSinGuardar] = useState(false);
  const campo = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setCorrecciones(leerCorrecciones());
    setRevisor(leerRevisor());
  }, []);

  useEffect(() => {
    let vigente = true;
    fetch('/catalogo.json')
      .then((r) => {
        if (!r.ok) throw new Error(String(r.status));
        return r.json() as Promise<IndiceCrudo>;
      })
      .then((crudo) => vigente && setFilas(rehidratar(crudo)))
      .catch(() => vigente && setError(true));
    return () => {
      vigente = false;
    };
  }, []);

  const pendientes = useMemo(
    () =>
      Object.values(correcciones).sort((a, b) =>
        b.cuando.localeCompare(a.cuando),
      ),
    [correcciones],
  );

  const resultados = useMemo(() => {
    if (!filas) return [];
    if (soloCorregidos) {
      const porEan = new Map(filas.map((f) => [f.ean, f]));
      return pendientes
        .map((c) => porEan.get(c.ean))
        .filter((f): f is Fila => Boolean(f));
    }
    if (!texto.trim()) return [];
    return buscar(filas, {
      texto,
      estados: new Set<Estado>(ORDEN_ESTADOS),
      categoria: null,
      soloConfirmados: false,
      soloConIngredientes: false,
      soloAnmat: false,
    }).slice(0, TOPE);
  }, [filas, texto, soloCorregidos, pendientes]);

  const corregir = useCallback(
    (f: Fila, estado: Estado) => {
      setCorrecciones((prev) => {
        const proximas = { ...prev };
        // Volver a elegir el veredicto que ya tiene el pipeline no es una
        // corrección: es sacarla.
        if (estado === f.estado) {
          delete proximas[f.ean];
        } else {
          proximas[f.ean] = {
            ean: f.ean,
            nombre: f.nombre,
            marca: f.marca,
            categoria: f.categoria,
            estadoActual: f.estado,
            estadoCorregido: estado,
            motivoActual: f.motivo,
            revisor: revisor.trim() || 'manual',
            cuando: new Date().toISOString(),
          };
        }
        setSinGuardar(!guardarCorrecciones(proximas));
        return proximas;
      });
    },
    [revisor],
  );

  const descargar = () => {
    const url = URL.createObjectURL(
      new Blob([aCsv(pendientes)], { type: 'text/csv;charset=utf-8' }),
    );
    const a = document.createElement('a');
    a.href = url;
    a.download = nombreDeArchivo();
    // Firefox no dispara el click de un ancla que no está en el documento, y
    // revocar la URL en la misma vuelta le corta la descarga a algunos
    // navegadores: por eso entra al DOM y se limpia recién después.
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 30_000);
  };

  const vaciar = () => {
    if (
      !window.confirm(
        `¿Borrar las ${pendientes.length} correcciones sin exportar?`,
      )
    ) {
      return;
    }
    setCorrecciones({});
    guardarCorrecciones({});
    // Sin esto la vista queda filtrada por una lista que ya no existe.
    setSoloCorregidos(false);
  };

  return (
    <>
      <div className="panel-riel">
        <div className="contenedor panel-riel__fila">
          <span className="panel-riel__lupa">
            <IconoLupa tam={20} />
          </span>
          <label className="solo-lectores" htmlFor="q-panel">
            Buscar el producto a corregir
          </label>
          <input
            id="q-panel"
            ref={campo}
            className="panel-riel__campo"
            type="search"
            value={texto}
            onChange={(e) => {
              setTexto(e.target.value);
              setSoloCorregidos(false);
            }}
            placeholder="nombre, marca o código de barras"
            autoComplete="off"
            spellCheck={false}
          />
          {texto && (
            <button
              type="button"
              className="panel-riel__limpiar"
              onClick={() => {
                setTexto('');
                campo.current?.focus();
              }}
            >
              <IconoCruz tam={18} />
              <span className="solo-lectores">Borrar la búsqueda</span>
            </button>
          )}
        </div>
      </div>

      <div className="contenedor">
        <div className="panel-barra">
          <label className="campo campo--linea">
            <span className="campo__rotulo">Revisor</span>
            <input
              className="campo__caja"
              type="text"
              value={revisor}
              placeholder="tu nombre"
              onChange={(e) => {
                setRevisor(e.target.value);
                guardarRevisor(e.target.value);
              }}
            />
          </label>

          <div className="panel-barra__acciones">
            <button
              type="button"
              className={`chip-panel${soloCorregidos ? ' chip-panel--puesto' : ''}`}
              onClick={() => setSoloCorregidos((v) => !v)}
              disabled={pendientes.length === 0}
            >
              {pendientes.length === 0
                ? 'Sin correcciones'
                : `${numero(pendientes.length)} corregido${pendientes.length === 1 ? '' : 's'}`}
            </button>
            <button
              type="button"
              className="boton"
              onClick={descargar}
              disabled={pendientes.length === 0}
            >
              Descargar CSV
            </button>
            <button
              type="button"
              className="enlace-boton"
              onClick={vaciar}
              disabled={pendientes.length === 0}
            >
              Vaciar
            </button>
            <button type="button" className="enlace-boton" onClick={() => { cerrar(); alSalir(); }}>
              Salir
            </button>
          </div>
        </div>

        {sinGuardar && (
          <p className="panel-aviso" role="alert">
            El navegador no deja guardar en este dispositivo (modo privado o
            almacenamiento bloqueado). Las correcciones siguen en pantalla,
            pero se pierden si recargás: descargá el CSV antes de cerrar.
          </p>
        )}

        {error && (
          <div className="aviso-bloque">
            <h2>No pudimos cargar el catálogo</h2>
            <p>Revisá tu conexión y volvé a cargar la página.</p>
          </div>
        )}

        {!error && filas === null && (
          <div className="cargando">Cargando el catálogo…</div>
        )}

        {filas !== null && !soloCorregidos && !texto.trim() && (
          <div className="aviso-bloque">
            <h2>Buscá el producto</h2>
            <p>
              Escribí el nombre, la marca o el código de barras. Elegí el
              veredicto correcto y queda anotado acá; cuando termines, bajá el
              CSV.
            </p>
          </div>
        )}

        {filas !== null && (soloCorregidos || texto.trim()) && resultados.length === 0 && (
          <div className="aviso-bloque">
            <h2>Sin resultados</h2>
            <p>Probá con menos palabras o con el código de barras.</p>
          </div>
        )}

        {resultados.length > 0 && (
          <ul className="curaduria">
            {resultados.map((f) => (
              <FilaCuraduria
                key={f.ean}
                f={f}
                correccion={correcciones[f.ean]}
                alElegir={(e) => corregir(f, e)}
              />
            ))}
          </ul>
        )}

        <div className="panel-instrucciones">
          <h2>Qué pasa con esto</h2>
          <p>
            El sitio es estático: no hay servidor al que escribirle, así que
            estas correcciones <strong>no se publican solas</strong>. El CSV
            que bajás es el que ya sabe leer la Capa 4 del pipeline, la
            curaduría humana, que pisa a todas las capas automáticas y
            sobrevive al refresco semanal. En la máquina donde está el
            repositorio:
          </p>
          <pre className="panel-comando">
            <code>python revision.py --importar correcciones-2026-09-08.csv</code>
          </pre>
          <p>
            Después <code>python export_web.py</code> y commitear{' '}
            <code>web/data/</code>: el deploy sale solo con ese commit.
          </p>
        </div>
      </div>
    </>
  );
}

function FilaCuraduria({
  f,
  correccion,
  alElegir,
}: {
  f: Fila;
  correccion?: Correccion;
  alElegir: (e: Estado) => void;
}) {
  const elegido = correccion?.estadoCorregido ?? f.estado;

  return (
    <li className={`curaduria__fila${correccion ? ' curaduria__fila--tocada' : ''}`}>
      <div className="curaduria__cabeza">
        <div>
          <h3 className="curaduria__nombre">{f.nombre}</h3>
          <p className="curaduria__meta">
            {[f.marca, f.categoria].filter(Boolean).join(' · ')}
            {f.marca || f.categoria ? ' · ' : ''}
            <span className="curaduria__ean">{f.ean}</span>
          </p>
        </div>
        {correccion && (
          <span className="curaduria__cambio">
            {VEREDICTOS[correccion.estadoActual].etiqueta} →{' '}
            <strong>{VEREDICTOS[correccion.estadoCorregido].etiqueta}</strong>
          </span>
        )}
      </div>

      {f.motivo && <p className="curaduria__motivo">{f.motivo}</p>}

      <div className="curaduria__opciones" role="group" aria-label={`Veredicto de ${f.nombre}`}>
        {ORDEN_ESTADOS.map((e) => {
          const v = VEREDICTOS[e];
          const activo = elegido === e;
          const esDelPipeline = f.estado === e;
          return (
            <button
              key={e}
              type="button"
              className={`opcion-v ${claseVeredicto(e)}${activo ? ' opcion-v--activa' : ''}`}
              aria-pressed={activo}
              onClick={() => alElegir(e)}
            >
              <IconoVeredicto estado={e} tam={16} />
              <span>{v.etiqueta}</span>
              {esDelPipeline && (
                <span className="opcion-v__actual" title="Lo que dice el pipeline hoy">
                  actual
                </span>
              )}
            </button>
          );
        })}
      </div>
    </li>
  );
}
