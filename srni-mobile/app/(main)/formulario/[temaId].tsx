// Motor de captura offline de un capítulo del formulario — Sprint 7, Diccionario V8.
import { useEffect, useState, useMemo, useCallback } from 'react';
import { View, FlatList, StyleSheet } from 'react-native';
import {
  Text, TextInput, RadioButton, Checkbox,
  ActivityIndicator, Chip, IconButton,
} from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useLocalSearchParams, router } from 'expo-router';
import * as instrumentoDao from '../../../src/db/instrumentoDao';
import * as borradoresDao from '../../../src/db/borradoresDao';
import * as colaDao from '../../../src/db/colaDao';
import { calcularVisibles } from '../../../src/services/skipLogic';
import { useSyncStore } from '../../../src/stores/syncStore';
import { useIAStore } from '../../../src/stores/iaStore';
import { AudioRecorder } from '../../../src/components/AudioRecorder';
import { SugerenciaIA } from '../../../src/components/SugerenciaIA';
import { GovHeader } from '../../../src/components/GovHeader';
import { GovButton } from '../../../src/components/GovButton';
import { GOV, SPACING, RADIUS, SHADOW, FONT } from '../../../src/theme/govTheme';
import type { PreguntaRow, OpcionRow, ReglaSkipLogicRow } from '../../../src/db/instrumentoDao';

// ─────────────────────────────────────────────────────────────────────────────

export default function CapituloScreen() {
  const {
    temaId,          // UUID del Capitulo
    borradorId: borradorIdParam,
    hogarId,
    sesionServerId,  // UUID de sesión en servidor (viene de [sesionId].tsx)
    instrumentoId,   // UUID de InstrumentoVersion (para reglas skip logic)
  } = useLocalSearchParams<{
    temaId: string;
    borradorId?: string;
    hogarId?: string;
    sesionServerId?: string;
    instrumentoId?: string;
  }>();

  const { estaOnline, refrescarContadores } = useSyncStore();
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
  // respuestas keyed by pregunta UUID
  const [respuestas, setRespuestasState] = useState<Record<string, string>>({});
  const [borradorId, setBorradorId] = useState<string | null>(borradorIdParam ?? null);
  const [capituloNombre, setCapituloNombre] = useState('');
  const [cargando, setCargando] = useState(true);

  // ── Cargar datos del capítulo desde SQLite ──────────────────────────────────
  useEffect(() => {
    if (!temaId) return;

    (async () => {
      // Nombre del capítulo
      const caps = await instrumentoDao.getCapitulos();
      const cap = caps.find((c) => c.id === temaId);
      setCapituloNombre(cap?.nombre ?? '');

      // Preguntas
      const pgs = await instrumentoDao.getPreguntas(temaId);
      setPreguntas(pgs);

      if (pgs.length > 0) {
        const ids = pgs.map((p) => p.id);
        const opts = await instrumentoDao.getOpcionesBatch(ids);
        setOpciones(opts);
      }

      // Reglas de skip logic del capítulo
      if (instrumentoId) {
        const rs = await instrumentoDao.getReglasPorCapitulo(temaId, instrumentoId);
        setReglas(rs);
      }

      // Manejar borrador
      if (borradorIdParam) {
        // Recargar respuestas existentes
        const mapaRaw = await borradoresDao.getRespuestaMap(borradorIdParam);
        setRespuestasState(mapaRaw);
      } else {
        // Crear nuevo borrador
        const meta = await instrumentoDao.getMeta();
        const instrId = instrumentoId ?? meta?.instrumento_id ?? '';
        const borrador = await borradoresDao.crearBorrador(instrId, hogarId);
        setBorradorId(borrador.id);

        if (sesionServerId) {
          await borradoresDao.vincularSesionServidor(borrador.id, sesionServerId);
        } else if (hogarId && instrId) {
          await colaDao.encolar('CREAR_SESION', borrador.id, {
            borrador_id: borrador.id,
            hogar: hogarId,
            instrumento: instrId,
          });
          await refrescarContadores();
        }
      }

      setCargando(false);
    })().catch(() => setCargando(false));
  }, [temaId]);

  // ── Skip logic — derivar mapa codigo_externo→valor para evaluación ──────────
  const respuestasParaSkip = useMemo<Record<string, string>>(() => {
    const m: Record<string, string> = {};
    for (const p of preguntas) {
      m[p.codigo_externo] = respuestas[p.id] ?? '';
    }
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

    if (estaOnline) {
      useSyncStore.getState().triggerSync();
    }
  }, [borradorId, borradorIdParam, estaOnline]);

  // ── Asistente IA ────────────────────────────────────────────────────────────
  const handleTextoTranscrito = useCallback(async (preguntaId: string, texto: string) => {
    const bid = borradorId ?? borradorIdParam;
    if (!bid) return;
    iniciarGrabacion(preguntaId);
    const borrador = await borradoresDao.getBorrador(bid);
    const sesionId = borrador?.sesion_id ?? '';
    await enviarTexto(sesionId, preguntaId, texto);
  }, [borradorId, borradorIdParam, iniciarGrabacion, enviarTexto]);

  const handleAceptarSugerencia = useCallback((preguntaId: string) => {
    const resultado = aceptarSugerencia();
    if (resultado?.sugerencia) {
      setRespuesta(preguntaId, resultado.sugerencia);
    }
  }, [aceptarSugerencia, setRespuesta]);

  useEffect(() => { return () => { resetearIA(); }; }, []);

  // ── Guardar y volver (sin finalizar sesión) ─────────────────────────────────
  async function finalizarCapitulo() {
    await refrescarContadores();
    if (estaOnline) useSyncStore.getState().triggerSync();
    router.back();
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

      <View style={styles.miga}>
        <Text style={styles.migaTxt}>Formulario  ›  {migaContexto}</Text>
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
        <GovButton label="Guardar y volver" icon="check" onPress={finalizarCapitulo} />
      </View>
    </View>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Componente de pregunta individual — soporte tipos Diccionario V8
// ─────────────────────────────────────────────────────────────────────────────

const BOOLEAN_OPCIONES = [
  { valor: '1', etiqueta: 'Sí' },
  { valor: '0', etiqueta: 'No' },
];

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
  const esRadio    = pregunta.tipo === 'RADIO' || pregunta.tipo === 'LISTA' || pregunta.tipo === 'COMBO_DINAMICO';
  const esMultiple = pregunta.tipo === 'LISTA_MULTIPLE';
  const esBoolean  = pregunta.tipo === 'BOOLEAN';

  const opcionesBoolean = esBoolean ? BOOLEAN_OPCIONES : [];
  const opcionesRadio   = esRadio   ? opciones : [];

  return (
    <View style={styles.preguntaCard}>
      <View style={styles.preguntaHeader}>
        <View style={styles.numBadge}>
          <Text style={styles.numBadgeTxt}>{index + 1}</Text>
        </View>
        <Text style={styles.numTotal}>de {total}</Text>
        {!!pregunta.obligatoria && (
          <View style={styles.requeridoChip}>
            <Text style={styles.requeridoTxt}>Requerida</Text>
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
        <RadioButton.Group value={valor} onValueChange={onChange}>
          {opcionesBoolean.map((o) => (
            <RadioButton.Item key={o.valor} label={o.etiqueta} value={o.valor} />
          ))}
        </RadioButton.Group>
      )}

      {esRadio && (
        <RadioButton.Group value={valor} onValueChange={onChange}>
          {opcionesRadio.map((o) => (
            <RadioButton.Item key={o.id} label={o.etiqueta} value={o.valor} />
          ))}
        </RadioButton.Group>
      )}

      {esMultiple && (
        <View>
          {opciones.map((o) => {
            const seleccionados = valor ? valor.split(',').filter(Boolean) : [];
            return (
              <Checkbox.Item
                key={o.id}
                label={o.etiqueta}
                status={seleccionados.includes(o.valor) ? 'checked' : 'unchecked'}
                onPress={() => {
                  const sel = [...seleccionados];
                  const idx = sel.indexOf(o.valor);
                  if (idx >= 0) sel.splice(idx, 1);
                  else sel.push(o.valor);
                  onChange(sel.join(','));
                }}
              />
            );
          })}
        </View>
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
  lista: { padding: SPACING.md, paddingBottom: 96 },
  sinPreguntas: { textAlign: 'center', color: GOV.textoT, marginTop: SPACING.xl, ...FONT.body },
  preguntaCard: {
    backgroundColor: GOV.superficie,
    borderRadius: RADIUS.md,
    padding: SPACING.md,
    marginBottom: SPACING.sm,
    borderLeftWidth: 4,
    borderLeftColor: GOV.azul,
    ...SHADOW.card,
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
  numBadgeTxt: { fontSize: 11, fontWeight: '800', color: '#FFFFFF' },
  numTotal: { ...FONT.caption, color: GOV.textoT },
  requeridoChip: {
    marginLeft: 'auto' as any,
    backgroundColor: GOV.rojoTenue,
    borderRadius: RADIUS.pill,
    paddingHorizontal: 8,
    paddingVertical: 2,
  },
  requeridoTxt: { fontSize: 10, fontWeight: '600', color: GOV.rojo },
  codigoTxt: { ...FONT.caption, color: GOV.textoT, fontFamily: 'monospace' },
  textoPregunta: { ...FONT.body, fontWeight: '600', color: GOV.textoP, marginBottom: SPACING.sm },
  ayuda: { ...FONT.small, color: GOV.textoS, marginBottom: SPACING.sm },
  inputTexto: { backgroundColor: GOV.fondoApp },
  footerBar: {
    backgroundColor: GOV.superficie,
    padding: SPACING.md,
    borderTopWidth: 1,
    borderTopColor: GOV.borde,
  },
  miga: {
    backgroundColor: GOV.azulTenue,
    paddingHorizontal: SPACING.md,
    paddingVertical: 6,
    borderBottomWidth: 1,
    borderBottomColor: GOV.borde,
  },
  migaTxt: { ...FONT.caption, color: GOV.azulOscuro },
});
