/**
 * Pantalla de grabación/transcripción de entrevista — modo asistido por IA.
 *
 * MVP: el encuestador escribe o pega la transcripción manualmente.
 * El flujo real de audio (expo-audio) se puede integrar en una iteración futura
 * sin cambiar esta pantalla.
 *
 * Params recibidos: temaId, capituloNombre, sesionServerId, instrumentoId
 */
import { useEffect, useState } from 'react';
import {
  View,
  ScrollView,
  StyleSheet,
  Alert,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import {
  Text,
  TextInput,
  ActivityIndicator,
  Chip,
} from 'react-native-paper';
import { router, useLocalSearchParams } from 'expo-router';
import * as instrumentos from '../../../src/services/instrumentos';
import type { PreguntaRow, OpcionRow } from '../../../src/db/instrumentoDao';
import { useIAStore } from '../../../src/stores/iaStore';
import { GovHeader } from '../../../src/components/GovHeader';
import { GovButton } from '../../../src/components/GovButton';
import { GOV, SPACING, RADIUS, SHADOW, FONT } from '../../../src/theme/govTheme';
import type { PreguntaBatch } from '../../../src/api/ia';

// ─────────────────────────────────────────────────────────────────────────────

export default function GrabacionEntrevistaScreen() {
  const {
    temaId,
    capituloNombre,
    sesionServerId,
    instrumentoId,
  } = useLocalSearchParams<{
    temaId: string;
    capituloNombre?: string;
    sesionServerId?: string;
    instrumentoId?: string;
  }>();

  const { estado, procesarEntrevista, errorMensaje, resultadosBatch } = useIAStore();

  const [transcripcion, setTranscripcion] = useState('');
  const [preguntas, setPreguntas] = useState<PreguntaRow[]>([]);
  const [opcionesPorPregunta, setOpcionesPorPregunta] = useState<
    Record<string, OpcionRow[]>
  >({});
  const [cargandoPreguntas, setCargandoPreguntas] = useState(true);

  const procesando = estado === 'procesando_entrevista';

  // Sprint 18 Fase D: lecturas del instrumento desde memoria (no SQLite).
  useEffect(() => {
    if (!temaId) return;
    try {
      const pgs = instrumentos.getPreguntas(temaId);
      setPreguntas(pgs);
      if (pgs.length > 0) {
        setOpcionesPorPregunta(instrumentos.getOpcionesBatch(pgs.map((p) => p.id)));
      }
    } finally {
      setCargandoPreguntas(false);
    }
  }, [temaId]);

  // ── Navegar a revision-ia cuando lleguen los resultados ────────────────────
  useEffect(() => {
    if (resultadosBatch && resultadosBatch.length > 0) {
      router.replace({
        pathname: '/(main)/formulario/revision-ia' as any,
        params: {
          temaId,
          sesionServerId: sesionServerId ?? '',
        },
      });
    }
  }, [resultadosBatch]);

  // ── Manejar error del store ────────────────────────────────────────────────
  useEffect(() => {
    if (estado === 'error' && errorMensaje) {
      Alert.alert(
        'Error de conexión IA',
        errorMensaje + '\n\n¿Desea continuar de forma manual?',
        [
          {
            text: 'Ir al modo manual',
            onPress: () => {
              router.replace({
                pathname: '/(main)/formulario/[temaId]',
                params: {
                  temaId,
                  ...(sesionServerId ? { sesionServerId } : {}),
                  ...(instrumentoId  ? { instrumentoId }  : {}),
                },
              });
            },
          },
          { text: 'Intentar de nuevo', style: 'cancel' },
        ],
      );
    }
  }, [estado, errorMensaje]);

  // ── Enviar al backend ──────────────────────────────────────────────────────
  async function handleProcesar() {
    if (!transcripcion.trim()) {
      Alert.alert('Transcripción vacía', 'Por favor ingrese o pegue la transcripción de la entrevista.');
      return;
    }
    if (!sesionServerId) {
      Alert.alert('Sin sesión', 'No hay una sesión activa vinculada al servidor. Active la sesión primero.');
      return;
    }
    if (preguntas.length === 0) {
      Alert.alert('Sin preguntas', 'No se encontraron preguntas para este capítulo.');
      return;
    }

    // Construir lista de preguntas con sus opciones para el batch
    const preguntasBatch: PreguntaBatch[] = preguntas.map((p) => ({
      pregunta_id: p.id,
      codigo_externo: p.codigo_externo,
      texto: p.texto,
      tipo: p.tipo,
      opciones: (opcionesPorPregunta[p.id] ?? []).map((o) => o.valor),
    }));

    await procesarEntrevista(sesionServerId, temaId, transcripcion.trim(), preguntasBatch);
  }

  // ── Render ─────────────────────────────────────────────────────────────────
  const nombreCapitulo = capituloNombre ?? 'Capítulo';

  return (
    <KeyboardAvoidingView
      style={styles.root}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <GovHeader
        title="Asistente IA"
        subtitle={`Entrevista — ${nombreCapitulo}`}
        onBack={() => router.back()}
      />

      <View style={styles.miga}>
        <Text style={styles.migaTxt}>
          Formulario  ›  {nombreCapitulo}  ›  Grabación
        </Text>
      </View>

      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
      >
        {/* Instrucciones */}
        <View style={styles.card}>
          <View style={styles.cardHeader}>
            <Chip icon="robot" style={styles.iaChip} textStyle={styles.iaChipTxt}>
              Modo asistido por IA
            </Chip>
          </View>
          <Text style={styles.instrucciones}>
            Ingrese o pegue la transcripción de la entrevista realizada. El asistente
            analizará el texto y sugerirá respuestas para cada pregunta del capítulo
            "{nombreCapitulo}".
          </Text>
          <Text style={styles.nota}>
            Podrá revisar y corregir cada sugerencia antes de guardarlas.
          </Text>
        </View>

        {/* Resumen de preguntas a procesar */}
        {cargandoPreguntas ? (
          <View style={styles.centrado}>
            <ActivityIndicator size="small" color={GOV.azul} />
            <Text style={styles.cargandoTxt}>Cargando preguntas…</Text>
          </View>
        ) : (
          <View style={styles.resumeRow}>
            <Chip icon="format-list-checks" compact style={styles.resumeChip}>
              {preguntas.length} preguntas
            </Chip>
          </View>
        )}

        {/* Área de transcripción */}
        <Text style={styles.label}>Transcripción de la entrevista</Text>
        <TextInput
          value={transcripcion}
          onChangeText={setTranscripcion}
          placeholder="Escriba o pegue aquí la transcripción completa de la entrevista…"
          multiline
          numberOfLines={12}
          style={styles.textArea}
          editable={!procesando}
          accessibilityLabel="Transcripción de la entrevista"
        />

        <Text style={styles.contador}>
          {transcripcion.length} / 50 000 caracteres
        </Text>

        {/* Indicador de procesamiento */}
        {procesando && (
          <View style={styles.procesandoBox}>
            <ActivityIndicator size="large" color={GOV.azul} />
            <Text style={styles.procesandoTxt}>
              Analizando entrevista con IA…
            </Text>
            <Text style={styles.procesandoSub}>
              Esto puede tardar unos segundos según la longitud de la transcripción.
            </Text>
          </View>
        )}
      </ScrollView>

      {/* Pie de pantalla */}
      <View style={styles.footer}>
        <View style={styles.footerBotones}>
          <GovButton
            label="Modo manual"
            variant="secondary"
            icon="pencil"
            fullWidth={false}
            onPress={() =>
              router.replace({
                pathname: '/(main)/formulario/[temaId]',
                params: {
                  temaId,
                  ...(sesionServerId ? { sesionServerId } : {}),
                  ...(instrumentoId  ? { instrumentoId }  : {}),
                },
              })
            }
            disabled={procesando}
          />
          <GovButton
            label="Procesar con IA"
            variant="primary"
            icon="send"
            fullWidth={false}
            onPress={handleProcesar}
            loading={procesando}
            disabled={procesando || cargandoPreguntas || !transcripcion.trim()}
          />
        </View>
      </View>
    </KeyboardAvoidingView>
  );
}

// ─── Estilos ──────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  root:         { flex: 1, backgroundColor: GOV.fondoApp },
  miga: {
    backgroundColor: GOV.azulTenue,
    paddingHorizontal: SPACING.md,
    paddingVertical: 6,
    borderBottomWidth: 1,
    borderBottomColor: GOV.borde,
  },
  migaTxt:      { ...FONT.caption, color: GOV.azulOscuro },
  scroll:       { flex: 1 },
  scrollContent: { padding: SPACING.md, paddingBottom: SPACING.xl },
  centrado:     { alignItems: 'center', paddingVertical: SPACING.md },
  cargandoTxt:  { ...FONT.small, color: GOV.textoS, marginTop: SPACING.xs },

  card: {
    backgroundColor: GOV.superficie,
    borderRadius: RADIUS.md,
    padding: SPACING.md,
    marginBottom: SPACING.md,
    borderLeftWidth: 4,
    borderLeftColor: GOV.azul,
    ...SHADOW.card,
  },
  cardHeader:   { marginBottom: SPACING.sm },
  iaChip:       { backgroundColor: GOV.azulTenue, alignSelf: 'flex-start' },
  iaChipTxt:    { color: GOV.azul, fontSize: 12 },
  instrucciones: { ...FONT.body, color: GOV.textoP, marginBottom: SPACING.sm },
  nota:         { ...FONT.small, color: GOV.textoS },

  resumeRow:    { flexDirection: 'row', marginBottom: SPACING.md, gap: SPACING.sm },
  resumeChip:   { backgroundColor: GOV.verdeTenue },

  label:        { ...FONT.label, color: GOV.textoS, marginBottom: SPACING.xs },
  textArea: {
    backgroundColor: GOV.superficie,
    minHeight: 200,
    textAlignVertical: 'top',
    fontSize: 14,
    lineHeight: 22,
  },
  contador:     { ...FONT.caption, color: GOV.textoT, textAlign: 'right', marginTop: 4 },

  procesandoBox: {
    alignItems: 'center',
    paddingVertical: SPACING.lg,
    gap: SPACING.sm,
  },
  procesandoTxt: { ...FONT.h3, color: GOV.azul, textAlign: 'center' },
  procesandoSub: { ...FONT.small, color: GOV.textoS, textAlign: 'center' },

  footer: {
    backgroundColor: GOV.superficie,
    padding: SPACING.md,
    borderTopWidth: 1,
    borderTopColor: GOV.borde,
  },
  footerBotones: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: SPACING.sm,
  },
});
