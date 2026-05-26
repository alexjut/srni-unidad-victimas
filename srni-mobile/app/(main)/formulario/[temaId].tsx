// Motor de captura offline de un capítulo — Sprint 8: carga previa, validación, bulk sync, progreso.
import { useEffect, useState, useMemo, useCallback } from 'react';
import { View, FlatList, StyleSheet, Alert } from 'react-native';
import {
  Text, TextInput, RadioButton, Checkbox,
  ActivityIndicator, Chip, IconButton, ProgressBar,
} from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useLocalSearchParams, router } from 'expo-router';
import * as instrumentos from '../../../src/services/instrumentos';
import * as borradoresDao from '../../../src/db/borradoresDao';
import * as colaDao from '../../../src/db/colaDao';
import { calcularVisibles } from '../../../src/services/skipLogic';
import { useSyncStore } from '../../../src/stores/syncStore';
import { useIAStore } from '../../../src/stores/iaStore';
import { useCaracterizacionStore } from '../../../src/stores/caracterizacionStore';
import { encuestasApi } from '../../../src/api/encuestas';
import { AudioRecorder } from '../../../src/components/AudioRecorder';
import { SugerenciaIA } from '../../../src/components/SugerenciaIA';
import { GovHeader } from '../../../src/components/GovHeader';
import { GovButton } from '../../../src/components/GovButton';
import { SelectorMunicipio } from '../../../src/components/SelectorMunicipio';
import { GOV, SPACING, RADIUS, SHADOW, FONT } from '../../../src/theme/govTheme';
import type { PreguntaRow, OpcionRow, ReglaSkipLogicRow } from '../../../src/db/instrumentoDao';

// ─────────────────────────────────────────────────────────────────────────────

export default function CapituloScreen() {
  const {
    temaId,
    borradorId: borradorIdParam,
    hogarId,
    sesionServerId,
    instrumentoId,
  } = useLocalSearchParams<{
    temaId: string;
    borradorId?: string;
    hogarId?: string;
    sesionServerId?: string;
    instrumentoId?: string;
  }>();

  const { estaOnline, refrescarContadores } = useSyncStore();
  const rutaEntrevista = useCaracterizacionStore((s) => s.rutaEntrevista);
  const {
    activo: iaActivo,
    estado: estadoIA,
    sugerencia,
    preguntaActivaId,
    iniciarGrabacion,
    enviarTexto,
    aceptarSugerencia,
    rechazarSugerencia,
    resetear: resetearIA,
  } = useIAStore();

  const [preguntas, setPreguntas] = useState<PreguntaRow[]>([]);
  const [opciones, setOpciones] = useState<Record<string, OpcionRow[]>>({});
  const [reglas, setReglas] = useState<ReglaSkipLogicRow[]>([]);
  const [respuestas, setRespuestasState] = useState<Record<string, string>>({});
  const [borradorId, setBorradorId] = useState<string | null>(borradorIdParam ?? null);
  const [capituloNombre, setCapituloNombre] = useState('');
  const [cargando, setCargando] = useState(true);
  const [sincronizando, setSincronizando] = useState(false);

  // ── Cargar datos del capítulo + borradores previos ──────────────────────────
  useEffect(() => {
    if (!temaId) return;

    (async () => {
      // Sprint 18 F1B: TODO viene de memoria (bundle), no SQLite.
      const caps = instrumentos.getCapitulos();
      const cap = caps.find((c) => c.id === temaId);
      setCapituloNombre(cap?.nombre ?? '');

      const pgs = instrumentos.getPreguntas(temaId);
      setPreguntas(pgs);
      if (pgs.length > 0) {
        setOpciones(instrumentos.getOpcionesBatch(pgs.map((p) => p.id)));
      }

      setReglas(instrumentos.getReglasPorCapitulo(temaId));

      // ── Resolver borrador ─────────────────────────────────────────────────
      const meta = instrumentos.getMeta();
      const instrId = instrumentoId ?? meta?.instrumento_id ?? '';

      if (borradorIdParam) {
        // Ya tenemos un borrador local — cargar sus respuestas
        setRespuestasState(await borradoresDao.getRespuestaMap(borradorIdParam));
        setBorradorId(borradorIdParam);

      } else if (sesionServerId) {
        // Buscar si ya existe un borrador vinculado a esta sesión
        const existente = await borradoresDao.findBySesionId(sesionServerId);

        if (existente) {
          setBorradorId(existente.id);
          setRespuestasState(await borradoresDao.getRespuestaMap(existente.id));
        } else {
          // Crear nuevo borrador y vincularlo
          const nuevo = await borradoresDao.crearBorrador(instrId, hogarId);
          await borradoresDao.vincularSesionServidor(nuevo.id, sesionServerId);
          setBorradorId(nuevo.id);

          // Si hay conexión, descargar respuestas previas del servidor
          if (estaOnline) {
            try {
              const { data: previas } = await encuestasApi.getRespuestas(sesionServerId);
              for (const r of previas) {
                if (r.valor) await borradoresDao.upsertRespuesta(nuevo.id, r.pregunta, r.valor);
              }
              setRespuestasState(await borradoresDao.getRespuestaMap(nuevo.id));
            } catch { /* sin red — empieza en blanco */ }
          }
        }

      } else {
        // Sesión sin id de servidor — borrador completamente nuevo
        const nuevo = await borradoresDao.crearBorrador(instrId, hogarId);
        setBorradorId(nuevo.id);
        if (hogarId && instrId) {
          await colaDao.encolar('CREAR_SESION', nuevo.id, {
            borrador_id: nuevo.id,
            hogar: hogarId,
            instrumento: instrId,
            ruta_entrevista: rutaEntrevista,
          });
          await refrescarContadores();
        }
      }

      setCargando(false);
    })().catch(() => setCargando(false));
  }, [temaId]);

  // ── Skip logic ──────────────────────────────────────────────────────────────
  const respuestasParaSkip = useMemo<Record<string, string>>(() => {
    const m: Record<string, string> = {};
    for (const p of preguntas) m[p.codigo_externo] = respuestas[p.id] ?? '';
    return m;
  }, [preguntas, respuestas]);

  const { visibles } = useMemo(
    () => calcularVisibles(preguntas, reglas, respuestasParaSkip),
    [preguntas, reglas, respuestasParaSkip],
  );

  const preguntasVisibles = useMemo(
    () => preguntas.filter((p) => visibles.has(p.codigo_externo)),
    [preguntas, visibles],
  );

  // ── Progreso del capítulo ───────────────────────────────────────────────────
  const { totalOblig, respondidoOblig } = useMemo(() => {
    const visiblesOblig = preguntasVisibles.filter((p) => p.obligatoria === 1);
    return {
      totalOblig: visiblesOblig.length,
      respondidoOblig: visiblesOblig.filter((p) => !!respuestas[p.id]?.trim()).length,
    };
  }, [preguntasVisibles, respuestas]);

  const progresoCap = totalOblig > 0 ? respondidoOblig / totalOblig : 0;

  // ── Guardar respuesta en SQLite + encolar ───────────────────────────────────
  const setRespuesta = useCallback(async (preguntaId: string, valor: string) => {
    setRespuestasState((prev) => ({ ...prev, [preguntaId]: valor }));

    const bid = borradorId ?? borradorIdParam;
    if (!bid) return;

    borradoresDao.upsertRespuesta(bid, preguntaId, valor).catch(() => {});

    const borrador = await borradoresDao.getBorrador(bid);
    if (borrador) {
      await colaDao.encolar('RESPONDER_PREGUNTA', bid, {
        borrador_id: bid,
        sesion_id: borrador.sesion_id ?? null,
        pregunta_id: preguntaId,
        valor,
      });
      await refrescarContadores();
    }
  }, [borradorId, borradorIdParam]);

  // ── Asistente IA ────────────────────────────────────────────────────────────
  const handleTextoTranscrito = useCallback(async (preguntaId: string, texto: string) => {
    const bid = borradorId ?? borradorIdParam;
    if (!bid) return;
    iniciarGrabacion(preguntaId);
    const borrador = await borradoresDao.getBorrador(bid);
    await enviarTexto(borrador?.sesion_id ?? '', preguntaId, texto);
  }, [borradorId, borradorIdParam, iniciarGrabacion, enviarTexto]);

  const handleAceptarSugerencia = useCallback((preguntaId: string) => {
    const resultado = aceptarSugerencia();
    if (resultado?.sugerencia) setRespuesta(preguntaId, resultado.sugerencia);
  }, [aceptarSugerencia, setRespuesta]);

  useEffect(() => { return () => { resetearIA(); }; }, []);

  // ── Guardar capítulo: bulk sync (online) o encolar (offline) → volver ─────────
  async function guardarYVolver() {
    const bid = borradorId ?? borradorIdParam;

    if (bid && sesionServerId) {
      setSincronizando(true);
      try {
        const mapa = await borradoresDao.getRespuestaMap(bid);
        const arr = Object.entries(mapa)
          .filter(([, v]) => v.trim() !== '')
          .map(([pregunta_id, valor]) => ({ pregunta_id, valor }));

        if (arr.length > 0) {
          if (estaOnline) {
            await encuestasApi.responderBulk(sesionServerId, arr);
          } else {
            // Sin red: encolar para sincronizar cuando vuelva la conexión
            await colaDao.encolar('RESPONDER_BULK', bid, {
              sesion_id: sesionServerId,
              borrador_id: bid,
              respuestas: arr,
            });
          }
        }
      } catch { /* silencioso — la cola lo reintentará */ }
      finally { setSincronizando(false); }
    }

    await refrescarContadores();
    router.back();
  }

  async function finalizarCapitulo() {
    // Preguntas obligatorias visibles sin respuesta
    const faltantes = preguntasVisibles.filter(
      (p) => p.obligatoria === 1 && !respuestas[p.id]?.trim(),
    );

    if (faltantes.length > 0) {
      Alert.alert(
        'Preguntas requeridas',
        `Hay ${faltantes.length} pregunta${faltantes.length > 1 ? 's' : ''} obligatoria${faltantes.length > 1 ? 's' : ''} sin responder.\n\n¿Desea guardar de todas formas?`,
        [
          { text: 'Revisar', style: 'cancel' },
          { text: 'Guardar igual', onPress: guardarYVolver },
        ],
      );
      return;
    }
    await guardarYVolver();
  }

  // ── Render ──────────────────────────────────────────────────────────────────
  if (cargando) {
    return (
      <View style={styles.root}>
        <GovHeader title="Cargando…" onBack={() => router.back()} />
        <View style={styles.centrado}>
          <ActivityIndicator size="large" color={GOV.azul} />
        </View>
      </View>
    );
  }

  const totalVisible = preguntasVisibles.length;
  const migaContexto = hogarId
    ? `Hogar ${hogarId.slice(0, 8)}…  ›  ${capituloNombre || 'Capítulo'}`
    : capituloNombre || 'Capítulo';

  return (
    <View style={styles.root}>
      <GovHeader
        title={capituloNombre || 'Capítulo'}
        subtitle={`${totalVisible} pregunta${totalVisible !== 1 ? 's' : ''}`}
        onBack={() => router.back()}
        right={
          <View style={styles.headerActions}>
            {!estaOnline && (
              <Chip compact icon="wifi-off" style={styles.offlineChip} textStyle={styles.offlineTxt}>
                Offline
              </Chip>
            )}
            {iaActivo ? (
              <Chip
                compact
                icon="microphone"
                style={styles.iaActivoChip}
                textStyle={styles.iaActivoTxt}
                onClose={() => useIAStore.getState().desactivar()}
              >
                IA
              </Chip>
            ) : (
              <IconButton
                icon="robot"
                size={20}
                iconColor="#FFFFFF"
                onPress={() => router.push({
                  pathname: '/(main)/formulario/consentimiento-ia',
                  params: { sesionEncuestaId: borradorId ?? borradorIdParam ?? '' },
                })}
              />
            )}
          </View>
        }
      />

      {/* Miga de pan */}
      <View style={styles.miga}>
        <Text style={styles.migaTxt}>Formulario  ›  {migaContexto}</Text>
      </View>

      {/* Barra de progreso del capítulo */}
      <View style={styles.progresoWrap}>
        <View style={styles.progresoRow}>
          <Text style={styles.progresoLabel}>
            {respondidoOblig} / {totalOblig} obligatoria{totalOblig !== 1 ? 's' : ''} respondida{totalOblig !== 1 ? 's' : ''}
          </Text>
          <Text style={[styles.progresoLabel, { color: progresoCap === 1 ? GOV.verde : GOV.azul, fontWeight: '700' }]}>
            {Math.round(progresoCap * 100)}%
          </Text>
        </View>
        <ProgressBar
          progress={progresoCap}
          style={styles.progressBar}
          color={progresoCap === 1 ? GOV.verde : GOV.azul}
        />
      </View>

      <FlatList
        data={preguntasVisibles}
        keyExtractor={(item) => item.id}
        renderItem={({ item, index }) => (
          <PreguntaItem
            pregunta={item}
            index={index}
            total={totalVisible}
            opciones={opciones[item.id] ?? []}
            valor={respuestas[item.id] ?? ''}
            onChange={(v) => setRespuesta(item.id, v)}
            iaActivo={iaActivo}
            onTextoIA={(texto) => handleTextoTranscrito(item.id, texto)}
            sugerenciaActiva={
              sugerencia && preguntaActivaId === item.id && estadoIA === 'sugerida'
                ? sugerencia
                : null
            }
            onAceptarIA={() => handleAceptarSugerencia(item.id)}
            onRechazarIA={rechazarSugerencia}
          />
        )}
        contentContainerStyle={styles.lista}
        ListEmptyComponent={
          <Text style={styles.sinPreguntas}>No hay preguntas en este capítulo.</Text>
        }
      />

      <View style={styles.footerBar}>
        <GovButton
          label={sincronizando ? 'Sincronizando…' : 'Guardar y volver'}
          icon={sincronizando ? undefined : 'check'}
          loading={sincronizando}
          disabled={sincronizando}
          onPress={finalizarCapitulo}
        />
      </View>
    </View>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Componente de pregunta individual
// ─────────────────────────────────────────────────────────────────────────────

// Sprint 17: alineado con el backend, que espera "true"/"false" como string.
// Pero al leer aceptamos también formatos viejos ('1'/'0') para retro-compat.
const BOOLEAN_OPCIONES = [
  { valor: 'true',  etiqueta: 'Sí' },
  { valor: 'false', etiqueta: 'No' },
];

function leerBooleanGuardado(valor: string): string {
  // Retro-compat: '1' → 'true', '0' → 'false'
  if (valor === '1' || valor === 'true')  return 'true';
  if (valor === '0' || valor === 'false') return 'false';
  return '';
}

/** Parsea LISTA_MULTIPLE: acepta JSON nuevo o CSV viejo. */
function parseMultiValor(valor: string): string[] {
  if (!valor) return [];
  const trimmed = valor.trim();
  if (trimmed.startsWith('[')) {
    try {
      const parsed = JSON.parse(trimmed);
      return Array.isArray(parsed) ? parsed.map(String) : [];
    } catch {
      return [];
    }
  }
  // CSV viejo (retro-compat)
  return trimmed.split(',').map(s => s.trim()).filter(Boolean);
}

function PreguntaItem({
  pregunta,
  index,
  total,
  opciones,
  valor,
  onChange,
  iaActivo,
  onTextoIA,
  sugerenciaActiva,
  onAceptarIA,
  onRechazarIA,
}: {
  pregunta: PreguntaRow;
  index: number;
  total: number;
  opciones: OpcionRow[];
  valor: string;
  onChange: (v: string) => void;
  iaActivo?: boolean;
  onTextoIA?: (texto: string) => void;
  sugerenciaActiva?: import('../../../src/api/ia').MapearAudioResponse | null;
  onAceptarIA?: () => void;
  onRechazarIA?: () => void;
}) {
  const esTexto    = pregunta.tipo === 'TEXTO' || pregunta.tipo === 'TEXTO_LARGO';
  const esNumerico = pregunta.tipo === 'NUMERICO';
  const esFecha    = pregunta.tipo === 'FECHA';
  // Sprint 20: COMBO_DINAMICO ya no se trata como LISTA — se renderiza con
  // SelectorMunicipio (consume /api/parametricas/municipios/todos/).
  const esRadio    = pregunta.tipo === 'RADIO' || pregunta.tipo === 'LISTA';
  const esCombo    = pregunta.tipo === 'COMBO_DINAMICO';
  const esMultiple = pregunta.tipo === 'LISTA_MULTIPLE';
  const esBoolean  = pregunta.tipo === 'BOOLEAN';

  const tieneRespuesta = !!valor?.trim();
  const esObligatoria  = pregunta.obligatoria === 1;

  return (
    <View style={[
      styles.preguntaCard,
      esObligatoria && !tieneRespuesta && styles.preguntaCardPendiente,
      tieneRespuesta && styles.preguntaCardRespondida,
    ]}>
      <View style={styles.preguntaHeader}>
        <View style={[styles.numBadge, tieneRespuesta && styles.numBadgeOk]}>
          {tieneRespuesta
            ? <MaterialCommunityIcons name="check" size={13} color="#FFFFFF" />
            : <Text style={styles.numBadgeTxt}>{index + 1}</Text>
          }
        </View>
        <Text style={styles.numTotal}>de {total}</Text>
        {esObligatoria && (
          <View style={[styles.requeridoChip, tieneRespuesta && styles.requeridoChipOk]}>
            <Text style={[styles.requeridoTxt, tieneRespuesta && styles.requeridoTxtOk]}>
              {tieneRespuesta ? 'Respondida' : 'Requerida'}
            </Text>
          </View>
        )}
        {pregunta.no_pregunta ? (
          <Text style={styles.codigoTxt}>{pregunta.no_pregunta}</Text>
        ) : null}
      </View>

      <Text style={styles.textoPregunta}>{pregunta.texto}</Text>

      {pregunta.descripcion_ayuda ? (
        <Text style={styles.ayuda}>{pregunta.descripcion_ayuda}</Text>
      ) : null}

      {/* Asistente de voz */}
      {iaActivo && onTextoIA && (
        <AudioRecorder
          preguntaId={pregunta.id}
          onTextoListo={onTextoIA}
          disabled={!!sugerenciaActiva}
        />
      )}
      {sugerenciaActiva && onAceptarIA && onRechazarIA && (
        <SugerenciaIA
          sugerencia={sugerenciaActiva}
          onAceptar={() => onAceptarIA()}
          onRechazar={onRechazarIA}
        />
      )}

      {/* Controles por tipo */}
      {(esTexto || esNumerico) && (
        <TextInput
          value={valor}
          onChangeText={onChange}
          keyboardType={esNumerico ? 'numeric' : 'default'}
          multiline={pregunta.tipo === 'TEXTO_LARGO'}
          numberOfLines={pregunta.tipo === 'TEXTO_LARGO' ? 3 : 1}
          style={styles.inputTexto}
          dense
        />
      )}

      {esFecha && (
        <TextInput
          value={valor}
          onChangeText={onChange}
          placeholder="AAAA-MM-DD"
          keyboardType="numeric"
          style={styles.inputTexto}
          dense
        />
      )}

      {esBoolean && (
        <RadioButton.Group value={leerBooleanGuardado(valor)} onValueChange={onChange}>
          {BOOLEAN_OPCIONES.map((o) => (
            <RadioButton.Item key={o.valor} label={o.etiqueta} value={o.valor} />
          ))}
        </RadioButton.Group>
      )}

      {esRadio && (
        opciones.length === 0 ? (
          <Text style={styles.sinOpciones}>
            ⚠ Esta pregunta no tiene opciones cargadas — contacte al administrador.
          </Text>
        ) : (
          <RadioButton.Group value={valor} onValueChange={onChange}>
            {opciones.map((o) => (
              <RadioButton.Item key={o.id} label={o.etiqueta} value={o.valor} />
            ))}
          </RadioButton.Group>
        )
      )}

      {/* Sprint 20: COMBO_DINAMICO = municipio (Z2/Z5A/Z15/A23A/HV3/Lud_encuesta).
          Consume /api/parametricas/municipios/todos/ con caché en memoria. */}
      {esCombo && (
        <SelectorMunicipio
          valor={valor}
          onChange={onChange}
          label={pregunta.no_pregunta ? `${pregunta.no_pregunta} · Municipio` : 'Municipio'}
        />
      )}

      {esMultiple && (
        opciones.length === 0 ? (
          <Text style={styles.sinOpciones}>
            ⚠ Esta pregunta no tiene opciones cargadas — contacte al administrador.
          </Text>
        ) : (() => {
          const seleccionados = parseMultiValor(valor);
          return (
            <View>
              <Text style={styles.multiHint}>
                Selecciona todas las que apliquen
                {seleccionados.length > 0 && ` (${seleccionados.length} seleccionada${seleccionados.length !== 1 ? 's' : ''})`}
              </Text>
              {opciones.map((o) => {
                const marcado = seleccionados.includes(o.valor);
                return (
                  <Checkbox.Item
                    key={o.id}
                    label={o.etiqueta}
                    status={marcado ? 'checked' : 'unchecked'}
                    onPress={() => {
                      const sel = [...seleccionados];
                      const idx = sel.indexOf(o.valor);
                      if (idx >= 0) sel.splice(idx, 1);
                      else sel.push(o.valor);
                      // Sprint 17: guardar como JSON (alineado con backend)
                      onChange(sel.length > 0 ? JSON.stringify(sel) : '');
                    }}
                  />
                );
              })}
            </View>
          );
        })()
      )}
    </View>
  );
}

// ─── Estilos ──────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: GOV.fondoApp },
  centrado: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  headerActions: { flexDirection: 'row', alignItems: 'center', gap: 2 },
  offlineChip: { backgroundColor: GOV.naranjaTenue },
  offlineTxt:  { color: GOV.naranja, fontSize: 10 },
  iaActivoChip: { backgroundColor: GOV.azulTenue },
  iaActivoTxt:  { color: GOV.azul, fontSize: 10 },
  miga: {
    backgroundColor: GOV.azulTenue,
    paddingHorizontal: SPACING.md,
    paddingVertical: 6,
    borderBottomWidth: 1,
    borderBottomColor: GOV.borde,
  },
  migaTxt: { ...FONT.caption, color: GOV.azulOscuro },

  // Progreso del capítulo
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
  progresoLabel: { ...FONT.caption, color: GOV.textoS },
  progressBar: { height: 6, borderRadius: 3, backgroundColor: GOV.borde },

  lista: { padding: SPACING.md, paddingBottom: 96 },
  sinPreguntas: { textAlign: 'center', color: GOV.textoT, marginTop: SPACING.xl, ...FONT.body },

  // Tarjeta de pregunta
  preguntaCard: {
    backgroundColor: GOV.superficie,
    borderRadius: RADIUS.md,
    padding: SPACING.md,
    marginBottom: SPACING.sm,
    borderLeftWidth: 4,
    borderLeftColor: GOV.borde,
    ...SHADOW.card,
  },
  preguntaCardPendiente: {
    borderLeftColor: GOV.naranja,
  },
  preguntaCardRespondida: {
    borderLeftColor: GOV.verde,
  },
  preguntaHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: SPACING.sm,
    gap: SPACING.xs,
  },
  numBadge: {
    width: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: GOV.azul,
    justifyContent: 'center',
    alignItems: 'center',
  },
  numBadgeOk: { backgroundColor: GOV.verde },
  numBadgeTxt: { fontSize: 11, fontWeight: '800', color: '#FFFFFF' },
  numTotal: { ...FONT.caption, color: GOV.textoT },
  requeridoChip: {
    marginLeft: 'auto' as any,
    backgroundColor: GOV.rojoTenue,
    borderRadius: RADIUS.pill,
    paddingHorizontal: 8,
    paddingVertical: 2,
  },
  requeridoChipOk: { backgroundColor: GOV.verdeTenue },
  requeridoTxt:    { fontSize: 10, fontWeight: '600', color: GOV.rojo },
  requeridoTxtOk:  { color: GOV.verde },
  codigoTxt: { ...FONT.caption, color: GOV.textoT, fontFamily: 'monospace' },
  textoPregunta: { ...FONT.body, fontWeight: '600', color: GOV.textoP, marginBottom: SPACING.sm },
  ayuda: { ...FONT.small, color: GOV.textoS, marginBottom: SPACING.sm },
  inputTexto: { backgroundColor: GOV.fondoApp },
  multiHint: {
    ...FONT.caption,
    color: GOV.azul,
    fontWeight: '600',
    marginBottom: SPACING.xs,
    fontStyle: 'italic',
  },
  sinOpciones: {
    ...FONT.small,
    color: GOV.naranja,
    fontStyle: 'italic',
    padding: SPACING.sm,
    backgroundColor: GOV.naranjaTenue,
    borderRadius: RADIUS.sm,
  },
  footerBar: {
    backgroundColor: GOV.superficie,
    padding: SPACING.md,
    borderTopWidth: 1,
    borderTopColor: GOV.borde,
  },
});
