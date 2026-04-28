// Motor de captura offline de un tema del formulario PAARI.
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
import { calcularVisibles, construirPreguntasConCondiciones } from '../../../src/services/skipLogic';
import { useSyncStore } from '../../../src/stores/syncStore';
import { useIAStore } from '../../../src/stores/iaStore';
import { AudioRecorder } from '../../../src/components/AudioRecorder';
import { SugerenciaIA } from '../../../src/components/SugerenciaIA';
import { GovHeader } from '../../../src/components/GovHeader';
import { GovButton } from '../../../src/components/GovButton';
import { GOV, SPACING, RADIUS, SHADOW, FONT } from '../../../src/theme/govTheme';
import type { PreguntaRow, OpcionRow, DerivadaRow } from '../../../src/db/instrumentoDao';

// ─────────────────────────────────────────────────────────────────────────────

export default function TemaScreen() {
  const { temaId, borradorId: borradorIdParam, hogarId, sesionServerId } = useLocalSearchParams<{
    temaId: string;
    borradorId?: string;
    hogarId?: string;
    sesionServerId?: string;   // UUID de sesión ya creada en servidor (viene desde [sesionId].tsx)
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
  const [opciones, setOpciones] = useState<Record<number, OpcionRow[]>>({});
  const [derivadas, setDerivadas] = useState<DerivadaRow[]>([]);
  const [respuestas, setRespuestas] = useState<Record<number, string>>({});
  const [borradorId, setBorradorId] = useState<string | null>(borradorIdParam ?? null);
  const [temaNombre, setTemaNombre] = useState('');
  const [cargando, setCargando] = useState(true);
  const [guardandoRespuesta, setGuardandoRespuesta] = useState(false);

  // ── Cargar datos del tema desde SQLite ──────────────────────────────────────
  useEffect(() => {
    if (!temaId) return;
    const tid = Number(temaId);

    (async () => {
      // Datos del tema
      const temas = await instrumentoDao.getTemas();
      const tema = temas.find((t) => t.id === tid);
      setTemaNombre(tema?.nombre ?? '');

      // Preguntas del tema
      const pgs = await instrumentoDao.getPreguntas(tid);
      setPreguntas(pgs);

      if (pgs.length > 0) {
        const ids = pgs.map((p) => p.id);
        const [opts, derivs] = await Promise.all([
          instrumentoDao.getOpcionesBatch(ids),
          instrumentoDao.getDerivadas(ids),
        ]);
        setOpciones(opts);
        setDerivadas(derivs);
      }

      // Cargar respuestas existentes del borrador (si lo hay)
      if (borradorIdParam) {
        const mapa = await borradoresDao.getRespuestaMap(borradorIdParam);
        setRespuestas(mapa);
      } else {
        // Crear nuevo borrador
        const instrMeta = await instrumentoDao.getMeta();
        const instrId = instrMeta?.instrumento_id ?? 1;
        const borrador = await borradoresDao.crearBorrador(instrId, hogarId);
        setBorradorId(borrador.id);

        if (sesionServerId) {
          // La sesión ya existe en el servidor (viene de [hogarId] → [sesionId] → formulario).
          // La vinculamos directamente para que las respuestas usen el sesion_id correcto.
          await borradoresDao.vincularSesionServidor(borrador.id, sesionServerId);
        } else if (hogarId) {
          // Sin sesión previa — crear en servidor vía cola de sincronización.
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

  // ── Skip logic — puro, sin I/O ──────────────────────────────────────────────
  const preguntasConCondiciones = useMemo(
    () => construirPreguntasConCondiciones(preguntas.map((p) => p.id), derivadas),
    [preguntas, derivadas],
  );

  const visibles = useMemo(
    () => calcularVisibles(preguntasConCondiciones, respuestas),
    [preguntasConCondiciones, respuestas],
  );

  const preguntasVisibles = useMemo(
    () => preguntas.filter((p) => visibles.has(p.id)),
    [preguntas, visibles],
  );

  // ── Guardar respuesta en SQLite + encolar ───────────────────────────────────
  const setRespuesta = useCallback(async (preguntaId: number, valor: string) => {
    setRespuestas((prev) => ({ ...prev, [preguntaId]: valor }));

    if (!borradorId) return;

    borradoresDao.upsertRespuesta(borradorId, preguntaId, valor).catch(() => {});

    // Encolar respuesta para sync con servidor
    const borrador = await borradoresDao.getBorrador(borradorId);
    if (borrador) {
      await colaDao.encolar('RESPONDER_PREGUNTA', borradorId, {
        borrador_id: borradorId,
        sesion_id: borrador.sesion_id ?? null,
        pregunta_id: preguntaId,
        valor,
      });
      await refrescarContadores();
    }

    // Intentar sync inmediato si hay red
    if (estaOnline) {
      useSyncStore.getState().triggerSync();
    }
  }, [borradorId, estaOnline]);

  // ── Asistente IA ────────────────────────────────────────────────────────────
  const handleTextoTranscrito = useCallback(async (preguntaId: number, texto: string) => {
    if (!borradorId) return;
    iniciarGrabacion(preguntaId);
    const borrador = await borradoresDao.getBorrador(borradorId);
    const sesionId = borrador?.sesion_id ?? '';
    await enviarTexto(sesionId, preguntaId, texto);
  }, [borradorId, iniciarGrabacion, enviarTexto]);

  const handleAceptarSugerencia = useCallback((preguntaId: number) => {
    const resultado = aceptarSugerencia();
    if (resultado?.sugerencia) {
      setRespuesta(preguntaId, resultado.sugerencia);
    }
  }, [aceptarSugerencia, setRespuesta]);

  // Limpiar estado IA al salir de la pantalla
  useEffect(() => {
    return () => { resetearIA(); };
  }, []);

  // ── Finalizar tema ──────────────────────────────────────────────────────────
  async function finalizarTema() {
    if (borradorId) {
      // Encolar finalización
      await colaDao.encolar('FINALIZAR_SESION', borradorId, {
        borrador_id: borradorId,
        sesion_id: null,  // se rellenará cuando CREAR_SESION se procese
      });
      await refrescarContadores();
      if (estaOnline) useSyncStore.getState().triggerSync();
    }
    router.back();
  }

  // ── Render ──────────────────────────────────────────────────────────────────
  if (cargando) {
    return (
      <View style={styles.root}>
        <GovHeader title="Cargando módulo…" onBack={() => router.back()} />
        <View style={styles.centrado}>
          <ActivityIndicator size="large" color={GOV.azul} />
        </View>
      </View>
    );
  }

  const totalVisible = preguntasVisibles.length;
  const migaContexto = hogarId
    ? `Hogar ${hogarId.slice(0, 8)}…  ›  ${temaNombre || 'Módulo'}`
    : temaNombre || 'Módulo';

  return (
    <View style={styles.root}>
      <GovHeader
        title={temaNombre || 'Módulo'}
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
                  params: { sesionEncuestaId: borradorId ?? '' },
                })}
              />
            )}
          </View>
        }
      />

      {/* Miga de pan */}
      <View style={styles.miga}>
        <Text style={styles.migaTxt}>
          Formulario PAARI  ›  {migaContexto}
        </Text>
      </View>

      <FlatList
        data={preguntasVisibles}
        keyExtractor={(item) => String(item.id)}
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
          <Text style={styles.sinPreguntas}>No hay preguntas en este módulo.</Text>
        }
      />

      <View style={styles.footerBar}>
        <GovButton label="Guardar y volver" icon="check" onPress={finalizarTema} />
      </View>
    </View>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Componente de pregunta individual
// ─────────────────────────────────────────────────────────────────────────────

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
  return (
    <View style={styles.preguntaCard}>
      {/* Encabezado: número de pregunta */}
      <View style={styles.preguntaHeader}>
        <View style={styles.numBadge}>
          <Text style={styles.numBadgeTxt}>{index + 1}</Text>
        </View>
        <Text style={styles.numTotal}>de {total}</Text>
        {pregunta.requerida && (
          <View style={styles.requeridoChip}>
            <Text style={styles.requeridoTxt}>Requerida</Text>
          </View>
        )}
      </View>
      <Text style={styles.textoPregunta}>
        {pregunta.texto}
      </Text>
      {pregunta.texto_ayuda ? (
        <Text style={styles.ayuda}>{pregunta.texto_ayuda}</Text>
      ) : null}

      {/* Asistente de voz — solo si IA activa */}
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

      {pregunta.tipo_respuesta === 'TEXTO' || pregunta.tipo_respuesta === 'NUMERICO' ? (
        <TextInput
          value={valor}
          onChangeText={onChange}
          keyboardType={pregunta.tipo_respuesta === 'NUMERICO' ? 'numeric' : 'default'}
          style={styles.inputTexto}
          dense
        />
      ) : pregunta.tipo_respuesta === 'FECHA' ? (
        <TextInput
          value={valor}
          onChangeText={onChange}
          placeholder="YYYY-MM-DD"
          style={styles.inputTexto}
          dense
        />
      ) : pregunta.tipo_respuesta === 'OPCION_UNICA' || pregunta.tipo_respuesta === 'SINO' ? (
        <RadioButton.Group value={valor} onValueChange={onChange}>
          {opciones.map((o) => (
            <RadioButton.Item key={o.id} label={o.texto} value={o.codigo} />
          ))}
        </RadioButton.Group>
      ) : pregunta.tipo_respuesta === 'OPCION_MULTIPLE' ? (
        <View>
          {opciones.map((o) => (
            <Checkbox.Item
              key={o.id}
              label={o.texto}
              status={valor.split(',').includes(o.codigo) ? 'checked' : 'unchecked'}
              onPress={() => {
                const sel = valor ? valor.split(',').filter(Boolean) : [];
                const idx = sel.indexOf(o.codigo);
                if (idx >= 0) sel.splice(idx, 1);
                else sel.push(o.codigo);
                onChange(sel.join(','));
              }}
            />
          ))}
        </View>
      ) : (
        <TextInput value={valor} onChangeText={onChange} style={styles.inputTexto} dense />
      )}
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
  },
  headerActions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 2,
  },
  offlineChip: {
    backgroundColor: GOV.naranjaTenue,
  },
  offlineTxt: {
    color: GOV.naranja,
    fontSize: 10,
  },
  iaActivoChip: {
    backgroundColor: GOV.azulTenue,
  },
  iaActivoTxt: {
    color: GOV.azul,
    fontSize: 10,
  },
  lista: {
    padding: SPACING.md,
    paddingBottom: 96,
  },
  sinPreguntas: {
    textAlign: 'center',
    color: GOV.textoT,
    marginTop: SPACING.xl,
    ...FONT.body,
  },
  // Tarjeta de pregunta
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
  numBadgeTxt: {
    fontSize: 11,
    fontWeight: '800',
    color: '#FFFFFF',
  },
  numTotal: {
    ...FONT.caption,
    color: GOV.textoT,
  },
  requeridoChip: {
    marginLeft: 'auto' as any,
    backgroundColor: GOV.rojoTenue,
    borderRadius: RADIUS.pill,
    paddingHorizontal: 8,
    paddingVertical: 2,
  },
  requeridoTxt: {
    fontSize: 10,
    fontWeight: '600',
    color: GOV.rojo,
  },
  textoPregunta: {
    ...FONT.body,
    fontWeight: '600',
    color: GOV.textoP,
    marginBottom: SPACING.sm,
  },
  ayuda: {
    ...FONT.small,
    color: GOV.textoS,
    marginBottom: SPACING.sm,
  },
  inputTexto: {
    backgroundColor: GOV.fondoApp,
  },
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
  migaTxt: {
    ...FONT.caption,
    color: GOV.azulOscuro,
  },
});
