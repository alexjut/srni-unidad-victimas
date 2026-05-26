/**
 * Tipos TypeScript compartidos para el cliente SRNI.
 * Espejean los serializers del backend Django.
 */

// ── Paramétricas ────────────────────────────────────────────────────────────

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
  departamento_codigo: string;
  departamento_nombre: string;
  activo: boolean;
}

export interface TipoDocumento {
  id: number;
  codigo: string;
  nombre: string;
  aplica_nacionales: boolean;
  aplica_extranjeros: boolean;
  activo: boolean;
}

// ── Víctimas ────────────────────────────────────────────────────────────────

export interface VictimaResumen {
  id: string;
  tipo_documento_codigo: string;
  numero_documento_hash: string;
  genero: 'M' | 'F' | 'NB' | 'ND';
  estado_civil: string;
  pertenencia_etnica: string;
  discapacidad: boolean;
  tipo_discapacidad: string;
  estado_ruv: 'INCLUIDO' | 'NO_INCLUIDO' | 'EN_PROCESO' | 'EXCLUIDO';
  municipio_residencia: number | null;
  municipio_residencia_nombre: string | null;
  departamento_nombre: string | null;
  created_at: string;
}

// ── Formulario ──────────────────────────────────────────────────────────────

export type TipoRespuesta =
  | 'TEXTO'
  | 'NUMERICO'
  | 'FECHA'
  | 'OPCION_UNICA'
  | 'OPCION_MULTIPLE'
  | 'SINO'
  | 'TABLA'
  | 'CALCULO';

export interface OpcionRespuesta {
  id: number;
  codigo: string;
  texto: string;
  orden: number;
  activa: boolean;
}

export interface CondicionHabilitacion {
  id: number;
  pregunta_padre: number;
  pregunta_padre_codigo: string;
  pregunta_hija: number;
  pregunta_hija_codigo: string;
  operador: 'EQ' | 'NEQ' | 'GT' | 'GTE' | 'LT' | 'LTE' | 'IN' | 'NOTNULL';
  valor_condicion: string;
}

export interface Pregunta {
  id: number;
  codigo: string;
  texto: string;
  texto_ayuda: string;
  tipo_respuesta: TipoRespuesta;
  orden: number;
  requerida: boolean;
  activa: boolean;
  columna_padre: string;
  validacion: Record<string, unknown>;
  opciones: OpcionRespuesta[];
  condiciones_habilitacion: CondicionHabilitacion[];
}

export interface TemaResumen {
  id: number;
  codigo: string;
  nombre: string;
  orden: number;
  activo: boolean;
  total_preguntas: number;
}

export interface TemaDetalle extends TemaResumen {
  preguntas: Pregunta[];
}

export interface Instrumento {
  id: number;
  codigo: string;
  nombre: string;
  version: string;
  vigente: boolean;
  total_temas: number;
  temas: TemaResumen[];
}

// ── Hogares ─────────────────────────────────────────────────────────────────

export type EstadoHogar = 'BORRADOR' | 'ACTIVO' | 'ARCHIVADO';
export type TipoVivienda = 'CASA' | 'APARTAMENTO' | 'CUARTO' | 'CAMBUCHE' | 'CONTENEDOR' | 'OTRO';
export type CondicionOcupacion = 'PROPIA' | 'PROPIA_PAGANDO' | 'ARRIENDO' | 'FAMILIAR' | 'INVASION' | 'OTRO';

/** Parentesco familiar (sin JEFE — el jefe de hogar se captura dentro de la entrevista) */
export type Parentesco =
  | 'CONYUGE' | 'HIJO_A' | 'YERNO_NUERA'
  | 'NIETO_A' | 'PADRE_MADRE' | 'HERMANO_A' | 'OTRO_PARIENTE' | 'NO_PARIENTE';

/** Rol funcional del integrante en el hogar */
export type RolMiembro = 'MIEMBRO' | 'TUTOR' | 'CUIDADOR_PERMANENTE';

/** Estado de inclusión según verificación en el RUV */
export type EstadoInclusion = 'INCLUIDO' | 'NO_INCLUIDO';

export interface MiembroHogarResumen {
  id: string;
  parentesco: Parentesco | '';
  parentesco_display: string;
  genero: 'M' | 'F' | 'NB' | 'ND';
  fecha_nacimiento: string | null;   // ISO date — NO indexado en backend
  /** Rol funcional en el hogar */
  rol: RolMiembro;
  rol_display: string;
  /** Marca del titular que autoriza la entrevista — solo uno por hogar */
  es_autorizado: boolean;
  /** Estado de inclusión en el RUV */
  estado_inclusion: EstadoInclusion;
  estado_inclusion_display: string;
  /** Código Oracle legacy (calculado en backend) */
  tipo_persona: string;
  incluido_ruv: boolean;
  tiene_discapacidad: boolean;
  victima: string | null;
  victima_hash: string | null;
}

export interface HogarResumen {
  id: string;
  estado: EstadoHogar;
  estado_display: string;
  /** UUID de la Victima autorizada (titular de la entrevista) */
  autorizado: string;
  autorizado_hash: string;
  municipio: number | null;
  municipio_nombre: string | null;
  total_miembros: number;
  numero_personas: number;
  encuestador_nombre: string | null;
  created_at: string;
  updated_at: string;
}

export interface HogarDetalle extends HogarResumen {
  tipo_vivienda: TipoVivienda;
  tipo_vivienda_display: string;
  condicion_ocupacion: CondicionOcupacion;
  condicion_ocupacion_display: string;
  estrato: number;
  numero_cuartos: number;
  observaciones: string;
  miembros: MiembroHogarResumen[];
  total_miembros: number;
  /** Caracterizaciones (sesiones de encuesta) asociadas al hogar — Sprint 13 */
  sesiones: SesionResumen[];
  total_sesiones: number;
}

// ── Encuestas ───────────────────────────────────────────────────────────────

export type EstadoSesion = 'INICIADA' | 'EN_PROGRESO' | 'COMPLETADA' | 'SUSPENDIDA';

export interface RespuestaEncuesta {
  id: number;
  sesion: string;
  pregunta: string;       // UUID (Sprint 7)
  pregunta_codigo: string;
  pregunta_texto: string;
  valor: string;
  updated_at: string;
}

export interface SesionResumen {
  id: string;
  hogar: string;
  instrumento: string;         // UUID de InstrumentoVersion (Sprint 7)
  instrumento_codigo?: string; // Código del perfil — necesario para descargar instrumento offline (Sprint 17)
  instrumento_nombre: string;
  instrumento_numero: string;  // p.ej. "V8"
  encuestador: string | null;
  encuestador_nombre: string | null;
  estado: EstadoSesion;
  estado_display: string;
  porcentaje_completado: number;
  fecha_inicio: string;
  fecha_fin: string | null;
  created_at: string;
  updated_at: string;
}

export interface SesionDetalle extends SesionResumen {
  observaciones: string;
  respuestas: RespuestaEncuesta[];
  total_respuestas: number;
}

// ── Paginación ──────────────────────────────────────────────────────────────

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

// ── Repositorio externo (VictimaRepository DTOs) ─────────────────────────────

export interface HechoResumenFuente {
  codigo: string;
  nombre: string;
  fecha_hecho: string | null;     // ISO date 'YYYY-MM-DD'
  municipio_hecho: string | null;
}

export interface VictimaResumenFuente {
  cons_persona: number | null;
  tipo_documento: string;         // 'CC', 'CE', 'TI', 'RC', 'PA'
  numero_documento: string;
  primer_nombre: string;
  segundo_nombre: string;
  primer_apellido: string;
  segundo_apellido: string;
  fecha_nacimiento: string;       // ISO date 'YYYY-MM-DD'
  genero: 'M' | 'F' | 'NB' | 'ND';
  estado_ruv: 'INCLUIDO' | 'NO_INCLUIDO' | 'EN_PROCESO' | 'EXCLUIDO';
  habilitado_para_caracterizacion: boolean;
  fecha_ult_caracterizacion: string | null;  // ISO datetime
  pertenencia_etnica: string;
  pueblo_indigena: string;
  discapacidad: boolean;
  tipo_discapacidad: string;
  hechos_victimizantes: HechoResumenFuente[];
  municipio_residencia_codigo: string | null;
  municipio_residencia_nombre: string | null;
  fuente_origen: string;
}

export interface ResultadoBusquedaFuente {
  encontrado: boolean;
  victima: VictimaResumenFuente | null;
  fuente: string;
  mensaje: string;
}
