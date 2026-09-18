/**
 * El padrón completo en el dispositivo (Fase B2).
 *
 * Lo que se fija acá es el contrato con el archivo que genera el servidor: cómo
 * se busca (clave binaria de 16 bytes, varias filas por documento) y cómo se lee
 * el mapa de bits de `flags`. Leerlo mal no falla: devuelve a la persona con las
 * banderas cambiadas, que en campo es peor que no encontrarla.
 */
const mockArchivo = { exists: true, size: 334_200_832, uri: 'file:///doc/padron.sqlite3', delete: jest.fn() };
const mockDescargar = jest.fn().mockResolvedValue(undefined);

jest.mock('expo-file-system', () => ({
  File: Object.assign(
    jest.fn().mockImplementation(() => mockArchivo),
    { downloadFileAsync: (...a: unknown[]) => mockDescargar(...a) },
  ),
  Paths: { document: { uri: 'file:///doc/' } },
}));

const mockDb = {
  getAllAsync: jest.fn(),
  getFirstAsync: jest.fn(),
  closeAsync: jest.fn().mockResolvedValue(undefined),
};
jest.mock('expo-sqlite', () => ({
  openDatabaseAsync: jest.fn(() => Promise.resolve(mockDb)),
}));

import { claveDocumento } from '../../crypto/docHash';
import {
  buscarEnArchivo, descargarPadron, esquemaSoportado, hayArchivo,
} from '../padronArchivo';

const INFO = { url: 'https://srni/api/victimas/padron/download/', version: 'v-2026', esquema: 3 };

function fila(over: Record<string, unknown> = {}) {
  return {
    nombre: 'JUANA PÉREZ', ubicacion: 'SOACHA', cantidad_hechos: 2,
    flags: 0, cons_persona: 991, clase_colision: null, ...over,
  };
}

beforeEach(() => {
  jest.clearAllMocks();
  mockArchivo.exists = true;
  mockArchivo.size = 334_200_832;
  mockDb.getFirstAsync.mockResolvedValue({ n: 1 });
});

describe('buscarEnArchivo', () => {
  it('consulta por la clave binaria de 16 bytes, no por el hash en texto', async () => {
    mockDb.getAllAsync.mockResolvedValue([fila()]);

    await buscarEnArchivo('CC', '1.030.547');

    const [, params] = mockDb.getAllAsync.mock.calls[0];
    expect(params[0]).toEqual(claveDocumento('CC', '1.030.547'));
    expect(params[0]).toHaveLength(16);
  });

  it('traduce el mapa de bits de flags', async () => {
    // bit 0 = en_ruv · bit 1 = habilitada · bit 2 = ya_caracterizada
    mockDb.getAllAsync.mockResolvedValue([fila({ flags: 0b011 })]);

    const [p] = await buscarEnArchivo('CC', '123');

    expect(p.en_ruv).toBe(true);
    expect(p.habilitada).toBe(true);
    expect(p.ya_caracterizada).toBe(false);
  });

  it('flags en cero: ninguna bandera encendida', async () => {
    mockDb.getAllAsync.mockResolvedValue([fila({ flags: 0 })]);

    const [p] = await buscarEnArchivo('CC', '123');

    expect([p.en_ruv, p.habilitada, p.ya_caracterizada]).toEqual([false, false, false]);
  });

  it('devuelve TODAS las filas del documento: un documento compartido no se resuelve solo', async () => {
    mockDb.getAllAsync.mockResolvedValue([
      fila({ nombre: 'UNA', clase_colision: 'AMBIGUO' }),
      fila({ nombre: 'OTRA', clase_colision: 'AMBIGUO' }),
    ]);

    const r = await buscarEnArchivo('CC', '123');

    expect(r).toHaveLength(2);
    expect(r.every((x) => x.clase_colision === 'AMBIGUO')).toBe(true);
  });

  it('sin archivo descargado no consulta nada', async () => {
    mockArchivo.exists = false;

    expect(await buscarEnArchivo('CC', '123')).toEqual([]);
    expect(mockDb.getAllAsync).not.toHaveBeenCalled();
  });

  it('si la consulta falla devuelve vacío en vez de tumbar la búsqueda', async () => {
    mockDb.getAllAsync.mockRejectedValue(new Error('archivo corrupto'));

    expect(await buscarEnArchivo('CC', '123')).toEqual([]);
  });

  it('cierra el archivo siempre, incluso al fallar', async () => {
    mockDb.getAllAsync.mockRejectedValue(new Error('x'));

    await buscarEnArchivo('CC', '123');

    expect(mockDb.closeAsync).toHaveBeenCalled();
  });
});

describe('esquemaSoportado', () => {
  it('acepta los esquemas 2 y 3', () => {
    expect(esquemaSoportado({ ...INFO, esquema: 2 })).toBe(true);
    expect(esquemaSoportado({ ...INFO, esquema: 3 })).toBe(true);
  });

  it('rechaza un esquema nuevo que este cliente no sabe leer', () => {
    // Leer un esquema desconocido no falla: devuelve respuestas mal formadas.
    expect(esquemaSoportado({ ...INFO, esquema: 4 })).toBe(false);
  });

  it('rechaza si el servidor no declara esquema o falta la url', () => {
    expect(esquemaSoportado({ url: INFO.url, version: 'v' } as never)).toBe(false);
    expect(esquemaSoportado({ version: 'v', esquema: 3 } as never)).toBe(false);
  });
});

describe('descargarPadron', () => {
  it('no intenta bajar un archivo de esquema desconocido', async () => {
    expect(await descargarPadron({ ...INFO, esquema: 9 }, 'tok')).toBe(false);
    expect(mockDescargar).not.toHaveBeenCalled();
  });

  it('descarga con el token del usuario y reemplaza el archivo anterior', async () => {
    const ok = await descargarPadron(INFO, 'tok-123');

    expect(ok).toBe(true);
    const [url, , opciones] = mockDescargar.mock.calls[0];
    expect(url).toBe(INFO.url);
    expect(opciones).toMatchObject({ idempotent: true, headers: { Authorization: 'Bearer tok-123' } });
  });

  it('descarga cortada: borra el archivo y no lo da por bueno', async () => {
    // Un SQLite truncado puede abrir y no tener la tabla; peor sería dejarlo
    // activo y que la búsqueda respondiera «no está» para todo el mundo.
    mockDb.getFirstAsync.mockResolvedValue({ n: 0 });

    expect(await descargarPadron(INFO, 'tok')).toBe(false);
    expect(mockArchivo.delete).toHaveBeenCalled();
  });

  it('si la descarga lanza, no deja el servicio en error', async () => {
    mockDescargar.mockRejectedValueOnce(new Error('sin red'));

    expect(await descargarPadron(INFO, 'tok')).toBe(false);
  });
});

describe('hayArchivo', () => {
  it('es falso si el archivo no existe o está vacío', () => {
    mockArchivo.exists = false;
    expect(hayArchivo()).toBe(false);

    mockArchivo.exists = true;
    mockArchivo.size = 0;
    expect(hayArchivo()).toBe(false);
  });
});
