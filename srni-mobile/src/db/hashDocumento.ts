/**
 * Hash de documento para INDEXACIÓN local en el almacén OFFLINE (Fase 0).
 *
 * El padrón se busca por el hash del documento en lugar del número en claro,
 * para usarlo como clave de índice estable y no volcar las cédulas literales
 * en las consultas.
 *
 * ATENCIÓN — NO es un mecanismo de seguridad. Es un hash NO criptográfico
 * (FNV-1a + djb2, 64 bits, SIN sal). Es REVERSIBLE por fuerza bruta: el dominio
 * de las cédulas (~10^10) se recorre en segundos, así que NO protege la PII si
 * el .db se filtra. Por eso Fase 0 trabaja con datos MOCK (no PII real).
 *
 * Decisión Fase 0: expo-crypto NO está instalado y su API SHA256 es asíncrona
 * (digestStringAsync). Para mantener la búsqueda SÍNCRONA y sin dependencias
 * nativas nuevas, se usa este hash determinista propio solo como índice local.
 *
 * TODO(cifrado-en-reposo): el cifrado en reposo real está PENDIENTE para la fase
 * con PII real. Reemplazar por SHA-256 con sal por dispositivo (guardada en
 * expo-secure-store) y alinear con el padrón SHA-256 del backend, además de
 * SQLCipher para la base. Implica re-precarga del padrón (Fase B). La firma de
 * `hashDocumento` se mantiene estable para que el resto del código no cambie;
 * si se vuelve asíncrona, los DAOs ya son async y se adaptan sin tocar pantallas.
 */

/**
 * Normaliza el documento antes de hashear: quita espacios, puntos y guiones,
 * pasa a mayúsculas. Garantiza que "12.345.678" y "12345678" colisionen igual
 * que el documento tecleado en la búsqueda.
 */
export function normalizarDocumento(documento: string): string {
  return documento.replace(/[\s.\-]/g, '').toUpperCase();
}

/**
 * Hash determinista de INDEXACIÓN del documento (NO de seguridad). Combina
 * FNV-1a y djb2 para reducir colisiones y devuelve hex de 16 chars. Reversible
 * por fuerza bruta: no usar como protección de PII (ver cabecera del archivo).
 */
export function hashDocumento(documento: string): string {
  const s = normalizarDocumento(documento);

  // FNV-1a 32-bit
  let fnv = 0x811c9dc5;
  for (let i = 0; i < s.length; i++) {
    fnv ^= s.charCodeAt(i);
    fnv = Math.imul(fnv, 0x01000193);
  }

  // djb2
  let djb = 5381;
  for (let i = 0; i < s.length; i++) {
    djb = (Math.imul(djb, 33) + s.charCodeAt(i)) | 0;
  }

  const h1 = (fnv >>> 0).toString(16).padStart(8, '0');
  const h2 = (djb >>> 0).toString(16).padStart(8, '0');
  return h1 + h2;
}

/** Display no sensible: últimos 4 caracteres del documento normalizado. */
export function displayDocumento(documento: string): string {
  const s = normalizarDocumento(documento);
  return s.length <= 4 ? s : s.slice(-4);
}
