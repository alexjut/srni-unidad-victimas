// Lista de módulos del formulario PAARI.
import { useEffect, useState } from 'react';
import { View, FlatList, StyleSheet, Pressable } from 'react-native';
import { Text, ProgressBar, ActivityIndicator } from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { router, useLocalSearchParams } from 'expo-router';
import * as SQLite from 'expo-sqlite';
import { DB_NAME } from '../../../src/db/schema';
import { GovHeader } from '../../../src/components/GovHeader';
import { EmptyState } from '../../../src/components/EmptyState';
import { GOV, SPACING, RADIUS, SHADOW, FONT } from '../../../src/theme/govTheme';

interface Tema {
  id: number;
  codigo: string;
  nombre: string;
  orden: number;
}

// ─── Tarjeta de tema ──────────────────────────────────────────────────────────

function TemaCard({
  tema,
  index,
  sesionServerId,
  hogarId,
}: {
  tema: Tema;
  index: number;
  sesionServerId?: string;
  hogarId?: string;
}) {
  return (
    <Pressable
      onPress={() => router.push({
        pathname: '/(main)/formulario/[temaId]',
        params: {
          temaId: tema.id,
          ...(sesionServerId ? { sesionServerId } : {}),
          ...(hogarId ? { hogarId } : {}),
        },
      })}
      style={({ pressed }) => [styles.card, pressed && styles.cardPressed]}
      accessibilityRole="button"
      accessibilityLabel={`Módulo ${index + 1}: ${tema.nombre}`}
    >
      {/* Número de módulo */}
      <View style={styles.numCircle}>
        <Text style={styles.numTxt}>{String(index + 1).padStart(2, '0')}</Text>
      </View>

      {/* Texto */}
      <View style={styles.cardTexto}>
        <Text style={styles.temaNombre} numberOfLines={2}>{tema.nombre}</Text>
        <Text style={styles.temaCodigo}>{tema.codigo}</Text>
      </View>

      <MaterialCommunityIcons name="chevron-right" size={20} color={GOV.borde} />
    </Pressable>
  );
}

// ─── Pantalla ─────────────────────────────────────────────────────────────────

export default function FormularioIndexScreen() {
  const { sesionServerId, hogarId } = useLocalSearchParams<{
    sesionServerId?: string;
    hogarId?: string;
  }>();

  const [temas, setTemas] = useState<Tema[]>([]);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    SQLite.openDatabaseAsync(DB_NAME)
      .then(async (db) => {
        const rows = await db.getAllAsync<Tema>(
          'SELECT id, codigo, nombre, orden FROM temas WHERE activo = 1 ORDER BY orden',
        );
        setTemas(rows);
      })
      .catch(() => {})
      .finally(() => setCargando(false));
  }, []);

  const subtituloHeader = hogarId
    ? `Hogar ${hogarId.slice(0, 8)}… · ${temas.length} módulos`
    : `${temas.length} módulos`;

  if (cargando) {
    return (
      <View style={styles.root}>
        <GovHeader title="Formulario PAARI" subtitle="Instrumento de caracterización" />
        <View style={styles.centrado}>
          <ActivityIndicator size="large" color={GOV.azul} />
          <Text style={styles.cargandoTxt}>Cargando instrumento…</Text>
        </View>
      </View>
    );
  }

  if (temas.length === 0) {
    return (
      <View style={styles.root}>
        <GovHeader title="Formulario PAARI" subtitle="Instrumento de caracterización" />
        <EmptyState
          icon="clipboard-alert-outline"
          title="Sin instrumento"
          message="No hay instrumento cargado. Sincronice con el servidor para descargar el formulario PAARI."
        />
      </View>
    );
  }

  return (
    <View style={styles.root}>
      <GovHeader title="Formulario PAARI" subtitle={subtituloHeader} />

      {/* Miga de pan */}
      {hogarId && (
        <View style={styles.miga}>
          <Text style={styles.migaTxt}>
            Hogares  ›  Hogar {hogarId.slice(0, 8)}…  ›  Formulario PAARI
          </Text>
        </View>
      )}

      {/* Barra de progreso global */}
      <View style={styles.progresoWrap}>
        <View style={styles.progresoRow}>
          <Text style={styles.progresoLabel}>{temas.length} módulos — PAARI v1.0</Text>
          <Text style={styles.progresoLabel}>Seleccione un módulo</Text>
        </View>
        <ProgressBar
          progress={0}
          style={styles.progressBar}
          color={GOV.azul}
        />
      </View>

      <FlatList
        data={temas}
        keyExtractor={(item) => String(item.id)}
        renderItem={({ item, index }) => (
          <TemaCard
            tema={item}
            index={index}
            sesionServerId={sesionServerId}
            hogarId={hogarId}
          />
        )}
        contentContainerStyle={styles.lista}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: GOV.fondoApp,
  },
  miga: {
    backgroundColor: GOV.azulTenue,
    paddingHorizontal: SPACING.md,
    paddingVertical: 6,
    borderBottomWidth: 1,
    borderBottomColor: GOV.borde,
  },
  migaTxt: {
    ...FONT.caption,
    color: GOV.azulOscuro,
  },
  centrado: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: SPACING.xl,
  },
  cargandoTxt: {
    ...FONT.small,
    color: GOV.textoS,
    marginTop: SPACING.sm,
  },
  progresoWrap: {
    backgroundColor: GOV.superficie,
    paddingHorizontal: SPACING.md,
    paddingVertical: SPACING.sm,
    borderBottomWidth: 1,
    borderBottomColor: GOV.borde,
  },
  progresoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 6,
  },
  progresoLabel: {
    ...FONT.caption,
    color: GOV.textoS,
  },
  progressBar: {
    height: 4,
    borderRadius: 2,
    backgroundColor: GOV.borde,
  },
  lista: {
    padding: SPACING.md,
    paddingBottom: SPACING.xl,
  },
  // Tarjeta de tema
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: GOV.superficie,
    borderRadius: RADIUS.md,
    padding: SPACING.md,
    marginBottom: SPACING.sm,
    ...SHADOW.card,
  },
  cardPressed: {
    opacity: 0.9,
    transform: [{ scale: 0.99 }],
  },
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
  numTxt: {
    fontSize: 13,
    fontWeight: '800',
    color: GOV.azul,
  },
  cardTexto: {
    flex: 1,
  },
  temaNombre: {
    ...FONT.body,
    fontWeight: '600',
    color: GOV.textoP,
    marginBottom: 2,
  },
  temaCodigo: {
    ...FONT.caption,
    color: GOV.textoT,
    fontFamily: 'monospace',
  },
});
