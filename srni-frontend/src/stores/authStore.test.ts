import { describe, it, expect, beforeEach } from 'vitest';
import { useAuthStore } from './authStore';

beforeEach(() => {
  sessionStorage.clear();
  useAuthStore.setState({
    accessToken: null,
    refreshToken: null,
    usuario: null,
  });
});

describe('authStore', () => {
  it('inicia sin tokens ni usuario', () => {
    const state = useAuthStore.getState();
    expect(state.accessToken).toBeNull();
    expect(state.refreshToken).toBeNull();
    expect(state.usuario).toBeNull();
  });

  it('setTokens guarda en store y sessionStorage', () => {
    useAuthStore.getState().setTokens('access123', 'refresh456');

    const state = useAuthStore.getState();
    expect(state.accessToken).toBe('access123');
    expect(state.refreshToken).toBe('refresh456');
    expect(sessionStorage.getItem('access_token')).toBe('access123');
    expect(sessionStorage.getItem('refresh_token')).toBe('refresh456');
  });

  it('setUsuario guarda el perfil', () => {
    const usuario = {
      codigo_usuario: 'ALEXJUT',
      nombre_completo: 'Javier Aguilar',
      email: 'javier@test.com',
      perfil: {
        id: 1,
        nombre: 'Supervisor',
        puede_caracterizar: true,
        puede_buscar_rni: true,
      },
    };

    useAuthStore.getState().setUsuario(usuario);
    expect(useAuthStore.getState().usuario).toEqual(usuario);
  });

  it('logout limpia todo', () => {
    useAuthStore.getState().setTokens('a', 'r');
    useAuthStore.getState().setUsuario({
      codigo_usuario: 'TEST',
      nombre_completo: 'Test',
      email: '',
      perfil: null,
    });

    useAuthStore.getState().logout();

    const state = useAuthStore.getState();
    expect(state.accessToken).toBeNull();
    expect(state.refreshToken).toBeNull();
    expect(state.usuario).toBeNull();
    expect(sessionStorage.getItem('access_token')).toBeNull();
    expect(sessionStorage.getItem('refresh_token')).toBeNull();
  });
});
