/**
 * Lista de hogares del encuestador.
 * Carga desde el servidor con pull-to-refresh y filtro por estado.
 */
import { useEffect, useState, useCallback } from 'react';
import { View, FlatList, StyleSheet, RefreshControl } from 'react-native';
import {
  Text, Card, Chip, FAB, ActivityIndicator,
  SegmentedButtons, Badge,
} from 'react-native-paper';
import { router } from 'expo-router';
import { hogaresApi } from '../../../src/api/hogares';
import type { HogarResumen } from '../../../src/types';

const ESTADOS = [
  { value: '', label: 'Todos' },
  { value: 'BORRADOR', label: 'Borrador' },
  { value: 'ACTIVO', label: 'Activo' },
];

export default function HogaresIndexScreen() {
  const [hogares, setHogares] = useState<HogarResumen[]>([]);
  const [cargando, setCargando] = useState(true);
  const [refrescando, setRefrescando] = useState(false);
  const [filtroEstado, setFiltroEstado] = useState('');
  const [error, setError] = useState<string | null>(null);

  const cargar = useCallback(async (esRefresh = false) => {
    if (esRefresh) setRefrescando(true);
    else setCargando(true);
    setError(null);
    try {
      const res = await hogaresApi.listar(filtroEstado ? { estado: filtroEstado } : undefined);
      setHogares(res.data.results);
    } catch {
      setError('No se pudo cargar la lista de hogares.');
    } finally {
      setCargando(false);
      setRefrescando(false);
    }
  }, [filtroEstado]);

  useEffect(() => { cargar(); }, [cargar]);

  if (cargando) {
    return (
      <View style={styles.centrado}>
        <ActivityIndicator size="large" />
        <Text style={styles.hint}>Cargando hogares…</Text>
      </View>
    );
  }

  return (
    <View style={styles.root}>
      <SegmentedButtons
        value={filtroEstado}
        onValueChange={setFiltroEstado}
        buttons={ESTADOS}
        style={styles.filtro}
      />

      {error && (
        <Text style={styles.error}>{error}</Text>
      )}

      <FlatList
        data={hogares}
        keyExtractor={(item) => item.id}
        refreshControl={
          <RefreshControl refreshing={refrescando} onRefresh={() => cargar(true)} />
        }
        ListEmptyComponent={
          <View style={styles.centrado}>
            <Text variant="bodyLarge" style={styles.hint}>
              No hay hogares registrados.
            </Text>
          </View>
        }
        renderItem={({ item }) => (
          <Card
            style={styles.card}
            onPress={() =>
              router.push({
                pathname: '/(main)/hogares/[hogarId]',
                params: { hogarId: item.id },
              })
            }
          >
            <Card.Content>
              <View style={styles.cardHeader}>
                <Text variant="bodyMedium" style={styles.idText} numberOfLines={1}>
                  {item.id.slice(0, 8)}…
                </Text>
                <EstadoChip estado={item.estado} label={item.estado_display} />
              </View>
              <Text variant="bodySmall" style={styles.municipio}>
                {item.municipio_nombre ?? 'Municipio no registrado'}
              </Text>
              <View style={styles.cardFooter}>
                <Text variant="labelSmall" style={styles.dato}>
                  {item.total_miembros} miembro{item.total_miembros !== 1 ? 's' : ''}
                </Text>
                <Text variant="labelSmall" style={styles.dato}>
                  {new Date(item.created_at).toLocaleDateString('es-CO')}
                </Text>
              </View>
            </Card.Content>
          </Card>
        )}
        contentContainerStyle={[styles.lista, hogares.length === 0 && styles.listaVacia]}
      />

      <FAB
        icon="plus"
        label="Nuevo hogar"
        style={styles.fab}
        onPress={() => router.push('/(main)/hogares/nuevo')}
      />
    </View>
  );
}

function EstadoChip({ estado, label }: { estado: string; label: string }) {
  const color =
    estado === 'ACTIVO' ? '#2E7D32' :
    estado === 'BORRADOR' ? '#E65100' :
    '#616161';
  return (
    <Chip
      mode="flat"
      compact
      style={{ backgroundColor: color + '22' }}
      textStyle={{ color, fontSize: 11 }}
    >
      {label}
    </Chip>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#F5F5F5' },
  centrado: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 32 },
  filtro: { margin: 12 },
  lista: { padding: 12, paddingBottom: 88 },
  listaVacia: { flexGrow: 1 },
  card: { marginBottom: 8, backgroundColor: '#FFFFFF' },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 },
  idText: { fontFamily: 'monospace', color: '#1565C0', fontWeight: '600', flex: 1 },
  municipio: { color: '#424242', marginBottom: 8 },
  cardFooter: { flexDirection: 'row', justifyContent: 'space-between' },
  dato: { color: '#9E9E9E' },
  hint: { marginTop: 12, color: '#757575' },
  error: { color: '#C62828', textAlign: 'center', margin: 16 },
  fab: { position: 'absolute', right: 16, bottom: 16 },
});
