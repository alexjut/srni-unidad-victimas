/**
 * DAO para el instrumento PAARI en SQLite.
 *
 * Guarda la respuesta completa del backend (Instrumento con temas y preguntas
 * anidados) en las tablas locales. Una vez guardado, toda la app lee desde
 * SQLite y no necesita red para mostrar el formulario.
 */
import { openDb } from './schema';
import type { TemaDetalle, Instrumento } from '../types';

export interface InstrumentoMeta {
  instrumento_id: number;
  version: string;
  descargado_en: string;
}

export interface PreguntaRow {
  id: number;
  tema_id: number;
  codigo: string;
  texto: string;
  texto_ayuda: string;
  tipo_respuesta: string;
  orden: number;
  requerida: number;
  activa: number;
  validacion: string;
}

export interface OpcionRow {
  id: number;
  pregunta_id: number;
  codigo: string;
  texto: string;
  orden: number;
}

export interface DerivadaRow {
  id: number;
  pregunta_padre_id: number;
  pregunta_hija_id: number;
  operador: string;
  valor_condicion: string;
}

export interface TemaRow {
  id: number;
  codigo: string;
  nombre: string;
  orden: number;
  activo: number;
}

// ─────────────────────────────────────────────────────────────────────────────

/**
 * Persiste el instrumento completo. Borra y reescribe todas las tablas del
 * instrumento para garantizar coherencia con la versión del servidor.
 */
export async function guardarInstrumento(instrumento: Instrumento): Promise<void> {
  const db = await openDb();

  await db.withTransactionAsync(async () => {
    // Limpiar datos anteriores del instrumento
    await db.runAsync('DELETE FROM preguntas_derivadas');
    await db.runAsync('DELETE FROM opciones_respuesta');
    await db.runAsync('DELETE FROM preguntas');
    await db.runAsync('DELETE FROM temas');
    await db.runAsync('DELETE FROM instrumento_meta');

    // Guardar cada tema y sus preguntas
    for (const tema of instrumento.temas as TemaDetalle[]) {
      await db.runAsync(
        'INSERT INTO temas (id, codigo, nombre, orden, activo) VALUES (?, ?, ?, ?, ?)',
        [tema.id, tema.codigo, tema.nombre, tema.orden, tema.activo ? 1 : 0],
      );

      if (!tema.preguntas) continue;

      for (const p of tema.preguntas) {
        await db.runAsync(
          `INSERT INTO preguntas
             (id, tema_id, codigo, texto, texto_ayuda, tipo_respuesta, orden, requerida, activa, validacion)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
          [
            p.id, tema.id, p.codigo, p.texto, p.texto_ayuda ?? '',
            p.tipo_respuesta, p.orden, p.requerida ? 1 : 0, p.activa ? 1 : 0,
            JSON.stringify(p.validacion ?? {}),
          ],
        );

        for (const o of p.opciones ?? []) {
          await db.runAsync(
            'INSERT INTO opciones_respuesta (id, pregunta_id, codigo, texto, orden) VALUES (?, ?, ?, ?, ?)',
            [o.id, p.id, o.codigo, o.texto, o.orden],
          );
        }

        for (const c of p.condiciones_habilitacion ?? []) {
          await db.runAsync(
            `INSERT INTO preguntas_derivadas
               (id, pregunta_padre_id, pregunta_hija_id, operador, valor_condicion)
             VALUES (?, ?, ?, ?, ?)`,
            [c.id, c.pregunta_padre, p.id, c.operador, c.valor_condicion],
          );
        }
      }
    }

    // Guardar metadata
    await db.runAsync(
      `INSERT INTO instrumento_meta (id, instrumento_id, version, descargado_en)
       VALUES (1, ?, ?, ?)`,
      [instrumento.id, instrumento.version, new Date().toISOString()],
    );
  });
}

export async function getMeta(): Promise<InstrumentoMeta | null> {
  const db = await openDb();
  return db.getFirstAsync<InstrumentoMeta>(
    'SELECT instrumento_id, version, descargado_en FROM instrumento_meta WHERE id = 1',
  );
}

export async function getTemas(): Promise<TemaRow[]> {
  const db = await openDb();
  return db.getAllAsync<TemaRow>(
    'SELECT * FROM temas WHERE activo = 1 ORDER BY orden',
  );
}

export async function getPreguntas(temaId: number): Promise<PreguntaRow[]> {
  const db = await openDb();
  return db.getAllAsync<PreguntaRow>(
    'SELECT * FROM preguntas WHERE tema_id = ? AND activa = 1 ORDER BY orden',
    [temaId],
  );
}

export async function getOpciones(preguntaId: number): Promise<OpcionRow[]> {
  const db = await openDb();
  return db.getAllAsync<OpcionRow>(
    'SELECT * FROM opciones_respuesta WHERE pregunta_id = ? ORDER BY orden',
    [preguntaId],
  );
}

/** Devuelve todas las opciones para un conjunto de preguntas (batch). */
export async function getOpcionesBatch(preguntaIds: number[]): Promise<Record<number, OpcionRow[]>> {
  if (preguntaIds.length === 0) return {};
  const db = await openDb();
  const ph = preguntaIds.map(() => '?').join(',');
  const rows = await db.getAllAsync<OpcionRow>(
    `SELECT * FROM opciones_respuesta WHERE pregunta_id IN (${ph}) ORDER BY orden`,
    preguntaIds,
  );
  const result: Record<number, OpcionRow[]> = {};
  for (const r of rows) {
    if (!result[r.pregunta_id]) result[r.pregunta_id] = [];
    result[r.pregunta_id].push(r);
  }
  return result;
}

/** Devuelve todas las condiciones cuyo padre está en el conjunto dado. */
export async function getDerivadas(preguntaIds: number[]): Promise<DerivadaRow[]> {
  if (preguntaIds.length === 0) return [];
  const db = await openDb();
  const ph = preguntaIds.map(() => '?').join(',');
  return db.getAllAsync<DerivadaRow>(
    `SELECT * FROM preguntas_derivadas WHERE pregunta_padre_id IN (${ph})`,
    preguntaIds,
  );
}
