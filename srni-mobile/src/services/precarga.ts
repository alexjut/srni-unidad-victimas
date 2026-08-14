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
import * as filtroUniverso from './filtroUniverso';

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

      // El filtro del universo va DESPUÉS de marcar 'lista', y aparte: son
      // 22,7 MB que tardan, y el encuestador debe poder salir a campo con el
      // padrón cargado aunque el filtro no alcance a bajar. Sin él la búsqueda
      // offline funciona como siempre; con él, además reconoce a los 8,12 M
      // que están en el RUV y nunca fueron entrevistados.
      await descargarFiltroUniverso(data);
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
 * Descarga el filtro del universo si el servidor lo ofrece y aún no lo tenemos.
 *
 * NO lanza nunca: es un accesorio. Si falla, la búsqueda offline sigue
 * comportándose como antes —solo reconoce a quien tiene ficha— y el intento se
 * repite en la siguiente precarga.
 *
 * Se re-descarga solo cuando cambia la versión del padrón. Bajar 22,7 MB en
 * cada login gastaría los datos del encuestador para reescribir lo mismo.
 */
async function descargarFiltroUniverso(data: PrecargaPayload): Promise<void> {
  try {
    const bloom = (data as any)?.padron_archivo?.bloom;
    const version = (data as any)?.padron_archivo?.version ?? '';
    if (!bloom?.url || !bloom?.m || !bloom?.k) return;

    const guardado = await precargaDao.getParametrosBloom();
    const yaEstaba = filtroUniverso.parsearParametros(guardado);
    if (yaEstaba && (yaEstaba as any).version === version
        && filtroUniverso.hayFiltro(yaEstaba)) {
      return;
    }

    const token = await obtenerToken();
    if (!token) return;

    const ok = await filtroUniverso.descargarFiltro({ ...bloom }, token);
    // Los parámetros se guardan SOLO si el archivo llegó completo. Guardarlos
    // antes dejaría a la APK convencida de tener un filtro que no tiene, y un
    // filtro ausente responde "no está en el universo" para todo el mundo.
    await precargaDao.guardarParametrosBloom(ok ? { ...bloom, version } : null);
  } catch (err) {
    console.warn('[precarga] no se pudo descargar el filtro del universo:', err);
  }
}

/** El Bearer del usuario, que el endpoint del filtro exige. */
async function obtenerToken(): Promise<string> {
  try {
    const mod = await import('../api/client');
    const cabecera = (mod.default.defaults.headers.common?.Authorization ?? '') as string;
    return cabecera.replace(/^Bearer\s+/i, '');
  } catch {
    return '';
  }
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
