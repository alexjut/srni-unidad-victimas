/**
 * Detalle de un hogar — GOV.CO design system.
 */
import { useEffect, useState } from 'react';
import { View, ScrollView, StyleSheet, Alert, Pressable } from 'react-native';
import { Text, ActivityIndicator } from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { router, useLocalSearchParams } from 'expo-router';
import { hogaresApi } from '../../../src/api/hogares';
import { victimasApi } from '../../../src/api/victimas';
import { useCaracterizacionStore } from '../../../src/stores/caracterizacionStore';
import { GovHeader } from '../../../src/components/GovHeader';
import { GovButton } from '../../../src/components/GovButton';
import { GOV, SPACING, RADIUS, SHADOW, FONT } from '../../../src/theme/govTheme';
import type { HogarDetalle, MiembroHogarResumen, VictimaResumenFuente } from '../../../src/types';

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
  const edadDisplay = miembro.fecha_nacimiento
    ? `n. ${miembro.fecha_nacimiento}`
    : 'fecha N/D';
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
          {miembro.genero} · {edadDisplay}
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

  // ── Store del flujo de caracterización ────────────────────────────────────
  const { victimaFuente, hogarId: hogarIdStore, limpiar } = useCaracterizacionStore();
  const esteHogarEnFlujo = hogarIdStore === hogarId;
  const consPersona = victimaFuente?.cons_persona ?? null;

  // ── Estado grupo familiar ─────────────────────────────────────────────────
  const [grupoFamiliar, setGrupoFamiliar] = useState<VictimaResumenFuente[]>([]);
  const [cargandoGrupo, setCargandoGrupo] = useState(false);
  const [miembrosAgregados, setMiembrosAgregados] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (!hogarId) return;
    hogaresApi.detalle(hogarId)
      .then((res) => setHogar(res.data))
      .catch(() => setError('No se pudo cargar el hogar.'))
      .finally(() => setCargando(false));
  }, [hogarId]);

  useEffect(() => {
    if (!esteHogarEnFlujo || consPersona == null) return;
    setCargandoGrupo(true);
    victimasApi.grupoFamiliar(consPersona)
      .then((res) => setGrupoFamiliar(res.data))
      .catch(() => {}) // silencioso — el grupo es opcional
      .finally(() => setCargandoGrupo(false));
  }, [esteHogarEnFlujo, consPersona]);

  function aplicarInstrumento() {
    if (!hogar) return;
    router.push({ pathname: '/(main)/caracterizar/index', params: { hogarId: hogar.id } });
  }

  // ── Agregar miembro desde la fuente ──────────────────────────────────────

  async function agregarDesdeFuente(miembro: VictimaResumenFuente, parentesco: string) {
    if (!hogarId) return;
    try {
      // Primero registra la víctima en la DB local si no está
      const { data: reg } = await victimasApi.registrarDesdeFuente(miembro);
      // Luego la agrega al hogar
      await hogaresApi.agregarMiembro(hogarId, {
        victima: reg.victima_id,
        parentesco,
        genero: miembro.genero,
        incluido_ruv: miembro.estado_ruv === 'INCLUIDO',
        tipo_persona: '5001',
      });
      // Marca como agregado
      const clave = `${miembro.tipo_documento}-${miembro.numero_documento}`;
      setMiembrosAgregados((prev) => new Set(prev).add(clave));
      // Refresca el hogar
      const refreshed = await hogaresApi.detalle(hogarId);
      setHogar(refreshed.data);
    } catch {
      Alert.alert('Error', 'No se pudo agregar el miembro. Intente nuevamente.');
    }
  }

  function seleccionarParentesco(miembro: VictimaResumenFuente) {
    const clave = `${miembro.tipo_documento}-${miembro.numero_documento}`;
    if (miembrosAgregados.has(clave)) return; // ya fue agregado
    Alert.alert(
      'Parentesco con el jefe',
      `¿Qué relación tiene ${miembro.primer_nombre} ${miembro.primer_apellido} con el jefe de hogar?`,
      [
        { text: 'Cónyuge',     onPress: () => agregarDesdeFuente(miembro, 'CONYUGE') },
        { text: 'Hijo/a',      onPress: () => agregarDesdeFuente(miembro, 'HIJO_A') },
        { text: 'Padre/Madre', onPress: () => agregarDesdeFuente(miembro, 'PADRE_MADRE') },
        { text: 'Hermano/a',   onPress: () => agregarDesdeFuente(miembro, 'HERMANO_A') },
        { text: 'Otro',        onPress: () => agregarDesdeFuente(miembro, 'OTRO_PARIENTE') },
        { text: 'Cancelar',    style: 'cancel' },
      ]
    );
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

        {/* Grupo familiar RUV — solo visible cuando el hogar está en el flujo activo */}
        {esteHogarEnFlujo && (cargandoGrupo || grupoFamiliar.length > 0) && (
          <SeccionCard titulo="Grupo familiar RUV">
            {cargandoGrupo ? (
              <ActivityIndicator size="small" color={GOV.azul} style={{ marginVertical: 8 }} />
            ) : (
              grupoFamiliar.map((miembro) => {
                const clave = `${miembro.tipo_documento}-${miembro.numero_documento}`;
                const yaAgregado = miembrosAgregados.has(clave);
                const nombre = [miembro.primer_nombre, miembro.segundo_nombre, miembro.primer_apellido, miembro.segundo_apellido]
                  .filter(Boolean).join(' ');
                return (
                  <View key={clave} style={grupoStyles.fila}>
                    <View style={grupoStyles.info}>
                      <Text style={grupoStyles.nombre}>{nombre}</Text>
                      <Text style={grupoStyles.meta}>
                        {miembro.tipo_documento} · {miembro.estado_ruv.replace('_', ' ')}
                      </Text>
                    </View>
                    <Pressable
                      onPress={() => seleccionarParentesco(miembro)}
                      disabled={yaAgregado}
                      style={[grupoStyles.btn, yaAgregado && grupoStyles.btnAgregado]}
                    >
                      <MaterialCommunityIcons
                        name={yaAgregado ? 'check' : 'account-plus'}
                        size={16}
                        color={yaAgregado ? GOV.verde : GOV.azul}
                      />
                      <Text style={[grupoStyles.btnTxt, yaAgregado && grupoStyles.btnTxtAgregado]}>
                        {yaAgregado ? 'Agregado' : 'Agregar'}
                      </Text>
                    </Pressable>
                  </View>
                );
              })
            )}
          </SeccionCard>
        )}

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

        {/* Botón finalizar conformación — solo en flujo activo */}
        {esteHogarEnFlujo && (
          <GovButton
            label="Finalizar conformación"
            icon="check-circle"
            variant="secondary"
            onPress={() => {
              limpiar();
              // No navegar — el usuario puede seguir viendo el hogar
            }}
          />
        )}

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

const grupoStyles = StyleSheet.create({
  fila: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: GOV.borde,
  },
  info: { flex: 1 },
  nombre: { ...FONT.small, fontWeight: '600', color: GOV.textoP },
  meta: { ...FONT.caption, color: GOV.textoT, marginTop: 2 },
  btn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: GOV.azulTenue,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: RADIUS.sm,
  },
  btnAgregado: { backgroundColor: GOV.verdeTenue },
  btnTxt: { ...FONT.label, color: GOV.azul },
  btnTxtAgregado: { color: GOV.verde },
});
