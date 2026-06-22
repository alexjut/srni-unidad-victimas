/**
 * Reconciliación de la cola offline al arrancar — fix #14.
 *
 * Conformar offline hace DOS escrituras separadas y NO atómicas:
 *   1. INSERT en {victimas,hogares,miembros}_offline (estado_sync='pendiente')
 *   2. colaDao.encolar(...) el item de sincronización
 * Si la app crashea (o se mata) entre (1) y (2), queda una fila offline
 * 'pendiente' SIN item en la cola → un recurso huérfano que jamás sincroniza.
 *
 * Esta reconciliación corre una vez al iniciar (antes de sincronizar) y re-encola
 * los huérfanos reconstruyendo el payload desde la propia fila offline. Es
 * IDEMPOTENTE: si ya existe un item de cola (no enviado) para el recurso, lo deja.
 *
 * Alcance: víctima / hogar / miembro (la "conformación"). Las respuestas no se
 * reconcilian aquí — el guardado por capítulo las re-encola en cada visita.
 */
import { openDb } from '../db/schema';
import * as colaDao from '../db/colaDao';

/** ¿Ya hay un item de cola NO enviado para este (tipo, recurso)? */
async function tieneEnCola(
  tipo: colaDao.TipoOperacion,
  recursoLocalId: string,
): Promise<boolean> {
  const db = await openDb();
  const row = await db.getFirstAsync<{ n: number }>(
    "SELECT COUNT(*) AS n FROM cola_sincronizacion WHERE tipo = ? AND recurso_local_id = ? AND estado != 'enviado'",
    [tipo, recursoLocalId],
  );
  return (row?.n ?? 0) > 0;
}

/**
 * Re-encola los recursos offline 'pendiente'/'error' que perdieron su item de
 * cola. Devuelve cuántos reparó (0 = nada que hacer).
 */
export async function reconciliarColaOffline(): Promise<number> {
  const db = await openDb();
  let reparados = 0;

  // 1. VÍCTIMAS — REGISTRAR_VICTIMA (precede a CREAR_HOGAR)
  const victimas = await db.getAllAsync<{ id_local: string; payload_json: string }>(
    "SELECT id_local, payload_json FROM victimas_offline WHERE estado_sync IN ('pendiente','error')",
  );
  for (const v of victimas) {
    if (await tieneEnCola('REGISTRAR_VICTIMA', v.id_local)) continue;
    let victima: unknown;
    try { victima = JSON.parse(v.payload_json); } catch { continue; }
    await colaDao.encolar('REGISTRAR_VICTIMA', v.id_local, { id_local: v.id_local, victima });
    reparados++;
  }

  // 2. HOGARES — CREAR_HOGAR
  const hogares = await db.getAllAsync<{
    id_local: string; jefe_hogar_uuid: string; municipio_id: number | null;
    tipo_vivienda: string; condicion_ocupacion: string; estrato: number;
    numero_cuartos: number; numero_personas: number; observaciones: string;
  }>(
    "SELECT * FROM hogares_offline WHERE estado_sync IN ('pendiente','error')",
  );
  for (const h of hogares) {
    if (await tieneEnCola('CREAR_HOGAR', h.id_local)) continue;
    await colaDao.encolar('CREAR_HOGAR', h.id_local, {
      id_local: h.id_local,
      autorizado: h.jefe_hogar_uuid,
      municipio: h.municipio_id ?? undefined,
      tipo_vivienda: h.tipo_vivienda,
      condicion_ocupacion: h.condicion_ocupacion,
      estrato: h.estrato,
      numero_cuartos: h.numero_cuartos,
      numero_personas: h.numero_personas,
      observaciones: h.observaciones,
    });
    reparados++;
  }

  // 3. MIEMBROS — AGREGAR_MIEMBRO (el sync remapea `hogar` local→servidor)
  const miembros = await db.getAllAsync<{
    id_local: string; hogar_id_local: string; payload_json: string;
  }>(
    "SELECT id_local, hogar_id_local, payload_json FROM miembros_offline WHERE estado_sync IN ('pendiente','error')",
  );
  for (const m of miembros) {
    if (await tieneEnCola('AGREGAR_MIEMBRO', m.id_local)) continue;
    let miembro: unknown;
    try { miembro = JSON.parse(m.payload_json); } catch { continue; }
    await colaDao.encolar('AGREGAR_MIEMBRO', m.id_local, {
      id_local: m.id_local,
      hogar: m.hogar_id_local,
      miembro,
    });
    reparados++;
  }

  return reparados;
}
