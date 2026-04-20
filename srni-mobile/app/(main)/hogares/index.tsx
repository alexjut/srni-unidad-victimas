/**
 * Lista de hogares — combina hogares del servidor (online) con hogares
 * creados offline (SQLite local) que aún no se han sincronizado.
 */
import { useEffect, useState, useCallback } from 'react';
import { View, FlatList, StyleSheet, RefreshControl } from 'react-native';
import {
  Text, Card, Chip, FAB, ActivityIndicator,
  SegmentedButtons, Badge,
} from 'react-native-paper';
import { router } from 'expo-router';
import { hogaresApi } from '../../../src/api/hogares';
import * as hogaresOfflineDao from '../../../src/db/hogaresOfflineDao';
import { useSyncStore } from '../../../src/stores/syncStore';
import type { HogarResumen } from '../../../src/types';
import type { HogarOfflineRow } from '../../../src/db/hogaresOfflineDao';

const ESTADOS = [
  { value: '', label: 'Todos' },
  { value: 'BORRADOR', label: 'Borrador' },
  { value: 'ACTIVO', label: 'Activo' },
];

type ItemLista =
  | { tipo: 'servidor'; data: HogarResumen }
  | { tipo: 'offline'; data: HogarOfflineRow };

export default function HogaresIndexScreen() {
  const { estaOnline } = useSyncStore();
  const [items, setItems] = useState<ItemLista[]>([]);
  const [cargando, setCargando] = useState(true);
  const [refrescando, setRefrescando] = useState(false);
  const [filtroEstado, setFiltroEstado] = useState('');
  const [error, setError] = useState<string | null>(null);

  const cargar = useCallback(async (esRefresh = false) => {
    if (esRefresh) setRefrescando(true);
    else setCargando(true);
    setError(null);

    const resultado: ItemLista[] = [];

    // Hogares offline pendientes (siempre desde SQLite)
    try {
      const offline = await hogaresOfflineDao.listarPendientes();
      for (const h of offline) resultado.push({ tipo: 'offline', data: h });
    } catch {
      // SQLite no disponible: ignorar hogares offline
    }

    // Hogares del servidor (solo si hay red)
    if (estaOnline) {
      try {
        const res = await hogaresApi.listar(filtroEstado ? { estado: filtroEstado } : undefined);
        for (const h of res.data.results) resultado.push({ tipo: 'servidor', data: h });
      } catch {
        setError('No se pudo cargar hogares del servidor.');
      }
    }

    setItems(resultado);
    setCargando(false);
    setRefrescando(false);
  }, [estaOnline, filtroEstado]);

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

      {!estaOnline && (
        <Chip icon="wifi-off" mode="flat" style={styles.offlineBanner} textStyle={styles.offlineTxt}>
          Sin conexión — mostrando datos locales
        </Chip>
      )}

      {error && <Text style={styles.error}>{error}</Text>}

      <FlatList
        data={items}
        keyExtractor={(item) =>
          item.tipo === 'offline' ? `offline-${item.data.id_local}` : item.data.id
        }
        refreshControl={
          <RefreshControl refreshing={refrescando} onRefresh={() => cargar(true)} />
        }
        ListEmptyComponent={
          <View style={styles.centrado}>
            <Text variant="bodyLarge" style={styles.hint}>No hay hogares registrados.</Text>
          </View>
        }
        renderItem={({ item }) =>
          item.tipo === 'offline'
            ? <HogarOfflineCard data={item.data} />
            : <HogarServidorCard data={item.data} />
        }
        contentContainerStyle={[styles.lista, items.length === 0 && styles.listaVacia]}
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

function HogarServidorCard({ data }: { data: HogarResumen }) {
  const color = data.estado === 'ACTIVO' ? '#2E7D32' : data.estado === 'BORRADOR' ? '#E65100' : '#616161';
  return (
    <Card
      style={styles.card}
      onPress={() => router.push({ pathname: '/(main)/hogares/[hogarId]', params: { hogarId: data.id } })}
    >
      <Card.Content>
        <View style={styles.cardHeader}>
          <Text variant="bodyMedium" style={styles.idText} numberOfLines={1}>{data.id.slice(0, 8)}…</Text>
          <Chip compact mode="flat" style={{ backgroundColor: color + '22' }} textStyle={{ color, fontSize: 11 }}>
            {data.estado_display}
          </Chip>
        </View>
        <Text variant="bodySmall" style={styles.municipio}>{data.municipio_nombre ?? 'Municipio no registrado'}</Text>
        <View style={styles.cardFooter}>
          <Text variant="labelSmall" style={styles.dato}>{data.total_miembros} miembro{data.total_miembros !== 1 ? 's' : ''}</Text>
          <Text variant="labelSmall" style={styles.dato}>{new Date(data.created_at).toLocaleDateString('es-CO')}</Text>
        </View>
      </Card.Content>
    </Card>
  );
}

function HogarOfflineCard({ data }: { data: HogarOfflineRow }) {
  return (
    <Card style={[styles.card, styles.cardOffline]}>
      <Card.Content>
        <View style={styles.cardHeader}>
          <Text variant="bodyMedium" style={styles.idText} numberOfLines={1}>{data.id_local.slice(0, 8)}…</Text>
          <Chip compact mode="flat" style={{ backgroundColor: '#FFF3E0' }} textStyle={{ color: '#E65100', fontSize: 11 }}>
            Pendiente sync
          </Chip>
        </View>
        <Text variant="bodySmall" style={styles.municipio}>
          {data.tipo_vivienda || 'Vivienda sin clasificar'} · {data.numero_personas} persona{data.numero_personas !== 1 ? 's' : ''}
        </Text>
        <Text variant="labelSmall" style={styles.dato}>
          {new Date(data.created_at).toLocaleDateString('es-CO')}
        </Text>
      </Card.Content>
    </Card>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#F5F5F5' },
  centrado: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 32 },
  filtro: { margin: 12 },
  offlineBanner: { marginHorizontal: 12, marginBottom: 8, backgroundColor: '#FFF3E0' },
  offlineTxt: { color: '#E65100', fontSize: 12 },
  lista: { padding: 12, paddingBottom: 88 },
  listaVacia: { flexGrow: 1 },
  card: { marginBottom: 8, backgroundColor: '#FFFFFF' },
  cardOffline: { borderLeftWidth: 3, borderLeftColor: '#E65100' },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 },
  idText: { fontFamily: 'monospace', color: '#1565C0', fontWeight: '600', flex: 1 },
  municipio: { color: '#424242', marginBottom: 8 },
  cardFooter: { flexDirection: 'row', justifyContent: 'space-between' },
  dato: { color: '#9E9E9E' },
  hint: { marginTop: 12, color: '#757575' },
  error: { color: '#C62828', textAlign: 'center', margin: 16 },
  fab: { position: 'absolute', right: 16, bottom: 16 },
});
