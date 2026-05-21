/**
 * Store de Zustand para el flujo de caracterización activo.
 *
 * Almacena la víctima encontrada en el repositorio externo (RUV / Mock)
 * y el UUID local Django resultante de registrarDesdeFuente().
 * Se limpia al terminar el flujo o al navegar fuera de él.
 *
 * NO persiste en disco — solo en memoria de la sesión activa.
 */
import { create } from 'zustand';
import type { VictimaResumenFuente } from '../types';

interface CaracterizacionState {
  victimaFuente: VictimaResumenFuente | null;
  victimaLocalId: string | null;
  hogarId: string | null;
  /** Ruta de entrevista seleccionada en búsqueda — se pasa al crear la sesión. */
  rutaEntrevista: string;
  /** ID del instrumento seleccionado en búsqueda — se usa al crear la sesión desde hogares/nuevo. */
  instrumentoId: string | null;

  setVictimaFuente: (v: VictimaResumenFuente | null) => void;
  setVictimaLocalId: (id: string | null) => void;
  setHogarId: (id: string | null) => void;
  setRutaEntrevista: (ruta: string) => void;
  setInstrumentoId: (id: string | null) => void;
  limpiar: () => void;
}

export const useCaracterizacionStore = create<CaracterizacionState>((set) => ({
  victimaFuente: null,
  victimaLocalId: null,
  hogarId: null,
  rutaEntrevista: 'GENERAL',
  instrumentoId: null,

  setVictimaFuente: (v) => set({ victimaFuente: v }),
  setVictimaLocalId: (id) => set({ victimaLocalId: id }),
  setHogarId: (id) => set({ hogarId: id }),
  setRutaEntrevista: (ruta) => set({ rutaEntrevista: ruta }),
  setInstrumentoId: (id) => set({ instrumentoId: id }),
  limpiar: () => set({
    victimaFuente: null, victimaLocalId: null, hogarId: null,
    rutaEntrevista: 'GENERAL', instrumentoId: null,
  }),
}));
