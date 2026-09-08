import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';

import { IconoVeredicto } from '@/components/Iconos';
import { claseVeredicto } from '@/components/Sello';
import { Tira } from '@/components/Tira';
import { deCategoria, meta, producto, productos, slugCategoria } from '@/lib/catalogo';
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

  // Vecinos alfabéticos dentro del rubro, no los primeros seis de la
  // categoría: con `slice(0, 6)` las casi tres mil fichas de «Otros» se
  // enlazaban entre sí siempre a los mismos seis productos, que para alguien
  // recorriendo el sitio es una puerta que da siempre al mismo lugar.
  const hermanos = p.categoria ? deCategoria(p.categoria) : [];
  const donde = hermanos.findIndex((o) => o.ean === p.ean);
  const parecidos = hermanos
    .slice(Math.max(0, donde - 3), donde + 4)
    .filter((o) => o.ean !== p.ean)
    .slice(0, 6);

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
    <div className={claseVeredicto(p.estado)}>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      <div className="contenedor">
        <nav className="migas" aria-label="Miga de pan">
          <Link href="/">Inicio</Link>
          {p.categoria && catSlug && (
            <>
              {' / '}
              <Link href={`/categoria/${catSlug}/`}>{p.categoria}</Link>
            </>
          )}
        </nav>

        <div className="titular">
          {/* La foto va al lado del nombre: quien llega desde una búsqueda
              necesita confirmar de un vistazo que es el producto que tiene en
              la mano, antes de leer el veredicto. El alt va vacío a propósito,
              porque el h1 de al lado ya dice cuál es. */}
          <div className="producto__cabecera">
            {p.imagen && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                className="producto__foto"
                src={p.imagen}
                alt=""
                width={80}
                height={80}
                decoding="async"
              />
            )}
            <div>
              <h1>{p.nombre}</h1>
              {p.marca && <p className="titular__bajada">{p.marca}</p>}
            </div>
          </div>
        </div>

        {/* Acá hay un solo producto y la respuesta es toda la pantalla: en la
            corrida el color es una columna angosta porque compite con miles,
            pero en la ficha el veredicto se queda con el frame entero. */}
        <section className="dictamen" aria-labelledby="veredicto">
          <h2 id="veredicto" className="solo-lectores">
            Veredicto
          </h2>
          <p className="dictamen__frase">
            <IconoVeredicto estado={v.estado} tam={32} />
            <span>
              {p.estado === 'revisar'
                ? `Sobre este producto todavía no podemos decidir`
                : `Este producto ${v.titular}`}
            </span>
          </p>
          <p className="dictamen__glosa">{v.explicacion}</p>
        </section>

        <div className="ficha-grilla">
          <div>
            {p.motivo && (
              <section className="bloque">
                <h2 className="bloque__titulo">Por qué</h2>
                <p className="bloque__cuerpo">{p.motivo}</p>
              </section>
            )}

            {p.ingredientes && (
              <section className="bloque">
                <h2 className="bloque__titulo">
                  Ingredientes declarados
                  {disparador && ` — señalamos «${disparador}»`}
                </h2>
                <p className="bloque__cuerpo ingredientes">
                  {trozos.map((t, i) =>
                    t.resaltado ? (
                      <mark key={i}>{t.texto}</mark>
                    ) : (
                      <span key={i}>{t.texto}</span>
                    ),
                  )}
                </p>
              </section>
            )}

            <p className="nota">
              El envase manda. Estos datos vienen de bases públicas y de las
              fichas que publican los supermercados, que pueden estar
              desactualizadas si el fabricante cambió la fórmula.{' '}
              {p.estado === 'apto' && (
                <>
                  Si sos alérgico o celíaco,{' '}
                  <strong>leé siempre la etiqueta</strong>: acá analizamos
                  origen animal, no trazas ni alérgenos.
                </>
              )}
            </p>
          </div>

          <aside>
            <section className="bloque">
              <h2 className="bloque__titulo">De dónde sale este dato</h2>
              <p className="bloque__cuerpo">
                {conEvidencia && (
                  <IconoVeredicto estado="apto" tam={15} />
                )}{' '}
                {m.fuente_legible[p.fuente] ?? p.fuente}
              </p>
              {!conEvidencia && (
                <p className="bloque__cuerpo nota">
                  Es una estimación a partir del nombre comercial, no una
                  lectura de la etiqueta. Tomala con pinzas.
                </p>
              )}
            </section>

            <section className="bloque">
              <h2 className="bloque__titulo">Ficha</h2>
              <dl className="bloque__cuerpo datos">
                <div>
                  <dt>Código de barras</dt>
                  <dd className="codigo">{p.ean}</dd>
                </div>
                {p.categoria && (
                  <div>
                    <dt>Categoría</dt>
                    <dd>
                      {catSlug ? (
                        <Link href={`/categoria/${catSlug}/`}>
                          {p.categoria}
                        </Link>
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
                {p.cadenas && p.cadenas.length > 0 && (
                  <div>
                    <dt>Visto en góndola</dt>
                    <dd>
                      {p.cadenas
                        .map((c) => m.cadena_legible[c] ?? c)
                        .join(', ')}
                    </dd>
                  </div>
                )}
              </dl>
            </section>
          </aside>
        </div>
      </div>

      {parecidos.length > 0 && (
        <div className="contenedor">
          <section className="bloque">
            <h2 className="bloque__titulo">Otros de {p.categoria}</h2>
            <ul className="corrida bloque__cuerpo">
              {parecidos.map((o) => (
                <Tira key={o.ean} p={o} fuenteLegible={m.fuente_legible} />
              ))}
            </ul>
          </section>
        </div>
      )}
    </div>
  );
}
