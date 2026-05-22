/**
 * Detalle de un hogar — GOV.CO design system.
 *
 * Muestra:
 *  - Badge ★ AUTORIZADO para el titular de la entrevista
 *  - Chips INCLUIDO (verde) / NO INCLUIDO (gris) por cada integrante
 *  - Selector de ROL (Miembro / Tutor / Cuidador permanente) al agregar
 *  - Botón "Crear entrevista" solo activo cuando el hogar tiene su autorizado
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
import type {
  HogarDetalle, MiembroHogarResumen, VictimaResumenFuente, RolMiembro,
} from '../../../src/types';

// ─── Labels de rol ────────────────────────────────────────────────────────────

const ROL_LABEL: Record<RolMiembro, string> = {
  MIEMBRO:             'Miembro',
  TUTOR:               'Tutor',
  CUIDADOR_PERMANENTE: 'Cuidador permanente',
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
  const esAutorizado = miembro.es_autorizado;
  const incluido = miembro.estado_inclusion === 'INCLUIDO';

  return (
    <View style={miembroStyles.root}>
      {/* Ícono con fondo según autorizado */}
      <View style={[miembroStyles.iconWrap, esAutorizado && miembroStyles.iconWrapAutorizado]}>
        <MaterialCommunityIcons
          name={esAutorizado ? 'account-star' : 'account'}
          size={16}
          color={esAutorizado ? '#FFFFFF' : GOV.azul}
        />
      </View>

      {/* Datos del integrante */}
      <View style={miembroStyles.info}>
        <View style={miembroStyles.fila}>
          {esAutorizado && (
            <View style={miembroStyles.badgeAutorizado}>
              <MaterialCommunityIcons name="star" size={9} color={GOV.amarillo} />
              <Text style={miembroStyles.badgeAutorizadoTxt}>AUTORIZADO</Text>
            </View>
          )}
          <Text style={[miembroStyles.rol, esAutorizado && miembroStyles.rolAutorizado]}>
            {ROL_LABEL[miembro.rol] ?? miembro.rol_display}
          </Text>
        </View>
        <View style={miembroStyles.fila}>
          {/* Chip estado de inclusión */}
          <View style={[
            miembroStyles.chipInclusion,
            incluido ? miembroStyles.chipIncluido : miembroStyles.chipNoIncluido,
          ]}>
            <MaterialCommunityIcons
              name={incluido ? 'check-circle' : 'minus-circle-outline'}
              size={10}
              color={incluido ? GOV.verde : GOV.textoT}
            />
            <Text style={[
              miembroStyles.chipTxt,
              incluido ? miembroStyles.chipTxtIncluido : miembroStyles.chipTxtNoIncluido,
            ]}>
              {incluido ? 'Incluido' : 'No incluido'}
            </Text>
          </View>
          {miembro.fecha_nacimiento && (
            <Text style={miembroStyles.dato}>n. {miembro.fecha_nacimiento}</Text>
          )}
        </View>
      </View>
    </View>
  );
}

const miembroStyles = StyleSheet.create({
  root: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    paddingVertical: SPACING.sm,
    borderBottomWidth: 1,
    borderBottomColor: GOV.borde,
    gap: SPACING.sm,
  },
  iconWrap: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: GOV.azulTenue,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 2,
  },
  iconWrapAutorizado: {
    backgroundColor: GOV.azul,
  },
  info: { flex: 1, gap: 4 },
  fila: { flexDirection: 'row', alignItems: 'center', flexWrap: 'wrap', gap: 6 },
  rol: { ...FONT.small, color: GOV.azulOscuro, fontWeight: '600' },
  rolAutorizado: { color: GOV.azul },
  dato: { ...FONT.caption, color: GOV.textoS },
  // Badge AUTORIZADO
  badgeAutorizado: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 3,
    backgroundColor: GOV.azulOscuro,
    borderRadius: RADIUS.pill,
    paddingHorizontal: 6,
    paddingVertical: 2,
  },
  badgeAutorizadoTxt: {
    fontSize: 9,
    fontWeight: '800',
    color: '#FFFFFF',
    letterSpacing: 0.5,
  },
  // Chip INCLUIDO / NO INCLUIDO
  chipInclusion: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 3,
    borderRadius: RADIUS.pill,
    paddingHorizontal: 7,
    paddingVertical: 2,
  },
  chipIncluido: {
    backgroundColor: GOV.verdeTenue ?? '#E8F5E9',
  },
  chipNoIncluido: {
    backgroundColor: GOV.fondoApp ?? '#F5F5F5',
  },
  chipTxt: { fontSize: 10, fontWeight: '600' },
  chipTxtIncluido: { color: GOV.verde },
  chipTxtNoIncluido: { color: GOV.textoT },
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

  // ── El hogar tiene autorizado cuando hay al menos un miembro con es_autorizado=true
  const tieneAutorizado = (hogar?.miembros ?? []).some((m) => m.es_autorizado);

  function crearEntrevista() {
    if (!hogar) return;
    router.push({ pathname: '/(main)/caracterizar/index', params: { hogarId: hogar.id } });
  }

  // ── Agregar miembro desde grupo familiar RUV ──────────────────────────────

  async function agregarDesdeFuente(miembro: VictimaResumenFuente, rol: RolMiembro) {
    if (!hogarId) return;
    try {
      const { data: reg } = await victimasApi.registrarDesdeFuente(miembro);
      const incluido = miembro.estado_ruv === 'INCLUIDO';
      await hogaresApi.agregarMiembro(hogarId, {
        victima: reg.victima_id,
        rol,
        estado_inclusion: incluido ? 'INCLUIDO' : 'NO_INCLUIDO',
        genero: miembro.genero,
      });
      const clave = `${miembro.tipo_documento}-${miembro.numero_documento}`;
      setMiembrosAgregados((prev) => new Set(prev).add(clave));
      const refreshed = await hogaresApi.detalle(hogarId);
      setHogar(refreshed.data);
    } catch {
      Alert.alert('Error', 'No se pudo agregar el integrante. Intente nuevamente.');
    }
  }

  function seleccionarRol(miembro: VictimaResumenFuente) {
    const clave = `${miembro.tipo_documento}-${miembro.numero_documento}`;
    if (miembrosAgregados.has(clave)) return;
    const nombre = [miembro.primer_nombre, miembro.primer_apellido].filter(Boolean).join(' ');
    Alert.alert(
      'Rol en el hogar',
      `¿Cuál es el rol de ${nombre} en este hogar?`,
      [
        { text: 'Miembro',              onPress: () => agregarDesdeFuente(miembro, 'MIEMBRO') },
        { text: 'Tutor (de un menor)',  onPress: () => agregarDesdeFuente(miembro, 'TUTOR') },
        { text: 'Cuidador permanente',  onPress: () => agregarDesdeFuente(miembro, 'CUIDADOR_PERMANENTE') },
        { text: 'Cancelar',            style: 'cancel' },
      ]
    );
  }

  // ── Estados de carga / error ──────────────────────────────────────────────

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

        {/* Integrantes del hogar */}
        <SeccionCard titulo={`Integrantes del hogar (${hogar.miembros.length})`}>
          {hogar.miembros.length === 0 ? (
            <Text style={styles.sinMiembros}>No se han registrado integrantes aún.</Text>
          ) : (
            hogar.miembros.map((m) => <MiembroItem key={m.id} miembro={m} />)
          )}
        </SeccionCard>

        {/* Grupo familiar RUV — solo visible cuando el hogar está en el flujo activo */}
        {esteHogarEnFlujo && (cargandoGrupo || grupoFamiliar.length > 0) && (
          <SeccionCard titulo="Agregar del grupo familiar RUV">
            <Text style={styles.grupoAyuda}>
              Personas registradas junto al autorizado en la fuente RUV. Selecciona su rol en el hogar.
            </Text>
            {cargandoGrupo ? (
              <ActivityIndicator size="small" color={GOV.azul} style={{ marginVertical: 8 }} />
            ) : (
              grupoFamiliar.map((miembro) => {
                const clave = `${miembro.tipo_documento}-${miembro.numero_documento}`;
                const yaAgregado = miembrosAgregados.has(clave);
                const nombre = [miembro.primer_nombre, miembro.segundo_nombre, miembro.primer_apellido, miembro.segundo_apellido]
                  .filter(Boolean).join(' ');
                const incluido = miembro.estado_ruv === 'INCLUIDO';
                return (
                  <View key={clave} style={grupoStyles.fila}>
                    <View style={grupoStyles.info}>
                      <Text style={grupoStyles.nombre}>{nombre}</Text>
                      <View style={grupoStyles.metaFila}>
                        <View style={[
                          grupoStyles.chipInclusion,
                          incluido ? grupoStyles.chipIncluido : grupoStyles.chipNoIncluido,
                        ]}>
                          <Text style={[
                            grupoStyles.chipTxt,
                            incluido ? grupoStyles.chipTxtIncluido : grupoStyles.chipTxtNoIncluido,
                          ]}>
                            {incluido ? 'Incluido' : 'No incluido'}
                          </Text>
                        </View>
                        <Text style={grupoStyles.meta}>{miembro.tipo_documento}</Text>
                      </View>
                    </View>
                    <Pressable
                      onPress={() => seleccionarRol(miembro)}
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

        {/* Entrevista */}
        <SeccionCard titulo={`Entrevista de caracterización (${hogar.total_sesiones})`}>
          {/* Botón principal — solo activo cuando hay autorizado */}
          <GovButton
            label="Crear entrevista"
            icon="clipboard-text-play"
            onPress={crearEntrevista}
            disabled={!tieneAutorizado}
          />
          {!tieneAutorizado && (
            <Text style={styles.ayudaEntrevista}>
              Primero confirma el autorizado del hogar para crear la entrevista.
            </Text>
          )}
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
            label="Finalizar conformación del hogar"
            icon="check-circle"
            variant="secondary"
            onPress={() => {
              limpiar();
            }}
          />
        )}

      </ScrollView>
    </View>
  );
}

// ─── Estilos ──────────────────────────────────────────────────────────────────

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
  grupoAyuda: {
    ...FONT.caption,
    color: GOV.textoS,
    marginBottom: SPACING.sm,
    lineHeight: 16,
  },
  ayudaEntrevista: {
    ...FONT.caption,
    color: GOV.textoT,
    textAlign: 'center',
    marginTop: SPACING.xs,
    fontStyle: 'italic',
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
    gap: SPACING.sm,
  },
  info: { flex: 1, gap: 4 },
  nombre: { ...FONT.small, fontWeight: '600', color: GOV.textoP },
  metaFila: { flexDirection: 'row', alignItems: 'center', gap: 6, flexWrap: 'wrap' },
  meta: { ...FONT.caption, color: GOV.textoT },
  chipInclusion: {
    borderRadius: RADIUS.pill,
    paddingHorizontal: 6,
    paddingVertical: 2,
  },
  chipIncluido: { backgroundColor: GOV.verdeTenue ?? '#E8F5E9' },
  chipNoIncluido: { backgroundColor: GOV.fondoApp ?? '#F5F5F5' },
  chipTxt: { fontSize: 10, fontWeight: '600' },
  chipTxtIncluido: { color: GOV.verde },
  chipTxtNoIncluido: { color: GOV.textoT },
  btn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: GOV.azulTenue,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: RADIUS.sm,
  },
  btnAgregado: { backgroundColor: GOV.verdeTenue ?? '#E8F5E9' },
  btnTxt: { ...FONT.label, color: GOV.azul },
  btnTxtAgregado: { color: GOV.verde },
});
