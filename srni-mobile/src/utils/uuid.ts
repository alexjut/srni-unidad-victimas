/**
 * Genera un UUID v4 compatible con Hermes (motor JS de React Native).
 *
 * Hermes NO incluye Web Crypto API por defecto — `crypto.getRandomValues`
 * lanza `ReferenceError: Property 'crypto' doesn't exist`. Por eso usamos
 * un fallback con Math.random.
 *
 * Aclaración de seguridad: estos UUIDs identifican BORRADORES LOCALES en
 * SQLite y items de cola de sincronización. No son tokens de autenticación
 * ni se exponen al servidor para tomar decisiones de seguridad. Math.random
 * tiene calidad suficiente para evitar colisiones en escala humana
 * (probabilidad < 2^-60 de colisión por dispositivo en la vida del contrato).
 *
 * Si en el futuro se requiere calidad criptográfica, instalar el polyfill
 * react-native-get-random-values e importarlo en app/_layout.tsx para activar
 * globalThis.crypto.
 */
function getRandomBytes(size: number): Uint8Array {
  const bytes = new Uint8Array(size);

  // 1) Crypto del navegador / Web (en panel web y entornos modernos)
  const g: any = globalThis as any;
  if (g.crypto?.getRandomValues) {
    g.crypto.getRandomValues(bytes);
    return bytes;
  }

  // 2) Fallback Math.random para Hermes (motor JS de React Native)
  for (let i = 0; i < size; i++) {
    bytes[i] = Math.floor(Math.random() * 256);
  }
  return bytes;
}

export function uuidv4(): string {
  const bytes = getRandomBytes(16);

  // Ajustar versión (4) y variante (RFC 4122)
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;

  const hex = Array.from(bytes).map((b) => b.toString(16).padStart(2, '0'));
  return [
    hex.slice(0, 4).join(''),
    hex.slice(4, 6).join(''),
    hex.slice(6, 8).join(''),
    hex.slice(8, 10).join(''),
    hex.slice(10, 16).join(''),
  ].join('-');
}
