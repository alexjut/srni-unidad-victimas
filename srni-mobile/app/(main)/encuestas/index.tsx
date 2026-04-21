/**
 * Lista de sesiones de encuesta del encuestador.
 * Muestra el progreso de cada sesión y permite continuar o ver detalles.
 */
import { useEffect, useState, useCallback } from 'react';
import { View, FlatList, StyleSheet, RefreshControl, Pressable } from 'react-native';
import {
  Text, Chip, ProgressBar,
  ActivityIndicator, SegmentedButtons,
} from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { encuestasApi } from '../../../src/api/encuestas';
import { GovHeader } from '../../../src/components/GovHeader';
import { EmptyState } from '../../../src/components/EmptyState';
import { GOV, SPACING, RADIUS, SHADOW, FONT } from '../../../src/theme/govTheme';
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
      <View style={styles.root}>
        <GovHeader title="Encuestas" subtitle="Sesiones PAARI" />
        <View style={styles.centrado}>
          <ActivityIndicator size="large" color={GOV.azul} />
          <Text style={styles.hint}>Cargando encuestas…</Text>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.root}>
      <GovHeader title="Encuestas" subtitle="Sesiones PAARI" />

      <SegmentedButtons
        value={filtroEstado}
        onValueChange={setFiltroEstado}
        buttons={ESTADOS}
        style={styles.filtro}
        theme={{ colors: { secondaryContainer: GOV.azulTenue, onSecondaryContainer: GOV.azul } }}
      />

      {error ? <Text style={styles.error}>{error}</Text> : null}

      <FlatList
        data={sesiones}
        keyExtractor={(item) => item.id}
        refreshControl={
          <RefreshControl
            refreshing={refrescando}
            onRefresh={() => cargar(true)}
            colors={[GOV.azul]}
            tintColor={GOV.azul}
          />
        }
        ListEmptyComponent={
          <EmptyState
            icon="clipboard-text-outline"
            title="Sin sesiones"
            message="No hay sesiones registradas para los filtros seleccionados."
          />
        }
        renderItem={({ item }) => {
          const estadoColor = ESTADO_COLOR[item.estado] ?? '#616161';
          return (
            <Pressable
              style={({ pressed }) => [styles.card, pressed && styles.cardPressed]}
              onPress={() => router.push({ pathname: '/(main)/encuestas/[sesionId]', params: { sesionId: item.id } })}
              accessibilityRole="button"
            >
              <View style={[styles.cardAccent, { backgroundColor: estadoColor }]} />
              <View style={styles.cardBody}>
                <View style={styles.cardHeader}>
                  <Text style={styles.instrumento} numberOfLines={1}>{item.instrumento_nombre}</Text>
                  <View style={[styles.estadoChip, { backgroundColor: estadoColor + '22' }]}>
                    <Text style={[styles.estadoTxt, { color: estadoColor }]}>{item.estado_display}</Text>
                  </View>
                </View>

                <Text style={styles.hogarId}>Hogar: {item.hogar.slice(0, 8)}…</Text>

                <View style={styles.progresoRow}>
                  <ProgressBar
                    progress={item.porcentaje_completado / 100}
                    style={styles.barra}
                    color={estadoColor}
                  />
                  <Text style={styles.pct}>{item.porcentaje_completado}%</Text>
                </View>

                <Text style={styles.fecha}>
                  {new Date(item.fecha_inicio).toLocaleDateString('es-CO')}
                  {item.fecha_fin ? ` — ${new Date(item.fecha_fin).toLocaleDateString('es-CO')}` : ''}
                </Text>
              </View>
              <MaterialCommunityIcons name="chevron-right" size={20} color={GOV.borde} style={styles.chevron} />
            </Pressable>
          );
        }}
        contentContainerStyle={[styles.lista, sesiones.length === 0 && styles.listaVacia]}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: GOV.fondoApp },
  centrado: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: SPACING.xl },
  filtro: { marginHorizontal: SPACING.md, marginVertical: SPACING.sm },
  lista: { padding: SPACING.md, paddingBottom: SPACING.xl },
  listaVacia: { flexGrow: 1 },
  // Tarjeta
  card: {
    flexDirection: 'row',
    backgroundColor: GOV.superficie,
    borderRadius: RADIUS.md,
    marginBottom: SPACING.sm,
    overflow: 'hidden',
    ...SHADOW.card,
  },
  cardPressed: { opacity: 0.92, transform: [{ scale: 0.99 }] },
  cardAccent: { width: 4 },
  cardBody: { flex: 1, padding: SPACING.md },
  chevron: { alignSelf: 'center', marginRight: SPACING.xs },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 },
  instrumento: { ...FONT.body, fontWeight: '600', color: GOV.textoP, flex: 1 },
  estadoChip: { borderRadius: RADIUS.pill, paddingHorizontal: 8, paddingVertical: 2 },
  estadoTxt: { fontSize: 10, fontWeight: '600' },
  hogarId: { fontFamily: 'monospace', ...FONT.caption, color: GOV.textoT, marginBottom: SPACING.sm },
  progresoRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 4 },
  barra: { flex: 1, height: 5, borderRadius: 2, marginRight: SPACING.sm },
  pct: { ...FONT.caption, color: GOV.textoS, minWidth: 32, textAlign: 'right' },
  fecha: { ...FONT.caption, color: GOV.textoT },
  hint: { marginTop: SPACING.sm, color: GOV.textoS, ...FONT.small },
  error: { ...FONT.small, color: GOV.rojo, textAlign: 'center', margin: SPACING.md },
});
