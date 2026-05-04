/**
 * Detalle de un hogar — GOV.CO design system.
 */
import { useEffect, useState } from 'react';
import { View, ScrollView, StyleSheet } from 'react-native';
import { Text, ActivityIndicator } from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { router, useLocalSearchParams } from 'expo-router';
import { hogaresApi } from '../../../src/api/hogares';
import { GovHeader } from '../../../src/components/GovHeader';
import { GovButton } from '../../../src/components/GovButton';
import { GOV, SPACING, RADIUS, SHADOW, FONT } from '../../../src/theme/govTheme';
import type { HogarDetalle, MiembroHogarResumen } from '../../../src/types';

const PARENTESCO_LABEL: Record<string, string> = {
  JEFE: 'Jefe/a', CONYUGE: 'Cónyuge', HIJO_A: 'Hijo/a',
  YERNO_NUERA: 'Yerno/Nuera', NIETO_A: 'Nieto/a',
  PADRE_MADRE: 'Padre/Madre', HERMANO_A: 'Hermano/a',
  OTRO_PARIENTE: 'Pariente', NO_PARIENTE: 'Sin parentesco',
};

// ─── Fila de información ──────────────────────────────────────────────────────

function InfoFila({ label, valor }: { label: string; valor: string }) {
  return (
    <View style={filaStyles.root}>
      <Text style={filaStyles.label}>{label}</Text>
      <Text style={filaStyles.valor}>{valor || '—'}</Text>
    </View>
  );
}

const filaStyles = StyleSheet.create({
  root: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 6,
    borderBottomWidth: 1,
    borderBottomColor: GOV.borde,
  },
  label: { ...FONT.small, color: GOV.textoT, flex: 1 },
  valor: { ...FONT.small, color: GOV.textoP, flex: 2, textAlign: 'right', fontWeight: '500' },
});

// ─── Ítem de miembro ──────────────────────────────────────────────────────────

function MiembroItem({ miembro }: { miembro: MiembroHogarResumen }) {
  return (
    <View style={miembroStyles.root}>
      <View style={miembroStyles.iconWrap}>
        <MaterialCommunityIcons name="account" size={16} color={GOV.azul} />
      </View>
      <View style={miembroStyles.info}>
        <Text style={miembroStyles.parentesco}>
          {PARENTESCO_LABEL[miembro.parentesco] ?? miembro.parentesco}
        </Text>
        <Text style={miembroStyles.dato}>
          {miembro.genero} · {miembro.edad != null ? `${miembro.edad} años` : 'edad N/D'}
        </Text>
      </View>
    </View>
  );
}

const miembroStyles = StyleSheet.create({
  root: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: GOV.borde,
  },
  iconWrap: {
    width: 30,
    height: 30,
    borderRadius: 15,
    backgroundColor: GOV.azulTenue,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: SPACING.sm,
  },
  info: { flex: 1 },
  parentesco: { ...FONT.small, color: GOV.azul, fontWeight: '600' },
  dato: { ...FONT.caption, color: GOV.textoS },
});

// ─── Sección card ─────────────────────────────────────────────────────────────

function SeccionCard({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <View style={seccionStyles.card}>
      <Text style={seccionStyles.titulo}>{titulo}</Text>
      {children}
    </View>
  );
}

const seccionStyles = StyleSheet.create({
  card: {
    backgroundColor: GOV.superficie,
    borderRadius: RADIUS.md,
    padding: SPACING.md,
    marginBottom: SPACING.md,
    ...SHADOW.card,
  },
  titulo: {
    ...FONT.h3,
    color: GOV.azulOscuro,
    marginBottom: SPACING.sm,
  },
});

// ─── Pantalla ─────────────────────────────────────────────────────────────────

export default function HogarDetalleScreen() {
  const { hogarId } = useLocalSearchParams<{ hogarId: string }>();
  const [hogar, setHogar] = useState<HogarDetalle | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!hogarId) return;
    hogaresApi.detalle(hogarId)
      .then((res) => setHogar(res.data))
      .catch(() => setError('No se pudo cargar el hogar.'))
      .finally(() => setCargando(false));
  }, [hogarId]);

  function aplicarInstrumento() {
    if (!hogar) return;
    router.push({ pathname: '/(main)/caracterizar/index', params: { hogarId: hogar.id } });
  }

  // ── Estados de carga / error ─────────────────────────────────────────────────

  if (cargando) {
    return (
      <View style={styles.root}>
        <GovHeader title="Detalle del hogar" onBack={() => router.back()} />
        <View style={styles.centrado}>
          <ActivityIndicator size="large" color={GOV.azul} />
        </View>
      </View>
    );
  }

  if (error || !hogar) {
    return (
      <View style={styles.root}>
        <GovHeader title="Detalle del hogar" onBack={() => router.back()} />
        <View style={styles.centrado}>
          <MaterialCommunityIcons name="alert-circle-outline" size={48} color={GOV.rojo} />
          <Text style={styles.errorTxt}>{error || 'Hogar no encontrado.'}</Text>
          <GovButton label="Volver" variant="secondary" onPress={() => router.back()} />
        </View>
      </View>
    );
  }

  const esActivo = hogar.estado === 'ACTIVO';
  const estadoColor = esActivo ? GOV.verde : GOV.naranja;
  const estadoBg    = esActivo ? GOV.verdeTenue : GOV.naranjaTenue;

  return (
    <View style={styles.root}>
      <GovHeader
        title={`Hogar ${hogar.id.slice(0, 8)}…`}
        subtitle={hogar.municipio_nombre ?? undefined}
        onBack={() => router.back()}
      />

      <ScrollView contentContainerStyle={styles.content}>

        {/* Fila de estado */}
        <View style={styles.estadoRow}>
          <View style={[styles.estadoChip, { backgroundColor: estadoBg }]}>
            <Text style={[styles.estadoTxt, { color: estadoColor }]}>{hogar.estado_display}</Text>
          </View>
          <Text style={styles.fecha}>{new Date(hogar.created_at).toLocaleDateString('es-CO')}</Text>
        </View>

        {/* Datos de vivienda */}
        <SeccionCard titulo="Datos de vivienda">
          <InfoFila label="Tipo"      valor={hogar.tipo_vivienda_display} />
          <InfoFila label="Ocupación" valor={hogar.condicion_ocupacion_display} />
          <InfoFila label="Estrato"   valor={String(hogar.estrato)} />
          <InfoFila label="Cuartos"   valor={String(hogar.numero_cuartos)} />
          <InfoFila label="Personas"  valor={String(hogar.numero_personas)} />
          {hogar.observaciones ? (
            <InfoFila label="Observaciones" valor={hogar.observaciones} />
          ) : null}
        </SeccionCard>

        {/* Miembros */}
        <SeccionCard titulo={`Miembros (${hogar.miembros.length})`}>
          {hogar.miembros.length === 0 ? (
            <Text style={styles.sinMiembros}>No se han registrado miembros aún.</Text>
          ) : (
            hogar.miembros.map((m) => <MiembroItem key={m.id} miembro={m} />)
          )}
        </SeccionCard>

        {/* Encuestas */}
        <SeccionCard titulo={`Encuestas (${hogar.total_sesiones})`}>
          <GovButton
            label="Aplicar instrumento"
            icon="clipboard-text-play"
            onPress={aplicarInstrumento}
          />
          {hogar.total_sesiones > 0 && (
            <View style={styles.verSesionesWrap}>
              <GovButton
                label="Ver sesiones de este hogar"
                variant="secondary"
                icon="clipboard-list"
                onPress={() => router.push({ pathname: '/(main)/encuestas', params: { hogar: hogar.id } })}
              />
            </View>
          )}
        </SeccionCard>

      </ScrollView>
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
    gap: SPACING.md,
  },
  content: {
    padding: SPACING.md,
    paddingBottom: SPACING.xxl,
  },
  estadoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: SPACING.md,
  },
  estadoChip: {
    borderRadius: RADIUS.pill,
    paddingHorizontal: 12,
    paddingVertical: 4,
  },
  estadoTxt: {
    fontSize: 12,
    fontWeight: '700',
  },
  fecha: {
    ...FONT.caption,
    color: GOV.textoT,
  },
  sinMiembros: {
    ...FONT.small,
    color: GOV.textoT,
    fontStyle: 'italic',
    textAlign: 'center',
    paddingVertical: SPACING.sm,
  },
  errorTxt: {
    ...FONT.body,
    color: GOV.rojo,
    textAlign: 'center',
  },
  verSesionesWrap: {
    marginTop: SPACING.sm,
  },
});
