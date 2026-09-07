import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';

import { Ficha } from '@/components/Ficha';
import { claseVeredicto, Sello } from '@/components/Sello';
import { meta, producto, productos, slugCategoria } from '@/lib/catalogo';
import { ingredienteDisparador, partirResaltando } from '@/lib/resaltar';
import { SITIO } from '@/lib/sitio';
import { veredicto } from '@/lib/veredicto';

type Props = { params: Promise<{ slug: string }> };

export const dynamicParams = false;

export function generateStaticParams() {
  return productos().map((p) => ({ slug: p.slug }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const p = producto(slug);
  if (!p) return { title: 'Producto no encontrado' };

  const v = veredicto(p.estado);
  const nombre = p.marca ? `${p.nombre} (${p.marca})` : p.nombre;

  return {
    title: `${nombre}: ${v.etiqueta}`,
    description:
      p.motivo ??
      `${nombre} ${v.titular}. Mirá de dónde sacamos este dato en buscavegan.`,
    alternates: { canonical: `/p/${p.slug}/` },
    openGraph: {
      type: 'article',
      title: `¿${p.nombre} es vegano? — ${v.etiqueta}`,
      description: p.motivo ?? v.explicacion,
      images: p.imagen ? [{ url: p.imagen }] : undefined,
    },
  };
}

export default async function PaginaProducto({ params }: Props) {
  const { slug } = await params;
  const p = producto(slug);
  if (!p) notFound();

  const m = meta();
  const v = veredicto(p.estado);
  const disparador = ingredienteDisparador(p.motivo);
  const trozos = p.ingredientes
    ? partirResaltando(p.ingredientes, disparador)
    : [];
  const conEvidencia = m.fuentes_con_evidencia.includes(p.fuente);
  const catSlug = p.categoria ? slugCategoria(p.categoria) : undefined;

  const parecidos = p.categoria
    ? productos()
        .filter((o) => o.categoria === p.categoria && o.ean !== p.ean)
        .slice(0, 6)
    : [];

  // Solo se declara lo que efectivamente sabemos. Nada de reseñas ni precios
  // inventados para ganar un rich snippet.
  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'Product',
    name: p.nombre,
    ...(p.marca ? { brand: { '@type': 'Brand', name: p.marca } } : {}),
    ...(p.imagen ? { image: p.imagen } : {}),
    gtin13: p.ean.length === 13 ? p.ean : undefined,
    description: p.motivo ?? v.explicacion,
    url: `${SITIO.url}/p/${p.slug}/`,
    additionalProperty: {
      '@type': 'PropertyValue',
      name: 'Apto vegano',
      value: v.etiqueta,
    },
  };

  return (
    <div className="contenedor">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      <nav className="migas" aria-label="Miga de pan">
        <Link href="/">Inicio</Link>
        {p.categoria && catSlug && (
          <>
            {' / '}
            <Link href={`/categoria/${catSlug}/`}>{p.categoria}</Link>
          </>
        )}
      </nav>

      <article className={`producto ${claseVeredicto(p.estado)}`}>
        <div>
          {/* La foto va al lado del nombre, no en la columna lateral: quien
              llega desde una búsqueda necesita confirmar de un vistazo que es
              el producto que tiene en la mano, antes de leer el veredicto. */}
          <div className={p.imagen ? 'producto__cabecera' : undefined}>
            {p.imagen && (
              // alt vacío a propósito: el h1 de al lado ya dice qué producto
              // es, y repetirlo haría que el lector de pantalla lo anuncie dos
              // veces seguidas.
              // eslint-disable-next-line @next/next/no-img-element
              <img
                className="producto__foto"
                src={p.imagen}
                alt=""
                width={88}
                height={88}
                decoding="async"
              />
            )}
            <div>
              <h1 className="producto__titulo">{p.nombre}</h1>
              {p.marca && <p className="producto__marca">{p.marca}</p>}
            </div>
          </div>

          <section className="dictamen" aria-labelledby="veredicto">
            <h2 id="veredicto" className="solo-lectores">
              Veredicto
            </h2>
            <Sello estado={p.estado} grande />
            <p className="dictamen__frase">
              {p.estado === 'revisar'
                ? `Sobre «${p.nombre}» todavía no podemos decidir.`
                : `«${p.nombre}» ${v.titular}.`}
            </p>
            <p className="dictamen__detalle">{v.explicacion}</p>
          </section>

          {p.motivo && (
            <section className="bloque">
              <h2 className="bloque__titulo">Por qué</h2>
              <p>{p.motivo}</p>
            </section>
          )}

          {p.ingredientes && (
            <section className="bloque">
              <h2 className="bloque__titulo">
                Ingredientes declarados
                {disparador && ` — señalamos «${disparador}»`}
              </h2>
              <p className="ingredientes">
                {trozos.map((t, i) =>
                  t.resaltado ? <mark key={i}>{t.texto}</mark> : <span key={i}>{t.texto}</span>,
                )}
              </p>
            </section>
          )}

          <p className="aviso">
            El envase manda. Estos datos vienen de bases públicas y de las
            fichas que publican los supermercados, que pueden estar
            desactualizadas si el fabricante cambió la fórmula.{' '}
            {p.estado === 'apto' && (
              <>
                Si sos alérgico o celíaco, <strong>leé siempre la etiqueta</strong>:
                acá analizamos origen animal, no trazas ni alérgenos.
              </>
            )}
          </p>
        </div>

        <aside>
          <div className="panel">
            <h2 className="panel__titulo">De dónde sale este dato</h2>
            <p className="evidencia">
              {conEvidencia && (
                <span className="evidencia__marca" aria-hidden="true">
                  ✓
                </span>
              )}
              <span>{m.fuente_legible[p.fuente] ?? p.fuente}</span>
            </p>
            {!conEvidencia && (
              <p className="panel__nota">
                Es una estimación a partir del nombre comercial, no una lectura
                de la etiqueta. Tomala con pinzas.
              </p>
            )}
          </div>

          <div className="panel">
            <h2 className="panel__titulo">Ficha</h2>
            <dl className="datos">
              <div>
                <dt>Código de barras</dt>
                <dd className="ean">{p.ean}</dd>
              </div>
              {p.categoria && (
                <div>
                  <dt>Categoría</dt>
                  <dd>
                    {catSlug ? (
                      <Link href={`/categoria/${catSlug}/`}>{p.categoria}</Link>
                    ) : (
                      p.categoria
                    )}
                  </dd>
                </div>
              )}
              {p.confianza !== undefined && (
                <div>
                  <dt>Confianza</dt>
                  <dd>{Math.round(p.confianza * 100)}%</dd>
                </div>
              )}
            </dl>
          </div>

          {p.cadenas && p.cadenas.length > 0 && (
            <div className="panel">
              <h2 className="panel__titulo">Visto en góndola</h2>
              <ul className="cadenas">
                {p.cadenas.map((c) => (
                  <li key={c} className="cadena">
                    {m.cadena_legible[c] ?? c}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </aside>
      </article>

      {parecidos.length > 0 && (
        <section className="bloque">
          <h2 className="bloque__titulo">Otros de {p.categoria}</h2>
          <ul className="grilla">
            {parecidos.map((o) => (
              <Ficha key={o.ean} p={o} fuenteLegible={m.fuente_legible} />
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
