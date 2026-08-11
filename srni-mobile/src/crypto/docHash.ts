/**
 * Los DOS hashes de documento del padrón descargable, replicados exactamente
 * como los calcula el backend.
 *
 * ── Son dos, y confundirlos hace que nada coincida ───────────────────────────
 *
 *     tabla `padron`         →  docHash(tipo, numero)  = sha256("cc|1234")
 *     tabla `universo_bloom` →  numHash(numero)        = sha256("1234")
 *
 * El filtro del universo va SIN tipo a propósito: `PersonaUniverso.tipo_documento`
 * llega sin homologar desde la fuente y hay 1,13 M de personas a las que nadie
 * les registró el tipo. Consultar el Bloom con `docHash` no devuelve "algunos
 * fallos": no encuentra absolutamente nada, y sin error — simplemente responde
 * que la persona no está en el RUV.
 *
 * ── La normalización es un contrato, no una preferencia ──────────────────────
 * Cada paso de aquí abajo tiene su gemelo en `normalizar_doc`
 * (srni-backend/apps/victimas/repository/base.py). Si uno de los dos cambia sin
 * el otro, el padrón deja de encontrar a nadie y NO hay excepción que lo avise.
 * El test `docHash.test.ts` fija los valores contra los que produce Python.
 *
 * ⚠️ NO confundir con `db/hashDocumento.ts`, que sigue siendo el índice interno
 * del almacén local (FNV-1a + djb2, 16 chars). Aquel indexa lo que la APK guarda;
 * este lee lo que el backend escribió. Conviven a propósito.
 */
import { sha256Hex } from './sha256';

/**
 * Quita diacríticos: 'á' → 'a'.
 *
 * Réplica de `unicodedata.normalize('NFKD', s)` seguido de descartar los
 * combinantes. `String.prototype.normalize` existe en Hermes; el rango
 * U+0300–U+036F es el bloque de marcas combinantes, que es justo lo que NFKD
 * separa de la letra base.
 */
function quitarDiacriticos(s: string): string {
  if (typeof (s as any).normalize === 'function') {
    return s.normalize('NFKD').replace(/[̀-ͯ]/g, '');
  }
  return s;
}

/**
 * Una parte del documento, canonizada. El ORDEN importa y es el del backend:
 * recortar extremos → quitar separadores → minúsculas → quitar diacríticos.
 *
 * Ojo con el paso 2: el backend elimina espacios, puntos y guiones **en toda la
 * cadena**, no solo en los extremos (`s.replace(ch, '')` sobre todo el texto).
 */
function limpiarParte(parte: string): string {
  let s = (parte || '').trim();
  s = s.split(' ').join('').split('.').join('').split('-').join('');
  s = s.toLowerCase();
  return quitarDiacriticos(s);
}

/** La cadena canónica `'<tipo>|<numero>'`, lista para hashear. */
export function normalizarDoc(tipoDocumento: string, numeroDocumento: string): string {
  return `${limpiarParte(tipoDocumento)}|${limpiarParte(numeroDocumento)}`;
}

/**
 * Hash de IDENTIDAD. Es la llave de la tabla `padron` del archivo descargable.
 *
 * En el archivo se guarda en BINARIO truncado a 16 bytes, no en hex: para
 * consultarlo hay que pasar por `claveDocumento`.
 */
export function docHash(tipoDocumento: string, numeroDocumento: string): string {
  return sha256Hex(normalizarDoc(tipoDocumento, numeroDocumento));
}

/**
 * Hash de RESPALDO: solo el NÚMERO, sin el tipo. Es con el que se consulta el
 * filtro de Bloom del universo.
 *
 * Réplica de `num_hash`, que normaliza con tipo vacío y se queda con la parte
 * derecha del '|' — de ahí que el resultado sea el sha256 del número pelado.
 */
export function numHash(numeroDocumento: string): string {
  return sha256Hex(limpiarParte(numeroDocumento));
}

/** Cuántos bytes del SHA-256 guarda el archivo. Es `HASH_BYTES` del backend. */
export const HASH_BYTES = 16;

/**
 * La llave binaria de la tabla `padron`: los primeros 16 bytes del `docHash`.
 *
 * 128 bits sobran para comparar por igualdad —con 5 millones de claves la
 * probabilidad de choque ronda 10⁻²⁶—, y en hexadecimal costaban 64 bytes por
 * fila más otros tantos en el índice.
 */
export function claveDocumento(tipoDocumento: string, numeroDocumento: string): Uint8Array {
  const hex = docHash(tipoDocumento, numeroDocumento);
  const out = new Uint8Array(HASH_BYTES);
  for (let i = 0; i < HASH_BYTES; i++) {
    out[i] = parseInt(hex.substr(i * 2, 2), 16);
  }
  return out;
}
