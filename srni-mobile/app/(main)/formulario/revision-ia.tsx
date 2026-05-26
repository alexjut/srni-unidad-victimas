/**
 * Pantalla de revisión de sugerencias IA — modo batch.
 *
 * Lee los resultadosBatch del iaStore, permite aceptar / editar / rechazar
 * cada sugerencia y luego guarda en borradoresDao + cola de sincronización.
 *
 * Params recibidos: temaId, sesionServerId, borradorId (opcional)
 */
import { useEffect, useState, useCallback } from 'react';
import {
  View,
  FlatList,
  StyleSheet,
  Alert,
} from 'react-native';
import {
  Text,
  TextInput,
  Chip,
  ActivityIndicator,
  IconButton,
} from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { router, useLocalSearchParams } from 'expo-router';
import * as instrumentos from '../../../src/services/instrumentos';
import * as borradoresDao from '../../../src/db/borradoresDao';
import * as colaDao from '../../../src/db/colaDao';
import { useIAStore } from '../../../src/stores/iaStore';
import { useSyncStore } from '../../../src/stores/syncStore';
import { GovHeader } from '../../../src/components/GovHeader';
import { GovButton } from '../../../src/components/GovButton';
import { GOV, SPACING, RADIUS, SHADOW, FONT } from '../../../src/theme/govTheme';
import type { ResultadoBatch } from '../../../src/stores/iaStore';

// ─── Tipos locales ────────────────────────────────────────────────────────────

interface ResultadoEditable {
  resultado: ResultadoBatch;
  preguntaTexto: string;
  valorEditado: string;      // valor que se guardará (puede haber sido editado)
  aceptado: boolean;
  editando: boolean;
}

// ─── Colores de confianza ─────────────────────────────────────────────────────

function colorConfianza(confianza: number): string {
  if (confianza >= 0.8) return GOV.verde;
  if (confianza >= 0.5) return GOV.naranja;
  return GOV.rojo;
}

function fondoConfianza(confianza: number): string {
  if (confianza >= 0.8) return GOV.verdeTenue;
  if (confianza >= 0.5) return GOV.naranjaTenue;
  return GOV.rojoTenue;
}

function etiquetaConfianza(confianza: number): string {
  if (confianza >= 0.8) return 'Alta confianza';
  if (confianza >= 0.5) return 'Confianza media';
  return 'Baja confianza';
}

// ─── Tarjeta de resultado individual ─────────────────────────────────────────

function ResultadoCard({
  item,
  index,
  onAceptar,
  onEditar,
  onConfirmarEdicion,
  onRechazar,
  onChangeValor,
}: {
  item: ResultadoEditable;
  index: number;
  onAceptar: () => void;
  onEditar: () => void;
  onConfirmarEdicion: () => void;
  onRechazar: () => void;
  onChangeValor: (v: string) => void;
}) {
  const sinSugerencia = item.resultado.sugerencia === null;
  const color = sinSugerencia ? GOV.textoT : colorConfianza(item.resultado.confianza);
  const fondo = sinSugerencia ? GOV.fondoApp : fondoConfianza(item.resultado.confianza);

  return (
    <View style={[styles.card, item.aceptado && styles.cardAceptada]}>
      {/* Encabezado */}
      <View style={styles.cardHeader}>
        <View style={styles.numBadge}>
          <Text style={styles.numBadgeTxt}>{index + 1}</Text>
        </View>
        <Text style={styles.codigoTxt}>{item.resultado.codigo_externo}</Text>
        {item.aceptado && (
          <MaterialCommunityIcons name="check-circle" size={18} color={GOV.verde} style={{ marginLeft: 'auto' as any }} />
        )}
      </View>

      {/* Texto de la pregunta */}
      <Text style={styles.preguntaTxt}>{item.preguntaTexto || item.resultado.pregunta_id}</Text>

      {/* Sin sugerencia */}
      {sinSugerencia ? (
        <Chip
          icon="alert-circle-outline"
          style={styles.sinSugerenciaChip}
          textStyle={styles.sinSugerenciaTxt}
        >
          Sin sugerencia — responder manualmente
        </Chip>
      ) : (
        <>
          {/* Chip de confianza */}
          <View style={[styles.confianzaRow, { backgroundColor: fondo }]}>
            <Text style={[styles.confianzaLabel, { color }]}>
              {etiquetaConfianza(item.resultado.confianza)} ({Math.round(item.resultado.confianza * 100)}%)
            </Text>
          </View>

          {/* Sugerencia / editor */}
          {item.editando ? (
            <View style={styles.editorRow}>
              <TextInput
                value={item.valorEditado}
                onChangeText={onChangeValor}
                style={styles.inputEditor}
                dense
                autoFocus
                accessibilityLabel="Editar respuesta"
              />
              <IconButton
                icon="check"
                iconColor={GOV.verde}
                size={22}
                onPress={onConfirmarEdicion}
                accessibilityLabel="Confirmar edición"
              />
            </View>
          ) : (
            <View style={styles.sugerenciaRow}>
              <Text style={styles.sugerenciaValor}>
                {item.valorEditado || item.resultado.sugerencia}
              </Text>
              {!item.aceptado && (
                <IconButton
                  icon="pencil"
                  iconColor={GOV.textoS}
                  size={18}
                  onPress={onEditar}
                  accessibilityLabel="Editar sugerencia"
                />
              )}
            </View>
          )}

          {/* Razonamiento */}
          {!!item.resultado.razonamiento && (
            <Text style={styles.razonamientoTxt}>
              IA: {item.resultado.razonamiento}
            </Text>
          )}

          {/* Botones aceptar / rechazar */}
          {!item.aceptado && !item.editando && (
            <View style={styles.botonesRow}>
              <GovButton
                label="Aceptar"
                variant="primary"
                icon="check"
                fullWidth={false}
                onPress={onAceptar}
              />
              <GovButton
                label="Ignorar"
                variant="ghost"
                icon="close"
                fullWidth={false}
                onPress={onRechazar}
              />
            </View>
          )}

          {item.aceptado && (
            <Text style={styles.aceptadaTxt}>Respuesta aceptada</Text>
          )}
        </>
      )}
    </View>
  );
}

// ─── Pantalla principal ───────────────────────────────────────────────────────

export default function RevisionIAScreen() {
  const {
    temaId,
    sesionServerId,
    borradorId: borradorIdParam,
  } = useLocalSearchParams<{
    temaId: string;
    sesionServerId?: string;
    borradorId?: string;
  }>();

  const { resultadosBatch, limpiarResultadosBatch } = useIAStore();
  const { estaOnline, refrescarContadores } = useSyncStore();

  const [items, setItems] = useState<ResultadoEditable[]>([]);
  const [cargando, setCargando] = useState(true);
  const [guardando, setGuardando] = useState(false);

  // ── Cruzar resultados con textos de preguntas ─────────────────────────────
  useEffect(() => {
    if (!resultadosBatch) {
      setCargando(false);
      return;
    }
    // Sprint 18 Fase D: lectura desde memoria (sin await)
    try {
      const pgs = instrumentos.getPreguntas(temaId);
      const mapa: Record<string, string> = {};
      for (const p of pgs) mapa[p.id] = p.texto;

      const editables: ResultadoEditable[] = resultadosBatch.map((r) => ({
        resultado: r,
        preguntaTexto: mapa[r.pregunta_id] ?? '',
        valorEditado: r.sugerencia ?? '',
        aceptado: false,
        editando: false,
      }));
      setItems(editables);
    } finally {
      setCargando(false);
    }
  }, [resultadosBatch, temaId]);

  // ── Limpieza al desmontar ─────────────────────────────────────────────────
  useEffect(() => {
    return () => { limpiarResultadosBatch(); };
  }, []);

  // ── Acciones sobre ítems ──────────────────────────────────────────────────
  const actualizarItem = useCallback(
    (index: number, cambios: Partial<ResultadoEditable>) => {
      setItems((prev) => {
        const next = [...prev];
        next[index] = { ...next[index], ...cambios };
        return next;
      });
    },
    [],
  );

  const handleAceptar = useCallback((index: number) => {
    actualizarItem(index, { aceptado: true, editando: false });
  }, [actualizarItem]);

  const handleEditar = useCallback((index: number) => {
    actualizarItem(index, { editando: true });
  }, [actualizarItem]);

  const handleConfirmarEdicion = useCallback((index: number) => {
    actualizarItem(index, { editando: false, aceptado: true });
  }, [actualizarItem]);

  const handleRechazar = useCallback((index: number) => {
    actualizarItem(index, { aceptado: false, editando: false, valorEditado: '' });
  }, [actualizarItem]);

  const handleChangeValor = useCallback((index: number, valor: string) => {
    actualizarItem(index, { valorEditado: valor });
  }, [actualizarItem]);

  // ── Confirmar todo: guardar respuestas aceptadas ──────────────────────────
  async function handleConfirmarTodo() {
    const aceptadas = items.filter((i) => i.aceptado && i.valorEditado);
    if (aceptadas.length === 0) {
      Alert.alert('Sin respuestas', 'No ha aceptado ninguna sugerencia. ¿Desea volver sin guardar?', [
        { text: 'Volver sin guardar', onPress: () => router.back() },
        { text: 'Seguir revisando', style: 'cancel' },
      ]);
      return;
    }

    setGuardando(true);
    try {
      // Obtener o crear borrador
      let bid = borradorIdParam ?? null;
      if (!bid && sesionServerId) {
        const meta = instrumentos.getMeta();
        const instrId = meta?.instrumento_id ?? '';
        const borrador = await borradoresDao.crearBorrador(instrId);
        bid = borrador.id;
        await borradoresDao.vincularSesionServidor(bid, sesionServerId);
      }

      if (!bid) {
        Alert.alert('Error', 'No se pudo determinar el borrador para guardar las respuestas.');
        setGuardando(false);
        return;
      }

      const borrador = await borradoresDao.getBorrador(bid);

      for (const item of aceptadas) {
        await borradoresDao.upsertRespuesta(bid, item.resultado.pregunta_id, item.valorEditado);
        if (borrador) {
          await colaDao.encolar('RESPONDER_PREGUNTA', bid, {
            borrador_id: bid,
            sesion_id: borrador.sesion_id ?? null,
            pregunta_id: item.resultado.pregunta_id,
            valor: item.valorEditado,
          });
        }
      }

      await refrescarContadores();
      if (estaOnline) useSyncStore.getState().triggerSync();

      Alert.alert(
        'Respuestas guardadas',
        `Se guardaron ${aceptadas.length} respuestas del asistente IA.`,
        [{ text: 'Continuar', onPress: () => router.back() }],
      );
    } catch (err) {
      Alert.alert('Error', 'No se pudieron guardar las respuestas. Intente de nuevo.');
    } finally {
      setGuardando(false);
    }
  }

  // ── Sin resultados ────────────────────────────────────────────────────────
  if (!cargando && (!resultadosBatch || resultadosBatch.length === 0)) {
    return (
      <View style={styles.root}>
        <GovHeader title="Revisión IA" onBack={() => router.back()} />
        <View style={styles.centrado}>
          <MaterialCommunityIcons name="robot-off" size={48} color={GOV.textoT} />
          <Text style={styles.sinResultadosTxt}>
            No hay resultados del asistente IA disponibles.
          </Text>
          <GovButton label="Volver" variant="secondary" onPress={() => router.back()} />
        </View>
      </View>
    );
  }

  if (cargando) {
    return (
      <View style={styles.root}>
        <GovHeader title="Revisión IA" onBack={() => router.back()} />
        <View style={styles.centrado}>
          <ActivityIndicator size="large" color={GOV.azul} />
          <Text style={styles.cargandoTxt}>Preparando revisión…</Text>
        </View>
      </View>
    );
  }

  const aceptadas = items.filter((i) => i.aceptado).length;
  const conSugerencia = items.filter((i) => i.resultado.sugerencia !== null).length;

  return (
    <View style={styles.root}>
      <GovHeader
        title="Revisión IA"
        subtitle={`${aceptadas} aceptadas de ${conSugerencia} sugerencias`}
        onBack={() => router.back()}
      />

      <View style={styles.miga}>
        <Text style={styles.migaTxt}>Formulario  ›  Revisión de sugerencias IA</Text>
      </View>

      {/* Resumen */}
      <View style={styles.resumenRow}>
        <Chip icon="check-circle" compact style={styles.chipVerde}>
          {aceptadas} aceptadas
        </Chip>
        <Chip icon="robot" compact style={styles.chipAzul}>
          {conSugerencia} con sugerencia
        </Chip>
        <Chip icon="help-circle" compact style={styles.chipGris}>
          {items.length - conSugerencia} sin sugerencia
        </Chip>
      </View>

      <FlatList
        data={items}
        keyExtractor={(_, i) => String(i)}
        renderItem={({ item, index }) => (
          <ResultadoCard
            item={item}
            index={index}
            onAceptar={() => handleAceptar(index)}
            onEditar={() => handleEditar(index)}
            onConfirmarEdicion={() => handleConfirmarEdicion(index)}
            onRechazar={() => handleRechazar(index)}
            onChangeValor={(v) => handleChangeValor(index, v)}
          />
        )}
        contentContainerStyle={styles.lista}
      />

      <View style={styles.footer}>
        <GovButton
          label={guardando ? 'Guardando…' : `Confirmar ${aceptadas > 0 ? aceptadas : 'seleccionadas'} y cerrar`}
          variant="primary"
          icon="content-save"
          onPress={handleConfirmarTodo}
          loading={guardando}
          disabled={guardando}
        />
      </View>
    </View>
  );
}

// ─── Estilos ──────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  root:           { flex: 1, backgroundColor: GOV.fondoApp },
  miga: {
    backgroundColor: GOV.azulTenue,
    paddingHorizontal: SPACING.md,
    paddingVertical: 6,
    borderBottomWidth: 1,
    borderBottomColor: GOV.borde,
  },
  migaTxt:        { ...FONT.caption, color: GOV.azulOscuro },
  centrado:       { flex: 1, justifyContent: 'center', alignItems: 'center', padding: SPACING.xl },
  cargandoTxt:    { ...FONT.small, color: GOV.textoS, marginTop: SPACING.sm },
  sinResultadosTxt: { ...FONT.body, color: GOV.textoS, textAlign: 'center', marginVertical: SPACING.md },

  resumenRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: SPACING.xs,
    paddingHorizontal: SPACING.md,
    paddingVertical: SPACING.sm,
    backgroundColor: GOV.superficie,
    borderBottomWidth: 1,
    borderBottomColor: GOV.borde,
  },
  chipVerde: { backgroundColor: GOV.verdeTenue },
  chipAzul:  { backgroundColor: GOV.azulTenue },
  chipGris:  { backgroundColor: GOV.fondoApp },

  lista: { padding: SPACING.md, paddingBottom: 96 },

  card: {
    backgroundColor: GOV.superficie,
    borderRadius: RADIUS.md,
    padding: SPACING.md,
    marginBottom: SPACING.sm,
    borderLeftWidth: 4,
    borderLeftColor: GOV.borde,
    ...SHADOW.card,
  },
  cardAceptada: {
    borderLeftColor: GOV.verde,
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: SPACING.sm,
    gap: SPACING.xs,
  },
  numBadge: {
    width: 24, height: 24, borderRadius: 12,
    backgroundColor: GOV.azul,
    justifyContent: 'center', alignItems: 'center',
  },
  numBadgeTxt:    { fontSize: 11, fontWeight: '800', color: '#FFFFFF' },
  codigoTxt:      { ...FONT.caption, color: GOV.textoT, fontFamily: 'monospace' },

  preguntaTxt:    { ...FONT.body, fontWeight: '600', color: GOV.textoP, marginBottom: SPACING.sm },

  sinSugerenciaChip: { backgroundColor: GOV.naranjaTenue, alignSelf: 'flex-start' },
  sinSugerenciaTxt:  { color: GOV.naranja, fontSize: 12 },

  confianzaRow: {
    borderRadius: RADIUS.sm,
    paddingHorizontal: SPACING.sm,
    paddingVertical: 4,
    marginBottom: SPACING.sm,
    alignSelf: 'flex-start',
  },
  confianzaLabel: { fontSize: 12, fontWeight: '600' },

  sugerenciaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: GOV.fondoApp,
    borderRadius: RADIUS.sm,
    paddingHorizontal: SPACING.sm,
    paddingVertical: SPACING.xs,
    marginBottom: SPACING.sm,
  },
  sugerenciaValor: { ...FONT.body, color: GOV.textoP, flex: 1 },

  editorRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: SPACING.sm,
  },
  inputEditor: { flex: 1, backgroundColor: GOV.fondoApp },

  razonamientoTxt: { ...FONT.caption, color: GOV.textoS, fontStyle: 'italic', marginBottom: SPACING.sm },

  botonesRow: {
    flexDirection: 'row',
    gap: SPACING.sm,
    marginTop: SPACING.xs,
  },
  aceptadaTxt: { ...FONT.small, color: GOV.verde, fontWeight: '600', marginTop: SPACING.xs },

  footer: {
    backgroundColor: GOV.superficie,
    padding: SPACING.md,
    borderTopWidth: 1,
    borderTopColor: GOV.borde,
  },
});
