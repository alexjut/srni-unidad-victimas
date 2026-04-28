// Root layout — inicializa DB, perfil y sync. La navegación vive en los _layout de grupo.
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

  useEffect(() => {
    initDatabase().catch(() => {});
    cargarPerfil();
  }, []);

  useEffect(() => {
    if (usuario) inicializar();
  }, [usuario?.id]);

  return (
    <PaperProvider theme={govTheme}>
      <StatusBar style="light" backgroundColor="#1565C0" />
      <Stack screenOptions={{ headerShown: false }} />
    </PaperProvider>
  );
}
