// Lista de capítulos del instrumento de caracterización.
import { useEffect, useState } from 'react';
import { View, FlatList, StyleSheet, Pressable } from 'react-native';
import { Text, ProgressBar, ActivityIndicator } from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { router, useLocalSearchParams } from 'expo-router';
import * as instrumentoDao from '../../../src/db/instrumentoDao';
import { GovHeader } from '../../../src/components/GovHeader';
import { EmptyState } from '../../../src/components/EmptyState';
import { GOV, SPACING, RADIUS, SHADOW, FONT } from '../../../src/theme/govTheme';

// ─── Tarjeta de capítulo ──────────────────────────────────────────────────────

function CapituloCard({
  capitulo,
  index,
  sesionServerId,
  instrumentoId,
  hogarId,
}: {
  capitulo: instrumentoDao.CapituloRow;
  index: number;
  sesionServerId?: string;
  instrumentoId?: string;
  hogarId?: string;
}) {
  return (
    <Pressable
      onPress={() => router.push({
        pathname: '/(main)/formulario/[temaId]',
        params: {
          temaId: capitulo.id,
          ...(sesionServerId ? { sesionServerId } : {}),
          ...(instrumentoId  ? { instrumentoId }  : {}),
          ...(hogarId        ? { hogarId }         : {}),
        },
      })}
      style={({ pressed }) => [styles.card, pressed && styles.cardPressed]}
      accessibilityRole="button"
      accessibilityLabel={`Capítulo ${index + 1}: ${capitulo.nombre}`}
    >
      <View style={styles.numCircle}>
        <Text style={styles.numTxt}>{String(index + 1).padStart(2, '0')}</Text>
      </View>

      <View style={styles.cardTexto}>
        <Text style={styles.capNombre} numberOfLines={2}>{capitulo.nombre}</Text>
        <Text style={styles.capCodigo}>
          [{capitulo.codigo}] · {capitulo.nivel === 'PERSONA' ? 'Por persona' : 'Por hogar'}
        </Text>
      </View>

      <MaterialCommunityIcons name="chevron-right" size={20} color={GOV.borde} />
    </Pressable>
  );
}

// ─── Pantalla ─────────────────────────────────────────────────────────────────

export default function FormularioIndexScreen() {
  const { sesionServerId, instrumentoId, hogarId } = useLocalSearchParams<{
    sesionServerId?: string;
    instrumentoId?: string;
    hogarId?: string;
  }>();

  const [capitulos, setCapitulos] = useState<instrumentoDao.CapituloRow[]>([]);
  const [meta, setMeta] = useState<instrumentoDao.InstrumentoMeta | null>(null);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    Promise.all([instrumentoDao.getCapitulos(), instrumentoDao.getMeta()])
      .then(([caps, m]) => {
        setCapitulos(caps);
        setMeta(m);
      })
      .catch(() => {})
      .finally(() => setCargando(false));
  }, []);

  const subtitulo = hogarId
    ? `Hogar ${hogarId.slice(0, 8)}… · ${capitulos.length} capítulos`
    : `${capitulos.length} capítulos`;

  if (cargando) {
    return (
      <View style={styles.root}>
        <GovHeader title="Formulario" subtitle="Instrumento de caracterización" onBack={() => router.back()} />
        <View style={styles.centrado}>
          <ActivityIndicator size="large" color={GOV.azul} />
          <Text style={styles.cargandoTxt}>Cargando instrumento…</Text>
        </View>
      </View>
    );
  }

  if (capitulos.length === 0) {
    return (
      <View style={styles.root}>
        <GovHeader title="Formulario" subtitle="Instrumento de caracterización" onBack={() => router.back()} />
        <EmptyState
          icon="clipboard-alert-outline"
          title="Sin instrumento"
          message="No hay instrumento cargado. Vaya al Dashboard y sincronice para descargar el formulario."
        />
      </View>
    );
  }

  return (
    <View style={styles.root}>
      <GovHeader
        title={meta ? `${meta.perfil_codigo} ${meta.version}` : 'Formulario'}
        subtitle={subtitulo}
        onBack={() => router.back()}
      />

      {hogarId && (
        <View style={styles.miga}>
          <Text style={styles.migaTxt}>
            Hogares  ›  Hogar {hogarId.slice(0, 8)}…  ›  Formulario
          </Text>
        </View>
      )}

      <View style={styles.progresoWrap}>
        <View style={styles.progresoRow}>
          <Text style={styles.progresoLabel}>{capitulos.length} capítulos</Text>
          <Text style={styles.progresoLabel}>Seleccione un capítulo</Text>
        </View>
        <ProgressBar progress={0} style={styles.progressBar} color={GOV.azul} />
      </View>

      <FlatList
        data={capitulos}
        keyExtractor={(item) => item.id}
        renderItem={({ item, index }) => (
          <CapituloCard
            capitulo={item}
            index={index}
            sesionServerId={sesionServerId}
            instrumentoId={instrumentoId}
            hogarId={hogarId}
          />
        )}
        contentContainerStyle={styles.lista}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: GOV.fondoApp },
  miga: {
    backgroundColor: GOV.azulTenue,
    paddingHorizontal: SPACING.md,
    paddingVertical: 6,
    borderBottomWidth: 1,
    borderBottomColor: GOV.borde,
  },
  migaTxt: { ...FONT.caption, color: GOV.azulOscuro },
  centrado: {
    flex: 1, justifyContent: 'center', alignItems: 'center', padding: SPACING.xl,
  },
  cargandoTxt: { ...FONT.small, color: GOV.textoS, marginTop: SPACING.sm },
  progresoWrap: {
    backgroundColor: GOV.superficie,
    paddingHorizontal: SPACING.md,
    paddingVertical: SPACING.sm,
    borderBottomWidth: 1,
    borderBottomColor: GOV.borde,
  },
  progresoRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 6 },
  progresoLabel: { ...FONT.caption, color: GOV.textoS },
  progressBar: { height: 4, borderRadius: 2, backgroundColor: GOV.borde },
  lista: { padding: SPACING.md, paddingBottom: SPACING.xl },
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: GOV.superficie,
    borderRadius: RADIUS.md,
    padding: SPACING.md,
    marginBottom: SPACING.sm,
    ...SHADOW.card,
  },
  cardPressed: { opacity: 0.9, transform: [{ scale: 0.99 }] },
  numCircle: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: GOV.azulTenue,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: SPACING.md,
    borderWidth: 1,
    borderColor: GOV.azul + '33',
  },
  numTxt: { fontSize: 13, fontWeight: '800', color: GOV.azul },
  cardTexto: { flex: 1 },
  capNombre: { ...FONT.body, fontWeight: '600', color: GOV.textoP, marginBottom: 2 },
  capCodigo: { ...FONT.caption, color: GOV.textoT, fontFamily: 'monospace' },
});
