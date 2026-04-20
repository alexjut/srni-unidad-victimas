/**
 * Motor de captura offline de un tema del formulario PAARI.
 *
 * Flujo completo:
 *  1. Carga preguntas, opciones y condiciones desde SQLite local
 *  2. Evalúa skip logic con el servicio puro (sin red)
 *  3. Al cambiar una respuesta: guarda en borrador SQLite y encola para sync
 *  4. Al pulsar "Guardar y continuar": encola FINALIZAR_SESION si es el último tema
 *
 * El borrador_id se pasa como parámetro de ruta junto con temaId.
 * Si no se pasa borrador_id, se crea uno nuevo en este tema.
 */
import { useEffect, useState, useMemo, useCallback } from 'react';
import { View, FlatList, StyleSheet } from 'react-native';
import {
  Text, TextInput, RadioButton, Checkbox,
  Button, ActivityIndicator, Chip,
} from 'react-native-paper';
import { useLocalSearchParams, router } from 'expo-router';
import * as instrumentoDao from '../../../src/db/instrumentoDao';
import * as borradoresDao from '../../../src/db/borradoresDao';
import * as colaDao from '../../../src/db/colaDao';
import { calcularVisibles, construirPreguntasConCondiciones } from '../../../src/services/skipLogic';
import { useSyncStore } from '../../../src/stores/syncStore';
import type { PreguntaRow, OpcionRow, DerivadaRow } from '../../../src/db/instrumentoDao';

// ─────────────────────────────────────────────────────────────────────────────

export default function TemaScreen() {
  const { temaId, borradorId: borradorIdParam, hogarId } = useLocalSearchParams<{
    temaId: string;
    borradorId?: string;
    hogarId?: string;
  }>();

  const { estaOnline, refrescarContadores } = useSyncStore();

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

        // Encolar creación de sesión en servidor
        if (hogarId) {
          await colaDao.encolar('CREAR_SESION', borrador.id, {
            borrador_id: borrador.id,
            hogar: hogarId,
            instrumento: instrId,
          });
          await refrescarContadores();
        }
      }

      setCargando(false);
    })().catch((e) => {
      console.error('Error cargando tema:', e);
      setCargando(false);
    });
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

    // Persistir en SQLite (no bloquea el render)
    borradoresDao.upsertRespuesta(borradorId, preguntaId, valor).catch(console.error);

    // Encolar respuesta para sync con servidor
    const borrador = await borradoresDao.getBorrador(borradorId);
    if (borrador) {
      await colaDao.encolar('RESPONDER_PREGUNTA', borradorId, {
        borrador_id: borradorId,
        sesion_id: borrador.sesion_id ?? null,  // se rellena al procesar CREAR_SESION
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
      <View style={styles.centrado}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  return (
    <View style={styles.root}>
      <View style={styles.headerRow}>
        <Text variant="titleMedium" style={styles.cabecera} numberOfLines={2}>
          {temaNombre}
        </Text>
        {!estaOnline && (
          <Chip compact icon="wifi-off" style={styles.offlineChip} textStyle={styles.offlineTxt}>
            Offline
          </Chip>
        )}
      </View>

      <FlatList
        data={preguntasVisibles}
        keyExtractor={(item) => String(item.id)}
        renderItem={({ item }) => (
          <PreguntaItem
            pregunta={item}
            opciones={opciones[item.id] ?? []}
            valor={respuestas[item.id] ?? ''}
            onChange={(v) => setRespuesta(item.id, v)}
          />
        )}
        contentContainerStyle={styles.lista}
        ListEmptyComponent={
          <Text style={styles.sinPreguntas}>No hay preguntas en este módulo.</Text>
        }
      />

      <Button mode="contained" style={styles.siguiente} onPress={finalizarTema}>
        Guardar y volver
      </Button>
    </View>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Componente de pregunta individual
// ─────────────────────────────────────────────────────────────────────────────

function PreguntaItem({
  pregunta,
  opciones,
  valor,
  onChange,
}: {
  pregunta: PreguntaRow;
  opciones: OpcionRow[];
  valor: string;
  onChange: (v: string) => void;
}) {
  return (
    <View style={styles.preguntaCard}>
      <Text variant="bodyMedium" style={styles.textoPregunta}>
        {pregunta.requerida ? '* ' : ''}{pregunta.texto}
      </Text>
      {pregunta.texto_ayuda ? (
        <Text variant="bodySmall" style={styles.ayuda}>{pregunta.texto_ayuda}</Text>
      ) : null}

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
  root: { flex: 1, backgroundColor: '#F5F5F5' },
  centrado: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  headerRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', margin: 16 },
  cabecera: { fontWeight: '600', color: '#1565C0', flex: 1, marginRight: 8 },
  offlineChip: { backgroundColor: '#FFF3E0' },
  offlineTxt: { color: '#E65100', fontSize: 10 },
  lista: { padding: 12, paddingBottom: 80 },
  sinPreguntas: { textAlign: 'center', color: '#9E9E9E', marginTop: 32 },
  preguntaCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 8,
    padding: 16,
    marginBottom: 8,
    borderLeftWidth: 3,
    borderLeftColor: '#1565C0',
  },
  textoPregunta: { fontWeight: '600', marginBottom: 8 },
  ayuda: { color: '#757575', marginBottom: 8 },
  inputTexto: { backgroundColor: '#FAFAFA' },
  siguiente: { margin: 16, borderRadius: 8 },
});
