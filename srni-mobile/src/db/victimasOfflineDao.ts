/**
 * DAO para víctimas registradas OFFLINE (Fase A).
 *
 * Cuando no hay red, no se puede llamar a POST registrar-desde-fuente/, así que
 * generamos un id_local (UUID) que actúa como `autorizado` del hogar y guardamos
 * el VictimaResumenFuente COMPLETO para re-registrarlo al recuperar señal. Al
 * sincronizar, el servidor devuelve victima_id y remapeamos id_local → id_servidor
 * en el payload de CREAR_HOGAR pendiente (mismo patrón que hogares→sesiones).
 *
 * SEGURIDAD: payload_json contiene PII (es el mismo dato que ya viaja en memoria
 * en el flujo online). Cifrado en reposo: pendiente (ver docs/offline-cifrado-reposo.md).
 */
import { openDb } from './schema';
import { uuidv4 } from '../utils/uuid';
import type { VictimaResumenFuente } from '../types';

export interface VictimaOfflineRow {
  id_local: string;
  id_servidor: string | null;
  payload_json: string;
  estado_sync: 'pendiente' | 'enviando' | 'enviado' | 'error';
  created_at: string;
  updated_at: string;
}

/**
 * Crea una víctima offline a partir del VictimaResumenFuente. Devuelve el
 * id_local (UUID) que se usará como `autorizado` del hogar mientras no haya red.
 */
export async function crearVictimaOffline(
  victima: VictimaResumenFuente,
): Promise<VictimaOfflineRow> {
  const db = await openDb();
  const now = new Date().toISOString();
  const idLocal = uuidv4();

  const row: VictimaOfflineRow = {
    id_local: idLocal,
    id_servidor: null,
    payload_json: JSON.stringify(victima),
    estado_sync: 'pendiente',
    created_at: now,
    updated_at: now,
  };

  await db.runAsync(
    `INSERT INTO victimas_offline
       (id_local, id_servidor, payload_json, estado_sync, created_at, updated_at)
     VALUES (?, NULL, ?, 'pendiente', ?, ?)`,
    [row.id_local, row.payload_json, now, now],
  );

  return row;
}

export async function obtenerPorIdLocal(idLocal: string): Promise<VictimaOfflineRow | null> {
  const db = await openDb();
  const row = await db.getFirstAsync<VictimaOfflineRow>(
    'SELECT * FROM victimas_offline WHERE id_local = ?',
    [idLocal],
  );
  return row ?? null;
}

export async function marcarSincronizado(
  idLocal: string,
  idServidor: string,
): Promise<void> {
  const db = await openDb();
  await db.runAsync(
    "UPDATE victimas_offline SET id_servidor = ?, estado_sync = 'enviado', updated_at = ? WHERE id_local = ?",
    [idServidor, new Date().toISOString(), idLocal],
  );
}

export async function marcarError(idLocal: string): Promise<void> {
  const db = await openDb();
  await db.runAsync(
    "UPDATE victimas_offline SET estado_sync = 'error', updated_at = ? WHERE id_local = ?",
    [new Date().toISOString(), idLocal],
  );
}

/**
 * La víctima registrada a mano en este teléfono que tenga este documento, o null.
 *
 * ─── Por qué hace falta ───────────────────────────────────────────────────
 * Corrige un defecto reportado el 11-sep-2026: sin señal, un alta manual quedaba
 * **invisible para la siguiente búsqueda**. `buscarOffline` consulta el padrón
 * precargado y el filtro del universo, y esta tabla solo se escribía, nunca se
 * leía. Buscar otra vez el mismo documento respondía «no está en el padrón» y
 * ofrecía darla de alta de nuevo: la encuestadora reescribía todo y quedaba un
 * SEGUNDO registro de la misma persona encolado para sincronizar.
 *
 * Es el caso que encaja literalmente con «obliga al usuario a ingresarlos
 * nuevamente», y además ensuciaba el padrón con duplicados.
 *
 * ─── Por qué se compara el par completo ───────────────────────────────────
 * Tipo y número juntos: el mismo número puede existir como cédula y como tarjeta
 * de identidad de dos personas distintas, y devolver la equivocada le entregaría
 * al encuestador los datos de otra persona sin que se entere.
 *
 * Se recorre en JavaScript en vez de con un WHERE porque el documento vive dentro
 * de `payload_json` y no como columna. Son las altas manuales pendientes de UN
 * teléfono —decenas, no miles—, así que no vale la pena una migración de esquema
 * por esto.
 */
export async function buscarPorDocumento(
  tipoDocumento: string,
  numeroDocumento: string,
): Promise<{ row: VictimaOfflineRow; victima: VictimaResumenFuente } | null> {
  const db = await openDb();
  const tipo = (tipoDocumento ?? '').trim().toUpperCase();
  const numero = (numeroDocumento ?? '').trim();
  if (!numero) return null;

  const filas = await db.getAllAsync<VictimaOfflineRow>(
    // Las más recientes primero: si por lo que sea hay dos, la última capturada
    // es la que refleja lo que el encuestador acabó de confirmar con la persona.
    'SELECT * FROM victimas_offline ORDER BY created_at DESC',
  );

  for (const row of filas) {
    try {
      const victima = JSON.parse(row.payload_json) as VictimaResumenFuente;
      if (
        (victima.numero_documento ?? '').trim() === numero &&
        (victima.tipo_documento ?? '').trim().toUpperCase() === tipo
      ) {
        return { row, victima };
      }
    } catch {
      // Payload corrupto: se omite. Una fila ilegible no puede impedir encontrar
      // las demás, y el alta se puede repetir — que es peor que esto, pero no
      // tanto como no poder buscar a nadie.
    }
  }
  return null;
}
