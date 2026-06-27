/**
 * Instrumentos en memoria — Sprint 18 Fase C (lazy per-perfil).
 *
 * Los instrumentos son datos ESTÁTICOS read-only del bundle. Esta capa los
 * indexa en Maps en memoria. Lectura O(1) directa, sin SQLite, sin awaits.
 *
 * Sprint 18 Fase C: solo MANTIENE UN PERFIL EN MEMORIA a la vez.
 * Cuando se activa un perfil distinto, libera los Maps del anterior.
 * En una entrevista solo se usa un instrumento — no tiene sentido tener
 * los 8 cargados (protege celulares gama baja de campo, 2-3MB extra).
 *
 * SQLite se mantiene SOLO para:
 *   - borradores, respuestas, cola_sincronizacion, hogares_offline
 *
 * API:
 *   activarPerfil(codigo)         - carga ese perfil en memoria, libera el previo
 *   listaPerfiles()               - los 8 códigos disponibles en el bundle
 *   getPerfilActivo()             - codigo del perfil activo o null
 *   getMeta()                     - metadata {id, codigo, version}
 *   getCapitulos()                - capítulos del perfil activo
 *   getPreguntas(capId)           - preguntas de un capítulo
 *   getOpciones(pregId)           - opciones de una pregunta
 *   getOpcionesBatch(pregIds[])   - {pregId → opciones[]}
 *   getReglas()                   - reglas skip logic del perfil activo
 *   getReglasPorCapitulo(capId)   - reglas que afectan a un capítulo
 *   contarPreguntasPorCapitulo()  - {capId → {total, obligatorias}}
 *   getCapituloIdDePregunta(id)   - join respuesta → capítulo
 *   codigoPorInstrumentoId(uuid)  - busca el código del perfil por UUID
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

// ── Caches del PERFIL ACTIVO (se vacían al cambiar de perfil) ────────────────
let _capsActivo: CapituloRow[] = [];
let _pregsPorCap = new Map<string, PreguntaRow[]>();
let _opcionesPorPreg = new Map<string, OpcionRow[]>();
let _reglasActivo: ReglaSkipLogicRow[] = [];
let _capPorPregId = new Map<string, string>();
let _conteoPreguntas: Record<string, {
  total: number;
  obligatorias: number;
  obligHogar: number;
  obligPersona: number;
}> = {};
let _metaActivo: InstrumentoMeta | null = null;
let _perfilActivo: string | null = null;

/**
 * Vacía los Maps del perfil actual y carga el nuevo desde el bundle.
 * Asignar nuevos Map permite que el GC libere el anterior (no acumula).
 */
function _cargarPerfilEnMemoria(codigo: string): void {
  const data = BUNDLED[codigo];
  if (!data) throw new Error(`Perfil no encontrado en el bundle: ${codigo}`);

  const caps: CapituloRow[] = [];
  const pregsPorCap = new Map<string, PreguntaRow[]>();
  const opcionesPorPreg = new Map<string, OpcionRow[]>();
  const capPorPregId = new Map<string, string>();
  // Sprint 21 fix — separar obligatorias por nivel para que la pantalla
  // formulario/index pueda calcular bien el progreso (obligPersona × miembros).
  const conteo: Record<string, {
    total: number;
    obligatorias: number;
    obligHogar: number;
    obligPersona: number;
  }> = {};

  for (const cap of data.capitulos ?? []) {
    caps.push({
      id: cap.id,
      codigo: cap.codigo,
      nombre: cap.nombre,
      orden: cap.orden ?? 0,
      nivel: cap.nivel ?? 'HOGAR',
      activo: 1,
    });

    const pregs: PreguntaRow[] = [];
    let obligs = 0;
    let obligHogar = 0;
    let obligPersona = 0;
    for (const p of cap.preguntas ?? []) {
      if (!p.activa) continue;
      const obligatoria = p.obligatoria ? 1 : 0;
      const nivel = p.nivel ?? cap.nivel ?? 'HOGAR';
      if (obligatoria === 1) {
        obligs++;
        if (nivel === 'PERSONA') obligPersona++;
        else obligHogar++;
      }
      pregs.push({
        id: p.id,
        capitulo_id: cap.id,
        codigo_externo: p.codigo_externo,
        no_pregunta: p.no_pregunta ?? '',
        texto: p.texto ?? '',
        descripcion_ayuda: p.descripcion_ayuda ?? '',
        tipo: p.tipo ?? 'TEXTO',
        nivel: p.nivel ?? cap.nivel ?? 'HOGAR',
        orden: p.orden ?? 0,
        obligatoria,
        activa: 1,
        es_precargada: p.es_precargada ? 1 : 0,
        validaciones: typeof p.validaciones === 'string'
          ? p.validaciones
          : JSON.stringify(p.validaciones ?? {}),
      });
      capPorPregId.set(p.id, cap.id);

      const opciones: OpcionRow[] = (p.opciones ?? []).map((o: any) => ({
        id: o.id,
        pregunta_id: p.id,
        valor: o.valor ?? '',
        etiqueta: o.etiqueta ?? '',
        orden: o.orden ?? 0,
        finaliza_capitulo: o.finaliza_capitulo ? 1 : 0,
      }));
      opcionesPorPreg.set(p.id, opciones);
    }
    pregs.sort((a, b) => a.orden - b.orden);
    pregsPorCap.set(cap.id, pregs);
    conteo[cap.id] = { total: pregs.length, obligatorias: obligs, obligHogar, obligPersona };
  }
  caps.sort((a, b) => a.orden - b.orden);

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

  // Reemplazo atómico: el GC libera los Maps del perfil anterior
  _capsActivo = caps;
  _pregsPorCap = pregsPorCap;
  _opcionesPorPreg = opcionesPorPreg;
  _reglasActivo = reglas;
  _capPorPregId = capPorPregId;
  _conteoPreguntas = conteo;
  _metaActivo = {
    instrumento_id: data.id,
    perfil_codigo: data.codigo,
    version: data.version ?? data.numero ?? '',
    descargado_en: '(bundled)',
  };
  _perfilActivo = codigo;
}

// ── API pública ──────────────────────────────────────────────────────────────

export function activarPerfil(codigo: string): void {
  if (!(codigo in BUNDLED)) {
    throw new Error(`Perfil no encontrado en el bundle: ${codigo}`);
  }
  if (_perfilActivo === codigo) return; // ya activo, no recargar
  _cargarPerfilEnMemoria(codigo);
}

export function getPerfilActivo(): string | null {
  return _perfilActivo;
}

export function listaPerfiles(): PerfilCodigo[] {
  return Object.keys(BUNDLED) as PerfilCodigo[];
}

/** Resumen de un instrumento para los selectores de UI (mismo shape que la API). */
export interface InstrumentoResumenBundle {
  id: string;
  codigo: string;
  nombre: string;
  version: string;
  activo: boolean;
  vigente: boolean;
  total_capitulos: number;
}

/**
 * Fase 0 offline — arma la lista de instrumentos disponibles DESDE EL BUNDLE
 * local, con el mismo shape que devuelve GET /api/formulario/instrumentos/.
 * Permite que el selector de instrumento funcione 100% offline (los JSON ya
 * están empaquetados). No carga los perfiles en memoria, solo lee metadata.
 */
export function listaInstrumentosBundle(): InstrumentoResumenBundle[] {
  return Object.entries(BUNDLED).map(([codigo, data]) => ({
    id: String(data?.id ?? codigo),
    codigo: String(data?.codigo ?? codigo),
    nombre: String(data?.nombre ?? data?.codigo ?? codigo),
    version: String(data?.version ?? data?.numero ?? ''),
    activo: true,
    vigente: true,
    total_capitulos: Array.isArray(data?.capitulos) ? data.capitulos.length : 0,
  }));
}

export function getMeta(): InstrumentoMeta | null {
  return _metaActivo;
}

export function getCapitulos(): CapituloRow[] {
  return _capsActivo;
}

export function getPreguntas(capituloId: string): PreguntaRow[] {
  return _pregsPorCap.get(capituloId) ?? [];
}

export function getOpciones(preguntaId: string): OpcionRow[] {
  return _opcionesPorPreg.get(preguntaId) ?? [];
}

export function getOpcionesBatch(preguntaIds: string[]): Record<string, OpcionRow[]> {
  const out: Record<string, OpcionRow[]> = {};
  for (const id of preguntaIds) {
    out[id] = _opcionesPorPreg.get(id) ?? [];
  }
  return out;
}

export function getReglas(): ReglaSkipLogicRow[] {
  return _reglasActivo;
}

export function getReglasPorCapitulo(capituloId: string): ReglaSkipLogicRow[] {
  return _reglasActivo.filter((r) => r.capitulo_afectado_id === capituloId);
}

export function contarPreguntasPorCapitulo(): Record<string, {
  total: number;
  obligatorias: number;
  obligHogar: number;
  obligPersona: number;
}> {
  return _conteoPreguntas;
}

/** Útil para joins respuestas → capítulo (las respuestas viven en SQLite). */
export function getCapituloIdDePregunta(preguntaId: string): string | null {
  return _capPorPregId.get(preguntaId) ?? null;
}

/**
 * Sprint 18 Fase B: dado un instrumento_id (UUID) busca su código de perfil
 * en el bundle. Permite recuperar el código cuando la sesión solo tiene el
 * UUID y el detalle backend no es accesible (offline).
 *
 * Esta función SÍ debe escanear todos los bundles porque el UUID puede ser
 * de cualquier perfil — no requiere cargarlos a memoria, solo lee el .id.
 */
export function codigoPorInstrumentoId(instrumentoId: string): string | null {
  for (const [codigo, data] of Object.entries(BUNDLED)) {
    if (data?.id === instrumentoId) return codigo;
  }
  return null;
}
