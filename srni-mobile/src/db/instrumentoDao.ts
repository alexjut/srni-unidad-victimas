/**
 * DAO para el instrumento de caracterización en SQLite — Sprint 7.
 *
 * Guarda la respuesta completa de InstrumentoCompletoView en tablas locales
 * UUID-based. Una vez guardado, toda la app lee desde SQLite y no necesita
 * red para mostrar el formulario.
 */
import { openDb } from './schema';

// ─── Interfaces de fila ───────────────────────────────────────────────────────

export interface InstrumentoMeta {
  instrumento_id: string;  // UUID de InstrumentoVersion
  perfil_codigo: string;
  version: string;
  descargado_en: string;
}

export interface CapituloRow {
  id: string;      // UUID
  codigo: string;
  nombre: string;
  orden: number;
  nivel: string;   // HOGAR | PERSONA
  activo: number;
}

export interface PreguntaRow {
  id: string;            // UUID
  capitulo_id: string;   // UUID
  codigo_externo: string;
  no_pregunta: string;
  texto: string;
  descripcion_ayuda: string;
  tipo: string;          // TEXTO | NUMERICO | FECHA | RADIO | LISTA | LISTA_MULTIPLE | BOOLEAN | TEXTO_LARGO | COMBO_DINAMICO
  nivel: string;         // HOGAR | PERSONA
  orden: number;
  obligatoria: number;   // 0 | 1
  activa: number;        // 0 | 1
  validaciones: string;  // JSON
}

export interface OpcionRow {
  id: string;            // UUID
  pregunta_id: string;   // UUID
  valor: string;
  etiqueta: string;
  orden: number;
  finaliza_capitulo: number; // 0 | 1
}

export interface ReglaSkipLogicRow {
  id: string;
  instrumento_id: string;
  pregunta_origen_codigo: string | null;
  valor_trigger: string;
  expresion_origen: string;
  pregunta_afectada_id: string | null;
  pregunta_afectada_codigo: string | null;
  capitulo_afectado_id: string | null;
  accion: string; // HABILITAR | DESHABILITAR | OBLIGAR | FINALIZAR
}

// ─── Tipo de entrada (respuesta del backend) ──────────────────────────────────

interface OpcionBackend {
  id: string;
  valor: string;
  etiqueta: string;
  orden: number;
  finaliza_capitulo: boolean;
}

interface ReglaBackend {
  id: string;
  pregunta_origen: string | null;
  pregunta_origen_codigo: string | null;
  expresion_origen: string;
  valor_trigger: string;
  pregunta_afectada: string | null;
  pregunta_afectada_codigo: string | null;
  capitulo_afectado: string | null;
  accion: string;
}

interface PreguntaBackend {
  id: string;
  codigo_externo: string;
  no_pregunta: string;
  texto: string;
  descripcion_ayuda: string;
  tipo: string;
  nivel: string;
  orden: number;
  obligatoria: boolean;
  activa: boolean;
  validaciones: Record<string, unknown>;
  opciones: OpcionBackend[];
  reglas_entrantes: ReglaBackend[];
}

interface CapituloBackend {
  id: string;
  codigo: string;
  nombre: string;
  orden: number;
  nivel: string;
  preguntas: PreguntaBackend[];
}

/**
 * Forma real de la respuesta del backend (InstrumentoCompletoView).
 * Sprint 17 fix: los campos son `codigo` y `version`, no `perfil_codigo`/`numero`.
 * Esos nombres viejos quedaron como aliases solo para retro-compat con
 * posibles mocks de tests pero NO los devuelve el backend real.
 */
export interface InstrumentoCompletoBackend {
  id: string;             // UUID de Instrumento
  codigo: string;         // p.ej. "TERRITORIAL"
  nombre?: string;
  version: string;        // p.ej. "V7"
  capitulos: CapituloBackend[];
  reglas: ReglaBackend[];
  // Aliases viejos opcionales (no se usan, mantenidos por si algún mock los pasa)
  perfil_codigo?: string;
  numero?: string;
}

// ─── Escritura ────────────────────────────────────────────────────────────────

/**
 * Persiste el instrumento completo desde el backend.
 * Borra y reescribe todas las tablas del instrumento para garantizar coherencia.
 */
export async function guardarInstrumentoCompleto(data: InstrumentoCompletoBackend): Promise<void> {
  // Logger import dinámico para evitar ciclo en imports
  const { log } = await import('../services/logger');
  const db = await openDb();
  log.event('GUARDAR', 'A. openDb OK, iniciando transacción', {
    caps: data.capitulos?.length, reglas: data.reglas?.length,
  });

  let preguntaActual = '';
  let capActual = '';
  try {
    await db.withTransactionAsync(async () => {
      log.event('GUARDAR', 'B. Limpiando tablas previas');
      await db.runAsync('DELETE FROM reglas_skip_logic');
      await db.runAsync('DELETE FROM opciones_respuesta');
      await db.runAsync('DELETE FROM preguntas');
      await db.runAsync('DELETE FROM capitulos');
      await db.runAsync('DELETE FROM instrumento_meta');
      log.event('GUARDAR', 'C. Tablas limpias');

      let totalP = 0, totalO = 0;
      for (const cap of data.capitulos) {
        capActual = cap.codigo;
        await db.runAsync(
          'INSERT INTO capitulos (id, codigo, nombre, orden, nivel, activo) VALUES (?, ?, ?, ?, ?, 1)',
          [cap.id, cap.codigo, cap.nombre, cap.orden, cap.nivel ?? 'HOGAR'],
        );

        for (const p of cap.preguntas ?? []) {
          if (!p.activa) continue;
          preguntaActual = p.codigo_externo;

          await db.runAsync(
            `INSERT INTO preguntas
               (id, capitulo_id, codigo_externo, no_pregunta, texto, descripcion_ayuda,
                tipo, nivel, orden, obligatoria, activa, validaciones)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)`,
            [
              p.id, cap.id, p.codigo_externo, p.no_pregunta ?? '',
              p.texto ?? '', p.descripcion_ayuda ?? '',
              p.tipo ?? 'TEXTO', p.nivel ?? cap.nivel ?? 'HOGAR',
              p.orden ?? 0, p.obligatoria ? 1 : 0,
              JSON.stringify(p.validaciones ?? {}),
            ],
          );
          totalP++;

          for (const o of p.opciones ?? []) {
            await db.runAsync(
              'INSERT INTO opciones_respuesta (id, pregunta_id, valor, etiqueta, orden, finaliza_capitulo) VALUES (?, ?, ?, ?, ?, ?)',
              [o.id, p.id, o.valor ?? '', o.etiqueta ?? '', o.orden ?? 0, o.finaliza_capitulo ? 1 : 0],
            );
            totalO++;
          }
        }
      }
      log.event('GUARDAR', 'D. Capítulos+preguntas+opciones insertadas', { totalP, totalO });

    // Guardar reglas del instrumento (nivel versión)
    for (const r of data.reglas ?? []) {
      await db.runAsync(
        `INSERT INTO reglas_skip_logic
           (id, instrumento_id, pregunta_origen_codigo, valor_trigger, expresion_origen,
            pregunta_afectada_id, pregunta_afectada_codigo, capitulo_afectado_id, accion)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        [
          r.id, data.id,
          r.pregunta_origen_codigo ?? null,
          r.valor_trigger ?? '',
          r.expresion_origen ?? '',
          r.pregunta_afectada ?? null,
          r.pregunta_afectada_codigo ?? null,
          r.capitulo_afectado ?? null,
          r.accion,
        ],
      );
    }

    // Sprint 17 fix: backend devuelve `codigo` y `version`, no `perfil_codigo`/`numero`.
    // Aceptamos los aliases viejos como fallback solo por defensiva.
    const perfilCodigo = data.codigo ?? data.perfil_codigo ?? '';
    const version      = data.version ?? data.numero ?? '0';

    // Guardar metadata
    await db.runAsync(
      `INSERT INTO instrumento_meta (id, instrumento_id, perfil_codigo, version, descargado_en)
       VALUES (1, ?, ?, ?, ?)`,
      [data.id, perfilCodigo, version, new Date().toISOString()],
    );
    log.event('GUARDAR', 'E. Meta insertado', { perfilCodigo, version });
    });
    log.event('GUARDAR', 'F. Transacción commit OK');
  } catch (err) {
    log.error('guardarInstrumentoCompleto EXPLOTÓ', err, {
      ultimoCap: capActual,
      ultimaPregunta: preguntaActual,
    });
    throw err;
  }
}

// ─── Lectura ──────────────────────────────────────────────────────────────────

export async function getMeta(): Promise<InstrumentoMeta | null> {
  const db = await openDb();
  return db.getFirstAsync<InstrumentoMeta>(
    'SELECT instrumento_id, perfil_codigo, version, descargado_en FROM instrumento_meta WHERE id = 1',
  );
}

export async function getCapitulos(): Promise<CapituloRow[]> {
  const db = await openDb();
  return db.getAllAsync<CapituloRow>(
    'SELECT * FROM capitulos WHERE activo = 1 ORDER BY orden',
  );
}

export async function getPreguntas(capituloId: string): Promise<PreguntaRow[]> {
  const db = await openDb();
  return db.getAllAsync<PreguntaRow>(
    'SELECT * FROM preguntas WHERE capitulo_id = ? AND activa = 1 ORDER BY orden',
    [capituloId],
  );
}

export async function getOpciones(preguntaId: string): Promise<OpcionRow[]> {
  const db = await openDb();
  return db.getAllAsync<OpcionRow>(
    'SELECT * FROM opciones_respuesta WHERE pregunta_id = ? ORDER BY orden',
    [preguntaId],
  );
}

export async function getOpcionesBatch(preguntaIds: string[]): Promise<Record<string, OpcionRow[]>> {
  if (preguntaIds.length === 0) return {};
  const db = await openDb();
  const ph = preguntaIds.map(() => '?').join(',');
  const rows = await db.getAllAsync<OpcionRow>(
    `SELECT * FROM opciones_respuesta WHERE pregunta_id IN (${ph}) ORDER BY orden`,
    preguntaIds,
  );
  const result: Record<string, OpcionRow[]> = {};
  for (const r of rows) {
    if (!result[r.pregunta_id]) result[r.pregunta_id] = [];
    result[r.pregunta_id].push(r);
  }
  return result;
}

export async function getReglasPorInstrumento(instrumentoId: string): Promise<ReglaSkipLogicRow[]> {
  const db = await openDb();
  return db.getAllAsync<ReglaSkipLogicRow>(
    'SELECT * FROM reglas_skip_logic WHERE instrumento_id = ?',
    [instrumentoId],
  );
}

/**
 * Devuelve conteo de preguntas activas por capítulo: total y sólo obligatorias.
 * Usado para calcular progreso real en la lista de capítulos.
 */
export async function contarPreguntasPorCapitulo(): Promise<
  Record<string, { total: number; obligatorias: number }>
> {
  const db = await openDb();
  const rows = await db.getAllAsync<{
    capitulo_id: string;
    total: number;
    obligatorias: number;
  }>(
    `SELECT capitulo_id,
            COUNT(*) AS total,
            SUM(CASE WHEN obligatoria = 1 THEN 1 ELSE 0 END) AS obligatorias
     FROM preguntas
     WHERE activa = 1
     GROUP BY capitulo_id`,
  );
  const map: Record<string, { total: number; obligatorias: number }> = {};
  for (const r of rows) map[r.capitulo_id] = { total: r.total, obligatorias: r.obligatorias };
  return map;
}

export async function getReglasPorCapitulo(
  capituloId: string,
  instrumentoId: string,
): Promise<ReglaSkipLogicRow[]> {
  const db = await openDb();
  // Reglas que afectan preguntas de este capítulo O el capítulo directamente
  return db.getAllAsync<ReglaSkipLogicRow>(
    `SELECT r.* FROM reglas_skip_logic r
     LEFT JOIN preguntas p ON p.id = r.pregunta_afectada_id
     WHERE r.instrumento_id = ?
       AND (p.capitulo_id = ? OR r.capitulo_afectado_id = ?)`,
    [instrumentoId, capituloId, capituloId],
  );
}
