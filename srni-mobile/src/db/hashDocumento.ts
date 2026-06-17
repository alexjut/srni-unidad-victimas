/**
 * Hash de documento para el almacén OFFLINE (Fase 0).
 *
 * El padrón NO guarda el número de documento en claro: se busca por su hash.
 * Esto evita exponer el listado completo de cédulas si el .db se filtra.
 *
 * Decisión Fase 0: expo-crypto NO está instalado en el proyecto y su API
 * SHA256 es asíncrona (digestStringAsync). Para mantener la búsqueda
 * SÍNCRONA y sin dependencias nativas nuevas, se usa un hash determinista
 * propio (FNV-1a de 64 bits combinado con djb2) — no es criptográfico, pero
 * para Fase 0 con datos MOCK (no PII real) basta como ofuscación no reversible.
 *
 * TODO(cifrado-fuerte): en una fase con PII real, reemplazar por SHA-256 con
 * sal por dispositivo guardada en expo-secure-store. La firma de `hashDocumento`
 * se mantiene estable para que el resto del código no cambie. Si se vuelve
 * asíncrona, los DAOs ya son async y se adaptan sin tocar las pantallas.
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
 * Hash determinista no reversible del documento. Combina FNV-1a y djb2 para
 * reducir colisiones y devuelve hex de 16 chars.
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
