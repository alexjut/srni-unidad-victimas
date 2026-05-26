// Lista de capítulos — Sprint 8: progreso real por capítulo + estado visual.
import { useEffect, useState, useMemo } from 'react';
import { View, FlatList, StyleSheet, Pressable, Alert, Modal, KeyboardAvoidingView, Platform } from 'react-native';
import { Text, ProgressBar, ActivityIndicator, TextInput } from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { router, useLocalSearchParams } from 'expo-router';
import * as instrumentos from '../../../src/services/instrumentos';
import * as borradoresDao from '../../../src/db/borradoresDao';
import type { CapituloRow, InstrumentoMeta } from '../../../src/db/instrumentoDao';
import { useIAStore } from '../../../src/stores/iaStore';
import { encuestasApi } from '../../../src/api/encuestas';
import { reportarError } from '../../../src/services/errorReporter';
import { GovHeader } from '../../../src/components/GovHeader';
import { GovButton } from '../../../src/components/GovButton';
import { EmptyState } from '../../../src/components/EmptyState';
import { GOV, SPACING, RADIUS, SHADOW, FONT } from '../../../src/theme/govTheme';

// ─── Tipos ────────────────────────────────────────────────────────────────────

type EstadoCap = 'pendiente' | 'en_progreso' | 'completado';

interface CapProgress {
  estado: EstadoCap;
  respondidas: number;
  obligatorias: number;
}

const ESTADO_ICONO: Record<EstadoCap, string> = {
  pendiente:    'circle-outline',
  en_progreso:  'progress-clock',
  completado:   'check-circle',
};

const ESTADO_COLOR: Record<EstadoCap, string> = {
  pendiente:   GOV.borde,
  en_progreso: GOV.naranja,
  completado:  GOV.verde,
};

// ─── Tarjeta de capítulo ──────────────────────────────────────────────────────

function CapituloCard({
  capitulo,
  index,
  progress,
  sesionServerId,
  instrumentoId,
  hogarId,
  modoIA,
}: {
  capitulo: instrumentoDao.CapituloRow;
  index: number;
  progress: CapProgress;
  sesionServerId?: string;
  instrumentoId?: string;
  hogarId?: string;
  modoIA: boolean;
}) {
  const colorEstado = ESTADO_COLOR[progress.estado];
  const iconoEstado = ESTADO_ICONO[progress.estado];

  function handlePress() {
    if (modoIA) {
      router.push({
        pathname: '/(main)/formulario/grabacion-entrevista' as any,
        params: {
          temaId: capitulo.id,
          capituloNombre: capitulo.nombre,
          ...(sesionServerId ? { sesionServerId } : {}),
          ...(instrumentoId  ? { instrumentoId }  : {}),
        },
      });
    } else {
      router.push({
        pathname: '/(main)/formulario/[temaId]',
        params: {
          temaId: capitulo.id,
          ...(sesionServerId ? { sesionServerId } : {}),
          ...(instrumentoId  ? { instrumentoId }  : {}),
          ...(hogarId        ? { hogarId }         : {}),
        },
      });
    }
  }

  return (
    <Pressable
      onPress={handlePress}
      style={({ pressed }) => [
        styles.card,
        pressed && styles.cardPressed,
        progress.estado === 'completado' && styles.cardCompletado,
      ]}
      accessibilityRole="button"
      accessibilityLabel={`Capítulo ${index + 1}: ${capitulo.nombre}`}
    >
      {/* Número / estado */}
      <View style={[styles.numCircle, { borderColor: colorEstado + '88' }]}>
        {progress.estado === 'pendiente' ? (
          <Text style={[styles.numTxt, { color: GOV.textoT }]}>{String(index + 1).padStart(2, '0')}</Text>
        ) : (
          <MaterialCommunityIcons
            name={iconoEstado as any}
            size={20}
            color={colorEstado}
          />
        )}
      </View>

      <View style={styles.cardTexto}>
        <Text style={[styles.capNombre, progress.estado === 'completado' && styles.capNombreOk]} numberOfLines={2}>
          {capitulo.nombre}
        </Text>
        <Text style={styles.capCodigo}>
          [{capitulo.codigo}]  ·  {capitulo.nivel === 'PERSONA' ? 'Por persona' : 'Por hogar'}
        </Text>

        {/* Mini barra de progreso por capítulo */}
        {progress.obligatorias > 0 && (
          <View style={styles.capProgresoWrap}>
            <ProgressBar
              progress={progress.respondidas / progress.obligatorias}
              style={styles.capProgressBar}
              color={colorEstado}
            />
            <Text style={[styles.capProgresoPct, { color: colorEstado }]}>
              {progress.respondidas}/{progress.obligatorias}
            </Text>
          </View>
        )}
      </View>

      {modoIA ? (
        <MaterialCommunityIcons name="robot" size={16} color={GOV.azul} style={{ marginRight: 4 }} />
      ) : null}
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

  const { activo: iaActivo } = useIAStore();

  const [capitulos, setCapitulos] = useState<CapituloRow[]>([]);
  const [meta, setMeta] = useState<InstrumentoMeta | null>(null);
  const [cargando, setCargando] = useState(true);
  const [modoIA, setModoIA] = useState<boolean | null>(null);

  // Progreso por capítulo
  const [conteoPreguntas, setConteoPreguntas] = useState<
    Record<string, { total: number; obligatorias: number }>
  >({});
  const [conteoRespondidas, setConteoRespondidas] = useState<Record<string, number>>({});

  // Finalizar sesión
  const [modalFinalizar, setModalFinalizar] = useState(false);
  const [observaciones, setObservaciones] = useState('');
  const [finalizando, setFinalizando] = useState(false);

  const [descargando, setDescargando] = useState(false);
  const [errorDescarga, setErrorDescarga] = useState('');

  // Sprint 18 F1B: instrumentos en memoria (require bundle). Activamos el
  // perfil correcto leyendo el instrumento_codigo de la sesión y todo
  // queda en RAM — sin SQLite, sin race conditions, sin lock.
  async function cargarTodo() {
    setCargando(true);
    setErrorDescarga('');
    try {
      // 1. Determinar qué perfil activar
      let codigoPerfil: string | null = null;
      if (sesionServerId) {
        try {
          const { data: sesion } = await encuestasApi.detalle(sesionServerId);
          codigoPerfil = (sesion as any).instrumento_codigo ?? null;
        } catch (e) {
          reportarError({
            nivel: 'warn',
            mensaje: 'No se pudo cargar detalle de sesión — usando perfil actual o TERRITORIAL',
            stack: (e as Error)?.stack,
            pantalla: 'formulario/index',
            contexto: { sesionServerId },
          });
        }
      }
      codigoPerfil = codigoPerfil ?? instrumentos.getPerfilActivo() ?? 'TERRITORIAL';

      try {
        instrumentos.activarPerfil(codigoPerfil);
      } catch (e) {
        setErrorDescarga(`El perfil "${codigoPerfil}" no está disponible en este dispositivo.`);
        reportarError({
          nivel: 'error',
          mensaje: 'activarPerfil falló',
          stack: (e as Error)?.stack,
          pantalla: 'formulario/index',
          contexto: { codigoPerfil },
        });
      }

      // 2. Leer de memoria — instantáneo
      const caps = instrumentos.getCapitulos();
      const m = instrumentos.getMeta();
      const conteo = instrumentos.contarPreguntasPorCapitulo();

      setCapitulos(caps);
      setMeta(m);
      setConteoPreguntas(conteo);

      // 3. Cargar respuestas del borrador (SI tenemos SQLite, eso sí)
      if (sesionServerId) {
        const borrador = await borradoresDao.findBySesionId(sesionServerId);
        if (borrador) {
          setConteoRespondidas(await borradoresDao.contarRespuestasPorCapitulo(borrador.id));
        }
      }
    } catch (e) {
      reportarError({
        nivel: 'error',
        mensaje: 'formulario/index cargarTodo falló: ' + ((e as Error)?.message ?? String(e)),
        stack: (e as Error)?.stack,
        pantalla: 'formulario/index',
        contexto: { sesionServerId, instrumentoId, hogarId },
      });
    } finally {
      setCargando(false);
    }
  }

  useEffect(() => {
    cargarTodo();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sesionServerId]);

  // Recalcular progreso al volver de un capítulo
  useEffect(() => {
    if (!sesionServerId) return;
    const refrescar = async () => {
      const borrador = await borradoresDao.findBySesionId(sesionServerId);
      if (borrador) {
        setConteoRespondidas(await borradoresDao.contarRespuestasPorCapitulo(borrador.id));
      }
    };
    // Expo Router no tiene un onFocus nativo fácil aquí; usamos un pequeño delay
    const t = setTimeout(refrescar, 300);
    return () => clearTimeout(t);
  }, [sesionServerId]);

  // ── Progreso global ─────────────────────────────────────────────────────────
  const { totalObligGlobal, respondidoGlobal, capsCompletados } = useMemo(() => {
    let total = 0, respondido = 0, completados = 0;
    for (const cap of capitulos) {
      const cp = conteoPreguntas[cap.id];
      const cr = conteoRespondidas[cap.id] ?? 0;
      if (!cp) continue;
      total      += cp.obligatorias;
      respondido += Math.min(cr, cp.obligatorias);
      if (cp.obligatorias > 0 && cr >= cp.obligatorias) completados++;
    }
    return { totalObligGlobal: total, respondidoGlobal: respondido, capsCompletados: completados };
  }, [capitulos, conteoPreguntas, conteoRespondidas]);

  const progresoGlobal = totalObligGlobal > 0 ? respondidoGlobal / totalObligGlobal : 0;

  function getCapProgress(capId: string): CapProgress {
    const cp = conteoPreguntas[capId];
    const cr = conteoRespondidas[capId] ?? 0;
    if (!cp || cp.obligatorias === 0) return { estado: 'pendiente', respondidas: 0, obligatorias: 0 };
    if (cr >= cp.obligatorias) return { estado: 'completado', respondidas: cr, obligatorias: cp.obligatorias };
    if (cr > 0)                return { estado: 'en_progreso', respondidas: cr, obligatorias: cp.obligatorias };
    return { estado: 'pendiente', respondidas: 0, obligatorias: cp.obligatorias };
  }

  async function handleFinalizar() {
    if (!sesionServerId) return;
    setFinalizando(true);
    try {
      await encuestasApi.finalizar(sesionServerId, { observaciones: observaciones.trim() || undefined });
      setModalFinalizar(false);
      Alert.alert(
        'Sesión finalizada',
        'La sesión ha sido cerrada exitosamente.',
        [{ text: 'Aceptar', onPress: () => router.back() }],
      );
    } catch (err: any) {
      Alert.alert('Error', err?.response?.data?.detail ?? 'No se pudo finalizar la sesión.');
    } finally {
      setFinalizando(false);
    }
  }

  const subtitulo = hogarId
    ? `Hogar ${hogarId.slice(0, 8)}… · ${capitulos.length} capítulos`
    : `${capitulos.length} capítulos`;

  // Miga: muestra el contexto del flujo (Sesión › Capítulos), con Hogar si está disponible.
  // El back nativo de router.back() es correcto porque venimos de [sesionId].
  const sesionCorta = sesionServerId ? String(sesionServerId).slice(0, 8) : null;
  const hogarCorto  = hogarId ? String(hogarId).slice(0, 8) : null;
  const renderMiga = () => (
    <View style={styles.miga}>
      <Text style={styles.migaTxt}>
        {hogarCorto ? `Hogar ${hogarCorto}…  ›  ` : ''}
        {sesionCorta ? `Sesión ${sesionCorta}…  ›  ` : ''}
        Capítulos
      </Text>
    </View>
  );

  if (cargando) {
    return (
      <View style={styles.root}>
        <GovHeader title="Formulario" subtitle="Instrumento de caracterización" onBack={() => router.back()} />
        {renderMiga()}
        <View style={styles.centrado}>
          <ActivityIndicator size="large" color={GOV.azul} />
          <Text style={styles.cargandoTxt}>
            {descargando ? 'Descargando instrumento…' : 'Cargando instrumento…'}
          </Text>
        </View>
      </View>
    );
  }

  if (capitulos.length === 0) {
    return (
      <View style={styles.root}>
        <GovHeader title="Formulario" subtitle="Instrumento de caracterización" onBack={() => router.back()} />
        {renderMiga()}
        <EmptyState
          icon="clipboard-alert-outline"
          title="Sin instrumento"
          message={
            errorDescarga
              || 'No hay instrumento cargado en el dispositivo. Toca "Reintentar descarga" si tienes conexión.'
          }
          actionLabel="Reintentar descarga"
          onAction={cargarTodo}
        />
      </View>
    );
  }

  const mostrarSelectorModo = modoIA === null && !!sesionServerId;

  return (
    <View style={styles.root}>
      <GovHeader
        title={meta ? `${meta.perfil_codigo} ${meta.version}` : 'Formulario'}
        subtitle={subtitulo}
        onBack={() => router.back()}
      />

      {/* Miga de pan */}
      {renderMiga()}

      {/* ── Selector de modo ────────────────────────────────────────────────── */}
      {mostrarSelectorModo && (
        <View style={styles.selectorModo}>
          <Text style={styles.selectorTitulo}>Seleccione el modo de captura</Text>
          <View style={styles.selectorBotones}>
            <Pressable
              style={({ pressed }) => [styles.modoCard, pressed && styles.modoCardPressed]}
              onPress={() => setModoIA(false)}
              accessibilityRole="button"
            >
              <MaterialCommunityIcons name="pencil" size={28} color={GOV.azulOscuro} />
              <Text style={styles.modoCardTitulo}>Manual</Text>
              <Text style={styles.modoCardDesc}>Responda cada pregunta directamente.</Text>
            </Pressable>

            {iaActivo ? (
              <Pressable
                style={({ pressed }) => [styles.modoCard, styles.modoCardIA, pressed && styles.modoCardPressed]}
                onPress={() => setModoIA(true)}
                accessibilityRole="button"
              >
                <MaterialCommunityIcons name="robot" size={28} color={GOV.azul} />
                <Text style={[styles.modoCardTitulo, { color: GOV.azul }]}>Asistido por IA</Text>
                <Text style={styles.modoCardDesc}>Transcriba la entrevista.</Text>
              </Pressable>
            ) : (
              <Pressable
                style={[styles.modoCard, styles.modoCardIADesactivado]}
                onPress={() =>
                  router.push({
                    pathname: '/(main)/formulario/consentimiento-ia',
                    params: { sesionEncuestaId: sesionServerId ?? '' },
                  })
                }
                accessibilityRole="button"
              >
                <MaterialCommunityIcons name="robot-off" size={28} color={GOV.textoT} />
                <Text style={[styles.modoCardTitulo, { color: GOV.textoS }]}>Asistido por IA</Text>
                <Text style={styles.modoCardDesc}>Toque para activar el consentimiento IA.</Text>
              </Pressable>
            )}
          </View>
        </View>
      )}

      {/* ── Banner de modo activo ────────────────────────────────────────────── */}
      {modoIA !== null && (
        <View style={[styles.modoActivoBanner, modoIA ? styles.modoActivoIA : styles.modoActivoManual]}>
          <MaterialCommunityIcons
            name={modoIA ? 'robot' : 'pencil'}
            size={14}
            color={modoIA ? GOV.azul : GOV.textoS}
          />
          <Text style={[styles.modoActivoTxt, { color: modoIA ? GOV.azul : GOV.textoS }]}>
            Modo {modoIA ? 'asistido por IA' : 'manual'} activo
          </Text>
          <Pressable onPress={() => setModoIA(null)} style={styles.cambiarModo}>
            <Text style={styles.cambiarModoTxt}>Cambiar</Text>
          </Pressable>
        </View>
      )}

      {/* ── Progreso global ──────────────────────────────────────────────────── */}
      <View style={styles.progresoWrap}>
        <View style={styles.progresoRow}>
          <Text style={styles.progresoLabel}>
            {capsCompletados} de {capitulos.length} capítulos completados
          </Text>
          <Text style={[styles.progresoLabel, {
            fontWeight: '700',
            color: progresoGlobal === 1 ? GOV.verde : GOV.azul,
          }]}>
            {Math.round(progresoGlobal * 100)}%
          </Text>
        </View>
        <ProgressBar
          progress={progresoGlobal}
          style={styles.progressBar}
          color={progresoGlobal === 1 ? GOV.verde : GOV.azul}
        />
      </View>

      <FlatList
        data={capitulos}
        keyExtractor={(item) => item.id}
        renderItem={({ item, index }) => (
          <CapituloCard
            capitulo={item}
            index={index}
            progress={getCapProgress(item.id)}
            sesionServerId={sesionServerId}
            instrumentoId={instrumentoId}
            hogarId={hogarId}
            modoIA={modoIA === true}
          />
        )}
        contentContainerStyle={styles.lista}
        ListFooterComponent={
          sesionServerId ? (
            <View style={styles.footerFinalizar}>
              <GovButton
                label="Finalizar sesión"
                variant="secondary"
                icon="check-circle-outline"
                onPress={() => setModalFinalizar(true)}
              />
            </View>
          ) : null
        }
      />

      {/* Modal de finalización */}
      <Modal
        visible={modalFinalizar}
        transparent
        animationType="slide"
        onRequestClose={() => setModalFinalizar(false)}
      >
        <KeyboardAvoidingView
          style={styles.modalOverlay}
          behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        >
          <View style={styles.modalCard}>
            <Text style={styles.modalTitulo}>Finalizar sesión</Text>
            <Text style={styles.modalCuerpo}>
              Al finalizar, la sesión quedará en estado{' '}
              <Text style={styles.modalDestacado}>COMPLETADA</Text> y no podrá
              modificarse.{'\n\n'}
              Progreso actual: <Text style={styles.modalDestacado}>{Math.round(progresoGlobal * 100)}%</Text>
              {' '}({capsCompletados}/{capitulos.length} capítulos).
            </Text>

            <Text style={styles.modalLabel}>Observaciones (opcional)</Text>
            <TextInput
              value={observaciones}
              onChangeText={setObservaciones}
              placeholder="Notas adicionales sobre la entrevista…"
              multiline
              numberOfLines={3}
              style={styles.modalTextArea}
              editable={!finalizando}
            />

            <View style={styles.modalBotones}>
              <GovButton
                label="Cancelar"
                variant="secondary"
                fullWidth={false}
                onPress={() => setModalFinalizar(false)}
                disabled={finalizando}
              />
              <GovButton
                label="Finalizar"
                variant="primary"
                icon="check"
                fullWidth={false}
                onPress={handleFinalizar}
                loading={finalizando}
                disabled={finalizando}
              />
            </View>
          </View>
        </KeyboardAvoidingView>
      </Modal>
    </View>
  );
}

// ─── Estilos ──────────────────────────────────────────────────────────────────

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
  centrado: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: SPACING.xl },
  cargandoTxt: { ...FONT.small, color: GOV.textoS, marginTop: SPACING.sm },

  selectorModo: {
    backgroundColor: GOV.superficie,
    padding: SPACING.md,
    borderBottomWidth: 1,
    borderBottomColor: GOV.borde,
  },
  selectorTitulo: { ...FONT.h3, color: GOV.azulOscuro, marginBottom: SPACING.sm },
  selectorBotones: { flexDirection: 'row', gap: SPACING.sm },
  modoCard: {
    flex: 1,
    backgroundColor: GOV.fondoApp,
    borderRadius: RADIUS.md,
    padding: SPACING.md,
    alignItems: 'center',
    borderWidth: 1.5,
    borderColor: GOV.borde,
    gap: SPACING.xs,
    ...SHADOW.card,
  },
  modoCardIA:           { borderColor: GOV.azul + '66', backgroundColor: GOV.azulTenue },
  modoCardIADesactivado:{ opacity: 0.6 },
  modoCardPressed:      { opacity: 0.85, transform: [{ scale: 0.98 }] },
  modoCardTitulo:       { ...FONT.h3, color: GOV.azulOscuro, textAlign: 'center' },
  modoCardDesc:         { ...FONT.caption, color: GOV.textoS, textAlign: 'center' },

  modoActivoBanner:  { flexDirection: 'row', alignItems: 'center', paddingHorizontal: SPACING.md, paddingVertical: 6, gap: SPACING.xs },
  modoActivoIA:      { backgroundColor: GOV.azulTenue },
  modoActivoManual:  { backgroundColor: GOV.fondoApp, borderBottomWidth: 1, borderBottomColor: GOV.borde },
  modoActivoTxt:     { ...FONT.caption, flex: 1 },
  cambiarModo:       { paddingHorizontal: SPACING.sm },
  cambiarModoTxt:    { ...FONT.caption, color: GOV.azul, fontWeight: '600' },

  progresoWrap: {
    backgroundColor: GOV.superficie,
    paddingHorizontal: SPACING.md,
    paddingVertical: SPACING.sm,
    borderBottomWidth: 1,
    borderBottomColor: GOV.borde,
  },
  progresoRow:   { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 6 },
  progresoLabel: { ...FONT.caption, color: GOV.textoS },
  progressBar:   { height: 6, borderRadius: 3, backgroundColor: GOV.borde },

  lista: { padding: SPACING.md, paddingBottom: SPACING.sm },
  footerFinalizar: { paddingVertical: SPACING.md, paddingBottom: SPACING.xl },

  card: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: GOV.superficie,
    borderRadius: RADIUS.md,
    padding: SPACING.md,
    marginBottom: SPACING.sm,
    ...SHADOW.card,
    borderLeftWidth: 3,
    borderLeftColor: 'transparent',
  },
  cardCompletado: { borderLeftColor: GOV.verde },
  cardPressed:    { opacity: 0.9, transform: [{ scale: 0.99 }] },

  numCircle: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: GOV.azulTenue,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: SPACING.md,
    borderWidth: 1.5,
    borderColor: GOV.borde,
  },
  numTxt: { fontSize: 13, fontWeight: '800', color: GOV.azul },

  cardTexto: { flex: 1 },
  capNombre:   { ...FONT.body, fontWeight: '600', color: GOV.textoP, marginBottom: 2 },
  capNombreOk: { color: GOV.verde },
  capCodigo:   { ...FONT.caption, color: GOV.textoT, fontFamily: 'monospace', marginBottom: 4 },

  capProgresoWrap: { flexDirection: 'row', alignItems: 'center', gap: SPACING.xs, marginTop: 2 },
  capProgressBar:  { flex: 1, height: 4, borderRadius: 2 },
  capProgresoPct:  { fontSize: 10, fontWeight: '700', minWidth: 28, textAlign: 'right' },

  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.45)', justifyContent: 'flex-end' },
  modalCard: {
    backgroundColor: GOV.superficie,
    borderTopLeftRadius: RADIUS.lg,
    borderTopRightRadius: RADIUS.lg,
    padding: SPACING.lg,
    paddingBottom: SPACING.xl,
    gap: SPACING.sm,
  },
  modalTitulo:    { ...FONT.h2, color: GOV.azulOscuro },
  modalCuerpo:    { ...FONT.body, color: GOV.textoS, lineHeight: 22 },
  modalDestacado: { fontWeight: '700', color: GOV.azulOscuro },
  modalLabel:     { ...FONT.label, color: GOV.textoT, marginTop: SPACING.xs },
  modalTextArea:  { backgroundColor: GOV.fondoApp, minHeight: 80, textAlignVertical: 'top', fontSize: 14 },
  modalBotones:   { flexDirection: 'row', justifyContent: 'flex-end', gap: SPACING.sm, marginTop: SPACING.sm },
});
