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
import { PaperProvider } from 'react-native-paper';
import { StatusBar } from 'expo-status-bar';

import { useAuthStore } from '../src/stores/authStore';
import { useSyncStore } from '../src/stores/syncStore';
import { initDatabase } from '../src/db/schema';
import { govTheme } from '../src/theme/govTheme';

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
    <PaperProvider theme={govTheme}>
      <StatusBar style="light" backgroundColor="#1565C0" />
      <Stack screenOptions={{ headerShown: false }} />
    </PaperProvider>
  );
}
