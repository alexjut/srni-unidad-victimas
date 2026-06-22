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

/**
 * Error que indica que un item de la cola espera a que se procese su dependencia
 * (p.ej. RESPONDER_BULK antes de CREAR_SESION). NO es un fallo: el orquestador lo
 * difiere sin gastar reintentos, evitando que la cadena quede trabada en 'error'.
 */
class DependenciaPendiente extends Error {
  readonly esDependenciaPendiente = true;
  constructor(message: string) {
    super(message);
    this.name = 'DependenciaPendiente';
  }
}

/**
 * Reescribe el payload de items pendientes/errados y los reactiva para reintento
 * inmediato con el id ya remapeado (local → servidor). Incluir estado 'error'
 * rescata items que murieron por usar un id local que el servidor rechazaba.
 */
async function reescribirPayloads(
  tipos: string[],
  coincide: (p: any) => boolean,
  mutar: (p: any) => void,
): Promise<void> {
  const db = await openDb();
  for (const tipo of tipos) {
    const items = await db.getAllAsync<{ id: number; payload: string }>(
      "SELECT id, payload FROM cola_sincronizacion WHERE tipo = ? AND estado IN ('pendiente', 'error')",
      [tipo],
    );
    for (const it of items) {
      let p: any;
      try { p = JSON.parse(it.payload); } catch { continue; }
      if (!coincide(p)) continue;
      mutar(p);
      await db.runAsync(
        `UPDATE cola_sincronizacion
           SET payload = ?, estado = 'pendiente', intentos = 0, retry_after = NULL, updated_at = ?
         WHERE id = ?`,
        [JSON.stringify(p), new Date().toISOString(), it.id],
      );
    }
  }
}

/**
 * Remapea un miembro_id local → id de servidor en TODA respuesta encolada
 * (RESPONDER_PREGUNTA top-level y RESPONDER_BULK dentro del array) y en las
 * respuestas ya guardadas en SQLite. Sin esto, las respuestas PERSONA capturadas
 * offline viajaban con el id_local del miembro y el backend las rechazaba (400).
 */
async function remapMiembroEnCola(idLocal: string, idServidor: string): Promise<void> {
  if (!idLocal || idLocal === idServidor) return;
  await reescribirPayloads(
    ['RESPONDER_PREGUNTA'],
    (p) => p.miembro_id === idLocal,
    (p) => { p.miembro_id = idServidor; },
  );
  await reescribirPayloads(
    ['RESPONDER_BULK'],
    (p) => Array.isArray(p.respuestas) && p.respuestas.some((r: any) => r.miembro_id === idLocal),
    (p) => { for (const r of p.respuestas) if (r.miembro_id === idLocal) r.miembro_id = idServidor; },
  );
  await borradoresDao.remapMiembro(idLocal, idServidor);
}

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

  // Remapear el `autorizado` (UUID local → servidor) en CREAR_HOGAR pendientes/errados.
  await reescribirPayloads(
    ['CREAR_HOGAR'],
    (p) => p.autorizado === payload.id_local || p.jefe_hogar === payload.id_local,
    (p) => {
      if (p.autorizado === payload.id_local) p.autorizado = data.victima_id;
      if (p.jefe_hogar === payload.id_local) p.jefe_hogar = data.victima_id;
    },
  );
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
  const victimaLocal = await db.getFirstAsync<{ id_local: string }>(
    "SELECT id_local FROM victimas_offline WHERE id_local = ? AND estado_sync != 'enviado'",
    [autorizado],
  );
  if (victimaLocal) {
    throw new DependenciaPendiente('autorizado aún no registrado en servidor — esperando REGISTRAR_VICTIMA');
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
  // AGREGAR_MIEMBRO pendientes/errados (ambos llevan el hogar por su id_local).
  await reescribirPayloads(
    ['CREAR_SESION', 'AGREGAR_MIEMBRO'],
    (p) => p.hogar === payload.id_local,
    (p) => { p.hogar = data.id; },
  );

  // C3 — remapear el MIEMBRO AUTORIZADO: offline las respuestas PERSONA del
  // autorizado se indexaron con su id local (jefe_hogar_uuid del hogar). El
  // backend crea su MiembroHogar al crear el hogar; tomamos ese id del response
  // (o, defensivamente, del detalle) y remapeamos las respuestas encoladas/SQLite.
  const hogarOff = await hogaresOfflineDao.obtenerPorIdLocal(payload.id_local);
  const claveLocalAutorizado = hogarOff?.jefe_hogar_uuid;
  if (claveLocalAutorizado) {
    let autorizadoMiembroId =
      (data.miembros ?? []).find((m) => m.es_autorizado)?.id ?? null;
    if (!autorizadoMiembroId) {
      try {
        const { data: detalle } = await hogaresApi.detalle(data.id);
        autorizadoMiembroId = (detalle.miembros ?? []).find((m) => m.es_autorizado)?.id ?? null;
      } catch { /* sin detalle: el remapeo del autorizado se hará en un próximo intento */ }
    }
    if (autorizadoMiembroId) {
      await remapMiembroEnCola(claveLocalAutorizado, autorizadoMiembroId);
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
    throw new DependenciaPendiente('hogar aún no creado en servidor — esperando CREAR_HOGAR');
  }

  const { data } = await hogaresApi.agregarMiembro(payload.hogar, payload.miembro);
  await miembrosOfflineDao.marcarSincronizado(payload.id_local, data.id);

  // C3 — las respuestas PERSONA de este integrante se capturaron con su id_local;
  // remapearlas al id de MiembroHogar del servidor para que el bulk no falle (400).
  await remapMiembroEnCola(payload.id_local, data.id);
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

  // Inyectar sesion_id en RESPONDER_BULK/RESPONDER_PREGUNTA/FINALIZAR_SESION
  // pendientes/errados de este borrador.
  await reescribirPayloads(
    ['RESPONDER_BULK', 'RESPONDER_PREGUNTA', 'FINALIZAR_SESION'],
    (p) => p.borrador_id === payload.borrador_id,
    (p) => { p.sesion_id = data.id; },
  );
}

async function procesarResponderBulk(item: colaDao.ColaItem): Promise<void> {
  const payload = JSON.parse(item.payload) as {
    sesion_id: string;
    borrador_id: string;
    respuestas: ResponderPayload[];
  };

  if (!payload.sesion_id) {
    throw new DependenciaPendiente('sesion_id no disponible aún — esperando CREAR_SESION');
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
    throw new DependenciaPendiente('sesion_id no disponible aún — esperando CREAR_SESION');
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
    throw new DependenciaPendiente('sesion_id no disponible aún — esperando CREAR_SESION');
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

// A2 — lock a nivel de módulo: impide que dos disparos casi simultáneos (polling
// de conectividad + AppState + reconexión) procesen la cola a la vez y dupliquen
// recursos en el servidor. El guard del store no basta porque su flag es estado
// React asíncrono.
let sincronizacionEnCurso = false;

/**
 * Intenta sincronizar todos los items pendientes de la cola cuyo retry_after ya venció.
 * Se detiene si detecta que el servidor no es alcanzable.
 * Al terminar con éxito, limpia los items ya enviados.
 */
export async function intentarSincronizar(): Promise<ResultadoSync> {
  if (sincronizacionEnCurso) {
    return { procesados: 0, errores: 0, pendientes: await colaDao.contarPendientes() };
  }
  sincronizacionEnCurso = true;
  try {
    return await ejecutarSincronizacion();
  } finally {
    sincronizacionEnCurso = false;
  }
}

async function ejecutarSincronizacion(): Promise<ResultadoSync> {
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
      // C4 — el item espera una dependencia (su id local aún no se remapeó).
      // No es un fallo: lo devolvemos a 'pendiente' SIN gastar intentos para que
      // no muera en 'error' y trabe la cadena. Se reintenta en la próxima pasada.
      if (err?.esDependenciaPendiente) {
        await colaDao.reencolar(item.id);
        continue;
      }

      const status = err?.response?.status as number | undefined;
      const mensaje = err?.message ?? 'Error desconocido';

      // Transitorios de infraestructura — NUNCA gastar intentos ni mandar a
      // 'error': red caída (sin respuesta) o 429/502/503/504 (servidor saturado/
      // caído). Se DIFIERE con reencolar() (no incrementa intentos) y se frena la
      // pasada (los demás items fallarían igual). Sin esto, una jornada offline
      // larga agota los 3 intentos y manda CREAR_HOGAR/respuestas a 'error'
      // definitivo = pérdida de la cadena entera de un hogar.
      const esRedCaida = (status === undefined || status === 0) && (err?.isAxiosError || err?.request);
      const esInfraTransitoria = status === 429 || status === 502 || status === 503 || status === 504;
      if (esRedCaida || esInfraTransitoria) {
        await colaDao.reencolar(item.id);
        sinRed = true;
        continue;
      }

      errores++;
      if (status !== undefined && status >= 400 && status < 500) {
        // 4xx (datos inválidos) — no reintentable.
        const detalle = JSON.stringify(err?.response?.data ?? mensaje).slice(0, 300);
        await colaDao.marcarError(item.id, `${status}: ${detalle}`);
      } else if (status !== undefined && status >= 500) {
        // 500 — puede ser dato específico o transitorio: reintentable con backoff
        // (consume intentos para no loopear infinito ante un dato realmente malo).
        await colaDao.marcarError(item.id, `${status}: ${mensaje}`);
      } else {
        // Error local (JSON.parse de payload corrupto, bug del procesador, etc.).
        // NO es falta de red: marcar solo este item y seguir con los demás.
        await colaDao.marcarError(item.id, `Dato local inválido: ${mensaje}`.slice(0, 500));
      }
    }
  }

  // Limpiar enviados para no acumular basura
  if (procesados > 0) {
    await colaDao.limpiarEnviados();
  }

  const pendientesRestantes = await colaDao.contarPendientes();

  // Purga de datos ya sincronizados SOLO cuando la cola quedó totalmente vacía
  // (sin pendientes ni errores): así nunca se borra trabajo aún por enviar.
  if (pendientesRestantes === 0 && procesados > 0) {
    await purgarSincronizados();
  }

  return { procesados, errores, pendientes: pendientesRestantes };
}

/**
 * Libera espacio borrando lo ya sincronizado: borradores COMPLETADOS con sus
 * respuestas y las filas offline (víctima/hogar/miembro) en estado 'enviado'.
 * Solo debe llamarse con la cola vacía. Evita el crecimiento ilimitado del .db
 * y reduce PII en reposo tras sincronizar.
 */
async function purgarSincronizados(): Promise<void> {
  const db = await openDb();
  try {
    await db.withTransactionAsync(async () => {
      await db.runAsync(
        "DELETE FROM respuestas WHERE borrador_id IN (SELECT id FROM borradores WHERE estado = 'COMPLETADO')",
      );
      await db.runAsync("DELETE FROM borradores WHERE estado = 'COMPLETADO'");
      await db.runAsync("DELETE FROM victimas_offline WHERE estado_sync = 'enviado'");
      await db.runAsync("DELETE FROM miembros_offline WHERE estado_sync = 'enviado'");
      await db.runAsync("DELETE FROM hogares_offline WHERE estado_sync = 'enviado'");
    });
  } catch {
    /* purga best-effort: si falla, no afecta la sincronización */
  }
}
