// Detalle de una sesión de encuesta — GOV.CO design system.
import { useEffect, useState } from 'react';
import { View, ScrollView, StyleSheet, Alert } from 'react-native';
import {
  Text, Chip, ProgressBar, ActivityIndicator, Divider,
} from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { router, useLocalSearchParams } from 'expo-router';
import { encuestasApi } from '../../../src/api/encuestas';
import { GovHeader } from '../../../src/components/GovHeader';
import { GovButton } from '../../../src/components/GovButton';
import { GOV, SPACING, RADIUS, SHADOW, FONT } from '../../../src/theme/govTheme';
import type { SesionDetalle } from '../../../src/types';

const ESTADO_COLOR: Record<string, string> = {
  INICIADA:    GOV.azul,
  EN_PROGRESO: GOV.naranja,
  COMPLETADA:  GOV.verde,
  SUSPENDIDA:  '#616161',
};

// ─── Fila de info ─────────────────────────────────────────────────────────────

function InfoFila({ label, valor }: { label: string; valor: string }) {
  return (
    <View style={styles.infoFila}>
      <Text style={styles.infoLabel}>{label}</Text>
      <Text style={styles.infoValor}>{valor || '—'}</Text>
    </View>
  );
}

// ─── Pantalla ─────────────────────────────────────────────────────────────────

export default function SesionDetalleScreen() {
  const { sesionId } = useLocalSearchParams<{ sesionId: string }>();
  const [sesion, setSesion] = useState<SesionDetalle | null>(null);
  const [cargando, setCargando] = useState(true);
  const [finalizando, setFinalizando] = useState(false);
  const [error, setError] = useState('');

  function cargar() {
    if (!sesionId) return;
    setCargando(true);
    encuestasApi.detalle(sesionId)
      .then((res) => setSesion(res.data))
      .catch(() => setError('No se pudo cargar la sesión.'))
      .finally(() => setCargando(false));
  }

  useEffect(() => { cargar(); }, [sesionId]);

  function confirmarFinalizar() {
    Alert.alert(
      'Finalizar sesión',
      `¿Confirma que desea cerrar esta sesión? Progreso: ${sesion?.porcentaje_completado ?? 0}%.`,
      [
        { text: 'Cancelar', style: 'cancel' },
        { text: 'Finalizar', style: 'destructive', onPress: finalizar },
      ],
    );
  }

  async function finalizar() {
    if (!sesion) return;
    setFinalizando(true);
    try {
      const res = await encuestasApi.finalizar(sesion.id);
      setSesion(res.data);
    } catch (err: any) {
      Alert.alert('Error', err?.response?.data?.detail ?? 'No se pudo finalizar la sesión.');
    } finally {
      setFinalizando(false);
    }
  }

  // ── Cargando ─────────────────────────────────────────────────────────────────

  if (cargando) {
    return (
      <View style={styles.root}>
        <GovHeader title="Sesión de encuesta" onBack={() => router.back()} />
        <View style={styles.centrado}>
          <ActivityIndicator size="large" color={GOV.azul} />
        </View>
      </View>
    );
  }

  // ── Error ─────────────────────────────────────────────────────────────────────

  if (error || !sesion) {
    return (
      <View style={styles.root}>
        <GovHeader title="Sesión de encuesta" onBack={() => router.back()} />
        <View style={styles.centrado}>
          <MaterialCommunityIcons name="alert-circle-outline" size={48} color={GOV.rojo} />
          <Text style={styles.errorTxt}>{error || 'Sesión no encontrada.'}</Text>
          <GovButton label="Volver" variant="secondary" onPress={() => router.back()} />
        </View>
      </View>
    );
  }

  const colorEstado = ESTADO_COLOR[sesion.estado] ?? '#616161';
  const bgEstado    = colorEstado + '22';
  const estaActiva  = sesion.estado !== 'COMPLETADA' && sesion.estado !== 'SUSPENDIDA';
  const hogarCorto  = sesion.hogar.slice(0, 8);

  return (
    <View style={styles.root}>
      <GovHeader
        title={`Sesión ${sesion.id.slice(0, 8)}…`}
        subtitle={sesion.instrumento_nombre}
        onBack={() => router.back()}
      />

      {/* Miga de pan */}
      <View style={styles.miga}>
        <Text style={styles.migaTxt}>
          Hogares  ›  Hogar {hogarCorto}…  ›  Sesión
        </Text>
      </View>

      <ScrollView contentContainerStyle={styles.content}>

        {/* Encabezado de sesión */}
        <View style={styles.card}>
          <View style={styles.estadoRow}>
            <View style={[styles.estadoChip, { backgroundColor: bgEstado }]}>
              <Text style={[styles.estadoTxt, { color: colorEstado }]}>{sesion.estado_display}</Text>
            </View>
            <Text style={styles.fecha}>
              {new Date(sesion.fecha_inicio).toLocaleDateString('es-CO')}
              {sesion.fecha_fin ? ` — ${new Date(sesion.fecha_fin).toLocaleDateString('es-CO')}` : ''}
            </Text>
          </View>

          <InfoFila label="Hogar"      valor={`${hogarCorto}…`} />
          <InfoFila label="Instrumento" valor={sesion.instrumento_nombre} />

          <Divider style={styles.divider} />

          {/* Barra de progreso */}
          <View style={styles.progresoRow}>
            <ProgressBar
              progress={sesion.porcentaje_completado / 100}
              style={styles.barra}
              color={colorEstado}
            />
            <Text style={[styles.pct, { color: colorEstado }]}>
              {sesion.porcentaje_completado}%
            </Text>
          </View>
          <Text style={styles.respuestasMeta}>
            {sesion.total_respuestas} respuesta{sesion.total_respuestas !== 1 ? 's' : ''} guardada{sesion.total_respuestas !== 1 ? 's' : ''}
          </Text>
        </View>

        {/* Acciones — solo si la sesión está activa */}
        {estaActiva && (
          <View style={styles.card}>
            <Text style={styles.seccionTitulo}>Continuar</Text>

            <GovButton
              label="Continuar formulario PAARI"
              icon="clipboard-text"
              onPress={() =>
                router.push({
                  pathname: '/(main)/formulario',
                  params: {
                    sesionServerId: sesion.id,
                    instrumentoId: sesion.instrumento,
                    hogarId: sesion.hogar,
                  },
                })
              }
            />

            <View style={styles.sepBtn}>
              <GovButton
                label="Finalizar sesión"
                variant="secondary"
                icon="check-circle"
                loading={finalizando}
                disabled={finalizando}
                onPress={confirmarFinalizar}
              />
            </View>
          </View>
        )}

        {/* Respuestas guardadas */}
        {sesion.respuestas.length > 0 && (
          <View style={styles.card}>
            <Text style={styles.seccionTitulo}>
              Respuestas guardadas ({sesion.total_respuestas})
            </Text>
            {sesion.respuestas.map((r) => (
              <View key={r.id} style={styles.respuestaRow}>
                <Text style={styles.codigoPregunta}>[{r.pregunta_codigo}]</Text>
                <Text style={styles.textoPregunta} numberOfLines={1}>{r.pregunta_texto}</Text>
                <Text style={styles.valorRespuesta}>{r.valor || '—'}</Text>
              </View>
            ))}
          </View>
        )}

        {sesion.estado === 'COMPLETADA' && sesion.observaciones ? (
          <View style={styles.card}>
            <Text style={styles.seccionTitulo}>Observaciones</Text>
            <Text style={styles.observaciones}>{sesion.observaciones}</Text>
          </View>
        ) : null}

      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: GOV.fondoApp,
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
  centrado: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: SPACING.xl,
    gap: SPACING.md,
  },
  errorTxt: {
    ...FONT.body,
    color: GOV.rojo,
    textAlign: 'center',
  },
  content: {
    padding: SPACING.md,
    paddingBottom: SPACING.xxl,
  },
  card: {
    backgroundColor: GOV.superficie,
    borderRadius: RADIUS.md,
    padding: SPACING.md,
    marginBottom: SPACING.md,
    ...SHADOW.card,
  },
  estadoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: SPACING.sm,
  },
  estadoChip: {
    borderRadius: RADIUS.pill,
    paddingHorizontal: 10,
    paddingVertical: 3,
  },
  estadoTxt: {
    fontSize: 11,
    fontWeight: '700',
  },
  fecha: {
    ...FONT.caption,
    color: GOV.textoT,
  },
  divider: {
    marginVertical: SPACING.sm,
  },
  progresoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
  },
  barra: {
    flex: 1,
    height: 8,
    borderRadius: 4,
    marginRight: SPACING.sm,
  },
  pct: {
    ...FONT.body,
    fontWeight: '700',
    minWidth: 40,
    textAlign: 'right',
  },
  respuestasMeta: {
    ...FONT.caption,
    color: GOV.textoT,
    marginTop: 2,
  },
  infoFila: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 5,
    borderBottomWidth: 1,
    borderBottomColor: GOV.borde,
  },
  infoLabel: {
    ...FONT.small,
    color: GOV.textoT,
    flex: 1,
  },
  infoValor: {
    ...FONT.small,
    color: GOV.textoP,
    flex: 2,
    textAlign: 'right',
    fontWeight: '500',
  },
  seccionTitulo: {
    ...FONT.label,
    color: GOV.textoS,
    textTransform: 'uppercase',
    letterSpacing: 0.8,
    marginBottom: SPACING.sm,
  },
  sepBtn: {
    marginTop: SPACING.sm,
  },
  respuestaRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    paddingVertical: 5,
    borderBottomWidth: 1,
    borderBottomColor: GOV.borde,
    gap: SPACING.sm,
  },
  codigoPregunta: {
    fontFamily: 'monospace',
    ...FONT.caption,
    color: GOV.azul,
    minWidth: 60,
  },
  textoPregunta: {
    ...FONT.caption,
    color: GOV.textoS,
    flex: 1,
  },
  valorRespuesta: {
    ...FONT.caption,
    color: GOV.textoP,
    fontWeight: '600',
    minWidth: 50,
    textAlign: 'right',
  },
  observaciones: {
    ...FONT.body,
    color: GOV.textoS,
  },
});
