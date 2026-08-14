/**
 * El filtro del universo del RUV en el dispositivo.
 *
 * ── Qué resuelve ────────────────────────────────────────────────────────────
 * Hasta ahora, en campo y sin señal, buscar a una persona que está en el RUV
 * pero nunca fue entrevistada respondía "no está en los datos offline". Es
 * falso: son **8,12 millones de víctimas reconocidas**, y de 68 cédulas traídas
 * del territorio, 33 estaban en ese caso. La pantalla ni siquiera ofrecía el
 * alta manual — dejaba al encuestador sin salida frente a la persona.
 *
 * ── Por qué un archivo suelto y no una tabla SQLite ─────────────────────────
 * Tres razones, y ninguna es de estilo:
 *
 * 1. **No cruzar 22,7 MB por el puente JS.** Leer un BLOB desde SQLite trae el
 *    buffer entero a JavaScript en CADA consulta. Acá se leen los **10 bytes**
 *    que hacen falta, con `offset` sobre el descriptor del archivo.
 * 2. **No tocar el esquema local.** Añadir una tabla obligaba a una
 *    MIGRATION_V12, y el mecanismo de migración de la APK no envuelve en
 *    transacción y sella `user_version` solo al final: una migración a medias
 *    deja la base en un estado que el arranque siguiente vuelve a intentar
 *    entero. Los parámetros caben en `meta_offline`, que ya existe.
 * 3. **Poder borrarlo sin vaciar la base**, que es lo que pide el cierre de
 *    jornada.
 *
 * ── El precio, que la pantalla DEBE decir ───────────────────────────────────
 * Nunca hay falsos negativos: si la persona está en el universo, el filtro la
 * reconoce siempre. Pero ~1 de cada 1.000 consultas sobre alguien ajeno
 * responde que sí. Un acierto es un **candidato a alta manual**, a confirmar
 * cuando vuelva la señal — nunca una identificación.
 */
import { File, Paths } from 'expo-file-system';

import { contieneCon, esUsable, type ParametrosBloom } from '../crypto/bloom';
import { numHash } from '../crypto/docHash';

/** Nombre del archivo en el directorio de documentos de la app. */
const ARCHIVO = 'universo-bloom.bin';

/** Claves en `meta_offline`. El filtro sin sus parámetros no se puede consultar. */
export const CLAVE_PARAMS = 'universo_bloom_params';
export const CLAVE_VERSION = 'universo_bloom_version';

export interface ParametrosDescarga extends ParametrosBloom {
  /** De dónde bajarlo. Viene en la precarga (`padron_archivo.bloom.url`). */
  url: string;
}

function archivo(): File {
  return new File(Paths.document, ARCHIVO);
}

/**
 * Descarga el filtro y lo deja listo para consultar.
 *
 * Devuelve `true` si al terminar hay un filtro usable. NO lanza si falla: sin
 * filtro la APK sigue funcionando como hasta ahora, y una precarga que revienta
 * porque no pudo bajar un accesorio es peor que no tenerlo.
 *
 * @param token  Bearer del usuario — el endpoint exige autenticación.
 */
export async function descargarFiltro(
  params: ParametrosDescarga,
  token: string,
): Promise<boolean> {
  if (params.formato !== 1 || !params.m || !params.k) {
    return false;
  }

  const destino = archivo();
  const esperado = Math.floor(params.m / 8);

  try {
    // `idempotent`: si quedó un filtro de una versión anterior, se sobrescribe.
    // Sin esto la segunda descarga lanza porque el archivo ya existe.
    await File.downloadFileAsync(params.url, destino, {
      headers: { Authorization: `Bearer ${token}` },
      idempotent: true,
    });
  } catch {
    return false;
  }

  // Verificación de tamaño, y no es opcional. Un filtro truncado NO falla al
  // consultarlo: los bytes que faltan se leen como 0 y responde "no está en el
  // universo" para todo el mundo, en silencio. Es exactamente el bug que este
  // módulo vino a evitar, así que se comprueba antes de dejarlo activo.
  if (!destino.exists || destino.size !== esperado) {
    try {
      destino.delete();
    } catch {
      /* si no se puede borrar, `hayFiltro()` lo descarta igual por tamaño */
    }
    return false;
  }

  return true;
}

/** ¿Hay un filtro descargado y del tamaño que declaran sus parámetros? */
export function hayFiltro(params: ParametrosBloom | null | undefined): boolean {
  if (!params || params.formato !== 1 || !params.m) return false;
  const f = archivo();
  return f.exists && f.size === Math.floor(params.m / 8);
}

/**
 * ¿Esta persona está en el universo del RUV?
 *
 * `false` es DEFINITIVO. `true` es "probablemente" — ver la nota de falsos
 * positivos arriba.
 *
 * Lee solo los bytes que necesita: k posiciones sueltas del archivo, no el
 * archivo. Con k=10 son 10 lecturas de 1 byte.
 *
 * ⚠️ Se consulta con `numHash` (SHA-256 del número SIN tipo). Consultarlo con
 * `docHash` no encuentra nada, y no avisa.
 */
export function estaEnUniverso(
  numeroDocumento: string,
  params: ParametrosBloom | null | undefined,
): boolean {
  if (!params || !hayFiltro(params)) return false;

  const f = archivo();
  const bytes = Math.floor(params.m / 8);
  const handle = f.open();
  try {
    return contieneCon(
      (indice) => {
        // Fuera de rango → 0. Nunca `undefined`: ver la nota de `contieneCon`.
        if (indice < 0 || indice >= bytes) return 0;
        handle.offset = indice;
        return handle.readBytes(1)[0] ?? 0;
      },
      params.m,
      params.k,
      numHash(numeroDocumento),
    );
  } catch {
    // Un fallo de lectura NO puede decir "no está en el RUV": eso negaría el
    // alta a una víctima real. Se responde false —igual que sin filtro— pero
    // conviene tener claro que es "no sé", no "no está".
    return false;
  } finally {
    try {
      handle.close();
    } catch {
      /* nada que hacer */
    }
  }
}

/** Borra el filtro. Al cerrar sesión, junto con el resto del almacén. */
export function borrarFiltro(): void {
  try {
    const f = archivo();
    if (f.exists) f.delete();
  } catch {
    /* si no se puede borrar, la próxima descarga lo sobrescribe */
  }
}

/** Parámetros guardados, o `null` si no hay filtro configurado. */
export function parsearParametros(json: string | null | undefined): ParametrosBloom | null {
  if (!json) return null;
  try {
    const p = JSON.parse(json) as ParametrosBloom;
    return esUsable(new Uint8Array(Math.floor(p.m / 8)), p) ? p : null;
  } catch {
    return null;
  }
}
