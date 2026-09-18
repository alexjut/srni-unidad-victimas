/**
 * Cifrado en reposo de los datos personales del teléfono.
 *
 * Mientras la cola está pendiente, el dispositivo guarda nombre y documento de
 * personas reales. Estaban en claro: un teléfono perdido, prestado o revisado los
 * entrega enteros, y son datos de víctimas del conflicto.
 *
 * Lo que se fija acá: que el texto guardado no se parezca al original, que un byte
 * alterado se detecte en vez de devolver un nombre inventado, y que lo guardado
 * ANTES de esta versión se siga leyendo.
 */
const mockAlmacen: Record<string, string> = {};
jest.mock('expo-secure-store', () => ({
  getItemAsync: jest.fn(async (k: string) => mockAlmacen[k] ?? null),
  setItemAsync: jest.fn(async (k: string, v: string) => { mockAlmacen[k] = v; }),
  deleteItemAsync: jest.fn(async (k: string) => { delete mockAlmacen[k]; }),
}));

// Semilla determinista: los tests no pueden depender del azar, pero el módulo sí
// tiene que pedirle los bytes al generador del sistema y no a Math.random.
let mockSemilla = 1;
jest.mock('expo-crypto', () => ({
  getRandomBytes: jest.fn((n: number) => {
    const b = new Uint8Array(n);
    for (let i = 0; i < n; i++) b[i] = (mockSemilla * 31 + i * 7) % 256;
    mockSemilla++;
    return b;
  }),
}));

import * as Crypto from 'expo-crypto';
import {
  aBase64, cifrar, desdeBase64, descifrar, estaCifrado, obtenerLlave, olvidarLlave,
} from '../cofreLocal';

const PII = JSON.stringify({
  primer_nombre: 'MARÍA JOSÉ', primer_apellido: 'PÉREZ ÑUÑEZ',
  numero_documento: '1030547250',
});

beforeEach(async () => {
  for (const k of Object.keys(mockAlmacen)) delete mockAlmacen[k];
  mockSemilla = 1;
  await olvidarLlave();
  jest.clearAllMocks();
});

describe('cifrar / descifrar', () => {
  it('lo cifrado vuelve a ser lo mismo', async () => {
    expect(await descifrar(await cifrar(PII))).toBe(PII);
  });

  it('el texto guardado no contiene el nombre ni el documento', async () => {
    const guardado = await cifrar(PII);

    expect(guardado).not.toContain('MARÍA');
    expect(guardado).not.toContain('1030547250');
    expect(estaCifrado(guardado)).toBe(true);
  });

  it('respeta acentos y eñes', async () => {
    const texto = 'ÑANDÚ ÁÉÍÓÚ üÜ — José Muñoz';

    expect(await descifrar(await cifrar(texto))).toBe(texto);
  });

  it('dos veces el mismo dato no da el mismo texto cifrado', async () => {
    // Si diera igual, ver dos filas idénticas ya diría que son la misma persona.
    expect(await cifrar(PII)).not.toBe(await cifrar(PII));
  });

  it('un byte alterado se detecta en vez de devolver un nombre inventado', async () => {
    const guardado = await cifrar(PII);
    const bytes = desdeBase64(guardado.slice(3));
    bytes[20] ^= 0x01;
    const alterado = 'c1:' + aBase64(bytes);

    await expect(descifrar(alterado)).rejects.toThrow(/alterado/i);
  });

  it('cambiar el IV tampoco pasa: el sello lo cubre', async () => {
    const guardado = await cifrar(PII);
    const bytes = desdeBase64(guardado.slice(3));
    bytes[0] ^= 0xff;

    await expect(descifrar('c1:' + aBase64(bytes))).rejects.toThrow(/alterado/i);
  });

  it('un dato recortado no se intenta descifrar', async () => {
    await expect(descifrar('c1:' + aBase64(new Uint8Array(8)))).rejects.toThrow(/incompleto/i);
  });

  it('el texto vacío se deja como está', async () => {
    expect(await cifrar('')).toBe('');
    expect(await descifrar('')).toBe('');
  });
});

describe('compatibilidad con lo guardado antes', () => {
  it('lo que está en claro se sigue leyendo', async () => {
    // Las filas anteriores a esta versión no llevan marca. Perderlas sería peor.
    expect(await descifrar(PII)).toBe(PII);
    expect(estaCifrado(PII)).toBe(false);
  });
});

describe('la llave', () => {
  it('se crea una sola vez y queda en el almacén seguro', async () => {
    const a = await obtenerLlave();
    await olvidarLlaveSoloDeMemoria();
    const b = await obtenerLlave();

    expect(Array.from(b)).toEqual(Array.from(a));
  });

  it('son 32 bytes del generador del sistema, no de Math.random', async () => {
    const llave = await obtenerLlave();

    expect(llave.length).toBe(32);
    expect(Crypto.getRandomBytes).toHaveBeenCalledWith(32);
  });

  it('sin llave, lo cifrado ya no se puede leer', async () => {
    const guardado = await cifrar(PII);
    await olvidarLlave();

    // Con otra llave el sello no cuadra: se rechaza en vez de devolver basura.
    await expect(descifrar(guardado)).rejects.toThrow();
  });
});

/** Vacía solo la copia en memoria, dejando la llave guardada. */
async function olvidarLlaveSoloDeMemoria() {
  const guardada = mockAlmacen['cofre_local_v1'];
  await olvidarLlave();
  mockAlmacen['cofre_local_v1'] = guardada;
}

describe('base64', () => {
  it('ida y vuelta con cualquier largo', async () => {
    for (const largo of [0, 1, 2, 3, 16, 31, 32, 100]) {
      const bytes = new Uint8Array(largo).map((_, i) => (i * 13) % 256);
      expect(Array.from(desdeBase64(aBase64(bytes)))).toEqual(Array.from(bytes));
    }
  });
});
