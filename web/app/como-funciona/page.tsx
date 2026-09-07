import type { Metadata } from 'next';
import Link from 'next/link';

import { meta } from '@/lib/catalogo';
import { SITIO } from '@/lib/sitio';
import { numero, porcentaje } from '@/lib/veredicto';

export const metadata: Metadata = {
  title: 'Cómo funciona',
  description:
    'De dónde salen los datos, cómo se decide cada veredicto y qué pasa ' +
    'cuando no alcanza la información. Sin cajas negras.',
  alternates: { canonical: '/como-funciona/' },
};

/** Las fuentes agrupadas como se explican, no como se llaman en la base. */
const CAPAS = [
  {
    titulo: 'Alguien lo certificó',
    fuentes: ['certificacion_oficial', 'off_label', 'sello_super'],
    cuerpo:
      'El registro oficial de ANMAT, la declaración del propio fabricante o ' +
      'el sello de certificación que publica el supermercado en su ficha. Es ' +
      'la evidencia más fuerte que existe: alguien se hizo responsable por ' +
      'escrito.',
  },
  {
    titulo: 'Leímos la lista de ingredientes',
    fuentes: ['ingredientes', 'ingredientes_super', 'off_analysis'],
    cuerpo:
      'El caballo de batalla. Se compara cada ingrediente declarado contra un ' +
      'léxico de origen animal, vegetal y ambiguo, construido a mano y ' +
      'auditado contra el Código Alimentario Argentino. Si un ingrediente ' +
      'puede ser animal o vegetal según el fabricante —la lecitina, el INS ' +
      '471, la margarina a secas— no se decide: se manda a revisar.',
  },
  {
    titulo: 'Es el mismo producto que otro',
    fuentes: ['duplicado'],
    cuerpo:
      'Un mismo producto suele tener varios códigos de barras según la ' +
      'presentación. Cuando uno de ellos ya está resuelto con evidencia ' +
      'directa, el veredicto se propaga a los demás.',
  },
  {
    titulo: 'Lo estimamos por el nombre',
    fuentes: ['heuristica', 'ml'],
    cuerpo:
      'El último recurso, y el más débil: reglas sobre el nombre comercial. ' +
      'Que un producto se llame «Café instantáneo» hace muy probable que sea ' +
      'apto, pero no es lo mismo que haber leído la etiqueta. Cada vez que un ' +
      'veredicto sale de acá, la ficha lo dice con todas las letras.',
  },
  {
    titulo: 'No sabemos',
    fuentes: ['sin_datos'],
    cuerpo:
      'Ni ingredientes, ni certificación, ni un nombre que diga algo. Antes ' +
      'que arriesgar, decimos que no sabemos.',
  },
];

export default function ComoFunciona() {
  const m = meta();
  const suma = (fuentes: string[]) =>
    fuentes.reduce((t, f) => t + (m.por_fuente[f] ?? 0), 0);

  return (
    <div className="contenedor">
      <article className="prosa">
        <h1>Cómo funciona</h1>
        <p className="hero__bajada">
          Cualquiera puede publicar una lista de productos veganos. Lo difícil
          —y lo único que hace que una lista sirva— es poder decir de dónde
          salió cada dato.
        </p>

        <ul className="cifras">
          <li className="cifra">
            <span className="cifra__valor">{numero(m.total)}</span>
            <span className="cifra__etiqueta">productos en el catálogo</span>
          </li>
          <li className="cifra">
            <span className="cifra__valor">
              {porcentaje(m.con_evidencia, m.total)}
            </span>
            <span className="cifra__etiqueta">
              resueltos con evidencia sobre el producto real
            </span>
          </li>
          <li className="cifra">
            <span className="cifra__valor">{numero(m.con_ingredientes)}</span>
            <span className="cifra__etiqueta">
              con su lista de ingredientes leída
            </span>
          </li>
          <li className="cifra">
            <span className="cifra__valor">{numero(m.confirmados)}</span>
            <span className="cifra__etiqueta">
              confirmados hoy en una góndola real
            </span>
          </li>
        </ul>

        <h2>La regla que manda sobre todas</h2>
        <p>
          <strong>Ante la duda, no decimos que es apto.</strong> Equivocarse
          hacia «no apto» le hace perder un producto a alguien; equivocarse
          hacia «apto» le hace comer algo que decidió no comer. Los dos errores
          no pesan igual, así que el sistema está deliberadamente inclinado: un
          ingrediente ambiguo nunca produce un «apto», produce un «a revisar».
        </p>
        <p>
          Por eso hay {numero(m.por_estado.revisar)} productos sin veredicto. No
          es que falten cargar: es que con lo que sabemos, afirmar sería mentir.
        </p>

        <h2>Las cuatro maneras de saber</h2>
        <p>
          Cada producto se resuelve con la mejor evidencia disponible, en este
          orden. La ficha de cada uno dice cuál se usó.
        </p>

        {CAPAS.map((capa) => {
          const n = suma(capa.fuentes);
          return (
            <section key={capa.titulo}>
              <h3>
                {capa.titulo} — {numero(n)} productos (
                {porcentaje(n, m.total)})
              </h3>
              <p>{capa.cuerpo}</p>
            </section>
          );
        })}

        <h2>De dónde salen los datos</h2>
        <ul>
          <li>
            <strong>Open Food Facts</strong>, la base colaborativa y abierta de
            productos alimenticios: nombres, marcas, listas de ingredientes y
            etiquetas declaradas.
          </li>
          <li>
            <strong>El registro de ANMAT</strong>, para los productos con
            atributo vegano declarado oficialmente.
          </li>
          <li>
            <strong>Las fichas públicas de Carrefour, Vea, Día, Jumbo y
            Disco</strong>. De acá salen dos cosas: la lista de ingredientes
            que el supermercado publica y la confirmación de que el producto se
            vende hoy, no hace cinco años.
          </li>
        </ul>

        <h2>Lo que sacamos del catálogo</h2>
        <p>
          Open Food Facts se llena escaneando códigos de barras, y comparte el
          pool de códigos con Open Beauty Facts. Resultado: se cuelan shampoos,
          cremas y hasta medicamentos, además de fichas que alguien escaneó y
          nunca completó.
        </p>
        <p>
          Se descarta un producto solo si le faltan{' '}
          <strong>las cuatro cosas a la vez</strong>: categoría, lista de
          ingredientes, presencia en alguna góndola y veredicto fundado. Con que
          tenga una sola señal, se queda. El criterio ingenuo —«sacar lo que no
          tiene categoría»— se llevaba puestos 1.608 productos bien
          clasificados, entre ellos 457 con sello vegano certificado.
        </p>

        <div className="aviso">
          <p style={{ marginBottom: 0 }}>
            <strong>«Apto» quiere decir vegano</strong>: sin ingredientes de
            origen animal. No quiere decir <em>cruelty-free</em>. Si la marca
            testea en animales, eso no figura en ninguna de estas fuentes y este
            sitio no lo puede responder.
          </p>
        </div>

        <h2>Errores</h2>
        <p>
          Los hay. Si encontrás uno, el código y los datos son abiertos:{' '}
          <a href={SITIO.repo}>el repositorio está en GitHub</a> y se puede
          abrir un issue con el código de barras del producto.
        </p>

        <p>
          <Link href="/">← Volver al buscador</Link>
        </p>
      </article>
    </div>
  );
}
