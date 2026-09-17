/**
 * Atasco reportado por QA: «se quedó bugeada una caracterización y nos tocó
 * salirnos para poder hacer otra». El servidor devuelve la sesión abierta del
 * hogar en vez de crear una nueva; estos tests fijan qué hace la app con ella.
 *
 * Función pura — sin mocks, sin I/O.
 */
import { decidirSesionDevuelta, mismoInstrumento, yaEmpezada, type SesionDevuelta } from '../sesionAbierta';

const TERRITORIAL = { id: 'uuid-territorial-v8', codigo: 'TERRITORIAL' };
const BUENAVENTURA = { id: 'uuid-buenaventura', codigo: 'BUENAVENTURA' };

function sesion(over: Partial<SesionDevuelta> = {}): SesionDevuelta {
  return {
    id: 'ses-1',
    instrumento: 'uuid-territorial-v8',
    instrumento_codigo: 'TERRITORIAL',
    estado: 'INICIADA',
    punto_atencion: null,
    total_respuestas: 0,
    ...over,
  };
}

describe('decidirSesionDevuelta', () => {
  it('sesión recién creada del instrumento pedido → NUEVA (pide ubicación)', () => {
    expect(decidirSesionDevuelta(sesion(), TERRITORIAL, null)).toEqual({ tipo: 'NUEVA' });
  });

  it('abierta de OTRO instrumento → OTRO_INSTRUMENTO, no se entra a ciegas', () => {
    const abierta = sesion({ estado: 'EN_PROGRESO', total_respuestas: 40 });
    expect(decidirSesionDevuelta(abierta, BUENAVENTURA, null)).toEqual({ tipo: 'OTRO_INSTRUMENTO' });
  });

  it('otro instrumento aunque la abierta no tenga ni una respuesta', () => {
    expect(decidirSesionDevuelta(sesion(), BUENAVENTURA, null)).toEqual({ tipo: 'OTRO_INSTRUMENTO' });
  });

  it('misma entrevista con respuestas → RETOMAR (no vuelve a pedir ubicación)', () => {
    const abierta = sesion({ estado: 'EN_PROGRESO', total_respuestas: 12 });
    expect(decidirSesionDevuelta(abierta, TERRITORIAL, null)).toEqual({ tipo: 'RETOMAR' });
  });

  it('misma entrevista con ubicación ya guardada pero sin respuestas → RETOMAR', () => {
    expect(decidirSesionDevuelta(sesion({ punto_atencion: 7 }), TERRITORIAL, null))
      .toEqual({ tipo: 'RETOMAR' });
  });

  it('finalizada sin señal (cierre en cola) → CERRADA_SIN_ENVIAR, aun con el mismo instrumento', () => {
    const abierta = sesion({ estado: 'EN_PROGRESO', total_respuestas: 90 });
    expect(decidirSesionDevuelta(abierta, TERRITORIAL, 'CERRADO_LOCAL'))
      .toEqual({ tipo: 'CERRADA_SIN_ENVIAR' });
  });

  it('el cierre pendiente pesa más que el cambio de instrumento', () => {
    expect(decidirSesionDevuelta(sesion(), BUENAVENTURA, 'CERRADO_LOCAL'))
      .toEqual({ tipo: 'CERRADA_SIN_ENVIAR' });
  });

  it('un borrador local EN_PROGRESO no bloquea: se retoma', () => {
    const abierta = sesion({ estado: 'EN_PROGRESO', total_respuestas: 3 });
    expect(decidirSesionDevuelta(abierta, TERRITORIAL, 'EN_PROGRESO')).toEqual({ tipo: 'RETOMAR' });
  });
});

describe('mismoInstrumento', () => {
  it('compara por código: otra versión del mismo perfil sigue siendo el mismo', () => {
    expect(mismoInstrumento(sesion({ instrumento: 'uuid-territorial-v7' }), TERRITORIAL)).toBe(true);
  });

  it('sin código del servidor, cae al UUID', () => {
    expect(mismoInstrumento(sesion({ instrumento_codigo: null }), TERRITORIAL)).toBe(true);
    expect(mismoInstrumento(sesion({ instrumento_codigo: null }), BUENAVENTURA)).toBe(false);
  });
});

describe('yaEmpezada', () => {
  it('INICIADA sin ubicación ni respuestas no está empezada', () => {
    expect(yaEmpezada(sesion())).toBe(false);
  });

  it('cualquier estado distinto de INICIADA cuenta como empezada', () => {
    expect(yaEmpezada(sesion({ estado: 'EN_PROGRESO' }))).toBe(true);
  });
});
