/**
 * Root layout — inicializa la app:
 *  1. Abre la base de datos SQLite y aplica migraciones
 *  2. Carga perfil desde SecureStore (si hay token guardado)
 *  3. Tras login: inicializa motor de sync (descarga instrumento si no existe,
 *     libera bloqueados, registra listener AppState)
 *  4. Redirige al login si no hay sesión activa
 */
import { useEffect, useRef } from 'react';
import { Stack, router, useSegments, useRootNavigationState } from 'expo-router';
import { PaperProvider, MD3LightTheme } from 'react-native-paper';
import { StatusBar } from 'expo-status-bar';

import { useAuthStore } from '../src/stores/authStore';
import { useSyncStore } from '../src/stores/syncStore';
import { initDatabase } from '../src/db/schema';

// Colores institucionales Unidad para las Víctimas
const srniTheme = {
  ...MD3LightTheme,
  colors: {
    ...MD3LightTheme.colors,
    primary: '#1565C0',
    primaryContainer: '#BBDEFB',
    secondary: '#FFC107',
    secondaryContainer: '#FFF8E1',
    error: '#C62828',
    background: '#F5F5F5',
    surface: '#FFFFFF',
    onPrimary: '#FFFFFF',
  },
};

function AuthGuard() {
  const { usuario, cargarPerfil } = useAuthStore();
  const { inicializar } = useSyncStore();
  const segments = useSegments();
  // navigationState.key es undefined hasta que el Stack esté completamente montado.
  // Nunca navegar antes de que key exista — este es el origen del Render Error.
  const navigationState = useRootNavigationState();
  const syncInitializado = useRef(false);

  useEffect(() => {
    cargarPerfil();
  }, []);

  // Inicializar sync una sola vez cuando el usuario queda autenticado
  useEffect(() => {
    if (usuario && !syncInitializado.current) {
      syncInitializado.current = true;
      inicializar();
    }
    if (!usuario) {
      syncInitializado.current = false;
    }
  }, [usuario]);

  useEffect(() => {
    // Esperar a que el navegador esté montado antes de redirigir
    if (!navigationState?.key) return;

    const inAuthGroup = segments[0] === '(auth)';
    if (!usuario && !inAuthGroup) {
      router.replace('/(auth)/login');
    } else if (usuario && inAuthGroup) {
      router.replace('/(main)');
    }
  }, [usuario, segments, navigationState?.key]);

  return null;
}

export default function RootLayout() {
  useEffect(() => {
    initDatabase().catch(console.error);
  }, []);

  return (
    <PaperProvider theme={srniTheme}>
      <StatusBar style="light" backgroundColor="#1565C0" />
      <AuthGuard />
      <Stack screenOptions={{ headerShown: false }} />
    </PaperProvider>
  );
}
