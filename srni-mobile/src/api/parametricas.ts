/**
 * Cliente API de paramétricas — solo lectura.
 *
 * Sprint 19: usado por la pantalla `caracterizar/ubicacion-atencion.tsx`
 * para armar la cascada UARIV:
 *   Dirección Territorial  →  Departamento  →  Municipio
 *                          →  Punto de Atención
 *
 * Las listas son chicas (21 DTs, 33 deptos, 1102 muns, 41 puntos), así
 * que se cachean en memoria (`paramCache`) al primer login para que la
 * cascada funcione offline en sesiones subsecuentes.
 */
import apiClient from './client';
import type { PaginatedResponse } from '../types';
import * as precargaDao from '../db/precargaDao';

export interface DireccionTerritorial {
  id: number;
  codigo: string;
  nombre: string;
  activo: boolean;
}

export interface Departamento {
  id: number;
  codigo_dane: string;
  nombre: string;
  activo: boolean;
}

export interface Municipio {
  id: number;
  codigo_dane: string;
  nombre: string;
  departamento: number;
  departamento_nombre?: string;
  activo: boolean;
}

export interface PuntoAtencion {
  id: number;
  codigo: string;
  nombre: string;
  direccion_territorial: number;
  municipio: number;
  activo: boolean;
}

const BASE = '/api/parametricas';

export const parametricasApi = {
  listarDirecciones: () =>
    apiClient.get<PaginatedResponse<DireccionTerritorial>>(
      `${BASE}/direcciones-territoriales/`,
      { params: { activo: 'true', page_size: 50 } },
    ),

  listarDeptosPorDT: (dtId: number) =>
    apiClient.get<PaginatedResponse<Departamento>>(
      `${BASE}/departamentos/`,
      { params: { direcciones_territoriales: dtId, activo: 'true', page_size: 50 } },
    ),

  listarMunicipiosPorDepto: (deptoId: number) =>
    apiClient.get<PaginatedResponse<Municipio>>(
      `${BASE}/municipios/`,
      { params: { departamento: deptoId, activo: 'true', page_size: 200 } },
    ),

  /**
   * Sprint 20 — devuelve los 1102 municipios DANE de Colombia en una sola
   * respuesta sin paginar. Usado para alimentar los selectores
   * COMBO_DINAMICO del formulario (Z2/Z5A/Z15/A23A/HV3 — todos pedidos de
   * municipio). El cliente cachea el resultado en memoria.
   */
  listarMunicipiosTodos: () =>
    apiClient.get<Municipio[]>(`${BASE}/municipios/todos/`),

  listarPuntosPorDT: (dtId: number) =>
    apiClient.get<PaginatedResponse<PuntoAtencion>>(
      `${BASE}/puntos-atencion/`,
      { params: { direccion_territorial: dtId, activo: 'true', page_size: 50 } },
    ),
};

// ── Caché en memoria simple ────────────────────────────────────────────────
// Las listas no cambian con frecuencia. Cachear evita pedirlas N veces por
// sesión. Si el usuario reabre la app, se piden de nuevo (cache en memoria,
// no persistente — se invalida con cerrar la app, que es lo deseado).

interface ParamCache {
  direcciones: DireccionTerritorial[] | null;
  deptosPorDT: Map<number, Departamento[]>;
  muniPorDepto: Map<number, Municipio[]>;
  puntosPorDT: Map<number, PuntoAtencion[]>;
  muniTodos: Municipio[] | null;
}

const paramCache: ParamCache = {
  direcciones: null,
  deptosPorDT: new Map(),
  muniPorDepto: new Map(),
  puntosPorDT: new Map(),
  muniTodos: null,
};

// ── Fallback OFFLINE (Fase 0) ───────────────────────────────────────────────
// Lee de parametricas_cache (persistido por la precarga al login) cuando la red
// falla. Las listas se persisten "tal cual" las da el endpoint de precarga;
// aquí se coercen defensivamente a los tipos del cliente.

async function dtOffline(): Promise<DireccionTerritorial[]> {
  const raw = await precargaDao.leerParametrica<any>('direcciones_territoriales');
  return raw.map((d, i) => ({
    id: Number(d.id ?? i),
    codigo: String(d.codigo ?? ''),
    nombre: String(d.nombre ?? ''),
    activo: d.activo !== false,
  }));
}

async function muniOffline(): Promise<Municipio[]> {
  const raw = await precargaDao.leerParametrica<any>('municipios');
  return raw.map((m, i) => ({
    id: Number(m.id ?? i),
    codigo_dane: String(m.codigo_dane ?? ''),
    nombre: String(m.nombre ?? ''),
    departamento: Number(m.departamento_id ?? m.departamento ?? 0),
    departamento_nombre:
      typeof m.departamento === 'string' ? m.departamento : m.departamento_nombre,
    activo: m.activo !== false,
  }));
}

async function puntosOffline(): Promise<PuntoAtencion[]> {
  const raw = await precargaDao.leerParametrica<any>('puntos_atencion');
  return raw.map((p, i) => ({
    id: Number(p.id ?? i),
    codigo: String(p.codigo ?? ''),
    nombre: String(p.nombre ?? ''),
    direccion_territorial: Number(p.direccion_territorial ?? 0),
    municipio: Number(p.municipio ?? 0),
    activo: p.activo !== false,
  }));
}

export const parametricasCacheado = {
  async getDirecciones(): Promise<DireccionTerritorial[]> {
    if (paramCache.direcciones) return paramCache.direcciones;
    try {
      const { data } = await parametricasApi.listarDirecciones();
      paramCache.direcciones = data.results;
      return data.results;
    } catch (e) {
      const off = await dtOffline();
      if (off.length > 0) { paramCache.direcciones = off; return off; }
      throw e;
    }
  },

  async getDeptosPorDT(dtId: number): Promise<Departamento[]> {
    const hit = paramCache.deptosPorDT.get(dtId);
    if (hit) return hit;
    try {
      const { data } = await parametricasApi.listarDeptosPorDT(dtId);
      paramCache.deptosPorDT.set(dtId, data.results);
      return data.results;
    } catch (e) {
      // Offline: derivar los departamentos de los municipios cacheados.
      const muns = await muniOffline();
      const vistos = new Map<string, Departamento>();
      for (const m of muns) {
        const nombre = m.departamento_nombre ?? '';
        if (!nombre || vistos.has(nombre)) continue;
        vistos.set(nombre, {
          id: m.departamento,
          codigo_dane: m.codigo_dane.slice(0, 2),
          nombre,
          activo: true,
        });
      }
      const off = Array.from(vistos.values());
      if (off.length > 0) { paramCache.deptosPorDT.set(dtId, off); return off; }
      throw e;
    }
  },

  async getMunicipiosPorDepto(deptoId: number): Promise<Municipio[]> {
    const hit = paramCache.muniPorDepto.get(deptoId);
    if (hit) return hit;
    try {
      const { data } = await parametricasApi.listarMunicipiosPorDepto(deptoId);
      paramCache.muniPorDepto.set(deptoId, data.results);
      return data.results;
    } catch (e) {
      const muns = await muniOffline();
      const off = muns.filter((m) => m.departamento === deptoId);
      if (off.length > 0) { paramCache.muniPorDepto.set(deptoId, off); return off; }
      throw e;
    }
  },

  async getPuntosPorDT(dtId: number): Promise<PuntoAtencion[]> {
    const hit = paramCache.puntosPorDT.get(dtId);
    if (hit) return hit;
    try {
      const { data } = await parametricasApi.listarPuntosPorDT(dtId);
      paramCache.puntosPorDT.set(dtId, data.results);
      return data.results;
    } catch (e) {
      const off = (await puntosOffline()).filter(
        (p) => !p.direccion_territorial || p.direccion_territorial === dtId,
      );
      if (off.length > 0) { paramCache.puntosPorDT.set(dtId, off); return off; }
      throw e;
    }
  },

  /** Sprint 20 — los 1102 municipios DANE para los COMBO_DINAMICO del formulario. */
  async getMunicipiosTodos(): Promise<Municipio[]> {
    if (paramCache.muniTodos) return paramCache.muniTodos;
    try {
      const { data } = await parametricasApi.listarMunicipiosTodos();
      paramCache.muniTodos = data;
      return data;
    } catch (e) {
      const off = await muniOffline();
      if (off.length > 0) { paramCache.muniTodos = off; return off; }
      throw e;
    }
  },

  /** Limpia toda la caché (útil al cerrar sesión). */
  invalidar() {
    paramCache.direcciones = null;
    paramCache.deptosPorDT.clear();
    paramCache.muniPorDepto.clear();
    paramCache.puntosPorDT.clear();
    paramCache.muniTodos = null;
  },
};
