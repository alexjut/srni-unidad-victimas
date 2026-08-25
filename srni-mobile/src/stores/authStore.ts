/**
 * Store de autenticación con Zustand.
 * Los tokens viven SOLO en expo-secure-store (keychain nativo).
 * El estado en memoria solo guarda el perfil del usuario y flags de sesión.
 */
import { create } from 'zustand';
import * as SecureStore from 'expo-secure-store';
import * as LocalAuthentication from 'expo-local-authentication';
import { authApi, type UsuarioMe } from '../api/auth';
import { precargarEnSegundoPlano } from '../services/precarga';
import * as precargaDao from '../db/precargaDao';
import * as colaDao from '../db/colaDao';
import * as filtroUniverso from '../services/filtroUniverso';

const KEY_BIOMETRICO = 'biometrico_habilitado';
// Perfil del usuario cacheado en el keychain. Permite rehidratar la sesión al
// arrancar SIN red: sin esto, cargarPerfil() no tenía de dónde sacar el usuario
// cuando `me()` fallaba por falta de señal, y terminaba borrando los tokens.
const KEY_PERFIL = 'perfil_cache';

interface AuthState {
  usuario: UsuarioMe | null;
  cargando: boolean;
  /** true una vez que cargarPerfil() terminó (con o sin sesión activa). */
  perfilCargado: boolean;
  error: string | null;

  // Acciones
  login: (codigo: string, password: string, activarBiometria?: boolean) => Promise<void>;
  loginBiometrico: () => Promise<void>;
  logout: () => Promise<void>;
  cargarPerfil: () => Promise<void>;
  limpiarError: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  usuario: null,
  cargando: false,
  perfilCargado: false,
  error: null,

  login: async (codigo, password, activarBiometria = false) => {
    set({ cargando: true, error: null });
    try {
      const { data } = await authApi.login({
        codigo_usuario: codigo.trim().toUpperCase(),
        password,
      });

      await SecureStore.setItemAsync('access_token', data.access);
      await SecureStore.setItemAsync('refresh_token', data.refresh);

      // #22 — biometría OPT-IN: solo se habilita si el usuario lo eligió
      // explícitamente (checkbox del login) y el dispositivo la soporta. Antes
      // se auto-activaba en silencio, registrando la huella sin consentimiento.
      try {
        if (activarBiometria) {
          const hw = await LocalAuthentication.hasHardwareAsync();
          const enrolled = await LocalAuthentication.isEnrolledAsync();
          if (hw && enrolled) await SecureStore.setItemAsync(KEY_BIOMETRICO, 'true');
        } else {
          // No eligió biometría → asegurar que quede deshabilitada (toggle off).
          await SecureStore.deleteItemAsync(KEY_BIOMETRICO);
        }
      } catch { /* silencioso — la biometría es opcional */ }

      const { data: me } = await authApi.me();
      await SecureStore.setItemAsync(KEY_PERFIL, JSON.stringify(me));
      set({ usuario: me, cargando: false });

      // Fase 0 offline: precargar el padrón/jornada/paramétricas en segundo
      // plano. NO bloquea el login ni lo hace fallar si la precarga falla.
      precargarEnSegundoPlano();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Error al iniciar sesión. Verifica tus credenciales.';
      set({ error: msg, cargando: false });
      throw err;
    }
  },

  loginBiometrico: async () => {
    set({ cargando: true, error: null });
    try {
      const result = await LocalAuthentication.authenticateAsync({
        promptMessage: 'Accede al SRNI con tu huella digital',
        cancelLabel: 'Cancelar',
        fallbackLabel: 'Usar contraseña',
        disableDeviceFallback: false,
      });

      if (!result.success) {
        set({ cargando: false });
        return; // usuario canceló, no es error
      }

      const refresh = await SecureStore.getItemAsync('refresh_token');
      if (!refresh) {
        set({
          error: 'No hay sesión guardada. Ingresa primero con tu contraseña.',
          cargando: false,
        });
        throw new Error('SIN_TOKEN');
      }

      const { data } = await authApi.refresh(refresh);
      await SecureStore.setItemAsync('access_token', data.access);
      await SecureStore.setItemAsync('refresh_token', data.refresh);

      const { data: me } = await authApi.me();
      await SecureStore.setItemAsync(KEY_PERFIL, JSON.stringify(me));
      set({ usuario: me, cargando: false });

      // Fase 0 offline: refrescar la precarga tras re-autenticación biométrica
      // (con red). NO bloquea ni hace fallar el flujo.
      precargarEnSegundoPlano();
    } catch (err: unknown) {
      if ((err as Error).message !== 'SIN_TOKEN') {
        set({ error: 'No se pudo autenticar. Intenta de nuevo.', cargando: false });
      }
      throw err;
    }
  },

  logout: async () => {
    // #22b — si el ingreso biométrico está activo, "cerrar sesión" CONSERVA el
    // refresh_token y la preferencia de huella para volver a entrar con huella
    // sin contraseña (celular personal del encuestador). Si NO está activo, se
    // limpia todo como antes (más seguro para celular compartido).
    const biometricoActivo = (await SecureStore.getItemAsync(KEY_BIOMETRICO)) === 'true';
    try {
      const refresh = await SecureStore.getItemAsync('refresh_token');
      // Con biometría activa NO invalidamos el refresh en el servidor: debe
      // seguir sirviendo para la re-autenticación por huella.
      if (refresh && !biometricoActivo) await authApi.logout(refresh);
    } finally {
      await SecureStore.deleteItemAsync('access_token');
      if (!biometricoActivo) {
        await SecureStore.deleteItemAsync('refresh_token');
        await SecureStore.deleteItemAsync(KEY_BIOMETRICO);
        await SecureStore.deleteItemAsync(KEY_PERFIL);
      }
      // Privacidad: borrar el almacén offline al cerrar sesión. Si NO hay nada
      // pendiente de sincronizar, se borra TODO (incluida la PII capturada de
      // víctimas/hogares) para que no quede para el siguiente usuario. Si hay
      // pendientes, solo se limpia la precarga (no se pierde el trabajo de campo).
      try {
        const pendientes = await colaDao.contarPendientes();
        if (pendientes === 0) {
          await precargaDao.limpiarTodoOffline();
        } else {
          await precargaDao.limpiarPrecarga();
        }
        // El filtro del universo es un archivo aparte, así que no se lo lleva
        // el DELETE de las tablas. En los dos casos se borra: sus parámetros
        // viven en `meta_offline`, que sí se vacía, y dejarlo huérfano solo
        // ocuparía 22,7 MB que nadie puede consultar.
        filtroUniverso.borrarFiltro();
      } catch { /* best-effort */ }
      set({ usuario: null, error: null });
    }
  },

  cargarPerfil: async () => {
    const token = await SecureStore.getItemAsync('access_token');
    if (!token) {
      set({ perfilCargado: true });
      return;
    }
    try {
      const { data } = await authApi.me();
      await SecureStore.setItemAsync(KEY_PERFIL, JSON.stringify(data));
      set({ usuario: data, perfilCargado: true });
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status;
      // Solo un rechazo de credenciales (401/403) invalida la sesión. El
      // interceptor del cliente ya intentó refrescar el token antes de llegar
      // acá, así que un 401 acá significa que el refresh TAMBIÉN falló.
      if (status === 401 || status === 403) {
        await SecureStore.deleteItemAsync('access_token');
        await SecureStore.deleteItemAsync('refresh_token');
        await SecureStore.deleteItemAsync(KEY_PERFIL);
        set({ usuario: null, perfilCargado: true });
        return;
      }
      // Sin respuesta (sin red / timeout) o error del servidor (5xx): NO se
      // cierra la sesión. Se rehidrata el perfil del caché para que la app
      // siga usable sin señal — sacar a la encuestadora del sistema en pleno
      // campo, y encima borrarle el token, era pérdida de jornada.
      try {
        const cache = await SecureStore.getItemAsync(KEY_PERFIL);
        if (cache) {
          set({ usuario: JSON.parse(cache) as UsuarioMe, perfilCargado: true });
          return;
        }
      } catch { /* caché corrupto: cae al cierre de abajo */ }
      // Sin caché (primer arranque sin red tras instalar): se conserva el
      // token para el próximo arranque con señal, pero sin perfil no hay a
      // quién mostrar. perfilCargado marca que el intento terminó.
      set({ perfilCargado: true });
    }
  },

  limpiarError: () => set({ error: null }),
}));
