/**
 * Reglas del cambio de contraseña, del lado del teléfono.
 *
 * Están acá y no dentro de la pantalla para poder probarlas: el servidor es quien
 * manda —vuelve a validar todo y tiene la última palabra—, pero pedirle un viaje
 * para enterarse de que las dos copias no coinciden es gastarle a la encuestadora
 * la señal que quizá no tenga.
 */

/** El mínimo que exige el servidor (`CambiarPasswordSerializer`). */
export const LARGO_MINIMO = 10;

export interface EntradaCambioPassword {
  actual: string;
  nueva: string;
  confirmacion: string;
}

/** Errores por campo. Vacío = se puede enviar. */
export function validarCambioPassword(
  { actual, nueva, confirmacion }: EntradaCambioPassword,
): Record<string, string> {
  const e: Record<string, string> = {};

  if (!actual) e.actual = 'Escriba su contraseña actual';

  if (nueva.length < LARGO_MINIMO) {
    e.nueva = `Debe tener al menos ${LARGO_MINIMO} caracteres`;
  } else if (actual && nueva === actual) {
    // Cambiarla por la misma deja la provisional viva, que es justo lo que este
    // cambio viene a evitar. El servidor lo aceptaría.
    e.nueva = 'La nueva contraseña debe ser distinta de la actual';
  }

  if (confirmacion !== nueva) {
    e.confirmacion = 'Las contraseñas nuevas no coinciden';
  }

  return e;
}
