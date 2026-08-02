/**
 * DAO del almacén OFFLINE de precarga (Fase 0).
 *
 * Persiste y consulta lo que el endpoint GET /api/victimas/precarga/ entrega:
 *   - padron  → índice ligero de personas (búsqueda por hash de documento)
 *   - jornada → VictimaResumenFuente COMPLETO por documento (json)
 *   - parametricas_cache → municipios / DT / puntos (json por tipo)
 *   - meta_offline → version del padrón + timestamp de última precarga
 *
 * REGLA: el documento se guarda HASHEADO (ver hashDocumento.ts). El display
 * es solo los últimos 4 dígitos. NO se persiste el documento en claro.
 *
 * TODO(cifrado-en-reposo): Fase 0 no cifra el .db. Migrar a SQLCipher en fase
 * posterior con PII real (ver nota en schema.ts MIGRATION_V6).
 */
import { openDb } from './schema';
import { hashDocumento, displayDocumento } from './hashDocumento';
import type { VictimaResumenFuente } from '../types';

// ── Tipos del contrato de precarga ──────────────────────────────────────────

export interface PadronEntradaApi {
  tipo_documento: string;
  documento: string;
  nombre: string;
  ubicacion: string;
  cantidad_hechos: number;
  en_ruv: boolean;
  habilitada: boolean;
  ya_caracterizada: boolean;
  cons_persona: number | null;
  /**
   * Qué hay detrás de este documento cuando lo comparte más de un registro.
   * null = documento limpio; 'AMBIGUO' = personas distintas, hay que preguntar;
   * 'NO_IDENTIFICANTE' = valor de relleno que no identifica a nadie.
   * Opcional: un servidor viejo no lo manda y la app sigue funcionando.
   */
  clase_colision?: string | null;
}

export interface MunicipioParam {
  codigo_dane: string;
  nombre: string;
  departamento: string;
}

export interface PrecargaParametricas {
  municipios?: unknown[];
  direcciones_territoriales?: unknown[];
  puntos_atencion?: unknown[];
}

export interface PrecargaPayload {
  version: string;
  padron: PadronEntradaApi[];
  jornada: VictimaResumenFuente[];
  parametricas: PrecargaParametricas;
}

/** Fila del padrón tal como se devuelve a las pantallas (sin documento en claro). */
export interface PadronRow {
  documento_hash: string;
  tipo_documento: string;
  documento_display: string;
  nombre: string;
  ubicacion: string;
  cantidad_hechos: number;
  en_ruv: boolean;
  habilitada: boolean;
  ya_caracterizada: boolean;
  cons_persona: number | null;
  /** null = documento limpio. 'AMBIGUO' | 'NO_IDENTIFICANTE' — ver schema v10. */
  clase_colision: string | null;
}

interface PadronRowDb {
  documento_hash: string;
  tipo_documento: string;
  documento_display: string;
  nombre: string;
  ubicacion: string;
  cantidad_hechos: number;
  en_ruv: number;
  habilitada: number;
  ya_caracterizada: number;
  cons_persona: number | null;
  clase_colision: string | null;
}

function mapPadron(r: PadronRowDb): PadronRow {
  return {
    documento_hash: r.documento_hash,
    tipo_documento: r.tipo_documento,
    documento_display: r.documento_display,
    nombre: r.nombre,
    ubicacion: r.ubicacion,
    cantidad_hechos: r.cantidad_hechos,
    en_ruv: r.en_ruv === 1,
    habilitada: r.habilitada === 1,
    ya_caracterizada: r.ya_caracterizada === 1,
    cons_persona: r.cons_persona,
    clase_colision: r.clase_colision ?? null,
  };
}

// ── Escritura (precarga) ────────────────────────────────────────────────────

/**
 * Persiste TODO el payload de precarga de forma transaccional. Reemplaza el
 * contenido previo de padron/jornada/parametricas (la precarga es la verdad).
 */
export async function guardarPrecarga(payload: PrecargaPayload): Promise<void> {
  const db = await openDb();

  await db.withTransactionAsync(async () => {
    await db.execAsync('DELETE FROM padron; DELETE FROM jornada;');

    // Inserción por LOTES con statement preparado: una sola preparación del
    // INSERT reutilizada por fila (executeAsync). Evita N round-trips de parseo
    // a SQLite, crítico al login con miles de filas. Sigue siendo transaccional
    // y el resultado es idéntico (mismo orden de columnas, mismos hash/display).
    // INSERT a secas, ya no `OR REPLACE`: dos personas distintas pueden compartir
    // documento y las dos tienen que entrar. Con `OR REPLACE` la segunda pisaba a
    // la primera y esa víctima desaparecía del dispositivo sin dejar rastro.
    // La tabla se vacía al principio de la precarga, así que no hay que temer
    // duplicados de una corrida anterior.
    const stmtPadron = await db.prepareAsync(
      `INSERT INTO padron
         (documento_hash, tipo_documento, documento_display, nombre, ubicacion,
          cantidad_hechos, en_ruv, habilitada, ya_caracterizada, cons_persona,
          clase_colision)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    );
    try {
      for (const p of payload.padron ?? []) {
        const hash = hashDocumento(p.documento);
        await stmtPadron.executeAsync([
          hash,
          p.tipo_documento ?? '',
          displayDocumento(p.documento),
          p.nombre ?? '',
          p.ubicacion ?? '',
          p.cantidad_hechos ?? 0,
          p.en_ruv ? 1 : 0,
          p.habilitada ? 1 : 0,
          p.ya_caracterizada ? 1 : 0,
          p.cons_persona ?? null,
          p.clase_colision ?? null,
        ]);
      }
    } finally {
      await stmtPadron.finalizeAsync();
    }

    const stmtJornada = await db.prepareAsync(
      `INSERT OR REPLACE INTO jornada (documento_hash, json) VALUES (?, ?)`,
    );
    try {
      for (const v of payload.jornada ?? []) {
        const hash = hashDocumento(v.numero_documento);
        await stmtJornada.executeAsync([hash, JSON.stringify(v)]);
      }
    } finally {
      await stmtJornada.finalizeAsync();
    }

    const param = payload.parametricas ?? {};
    const tipos: [string, unknown[] | undefined][] = [
      ['municipios', param.municipios],
      ['direcciones_territoriales', param.direcciones_territoriales],
      ['puntos_atencion', param.puntos_atencion],
    ];
    for (const [tipo, lista] of tipos) {
      if (!lista) continue;
      await db.runAsync(
        `INSERT OR REPLACE INTO parametricas_cache (tipo, json) VALUES (?, ?)`,
        [tipo, JSON.stringify(lista)],
      );
    }

    await db.runAsync(
      `INSERT OR REPLACE INTO meta_offline (clave, valor) VALUES ('padron_version', ?)`,
      [payload.version ?? ''],
    );
    await db.runAsync(
      `INSERT OR REPLACE INTO meta_offline (clave, valor) VALUES ('precarga_at', ?)`,
      [new Date().toISOString()],
    );
  });
}

// ── Lectura ──────────────────────────────────────────────────────────────────

/**
 * Busca una persona en el padrón local por el documento tecleado.
 *
 * ⚠️ Devuelve la PRIMERA coincidencia. Un documento puede pertenecer a más de
 * una persona (ver `buscarCandidatosEnPadron`), así que esto solo es correcto
 * cuando ya se sabe que el documento es limpio. Para el flujo de búsqueda usar
 * `buscarCandidatosEnPadron`, que no esconde a nadie.
 */
export async function buscarEnPadron(documento: string): Promise<PadronRow | null> {
  const db = await openDb();
  const row = await db.getFirstAsync<PadronRowDb>(
    'SELECT * FROM padron WHERE documento_hash = ?',
    [hashDocumento(documento)],
  );
  return row ? mapPadron(row) : null;
}

/** Qué encontró el padrón local para un documento. */
export interface ResultadoPadron {
  /** Todas las personas registradas con ese documento. Vacío si no hay ninguna. */
  candidatos: PadronRow[];
  /**
   * true cuando el documento es un valor de relleno ('99', '0'): NO identifica a
   * nadie y `candidatos` viene vacío a propósito. No es lo mismo que "no está":
   * la persona puede existir, pero ese número no sirve para encontrarla.
   */
  noIdentificante: boolean;
  /** true cuando hay más de una persona y el encuestador tiene que elegir. */
  requiereConfirmacion: boolean;
}

/**
 * Busca en el padrón local devolviendo TODAS las personas con ese documento.
 *
 * Por qué no alcanza con la primera: en el padrón real hay 768.096 documentos
 * repetidos y ~7 % de ellos son personas distintas. Quedarse con una y no decir
 * nada es entregarle al encuestador los datos de otra persona sin que se entere
 * — y sin señal no tiene cómo verificarlo.
 */
export async function buscarCandidatosEnPadron(documento: string): Promise<ResultadoPadron> {
  const db = await openDb();
  const rows = await db.getAllAsync<PadronRowDb>(
    'SELECT * FROM padron WHERE documento_hash = ?',
    [hashDocumento(documento)],
  );

  const noIdentificante = rows.some((r) => r.clase_colision === 'NO_IDENTIFICANTE');
  const candidatos = noIdentificante ? [] : rows.map(mapPadron);

  return {
    candidatos,
    noIdentificante,
    requiereConfirmacion: candidatos.length > 1,
  };
}

/**
 * Devuelve el VictimaResumenFuente COMPLETO si la persona viene en la jornada
 * del día (para continuar el flujo de caracterización offline).
 */
export async function buscarEnJornada(documento: string): Promise<VictimaResumenFuente | null> {
  const db = await openDb();
  const row = await db.getFirstAsync<{ json: string }>(
    'SELECT json FROM jornada WHERE documento_hash = ?',
    [hashDocumento(documento)],
  );
  if (!row) return null;
  try {
    return JSON.parse(row.json) as VictimaResumenFuente;
  } catch {
    return null;
  }
}

/** Lee una lista paramétrica cacheada (municipios / direcciones_territoriales / puntos_atencion). */
export async function leerParametrica<T = unknown>(tipo: string): Promise<T[]> {
  const db = await openDb();
  const row = await db.getFirstAsync<{ json: string }>(
    'SELECT json FROM parametricas_cache WHERE tipo = ?',
    [tipo],
  );
  if (!row) return [];
  try {
    return JSON.parse(row.json) as T[];
  } catch {
    return [];
  }
}

/** Versión del padrón persistida (vacío si nunca se precargó). */
export async function getPadronVersion(): Promise<string> {
  const db = await openDb();
  const row = await db.getFirstAsync<{ valor: string }>(
    "SELECT valor FROM meta_offline WHERE clave = 'padron_version'",
  );
  return row?.valor ?? '';
}

/** true si hay datos de precarga persistidos (padron no vacío). */
export async function hayPrecarga(): Promise<boolean> {
  const db = await openDb();
  const row = await db.getFirstAsync<{ n: number }>('SELECT COUNT(*) AS n FROM padron');
  return (row?.n ?? 0) > 0;
}

/** Cuenta de registros precargados — para el indicador de "listo para campo". */
export async function contarPrecarga(): Promise<{ padron: number; jornada: number }> {
  const db = await openDb();
  const p = await db.getFirstAsync<{ n: number }>('SELECT COUNT(*) AS n FROM padron');
  const j = await db.getFirstAsync<{ n: number }>('SELECT COUNT(*) AS n FROM jornada');
  return { padron: p?.n ?? 0, jornada: j?.n ?? 0 };
}

/** Limpia el almacén offline (al cerrar sesión, por privacidad). */
export async function limpiarPrecarga(): Promise<void> {
  const db = await openDb();
  await db.execAsync(
    'DELETE FROM padron; DELETE FROM jornada; DELETE FROM parametricas_cache; DELETE FROM meta_offline;',
  );
}

/**
 * Borra TODO el almacén offline, incluida la PII capturada (víctimas, miembros,
 * hogares, borradores, respuestas) y la cola. Lo usa logout() SOLO cuando no hay
 * nada pendiente de sincronizar, para que el dispositivo no quede con datos de
 * víctimas del usuario anterior en claro. NUNCA llamar con la cola con pendientes
 * (se perdería trabajo de campo).
 */
export async function limpiarTodoOffline(): Promise<void> {
  const db = await openDb();
  await db.execAsync(
    'DELETE FROM respuestas; DELETE FROM borradores;' +
    ' DELETE FROM victimas_offline; DELETE FROM miembros_offline; DELETE FROM hogares_offline;' +
    ' DELETE FROM cola_sincronizacion;' +
    ' DELETE FROM padron; DELETE FROM jornada; DELETE FROM parametricas_cache; DELETE FROM meta_offline;',
  );
}
