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
  estado_ruv: 'INCLUIDO' | 'NO_INCLUIDO' | 'EN_PROCESO' | 'EXCLUIDO' | 'NO_VERIFICADO';
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
export type EstadoInclusion = 'INCLUIDO' | 'NO_INCLUIDO' | 'NO_VERIFICADO';

export interface MiembroHogarResumen {
  id: string;
  /**
   * Sprint 21 — nombre completo del miembro. Solo visible para encuestadores
   * con `puede_caracterizar`. Vive en memoria del cliente, NUNCA se persiste
   * en SQLite. Puede venir vacío si el miembro no se ha completado.
   */
  nombre_completo: string;
  /**
   * Las partes del nombre y el documento, por separado (backend del 11-sep-2026).
   *
   * Opcionales porque una APK nueva puede estar hablando con un backend que
   * todavía no los manda, y porque los resúmenes reconstruidos desde la caché
   * sin conexión pueden no tenerlos. Quien los consuma debe conservar el
   * respaldo de partir `nombre_completo`.
   *
   * Existen porque sin ellos el integrante que NO es el autorizado llegaba a la
   * encuesta con el primer nombre y nada más: partir la cadena en el cliente no
   * distingue a «José Luis Vargas Mora» de «José Vargas Mora», y adivinarlo le
   * escribe a alguien un apellido que no es el suyo.
   */
  primer_nombre?: string;
  segundo_nombre?: string;
  primer_apellido?: string;
  segundo_apellido?: string;
  numero_documento?: string;
  tipo_documento_codigo?: string;
  parentesco: Parentesco | '';
  parentesco_display: string;
  genero: 'M' | 'F' | 'NB' | 'ND';
  fecha_nacimiento: string | null;   // ISO date — NO indexado en backend
  /**
   * Retiro del hogar (backend del 11-sep-2026). `null` = sigue perteneciendo.
   *
   * Es la fecha del HECHO, no la del registro: la familia informa en septiembre
   * un fallecimiento de marzo, y ese es el caso corriente.
   *
   * El integrante retirado **se sigue mostrando** —para que nadie crea que se
   * perdió— pero sus filas de preguntas quedan inactivas con el motivo a la
   * vista, y no cuentan para el avance. Ver `esSoloLectura` y `progreso.ts`.
   *
   * Opcional porque una APK nueva puede estar hablando con un backend anterior,
   * y porque los resúmenes reconstruidos de la caché sin conexión no lo traen.
   */
  retirado_en?: string | null;
  motivo_retiro?: string;
  motivo_retiro_display?: string;
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
  estado_ruv: 'INCLUIDO' | 'NO_INCLUIDO' | 'EN_PROCESO' | 'EXCLUIDO' | 'NO_VERIFICADO';
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
  /**
   * Las OTRAS personas que comparten el documento buscado. Normalmente vacío.
   *
   * El backend lo manda desde que se distingue un duplicado de la fuente de una
   * ambigüedad real; si esta lista trae algo, la pantalla DEBE pedir
   * confirmación en vez de mostrar `victima` como si fuera la única. Sin este
   * campo declarado, el cliente descartaba el dato en silencio y la ambigüedad
   * se preguntaba sin red pero se ocultaba con red.
   */
  candidatos?: VictimaResumenFuente[];
  /**
   * El documento buscado es un valor de RELLENO del padrón ('99', '0', '999999'):
   * no identifica a nadie. Distinto de "no está en el padrón" — la persona puede
   * existir, pero ese número no sirve para encontrarla.
   */
  no_identificante?: boolean;
  /**
   * Motivo enumerado del veredicto, además del texto de `mensaje`.
   *
   * Sin esto la app solo podía pintar la cadena y por eso un bloqueo previsto
   * —"ficha vigente"— se leía en campo como una falla del sistema: no había
   * forma de saber en qué caso estábamos para ofrecer la salida correcta.
   *
   * `FICHA_VIGENTE` habilita el botón de ruta de excepción; `NO_EN_PADRON`, el
   * alta manual.
   */
  motivo?: string;
  /** Desde cuándo se podrá recaracterizar por la ruta general (fecha + 2 años). */
  disponible_desde?: string | null;
}
