/**
 * Puerta única al cifrado de los datos personales guardados en el teléfono.
 *
 * Los DAO no hablan directo con `crypto/cofreLocal` por una razón de campo: si el
 * almacén seguro del sistema falla —no debería en un teléfono, pero pasa en
 * emuladores y equipos con el Keystore roto—, **guardar en claro es mejor que
 * perder la captura**. La encuestadora tiene a la persona enfrente; una excepción
 * acá le borraría el trabajo.
 *
 * Por eso: se intenta cifrar y, si no se puede, se guarda como antes y se registra.
 * Al leer es al revés y sin concesiones: si el dato viene cifrado y el sello no
 * cuadra, se propaga el error. Descifrar a medias devolvería un nombre que nadie
 * escribió, y eso terminaría dentro de la caracterización de una persona real.
 */
import { cifrar, descifrar } from '../crypto/cofreLocal';
import { reportarError } from '../services/errorReporter';

export async function cifrarPayload(texto: string): Promise<string> {
  try {
    return await cifrar(texto);
  } catch (e) {
    reportarError({
      nivel: 'warn',
      mensaje: 'No se pudo cifrar el dato local; se guarda como antes: '
        + ((e as Error)?.message ?? String(e)),
      pantalla: 'db/payloadSeguro',
    });
    return texto;
  }
}

export async function descifrarPayload(texto: string): Promise<string> {
  return descifrar(texto);
}
