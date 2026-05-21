/**
 * Dashboard del encuestador — estilo GOV.CO institucional.
 */
import { View, ScrollView, StyleSheet, Pressable } from 'react-native';
import { Text, Chip, ActivityIndicator } from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { useAuthStore } from '../../src/stores/authStore';
import { useSyncStore, getEstadoSync } from '../../src/stores/syncStore';
import { GovHeader } from '../../src/components/GovHeader';
import { GovButton } from '../../src/components/GovButton';
import { NextStepCard } from '../../src/components/NextStepCard';
import { GOV, SPACING, RADIUS, SHADOW, FONT } from '../../src/theme/govTheme';

// ─── Chip de sincronización ────────────────────────────────────────────────────

const SYNC_CFG = {
  sincronizando: { label: 'Sincronizando…', color: GOV.azul,     bg: GOV.azulTenue },
  pendientes:    { label: (n: number) => `${n} pendiente${n !== 1 ? 's' : ''}`, color: GOV.naranja, bg: GOV.naranjaTenue },
  sin_conexion:  { label: 'Sin conexión',  color: '#616161',      bg: '#F5F5F5' },
  error:         { label: (n: number) => `${n} error${n !== 1 ? 'es' : ''}`, color: GOV.rojo, bg: GOV.rojoTenue },
  sincronizado:  { label: '✓ Al día',      color: GOV.verde,      bg: GOV.verdeTenue },
} as const;

function SyncChip() {
  const syncState = useSyncStore();
  const estado = getEstadoSync(syncState);
  const { triggerSync, sincronizando, pendientesCola, erroresCola } = syncState;

  const cfg = SYNC_CFG[estado];
  const labelFn = cfg.label as string | ((n: number) => string);
  const label =
    estado === 'pendientes' ? (labelFn as (n: number) => string)(pendientesCola) :
    estado === 'error'      ? (labelFn as (n: number) => string)(erroresCola) :
    labelFn as string;

  return (
    <Chip
      mode="flat"
      style={{ backgroundColor: cfg.bg, borderRadius: RADIUS.pill }}
      textStyle={{ color: cfg.color, fontSize: 11, fontWeight: '600' }}
      onPress={estado !== 'sincronizando' ? triggerSync : undefined}
      icon={sincronizando ? undefined : estado === 'sin_conexion' ? 'wifi-off' : estado === 'error' ? 'alert-circle' : 'cloud-check'}
    >
      {sincronizando ? 'Sincronizando…' : label}
    </Chip>
  );
}

// ─── Fila de acción ─────────────────────────────────────────────────────────────

function AccionRow({
  icon, label, subtitle, onPress,
}: { icon: string; label: string; subtitle?: string; onPress: () => void }) {
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [styles.accionRow, pressed && styles.accionPressed]}
      accessibilityRole="button"
    >
      <View style={styles.accionIcon}>
        <MaterialCommunityIcons name={icon as any} size={22} color={GOV.azul} />
      </View>
      <View style={styles.accionTexto}>
        <Text style={styles.accionLabel}>{label}</Text>
        {subtitle ? <Text style={styles.accionSub}>{subtitle}</Text> : null}
      </View>
      <MaterialCommunityIcons name="chevron-right" size={20} color={GOV.borde} />
    </Pressable>
  );
}

// ─── Pantalla ────────────────────────────────────────────────────────────────────

export default function DashboardScreen() {
  const { usuario, logout } = useAuthStore();
  const syncState = useSyncStore();
  const perfil = usuario?.perfil;
  const nombre = usuario?.nombre_completo ?? '—';
  const primerNombre = nombre.split(' ')[0];

  return (
    <View style={styles.root}>
      <GovHeader
        title={`Hola, ${primerNombre}`}
        subtitle={perfil?.nombre ?? 'Sin perfil asignado'}
        right={<SyncChip />}
      />

      <ScrollView contentContainerStyle={styles.content}>

        {/* Siguiente paso */}
        {perfil?.puede_caracterizar && (
          <NextStepCard
            title="Registrar nuevo hogar"
            description="Inicia el proceso de caracterización creando la unidad familiar."
            icon="home-plus"
            onPress={() => router.push('/(main)/hogares/nuevo')}
          />
        )}

        {/* Acciones principales */}
        <Text style={styles.seccionTitulo}>Acciones</Text>

        <View style={styles.accionesCard}>
          {perfil?.puede_buscar_rni && (
            <AccionRow
              icon="magnify"
              label="Búsqueda RNI"
              subtitle="Consultar víctimas registradas"
              onPress={() => router.push('/(main)/busqueda')}
            />
          )}

          {perfil?.puede_caracterizar && (
            <>
              <View style={styles.separador} />
              <AccionRow
                icon="home-group"
                label="Hogares"
                subtitle="Gestionar unidades familiares"
                onPress={() => router.push('/(main)/hogares')}
              />
              <View style={styles.separador} />
              <AccionRow
                icon="clipboard-list"
                label="Encuestas"
                subtitle="Sesiones PAARI en curso"
                onPress={() => router.push('/(main)/encuestas')}
              />
              <View style={styles.separador} />
              <AccionRow
                icon="form-select"
                label="Formulario PAARI"
                subtitle="Nueva sesión de caracterización"
                onPress={() => router.push('/(main)/formulario')}
              />
            </>
          )}
        </View>

        {/* Sincronización */}
        <Text style={styles.seccionTitulo}>Sistema</Text>
        <View style={styles.accionesCard}>
          <AccionRow
            icon="cloud-sync"
            label="Estado de sincronización"
            subtitle={syncState.pendientesCola > 0
              ? `${syncState.pendientesCola} pendiente(s) en cola`
              : syncState.erroresCola > 0
                ? `${syncState.erroresCola} error(es) en cola`
                : 'Todo al día'}
            onPress={() => router.push('/(main)/sync-status')}
          />
        </View>

        {/* Cerrar sesión */}
        <View style={styles.logoutWrap}>
          <GovButton
            label="Cerrar sesión"
            variant="danger"
            icon="logout"
            onPress={logout}
          />
        </View>

      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: GOV.fondoApp,
  },
  content: {
    padding: SPACING.md,
    paddingBottom: SPACING.xxl,
  },
  seccionTitulo: {
    ...FONT.label,
    color: GOV.textoT,
    marginBottom: SPACING.sm,
    marginTop: SPACING.xs,
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  accionesCard: {
    backgroundColor: GOV.superficie,
    borderRadius: RADIUS.md,
    ...SHADOW.card,
    overflow: 'hidden',
  },
  accionRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: SPACING.md,
    paddingVertical: 14,
    minHeight: 56,
  },
  accionPressed: {
    backgroundColor: GOV.fondoApp,
  },
  accionIcon: {
    width: 36,
    height: 36,
    borderRadius: RADIUS.sm,
    backgroundColor: GOV.azulTenue,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: SPACING.md,
  },
  accionTexto: {
    flex: 1,
  },
  accionLabel: {
    ...FONT.body,
    fontWeight: '600',
    color: GOV.textoP,
  },
  accionSub: {
    ...FONT.caption,
    color: GOV.textoS,
    marginTop: 1,
  },
  separador: {
    height: 1,
    backgroundColor: GOV.borde,
    marginLeft: SPACING.md + 36 + SPACING.md,
  },
  logoutWrap: {
    marginTop: SPACING.xl,
  },
});
