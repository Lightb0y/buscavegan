import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';

import { Ficha } from '@/components/Ficha';
import { categoria, deCategoria, meta } from '@/lib/catalogo';
import { numero, ORDEN_ESTADOS, VEREDICTOS } from '@/lib/veredicto';

/** Una ruta atrapa-todo para `/categoria/lacteos/` y `/categoria/lacteos/3/`.
 *  La paginación no es cosmética: sin ella, los 2.978 productos de «Otros»
 *  saldrían en un solo HTML de varios megas, y encima los productos del final
 *  no tendrían ningún link interno que los descubra. */
const POR_PAGINA = 60;

type Props = { params: Promise<{ ruta: string[] }> };

export const dynamicParams = false;

export function generateStaticParams() {
  const params: { ruta: string[] }[] = [];
  for (const c of meta().categorias) {
    const paginas = Math.max(1, Math.ceil(c.total / POR_PAGINA));
    params.push({ ruta: [c.slug] });
    for (let i = 2; i <= paginas; i++) params.push({ ruta: [c.slug, String(i)] });
  }
  return params;
}

function leer(ruta: string[]) {
  const [slug, pagina] = ruta;
  const cat = categoria(slug);
  if (!cat) return null;
  const n = pagina ? Number(pagina) : 1;
  if (!Number.isInteger(n) || n < 1) return null;

  const todos = deCategoria(cat.nombre);
  const paginas = Math.max(1, Math.ceil(todos.length / POR_PAGINA));
  if (n > paginas) return null;

  return {
    cat,
    n,
    paginas,
    items: todos.slice((n - 1) * POR_PAGINA, n * POR_PAGINA),
    total: todos.length,
  };
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { ruta } = await params;
  const d = leer(ruta);
  if (!d) return { title: 'Categoría no encontrada' };

  const sufijo = d.n > 1 ? ` — página ${d.n}` : '';
  return {
    title: `${d.cat.nombre} aptos veganos${sufijo}`,
    description:
      `${numero(d.total)} productos de ${d.cat.nombre.toLowerCase()} en ` +
      'Argentina, clasificados como aptos veganos, vegetarianos o no aptos, ' +
      'con la evidencia de cada veredicto a la vista.',
    alternates: {
      canonical: `/categoria/${d.cat.slug}/${d.n > 1 ? d.n + '/' : ''}`,
    },
    // La página 2 en adelante no aporta nada nuevo a un buscador, pero sus
    // links a los productos sí: que no indexe, que siga los links.
    robots: d.n > 1 ? { index: false, follow: true } : undefined,
  };
}

export default async function PaginaCategoria({ params }: Props) {
  const { ruta } = await params;
  const d = leer(ruta);
  if (!d) notFound();

  const m = meta();
  const conteo = new Map(ORDEN_ESTADOS.map((e) => [e, 0]));
  for (const p of deCategoria(d.cat.nombre)) {
    conteo.set(p.estado, (conteo.get(p.estado) ?? 0) + 1);
  }

  return (
    <div className="contenedor">
      <nav className="migas" aria-label="Miga de pan">
        <Link href="/">Inicio</Link> / <Link href="/categorias/">Categorías</Link>
      </nav>

      <div className="hero">
        <h1>
          {d.cat.nombre}
          {d.n > 1 && <> — página {d.n}</>}
        </h1>
        <p className="hero__bajada">
          {numero(d.total)} productos. Si ya sabés el nombre,{' '}
          <Link href="/">buscalo en el catálogo completo</Link>.
        </p>

        <ul className="cifras">
          {ORDEN_ESTADOS.map((e) => (
            <li key={e} className="cifra">
              <span className="cifra__valor">{numero(conteo.get(e) ?? 0)}</span>
              <span className="cifra__etiqueta">{VEREDICTOS[e].etiqueta}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* Sin este h2, los nombres de producto (h3) saltarían un nivel desde el
          h1 de la categoría. */}
      <h2 className="solo-lectores">Productos de {d.cat.nombre}</h2>
      <ul className="grilla">
        {d.items.map((p) => (
          <Ficha key={p.ean} p={p} fuenteLegible={m.fuente_legible} />
        ))}
      </ul>

      {d.paginas > 1 && (
        <nav className="resumen" aria-label="Paginación">
          <span>
            Página <strong>{d.n}</strong> de {d.paginas}
          </span>
          <span className="paginacion__links">
            {d.n > 1 && (
              <Link
                href={
                  d.n === 2
                    ? `/categoria/${d.cat.slug}/`
                    : `/categoria/${d.cat.slug}/${d.n - 1}/`
                }
                rel="prev"
              >
                ← Anterior
              </Link>
            )}
            {d.n < d.paginas && (
              <Link href={`/categoria/${d.cat.slug}/${d.n + 1}/`} rel="next">
                Siguiente →
              </Link>
            )}
          </span>
        </nav>
      )}
    </div>
  );
}
