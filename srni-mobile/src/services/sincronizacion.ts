// Sincronización offline → servidor: cola con backoff exponencial y bulk de respuestas.
//
// Sprint 18 Fase E: eliminada descargarInstrumento (los instrumentos viven en
// bundle/memoria, no se descargan más). Solo queda la lógica de sincronización
// de respuestas/hogares/sesiones (la cola).
import apiClient from '../api/client';
import { hogaresApi } from '../api/hogares';
import { encuestasApi } from '../api/encuestas';
import type { ResponderPayload } from '../api/encuestas';
import { victimasApi } from '../api/victimas';
import type { AgregarMiembroPayload } from '../api/hogares';
import type { VictimaResumenFuente } from '../types';
import * as borradoresDao from '../db/borradoresDao';
import { openDb } from '../db/schema';
import * as hogaresOfflineDao from '../db/hogaresOfflineDao';
import * as victimasOfflineDao from '../db/victimasOfflineDao';
import * as miembrosOfflineDao from '../db/miembrosOfflineDao';
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

// ─────────────────────────────────────────────────────────────────────────────
// Procesadores por tipo de operación
// ─────────────────────────────────────────────────────────────────────────────

async function procesarRegistrarVictima(item: colaDao.ColaItem): Promise<void> {
  // Fase A: registra en el servidor la víctima autorizada creada offline y
  // remapea su UUID local → victima_id servidor en los CREAR_HOGAR pendientes.
  const payload = JSON.parse(item.payload) as {
    id_local: string;
    victima: VictimaResumenFuente;
  };

  const { data } = await victimasApi.registrarDesdeFuente(payload.victima);

  await victimasOfflineDao.marcarSincronizado(payload.id_local, data.victima_id);

  const db = await openDb();
  // Actualizar el `autorizado` en CREAR_HOGAR pendientes que apuntan al UUID local.
  const itemsHogar = await db.getAllAsync<{ id: number; payload: string }>(
    "SELECT id, payload FROM cola_sincronizacion WHERE tipo = 'CREAR_HOGAR' AND estado = 'pendiente'",
  );
  for (const h of itemsHogar) {
    const p = JSON.parse(h.payload);
    if (p.autorizado === payload.id_local) {
      p.autorizado = data.victima_id;
      await db.runAsync(
        'UPDATE cola_sincronizacion SET payload = ? WHERE id = ?',
        [JSON.stringify(p), h.id],
      );
    }
  }
}

async function procesarCrearHogar(item: colaDao.ColaItem): Promise<void> {
  // Sprint 12: el backend renombró 'jefe_hogar' → 'autorizado'.
  // Aceptamos ambos en el payload por compatibilidad con items viejos
  // ya encolados antes del fix del Sprint 17.
  const payload = JSON.parse(item.payload) as {
    id_local: string;
    autorizado?: string;
    jefe_hogar?: string;          // legado — items encolados antes del Sprint 17
    municipio?: number;
    tipo_vivienda?: string;
    condicion_ocupacion?: string;
    estrato?: number;
    numero_cuartos?: number;
    numero_personas?: number;
    observaciones?: string;
  };

  const autorizado = payload.autorizado ?? payload.jefe_hogar;
  if (!autorizado) {
    throw new Error('Payload sin autorizado/jefe_hogar — hogar inválido');
  }

  const db = await openDb();

  // Fase A: si el autorizado sigue siendo un UUID local (la víctima aún no se
  // registró en el servidor), esperar a que corra REGISTRAR_VICTIMA primero.
  // El error es reintentable (no es 4xx), así que la cola lo reintenta con backoff.
  const victimaLocal = await db.getFirstAsync<{ id_local: string }>(
    "SELECT id_local FROM victimas_offline WHERE id_local = ? AND estado_sync != 'enviado'",
    [autorizado],
  );
  if (victimaLocal) {
    throw new Error('autorizado aún no registrado en servidor — esperando REGISTRAR_VICTIMA');
  }

  const { data } = await hogaresApi.crear({
    autorizado,
    municipio: payload.municipio,
    tipo_vivienda: payload.tipo_vivienda,
    condicion_ocupacion: payload.condicion_ocupacion,
    estrato: payload.estrato,
    numero_cuartos: payload.numero_cuartos,
    numero_personas: payload.numero_personas,
    observaciones: payload.observaciones,
  });

  await hogaresOfflineDao.marcarSincronizado(payload.id_local, data.id);

  await db.runAsync(
    'UPDATE borradores SET hogar_id = ? WHERE hogar_id = ?',
    [data.id, payload.id_local],
  );

  // Actualizar referencias hogar local → servidor en CREAR_SESION y
  // AGREGAR_MIEMBRO pendientes (ambos llevan el hogar por su id_local).
  for (const tipo of ['CREAR_SESION', 'AGREGAR_MIEMBRO']) {
    const items = await db.getAllAsync<{ id: number; payload: string }>(
      "SELECT id, payload FROM cola_sincronizacion WHERE tipo = ? AND estado = 'pendiente'",
      [tipo],
    );
    for (const s of items) {
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
}

async function procesarAgregarMiembro(item: colaDao.ColaItem): Promise<void> {
  // Fase A: agrega un integrante al hogar. `hogar` ya fue remapeado a su id de
  // servidor por procesarCrearHogar; si aún es un id_local, esperamos al hogar.
  const payload = JSON.parse(item.payload) as {
    id_local: string;
    hogar: string;
    miembro: AgregarMiembroPayload;
  };

  const db = await openDb();
  const hogarLocal = await db.getFirstAsync<{ id_local: string }>(
    "SELECT id_local FROM hogares_offline WHERE id_local = ? AND estado_sync != 'enviado'",
    [payload.hogar],
  );
  if (hogarLocal) {
    throw new Error('hogar aún no creado en servidor — esperando CREAR_HOGAR');
  }

  const { data } = await hogaresApi.agregarMiembro(payload.hogar, payload.miembro);
  await miembrosOfflineDao.marcarSincronizado(payload.id_local, data.id);
}

async function procesarCrearSesion(item: colaDao.ColaItem): Promise<void> {
  const payload = JSON.parse(item.payload) as {
    borrador_id: string;
    hogar: string;
    instrumento: string;
    ruta_entrevista?: string;
  };

  const { data } = await encuestasApi.crear({
    hogar: payload.hogar,
    instrumento: payload.instrumento,
    ruta_entrevista: payload.ruta_entrevista ?? 'GENERAL',
  });

  await borradoresDao.marcarSincronizado(payload.borrador_id, data.id);

  const db = await openDb();

  // Inyectar sesion_id en RESPONDER_BULK/RESPONDER_PREGUNTA pendientes de este borrador
  for (const tipo of ['RESPONDER_BULK', 'RESPONDER_PREGUNTA', 'FINALIZAR_SESION']) {
    const items = await db.getAllAsync<{ id: number; payload: string }>(
      `SELECT id, payload FROM cola_sincronizacion WHERE tipo = ? AND estado = 'pendiente'`,
      [tipo],
    );
    for (const r of items) {
      const p = JSON.parse(r.payload);
      if (p.borrador_id === payload.borrador_id) {
        p.sesion_id = data.id;
        await db.runAsync(
          'UPDATE cola_sincronizacion SET payload = ? WHERE id = ?',
          [JSON.stringify(p), r.id],
        );
      }
    }
  }
}

async function procesarResponderBulk(item: colaDao.ColaItem): Promise<void> {
  const payload = JSON.parse(item.payload) as {
    sesion_id: string;
    borrador_id: string;
    respuestas: ResponderPayload[];
  };

  if (!payload.sesion_id) {
    throw new Error('sesion_id no disponible aún — esperando CREAR_SESION');
  }

  // Defensiva: r.valor puede no ser string si la cola tiene items viejos
  const respuestas = payload.respuestas.filter(r => {
    const v = r.valor;
    return v !== undefined && v !== null && String(v).trim() !== '';
  });
  if (respuestas.length === 0) return;

  await encuestasApi.responderBulk(payload.sesion_id, respuestas);
}

async function procesarResponder(item: colaDao.ColaItem): Promise<void> {
  const payload = JSON.parse(item.payload) as {
    sesion_id: string;
    pregunta_id: string;
    /** Sprint 21: presente cuando la pregunta es PERSONA. */
    miembro_id?: string | null;
    valor: string;
  };

  if (!payload.sesion_id) {
    throw new Error('sesion_id no disponible aún — esperando CREAR_SESION');
  }

  await encuestasApi.responder(payload.sesion_id, {
    pregunta_id: payload.pregunta_id,
    miembro_id: payload.miembro_id ?? null,
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
  REGISTRAR_VICTIMA:  procesarRegistrarVictima,
  CREAR_HOGAR:        procesarCrearHogar,
  AGREGAR_MIEMBRO:    procesarAgregarMiembro,
  CREAR_SESION:       procesarCrearSesion,
  RESPONDER_BULK:     procesarResponderBulk,
  RESPONDER_PREGUNTA: procesarResponder,
  FINALIZAR_SESION:   procesarFinalizar,
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
 * Intenta sincronizar todos los items pendientes de la cola cuyo retry_after ya venció.
 * Se detiene si detecta que el servidor no es alcanzable.
 * Al terminar con éxito, limpia los items ya enviados.
 */
export async function intentarSincronizar(): Promise<ResultadoSync> {
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
      errores++;
      const status = err?.response?.status as number | undefined;
      const mensaje = err?.message ?? 'Error desconocido';

      if (status !== undefined && status !== 0 && status >= 400 && status < 500 && status !== 429) {
        // Error de cliente — no reintentable (datos inválidos)
        const detalle = JSON.stringify(err?.response?.data ?? mensaje).slice(0, 300);
        await colaDao.marcarError(item.id, `${status}: ${detalle}`);
      } else if (status !== undefined && status !== 0) {
        // 5xx o 429 — reintentable con backoff
        await colaDao.marcarError(item.id, `${status}: ${mensaje}`);
      } else if (err?.isAxiosError || err?.request) {
        // Error de red real (petición salió pero no hubo respuesta del servidor):
        // frenar la pasada entera — los demás items también fallarían.
        await colaDao.marcarError(item.id, 'Sin conexión');
        sinRed = true;
      } else {
        // Error local (JSON.parse de payload corrupto, bug del procesador, etc.).
        // NO es falta de red: marcar solo este item y seguir con los demás,
        // de lo contrario un único item corrupto bloquearía la cola para siempre.
        await colaDao.marcarError(item.id, `Dato local inválido: ${mensaje}`.slice(0, 500));
      }
    }
  }

  // Limpiar enviados para no acumular basura
  if (procesados > 0) {
    await colaDao.limpiarEnviados();
  }

  const pendientesRestantes = await colaDao.contarPendientes();
  return { procesados, errores, pendientes: pendientesRestantes };
}
