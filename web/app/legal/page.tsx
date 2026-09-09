import type { Metadata } from 'next';
import Link from 'next/link';

import { meta } from '@/lib/catalogo';
import { SITIO } from '@/lib/sitio';
import { numero } from '@/lib/veredicto';

export const metadata: Metadata = {
  title: 'Aviso legal',
  description:
    'Qué garantiza y qué no garantiza este sitio, de dónde salen los datos ' +
    'y qué se mide de tu visita.',
  alternates: { canonical: '/legal/' },
};

export default function PaginaLegal() {
  const m = meta();

  return (
    <div className="contenedor">
      <article className="prosa">
        <h1>Aviso legal</h1>
        <p className="titular__bajada">
          Qué garantiza este sitio, qué no, y qué se mide de tu visita. Escrito
          con el mismo criterio que el resto: si hay algo que no podemos
          afirmar, lo decimos.
        </p>

        <section>
          <h2>El envase manda. Siempre.</h2>
          <p>
            buscavegan es una herramienta de <strong>orientación</strong>. Toda
            la información sale de bases de datos públicas y de las fichas que
            publican los supermercados, no de tener el producto en la mano.
          </p>
          <p>
            Eso significa que un dato puede estar desactualizado sin que
            nosotros lo sepamos: los fabricantes cambian fórmulas y proveedores,
            y no existe ningún aviso automático cuando eso pasa. Ante cualquier
            diferencia entre lo que dice este sitio y lo que dice el envase que
            tenés adelante, <strong>el envase tiene razón</strong>.
          </p>
        </section>

        <section>
          <h2>Si tenés una alergia o una condición médica, esto no alcanza</h2>
          <p>
            Este sitio analiza <strong>origen animal de los ingredientes</strong>
            . No analiza alérgenos, no analiza trazas ni contaminación cruzada,
            y no analiza gluten. No es información médica ni nutricional, y no
            reemplaza la consulta con un profesional de la salud.
          </p>
          <p>
            Si una equivocación puede mandarte al hospital —alergia severa,
            celiaquía, cualquier condición donde el error no sea negociable—
            leé la etiqueta y consultá al fabricante. Una herramienta gratuita
            que lee bases de datos públicas no es el lugar donde apoyar esa
            decisión.
          </p>
        </section>

        <section>
          <h2>«Apto» quiere decir vegano, y nada más</h2>
          <p>
            Cuando el sitio dice que un producto es <strong>apto</strong>, dice
            que según la evidencia disponible no tiene ingredientes de origen
            animal. No dice que sea <em>cruelty-free</em>: el testeo en animales
            no figura en ninguna de las fuentes de datos que usamos, así que
            sobre eso el sitio no se pronuncia ni a favor ni en contra.
          </p>
          <p>
            Tampoco dice nada sobre si el producto es saludable, sobre sus
            condiciones de producción ni sobre la política de la empresa que lo
            fabrica.
          </p>
        </section>

        <section>
          <h2>Qué tan seguros estamos de cada veredicto</h2>
          <p>
            Depende del producto, y por eso cada ficha lo dice. De los{' '}
            {numero(m.total)} productos del catálogo, la mayoría se resuelve
            leyendo la lista de ingredientes o con una certificación, pero una
            parte se estima a partir del nombre comercial. Cuando pasa eso,{' '}
            <strong>la ficha lo aclara en el mismo lugar donde da el
            veredicto</strong>, no en letra chica.
          </p>
          <p>
            El sistema está deliberadamente inclinado a decir «no sabemos» antes
            que arriesgar un «apto». Aun así puede equivocarse en las dos
            direcciones. Cómo se decide cada caso está explicado en{' '}
            <Link href="/como-funciona/">Cómo funciona</Link>.
          </p>
        </section>

        <section>
          <h2>Sin garantías</h2>
          <p>
            El sitio se ofrece <strong>tal cual está</strong>, gratis y sin
            garantía de exactitud, de completitud ni de disponibilidad. No nos
            responsabilizamos por decisiones de compra o de consumo tomadas a
            partir de esta información, ni por los daños que pudieran derivarse
            de un dato equivocado o desactualizado.
          </p>
          <p>
            No es una limitación de compromiso: es una descripción honesta de lo
            que puede prometer un proyecto que cruza bases de datos públicas.
            Corregimos todo error que se nos señale.
          </p>
        </section>

        <section>
          <h2>Encontraste un error</h2>
          <p>
            Es la contribución más valiosa que existe para este proyecto. Cada
            error que alguien señala se revisa a mano, se corrige, y la
            corrección queda guardada de forma que sobreviva a las
            actualizaciones automáticas.
          </p>
          <p>
            Escribinos a{' '}
            <a href={`mailto:${SITIO.contacto}`}>{SITIO.contacto}</a> con el
            nombre del producto y su código de barras.
          </p>
        </section>

        <section>
          <h2>De dónde salen los datos</h2>
          <p>
            Los datos de productos provienen de{' '}
            <a
              href="https://world.openfoodfacts.org"
              rel="noopener noreferrer"
              target="_blank"
            >
              Open Food Facts
            </a>
            , una base colaborativa y abierta, publicada bajo licencia{' '}
            <a
              href="https://opendatacommons.org/licenses/odbl/1-0/"
              rel="noopener noreferrer"
              target="_blank"
            >
              ODbL
            </a>
            ; las fotos de producto son de sus respectivos colaboradores. Se
            suman el registro público de productos con atributo vegano de{' '}
            <strong>ANMAT</strong> y las fichas que publican en sus sitios
            Carrefour, Vea, Día, Jumbo y Disco.
          </p>
          <p>
            Las marcas, nombres comerciales e imágenes de producto pertenecen a
            sus titulares y se muestran únicamente para identificar el producto
            del que se habla. Este sitio no tiene relación comercial con ninguna
            de esas empresas, no recibe pagos por figurar ni por el veredicto que
            se le asigna a un producto.
          </p>
        </section>

        <section>
          <h2>Qué se mide de tu visita</h2>
          <p>
            Lo mínimo para saber si el sitio le sirve a alguien:{' '}
            <strong>cuántas visitas hay</strong> y{' '}
            <strong>qué se buscó sin encontrar</strong> —eso último es,
            literalmente, la lista de qué productos falta cargar—.
          </p>
          <p>
            No se usan cookies, no se registra tu dirección IP y no hay forma de
            asociar una visita con una persona. Tampoco se guardan las búsquedas
            que sí encontraron resultados. No hay publicidad ni rastreadores de
            terceros.
          </p>
        </section>

        <div className="nota">
          <p>
            Última actualización de esta página:{' '}
            {new Date(m.actualizado + 'T00:00:00').toLocaleDateString('es-AR', {
              day: 'numeric',
              month: 'long',
              year: 'numeric',
            })}
            .
          </p>
        </div>
      </article>
    </div>
  );
}
