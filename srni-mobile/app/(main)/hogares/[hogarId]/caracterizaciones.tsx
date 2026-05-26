/**
 * Caracterizaciones del hogar (Sprint 14 — flujo cosido).
 *
 * Esta pantalla es el "hub" tras conformar el hogar:
 *  - Resumen rápido del hogar (autorizado, miembros, municipio)
 *  - Lista de caracterizaciones (sesiones de encuesta) ya creadas
 *  - Cada item navega al detalle de la sesión (encuestas/[sesionId])
 *  - Botón sticky "+ Nueva caracterización" → caracterizar/index?hogarId=X
 *
 * Reemplaza el flujo viejo:
 *  - conformar.tsx ya no crea la sesión directamente
 *  - [hogarId]/index.tsx ya no tiene dos botones sueltos
 */
import { useEffect, useState, useCallback } from 'react';
import { View, ScrollView, StyleSheet, Pressable, RefreshControl } from 'react-native';
import { Text, ActivityIndicator } from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { router, useLocalSearchParams, useFocusEffect } from 'expo-router';
import { hogaresApi } from '../../../../src/api/hogares';
import { GovHeader } from '../../../../src/components/GovHeader';
import { GovButton } from '../../../../src/components/GovButton';
import { EmptyState } from '../../../../src/components/EmptyState';
import { GOV, SPACING, RADIUS, SHADOW, FONT } from '../../../../src/theme/govTheme';
import type { HogarDetalle, SesionResumen, EstadoSesion } from '../../../../src/types';

// ── Mapa de colores por estado de la sesión ───────────────────────────────────

const ESTADO_COLOR: Record<EstadoSesion, { fg: string; bg: string; icon: string }> = {
  INICIADA:    { fg: GOV.naranja, bg: GOV.naranjaTenue, icon: 'clock-outline' },
  EN_PROGRESO: { fg: GOV.azul,    bg: GOV.azulTenue,    icon: 'progress-clock' },
  COMPLETADA:  { fg: GOV.verde,   bg: GOV.verdeTenue,   icon: 'check-circle' },
  SUSPENDIDA:  { fg: GOV.rojo,    bg: GOV.rojoTenue,    icon: 'pause-circle-outline' },
};

// ── Tarjeta de caracterización (una sesión) ───────────────────────────────────

function TarjetaSesion({
  sesion,
  onPress,
}: {
  sesion: SesionResumen;
  onPress: () => void;
}) {
  const colores = ESTADO_COLOR[sesion.estado] ?? ESTADO_COLOR.INICIADA;
  const fecha = new Date(sesion.fecha_inicio).toLocaleDateString('es-CO', {
    day: '2-digit', month: 'short', year: 'numeric',
  });

  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [styles.card, pressed && { opacity: 0.88 }]}
      accessibilityRole="button"
      accessibilityLabel={`Caracterización ${sesion.instrumento_nombre}, ${sesion.estado_display}`}
    >
      {/* Encabezado: instrumento + chip estado */}
      <View style={styles.cardEncabezado}>
        <View style={styles.cardTituloWrap}>
          <Text style={styles.cardInstrumento} numberOfLines={1}>
            {sesion.instrumento_nombre}
          </Text>
          <Text style={styles.cardVersion}>
            {sesion.instrumento_numero} · {fecha}
          </Text>
        </View>
        <View style={[styles.chipEstado, { backgroundColor: colores.bg }]}>
          <MaterialCommunityIcons name={colores.icon as any} size={12} color={colores.fg} />
          <Text style={[styles.chipEstadoTxt, { color: colores.fg }]}>
            {sesion.estado_display}
          </Text>
        </View>
      </View>

      {/* Barra de progreso */}
      <View style={styles.progresoFila}>
        <View style={styles.progresoBarra}>
          <View
            style={[
              styles.progresoRelleno,
              {
                width: `${Math.min(100, Math.max(0, sesion.porcentaje_completado))}%`,
                backgroundColor: colores.fg,
              },
            ]}
          />
        </View>
        <Text style={styles.progresoTxt}>{sesion.porcentaje_completado}%</Text>
      </View>

      {/* Pie: encuestador + chevron */}
      <View style={styles.cardPie}>
        <View style={styles.cardPieIzq}>
          <MaterialCommunityIcons name="account-outline" size={13} color={GOV.textoT} />
          <Text style={styles.cardPieTxt} numberOfLines={1}>
            {sesion.encuestador_nombre ?? 'Sin asignar'}
          </Text>
        </View>
        <MaterialCommunityIcons name="chevron-right" size={20} color={GOV.borde} />
      </View>
    </Pressable>
  );
}

// ── Tarjeta resumen del hogar (header) ────────────────────────────────────────

function ResumenHogar({ hogar }: { hogar: HogarDetalle }) {
  const autorizado = hogar.miembros.find((m) => m.es_autorizado);
  const totalMiembros = hogar.total_miembros ?? hogar.miembros.length;

  return (
    <View style={resumenStyles.card}>
      <View style={resumenStyles.row}>
        <MaterialCommunityIcons name="home-account" size={20} color={GOV.azul} />
        <Text style={resumenStyles.codigo}>Hogar {hogar.id.slice(0, 8)}…</Text>
      </View>

      <View style={resumenStyles.metaRow}>
        <View style={resumenStyles.metaItem}>
          <MaterialCommunityIcons name="map-marker" size={13} color={GOV.textoT} />
          <Text style={resumenStyles.metaTxt}>
            {hogar.municipio_nombre ?? 'Municipio no registrado'}
          </Text>
        </View>
        <View style={resumenStyles.metaItem}>
          <MaterialCommunityIcons name="account-group" size={13} color={GOV.textoT} />
          <Text style={resumenStyles.metaTxt}>
            {totalMiembros} integrante{totalMiembros !== 1 ? 's' : ''}
          </Text>
        </View>
      </View>

      {autorizado ? (
        <View style={resumenStyles.autorizadoFila}>
          <MaterialCommunityIcons name="account-star" size={13} color={GOV.amarillo} />
          <Text style={resumenStyles.autorizadoLabel}>Autorizado:</Text>
          <Text style={resumenStyles.autorizadoNombre} numberOfLines={1}>
            {autorizado.rol_display}
          </Text>
        </View>
      ) : null}
    </View>
  );
}

const resumenStyles = StyleSheet.create({
  card: {
    backgroundColor: GOV.superficie,
    borderRadius: RADIUS.md,
    padding: SPACING.md,
    marginBottom: SPACING.md,
    ...SHADOW.card,
    gap: SPACING.xs,
  },
  row: { flexDirection: 'row', alignItems: 'center', gap: SPACING.xs },
  codigo: { ...FONT.h3, color: GOV.azulOscuro },
  metaRow: { flexDirection: 'row', flexWrap: 'wrap', gap: SPACING.md, marginTop: 4 },
  metaItem: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  metaTxt: { ...FONT.caption, color: GOV.textoS },
  autorizadoFila: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginTop: SPACING.xs,
    paddingTop: SPACING.xs,
    borderTopWidth: 1,
    borderTopColor: GOV.borde,
  },
  autorizadoLabel: { ...FONT.caption, color: GOV.textoT, fontWeight: '600' },
  autorizadoNombre: { ...FONT.caption, color: GOV.azulOscuro, flex: 1, fontWeight: '600' },
});

// ── Pantalla principal ────────────────────────────────────────────────────────

export default function CaracterizacionesHogarScreen() {
  const { hogarId } = useLocalSearchParams<{ hogarId: string }>();
  const [hogar, setHogar] = useState<HogarDetalle | null>(null);
  const [cargando, setCargando] = useState(true);
  const [refrescando, setRefrescando] = useState(false);
  const [error, setError] = useState('');

  const cargar = useCallback(async () => {
    if (!hogarId) return;
    setError('');
    try {
      const { data } = await hogaresApi.detalle(hogarId);
      setHogar(data);
    } catch {
      setError('No se pudo cargar el hogar. Verifique la conexión.');
    } finally {
      setCargando(false);
      setRefrescando(false);
    }
  }, [hogarId]);

  // Carga inicial
  useEffect(() => {
    cargar();
  }, [cargar]);

  // Recarga cada vez que la pantalla vuelve a tener foco
  // (p. ej. tras crear una nueva caracterización y regresar)
  useFocusEffect(
    useCallback(() => {
      cargar();
    }, [cargar]),
  );

  function irANuevaCaracterizacion() {
    router.push({
      pathname: '/(main)/caracterizar',
      params: { hogarId: String(hogarId) },
    });
  }

  function abrirSesion(sesionId: string) {
    router.push({
      pathname: '/(main)/encuestas/[sesionId]',
      params: { sesionId },
    });
  }

  // Back coherente: vuelve al detalle del hogar (padre conceptual del hub).
  // Evita `router.back()` ciego que puede saltar al home si la pila se rompió.
  const volverAHogar = () =>
    router.push({
      pathname: '/(main)/hogares/[hogarId]',
      params: { hogarId: String(hogarId) },
    });

  const hogarCorto = hogar?.id ? hogar.id.slice(0, 8) : (hogarId ? String(hogarId).slice(0, 8) : '');

  // ── Estados de carga / error ────────────────────────────────────────────────

  if (cargando) {
    return (
      <View style={styles.root}>
        <GovHeader title="Caracterizaciones" onBack={volverAHogar} />
        <View style={styles.miga}>
          <Text style={styles.migaTxt}>
            Hogar {hogarCorto}…  ›  Caracterizaciones
          </Text>
        </View>
        <View style={styles.centrado}>
          <ActivityIndicator size="large" color={GOV.azul} />
        </View>
      </View>
    );
  }

  if (error || !hogar) {
    return (
      <View style={styles.root}>
        <GovHeader title="Caracterizaciones" onBack={volverAHogar} />
        <View style={styles.miga}>
          <Text style={styles.migaTxt}>
            Hogar {hogarCorto}…  ›  Caracterizaciones
          </Text>
        </View>
        <View style={styles.centrado}>
          <MaterialCommunityIcons name="alert-circle-outline" size={48} color={GOV.rojo} />
          <Text style={styles.errorTxt}>{error || 'Hogar no encontrado.'}</Text>
          <GovButton label="Volver" variant="secondary" onPress={volverAHogar} fullWidth={false} />
        </View>
      </View>
    );
  }

  const sesiones = hogar.sesiones ?? [];
  const tieneAutorizado = hogar.miembros.some((m) => m.es_autorizado);

  // ── Render principal ────────────────────────────────────────────────────────

  return (
    <View style={styles.root}>
      <GovHeader
        title="Caracterizaciones"
        subtitle={hogar.municipio_nombre ?? `Hogar ${hogarCorto}…`}
        onBack={volverAHogar}
      />

      {/* Miga de pan */}
      <View style={styles.miga}>
        <Text style={styles.migaTxt}>
          Hogar {hogarCorto}…  ›  Caracterizaciones
        </Text>
      </View>

      <ScrollView
        contentContainerStyle={styles.content}
        refreshControl={
          <RefreshControl
            refreshing={refrescando}
            onRefresh={() => {
              setRefrescando(true);
              cargar();
            }}
            colors={[GOV.azul]}
            tintColor={GOV.azul}
          />
        }
      >
        {/* Resumen del hogar */}
        <ResumenHogar hogar={hogar} />

        {/* Sección caracterizaciones */}
        <View style={styles.seccionEncabezado}>
          <Text style={styles.seccionTitulo}>
            Caracterizaciones del hogar ({sesiones.length})
          </Text>
        </View>

        {sesiones.length === 0 ? (
          <View style={styles.emptyWrap}>
            <EmptyState
              icon="clipboard-text-outline"
              title="Sin caracterizaciones todavía"
              message={
                tieneAutorizado
                  ? 'Aún no se ha iniciado ninguna caracterización para este hogar. Pulsa el botón inferior para crear la primera.'
                  : 'Primero confirma el autorizado del hogar para poder crear caracterizaciones.'
              }
            />
          </View>
        ) : (
          sesiones.map((s) => (
            <TarjetaSesion key={s.id} sesion={s} onPress={() => abrirSesion(s.id)} />
          ))
        )}
      </ScrollView>

      {/* Botón sticky inferior — Nueva caracterización */}
      <View style={styles.stickyFooter}>
        <GovButton
          label="+ Nueva caracterización"
          icon="clipboard-plus"
          onPress={irANuevaCaracterizacion}
          disabled={!tieneAutorizado}
        />
        {!tieneAutorizado ? (
          <Text style={styles.ayudaFooter}>
            Confirma el autorizado del hogar antes de crear caracterizaciones.
          </Text>
        ) : null}
      </View>
    </View>
  );
}

// ── Estilos ───────────────────────────────────────────────────────────────────

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
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: SPACING.xl,
    gap: SPACING.md,
  },
  content: {
    padding: SPACING.md,
    paddingBottom: 120, // espacio para el sticky footer
  },
  errorTxt: { ...FONT.body, color: GOV.rojo, textAlign: 'center' },

  // Sección
  seccionEncabezado: {
    marginBottom: SPACING.sm,
    paddingHorizontal: 4,
  },
  seccionTitulo: { ...FONT.h3, color: GOV.azulOscuro },

  // Card de sesión
  card: {
    backgroundColor: GOV.superficie,
    borderRadius: RADIUS.md,
    padding: SPACING.md,
    marginBottom: SPACING.sm,
    ...SHADOW.card,
    gap: SPACING.sm,
  },
  cardEncabezado: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: SPACING.sm,
  },
  cardTituloWrap: { flex: 1, gap: 2 },
  cardInstrumento: { ...FONT.body, color: GOV.textoP, fontWeight: '600' },
  cardVersion: { ...FONT.caption, color: GOV.textoT },

  // Chip de estado
  chipEstado: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: RADIUS.pill,
  },
  chipEstadoTxt: { fontSize: 11, fontWeight: '700' },

  // Progreso
  progresoFila: { flexDirection: 'row', alignItems: 'center', gap: SPACING.sm },
  progresoBarra: {
    flex: 1,
    height: 6,
    backgroundColor: GOV.fondoApp,
    borderRadius: 3,
    overflow: 'hidden',
  },
  progresoRelleno: { height: '100%', borderRadius: 3 },
  progresoTxt: { ...FONT.caption, color: GOV.textoS, fontWeight: '600', minWidth: 40, textAlign: 'right' },

  // Pie
  cardPie: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingTop: SPACING.xs,
    borderTopWidth: 1,
    borderTopColor: GOV.borde,
  },
  cardPieIzq: { flexDirection: 'row', alignItems: 'center', gap: 4, flex: 1 },
  cardPieTxt: { ...FONT.caption, color: GOV.textoS },

  // Empty wrap (centra el EmptyState dentro del scroll)
  emptyWrap: { minHeight: 280, justifyContent: 'center' },

  // Sticky footer
  stickyFooter: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: GOV.superficie,
    paddingHorizontal: SPACING.md,
    paddingTop: SPACING.sm,
    paddingBottom: SPACING.md,
    borderTopWidth: 1,
    borderTopColor: GOV.borde,
    ...SHADOW.fab,
  },
  ayudaFooter: {
    ...FONT.caption,
    color: GOV.textoT,
    textAlign: 'center',
    marginTop: SPACING.xs,
    fontStyle: 'italic',
  },
});
