/**
 * Detalle de una sesión de encuesta.
 * Muestra el progreso, lista de respuestas guardadas y permite finalizar la sesión.
 */
import { useEffect, useState } from 'react';
import { View, ScrollView, StyleSheet, Alert } from 'react-native';
import {
  Text, Card, Chip, ProgressBar, Button,
  ActivityIndicator, Divider, List,
} from 'react-native-paper';
import { router, useLocalSearchParams, Stack } from 'expo-router';
import { encuestasApi } from '../../../src/api/encuestas';
import type { SesionDetalle } from '../../../src/types';

const ESTADO_COLOR: Record<string, string> = {
  INICIADA: '#1565C0',
  EN_PROGRESO: '#E65100',
  COMPLETADA: '#2E7D32',
  SUSPENDIDA: '#616161',
};

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
      `¿Confirma que desea cerrar esta sesión? Progreso actual: ${sesion?.porcentaje_completado ?? 0}%.`,
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
      const msg = err?.response?.data?.detail ?? 'No se pudo finalizar la sesión.';
      Alert.alert('Error', msg);
    } finally {
      setFinalizando(false);
    }
  }

  if (cargando) {
    return (
      <View style={styles.centrado}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  if (error || !sesion) {
    return (
      <View style={styles.centrado}>
        <Text style={styles.errorTxt}>{error || 'Sesión no encontrada.'}</Text>
        <Button onPress={() => router.back()}>Volver</Button>
      </View>
    );
  }

  const colorEstado = ESTADO_COLOR[sesion.estado] ?? '#616161';
  const estaActiva = sesion.estado !== 'COMPLETADA' && sesion.estado !== 'SUSPENDIDA';

  return (
    <>
      <Stack.Screen options={{ title: `Sesión ${sesion.id.slice(0, 8)}…` }} />
      <ScrollView style={styles.root} contentContainerStyle={styles.content}>

        {/* Encabezado */}
        <Card style={styles.card}>
          <Card.Content>
            <View style={styles.estadoRow}>
              <Text variant="titleMedium" style={styles.instrumento}>
                {sesion.instrumento_nombre}
              </Text>
              <Chip
                mode="flat"
                style={{ backgroundColor: colorEstado + '22' }}
                textStyle={{ color: colorEstado }}
              >
                {sesion.estado_display}
              </Chip>
            </View>

            <Text variant="bodySmall" style={styles.meta}>
              Hogar: {sesion.hogar.slice(0, 8)}…
            </Text>
            <Text variant="bodySmall" style={styles.meta}>
              Inicio: {new Date(sesion.fecha_inicio).toLocaleDateString('es-CO')}
              {sesion.fecha_fin
                ? `  ·  Fin: ${new Date(sesion.fecha_fin).toLocaleDateString('es-CO')}`
                : ''}
            </Text>

            <Divider style={styles.divider} />

            <View style={styles.progresoRow}>
              <ProgressBar
                progress={sesion.porcentaje_completado / 100}
                style={styles.barra}
                color={colorEstado}
              />
              <Text variant="titleMedium" style={[styles.pct, { color: colorEstado }]}>
                {sesion.porcentaje_completado}%
              </Text>
            </View>
            <Text variant="labelSmall" style={styles.meta}>
              {sesion.total_respuestas} respuesta{sesion.total_respuestas !== 1 ? 's' : ''} guardada{sesion.total_respuestas !== 1 ? 's' : ''}
            </Text>
          </Card.Content>
        </Card>

        {/* Acciones */}
        {estaActiva && (
          <Card style={styles.card}>
            <Card.Content>
              <Button
                mode="contained"
                icon="clipboard-text"
                onPress={() =>
                  router.push({
                    pathname: '/(main)/formulario',
                    // Aquí se pasará la sesionId para que el formulario guarde respuestas
                  })
                }
              >
                Continuar formulario PAARI
              </Button>

              <Button
                mode="outlined"
                icon="check-circle"
                loading={finalizando}
                disabled={finalizando}
                style={styles.btnFinalizar}
                textColor="#2E7D32"
                onPress={confirmarFinalizar}
              >
                Finalizar sesión
              </Button>
            </Card.Content>
          </Card>
        )}

        {/* Respuestas guardadas */}
        {sesion.respuestas.length > 0 && (
          <Card style={styles.card}>
            <Card.Title
              title="Respuestas guardadas"
              subtitle={`${sesion.total_respuestas} en total`}
            />
            <Card.Content>
              {sesion.respuestas.map((r) => (
                <View key={r.id} style={styles.respuestaRow}>
                  <View style={styles.respuestaMeta}>
                    <Text variant="labelSmall" style={styles.codigoPregunta}>
                      [{r.pregunta_codigo}]
                    </Text>
                    <Text variant="bodySmall" style={styles.textoPregunta} numberOfLines={1}>
                      {r.pregunta_texto}
                    </Text>
                  </View>
                  <Text variant="bodySmall" style={styles.valor}>
                    {r.valor || '—'}
                  </Text>
                </View>
              ))}
            </Card.Content>
          </Card>
        )}

        {sesion.estado === 'COMPLETADA' && sesion.observaciones ? (
          <Card style={styles.card}>
            <Card.Title title="Observaciones" />
            <Card.Content>
              <Text variant="bodySmall">{sesion.observaciones}</Text>
            </Card.Content>
          </Card>
        ) : null}

        <Button
          mode="text"
          icon="chevron-left"
          onPress={() => router.back()}
          style={styles.volver}
        >
          Volver
        </Button>
      </ScrollView>
    </>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#F5F5F5' },
  content: { padding: 16, paddingBottom: 40 },
  centrado: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 32 },
  card: { marginBottom: 12, backgroundColor: '#FFFFFF' },
  estadoRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 },
  instrumento: { fontWeight: '700', flex: 1, marginRight: 8 },
  meta: { color: '#9E9E9E', marginBottom: 2 },
  divider: { marginVertical: 12 },
  progresoRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 4 },
  barra: { flex: 1, height: 10, borderRadius: 5, marginRight: 12 },
  pct: { fontWeight: '700', minWidth: 44 },
  btnFinalizar: { marginTop: 8, borderColor: '#2E7D32' },
  respuestaRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    paddingVertical: 5,
    borderBottomWidth: 1,
    borderBottomColor: '#F0F0F0',
  },
  respuestaMeta: { flex: 3 },
  codigoPregunta: { color: '#1565C0', fontFamily: 'monospace' },
  textoPregunta: { color: '#424242' },
  valor: { flex: 1, textAlign: 'right', color: '#212121', fontWeight: '600' },
  errorTxt: { color: '#C62828', marginBottom: 16 },
  volver: { marginTop: 8 },
});
