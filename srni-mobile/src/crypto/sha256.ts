/**
 * SHA-256 en JavaScript puro.
 *
 * ── Por qué existe este archivo ──────────────────────────────────────────────
 * El padrón descargable del backend está indexado por SHA-256 (`doc_hash`), y el
 * filtro de Bloom del universo se consulta con SHA-256 (`num_hash`). El hash que
 * la APK usaba hasta ahora —FNV-1a + djb2, en `db/hashDocumento.ts`— es otro
 * algoritmo, con otra entrada y hasta otra longitud: 16 caracteres contra 64.
 * No hay forma de que coincidan.
 *
 * Eso hoy no rompe nada porque el backend manda el documento EN CLARO en la
 * precarga y la APK hashea de su lado, tanto al escribir como al leer: es
 * autoconsistente dentro del dispositivo. Deja de serlo en el momento en que la
 * APK abre el archivo `padron-<version>.sqlite3`, cuya llave la calculó Python.
 *
 * ── Por qué en JS puro y no con expo-crypto ──────────────────────────────────
 * `expo-crypto` no está instalado (0 menciones en package-lock.json) y añadirlo
 * es un módulo nativo: build EAS nueva y QA de por medio. Esto son ~90 líneas
 * sin dependencias, que corren igual en Hermes hoy mismo.
 *
 * El costo no importa: son DOS hashes por búsqueda —uno para la tabla `padron`,
 * otro para el Bloom—, no un bucle sobre millones. Lo que sí importa es que el
 * resultado sea idéntico al de Python, y eso lo fija el test contra los vectores
 * oficiales de NIST más el vector compartido con `test_bloom.py`.
 *
 * ⚠️ Esto NO reemplaza el cifrado en reposo. Sigue siendo un hash sin sal sobre
 * un dominio de ~10^10 cédulas: recorrerlo por fuerza bruta es cuestión de
 * segundos. Ver TODO(cifrado-en-reposo) en `db/schema.ts`.
 */

/** Constantes de SHA-256: primeros 32 bits de la parte fraccionaria de las
 *  raíces cúbicas de los 64 primeros números primos (FIPS 180-4, §4.2.2). */
const K = new Uint32Array([
  0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1,
  0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
  0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786,
  0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
  0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147,
  0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
  0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b,
  0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
  0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a,
  0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
  0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
]);

/** Rotación a la derecha de 32 bits. `>>> 0` mantiene el resultado sin signo. */
function rotr(x: number, n: number): number {
  return ((x >>> n) | (x << (32 - n))) >>> 0;
}

/**
 * Texto → bytes UTF-8.
 *
 * Importa más de lo que parece: Python hashea `canon.encode('utf-8')`, o sea
 * BYTES, mientras que el hash viejo del móvil recorría unidades de código UTF-16
 * con `charCodeAt`. Coinciden mientras todo sea ASCII y divergen en cuanto
 * aparece una tilde. Un documento es casi siempre numérico, pero "casi siempre"
 * no es un contrato: acá se fija en bytes UTF-8 y se acabó la ambigüedad.
 *
 * No se usa `TextEncoder` porque su presencia en Hermes depende de la versión
 * del runtime, y este archivo no puede depender de eso.
 */
export function utf8Bytes(texto: string): Uint8Array {
  const out: number[] = [];
  for (let i = 0; i < texto.length; i++) {
    let cp = texto.charCodeAt(i);

    // Par suplente (emoji, caracteres fuera del BMP) → un solo code point.
    if (cp >= 0xd800 && cp <= 0xdbff && i + 1 < texto.length) {
      const bajo = texto.charCodeAt(i + 1);
      if (bajo >= 0xdc00 && bajo <= 0xdfff) {
        cp = (cp - 0xd800) * 0x400 + (bajo - 0xdc00) + 0x10000;
        i++;
      }
    }

    if (cp < 0x80) {
      out.push(cp);
    } else if (cp < 0x800) {
      out.push(0xc0 | (cp >> 6), 0x80 | (cp & 0x3f));
    } else if (cp < 0x10000) {
      out.push(0xe0 | (cp >> 12), 0x80 | ((cp >> 6) & 0x3f), 0x80 | (cp & 0x3f));
    } else {
      out.push(
        0xf0 | (cp >> 18),
        0x80 | ((cp >> 12) & 0x3f),
        0x80 | ((cp >> 6) & 0x3f),
        0x80 | (cp & 0x3f),
      );
    }
  }
  return new Uint8Array(out);
}

/** SHA-256 de un arreglo de bytes → 32 bytes. Implementa FIPS 180-4 §6.2. */
export function sha256Bytes(datos: Uint8Array): Uint8Array {
  // Valores iniciales: parte fraccionaria de las raíces cuadradas de los 8
  // primeros primos (FIPS 180-4, §5.3.3).
  let h0 = 0x6a09e667, h1 = 0xbb67ae85, h2 = 0x3c6ef372, h3 = 0xa54ff53a;
  let h4 = 0x510e527f, h5 = 0x9b05688c, h6 = 0x1f83d9ab, h7 = 0x5be0cd19;

  // Relleno: byte 0x80, ceros, y la longitud en BITS como entero de 64 bits
  // big-endian. El bloque debe quedar múltiplo de 64 bytes.
  const largoBits = datos.length * 8;
  const conRelleno = new Uint8Array(((datos.length + 9 + 63) >> 6) << 6);
  conRelleno.set(datos);
  conRelleno[datos.length] = 0x80;

  // Los 4 bytes altos de la longitud: un documento jamás llega a 2^32 bits, pero
  // escribirlos evita que esta función quede mal para cualquier otro uso.
  const alto = Math.floor(largoBits / 0x100000000);
  const bajo = largoBits >>> 0;
  const finLargo = conRelleno.length;
  conRelleno[finLargo - 8] = (alto >>> 24) & 0xff;
  conRelleno[finLargo - 7] = (alto >>> 16) & 0xff;
  conRelleno[finLargo - 6] = (alto >>> 8) & 0xff;
  conRelleno[finLargo - 5] = alto & 0xff;
  conRelleno[finLargo - 4] = (bajo >>> 24) & 0xff;
  conRelleno[finLargo - 3] = (bajo >>> 16) & 0xff;
  conRelleno[finLargo - 2] = (bajo >>> 8) & 0xff;
  conRelleno[finLargo - 1] = bajo & 0xff;

  const w = new Uint32Array(64);

  for (let bloque = 0; bloque < conRelleno.length; bloque += 64) {
    for (let i = 0; i < 16; i++) {
      const o = bloque + i * 4;
      w[i] =
        ((conRelleno[o] << 24) |
          (conRelleno[o + 1] << 16) |
          (conRelleno[o + 2] << 8) |
          conRelleno[o + 3]) >>> 0;
    }
    for (let i = 16; i < 64; i++) {
      const s0 = (rotr(w[i - 15], 7) ^ rotr(w[i - 15], 18) ^ (w[i - 15] >>> 3)) >>> 0;
      const s1 = (rotr(w[i - 2], 17) ^ rotr(w[i - 2], 19) ^ (w[i - 2] >>> 10)) >>> 0;
      w[i] = (w[i - 16] + s0 + w[i - 7] + s1) >>> 0;
    }

    let a = h0, b = h1, c = h2, d = h3, e = h4, f = h5, g = h6, h = h7;

    for (let i = 0; i < 64; i++) {
      const S1 = (rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25)) >>> 0;
      const ch = ((e & f) ^ (~e & g)) >>> 0;
      const temp1 = (h + S1 + ch + K[i] + w[i]) >>> 0;
      const S0 = (rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22)) >>> 0;
      const maj = ((a & b) ^ (a & c) ^ (b & c)) >>> 0;
      const temp2 = (S0 + maj) >>> 0;

      h = g; g = f; f = e;
      e = (d + temp1) >>> 0;
      d = c; c = b; b = a;
      a = (temp1 + temp2) >>> 0;
    }

    h0 = (h0 + a) >>> 0; h1 = (h1 + b) >>> 0;
    h2 = (h2 + c) >>> 0; h3 = (h3 + d) >>> 0;
    h4 = (h4 + e) >>> 0; h5 = (h5 + f) >>> 0;
    h6 = (h6 + g) >>> 0; h7 = (h7 + h) >>> 0;
  }

  const salida = new Uint8Array(32);
  [h0, h1, h2, h3, h4, h5, h6, h7].forEach((valor, i) => {
    salida[i * 4] = (valor >>> 24) & 0xff;
    salida[i * 4 + 1] = (valor >>> 16) & 0xff;
    salida[i * 4 + 2] = (valor >>> 8) & 0xff;
    salida[i * 4 + 3] = valor & 0xff;
  });
  return salida;
}

/** SHA-256 de un texto → 64 caracteres hex en MINÚSCULAS, como `hexdigest()`. */
export function sha256Hex(texto: string): string {
  return bytesAHex(sha256Bytes(utf8Bytes(texto)));
}

/** Bytes → hex en minúsculas. */
export function bytesAHex(bytes: Uint8Array): string {
  let hex = '';
  for (let i = 0; i < bytes.length; i++) {
    hex += bytes[i].toString(16).padStart(2, '0');
  }
  return hex;
}

/** Hex → bytes. Acepta mayúsculas o minúsculas. */
export function hexABytes(hex: string): Uint8Array {
  const out = new Uint8Array(hex.length >> 1);
  for (let i = 0; i < out.length; i++) {
    out[i] = parseInt(hex.substr(i * 2, 2), 16);
  }
  return out;
}
