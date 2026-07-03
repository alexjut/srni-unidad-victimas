/**
 * Servicio de PRE-CARGA OFFLINE (Fase 0).
 *
 * Tras un login exitoso CON conexión, descarga GET /api/victimas/precarga/ y
 * persiste padron + jornada + parametricas + version en SQLite, para que la
 * app pueda buscar, seleccionar instrumento y armar la cascada de ubicación
 * SIN red en sesiones subsecuentes.
 *
 * Es NO bloqueante: si la precarga falla, el login NO debe fallar. El estado
 * se expone via getEstadoPrecarga() para que la UI lo refleje si lo desea.
 */
import apiClient from '../api/client';
import * as precargaDao from '../db/precargaDao';
import type { PrecargaPayload } from '../db/precargaDao';

export type EstadoPrecarga = 'inactiva' | 'cargando' | 'lista' | 'error';

let _estado: EstadoPrecarga = 'inactiva';
let _enVuelo: Promise<void> | null = null;

/** Estado actual de la precarga (para indicadores en UI). */
export function getEstadoPrecarga(): EstadoPrecarga {
  return _estado;
}

/**
 * Descarga y persiste la precarga. NO lanza — captura todo error y lo refleja
 * en el estado. Idempotente: si ya hay una corrida en vuelo, devuelve la misma.
 */
export async function ejecutarPrecarga(): Promise<void> {
  if (_enVuelo) return _enVuelo;

  _estado = 'cargando';
  _enVuelo = (async () => {
    try {
      const { data } = await apiClient.get<PrecargaPayload>('/api/victimas/precarga/', {
        timeout: 30000,
      });
      await precargaDao.guardarPrecarga(data);
      _estado = 'lista';
    } catch (err) {
      // NO propagar — la precarga es best-effort. Solo registrar.
      _estado = 'error';
      console.warn('[precarga] no se pudo precargar el padrón offline:', err);
    } finally {
      _enVuelo = null;
    }
  })();

  return _enVuelo;
}

/**
 * Lanza la precarga en segundo plano sin esperar (fire-and-forget). Pensado
 * para llamarse desde el login: el login retorna de inmediato y la precarga
 * sigue corriendo.
 */
export function precargarEnSegundoPlano(): void {
  void ejecutarPrecarga();
}

/** true si hay datos de precarga ya persistidos en el dispositivo. */
export function hayPrecarga(): Promise<boolean> {
  return precargaDao.hayPrecarga();
}
