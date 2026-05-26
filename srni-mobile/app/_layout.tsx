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
import { activarLogsRemoto, log } from '../src/services/logger';
import { asegurarInstrumentoLocal, listaPerfilesBundled } from '../src/services/bundledInstrumentos';

// Activar logs remotos lo más temprano posible (a nivel módulo) — antes
// de que cualquier console.warn/error ocurra en el resto de la app.
activarLogsRemoto();

export default function RootLayout() {
  const { cargarPerfil, usuario } = useAuthStore();
  const { inicializar } = useSyncStore();

  useEffect(() => {
    log.event('APP', 'RootLayout montado — iniciando BD y perfil');
    (async () => {
      try {
        await initDatabase();
        log.event('APP', 'initDatabase OK');
      } catch (e) {
        reportarExcepcion(e, '[RootLayout] initDatabase');
      }
      cargarPerfil().catch((e) => reportarExcepcion(e, '[RootLayout] cargarPerfil'));
    })();
  }, []);

  useEffect(() => {
    if (usuario) {
      log.event('AUTH', `Usuario cargado: ${usuario.codigo_usuario}`);
      inicializar().catch((e) => reportarExcepcion(e, '[RootLayout] syncStore.inicializar'));

      // Sprint 18: cargar el instrumento por defecto desde el bundle.
      // Los demás se cargan on-demand cuando el usuario elija uno distinto
      // (es más rápido cargar uno-a-uno que precalentar los 8 en paralelo
      // — SQLite serializa los writes igualmente).
      (async () => {
        try {
          await asegurarInstrumentoLocal('TERRITORIAL');
          log.event('BUNDLE', 'Default TERRITORIAL listo en SQLite');
        } catch (e) {
          reportarExcepcion(e, '[RootLayout] precarga bundle TERRITORIAL');
        }
      })();
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
