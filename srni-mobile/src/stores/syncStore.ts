/**
 * Store de sincronización con Zustand.
 *
 * Estado observable que alimenta el indicador visual en el header:
 *   ✓ Sincronizado   — estaOnline && pendientesCola === 0
 *   ↻ N pendientes   — estaOnline && pendientesCola > 0
 *   ✗ Sin conexión   — !estaOnline
 *   ⚠ N errores      — erroresCola > 0
 *
 * Sprint 9: polling de conectividad cada 60 s + backoff exponencial en la cola.
 */
import { create } from 'zustand';
import { AppState, type AppStateStatus } from 'react-native';
import * as sincronizacionService from '../services/sincronizacion';
import * as colaDao from '../db/colaDao';
import * as instrumentoDao from '../db/instrumentoDao';

export type EstadoSync =
  | 'sincronizado'
  | 'sincronizando'
  | 'pendientes'
  | 'sin_conexion'
  | 'error';

interface SyncState {
  estaOnline: boolean;
  sincronizando: boolean;
  pendientesCola: number;
  erroresCola: number;
  ultimaSincronizacion: string | null;   // ISO string
  instrumentoDescargado: boolean;

  // Acciones
  inicializar: () => Promise<void>;
  triggerSync: () => Promise<void>;
  checkConnectivity: () => Promise<void>;
  refrescarContadores: () => Promise<void>;
  reintentarErrores: () => Promise<void>;
}

// ─────────────────────────────────────────────────────────────────────────────

let pollingInterval: ReturnType<typeof setInterval> | null = null;

export const useSyncStore = create<SyncState>((set, get) => ({
  estaOnline: false,
  sincronizando: false,
  pendientesCola: 0,
  erroresCola: 0,
  ultimaSincronizacion: null,
  instrumentoDescargado: false,

  /** Llamar una vez al inicio de la app (en RootLayout). */
  inicializar: async () => {
    await colaDao.resetearBloqueados();

    const meta = await instrumentoDao.getMeta();
    set({ instrumentoDescargado: !!meta });

    await get().refrescarContadores();
    await get().checkConnectivity();

    // Listener de AppState: disparar check al volver al primer plano
    AppState.addEventListener('change', (estado: AppStateStatus) => {
      if (estado === 'active') {
        get().checkConnectivity();
      }
    });

    // Polling cada 60 s para detectar cuando vuelve la red
    if (pollingInterval) clearInterval(pollingInterval);
    pollingInterval = setInterval(() => {
      get().checkConnectivity();
    }, 60_000);
  },

  checkConnectivity: async () => {
    const online = await sincronizacionService.estaOnline();
    const eraOffline = !get().estaOnline;
    set({ estaOnline: online });

    if (online) {
      // Descargar instrumento si no lo tenemos (usa perfil_codigo del meta local)
      if (!get().instrumentoDescargado) {
        const descargado = await sincronizacionService.descargarInstrumento();
        if (descargado) {
          set({ instrumentoDescargado: true });
        }
      }

      // Si acaba de recuperar conexión o hay pendientes, intentar sync
      await get().refrescarContadores();
      const { pendientesCola, sincronizando } = get();
      if ((eraOffline || pendientesCola > 0) && !sincronizando) {
        get().triggerSync();
      }
    }
  },

  triggerSync: async () => {
    if (get().sincronizando) return;
    set({ sincronizando: true });

    try {
      await sincronizacionService.intentarSincronizar();
      set({ ultimaSincronizacion: new Date().toISOString() });
    } finally {
      set({ sincronizando: false });
      await get().refrescarContadores();
    }
  },

  refrescarContadores: async () => {
    const [pendientes, errores] = await Promise.all([
      colaDao.contarPendientes(),
      colaDao.contarErrores(),
    ]);
    set({ pendientesCola: pendientes, erroresCola: errores });
  },

  reintentarErrores: async () => {
    await colaDao.reintentarErrores();
    await get().refrescarContadores();
    if (get().estaOnline && !get().sincronizando) {
      get().triggerSync();
    }
  },
}));

/** Selector: devuelve el estado visual de sync simplificado. */
export function getEstadoSync(state: SyncState): EstadoSync {
  if (state.sincronizando) return 'sincronizando';
  if (!state.estaOnline) return 'sin_conexion';
  if (state.erroresCola > 0) return 'error';
  if (state.pendientesCola > 0) return 'pendientes';
  return 'sincronizado';
}
