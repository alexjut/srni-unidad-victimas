/**
 * Detalle de un hogar — GOV.CO design system.
 *
 * Muestra:
 *  - Badge ★ AUTORIZADO para el titular de la entrevista
 *  - Chips INCLUIDO (verde) / NO INCLUIDO (gris) por cada integrante
 *  - Selector de ROL (Miembro / Tutor / Cuidador permanente) al agregar
 *  - UN solo botón "Ver caracterizaciones (N)" → hub del hogar (Sprint 14)
 *
 * Sprint 14: se removieron los botones "Crear entrevista" y "Ver sesiones
 * de este hogar" — ahora todo pasa por el hub /(main)/hogares/[hogarId]/
 * caracterizaciones, que muestra el listado y permite crear nuevas desde
 * un solo lugar.
 */
import { useEffect, useState } from 'react';
import { View, ScrollView, StyleSheet, Alert, Pressable } from 'react-native';
import { Text, ActivityIndicator, Modal, Portal, TextInput } from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { router, useLocalSearchParams } from 'expo-router';
import { hogaresApi, MOTIVOS_RETIRO } from '../../../../src/api/hogares';
import type { MotivoRetiro } from '../../../../src/api/hogares';
import { victimasApi } from '../../../../src/api/victimas';
import { useCaracterizacionStore } from '../../../../src/stores/caracterizacionStore';
import { GovHeader } from '../../../../src/components/GovHeader';
import { GovButton } from '../../../../src/components/GovButton';
import { GOV, SPACING, RADIUS, SHADOW, FONT } from '../../../../src/theme/govTheme';
import type {
  HogarDetalle, MiembroHogarResumen, VictimaResumenFuente, RolMiembro,
} from '../../../../src/types';

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

function MiembroItem({ miembro, onRetirar, onReincorporar }: {
  miembro: MiembroHogarResumen;
  onRetirar?: (m: MiembroHogarResumen) => void;
  onReincorporar?: (m: MiembroHogarResumen) => void;
}) {
  const esAutorizado = miembro.es_autorizado;
  const incluido = miembro.estado_inclusion === 'INCLUIDO';
  const retirado = !!miembro.retirado_en;

  return (
    <View style={[miembroStyles.root, retirado && miembroStyles.rootRetirado]}>
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
        {/* Nombre del integrante — para el autorizado y miembros del RNI viene
            derivado de la Victima; para miembros de campo viene del nombre
            capturado en la conformación. Sin esto las filas se veían anónimas. */}
        <Text style={miembroStyles.nombre} numberOfLines={1}>
          {(miembro.nombre_completo || '').trim() || 'Sin nombre registrado'}
        </Text>
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

        {/*
          El retiro se MUESTRA, no se esconde. Ocultar al integrante retirado
          haria creer que se perdio un dato -ese susto ya se vivio en campo- y
          dejaria sin explicacion por que el hogar paso de cinco personas a tres.
        */}
        {retirado && (
          <View style={miembroStyles.retiroCaja}>
            <MaterialCommunityIcons name="account-off-outline" size={12} color={GOV.naranja} />
            <Text style={miembroStyles.retiroTxt}>
              {(miembro.motivo_retiro_display || 'Retirado')} · desde {miembro.retirado_en}
            </Text>
          </View>
        )}

        {/*
          Al autorizado no se le ofrece: es el titular del hogar. Si es el quien
          dejo de pertenecer, primero hay que cambiar el autorizado.
        */}
        {!esAutorizado && (retirado ? onReincorporar : onRetirar) && (
          <Pressable
            onPress={() => (retirado ? onReincorporar!(miembro) : onRetirar!(miembro))}
            hitSlop={8}
            accessibilityRole="button"
            accessibilityLabel={retirado
              ? `Deshacer el retiro de ${miembro.nombre_completo || 'este integrante'}`
              : `Retirar del hogar a ${miembro.nombre_completo || 'este integrante'}`}
          >
            <Text style={[miembroStyles.accion, retirado && miembroStyles.accionDeshacer]}>
              {retirado ? 'Deshacer retiro' : 'Retirar del hogar'}
            </Text>
          </Pressable>
        )}
      </View>
    </View>
  );
}

// --- Modal de retiro --------------------------------------------------------

/**
 * Pide el motivo y la FECHA DEL HECHO.
 *
 * La fecha no es la de hoy, y por eso se pregunta: una familia informa en
 * septiembre un fallecimiento de marzo, y ese es el caso corriente. Con la fecha
 * de hoy, la caracterizacion anterior quedaria diciendo que la persona
 * pertenecia al hogar cuando ya no era cierto.
 */
function ModalRetiro({ miembro, visible, guardando, onCancelar, onConfirmar }: {
  miembro: MiembroHogarResumen | null;
  visible: boolean;
  guardando: boolean;
  onCancelar: () => void;
  onConfirmar: (motivo: MotivoRetiro, fecha: string, observacion: string) => void;
}) {
  const [motivo, setMotivo] = useState<MotivoRetiro | null>(null);
  const [fecha, setFecha] = useState('');
  const [observacion, setObservacion] = useState('');

  useEffect(() => {
    if (visible) { setMotivo(null); setFecha(''); setObservacion(''); }
  }, [visible]);

  const fechaValida = /^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(fecha);
  // 'Otro' sin explicacion no dice nada, y es el motivo que mas se va a usar.
  const faltaDetalle = motivo === 'OTRO' && !observacion.trim();
  const puede = !!motivo && fechaValida && !faltaDetalle && !guardando;

  return (
    <Portal>
      <Modal visible={visible} onDismiss={onCancelar} contentContainerStyle={modalStyles.caja}>
        <Text style={modalStyles.titulo}>Retirar del hogar</Text>
        <Text style={modalStyles.nombre}>
          {(miembro?.nombre_completo || '').trim() || 'Integrante sin nombre'}
        </Text>
        <Text style={modalStyles.ayuda}>
          No se borra ni se pierde nada: la caracterizacion anterior queda igual.
          Solo se registra que esta persona ya no hace parte del hogar.
        </Text>

        <Text style={modalStyles.label}>Por que</Text>
        {MOTIVOS_RETIRO.map((op) => (
          <Pressable
            key={op.valor}
            onPress={() => setMotivo(op.valor)}
            style={[modalStyles.opcion, motivo === op.valor && modalStyles.opcionActiva]}
            accessibilityRole="radio"
            accessibilityState={{ selected: motivo === op.valor }}
          >
            <MaterialCommunityIcons
              name={motivo === op.valor ? 'radiobox-marked' : 'radiobox-blank'}
              size={18}
              color={motivo === op.valor ? GOV.azul : GOV.textoT}
            />
            <Text style={[modalStyles.opcionTxt, motivo === op.valor && modalStyles.opcionTxtActiva]}>
              {op.etiqueta}
            </Text>
          </Pressable>
        ))}

        <TextInput
          mode="outlined"
          label="Desde cuando (AAAA-MM-DD)"
          placeholder="2026-03-15"
          value={fecha}
          onChangeText={setFecha}
          style={modalStyles.input}
          outlineColor={GOV.borde}
          activeOutlineColor={GOV.azul}
        />
        <Text style={modalStyles.pista}>
          La fecha del hecho, no la de hoy. Preguntesela a la familia.
        </Text>

        <TextInput
          mode="outlined"
          label={motivo === 'OTRO' ? 'Explique el motivo *' : 'Observacion (opcional)'}
          value={observacion}
          onChangeText={setObservacion}
          multiline
          numberOfLines={2}
          style={modalStyles.input}
          outlineColor={GOV.borde}
          activeOutlineColor={GOV.azul}
        />

        <View style={modalStyles.botones}>
          <View style={modalStyles.boton}>
            <GovButton label="Cancelar" variant="secondary" onPress={onCancelar} />
          </View>
          <View style={modalStyles.boton}>
            <GovButton
              label="Retirar"
              loading={guardando}
              disabled={!puede}
              onPress={() => { if (puede) onConfirmar(motivo!, fecha, observacion); }}
            />
          </View>
        </View>
      </Modal>
    </Portal>
  );
}

const modalStyles = StyleSheet.create({
  caja: {
    backgroundColor: GOV.superficie,
    marginHorizontal: SPACING.md,
    padding: SPACING.md,
    borderRadius: RADIUS.md,
  },
  titulo: { ...FONT.h3, color: GOV.naranja, marginBottom: 2 },
  nombre: { ...FONT.small, color: GOV.textoP, fontWeight: '600', marginBottom: SPACING.xs },
  ayuda: { ...FONT.caption, color: GOV.textoS, marginBottom: SPACING.md },
  label: { ...FONT.label, color: GOV.textoS, marginBottom: SPACING.xs },
  opcion: {
    flexDirection: 'row', alignItems: 'center', gap: SPACING.xs,
    paddingVertical: 6, paddingHorizontal: SPACING.xs, borderRadius: RADIUS.sm,
  },
  opcionActiva: { backgroundColor: GOV.fondoApp },
  opcionTxt: { ...FONT.small, color: GOV.textoP },
  opcionTxtActiva: { fontWeight: '600', color: GOV.azulOscuro },
  input: { marginTop: SPACING.sm, backgroundColor: GOV.superficie },
  pista: { ...FONT.caption, color: GOV.textoT, marginTop: 2 },
  botones: { flexDirection: 'row', gap: SPACING.xs, marginTop: SPACING.md },
  boton: { flex: 1 },
});

const miembroStyles = StyleSheet.create({
  // El retirado se atenua, pero no al punto de no poder leerlo: tiene que
  // seguir siendo consultable, porque es el que explica el cambio del hogar.
  rootRetirado: { opacity: 0.62 },
  retiroCaja: {
    flexDirection: 'row', alignItems: 'center', gap: 4, marginTop: 4,
  },
  retiroTxt: { ...FONT.caption, color: GOV.naranja, fontWeight: '600', flexShrink: 1 },
  accion: {
    ...FONT.caption, color: GOV.naranja, fontWeight: '700',
    marginTop: 6, textDecorationLine: 'underline',
  },
  accionDeshacer: { color: GOV.azul },
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
  nombre: { ...FONT.body, color: GOV.textoP, fontWeight: '700' },
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

  // ── Retiro de un integrante ───────────────────────────────────────────────
  //
  // Es la salida para la familia que cambio entre una caracterizacion y la
  // siguiente. No borra: registra la novedad con su fecha, y por eso funciona
  // aunque el hogar ya tenga una caracterizacion completada.
  const [miembroARetirar, setMiembroARetirar] = useState<MiembroHogarResumen | null>(null);
  const [retirando, setRetirando] = useState(false);

  /**
   * Reemplaza UN integrante en el hogar que ya esta en pantalla.
   *
   * Se hace asi y no recargando el detalle completo: recargar pierde el scroll
   * -en un hogar de seis integrantes el encuestador vuelve arriba cada vez- y
   * dispara de nuevo la consulta del grupo familiar, que no cambio.
   */
  function reemplazarMiembro(actualizado: MiembroHogarResumen) {
    setHogar((prev) => (prev
      ? { ...prev, miembros: prev.miembros.map((x) => (x.id === actualizado.id ? actualizado : x)) }
      : prev));
  }

  async function confirmarRetiro(motivo: MotivoRetiro, fecha: string, observacion: string) {
    if (!hogarId || !miembroARetirar) return;
    setRetirando(true);
    try {
      const { data } = await hogaresApi.retirarMiembro(hogarId, miembroARetirar.id, {
        motivo, fecha, observacion,
      });
      reemplazarMiembro(data);
      setMiembroARetirar(null);
    } catch (err: any) {
      // El detalle del servidor cuando lo hay: dice POR QUE no se pudo, y es lo
      // unico que le permite al encuestador hacer algo distinto.
      const detalle = err?.response?.data?.detail
        || err?.response?.data?.fecha?.[0]
        || err?.response?.data?.observacion?.[0];
      Alert.alert(
        'No se pudo retirar',
        detalle || 'Revise la conexion e intente de nuevo. El integrante sigue en el hogar.',
      );
    } finally {
      setRetirando(false);
    }
  }

  function reincorporar(miembro: MiembroHogarResumen) {
    if (!hogarId) return;
    Alert.alert(
      'Deshacer el retiro',
      `${(miembro.nombre_completo || 'Este integrante').trim()} volvera a hacer parte del hogar.`,
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Deshacer',
          onPress: async () => {
            try {
              const { data } = await hogaresApi.reincorporarMiembro(hogarId, miembro.id);
              reemplazarMiembro(data);
            } catch {
              Alert.alert('No se pudo deshacer', 'Revise la conexion e intente de nuevo.');
            }
          },
        },
      ],
    );
  }

  useEffect(() => {
    if (!hogarId) {
      setError('No se recibió identificador del hogar.');
      setCargando(false);
      return;
    }
    hogaresApi.detalle(hogarId)
      .then((res) => setHogar(res.data))
      .catch((err: any) => {
        // Sprint 17 QA fix: errores específicos para que el usuario sepa qué pasó.
        const status = err?.response?.status;
        if (status === 404) {
          setError(
            'Este hogar ya no existe en el servidor. Vuelve a la lista de hogares.',
          );
        } else if (status === 403) {
          setError('No tienes permisos para ver este hogar.');
        } else if (status === 401) {
          setError('Tu sesión expiró. Vuelve a iniciar sesión.');
        } else if (!err?.response) {
          setError('Sin conexión con el servidor. Verifica tu red.');
        } else {
          setError(`No se pudo cargar el hogar (error ${status ?? 'desconocido'}).`);
        }
      })
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

  function verCaracterizaciones() {
    if (!hogar) return;
    router.push({
      pathname: '/(main)/hogares/[hogarId]/caracterizaciones',
      params: { hogarId: hogar.id },
    });
  }

  // ── Agregar miembro desde grupo familiar RUV ──────────────────────────────

  async function agregarDesdeFuente(miembro: VictimaResumenFuente, rol: RolMiembro) {
    if (!hogarId) return;
    try {
      const { data: reg } = await victimasApi.registrarDesdeFuente(miembro);
      // Se propaga el estado del padrón tal cual. Antes todo lo que no fuera
      // INCLUIDO caía en NO_INCLUIDO, que afirma una verificación que no hubo.
      const estadoInclusion =
        miembro.estado_ruv === 'INCLUIDO' ? 'INCLUIDO'
        : miembro.estado_ruv === 'NO_INCLUIDO' ? 'NO_INCLUIDO'
        : 'NO_VERIFICADO';
      await hogaresApi.agregarMiembro(hogarId, {
        victima: reg.victima_id,
        rol,
        estado_inclusion: estadoInclusion,
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
    // Sprint 17 QA: si el hogar no se pudo cargar, ofrecer ir a la lista
    // (router.back() puede volver a una ruta inválida tras reset de BD).
    const irAListaHogares = () => router.replace('/(main)/hogares');
    return (
      <View style={styles.root}>
        <GovHeader title="Detalle del hogar" onBack={irAListaHogares} />
        <View style={styles.centrado}>
          <MaterialCommunityIcons name="alert-circle-outline" size={48} color={GOV.rojo} />
          <Text style={styles.errorTxt}>{error || 'Hogar no encontrado.'}</Text>
          <GovButton label="Ir a la lista de hogares" variant="secondary" onPress={irAListaHogares} />
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
            hogar.miembros.map((m) => (
              <MiembroItem
                key={m.id}
                miembro={m}
                onRetirar={setMiembroARetirar}
                onReincorporar={reincorporar}
              />
            ))
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

        {/* Caracterizaciones del hogar — un solo botón unificado (Sprint 14) */}
        <SeccionCard titulo="Caracterizaciones del hogar">
          <GovButton
            label={`Ver caracterizaciones (${hogar.total_sesiones})`}
            icon="clipboard-list"
            onPress={verCaracterizaciones}
            disabled={!tieneAutorizado}
          />
          {!tieneAutorizado ? (
            <Text style={styles.ayudaEntrevista}>
              Primero confirma el autorizado del hogar para acceder a las caracterizaciones.
            </Text>
          ) : (
            <Text style={styles.ayudaEntrevista}>
              {hogar.total_sesiones === 0
                ? 'Aún no se ha iniciado ninguna caracterización para este hogar.'
                : 'Revisa el progreso, abre una caracterización existente o crea una nueva.'}
            </Text>
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

      <ModalRetiro
        miembro={miembroARetirar}
        visible={miembroARetirar !== null}
        guardando={retirando}
        onCancelar={() => setMiembroARetirar(null)}
        onConfirmar={confirmarRetiro}
      />
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
