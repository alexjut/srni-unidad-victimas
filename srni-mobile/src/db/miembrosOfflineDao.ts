/**
 * DAO para integrantes del hogar agregados OFFLINE (Fase A).
 *
 * Cuando no hay red, no se puede llamar a POST hogares/{id}/agregar-miembro/.
 * Guardamos el miembro localmente vinculado al hogar por su id_local y encolamos
 * AGREGAR_MIEMBRO. Al sincronizar, tras crear el hogar en el servidor, se remapea
 * hogar_id_local → id_servidor en el payload pendiente (igual que CREAR_SESION).
 *
 * SEGURIDAD: payload_json contiene PII del integrante (nombre, documento). Es el
 * mismo dato que ya viaja en memoria en el flujo online. Cifrado en reposo:
 * pendiente (ver docs/offline-cifrado-reposo.md).
 */
import { openDb } from './schema';
import { uuidv4 } from '../utils/uuid';
import type { AgregarMiembroPayload } from '../api/hogares';
import type { MiembroHogarResumen } from '../types';
import * as hogaresOfflineDao from './hogaresOfflineDao';
import * as victimasOfflineDao from './victimasOfflineDao';

export interface MiembroOfflineRow {
  id_local: string;
  id_servidor: string | null;
  hogar_id_local: string;
  payload_json: string;
  estado_sync: 'pendiente' | 'enviando' | 'enviado' | 'error';
  created_at: string;
  updated_at: string;
}

/**
 * Guarda un integrante offline vinculado al hogar (por su id_local). Devuelve el
 * id_local del miembro generado.
 */
export async function crearMiembroOffline(
  hogarIdLocal: string,
  payload: AgregarMiembroPayload,
): Promise<MiembroOfflineRow> {
  const db = await openDb();
  const now = new Date().toISOString();
  const idLocal = uuidv4();

  const row: MiembroOfflineRow = {
    id_local: idLocal,
    id_servidor: null,
    hogar_id_local: hogarIdLocal,
    payload_json: JSON.stringify(payload),
    estado_sync: 'pendiente',
    created_at: now,
    updated_at: now,
  };

  await db.runAsync(
    `INSERT INTO miembros_offline
       (id_local, id_servidor, hogar_id_local, payload_json, estado_sync, created_at, updated_at)
     VALUES (?, NULL, ?, ?, 'pendiente', ?, ?)`,
    [row.id_local, row.hogar_id_local, row.payload_json, now, now],
  );

  return row;
}

/** Integrantes offline de un hogar (por id_local del hogar), en orden de creación. */
export async function listarPorHogar(hogarIdLocal: string): Promise<MiembroOfflineRow[]> {
  const db = await openDb();
  return db.getAllAsync<MiembroOfflineRow>(
    'SELECT * FROM miembros_offline WHERE hogar_id_local = ? ORDER BY created_at',
    [hogarIdLocal],
  );
}

export async function marcarSincronizado(
  idLocal: string,
  idServidor: string,
): Promise<void> {
  const db = await openDb();
  await db.runAsync(
    "UPDATE miembros_offline SET id_servidor = ?, estado_sync = 'enviado', updated_at = ? WHERE id_local = ?",
    [idServidor, new Date().toISOString(), idLocal],
  );
}

export async function marcarError(idLocal: string): Promise<void> {
  const db = await openDb();
  await db.runAsync(
    "UPDATE miembros_offline SET estado_sync = 'error', updated_at = ? WHERE id_local = ?",
    [new Date().toISOString(), idLocal],
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Reconstrucción de la lista de miembros SIN RED (Fase A)
// ─────────────────────────────────────────────────────────────────────────────

const PARENTESCO_LABEL: Record<string, string> = {
  CONYUGE: 'Cónyuge / Compañero/a', HIJO_A: 'Hijo/a', YERNO_NUERA: 'Yerno / Nuera',
  NIETO_A: 'Nieto/a', PADRE_MADRE: 'Padre / Madre', HERMANO_A: 'Hermano/a',
  OTRO_PARIENTE: 'Otro pariente', NO_PARIENTE: 'No pariente',
};
const ROL_LABEL: Record<string, string> = {
  MIEMBRO: 'Miembro del hogar', TUTOR: 'Tutor', CUIDADOR_PERMANENTE: 'Cuidador permanente',
};

/** Construye un MiembroHogarResumen completo a partir de campos parciales. */
function resumen(parcial: Partial<MiembroHogarResumen> & { id: string }): MiembroHogarResumen {
  return {
    id: parcial.id,
    nombre_completo: parcial.nombre_completo ?? '',
    parentesco: (parcial.parentesco ?? '') as MiembroHogarResumen['parentesco'],
    parentesco_display: parcial.parentesco_display ?? '',
    genero: (parcial.genero ?? 'ND') as MiembroHogarResumen['genero'],
    fecha_nacimiento: parcial.fecha_nacimiento ?? null,
    rol: (parcial.rol ?? 'MIEMBRO') as MiembroHogarResumen['rol'],
    rol_display: parcial.rol_display ?? '',
    es_autorizado: parcial.es_autorizado ?? false,
    // Sin dato ⇒ 'NO_VERIFICADO': un miembro guardado offline no se cruzó contra
    // el padrón, y 'NO_INCLUIDO' afirmaría una verificación que no ocurrió.
    estado_inclusion: (parcial.estado_inclusion ?? 'NO_VERIFICADO') as MiembroHogarResumen['estado_inclusion'],
    estado_inclusion_display: parcial.estado_inclusion_display ?? '',
    tipo_persona: parcial.tipo_persona ?? '',
    incluido_ruv: parcial.incluido_ruv ?? false,
    tiene_discapacidad: parcial.tiene_discapacidad ?? false,
    victima: parcial.victima ?? null,
    victima_hash: parcial.victima_hash ?? null,
  };
}

/**
 * Reconstruye la lista COMPLETA de miembros de un hogar creado offline, leyendo
 * solo de SQLite (sin red). Incluye:
 *   - el AUTORIZADO (desde hogares_offline.jefe_hogar_uuid + victimas_offline),
 *     usando su id_local de víctima como id de miembro — la sincronización lo
 *     remapea al id de MiembroHogar del servidor (procesarCrearHogar).
 *   - los INTEGRANTES adicionales (miembros_offline), usando su id_local —
 *     remapeado por procesarAgregarMiembro.
 *
 * Así las preguntas PERSONA se pueden capturar 100% offline y las respuestas
 * quedan ligadas a un miembro_id que el servidor reconoce tras sincronizar.
 */
export async function construirMiembrosOffline(
  hogarIdLocal: string,
): Promise<MiembroHogarResumen[]> {
  const out: MiembroHogarResumen[] = [];

  const hogar = await hogaresOfflineDao.obtenerPorIdLocal(hogarIdLocal);
  if (hogar) {
    let nombre = '';
    try {
      const vic = await victimasOfflineDao.obtenerPorIdLocal(hogar.jefe_hogar_uuid);
      if (vic) {
        const v = JSON.parse(vic.payload_json) as Record<string, string>;
        nombre = [v.primer_nombre, v.segundo_nombre, v.primer_apellido, v.segundo_apellido]
          .filter(Boolean).join(' ');
      }
    } catch { /* sin datos de víctima offline (autorizado del RNI): nombre vacío */ }
    out.push(resumen({
      id: hogar.jefe_hogar_uuid,
      nombre_completo: nombre,
      es_autorizado: true,
      rol_display: 'Autorizado',
    }));
  }

  const adicionales = await listarPorHogar(hogarIdLocal);
  for (const m of adicionales) {
    let p: Record<string, string> = {};
    try { p = JSON.parse(m.payload_json); } catch { /* payload corrupto */ }
    out.push(resumen({
      id: m.id_local,
      nombre_completo: p.nombre_completo ?? '',
      parentesco: p.parentesco as MiembroHogarResumen['parentesco'],
      parentesco_display: PARENTESCO_LABEL[p.parentesco] ?? p.parentesco ?? '',
      genero: p.genero as MiembroHogarResumen['genero'],
      fecha_nacimiento: p.fecha_nacimiento ?? null,
      rol: p.rol as MiembroHogarResumen['rol'],
      rol_display: ROL_LABEL[p.rol] ?? 'Miembro del hogar',
      estado_inclusion: p.estado_inclusion as MiembroHogarResumen['estado_inclusion'],
    }));
  }

  return out;
}
