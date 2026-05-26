/**
 * Instrumentos en memoria — Sprint 18 Fase 1B (definitivo).
 *
 * Los instrumentos (capítulos, preguntas, opciones, reglas) son datos
 * ESTÁTICOS read-only que vienen del bundle empaquetado en el APK.
 * NO tiene sentido meterlos en SQLite — solo causa transacciones masivas
 * que colisionan con escrituras de cola/borradores → 'database is locked'.
 *
 * Esta capa carga los 8 instrumentos al primer uso (require static) y los
 * mantiene en memoria. La lectura es O(1) directamente sobre Map.
 *
 * SQLite se mantiene SOLO para:
 *   - borradores (sesiones en progreso)
 *   - respuestas (lo que el usuario captura)
 *   - cola_sincronizacion
 *   - hogares_offline
 *
 * API:
 *   activarPerfil(codigo)        - cambia el perfil activo (sin escribir nada)
 *   getCapitulos()               - capítulos del perfil activo
 *   getPreguntas(capId)          - preguntas de un capítulo
 *   getOpciones(pregId)          - opciones de una pregunta
 *   getOpcionesBatch(pregIds[])  - {pregId → opciones[]}
 *   getReglas()                  - reglas skip logic del perfil activo
 *   getMeta()                    - metadata del perfil activo (id, codigo, version)
 *   getCapituloIdDePregunta(id)  - para joins respuestas → capítulo
 */
import type {
  CapituloRow, PreguntaRow, OpcionRow, ReglaSkipLogicRow,
  InstrumentoMeta,
} from '../db/instrumentoDao';

// ── Bundle estático — Metro empaqueta los JSON al hacer el build ─────────────
const BUNDLED: Record<string, any> = {
  ASISTENCIA:        require('../../assets/instrumentos/asistencia_v8.json'),
  BUENAVENTURA:      require('../../assets/instrumentos/buenaventura_v7.json'),
  RURAL_ETNICO:      require('../../assets/instrumentos/rural_etnico_v1.json'),
  SAN_ANDRES:        require('../../assets/instrumentos/san_andres_v7.json'),
  TELEFONICO:        require('../../assets/instrumentos/telefonico_v8.json'),
  TERRITORIAL:       require('../../assets/instrumentos/territorial_v7.json'),
  URBANO_ETNICO:     require('../../assets/instrumentos/urbano_etnico_v1.json'),
  VICTIMAS_EXTERIOR: require('../../assets/instrumentos/victimas_exterior_v1.json'),
};

export type PerfilCodigo = keyof typeof BUNDLED;

// ── Caches (se llenan al primer acceso) ──────────────────────────────────────
const _porCodigo = new Map<string, any>();
const _capsPorPerfil = new Map<string, CapituloRow[]>();
const _capPorId = new Map<string, CapituloRow>();
const _pregsPorCap = new Map<string, PreguntaRow[]>();
const _opcionesPorPreg = new Map<string, OpcionRow[]>();
const _reglasPorPerfil = new Map<string, ReglaSkipLogicRow[]>();
const _capPorPregId = new Map<string, string>();   // para JOIN respuestas → cap

let _perfilActivo: string | null = null;
let _inicializado = false;

// ── Inicialización idempotente ───────────────────────────────────────────────
function _inicializar(): void {
  if (_inicializado) return;

  for (const [codigo, data] of Object.entries(BUNDLED)) {
    _porCodigo.set(codigo, data);

    const caps: CapituloRow[] = [];
    for (const cap of data.capitulos ?? []) {
      const capRow: CapituloRow = {
        id: cap.id,
        codigo: cap.codigo,
        nombre: cap.nombre,
        orden: cap.orden ?? 0,
        nivel: cap.nivel ?? 'HOGAR',
        activo: 1,
      };
      caps.push(capRow);
      _capPorId.set(cap.id, capRow);

      const pregs: PreguntaRow[] = [];
      for (const p of cap.preguntas ?? []) {
        if (!p.activa) continue;
        const pregRow: PreguntaRow = {
          id: p.id,
          capitulo_id: cap.id,
          codigo_externo: p.codigo_externo,
          no_pregunta: p.no_pregunta ?? '',
          texto: p.texto ?? '',
          descripcion_ayuda: p.descripcion_ayuda ?? '',
          tipo: p.tipo ?? 'TEXTO',
          nivel: p.nivel ?? cap.nivel ?? 'HOGAR',
          orden: p.orden ?? 0,
          obligatoria: p.obligatoria ? 1 : 0,
          activa: 1,
          validaciones: typeof p.validaciones === 'string'
            ? p.validaciones
            : JSON.stringify(p.validaciones ?? {}),
        };
        pregs.push(pregRow);
        _capPorPregId.set(p.id, cap.id);

        const opciones: OpcionRow[] = (p.opciones ?? []).map((o: any) => ({
          id: o.id,
          pregunta_id: p.id,
          valor: o.valor ?? '',
          etiqueta: o.etiqueta ?? '',
          orden: o.orden ?? 0,
          finaliza_capitulo: o.finaliza_capitulo ? 1 : 0,
        }));
        _opcionesPorPreg.set(p.id, opciones);
      }
      pregs.sort((a, b) => a.orden - b.orden);
      _pregsPorCap.set(cap.id, pregs);
    }
    caps.sort((a, b) => a.orden - b.orden);
    _capsPorPerfil.set(codigo, caps);

    const reglas: ReglaSkipLogicRow[] = (data.reglas ?? []).map((r: any) => ({
      id: r.id,
      instrumento_id: data.id,
      pregunta_origen_codigo: r.pregunta_origen_codigo ?? null,
      valor_trigger: r.valor_trigger ?? '',
      expresion_origen: r.expresion_origen ?? '',
      pregunta_afectada_id: r.pregunta_afectada ?? null,
      pregunta_afectada_codigo: r.pregunta_afectada_codigo ?? null,
      capitulo_afectado_id: r.capitulo_afectado ?? null,
      accion: r.accion,
    }));
    _reglasPorPerfil.set(codigo, reglas);
  }

  _inicializado = true;
}

// ── API pública ──────────────────────────────────────────────────────────────

export function activarPerfil(codigo: string): void {
  _inicializar();
  if (!_porCodigo.has(codigo)) {
    throw new Error(`Perfil no encontrado en el bundle: ${codigo}`);
  }
  _perfilActivo = codigo;
}

export function getPerfilActivo(): string | null {
  return _perfilActivo;
}

export function listaPerfiles(): PerfilCodigo[] {
  _inicializar();
  return Array.from(_porCodigo.keys()) as PerfilCodigo[];
}

export function getMeta(): InstrumentoMeta | null {
  _inicializar();
  if (!_perfilActivo) return null;
  const data = _porCodigo.get(_perfilActivo);
  if (!data) return null;
  return {
    instrumento_id: data.id,
    perfil_codigo: data.codigo,
    version: data.version ?? data.numero ?? '',
    descargado_en: '(bundled)',
  };
}

export function getCapitulos(): CapituloRow[] {
  _inicializar();
  if (!_perfilActivo) return [];
  return _capsPorPerfil.get(_perfilActivo) ?? [];
}

export function getPreguntas(capituloId: string): PreguntaRow[] {
  _inicializar();
  return _pregsPorCap.get(capituloId) ?? [];
}

export function getOpciones(preguntaId: string): OpcionRow[] {
  _inicializar();
  return _opcionesPorPreg.get(preguntaId) ?? [];
}

export function getOpcionesBatch(preguntaIds: string[]): Record<string, OpcionRow[]> {
  _inicializar();
  const out: Record<string, OpcionRow[]> = {};
  for (const id of preguntaIds) {
    out[id] = _opcionesPorPreg.get(id) ?? [];
  }
  return out;
}

export function getReglas(): ReglaSkipLogicRow[] {
  _inicializar();
  if (!_perfilActivo) return [];
  return _reglasPorPerfil.get(_perfilActivo) ?? [];
}

export function getReglasPorCapitulo(capituloId: string): ReglaSkipLogicRow[] {
  return getReglas().filter((r) => r.capitulo_afectado_id === capituloId);
}

export function contarPreguntasPorCapitulo(): Record<string, { total: number; obligatorias: number }> {
  _inicializar();
  const out: Record<string, { total: number; obligatorias: number }> = {};
  for (const caps of _capsPorPerfil.values()) {
    for (const cap of caps) {
      const pregs = _pregsPorCap.get(cap.id) ?? [];
      out[cap.id] = {
        total: pregs.length,
        obligatorias: pregs.filter((p) => p.obligatoria === 1).length,
      };
    }
  }
  return out;
}

/** Útil para joins respuestas → capítulo (las respuestas viven en SQLite). */
export function getCapituloIdDePregunta(preguntaId: string): string | null {
  _inicializar();
  return _capPorPregId.get(preguntaId) ?? null;
}
