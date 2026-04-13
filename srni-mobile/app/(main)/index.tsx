/**
 * Dashboard del encuestador — pantalla de inicio tras login.
 */
import { View, ScrollView, StyleSheet } from 'react-native';
import { Text, Card, Button, Divider, Chip } from 'react-native-paper';
import { router } from 'expo-router';
import { useAuthStore } from '../../src/stores/authStore';

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
        <Card style={styles.card} onPress={() => router.push('/(main)/formulario')}>
          <Card.Title title="Formulario de Caracterización" subtitle="Nueva encuesta PAARI" />
          <Card.Actions>
            <Button onPress={() => router.push('/(main)/formulario')}>Ir</Button>
          </Card.Actions>
        </Card>
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
  divider: { marginVertical: 12 },
  card: { marginBottom: 12, backgroundColor: '#FFFFFF' },
  logout: { marginTop: 24, borderColor: '#C62828' },
});
