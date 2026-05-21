/**
 * Tests del módulo IA mobile.
 *
 * Cubre:
 * - iaApi.mapearAudio: llamada correcta al backend
 * - iaStore: transiciones de estado
 * - iaStore.activar: registra consentimiento y cambia estado
 * - iaStore.enviarTexto: procesando → sugerida / error
 * - iaStore.aceptarSugerencia: devuelve valor y limpia estado
 * - iaStore.rechazarSugerencia: limpia estado
 */
import { iaApi } from '../../api/ia';
import { useIAStore } from '../../stores/iaStore';

// Mock de apiClient — el módulo exporta el cliente como default
jest.mock('../../api/client', () => {
  const mock = {
    get: jest.fn(),
    post: jest.fn(),
  };
  return { __esModule: true, default: mock, apiClient: mock };
});

// Importar DESPUÉS del mock para que Jest inyecte el stub
import apiClientModule from '../../api/client';
const mockPost = (apiClientModule as any).post as jest.MockedFunction<any>;
const mockGet = (apiClientModule as any).get as jest.MockedFunction<any>;

// ─────────────────────────────────────────────────────────────────────────────
// iaApi
// ─────────────────────────────────────────────────────────────────────────────

describe('iaApi', () => {
  beforeEach(() => jest.clearAllMocks());

  it('registrarConsentimiento llama al endpoint correcto', async () => {
    mockPost.mockResolvedValueOnce({
      data: { id: 'c-123', acepto: true, firma_digital: 'abc', creado_en: '2026-04-19T00:00:00Z' },
    } as any);

    await iaApi.registrarConsentimiento({ sesion_encuesta_id: 's-1', acepto: true });

    expect(mockPost).toHaveBeenCalledWith('/api/ia/consentimiento/', {
      sesion_encuesta_id: 's-1',
      acepto: true,
    });
  });

  it('mapearAudio llama al endpoint correcto con payload', async () => {
    mockPost.mockResolvedValueOnce({
      data: { sugerencia: 'CASA', confianza: 1.0, modelo: 'gemini-1.5-flash' },
    } as any);

    const resultado = await iaApi.mapearAudio({
      sesion_encuesta_id: 's-1',
      pregunta_id: 'pregunta-uuid-1',
      texto_transcrito: 'Vivimos en una casa propia',
    });

    expect(mockPost).toHaveBeenCalledWith('/api/ia/mapear-audio/', {
      sesion_encuesta_id: 's-1',
      pregunta_id: 'pregunta-uuid-1',
      texto_transcrito: 'Vivimos en una casa propia',
    });
    expect(resultado.data.sugerencia).toBe('CASA');
  });

  it('estado llama a GET con query param', async () => {
    mockGet.mockResolvedValueOnce({
      data: { activo: true, consentimiento_id: 'c-1', sesion_ia_id: null, total_llamadas: 0 },
    } as any);

    await iaApi.estado('sesion-uuid-1');

    expect(mockGet).toHaveBeenCalledWith('/api/ia/estado/', {
      params: { sesion_encuesta_id: 'sesion-uuid-1' },
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// iaStore — transiciones de estado
// ─────────────────────────────────────────────────────────────────────────────

describe('iaStore', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Reset store al estado inicial
    useIAStore.getState().resetear();
  });

  it('estado inicial es inactivo y no activo', () => {
    const { estado, activo } = useIAStore.getState();
    expect(estado).toBe('inactivo');
    expect(activo).toBe(false);
  });

  it('activar — consentimiento exitoso → activo=true', async () => {
    mockPost.mockResolvedValueOnce({
      data: { id: 'consent-1', acepto: true, firma_digital: 'abc', creado_en: '' },
    } as any);

    await useIAStore.getState().activar('sesion-1');

    const { activo, estado, consentimientoId } = useIAStore.getState();
    expect(activo).toBe(true);
    expect(estado).toBe('inactivo');
    expect(consentimientoId).toBe('consent-1');
  });

  it('activar — error de red → activo=false', async () => {
    mockPost.mockRejectedValueOnce(new Error('network error'));

    await useIAStore.getState().activar('sesion-1');

    const { activo, errorMensaje } = useIAStore.getState();
    expect(activo).toBe(false);
    expect(errorMensaje).toBeTruthy();
  });

  it('iniciarGrabacion — cambia estado a grabando', () => {
    useIAStore.getState().iniciarGrabacion('pregunta-uuid-1');
    const { estado, preguntaActivaId } = useIAStore.getState();
    expect(estado).toBe('grabando');
    expect(preguntaActivaId).toBe('pregunta-uuid-1');
  });

  it('enviarTexto — éxito → estado sugerida con datos', async () => {
    mockPost.mockResolvedValueOnce({
      data: { sugerencia: 'CASA', confianza: 1.0, modelo: 'gemini-1.5-flash' },
    } as any);

    await useIAStore.getState().enviarTexto('sesion-1', 'pregunta-uuid-5', 'casa propia');

    const { estado, sugerencia } = useIAStore.getState();
    expect(estado).toBe('sugerida');
    expect(sugerencia?.sugerencia).toBe('CASA');
    expect(sugerencia?.confianza).toBe(1.0);
  });

  it('enviarTexto — error de red → estado error', async () => {
    mockPost.mockRejectedValueOnce(new Error('503'));

    await useIAStore.getState().enviarTexto('sesion-1', 'pregunta-uuid-5', 'casa');

    const { estado, errorMensaje } = useIAStore.getState();
    expect(estado).toBe('error');
    expect(errorMensaje).toBeTruthy();
  });

  it('aceptarSugerencia — devuelve la sugerencia y limpia estado', async () => {
    mockPost.mockResolvedValueOnce({
      data: { sugerencia: 'APARTAMENTO', confianza: 0.9, modelo: 'gemini-1.5-flash' },
    } as any);

    await useIAStore.getState().enviarTexto('s-1', 'pregunta-uuid-3', 'apartamento');
    const resultado = useIAStore.getState().aceptarSugerencia();

    expect(resultado?.sugerencia).toBe('APARTAMENTO');
    const { estado, sugerencia } = useIAStore.getState();
    expect(estado).toBe('inactivo');
    expect(sugerencia).toBeNull();
  });

  it('rechazarSugerencia — descarta sugerencia y vuelve a inactivo', async () => {
    mockPost.mockResolvedValueOnce({
      data: { sugerencia: 'X', confianza: 0.5, modelo: 'gemini-1.5-flash' },
    } as any);

    await useIAStore.getState().enviarTexto('s-1', 'pregunta-uuid-3', 'algo');
    useIAStore.getState().rechazarSugerencia();

    const { estado, sugerencia } = useIAStore.getState();
    expect(estado).toBe('inactivo');
    expect(sugerencia).toBeNull();
  });

  it('desactivar — limpia todo el estado IA', async () => {
    mockPost.mockResolvedValueOnce({
      data: { id: 'c-1', acepto: true, firma_digital: '', creado_en: '' },
    } as any);

    await useIAStore.getState().activar('s-1');
    useIAStore.getState().desactivar();

    const { activo, estado, consentimientoId } = useIAStore.getState();
    expect(activo).toBe(false);
    expect(estado).toBe('inactivo');
    expect(consentimientoId).toBeNull();
  });
});
