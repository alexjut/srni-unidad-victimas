/**
 * Cifrado en reposo de los datos personales que quedan en el teléfono.
 *
 * ── Qué protege ─────────────────────────────────────────────────────────────
 * Mientras la cola está pendiente, el dispositivo guarda en SQLite el nombre y el
 * documento de personas reales: las altas manuales (`victimas_offline`), los
 * integrantes capturados sin señal (`miembros_offline`) y las personas de la
 * jornada. Estaban en claro. Un teléfono perdido, prestado o revisado los entrega
 * enteros, y son datos de víctimas del conflicto.
 *
 * Lo pidió también la OTI en su concepto del 17-sep-2026, y ya estaba reconocido
 * como pendiente en `docs/mobile/offline-cifrado-en-reposo.md`.
 *
 * ── Por qué así y no con SQLCipher ──────────────────────────────────────────
 * Cifrar el archivo completo exige cambiar el motor de base de datos por
 * `op-sqlite` y rehacer TODO `src/db/`: borradores, cola, sincronización. Es el
 * camino correcto a futuro y está documentado, pero cambiar el motor que sostiene
 * la captura de campo, en la misma semana de las jornadas, es arriesgar lo que
 * funciona por lo que falta.
 *
 * Esto cifra las columnas que llevan datos personales y deja intacto el motor. La
 * diferencia real es acotada: el resto del esquema son identificadores opacos,
 * respuestas por código de pregunta y datos de vivienda.
 *
 * ── Cómo ────────────────────────────────────────────────────────────────────
 * AES-256 en modo contador, y después un sello HMAC-SHA256 sobre lo cifrado
 * (cifrar-y-luego-sellar). Sin el sello, quien pueda escribir el archivo altera
 * bytes y la app descifra basura sin enterarse.
 *
 * La llave son 32 bytes aleatorios que se crean la primera vez y viven en el
 * almacén seguro del sistema (Keystore en Android), no en la base. Así, copiar el
 * archivo de la base a otro equipo no alcanza para leerlo.
 *
 * ── Compatibilidad ──────────────────────────────────────────────────────────
 * Lo guardado ANTES de esta versión está en claro y se sigue leyendo: `descifrar`
 * devuelve tal cual lo que no lleva la marca `c1:`. Reescribir esas filas al
 * vuelo obligaría a una migración con la base a medio camino; se vuelven a
 * escribir cifradas la próxima vez que se toquen, y desaparecen al sincronizar.
 */
import * as SecureStore from 'expo-secure-store';
import * as Crypto from 'expo-crypto';
import aesjs from 'aes-js';

import { hmacSha256, igualesEnTiempoConstante } from './hmac';
import { sha256Bytes, utf8Bytes } from './sha256';

/** Dónde vive la llave. El `v1` permite rotarla sin adivinar qué hay guardado. */
const CLAVE_ALMACEN = 'cofre_local_v1';

/** Marca de formato. Lo que no la lleva es texto viejo, en claro. */
const MARCA = 'c1:';

const LARGO_IV = 16;
const LARGO_SELLO = 32;

let _llaveEnMemoria: Uint8Array | null = null;

// ── Base64 sin dependencias ──────────────────────────────────────────────────
// Hermes no trae `btoa`/`atob`, y sumar una librería por esto sería exagerado.
const B64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';

export function aBase64(bytes: Uint8Array): string {
  let salida = '';
  for (let i = 0; i < bytes.length; i += 3) {
    const a = bytes[i];
    const b = i + 1 < bytes.length ? bytes[i + 1] : 0;
    const c = i + 2 < bytes.length ? bytes[i + 2] : 0;
    salida += B64[a >> 2];
    salida += B64[((a & 3) << 4) | (b >> 4)];
    salida += i + 1 < bytes.length ? B64[((b & 15) << 2) | (c >> 6)] : '=';
    salida += i + 2 < bytes.length ? B64[c & 63] : '=';
  }
  return salida;
}

export function desdeBase64(texto: string): Uint8Array {
  const limpio = texto.replace(/=+$/, '');
  const out = new Uint8Array(Math.floor((limpio.length * 6) / 8));
  let acumulado = 0;
  let bits = 0;
  let pos = 0;
  for (const caracter of limpio) {
    const valor = B64.indexOf(caracter);
    if (valor < 0) continue;
    acumulado = (acumulado << 6) | valor;
    bits += 6;
    if (bits >= 8) {
      bits -= 8;
      out[pos++] = (acumulado >> bits) & 0xff;
    }
  }
  return out.subarray(0, pos);
}

// ── La llave ─────────────────────────────────────────────────────────────────

/**
 * La llave del dispositivo. Se crea la primera vez y se guarda en el almacén seguro.
 *
 * Si el almacén seguro no está disponible —no debería pasar en un teléfono, pero
 * pasa en pruebas y en emuladores mal configurados— se lanza. El que llama decide:
 * los DAO prefieren guardar en claro antes que perder la captura de campo, y eso
 * está dicho donde se hace.
 */
export async function obtenerLlave(): Promise<Uint8Array> {
  if (_llaveEnMemoria) return _llaveEnMemoria;

  const guardada = await SecureStore.getItemAsync(CLAVE_ALMACEN);
  if (guardada) {
    _llaveEnMemoria = desdeBase64(guardada);
    return _llaveEnMemoria;
  }

  // 32 bytes del generador del sistema. NO se usa `Math.random`, que es lo que
  // usa el generador de identificadores locales: ahí da igual, acá sería la llave.
  const nueva = Crypto.getRandomBytes(32);
  await SecureStore.setItemAsync(CLAVE_ALMACEN, aBase64(nueva));
  _llaveEnMemoria = nueva;
  return nueva;
}

/** Llaves separadas para cifrar y para sellar, derivadas de la misma raíz. */
function subllaves(llave: Uint8Array) {
  return {
    cifrado: sha256Bytes(concat(llave, utf8Bytes('cifrado'))),
    sello: sha256Bytes(concat(llave, utf8Bytes('sello'))),
  };
}

function concat(a: Uint8Array, b: Uint8Array): Uint8Array {
  const out = new Uint8Array(a.length + b.length);
  out.set(a);
  out.set(b, a.length);
  return out;
}

// ── Cifrar y descifrar ───────────────────────────────────────────────────────

/** Devuelve `c1:<base64>` con IV + texto cifrado + sello. */
export async function cifrar(texto: string): Promise<string> {
  if (!texto) return texto;

  const { cifrado, sello } = subllaves(await obtenerLlave());
  const iv = Crypto.getRandomBytes(LARGO_IV);

  const ctr = new aesjs.ModeOfOperation.ctr(cifrado, new aesjs.Counter(iv as any));
  const datos = ctr.encrypt(utf8Bytes(texto));

  // El sello cubre el IV además del texto cifrado: si solo cubriera el texto,
  // cambiar el IV pasaría la verificación y devolvería otra cosa.
  const marca = hmacSha256(sello, concat(iv, datos));

  return MARCA + aBase64(concat(concat(iv, datos), marca));
}

/**
 * Devuelve el texto original. Lo que no lleva la marca se devuelve igual: es lo
 * guardado antes de esta versión, y perderlo sería peor que leerlo en claro.
 *
 * Lanza si el sello no cuadra. Descifrar igual devolvería un nombre que nadie
 * escribió, y eso terminaría en la caracterización de una persona real.
 */
export async function descifrar(texto: string): Promise<string> {
  if (!texto || !texto.startsWith(MARCA)) return texto;

  const bruto = desdeBase64(texto.slice(MARCA.length));
  if (bruto.length < LARGO_IV + LARGO_SELLO) {
    throw new Error('El dato cifrado está incompleto.');
  }

  const iv = bruto.subarray(0, LARGO_IV);
  const datos = bruto.subarray(LARGO_IV, bruto.length - LARGO_SELLO);
  const marca = bruto.subarray(bruto.length - LARGO_SELLO);

  const { cifrado, sello } = subllaves(await obtenerLlave());
  if (!igualesEnTiempoConstante(hmacSha256(sello, concat(iv, datos)), marca)) {
    throw new Error('El dato cifrado fue alterado.');
  }

  const ctr = new aesjs.ModeOfOperation.ctr(cifrado, new aesjs.Counter(iv as any));
  return new TextDecoder().decode(ctr.decrypt(datos));
}

/** ¿Este valor ya está cifrado? Sirve para no cifrar dos veces. */
export function estaCifrado(texto: string): boolean {
  return typeof texto === 'string' && texto.startsWith(MARCA);
}

/**
 * Borra la llave. Al cerrar sesión se borran los datos del teléfono; sin llave, lo
 * que quedara cifrado tampoco se puede recuperar.
 */
export async function olvidarLlave(): Promise<void> {
  _llaveEnMemoria = null;
  try {
    await SecureStore.deleteItemAsync(CLAVE_ALMACEN);
  } catch {
    /* si no se puede borrar, la próxima sesión la reutiliza: no hay dato que salvar */
  }
}
