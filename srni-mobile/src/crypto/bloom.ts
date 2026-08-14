/**
 * Consulta del filtro de Bloom del universo de víctimas.
 *
 * ── Qué contesta ────────────────────────────────────────────────────────────
 * "¿Esta persona está en el universo del RUV?" — sí/no, sin llevar sus datos.
 *
 * El padrón descargable trae a quien tiene ficha (4,55 M documentos). El
 * universo son 12,68 M, y las 8,12 M que solo están ahí no cabían: con nombre y
 * datos costaban ~190 MB. El filtro responde lo único que hace falta para
 * habilitar un alta manual en campo, en 21,7 MiB. El nombre se lo pregunta el
 * encuestador a la persona, que está enfrente.
 *
 * ── El precio, que la UI debe sostener ──────────────────────────────────────
 * NUNCA hay falsos negativos: si la persona es víctima, el filtro la reconoce
 * siempre. Pero ~1 de cada 1.000 consultas sobre alguien ajeno al universo
 * responde que sí. Por eso un acierto es un **candidato a alta manual**, a
 * confirmar cuando vuelva la señal — igual que `clase_colision = 'AMBIGUO'`.
 * Nunca una identificación.
 *
 * ── ⚠️ Se consulta con `numHash`, NO con `docHash` ──────────────────────────
 * El filtro se construyó con el SHA-256 del NÚMERO SIN TIPO. Consultarlo con el
 * hash de identidad no encuentra nada, y falla en silencio.
 *
 * ── La derivación tiene que ser idéntica a la de Python ─────────────────────
 * Doble hashing de Kirsch-Mitzenmacher. El gemelo vive en
 * `srni-backend/apps/victimas/bloom.py`, y `test_bloom.py::test_vector_fijo_de_indices`
 * es el vector compartido: si los dos lados se separan, el filtro no falla,
 * responde basura.
 */
import { hexABytes } from './sha256';

/** Formato del filtro que esta implementación sabe leer. Viaja en el manifiesto. */
export const BLOOM_FORMATO_SOPORTADO = 1;

export interface ParametrosBloom {
  /** Versión del formato. Si no es la soportada, NO consultar el filtro. */
  formato: number;
  /** Bits del filtro. */
  m: number;
  /** Funciones hash. */
  k: number;
  /** Documentos que se agregaron. Informativo. */
  n: number;
  /** Tasa de falsos positivos MEDIDA sobre el filtro construido. */
  falsos_positivos: number;
}

/**
 * Los k índices de bit de un hash. Réplica exacta de `_indices` en Python.
 *
 * `h2` se fuerza IMPAR (`| 1`): si `h2` y `m` comparten factores, la progresión
 * `h1 + i*h2` recorre solo una parte del filtro y los falsos positivos reales se
 * disparan por encima de lo declarado.
 *
 * Los dos enteros se leen big-endian, como `int.from_bytes(..., 'big')`.
 *
 * Cuidado con la aritmética: `h1` y `h2` son de 32 bits sin signo, así que
 * `h1 + i*h2` con k=10 llega a ~4,3e10 — por encima de los 2^32 de los enteros
 * de JS, pero muy por debajo de los 2^53 que `Number` representa exacto. Por eso
 * se opera con `Number` normal y NO con operadores de bits (`|`, `>>>`), que
 * truncarían a 32 bits y darían otros índices que los de Python.
 */
function indices(sha: Uint8Array, m: number, k: number): number[] {
  const h1 =
    ((sha[0] << 24) | (sha[1] << 16) | (sha[2] << 8) | sha[3]) >>> 0;

  // ⚠️ El `>>> 0` va DESPUÉS del `| 1`, y el orden no es cosmético.
  //
  // `| 1` es un operador de bits: convierte su operando a int32 CON SIGNO. Si se
  // escribe `(... >>> 0) | 1`, el `>>> 0` produce el uint32 correcto y el `| 1`
  // lo devuelve a int32 — con lo que todo hash cuyo byte 4 tenga el bit alto
  // encendido (la mitad de ellos) sale NEGATIVO.
  //
  // Medido: el documento 28683981 daba h2 = -1270920853 e índices
  // [4908, 7319, -6654, -4243, -1832]. Un índice negativo lee fuera del arreglo,
  // `bits[-832]` es `undefined`, y `undefined & 1` es 0: el filtro responde "no
  // está en el universo" — el falso negativo que este diseño promete que NUNCA
  // ocurre, en silencio y para media población.
  //
  // En Python no aparece porque sus enteros no tienen ancho fijo.
  const h2 =
    ((((sha[4] << 24) | (sha[5] << 16) | (sha[6] << 8) | sha[7]) | 1) >>> 0);

  const out: number[] = new Array(k);
  for (let i = 0; i < k; i++) {
    out[i] = (h1 + i * h2) % m;
  }
  return out;
}

/**
 * Los k índices de un hash — expuesto para poder CONSTRUIR un filtro en los
 * tests con la misma fórmula que lo consulta.
 *
 * Existe por una razón concreta: mientras esta derivación estaba duplicada entre
 * el módulo y el test, el bug del signo apareció en los dos lados a la vez y el
 * test no podía delatarlo. Una sola definición, usada por ambos.
 */
export function indicesDe(hashHex: string, m: number, k: number): number[] {
  return indices(hexABytes(hashHex), m, k);
}

/**
 * ¿El filtro reconoce este hash?
 *
 * `false` es DEFINITIVO: la persona no está en el universo.
 * `true` es "probablemente" — ver la tasa de falsos positivos del manifiesto.
 *
 * @param bits  el blob del filtro, tal como viene de `universo_bloom.bits`
 * @param hashHex  salida de `numHash(numero)` — SIN tipo de documento
 */
export function contiene(
  bits: Uint8Array,
  m: number,
  k: number,
  hashHex: string,
): boolean {
  return contieneCon((i) => bits[i] ?? 0, m, k, hashHex);
}

/**
 * Igual que `contiene`, pero pidiendo los bytes de uno en uno.
 *
 * Existe porque en el dispositivo el filtro son 22,7 MB en un archivo, y traerlo
 * entero a memoria en cada búsqueda sería absurdo cuando solo se necesitan k
 * bytes sueltos —con k=10, diez—. El lector va al archivo por `offset`.
 *
 * `leerByte` DEBE devolver 0 para posiciones fuera de rango, nunca `undefined`:
 * `undefined & 1` es 0 y el filtro respondería "no está" en silencio, que es
 * justo el falso negativo que este diseño promete que no ocurre.
 */
export function contieneCon(
  leerByte: (indice: number) => number,
  m: number,
  k: number,
  hashHex: string,
): boolean {
  const idx = indices(hexABytes(hashHex), m, k);
  for (let i = 0; i < idx.length; i++) {
    const bit = idx[i];
    if ((leerByte(bit >> 3) & (1 << (bit & 7))) === 0) {
      return false;
    }
  }
  return true;
}

/**
 * Verifica que un filtro sea consultable ANTES de usarlo.
 *
 * Un Bloom mal leído no lanza excepciones: devuelve respuestas plausibles y
 * equivocadas. Estas tres comprobaciones son la única defensa — que el formato
 * sea el que esta versión entiende, y que el blob tenga exactamente el tamaño
 * que `m` declara. Un blob más corto haría que `bits[bit >> 3]` devuelva
 * `undefined`, y `undefined & 1` es 0: el filtro respondería "no está" para
 * todo el mundo, en silencio.
 */
export function esUsable(
  bits: Uint8Array | null | undefined,
  params: ParametrosBloom | null | undefined,
): boolean {
  if (!bits || !params) return false;
  if (params.formato !== BLOOM_FORMATO_SOPORTADO) return false;
  if (!params.m || !params.k) return false;
  return bits.length === Math.floor(params.m / 8);
}
