// Pantalla de inicio de caracterización: paso 1 instrumento → paso 2 hogar.
import { useEffect, useState, useCallback } from 'react';
import { View, FlatList, StyleSheet, Pressable, Alert } from 'react-native';
import { Text, ActivityIndicator } from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { router, useLocalSearchParams } from 'expo-router';
import { GovHeader } from '../../../src/components/GovHeader';
import { EmptyState } from '../../../src/components/EmptyState';
import { GOV, SPACING, RADIUS, SHADOW, FONT } from '../../../src/theme/govTheme';
import apiClient from '../../../src/api/client';
import { encuestasApi } from '../../../src/api/encuestas';
import { hogaresApi } from '../../../src/api/hogares';
import { useCaracterizacionStore } from '../../../src/stores/caracterizacionStore';
import type { HogarResumen } from '../../../src/types';

// ── Tipos ──────────────────────────────────────────────────────────────────

interface InstrumentoResumen {
  id: string;
  codigo: string;
  nombre: string;
  version: string;
  activo: boolean;
  vigente: boolean;
  total_capitulos: number;
}

// ── Iconos por código de instrumento ──────────────────────────────────────

const ICONO: Record<string, string> = {
  TERRITORIAL:   'map-marker-multiple',
  BUENAVENTURA:  'city-variant',
  SAN_ANDRES:    'island',
  TELEFONICO:    'phone-in-talk',
  URBANO_ETNICO: 'home-city',
  RURAL_ETNICO:  'tree',
  ASISTENCIA:    'hand-heart',
};

// ── Tarjeta de instrumento ────────────────────────────────────────────────

function TarjetaInstrumento({
  item,
  activo,
  onPress,
}: {
  item: InstrumentoResumen;
  activo: boolean;
  onPress: () => void;
}) {
  const icono = (ICONO[item.codigo] ?? 'clipboard-outline') as any;
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [styles.card, activo && styles.cardActivo, pressed && { opacity: 0.88 }]}
      accessibilityRole="radio"
      accessibilityState={{ selected: activo }}
      accessibilityLabel={item.nombre}
    >
      <View style={[styles.iconoCirculo, activo && styles.iconoCirculoActivo]}>
        <MaterialCommunityIcons name={icono} size={26} color={activo ? '#FFF' : GOV.azul} />
      </View>
      <View style={styles.cardTexto}>
        <Text style={[styles.cardNombre, activo && styles.cardNombreActivo]} numberOfLines={2}>
          {item.nombre}
        </Text>
        <Text style={styles.cardMeta}>
          {item.version}  ·  {item.total_capitulos} capítulos
        </Text>
      </View>
      <MaterialCommunityIcons
        name={activo ? 'check-circle' : 'chevron-right'}
        size={22}
        color={activo ? GOV.azul : GOV.borde}
      />
    </Pressable>
  );
}

// ── Tarjeta de hogar ──────────────────────────────────────────────────────

function TarjetaHogar({ hogar, onPress }: { hogar: HogarResumen; onPress: () => void }) {
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [styles.card, pressed && { opacity: 0.88 }]}
      accessibilityRole="button"
      accessibilityLabel={`Hogar ${hogar.id.slice(0, 8)}`}
    >
      <View style={styles.iconoCirculo}>
        <MaterialCommunityIcons name="home-group" size={22} color={GOV.azul} />
      </View>
      <View style={styles.cardTexto}>
        <Text style={styles.cardNombre}>{hogar.id.slice(0, 8)}…</Text>
        <Text style={styles.cardMeta}>
          {hogar.municipio_nombre ?? 'Municipio no registrado'}  ·  {hogar.total_miembros} miembro{hogar.total_miembros !== 1 ? 's' : ''}
        </Text>
      </View>
      <MaterialCommunityIcons name="chevron-right" size={22} color={GOV.borde} />
    </Pressable>
  );
}

// ── Pantalla ──────────────────────────────────────────────────────────────

export default function CaracterizarScreen() {
  const { hogarId } = useLocalSearchParams<{ hogarId?: string }>();
  const rutaEntrevista = useCaracterizacionStore((s) => s.rutaEntrevista);

  const [paso, setPaso] = useState<'instrumento' | 'hogar'>('instrumento');
  const [instrumentos, setInstrumentos] = useState<InstrumentoResumen[]>([]);
  const [hogares, setHogares] = useState<HogarResumen[]>([]);
  const [cargandoPerfiles, setCargandoPerfiles] = useState(true);
  const [cargandoHogares, setCargandoHogares] = useState(false);
  const [seleccionado, setSeleccionado] = useState<InstrumentoResumen | null>(null);
  const [creando, setCreando] = useState(false);

  useEffect(() => {
    apiClient
      .get<{ results: InstrumentoResumen[] }>('/api/formulario/instrumentos/')
      .then((r) => {
        const activos = r.data.results.filter((i) => i.activo && i.vigente);
        setInstrumentos(activos);
      })
      .catch(() => {})
      .finally(() => setCargandoPerfiles(false));
  }, []);

  const cargarHogares = useCallback(async () => {
    setCargandoHogares(true);
    try {
      const { data } = await hogaresApi.listar();
      setHogares(data.results);
    } catch {
      setHogares([]);
    } finally {
      setCargandoHogares(false);
    }
  }, []);

  async function crearSesion(hId: string) {
    if (!seleccionado) return;
    setCreando(true);
    try {
      await encuestasApi.crear({
        hogar: hId,
        instrumento: seleccionado.id,
        ruta_entrevista: rutaEntrevista,
      });
      // Sprint 14: tras crear la caracterización volvemos al hub del hogar
      // (no al formulario directo). El usuario ve la nueva sesión en la lista
      // y decide si entra a llenarla o crea otra.
      router.replace({
        pathname: '/(main)/hogares/[hogarId]/caracterizaciones',
        params: { hogarId: hId },
      });
    } catch (err: any) {
      Alert.alert('Error', err?.response?.data?.detail ?? 'No se pudo iniciar la sesión.');
      setCreando(false);
    }
  }

  async function avanzar() {
    if (!seleccionado) return;
    if (hogarId) {
      await crearSesion(hogarId);
    } else {
      await cargarHogares();
      setPaso('hogar');
    }
  }

  // ── Cargando ──────────────────────────────────────────────────────────────

  if (cargandoPerfiles) {
    return (
      <View style={styles.root}>
        <GovHeader title="Caracterizar" subtitle="Cargando instrumentos…" />
        <View style={styles.centrado}><ActivityIndicator size="large" color={GOV.azul} /></View>
      </View>
    );
  }

  // ── Paso 1: seleccionar instrumento ───────────────────────────────────────

  if (paso === 'instrumento') {
    return (
      <View style={styles.root}>
        <GovHeader
          title="Caracterizar"
          subtitle={hogarId ? `Hogar ${hogarId.slice(0, 8)}…` : 'Seleccionar instrumento'}
          onBack={hogarId ? () => router.back() : undefined}
        />
        {hogarId && (
          <View style={styles.miga}>
            <Text style={styles.migaTxt}>Hogares  ›  Hogar {hogarId.slice(0, 8)}…  ›  Instrumento</Text>
          </View>
        )}

        <View style={styles.intro}>
          <Text style={styles.introTitulo}>¿Qué tipo de caracterización vas a realizar?</Text>
          {!hogarId && (
            <View style={styles.pasoIndicador}>
              <View style={styles.pasoBurbuja}><Text style={styles.pasoBurbujaActivo}>1</Text></View>
              <View style={styles.pasoLinea} />
              <View style={[styles.pasoBurbuja, styles.pasoBurbujaInactivo]}><Text style={styles.pasoBurbujaTextoInactivo}>2</Text></View>
              <Text style={styles.pasoLabel}>Instrumento  →  Hogar</Text>
            </View>
          )}
        </View>

        {instrumentos.length === 0 ? (
          <EmptyState
            icon="clipboard-alert-outline"
            title="Sin instrumentos"
            message="No hay instrumentos vigentes disponibles. Verifica la conexión con el servidor."
          />
        ) : (
          <FlatList
            data={instrumentos}
            keyExtractor={(item) => item.id}
            contentContainerStyle={styles.lista}
            renderItem={({ item }) => (
              <TarjetaInstrumento
                item={item}
                activo={seleccionado?.id === item.id}
                onPress={() => setSeleccionado(item)}
              />
            )}
            ListFooterComponent={
              seleccionado ? (
                <Pressable
                  onPress={avanzar}
                  disabled={creando}
                  style={({ pressed }) => [styles.btnContinuar, pressed && { opacity: 0.85 }]}
                >
                  {creando
                    ? <ActivityIndicator color="#FFF" size={18} />
                    : <>
                        <Text style={styles.btnTxt}>
                          {hogarId ? 'Iniciar caracterización' : 'Seleccionar hogar'}
                        </Text>
                        <MaterialCommunityIcons name="arrow-right" size={18} color="#FFF" />
                      </>
                  }
                </Pressable>
              ) : null
            }
          />
        )}
      </View>
    );
  }

  // ── Paso 2: seleccionar hogar ─────────────────────────────────────────────

  return (
    <View style={styles.root}>
      <GovHeader
        title="Seleccionar hogar"
        subtitle={`${seleccionado?.codigo}  ·  ${seleccionado?.version}`}
        onBack={() => setPaso('instrumento')}
      />
      <View style={styles.miga}>
        <Text style={styles.migaTxt}>
          Caracterizar  ›  {seleccionado?.codigo}  ›  Hogar
        </Text>
      </View>

      <View style={styles.intro}>
        <Text style={styles.introTitulo}>¿A qué hogar vas a caracterizar?</Text>
        <View style={styles.pasoIndicador}>
          <View style={[styles.pasoBurbuja, styles.pasoBurbujaCompletado]}>
            <MaterialCommunityIcons name="check" size={12} color="#FFF" />
          </View>
          <View style={[styles.pasoLinea, styles.pasoLineaCompletada]} />
          <View style={styles.pasoBurbuja}><Text style={styles.pasoBurbujaActivo}>2</Text></View>
          <Text style={styles.pasoLabel}>{seleccionado?.nombre}  →  Hogar</Text>
        </View>
      </View>

      {cargandoHogares ? (
        <View style={styles.centrado}><ActivityIndicator size="large" color={GOV.azul} /></View>
      ) : hogares.length === 0 ? (
        <EmptyState
          icon="home-outline"
          title="Sin hogares registrados"
          message="Crea el hogar primero desde la pestaña Hogares y luego regresa aquí."
          actionLabel="Ir a Hogares"
          onAction={() => router.push('/(main)/hogares/index')}
        />
      ) : (
        <FlatList
          data={hogares}
          keyExtractor={(item) => item.id}
          contentContainerStyle={styles.lista}
          renderItem={({ item }) => (
            <TarjetaHogar
              hogar={item}
              onPress={() => { if (!creando) crearSesion(item.id); }}
            />
          )}
        />
      )}

      {creando && (
        <View style={styles.overlay}>
          <ActivityIndicator size="large" color="#FFF" />
          <Text style={styles.overlayTxt}>Iniciando sesión…</Text>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: GOV.fondoApp },
  centrado: { flex: 1, justifyContent: 'center', alignItems: 'center' },

  miga: {
    backgroundColor: GOV.azulTenue,
    paddingHorizontal: SPACING.md,
    paddingVertical: 6,
    borderBottomWidth: 1,
    borderBottomColor: GOV.borde,
  },
  migaTxt: { ...FONT.caption, color: GOV.azulOscuro },

  intro: {
    paddingHorizontal: SPACING.md,
    paddingTop: SPACING.md,
    paddingBottom: SPACING.sm,
    borderBottomWidth: 1,
    borderBottomColor: GOV.borde,
    backgroundColor: GOV.superficie,
    gap: SPACING.sm,
  },
  introTitulo: { ...FONT.h3, color: GOV.textoP },

  pasoIndicador: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.xs,
    paddingBottom: SPACING.xs,
  },
  pasoBurbuja: {
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: GOV.azul,
    justifyContent: 'center',
    alignItems: 'center',
  },
  pasoBurbujaActivo: { color: '#FFF', fontSize: 11, fontWeight: '800' },
  pasoBurbujaInactivo: { backgroundColor: GOV.borde },
  pasoBurbujaTextoInactivo: { color: GOV.textoT, fontSize: 11, fontWeight: '700' },
  pasoBurbujaCompletado: { backgroundColor: GOV.verde },
  pasoLinea: { width: 20, height: 2, backgroundColor: GOV.borde },
  pasoLineaCompletada: { backgroundColor: GOV.verde },
  pasoLabel: { ...FONT.caption, color: GOV.textoT, marginLeft: SPACING.xs, flex: 1 },

  lista: { padding: SPACING.md, paddingBottom: SPACING.xl },

  card: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: GOV.superficie,
    borderRadius: RADIUS.md,
    padding: SPACING.md,
    marginBottom: SPACING.sm,
    ...SHADOW.card,
    borderWidth: 2,
    borderColor: 'transparent',
  },
  cardActivo: { borderColor: GOV.azul, backgroundColor: GOV.azulTenue },
  iconoCirculo: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: GOV.azulTenue,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: SPACING.md,
    borderWidth: 1,
    borderColor: `${GOV.azul}33`,
  },
  iconoCirculoActivo: { backgroundColor: GOV.azul, borderColor: GOV.azul },
  cardTexto: { flex: 1 },
  cardNombre: { ...FONT.body, fontWeight: '600', color: GOV.textoP, marginBottom: 2 },
  cardNombreActivo: { color: GOV.azulOscuro, fontWeight: '700' },
  cardMeta: { ...FONT.caption, color: GOV.textoT, fontFamily: 'monospace' },

  btnContinuar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: GOV.azul,
    borderRadius: RADIUS.md,
    paddingVertical: 14,
    gap: SPACING.sm,
    marginTop: SPACING.sm,
  },
  btnTxt: { color: '#FFF', fontSize: 15, fontWeight: '700' },

  overlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: '#00000088',
    justifyContent: 'center',
    alignItems: 'center',
    gap: SPACING.md,
  },
  overlayTxt: { color: '#FFF', ...FONT.body, fontWeight: '600' },
});
