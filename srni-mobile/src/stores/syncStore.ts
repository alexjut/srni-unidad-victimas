/**
 * Store de sincronización con Zustand.
 *
 * Estado observable que alimenta el indicador visual en el header:
 *   ✓ Sincronizado   — estaOnline && pendientesCola === 0
 *   ↻ N pendientes   — estaOnline && pendientesCola > 0
 *   ✗ Sin conexión   — !estaOnline
 *   ⚠ N errores      — erroresCola > 0
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
}

// ─────────────────────────────────────────────────────────────────────────────

export const useSyncStore = create<SyncState>((set, get) => ({
  estaOnline: false,
  sincronizando: false,
  pendientesCola: 0,
  erroresCola: 0,
  ultimaSincronizacion: null,
  instrumentoDescargado: false,

  /** Llamar una vez al inicio de la app (en RootLayout). */
  inicializar: async () => {
    // Liberar items bloqueados de una sesión anterior crasheada
    await colaDao.resetearBloqueados();

    // Verificar si ya hay instrumento descargado
    const meta = await instrumentoDao.getMeta();
    set({ instrumentoDescargado: !!meta });

    await get().refrescarContadores();
    await get().checkConnectivity();

    // Listener de AppState: triggerear sync al volver al primer plano
    AppState.addEventListener('change', (estado: AppStateStatus) => {
      if (estado === 'active') {
        get().checkConnectivity();
      }
    });
  },

  checkConnectivity: async () => {
    const online = await sincronizacionService.estaOnline();
    set({ estaOnline: online });

    if (online) {
      // Descargar instrumento si no lo tenemos
      if (!get().instrumentoDescargado) {
        const descargado = await sincronizacionService.descargarInstrumento();
        if (descargado) {
          set({ instrumentoDescargado: true });
        }
      }
      // Intentar sync automático si hay pendientes
      if (get().pendientesCola > 0 && !get().sincronizando) {
        get().triggerSync();
      }
    }
  },

  triggerSync: async () => {
    if (get().sincronizando) return;
    set({ sincronizando: true });

    try {
      const resultado = await sincronizacionService.intentarSincronizar();
      set({ ultimaSincronizacion: new Date().toISOString() });
      await get().refrescarContadores();
    } finally {
      set({ sincronizando: false });
    }
  },

  refrescarContadores: async () => {
    const [pendientes, errores] = await Promise.all([
      colaDao.contarPendientes(),
      colaDao.contarErrores(),
    ]);
    set({ pendientesCola: pendientes, erroresCola: errores });
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
