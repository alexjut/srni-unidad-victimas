/**
 * HMAC-SHA256 (RFC 2104) sobre el SHA-256 en JS puro que ya tiene la app.
 *
 * Hace falta para el cifrado del almacén local: cifrar sin autenticar deja el texto
 * cifrado modificable. Quien pueda escribir el archivo de la base —el escenario que
 * todo esto contempla— podría alterar bytes y la app descifraría basura sin notarlo.
 * Con el sello, un byte cambiado se detecta y el dato se rechaza.
 */
import { sha256Bytes } from './sha256';

const BLOQUE = 64; // SHA-256 procesa bloques de 64 bytes

function concat(a: Uint8Array, b: Uint8Array): Uint8Array {
  const out = new Uint8Array(a.length + b.length);
  out.set(a);
  out.set(b, a.length);
  return out;
}

/** HMAC-SHA256 → 32 bytes. */
export function hmacSha256(llave: Uint8Array, datos: Uint8Array): Uint8Array {
  // Una llave más larga que el bloque se reduce con la propia función hash;
  // una más corta se rellena con ceros (RFC 2104 §2).
  let k = llave.length > BLOQUE ? sha256Bytes(llave) : llave;
  if (k.length < BLOQUE) {
    const rellena = new Uint8Array(BLOQUE);
    rellena.set(k);
    k = rellena;
  }

  const ipad = new Uint8Array(BLOQUE);
  const opad = new Uint8Array(BLOQUE);
  for (let i = 0; i < BLOQUE; i++) {
    ipad[i] = k[i] ^ 0x36;
    opad[i] = k[i] ^ 0x5c;
  }

  return sha256Bytes(concat(opad, sha256Bytes(concat(ipad, datos))));
}

/**
 * Compara dos sellos sin delatar en cuál byte difieren.
 *
 * Un `===` corta en la primera diferencia, y ese tiempo distinto es lo que permite
 * ir adivinando el sello byte por byte. Acá siempre se recorren los 32.
 */
export function igualesEnTiempoConstante(a: Uint8Array, b: Uint8Array): boolean {
  if (a.length !== b.length) return false;
  let diferencia = 0;
  for (let i = 0; i < a.length; i++) diferencia |= a[i] ^ b[i];
  return diferencia === 0;
}
