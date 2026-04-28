// Sincronización offline → servidor: cola de operaciones con reintentos y resolución de conflictos.
import apiClient from '../api/client';
import { hogaresApi } from '../api/hogares';
import { encuestasApi } from '../api/encuestas';
import * as instrumentoDao from '../db/instrumentoDao';
import * as borradoresDao from '../db/borradoresDao';
import { openDb } from '../db/schema';
import * as hogaresOfflineDao from '../db/hogaresOfflineDao';
import * as colaDao from '../db/colaDao';
import type { TipoOperacion } from '../db/colaDao';

// ─────────────────────────────────────────────────────────────────────────────

/** Devuelve true si el backend es alcanzable en este momento. */
export async function estaOnline(): Promise<boolean> {
  try {
    await apiClient.get('/health/', { timeout: 4000 });
    return true;
  } catch {
    return false;
  }
}

/**
 * Descarga el instrumento activo y lo guarda en SQLite.
 * Si ya existe una versión local, solo descarga si la versión del servidor
 * es diferente.
 */
export async function descargarInstrumento(): Promise<boolean> {
  try {
    // Obtener lista de instrumentos vigentes
    const { data } = await apiClient.get<{
      results: Array<{ id: number; version: string; vigente: boolean; codigo: string }>;
    }>('/api/formulario/instrumentos/', { params: { vigente: true } });

    const activo = data.results.find((i) => i.vigente) ?? data.results[0];
    if (!activo) return false;

    // Comprobar si ya tenemos esa versión
    const meta = await instrumentoDao.getMeta();
    if (meta?.instrumento_id === activo.id && meta?.version === activo.version) {
      return false; // Nada que descargar
    }

    // Descargar instrumento completo con temas y preguntas
    const { data: instrumento } = await apiClient.get(
      `/api/formulario/instrumentos/${activo.id}/`,
    );
    await instrumentoDao.guardarInstrumento(instrumento);
    return true;
  } catch {
    return false;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Procesadores por tipo de operación
// ─────────────────────────────────────────────────────────────────────────────

async function procesarCrearHogar(item: colaDao.ColaItem): Promise<void> {
  const payload = JSON.parse(item.payload) as {
    id_local: string;
    jefe_hogar: string;
    municipio?: number;
    tipo_vivienda?: string;
    condicion_ocupacion?: string;
    estrato?: number;
    numero_cuartos?: number;
    numero_personas?: number;
    observaciones?: string;
  };

  const { data } = await hogaresApi.crear({
    jefe_hogar: payload.jefe_hogar,
    municipio: payload.municipio,
    tipo_vivienda: payload.tipo_vivienda,
    condicion_ocupacion: payload.condicion_ocupacion,
    estrato: payload.estrato,
    numero_cuartos: payload.numero_cuartos,
    numero_personas: payload.numero_personas,
    observaciones: payload.observaciones,
  });

  // Actualizar el UUID local con el del servidor en hogares_offline y borradores
  await hogaresOfflineDao.marcarSincronizado(payload.id_local, data.id);

  // Actualizar todos los borradores que referencian este hogar local
  const db = await openDb();
  await db.runAsync(
    'UPDATE borradores SET hogar_id = ? WHERE hogar_id = ?',
    [data.id, payload.id_local],
  );

  // Actualizar el payload de los items CREAR_SESION que usen el id_local
  const itemsSesion = await db.getAllAsync<{ id: number; payload: string }>(
    "SELECT id, payload FROM cola_sincronizacion WHERE tipo = 'CREAR_SESION' AND estado = 'pendiente'",
  );
  for (const s of itemsSesion) {
    const p = JSON.parse(s.payload);
    if (p.hogar === payload.id_local) {
      p.hogar = data.id;
      await db.runAsync(
        'UPDATE cola_sincronizacion SET payload = ? WHERE id = ?',
        [JSON.stringify(p), s.id],
      );
    }
  }
}

async function procesarCrearSesion(item: colaDao.ColaItem): Promise<void> {
  const payload = JSON.parse(item.payload) as {
    borrador_id: string;
    hogar: string;
    instrumento: number;
  };

  const { data } = await encuestasApi.crear({
    hogar: payload.hogar,
    instrumento: payload.instrumento,
  });

  await borradoresDao.marcarSincronizado(payload.borrador_id, data.id);

  // Actualizar items de respuestas que referencien este borrador
  const db = await openDb();
  const itemsResp = await db.getAllAsync<{ id: number; payload: string }>(
    "SELECT id, payload FROM cola_sincronizacion WHERE tipo = 'RESPONDER_PREGUNTA' AND estado = 'pendiente'",
  );
  for (const r of itemsResp) {
    const p = JSON.parse(r.payload);
    if (p.borrador_id === payload.borrador_id) {
      p.sesion_id = data.id;
      await db.runAsync(
        'UPDATE cola_sincronizacion SET payload = ? WHERE id = ?',
        [JSON.stringify(p), r.id],
      );
    }
  }

  // Lo mismo para FINALIZAR_SESION
  const itemsFin = await db.getAllAsync<{ id: number; payload: string }>(
    "SELECT id, payload FROM cola_sincronizacion WHERE tipo = 'FINALIZAR_SESION' AND estado = 'pendiente'",
  );
  for (const f of itemsFin) {
    const p = JSON.parse(f.payload);
    if (p.borrador_id === payload.borrador_id) {
      p.sesion_id = data.id;
      await db.runAsync(
        'UPDATE cola_sincronizacion SET payload = ? WHERE id = ?',
        [JSON.stringify(p), f.id],
      );
    }
  }
}

async function procesarResponder(item: colaDao.ColaItem): Promise<void> {
  const payload = JSON.parse(item.payload) as {
    sesion_id: string;
    pregunta_id: number;
    valor: string;
  };

  if (!payload.sesion_id) {
    throw new Error('sesion_id no disponible aún — esperando CREAR_SESION');
  }

  await encuestasApi.responder(payload.sesion_id, {
    pregunta_id: payload.pregunta_id,
    valor: payload.valor,
  });
}

async function procesarFinalizar(item: colaDao.ColaItem): Promise<void> {
  const payload = JSON.parse(item.payload) as {
    sesion_id: string;
    borrador_id: string;
    observaciones?: string;
  };

  if (!payload.sesion_id) {
    throw new Error('sesion_id no disponible aún — esperando CREAR_SESION');
  }

  await encuestasApi.finalizar(payload.sesion_id, {
    observaciones: payload.observaciones,
  });

  await borradoresDao.marcarCompletado(payload.borrador_id);
}

const PROCESADORES: Record<TipoOperacion, (item: colaDao.ColaItem) => Promise<void>> = {
  CREAR_HOGAR: procesarCrearHogar,
  CREAR_SESION: procesarCrearSesion,
  RESPONDER_PREGUNTA: procesarResponder,
  FINALIZAR_SESION: procesarFinalizar,
};

// ─────────────────────────────────────────────────────────────────────────────
// Orquestador principal
// ─────────────────────────────────────────────────────────────────────────────

export interface ResultadoSync {
  procesados: number;
  errores: number;
  pendientes: number;
}

/**
 * Intenta sincronizar todos los items pendientes de la cola.
 * Se detiene si detecta que el servidor no es alcanzable.
 */
export async function intentarSincronizar(): Promise<ResultadoSync> {
  // Liberar items bloqueados de sesiones anteriores
  await colaDao.resetearBloqueados();

  const pendientes = await colaDao.obtenerPendientes();
  if (pendientes.length === 0) {
    return { procesados: 0, errores: 0, pendientes: 0 };
  }

  let procesados = 0;
  let errores = 0;
  let sinRed = false;

  for (const item of pendientes) {
    if (sinRed) break;

    await colaDao.marcarEnviando(item.id);
    const procesador = PROCESADORES[item.tipo];

    if (!procesador) {
      await colaDao.marcarError(item.id, `Tipo desconocido: ${item.tipo}`);
      errores++;
      continue;
    }

    try {
      await procesador(item);
      await colaDao.marcarEnviado(item.id);
      procesados++;
    } catch (err: any) {
      const status = err?.response?.status as number | undefined;
      const mensaje = err?.message ?? 'Error desconocido';

      if (status === undefined || status === 0) {
        // Sin conexión — no tiene sentido seguir
        await colaDao.marcarError(item.id, 'Sin conexión');
        sinRed = true;
        errores++;
      } else if (status >= 400 && status < 500 && status !== 429) {
        // Error del cliente — no reintentar (datos inválidos)
        const detalle = JSON.stringify(err?.response?.data ?? mensaje).slice(0, 300);
        await colaDao.marcarError(item.id, `${status}: ${detalle}`);
        errores++;
      } else {
        // 5xx o 429 — reintentable
        await colaDao.marcarError(item.id, `${status ?? 'red'}: ${mensaje}`);
        errores++;
      }
    }
  }

  const pendientesRestantes = await colaDao.contarPendientes();
  return { procesados, errores, pendientes: pendientesRestantes };
}
