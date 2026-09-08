/** Tests de la búsqueda y del resaltado.
 *
 *     npm test
 *
 * Node 24 ejecuta TypeScript directamente, así que no hace falta compilar ni
 * sumar un framework de tests.
 */
import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  buscar,
  completitud,
  FUENTE_ANMAT,
  normalizar,
  rehidratar,
  type Fila,
} from '../lib/buscar.ts';
import { ingredienteDisparador, partirResaltando } from '../lib/resaltar.ts';
import type { Estado, IndiceCrudo } from '../lib/tipos.ts';

const TODOS = new Set<Estado>(['apto', 'vegetariano', 'no_apto', 'revisar']);

function indice(): Fila[] {
  const crudo: IndiceCrudo = {
    v: 1,
    estados: ['apto', 'vegetariano', 'no_apto', 'revisar'],
    marcas: ['Ades', 'Arcor', 'La Serenísima'],
    categorias: ['Bebidas vegetales', 'Lácteos'],
    fuentes: ['ingredientes', 'heuristica', 'certificacion_oficial'],
    cadenas: ['disco', 'carrefour'],
    p: [
      ['111', 'leche-de-almendras-111', 'Leche de almendras', 0, 0, 0, 0, 1, 1, 'Sin ingredientes animales', '779/000/000/1111/front_es.4.200.jpg'],
      ['222', 'leche-entera-222', 'Leche entera', 2, 1, 1, 0, 0, 1, 'Contiene leche: es vegetariano pero no vegano', ''],
      ['333', 'alfajor-333', 'Alfajor de chocolate', 1, 1, 2, 0, 3, 0, 'Contiene gelatina, de origen animal', '779/000/000/3333/front_es.1.200.jpg'],
      ['444', 'lechuga-444', 'Lechuga criolla', -1, -1, 0, 1, 0, 0, '', ''],
      // Los dos con sello de ANMAT. El segundo es el caso que obliga a que el
      // filtro NO sea tambien un filtro de veredicto: tiene el sello, pero su
      // lista de ingredientes lo contradice y por eso quedo en «a revisar».
      // Quien filtra por ANMAT tiene que verlo igual, o el filtro esconderia
      // justo el producto sobre el que hay que desconfiar.
      ['555', 'medallones-555', 'Medallones de quinoa', -1, -1, 0, 2, 0, 0, 'Registro oficial de ANMAT con atributo vegano', ''],
      ['666', 'dulce-666', 'Dulce de leche vegano', -1, -1, 3, 2, 0, 1, 'Certificado por ANMAT, pero su propia lista de ingredientes dice lo contrario: contiene leche', ''],
    ],
  };
  return rehidratar(crudo);
}

const soloNombres = (f: Fila[]) => f.map((x) => x.nombre);

// --- normalización --------------------------------------------------------

test('normalizar saca tildes y baja a minúsculas', () => {
  assert.equal(normalizar('La Serenísima'), 'la serenisima');
  // La ñ también se aplana a n. Es a propósito: mucha gente escribe "noqui"
  // o "banana con nuez" sin la tilde de la eñe, y como el texto buscado y el
  // catálogo pasan los dos por acá, el match sigue siendo simétrico.
  assert.equal(normalizar('Almíbar ÑOÑO'), 'almibar nono');
});

// --- rehidratado ----------------------------------------------------------

test('rehidratar reconstruye marcas, cadenas y ausencias', () => {
  const [primero, , , cuarto] = indice();
  assert.equal(primero.marca, 'Ades');
  assert.deepEqual(primero.cadenas, ['disco']);
  assert.equal(primero.tieneIngredientes, true);
  // marcaIdx -1 significa "no sabemos", no "índice 0".
  assert.equal(cuarto.marca, undefined);
  assert.equal(cuarto.categoria, undefined);
  assert.deepEqual(cuarto.cadenas, []);
});

test('el bitmask de cadenas guarda varias a la vez', () => {
  const alfajor = indice()[2];
  assert.deepEqual(alfajor.cadenas, ['disco', 'carrefour']);
});

test('rehidratar le vuelve a pegar el prefijo a la foto', () => {
  // El índice guarda solo el sufijo para no repetir 6.030 veces la misma URL
  // base. Si este test se rompe, la grilla de búsqueda vuelve a mostrar el
  // marco vacío en todos los productos: fue exactamente el bug de la v1.
  const [primero, segundo] = indice();
  assert.equal(
    primero.imagen,
    'https://images.openfoodfacts.org/images/products/779/000/000/1111/front_es.4.200.jpg',
  );
  // Sin foto es `undefined`, no la cadena vacía: la tarjeta pregunta por
  // `p.imagen` para decidir si dibuja el marco de reemplazo.
  assert.equal(segundo.imagen, undefined);
});

// --- búsqueda -------------------------------------------------------------

test('sin texto ordena por evidencia disponible, no por nombre', () => {
  // Antes esto era orden alfabético y la portada abria con las filas mas rotas
  // del catalogo: productos llamados «1» o «1001843», que son ruido de las
  // fuentes. Ahora manda `completitud` y el alfabeto solo desempata.
  const r = buscar(indice(), {
    texto: '',
    estados: TODOS,
    categoria: null,
    soloConfirmados: false,
    soloConIngredientes: false,
    soloAnmat: false,
  });
  assert.deepEqual(soloNombres(r), [
    'Leche de almendras', // 5: nombre, ingredientes, foto y cadena
    'Alfajor de chocolate', // 3: nombre, foto y cadenas
    'Dulce de leche vegano', // 3: nombre e ingredientes
    'Leche entera', // 3: idem; los tres empatan y ordena el alfabeto
    'Lechuga criolla', // 1: solo el nombre
    'Medallones de quinoa', // 1: idem
  ]);
});

test('completitud mide evidencia y es ciega al veredicto', () => {
  const [almendras, entera, alfajor, lechuga] = indice();

  assert.equal(completitud(almendras), 5);
  assert.equal(completitud(entera), 3);
  assert.equal(completitud(alfajor), 3);
  assert.equal(completitud(lechuga), 1);

  // Lo que se premia es tener con qué respaldar el dato, no que el dato sea
  // buena noticia: un «no apto» con foto y cadenas rankea igual que un
  // «vegetariano» con ingredientes. Si esto se rompe, la primera pantalla deja
  // de mostrar la distribución real de veredictos.
  assert.equal(alfajor.estado, 'no_apto');
  assert.equal(entera.estado, 'vegetariano');
  assert.equal(completitud(alfajor), completitud(entera));

  // Un nombre casi sin letras es un código que se coló como nombre.
  assert.equal(
    completitud({
      nombre: '1001843',
      tieneIngredientes: false,
      imagen: undefined,
      cadenas: [],
    }),
    0,
  );
});

test('busca por prefijo de palabra, no por subcadena', () => {
  const r = buscar(indice(), {
    texto: 'leche',
    estados: TODOS,
    categoria: null,
    soloConfirmados: false,
    soloConIngredientes: false,
    soloAnmat: false,
  });
  // "Lechuga" NO matchea "leche": el prefijo se compara contra la palabra
  // entera, si no buscar "leche" traería media verdulería.
  // Y entre los que sí matchean, primero los que EMPIEZAN con la palabra y
  // recién después el que solo la contiene; entre los dos primeros gana el
  // nombre más corto, porque quien escribe "leche" a secas casi siempre busca
  // la leche y no una variante larga.
  assert.deepEqual(soloNombres(r), [
    'Leche entera',
    'Leche de almendras',
    'Dulce de leche vegano',
  ]);
});

test('los tokens pueden estar salteados en el nombre', () => {
  const r = buscar(indice(), {
    texto: 'leche almen',
    estados: TODOS,
    categoria: null,
    soloConfirmados: false,
    soloConIngredientes: false,
    soloAnmat: false,
  });
  assert.deepEqual(soloNombres(r), ['Leche de almendras']);
});

test('encuentra por marca aunque no esté en el nombre', () => {
  const r = buscar(indice(), {
    texto: 'serenisima',
    estados: TODOS,
    categoria: null,
    soloConfirmados: false,
    soloConIngredientes: false,
    soloAnmat: false,
  });
  assert.deepEqual(soloNombres(r), ['Leche entera']);
});

test('la marca acentuada se encuentra sin acento', () => {
  const r = buscar(indice(), {
    texto: 'Serenísima',
    estados: TODOS,
    categoria: null,
    soloConfirmados: false,
    soloConIngredientes: false,
    soloAnmat: false,
  });
  assert.equal(r.length, 1);
});

test('el match en el nombre gana al match en la marca', () => {
  // "Leche entera" tiene "leche" en el nombre; ningún otro producto lo tiene
  // solo en la marca, así que se agrega uno al vuelo para comparar.
  const filas = indice();
  const conMarca = { ...filas[2], marca: 'Leche SA', _todo: filas[2]._nombre + ' leche sa' };
  const r = buscar([conMarca, filas[1]], {
    texto: 'leche',
    estados: TODOS,
    categoria: null,
    soloConfirmados: false,
    soloConIngredientes: false,
    soloAnmat: false,
  });
  assert.equal(r[0].nombre, 'Leche entera');
});

test('un código de barras es identidad: match exacto y sin filtros', () => {
  const r = buscar(indice(), {
    texto: '333',
    estados: new Set<Estado>(['apto']), // el alfajor es no_apto: igual aparece
    categoria: null,
    soloConfirmados: false,
    soloConIngredientes: false,
    soloAnmat: false,
  });
  // '333' tiene 3 dígitos, no llega al mínimo de 8: se busca como texto.
  assert.deepEqual(r, []);

  const conEan = rehidratar({
    v: 1,
    estados: ['apto', 'vegetariano', 'no_apto', 'revisar'],
    marcas: [],
    categorias: [],
    fuentes: ['ingredientes'],
    cadenas: [],
    p: [['7790040123456', 'x-7790040123456', 'Producto X', -1, -1, 2, 0, 0, 0, '']],
  });
  const r2 = buscar(conEan, {
    texto: '7790040123456',
    estados: new Set<Estado>(['apto']),
    categoria: null,
    soloConfirmados: false,
    soloConIngredientes: false,
    soloAnmat: false,
  });
  assert.equal(r2.length, 1);
});

test('los filtros se combinan y son excluyentes entre sí', () => {
  const filas = indice();
  const base = {
    texto: '',
    estados: TODOS,
    categoria: null,
    soloConfirmados: false,
    soloConIngredientes: false,
    soloAnmat: false,
  };

  assert.deepEqual(
    soloNombres(buscar(filas, { ...base, estados: new Set<Estado>(['apto']) })),
    ['Leche de almendras', 'Lechuga criolla', 'Medallones de quinoa'],
  );
  assert.deepEqual(
    soloNombres(buscar(filas, { ...base, categoria: 'Lácteos' })),
    ['Alfajor de chocolate', 'Leche entera'],
  );
  assert.deepEqual(
    soloNombres(buscar(filas, { ...base, soloConfirmados: true })),
    ['Leche de almendras', 'Alfajor de chocolate'],
  );
  assert.deepEqual(
    soloNombres(buscar(filas, { ...base, soloConIngredientes: true })),
    ['Leche de almendras', 'Dulce de leche vegano', 'Leche entera'],
  );
});

test('el filtro de ANMAT deja solo lo que está en el registro del Estado', () => {
  const filas = indice();
  const base = {
    texto: '',
    estados: TODOS,
    categoria: null,
    soloConfirmados: false,
    soloConIngredientes: false,
    soloAnmat: false,
  };

  const r = buscar(filas, { ...base, soloAnmat: true });
  assert.deepEqual(soloNombres(r), [
    'Dulce de leche vegano',
    'Medallones de quinoa',
  ]);
  for (const f of r) assert.equal(f.fuente, FUENTE_ANMAT);

  // No confundir con las otras dos capas de certificación: el sello del
  // supermercado y la etiqueta que declara el fabricante quedan afuera, igual
  // que la lectura de ingredientes y la heurística.
  assert.equal(
    filas.filter((f) => f.fuente !== FUENTE_ANMAT).length,
    filas.length - 2,
  );

  // Lo que no hace: filtrar por veredicto. El dulce de leche tiene el sello y
  // aun así está «a revisar» porque su lista de ingredientes lo contradice.
  // Si algún día este filtro se pusiera a mostrar solo los aptos, escondería
  // exactamente el producto sobre el que hay que desconfiar.
  const contradicho = r.find((f) => f.nombre === 'Dulce de leche vegano');
  assert.equal(contradicho?.estado, 'revisar');

  // Y se combina con los demás filtros en vez de reemplazarlos.
  assert.deepEqual(
    soloNombres(
      buscar(filas, {
        ...base,
        soloAnmat: true,
        estados: new Set<Estado>(['apto']),
      }),
    ),
    ['Medallones de quinoa'],
  );
});

test('una búsqueda sin resultados devuelve lista vacía, no todo', () => {
  const r = buscar(indice(), {
    texto: 'zzzz',
    estados: TODOS,
    categoria: null,
    soloConfirmados: false,
    soloConIngredientes: false,
    soloAnmat: false,
  });
  assert.deepEqual(r, []);
});

// --- ingrediente que disparó el veredicto --------------------------------

test('extrae el ingrediente de cada forma que escribe el pipeline', () => {
  const casos: [string, string | null][] = [
    ['Contiene leche: es vegetariano pero no vegano', 'leche'],
    ['Contiene gelatina, de origen animal', 'gelatina'],
    ['Contiene grasa animal, de origen animal', 'grasa animal'],
    ['Contiene carmín (cochinilla), de origen animal', 'carmín'],
    ['Contiene suero lácteo: es vegetariano pero no vegano', 'suero lácteo'],
    ['Contiene oleomargarina (grasa bovina u ovina, CAA art. 545), de origen animal', 'oleomargarina'],
  ];
  for (const [motivo, esperado] of casos) {
    assert.equal(ingredienteDisparador(motivo), esperado, motivo);
  }
});

test('no inventa un disparador cuando el motivo no nombra ninguno', () => {
  const nada = [
    undefined,
    'Ningún ingrediente de origen animal en los 12 declarados',
    'Certificado como vegano en la ficha del supermercado',
    'Sin datos suficientes para clasificar por nombre',
    '"cafe" es de origen vegetal o mineral',
    'Contiene ingredientes de origen animal',
  ];
  for (const motivo of nada) {
    assert.equal(ingredienteDisparador(motivo), null, String(motivo));
  }
});

// --- resaltado ------------------------------------------------------------

const resaltados = (texto: string, termino: string | null) =>
  partirResaltando(texto, termino)
    .filter((t) => t.resaltado)
    .map((t) => t.texto);

test('resalta el término respetando tildes y mayúsculas del original', () => {
  assert.deepEqual(
    resaltados('Agua, carmín, sal', 'carmín'),
    ['carmín'],
  );
  assert.deepEqual(
    resaltados('CONTIENE LECHE. Azúcar.', 'leche'),
    ['LECHE'],
  );
  // El término viene sin tilde pero el texto la tiene, y al revés.
  assert.deepEqual(resaltados('Suero lacteo en polvo', 'suero lácteo'), ['Suero lacteo']);
});

test('no resalta dentro de otra palabra', () => {
  assert.deepEqual(resaltados('Crema lechera y manteca', 'leche'), []);
  assert.deepEqual(resaltados('Alechuga', 'leche'), []);
});

test('resalta todas las apariciones y no pierde texto', () => {
  const texto = 'Leche en polvo, azúcar, suero de leche.';
  const trozos = partirResaltando(texto, 'leche');
  assert.equal(trozos.map((t) => t.texto).join(''), texto);
  assert.equal(trozos.filter((t) => t.resaltado).length, 2);
});

test('sin término no toca el texto', () => {
  const texto = 'Harina, sal, agua';
  assert.deepEqual(partirResaltando(texto, null), [
    { texto, resaltado: false },
  ]);
});

test('un término que no aparece deja el texto entero sin resaltar', () => {
  const texto = 'Harina, sal, agua';
  const trozos = partirResaltando(texto, 'gelatina');
  assert.deepEqual(trozos, [{ texto, resaltado: false }]);
});
