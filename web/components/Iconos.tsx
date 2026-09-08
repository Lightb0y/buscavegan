/** Los iconos del sistema, dibujados.
 *
 *  Antes el veredicto se marcaba con glifos Unicode (`✓ ◐ ✕ ?`). Se ven
 *  distinto en cada plataforma, cambian de peso con la fuente y no comparten
 *  ni grosor ni caja óptica: no eran un sistema de iconos, eran tipografía
 *  disfrazada. Estos cuatro se dibujan sobre la misma grilla de 16, con el
 *  mismo trazo de 2 y las mismas terminaciones redondeadas, y por eso pesan
 *  igual uno al lado del otro en la corrida.
 *
 *  Las cuatro siluetas son deliberadamente distintas entre sí —tilde, disco
 *  mitad lleno, aspa, anillo abierto— para que el veredicto se distinga sin
 *  leer el color ni la palabra. Igual las tres señales viajan siempre juntas.
 */

export type NombreIcono = 'apto' | 'vegetariano' | 'no_apto' | 'revisar';

const TRAZO = {
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 2,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
} as const;

/** El anillo abierto de «a revisar» no se cierra a propósito: el estado es un
 *  recuento que todavía no terminó, no un error. */
const FORMAS: Record<NombreIcono, React.ReactNode> = {
  apto: <path d="M3.5 8.5 6.75 12l5.75-7" {...TRAZO} />,
  vegetariano: (
    <>
      <circle cx="8" cy="8" r="5.25" {...TRAZO} />
      <path d="M8 2.75a5.25 5.25 0 0 0 0 10.5z" fill="currentColor" />
    </>
  ),
  no_apto: (
    <>
      <path d="m4.5 4.5 7 7" {...TRAZO} />
      <path d="m11.5 4.5-7 7" {...TRAZO} />
    </>
  ),
  revisar: (
    <>
      <path d="M8 2.75a5.25 5.25 0 1 1-5.13 6.44" {...TRAZO} />
      <circle cx="8" cy="8" r="1.4" fill="currentColor" />
    </>
  ),
};

export function IconoVeredicto({
  estado,
  tam = 16,
}: {
  estado: NombreIcono;
  tam?: number;
}) {
  return (
    <svg
      className="icono"
      width={tam}
      height={tam}
      viewBox="0 0 16 16"
      aria-hidden="true"
      focusable="false"
    >
      {FORMAS[estado]}
    </svg>
  );
}

/** La lupa del riel de búsqueda, con el mismo trazo que los veredictos. */
export function IconoLupa({ tam = 18 }: { tam?: number }) {
  return (
    <svg
      className="icono"
      width={tam}
      height={tam}
      viewBox="0 0 16 16"
      aria-hidden="true"
      focusable="false"
    >
      <circle cx="7" cy="7" r="4.25" {...TRAZO} />
      <path d="m10.25 10.25 3 3" {...TRAZO} />
    </svg>
  );
}

export function IconoCruz({ tam = 16 }: { tam?: number }) {
  return (
    <svg
      className="icono"
      width={tam}
      height={tam}
      viewBox="0 0 16 16"
      aria-hidden="true"
      focusable="false"
    >
      <path d="m4.5 4.5 7 7" {...TRAZO} />
      <path d="m11.5 4.5-7 7" {...TRAZO} />
    </svg>
  );
}

export function IconoFlecha({
  sentido = 'derecha',
  tam = 16,
}: {
  sentido?: 'izquierda' | 'derecha';
  tam?: number;
}) {
  return (
    <svg
      className="icono"
      width={tam}
      height={tam}
      viewBox="0 0 16 16"
      aria-hidden="true"
      focusable="false"
      style={
        sentido === 'izquierda' ? { transform: 'scaleX(-1)' } : undefined
      }
    >
      <path d="M2.75 8h10.5" {...TRAZO} />
      <path d="m9.25 4 4 4-4 4" {...TRAZO} />
    </svg>
  );
}

/** El isotipo: un cartel de zócalo enganchado al filo del estante. Es la
 *  forma que gobierna toda la interfaz, reducida a diez pixeles. */
export function Isotipo({ tam = 22 }: { tam?: number }) {
  return (
    <svg
      className="isotipo"
      width={tam}
      height={tam}
      viewBox="0 0 24 24"
      aria-hidden="true"
      focusable="false"
    >
      <path d="M2 5.5h20" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
      <rect x="4.25" y="9" width="15.5" height="10.5" rx="0.5" fill="currentColor" />
      <path d="M7.25 14.25 9 16l3.25-4" stroke="var(--stock)" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" fill="none" />
    </svg>
  );
}
