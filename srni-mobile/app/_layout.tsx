/**
 * Root layout — solo inicializa servicios y renderiza el Stack.
 *
 * REGLA: este archivo NO navega. Toda lógica de redirección
 * vive en los _layout de cada grupo ((auth) y (main)) mediante
 * el componente <Redirect /> de expo-router, que se evalúa
 * durante el render — nunca antes del mount del Stack.
 */
import { useEffect } from 'react';
import { Stack } from 'expo-router';
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

export default function RootLayout() {
  const { cargarPerfil, usuario } = useAuthStore();
  const { inicializar } = useSyncStore();

  // 1. Inicializar DB y cargar perfil al arrancar
  useEffect(() => {
    initDatabase().catch(console.error);
    cargarPerfil();
  }, []);

  // 2. Inicializar sync cuando el usuario quede autenticado
  useEffect(() => {
    if (usuario) {
      inicializar();
    }
  }, [usuario?.id]);   // solo cuando cambia el ID (login / logout)

  return (
    <PaperProvider theme={srniTheme}>
      <StatusBar style="light" backgroundColor="#1565C0" />
      <Stack screenOptions={{ headerShown: false }} />
    </PaperProvider>
  );
}
