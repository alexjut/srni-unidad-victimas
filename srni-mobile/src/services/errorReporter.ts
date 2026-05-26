/**
 * Reporte de errores al backend.
 *
 * Sprint 17: como Metro/Expo no siempre muestra los logs en el celular,
 * este servicio envía cualquier error capturado (ErrorBoundary, axios,
 * tareas async) al endpoint /api/_debug/log/ del backend. Los errores
 * aparecen en la terminal del Django runserver con formato visible.
 *
 * Es defensivo: si el envío falla, NO lanza error (no queremos crashear
 * la app por no poder reportar). Si no hay conexión, simplemente lo
 * silencia (lo guardará el siguiente try o se perderá).
 */
import { Platform } from 'react-native';
import Constants from 'expo-constants';

const BASE_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8001';

export interface ErrorReportPayload {
  nivel?: 'error' | 'warn' | 'info';
  mensaje: string;
  stack?: string;
  pantalla?: string;
  contexto?: Record<string, unknown>;
}

function obtenerDispositivo(): string {
  const platform = Platform.OS;
  const ver = Platform.Version;
  const device = Constants.deviceName ?? '?';
  return `${platform} ${ver} / ${device}`;
}

/** Envía un error al backend. NUNCA lanza. */
export async function reportarError(payload: ErrorReportPayload): Promise<void> {
  try {
    await fetch(`${BASE_URL}/api/_debug/log/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        nivel: payload.nivel ?? 'error',
        mensaje: payload.mensaje,
        stack: payload.stack ?? '',
        pantalla: payload.pantalla ?? '',
        contexto: payload.contexto ?? {},
        dispositivo: obtenerDispositivo(),
      }),
    });
  } catch {
    // Silencioso — no queremos crash en cascada
  }
}

/** Helper: reportar excepción genérica con stack. */
export async function reportarExcepcion(
  error: unknown,
  pantalla?: string,
  contexto?: Record<string, unknown>,
): Promise<void> {
  const e = error as Error;
  await reportarError({
    nivel: 'error',
    mensaje: e?.message ?? String(error),
    stack: e?.stack,
    pantalla,
    contexto,
  });
}
