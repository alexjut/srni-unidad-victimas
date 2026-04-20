/**
 * DAO para hogares creados offline.
 *
 * SEGURIDAD: jefe_hogar_uuid es el UUID de la Victima en el servidor.
 * Es una referencia opaca — no contiene nombre ni documento.
 */
import { openDb } from './schema';
import { uuidv4 } from '../utils/uuid';

export interface HogarOfflineRow {
  id_local: string;
  id_servidor: string | null;
  jefe_hogar_uuid: string;
  municipio_id: number | null;
  tipo_vivienda: string;
  condicion_ocupacion: string;
  estrato: number;
  numero_cuartos: number;
  numero_personas: number;
  observaciones: string;
  estado_sync: 'pendiente' | 'enviando' | 'enviado' | 'error';
  created_at: string;
  updated_at: string;
}

export interface CrearHogarOfflineInput {
  jefe_hogar_uuid: string;
  municipio_id?: number;
  tipo_vivienda?: string;
  condicion_ocupacion?: string;
  estrato?: number;
  numero_cuartos?: number;
  numero_personas?: number;
  observaciones?: string;
}

// ─────────────────────────────────────────────────────────────────────────────

export async function crearHogarOffline(
  input: CrearHogarOfflineInput,
): Promise<HogarOfflineRow> {
  const db = await openDb();
  const now = new Date().toISOString();
  const idLocal = uuidv4();

  const row: HogarOfflineRow = {
    id_local: idLocal,
    id_servidor: null,
    jefe_hogar_uuid: input.jefe_hogar_uuid,
    municipio_id: input.municipio_id ?? null,
    tipo_vivienda: input.tipo_vivienda ?? '',
    condicion_ocupacion: input.condicion_ocupacion ?? '',
    estrato: input.estrato ?? 0,
    numero_cuartos: input.numero_cuartos ?? 0,
    numero_personas: input.numero_personas ?? 1,
    observaciones: input.observaciones ?? '',
    estado_sync: 'pendiente',
    created_at: now,
    updated_at: now,
  };

  await db.runAsync(
    `INSERT INTO hogares_offline
       (id_local, id_servidor, jefe_hogar_uuid, municipio_id, tipo_vivienda,
        condicion_ocupacion, estrato, numero_cuartos, numero_personas,
        observaciones, estado_sync, created_at, updated_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pendiente', ?, ?)`,
    [
      row.id_local, null, row.jefe_hogar_uuid, row.municipio_id,
      row.tipo_vivienda, row.condicion_ocupacion, row.estrato,
      row.numero_cuartos, row.numero_personas, row.observaciones,
      now, now,
    ],
  );

  return row;
}

export async function listarPendientes(): Promise<HogarOfflineRow[]> {
  const db = await openDb();
  return db.getAllAsync<HogarOfflineRow>(
    "SELECT * FROM hogares_offline WHERE estado_sync IN ('pendiente', 'error') ORDER BY created_at",
  );
}

export async function listarTodos(): Promise<HogarOfflineRow[]> {
  const db = await openDb();
  return db.getAllAsync<HogarOfflineRow>(
    'SELECT * FROM hogares_offline ORDER BY created_at DESC',
  );
}

export async function marcarSincronizado(
  idLocal: string,
  idServidor: string,
): Promise<void> {
  const db = await openDb();
  await db.runAsync(
    "UPDATE hogares_offline SET id_servidor = ?, estado_sync = 'enviado', updated_at = ? WHERE id_local = ?",
    [idServidor, new Date().toISOString(), idLocal],
  );
}

export async function marcarError(idLocal: string, mensaje: string): Promise<void> {
  const db = await openDb();
  await db.runAsync(
    "UPDATE hogares_offline SET estado_sync = 'error', updated_at = ? WHERE id_local = ?",
    [new Date().toISOString(), idLocal],
  );
}
