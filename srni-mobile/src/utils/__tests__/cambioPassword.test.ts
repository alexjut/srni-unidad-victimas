/**
 * Las 10 encuestadoras que llegaron de VIVANTO el 16-sep-2026 recibieron una
 * contraseña PROVISIONAL, y hasta hoy no tenían dónde cambiarla desde el
 * teléfono. Estas reglas son las que se comprueban antes de gastar señal.
 */
import { validarCambioPassword, LARGO_MINIMO } from '../cambioPassword';

const ok = { actual: 'Sicav.ht9pqm', nueva: 'MiClaveNueva2026', confirmacion: 'MiClaveNueva2026' };

describe('validarCambioPassword', () => {
  it('una entrada correcta no tiene errores', () => {
    expect(validarCambioPassword(ok)).toEqual({});
  });

  it('exige la contraseña actual', () => {
    expect(validarCambioPassword({ ...ok, actual: '' })).toHaveProperty('actual');
  });

  it('exige el largo mínimo que pide el servidor', () => {
    const corta = 'a'.repeat(LARGO_MINIMO - 1);
    const r = validarCambioPassword({ ...ok, nueva: corta, confirmacion: corta });

    expect(r.nueva).toContain(String(LARGO_MINIMO));
  });

  it('acepta exactamente el largo mínimo', () => {
    const justa = 'a'.repeat(LARGO_MINIMO);
    expect(validarCambioPassword({ ...ok, nueva: justa, confirmacion: justa })).toEqual({});
  });

  it('rechaza repetir la actual: dejaría viva la provisional', () => {
    // El servidor lo aceptaría; el sentido del cambio es retirar esa clave.
    const r = validarCambioPassword({ actual: ok.actual, nueva: ok.actual, confirmacion: ok.actual });

    expect(r.nueva).toBe('La nueva contraseña debe ser distinta de la actual');
  });

  it('avisa si las dos copias no coinciden, sin ir al servidor', () => {
    const r = validarCambioPassword({ ...ok, confirmacion: 'otra cosa distinta' });

    expect(r.confirmacion).toBe('Las contraseñas nuevas no coinciden');
  });

  it('una nueva corta se marca por el largo, no por la confirmación vacía', () => {
    const r = validarCambioPassword({ actual: 'x', nueva: 'corta', confirmacion: 'corta' });

    expect(r.nueva).toBeDefined();
    expect(r.confirmacion).toBeUndefined();
  });
});
