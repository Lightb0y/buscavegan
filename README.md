# buscavegan

Buscador de productos **aptos veganos** que se venden en supermercados argentinos,
con transparencia sobre **cómo se determinó** cada clasificación.

Cruza dos fuentes:

- **SEPA / Precios Claros** — qué productos existen en Argentina (EAN, nombre, marca, precio).
- **Open Food Facts (OFF)** — análisis de ingredientes por código de barras.

La especificación completa está en [SPEC.md](SPEC.md).

## Qué significa "apto" acá

**"Apto" = vegano**: sin ingredientes ni derivados de origen animal, según el análisis de
ingredientes de Open Food Facts o la declaración del fabricante.

**No** significa *cruelty-free* en sentido estricto. "Cruelty-free" (no testeado en animales)
es un atributo de cosmética y **no está presente en ninguna de las fuentes de datos de
alimentos que usa este proyecto**. Si un producto aparece como `apto` acá, eso dice algo
sobre sus ingredientes, no sobre la política de testeo del fabricante.

## Estados

| Estado | Significado |
|---|---|
| `apto` | Vegano según OFF, el fabricante o las reglas |
| `vegetariano` | Sin carne, pero con derivados animales (lácteos, huevo, miel) |
| `no_apto` | Contiene ingredientes de origen animal |
| `revisar` | **Sin datos suficientes.** No es "no apto": es "no sabemos" |

**Regla de seguridad:** ante cualquier ambigüedad se asigna `revisar`, nunca `apto`.
Un falso positivo (marcar vegano algo que no lo es) es mucho más grave que un falso negativo.

## Limitaciones conocidas

- **Cobertura de OFF en Argentina es baja.** El cruce por EAN matchea solo una fracción del
  catálogo SEPA; el resto se resuelve por heurística de nombre o queda en `revisar`.
  El match rate real se mide con `sprint0.py` (ver abajo) y se documenta en cada corrida.
- La heurística de nombre trabaja sobre el nombre comercial, que suele ser incompleto.
  No reemplaza leer la etiqueta.
- SEPA no publica ingredientes ni tabla nutricional: todo eso viene de OFF.
- El portal oficial de SEPA bloquea acceso automatizado. La descarga es manual o vía mirror
  (ver [SPEC.md](SPEC.md) §2.1); el pipeline consume un CSV ya bajado.

## Uso

```bash
pip install -r requirements.txt

# Sprint 0: medir el match rate de OFF sobre una muestra antes de construir todo
python ingest_sepa.py --csv data/raw/sepa.csv
python sprint0.py --sample 500
```

## Frecuencia de refresco

El catálogo SEPA se re-descarga en cada corrida; las respuestas de OFF se cachean en SQLite
con un TTL de 60 días por defecto (`OFF_CACHE_TTL_DAYS`), de modo que los refrescos
posteriores solo consultan la API por productos nuevos o vencidos. Todo se configura en
[config.py](config.py) o por variables de entorno.

## Estado del proyecto

En desarrollo. Ver el checklist de calidad en [SPEC.md](SPEC.md) §9.
