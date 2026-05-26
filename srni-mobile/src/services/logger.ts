/**
 * Logger remoto — Sprint 17.
 *
 * Envuelve console.warn / console.error para que TODO lo que se loguee en
 * la app móvil aparezca también en la terminal del Django runserver (via
 * el endpoint /api/_debug/log/). Útil cuando Metro no es visible.
 *
 * NO captura console.log para no saturar (en una sesión normal hay cientos).
 *
 * Para logear eventos importantes manualmente, usa `log.info(...)`.
 *
 * Uso:
 *   import { activarLogsRemoto, log } from './services/logger';
 *   activarLogsRemoto();   // una sola vez al inicio (en _layout.tsx)
 *   log.info('Login exitoso', { codigo: 'ALEXJUT' });
 *   log.event('SYNC', 'Inicio sincronizacion', { pendientes: 5 });
 */
import { reportarError } from './errorReporter';

const ORIGINAL = {
  log:   console.log,
  warn:  console.warn,
  error: console.error,
};

let activado = false;

function serializar(args: unknown[]): string {
  return args
    .map((a) => {
      if (a instanceof Error) return `${a.message}\n${a.stack ?? ''}`;
      if (typeof a === 'object') {
        try { return JSON.stringify(a); } catch { return String(a); }
      }
      return String(a);
    })
    .join(' ');
}

/**
 * Activa el envío de console.warn / console.error al backend.
 * Idempotente: llamar varias veces no duplica.
 */
export function activarLogsRemoto(): void {
  if (activado) return;
  activado = true;

  console.warn = (...args: unknown[]) => {
    ORIGINAL.warn(...args);
    reportarError({
      nivel: 'warn',
      mensaje: serializar(args).slice(0, 1500),
      pantalla: '[console.warn]',
    });
  };

  console.error = (...args: unknown[]) => {
    ORIGINAL.error(...args);
    // Extraer stack si hay un Error en los argumentos
    const err = args.find((a) => a instanceof Error) as Error | undefined;
    reportarError({
      nivel: 'error',
      mensaje: serializar(args).slice(0, 1500),
      stack: err?.stack,
      pantalla: '[console.error]',
    });
  };
}

/** Helpers para logear eventos importantes manualmente. */
export const log = {
  /** Evento informativo — siempre se envía. */
  info(mensaje: string, contexto?: Record<string, unknown>): void {
    ORIGINAL.log('[info]', mensaje, contexto ?? '');
    reportarError({
      nivel: 'info',
      mensaje,
      contexto,
      pantalla: '[log.info]',
    });
  },

  /** Evento con categoría (LOGIN, SYNC, DESCARGA, etc). */
  event(categoria: string, mensaje: string, contexto?: Record<string, unknown>): void {
    ORIGINAL.log(`[${categoria}]`, mensaje, contexto ?? '');
    reportarError({
      nivel: 'info',
      mensaje: `[${categoria}] ${mensaje}`,
      contexto,
      pantalla: `[event:${categoria}]`,
    });
  },

  /** Warning manual. Pasa por el wrapper de console.warn. */
  warn(mensaje: string, contexto?: Record<string, unknown>): void {
    console.warn(mensaje, contexto ?? '');
  },

  /** Error manual con stack opcional. */
  error(mensaje: string, error?: unknown, contexto?: Record<string, unknown>): void {
    if (error) console.error(mensaje, error, contexto ?? '');
    else console.error(mensaje, contexto ?? '');
  },
};
