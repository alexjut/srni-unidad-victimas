// Root layout — inicializa DB, perfil y sync. La navegación vive en los _layout de grupo.
import { useEffect } from 'react';
import { Stack } from 'expo-router';
import { PaperProvider } from 'react-native-paper';
import { StatusBar } from 'expo-status-bar';

import { useAuthStore } from '../src/stores/authStore';
import { useSyncStore } from '../src/stores/syncStore';
import { initDatabase } from '../src/db/schema';
import { govTheme } from '../src/theme/govTheme';
import { ErrorBoundary } from '../src/components/ErrorBoundary';
import { reportarExcepcion } from '../src/services/errorReporter';

export default function RootLayout() {
  const { cargarPerfil, usuario } = useAuthStore();
  const { inicializar } = useSyncStore();

  useEffect(() => {
    // CRÍTICO: esperar a que initDatabase termine ANTES de cualquier otra
    // operación que use la BD (cargarPerfil → JWT en SecureStore es ok,
    // pero el syncStore.inicializar() usa colaDao que necesita la BD).
    (async () => {
      try {
        await initDatabase();
      } catch (e) {
        console.warn('[RootLayout] initDatabase falló:', e);
        reportarExcepcion(e, '[RootLayout] initDatabase');
      }
      cargarPerfil().catch((e) => reportarExcepcion(e, '[RootLayout] cargarPerfil'));
    })();
  }, []);

  useEffect(() => {
    if (usuario) {
      inicializar().catch((e) => reportarExcepcion(e, '[RootLayout] syncStore.inicializar'));
    }
  }, [usuario?.id]);

  return (
    <ErrorBoundary>
      <PaperProvider theme={govTheme}>
        <StatusBar style="light" backgroundColor="#1565C0" />
        <Stack screenOptions={{ headerShown: false }} />
      </PaperProvider>
    </ErrorBoundary>
  );
}
