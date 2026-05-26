/**
 * Lista de hogares — GOV.CO design system.
 * Combina hogares del servidor (online) con hogares offline (SQLite).
 */
import { useState, useCallback } from 'react';
import { View, FlatList, StyleSheet, RefreshControl, Pressable } from 'react-native';
import {
  Text, Chip, FAB, ActivityIndicator, SegmentedButtons,
} from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { router, useFocusEffect } from 'expo-router';
import { hogaresApi } from '../../../src/api/hogares';
import * as hogaresOfflineDao from '../../../src/db/hogaresOfflineDao';
import { useSyncStore } from '../../../src/stores/syncStore';
import { GovHeader } from '../../../src/components/GovHeader';
import { EmptyState } from '../../../src/components/EmptyState';
import { GOV, SPACING, RADIUS, SHADOW, FONT } from '../../../src/theme/govTheme';
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

// ─── Tarjeta de hogar (servidor) ─────────────────────────────────────────────

function HogarServidorCard({ data }: { data: HogarResumen }) {
  const esActivo = data.estado === 'ACTIVO';
  const estadoColor = esActivo ? GOV.verde : GOV.naranja;
  const estadoBg    = esActivo ? GOV.verdeTenue : GOV.naranjaTenue;

  return (
    <Pressable
      onPress={() => router.push({ pathname: '/(main)/hogares/[hogarId]', params: { hogarId: data.id } })}
      style={({ pressed }) => [styles.card, pressed && styles.cardPressed]}
      accessibilityRole="button"
      accessibilityLabel={`Hogar ${data.id.slice(0, 8)}`}
    >
      <View style={styles.cardLeft} />
      <View style={styles.cardBody}>
        <View style={styles.cardHeader}>
          <Text style={styles.cardId} numberOfLines={1}>{data.id.slice(0, 8)}…</Text>
          <View style={[styles.estadoChip, { backgroundColor: estadoBg }]}>
            <Text style={[styles.estadoTxt, { color: estadoColor }]}>{data.estado_display}</Text>
          </View>
        </View>
        <Text style={styles.municipio} numberOfLines={1}>
          {data.municipio_nombre ?? 'Municipio no registrado'}
        </Text>
        <View style={styles.cardFooter}>
          <View style={styles.metaDato}>
            <MaterialCommunityIcons name="account-group" size={13} color={GOV.textoT} />
            <Text style={styles.metaTxt}>{data.total_miembros} miembro{data.total_miembros !== 1 ? 's' : ''}</Text>
          </View>
          <Text style={styles.metaTxt}>{new Date(data.created_at).toLocaleDateString('es-CO')}</Text>
        </View>
      </View>
      <View style={styles.chevron}>
        <MaterialCommunityIcons name="chevron-right" size={20} color={GOV.borde} />
      </View>
    </Pressable>
  );
}

// ─── Tarjeta de hogar (offline pendiente) ────────────────────────────────────

function HogarOfflineCard({ data }: { data: HogarOfflineRow }) {
  return (
    <View style={[styles.card, styles.cardOffline]}>
      <View style={[styles.cardLeft, { backgroundColor: GOV.naranja }]} />
      <View style={styles.cardBody}>
        <View style={styles.cardHeader}>
          <Text style={styles.cardId} numberOfLines={1}>{data.id_local.slice(0, 8)}…</Text>
          <View style={[styles.estadoChip, { backgroundColor: GOV.naranjaTenue }]}>
            <Text style={[styles.estadoTxt, { color: GOV.naranja }]}>Pendiente sync</Text>
          </View>
        </View>
        <Text style={styles.municipio} numberOfLines={1}>
          {data.tipo_vivienda || 'Vivienda sin clasificar'} · {data.numero_personas} persona{data.numero_personas !== 1 ? 's' : ''}
        </Text>
        <Text style={styles.metaTxt}>{new Date(data.created_at).toLocaleDateString('es-CO')}</Text>
      </View>
    </View>
  );
}

// ─── Pantalla ────────────────────────────────────────────────────────────────

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

    try {
      const offline = await hogaresOfflineDao.listarPendientes();
      for (const h of offline) resultado.push({ tipo: 'offline', data: h });
    } catch {
      // SQLite no disponible
    }

    // Sprint 17 fix: NO condicionar la llamada a `estaOnline`. El flag se actualiza
    // con polling cada 60 s y puede estar desincronizado al montar la pantalla
    // (queda en false hasta que el primer checkConnectivity resuelva). El try/catch
    // ya maneja el caso sin red. Esto evita el bug en el que el usuario no veía
    // los hogares creados en el servidor.
    try {
      const res = await hogaresApi.listar(filtroEstado ? { estado: filtroEstado } : undefined);
      for (const h of res.data.results) resultado.push({ tipo: 'servidor', data: h });
    } catch {
      if (estaOnline) setError('No se pudo cargar hogares del servidor.');
      // Sin red: silenciosamente solo mostramos los offline.
    }

    setItems(resultado);
    setCargando(false);
    setRefrescando(false);
  }, [estaOnline, filtroEstado]);

  // useFocusEffect recarga al volver al tab (p. ej. tras crear un hogar en /nuevo
  // o /conformar). Con useEffect tradicional la pantalla quedaba con estado obsoleto
  // porque los tabs preservan la instancia montada.
  useFocusEffect(
    useCallback(() => {
      cargar();
    }, [cargar]),
  );

  if (cargando) {
    return (
      <View style={styles.root}>
        <GovHeader title="Hogares" subtitle="Unidades familiares registradas" />
        <View style={styles.centrado}>
          <ActivityIndicator size="large" color={GOV.azul} />
          <Text style={styles.hint}>Cargando hogares…</Text>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.root}>
      <GovHeader title="Hogares" subtitle="Unidades familiares registradas" />

      {/* Filtro de estado */}
      <SegmentedButtons
        value={filtroEstado}
        onValueChange={setFiltroEstado}
        buttons={ESTADOS}
        style={styles.filtro}
        theme={{ colors: { secondaryContainer: GOV.azulTenue, onSecondaryContainer: GOV.azul } }}
      />

      {/* Banner offline */}
      {!estaOnline && (
        <View style={styles.offlineBanner}>
          <MaterialCommunityIcons name="wifi-off" size={14} color={GOV.naranja} />
          <Text style={styles.offlineTxt}>Sin conexión — datos locales</Text>
        </View>
      )}

      {/* Error */}
      {error ? (
        <Text style={styles.errorTxt}>{error}</Text>
      ) : null}

      <FlatList
        data={items}
        keyExtractor={(item) =>
          item.tipo === 'offline' ? `offline-${item.data.id_local}` : item.data.id
        }
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
            icon="home-outline"
            title="Sin hogares"
            message="No hay hogares registrados aún. Crea el primero para comenzar la caracterización."
            actionLabel="Nuevo hogar"
            onAction={() => router.push('/(main)/hogares/nuevo')}
          />
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
        color="#FFFFFF"
        onPress={() => router.push('/(main)/hogares/nuevo')}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: GOV.fondoApp,
  },
  centrado: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: SPACING.xl,
  },
  hint: {
    marginTop: SPACING.sm,
    color: GOV.textoS,
    ...FONT.small,
  },
  filtro: {
    marginHorizontal: SPACING.md,
    marginVertical: SPACING.sm,
  },
  offlineBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.xs,
    backgroundColor: GOV.naranjaTenue,
    marginHorizontal: SPACING.md,
    marginBottom: SPACING.sm,
    paddingHorizontal: SPACING.sm,
    paddingVertical: 6,
    borderRadius: RADIUS.sm,
  },
  offlineTxt: {
    ...FONT.caption,
    color: GOV.naranja,
    fontWeight: '600',
  },
  errorTxt: {
    ...FONT.small,
    color: GOV.rojo,
    textAlign: 'center',
    marginHorizontal: SPACING.md,
    marginBottom: SPACING.sm,
  },
  lista: {
    padding: SPACING.md,
    paddingBottom: 96,
  },
  listaVacia: {
    flexGrow: 1,
  },
  // Tarjeta
  card: {
    flexDirection: 'row',
    backgroundColor: GOV.superficie,
    borderRadius: RADIUS.md,
    marginBottom: SPACING.sm,
    overflow: 'hidden',
    ...SHADOW.card,
  },
  cardPressed: {
    opacity: 0.92,
    transform: [{ scale: 0.99 }],
  },
  cardOffline: {
    // sin onPress — solo visual
  },
  cardLeft: {
    width: 4,
    backgroundColor: GOV.azul,
  },
  cardBody: {
    flex: 1,
    padding: SPACING.md,
  },
  chevron: {
    justifyContent: 'center',
    paddingRight: SPACING.sm,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
  },
  cardId: {
    fontFamily: 'monospace',
    fontSize: 13,
    fontWeight: '600',
    color: GOV.azul,
    flex: 1,
  },
  estadoChip: {
    borderRadius: RADIUS.pill,
    paddingHorizontal: 8,
    paddingVertical: 2,
  },
  estadoTxt: {
    fontSize: 11,
    fontWeight: '600',
  },
  municipio: {
    ...FONT.small,
    color: GOV.textoS,
    marginBottom: 6,
  },
  cardFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  metaDato: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 3,
  },
  metaTxt: {
    ...FONT.caption,
    color: GOV.textoT,
  },
  fab: {
    position: 'absolute',
    right: SPACING.md,
    bottom: SPACING.md,
    backgroundColor: GOV.azul,
  },
});
