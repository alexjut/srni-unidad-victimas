/**
 * Lista de sesiones de encuesta del encuestador.
 * Muestra el progreso de cada sesión y permite continuar o ver detalles.
 */
import { useEffect, useState, useCallback } from 'react';
import { View, FlatList, StyleSheet, RefreshControl } from 'react-native';
import {
  Text, Card, Chip, ProgressBar,
  ActivityIndicator, SegmentedButtons,
} from 'react-native-paper';
import { router } from 'expo-router';
import { encuestasApi } from '../../../src/api/encuestas';
import type { SesionResumen } from '../../../src/types';

const ESTADOS = [
  { value: '', label: 'Todas' },
  { value: 'INICIADA', label: 'Iniciadas' },
  { value: 'EN_PROGRESO', label: 'En curso' },
  { value: 'COMPLETADA', label: 'Completadas' },
];

const ESTADO_COLOR: Record<string, string> = {
  INICIADA: '#1565C0',
  EN_PROGRESO: '#E65100',
  COMPLETADA: '#2E7D32',
  SUSPENDIDA: '#616161',
};

export default function EncuestasIndexScreen() {
  const [sesiones, setSesiones] = useState<SesionResumen[]>([]);
  const [cargando, setCargando] = useState(true);
  const [refrescando, setRefrescando] = useState(false);
  const [filtroEstado, setFiltroEstado] = useState('');
  const [error, setError] = useState('');

  const cargar = useCallback(async (esRefresh = false) => {
    if (esRefresh) setRefrescando(true);
    else setCargando(true);
    setError('');
    try {
      const res = await encuestasApi.listar(
        filtroEstado ? { estado: filtroEstado } : undefined
      );
      setSesiones(res.data.results);
    } catch {
      setError('No se pudo cargar las sesiones.');
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
        <Text style={styles.hint}>Cargando encuestas…</Text>
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

      {error ? <Text style={styles.error}>{error}</Text> : null}

      <FlatList
        data={sesiones}
        keyExtractor={(item) => item.id}
        refreshControl={
          <RefreshControl refreshing={refrescando} onRefresh={() => cargar(true)} />
        }
        ListEmptyComponent={
          <View style={styles.centrado}>
            <Text variant="bodyLarge" style={styles.hint}>
              No hay sesiones registradas.
            </Text>
          </View>
        }
        renderItem={({ item }) => (
          <Card
            style={styles.card}
            onPress={() =>
              router.push({
                pathname: '/(main)/encuestas/[sesionId]',
                params: { sesionId: item.id },
              })
            }
          >
            <Card.Content>
              <View style={styles.cardHeader}>
                <Text variant="bodyMedium" style={styles.instrumento} numberOfLines={1}>
                  {item.instrumento_nombre}
                </Text>
                <Chip
                  compact
                  mode="flat"
                  style={{ backgroundColor: (ESTADO_COLOR[item.estado] ?? '#616161') + '22' }}
                  textStyle={{ color: ESTADO_COLOR[item.estado] ?? '#616161', fontSize: 10 }}
                >
                  {item.estado_display}
                </Chip>
              </View>

              <Text variant="bodySmall" style={styles.hogarId}>
                Hogar: {item.hogar.slice(0, 8)}…
              </Text>

              <View style={styles.progresoRow}>
                <ProgressBar
                  progress={item.porcentaje_completado / 100}
                  style={styles.barra}
                  color={ESTADO_COLOR[item.estado]}
                />
                <Text variant="labelSmall" style={styles.pct}>
                  {item.porcentaje_completado}%
                </Text>
              </View>

              <Text variant="labelSmall" style={styles.fecha}>
                {new Date(item.fecha_inicio).toLocaleDateString('es-CO')}
                {item.fecha_fin
                  ? ` — ${new Date(item.fecha_fin).toLocaleDateString('es-CO')}`
                  : ''}
              </Text>
            </Card.Content>
          </Card>
        )}
        contentContainerStyle={[styles.lista, sesiones.length === 0 && styles.listaVacia]}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#F5F5F5' },
  centrado: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 32 },
  filtro: { margin: 12 },
  lista: { padding: 12, paddingBottom: 32 },
  listaVacia: { flexGrow: 1 },
  card: { marginBottom: 8, backgroundColor: '#FFFFFF' },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 },
  instrumento: { fontWeight: '600', color: '#212121', flex: 1 },
  hogarId: { fontFamily: 'monospace', color: '#9E9E9E', marginBottom: 8 },
  progresoRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 4 },
  barra: { flex: 1, height: 6, borderRadius: 3, marginRight: 8 },
  pct: { color: '#616161', minWidth: 32, textAlign: 'right' },
  fecha: { color: '#BDBDBD' },
  hint: { marginTop: 12, color: '#757575' },
  error: { color: '#C62828', textAlign: 'center', margin: 16 },
});
