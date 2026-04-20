/**
 * Dashboard del encuestador con indicador de estado de sincronización.
 */
import { View, ScrollView, StyleSheet } from 'react-native';
import { Text, Card, Button, Divider, Chip, ActivityIndicator } from 'react-native-paper';
import { router } from 'expo-router';
import { useAuthStore } from '../../src/stores/authStore';
import { useSyncStore, getEstadoSync } from '../../src/stores/syncStore';

const SYNC_CONFIG = {
  sincronizando: { label: 'Sincronizando…', color: '#1565C0', bg: '#E3F2FD' },
  pendientes:    { label: (n: number) => `${n} pendiente${n !== 1 ? 's' : ''}`, color: '#E65100', bg: '#FFF3E0' },
  sin_conexion:  { label: 'Sin conexión', color: '#616161', bg: '#F5F5F5' },
  error:         { label: (n: number) => `${n} error${n !== 1 ? 'es' : ''}`, color: '#C62828', bg: '#FFEBEE' },
  sincronizado:  { label: '✓ Sincronizado', color: '#2E7D32', bg: '#E8F5E9' },
} as const;

function SyncChip() {
  const syncState = useSyncStore();
  const estado = getEstadoSync(syncState);
  const { triggerSync, sincronizando, pendientesCola, erroresCola } = syncState;

  const cfg = SYNC_CONFIG[estado];
  const label =
    estado === 'sincronizando' ? cfg.label :
    estado === 'pendientes'    ? cfg.label(pendientesCola) :
    estado === 'error'         ? cfg.label(erroresCola) :
    (cfg as { label: string }).label;

  return (
    <Chip
      mode="flat"
      style={{ backgroundColor: cfg.bg }}
      textStyle={{ color: cfg.color, fontSize: 11 }}
      onPress={estado !== 'sincronizando' ? triggerSync : undefined}
      icon={sincronizando ? undefined : estado === 'sin_conexion' ? 'wifi-off' : estado === 'error' ? 'alert-circle' : 'cloud-sync'}
    >
      {sincronizando ? '…' : label}
    </Chip>
  );
}

export default function DashboardScreen() {
  const { usuario, logout } = useAuthStore();
  const perfil = usuario?.perfil;

  return (
    <ScrollView style={styles.root} contentContainerStyle={styles.content}>
      <View style={styles.bienvenida}>
        <Text variant="headlineSmall" style={styles.nombre}>
          {usuario?.nombre_completo ?? '—'}
        </Text>
        <Chip mode="flat" style={styles.perfilChip}>
          {perfil?.nombre ?? 'Sin perfil'}
        </Chip>
      </View>

      <View style={styles.syncRow}>
        <SyncChip />
      </View>

      <Divider style={styles.divider} />

      {perfil?.puede_buscar_rni && (
        <Card style={styles.card} onPress={() => router.push('/(main)/busqueda')}>
          <Card.Title title="Búsqueda en el RNI" subtitle="Consultar víctimas registradas" />
          <Card.Actions>
            <Button onPress={() => router.push('/(main)/busqueda')}>Ir</Button>
          </Card.Actions>
        </Card>
      )}

      {perfil?.puede_caracterizar && (
        <>
          <Card style={styles.card} onPress={() => router.push('/(main)/hogares')}>
            <Card.Title title="Hogares" subtitle="Gestionar unidades familiares" />
            <Card.Actions>
              <Button onPress={() => router.push('/(main)/hogares')}>Ver hogares</Button>
            </Card.Actions>
          </Card>

          <Card style={styles.card} onPress={() => router.push('/(main)/encuestas')}>
            <Card.Title title="Encuestas" subtitle="Sesiones PAARI en curso" />
            <Card.Actions>
              <Button onPress={() => router.push('/(main)/encuestas')}>Ver sesiones</Button>
            </Card.Actions>
          </Card>

          <Card style={styles.card} onPress={() => router.push('/(main)/formulario')}>
            <Card.Title title="Formulario de Caracterización" subtitle="Nueva encuesta PAARI" />
            <Card.Actions>
              <Button onPress={() => router.push('/(main)/formulario')}>Ir</Button>
            </Card.Actions>
          </Card>
        </>
      )}

      <Button
        mode="outlined"
        onPress={logout}
        style={styles.logout}
        icon="logout"
        textColor="#C62828"
      >
        Cerrar sesión
      </Button>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#F5F5F5' },
  content: { padding: 16, paddingBottom: 32 },
  bienvenida: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 },
  nombre: { fontWeight: '700', flex: 1, flexShrink: 1 },
  perfilChip: { marginLeft: 8 },
  syncRow: { flexDirection: 'row', marginTop: 4, marginBottom: 4 },
  divider: { marginVertical: 12 },
  card: { marginBottom: 12, backgroundColor: '#FFFFFF' },
  logout: { marginTop: 24, borderColor: '#C62828' },
});
