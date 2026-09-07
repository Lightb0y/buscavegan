import Link from 'next/link';

export default function NoEncontrado() {
  return (
    <div className="contenedor">
      <div className="vacio">
        <h1>No encontramos esa página</h1>
        <p>
          El producto puede haber cambiado de nombre, o el link puede estar
          incompleto.
        </p>
        <p>
          <Link href="/">Volver al buscador</Link>
        </p>
      </div>
    </div>
  );
}
