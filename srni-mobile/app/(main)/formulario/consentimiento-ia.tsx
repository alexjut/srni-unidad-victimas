/**
 * Pantalla de consentimiento para el asistente de voz IA.
 *
 * El encuestador debe leer el aviso de privacidad y marcar el checkbox
 * antes de poder activar el micrófono.
 *
 * Parámetros de ruta:
 *   sesionEncuestaId: UUID de la sesión activa
 */
import React, { useState } from 'react';
import { View, ScrollView, StyleSheet } from 'react-native';
import { Text, Checkbox, Button, Appbar, Divider, Banner } from 'react-native-paper';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useIAStore } from '../../../src/stores/iaStore';

export default function ConsentimientoIAScreen() {
  const { sesionEncuestaId } = useLocalSearchParams<{ sesionEncuestaId: string }>();
  const router = useRouter();
  const { activar } = useIAStore();

  const [acepta, setAcepta] = useState(false);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleActivar = async () => {
    if (!acepta || !sesionEncuestaId) return;
    setCargando(true);
    setError(null);
    try {
      await activar(sesionEncuestaId);
      router.back();
    } catch {
      setError('No se pudo registrar el consentimiento. Intenta de nuevo.');
    } finally {
      setCargando(false);
    }
  };

  return (
    <>
      <Appbar.Header>
        <Appbar.BackAction onPress={() => router.back()} />
        <Appbar.Content title="Consentimiento — Asistente IA" />
      </Appbar.Header>

      <ScrollView style={styles.container} contentContainerStyle={styles.content}>
        {error && (
          <Banner visible icon="alert" actions={[{ label: 'Cerrar', onPress: () => setError(null) }]}>
            {error}
          </Banner>
        )}

        <Text variant="titleMedium" style={styles.titulo}>
          Aviso de uso del asistente de voz
        </Text>

        <Text style={styles.parrafo}>
          El asistente de voz utiliza inteligencia artificial (Google Gemini) para
          interpretar sus respuestas orales y sugerir los valores correspondientes
          en el formulario PAARI.
        </Text>

        <Divider style={styles.divisor} />

        <Text variant="labelLarge" style={styles.subtitulo}>
          Condiciones de uso
        </Text>

        {CONDICIONES.map((c, i) => (
          <View key={i} style={styles.condicion}>
            <Text style={styles.bullet}>•</Text>
            <Text style={styles.condicionTexto}>{c}</Text>
          </View>
        ))}

        <Divider style={styles.divisor} />

        <View style={styles.checkRow}>
          <Checkbox
            status={acepta ? 'checked' : 'unchecked'}
            onPress={() => setAcepta(!acepta)}
          />
          <Text style={styles.checkLabel} onPress={() => setAcepta(!acepta)}>
            He leído y acepto las condiciones de uso del asistente de voz IA
            para esta sesión de caracterización.
          </Text>
        </View>

        <Button
          mode="contained"
          onPress={handleActivar}
          disabled={!acepta || cargando}
          loading={cargando}
          style={styles.boton}
          icon="microphone"
        >
          Activar asistente de voz
        </Button>

        <Button
          mode="text"
          onPress={() => router.back()}
          style={styles.botonCancelar}
        >
          Cancelar
        </Button>
      </ScrollView>
    </>
  );
}

const CONDICIONES = [
  'El audio se transcribe en el dispositivo y solo el texto transcrito se envía al servidor.',
  'El audio nunca se almacena en el dispositivo ni en los servidores de la Unidad.',
  'La clave de acceso a Gemini está en el servidor SRNI — el móvil no tiene acceso a Google.',
  'Cada llamada al asistente queda registrada en el log de auditoría del sistema.',
  'El asistente solo sugiere valores — el encuestador siempre toma la decisión final.',
  'Puede desactivar el asistente en cualquier momento durante la encuesta.',
  'El uso del asistente es opcional y no afecta la validez de la encuesta.',
];

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  content: { padding: 20, paddingBottom: 40 },
  titulo: { fontWeight: '700', marginBottom: 12, color: '#1A237E' },
  parrafo: { lineHeight: 22, color: '#333', marginBottom: 16 },
  subtitulo: { marginBottom: 10, color: '#333' },
  divisor: { marginVertical: 16 },
  condicion: { flexDirection: 'row', marginBottom: 8, alignItems: 'flex-start' },
  bullet: { marginRight: 8, color: '#1565C0', fontWeight: 'bold', marginTop: 1 },
  condicionTexto: { flex: 1, lineHeight: 20, color: '#444', fontSize: 14 },
  checkRow: {
    flexDirection: 'row', alignItems: 'flex-start', marginBottom: 24, gap: 8,
  },
  checkLabel: { flex: 1, lineHeight: 20, color: '#333', fontSize: 14, marginTop: 6 },
  boton: { marginBottom: 12, paddingVertical: 4 },
  botonCancelar: { marginBottom: 8 },
});
