/**
 * Root layout — inicializa la app:
 * 1. Abre la base de datos SQLite offline
 * 2. Carga perfil desde SecureStore (si hay token guardado)
 * 3. Redirige al login si no hay sesión activa
 */
import { useEffect } from 'react';
import { Stack, router, useSegments } from 'expo-router';
import { PaperProvider, MD3LightTheme } from 'react-native-paper';
import { StatusBar } from 'expo-status-bar';

import { useAuthStore } from '../src/stores/authStore';
import { initDatabase } from '../src/db/schema';

// Colores institucionales Unidad para las Víctimas
const srniTheme = {
  ...MD3LightTheme,
  colors: {
    ...MD3LightTheme.colors,
    primary: '#1565C0',       // Azul institucional
    primaryContainer: '#BBDEFB',
    secondary: '#FFC107',     // Amarillo
    secondaryContainer: '#FFF8E1',
    error: '#C62828',
    background: '#F5F5F5',
    surface: '#FFFFFF',
    onPrimary: '#FFFFFF',
  },
};

function AuthGuard() {
  const { usuario, cargarPerfil } = useAuthStore();
  const segments = useSegments();

  useEffect(() => {
    cargarPerfil();
  }, []);

  useEffect(() => {
    const inAuthGroup = segments[0] === '(auth)';

    if (!usuario && !inAuthGroup) {
      router.replace('/(auth)/login');
    } else if (usuario && inAuthGroup) {
      router.replace('/(main)');
    }
  }, [usuario, segments]);

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
