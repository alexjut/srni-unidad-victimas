/**
 * APK-002 — lo que ve el encuestador cuando algo falla al conformar el hogar.
 *
 * El reporte de QA decía «error intermitente, sin diagnóstico suficiente». Lo
 * intermitente era que el mismo intento fallaba distinto según hubiera red, la
 * víctima tuviera hogar de otro encuestador o el cuerpo viniera vacío — y las
 * tres cosas se veían igual de opacas porque se volcaba el JSON crudo.
 */
import { interpretarError, mensajeDeError } from '../errores';

describe('interpretarError', () => {
  it('sin respuesta del servidor dice que el trabajo no se pierde', () => {
    // El caso más común en campo. La acción es esperar, no reportar: si el
    // mensaje no lo dice, el encuestador cree que perdió lo que llevaba.
    const info = interpretarError({ message: 'Network Error' }, 'Falló algo.');

    expect(info.sinRed).toBe(true);
    expect(info.mensaje).toContain('Sin conexión');
    expect(info.mensaje).toContain('no se pierde');
  });

  it('muestra el texto del servidor tal cual cuando viene en detail', () => {
    // Los mensajes del backend ya están redactados para el encuestador
    // ("Solicita su reasignación al supervisor"). Reescribirlos sería peor.
    const detalle = 'Esta víctima ya tiene un hogar activo registrado por otro '
      + 'encuestador. Solicita su reasignación al supervisor.';
    const info = interpretarError(
      { response: { status: 409, data: { detail: detalle } } }, 'Falló algo.');

    expect(info.mensaje).toBe(detalle);
    expect(info.estado).toBe(409);
  });

  it('arma los errores por campo en vez de volcar el JSON', () => {
    const info = interpretarError({
      response: { status: 400, data: { autorizado: ['Este campo es requerido.'] } },
    }, 'Falló algo.');

    expect(info.mensaje).toBe('Persona autorizada: Este campo es requerido.');
    // Lo que NO debe pasar: que se vean llaves, comillas o nombres internos.
    expect(info.mensaje).not.toContain('{');
    expect(info.mensaje).not.toContain('autorizado');
  });

  it('un cuerpo nulo NO muestra la palabra «null»', () => {
    // El defecto exacto que reportó QA: `typeof null === 'object'` en
    // JavaScript, así que el `JSON.stringify` anterior imprimía "null" en
    // pantalla — lo más parecido a no decir nada.
    const info = interpretarError(
      { response: { status: 500, data: null } }, 'No se pudo crear el hogar.');

    expect(info.mensaje).not.toContain('null');
    expect(info.mensaje).toContain('No se pudo crear el hogar.');
    // Con el código, que es lo que le permite a soporte distinguir un 500 de un
    // 403 sin pedirle capturas a quien está en campo.
    expect(info.mensaje).toContain('500');
  });

  it('el diagnóstico técnico no viaja a la pantalla', () => {
    const info = interpretarError(
      { response: { status: 500, data: { traza: 'IntegrityError en la fila 42' } } },
      'No se pudo crear el hogar.');

    expect(info.diagnostico).toContain('500');
    expect(info.diagnostico).toContain('IntegrityError');
  });

  it('mensajeDeError devuelve solo el texto', () => {
    expect(mensajeDeError({ response: { status: 404, data: { detail: 'No existe.' } } }, 'x'))
      .toBe('No existe.');
  });
});
