/**
 * Qué hacer con la sesión que devuelve `POST /api/encuestas/`.
 *
 * El servidor aplica «un hogar → una caracterización abierta»: si el hogar ya
 * tiene una sin completar de este encuestador, NO crea otra y devuelve esa con
 * 200, sin mirar el instrumento pedido. La pantalla de caracterizar la trataba
 * siempre como recién creada, y de ahí salían los atascos que reportó campo:
 *
 *  - Se pedía otro instrumento: la app entraba a la entrevista vieja con el
 *    instrumento nuevo en los parámetros. El formulario activaba el perfil de la
 *    sesión y el capítulo creaba el borrador con el otro → la encuestadora quedaba
 *    «dentro» de la anterior sin entender por qué, y solo salía abandonándola.
 *  - La anterior se finalizó sin señal (borrador CERRADO_LOCAL, cierre en cola):
 *    para el servidor sigue abierta, así que «nueva caracterización» devolvía
 *    esa misma, que en el teléfono ya no deja hacer nada.
 *  - Se retomaba la misma entrevista: volvía a pedir la ubicación de atención y
 *    la sobrescribía.
 *
 * Función pura: la pantalla hace la red y la navegación.
 */

export interface SesionDevuelta {
  id: string;
  instrumento: string;
  instrumento_codigo?: string | null;
  estado: string;
  punto_atencion?: number | null;
  total_respuestas?: number;
}

export interface InstrumentoPedido {
  id: string;
  codigo: string;
}

export type DecisionSesion =
  /** Sesión nueva de verdad: seguir a la ubicación de atención. */
  | { tipo: 'NUEVA' }
  /** La misma entrevista ya empezada: ir directo al formulario. */
  | { tipo: 'RETOMAR' }
  /** Hay una abierta de OTRO instrumento: avisar, no entrar a ciegas. */
  | { tipo: 'OTRO_INSTRUMENTO' }
  /** La abierta ya se cerró en este teléfono y su cierre sigue en la cola. */
  | { tipo: 'CERRADA_SIN_ENVIAR' };

export function mismoInstrumento(sesion: SesionDevuelta, pedido: InstrumentoPedido): boolean {
  // El código es la identidad del perfil; el UUID cambia entre versiones del
  // mismo instrumento, así que solo se usa si el servidor no mandó el código.
  if (sesion.instrumento_codigo && pedido.codigo) {
    return sesion.instrumento_codigo === pedido.codigo;
  }
  return sesion.instrumento === pedido.id;
}

export function yaEmpezada(sesion: SesionDevuelta): boolean {
  return (
    sesion.estado !== 'INICIADA'
    || sesion.punto_atencion != null
    || (sesion.total_respuestas ?? 0) > 0
  );
}

/**
 * @param estadoBorradorLocal estado del borrador del teléfono vinculado a esa
 *   sesión (`borradoresDao.findBySesionId`), o null si no hay.
 */
export function decidirSesionDevuelta(
  sesion: SesionDevuelta,
  pedido: InstrumentoPedido,
  estadoBorradorLocal: string | null,
): DecisionSesion {
  // Primero el cierre pendiente: aunque sea del mismo instrumento, entrar ahí no
  // sirve de nada — está cerrada y no admite otra finalización.
  if (estadoBorradorLocal === 'CERRADO_LOCAL') return { tipo: 'CERRADA_SIN_ENVIAR' };
  if (!mismoInstrumento(sesion, pedido)) return { tipo: 'OTRO_INSTRUMENTO' };
  return yaEmpezada(sesion) ? { tipo: 'RETOMAR' } : { tipo: 'NUEVA' };
}
