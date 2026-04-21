/**
 * AudioRecorder — botón de micrófono con estado visual.
 *
 * Ciclo de vida:
 *   Inactivo → tap → grabando (indicador pulsante) → tap stop → procesando → ...
 *
 * El audio capturado con expo-av SE ELIMINA inmediatamente tras extraer el texto.
 * NUNCA se almacena en disco entre sesiones.
 *
 * Para este MVP, la "transcripción" se simula con un placeholder.
 * En producción se integraría expo-speech o Gemini multimodal via backend.
 */
import React, { useRef, useState } from 'react';
import { View, StyleSheet, Animated } from 'react-native';
import { IconButton, Text, ActivityIndicator } from 'react-native-paper';

interface AudioRecorderProps {
  /** ID de la pregunta activa — para etiquetar el log. */
  preguntaId: number;
  /** Callback cuando el texto ya está listo para enviar al backend. */
  onTextoListo: (texto: string) => void;
  /** Deshabilitar mientras hay sugerencia pendiente o procesando. */
  disabled?: boolean;
}

type EstadoGrabacion = 'idle' | 'grabando' | 'procesando';

export function AudioRecorder({ preguntaId, onTextoListo, disabled }: AudioRecorderProps) {
  const [estado, setEstado] = useState<EstadoGrabacion>('idle');
  const [segundos, setSegundos] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pulsoAnim = useRef(new Animated.Value(1)).current;

  // Animación de pulso durante grabación
  const iniciarPulso = () => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulsoAnim, { toValue: 1.3, duration: 600, useNativeDriver: true }),
        Animated.timing(pulsoAnim, { toValue: 1.0, duration: 600, useNativeDriver: true }),
      ]),
    ).start();
  };

  const detenerPulso = () => {
    pulsoAnim.stopAnimation();
    pulsoAnim.setValue(1);
  };

  const iniciarGrabacion = () => {
    setEstado('grabando');
    setSegundos(0);
    iniciarPulso();
    timerRef.current = setInterval(() => setSegundos((s) => s + 1), 1000);
  };

  const detenerGrabacion = async () => {
    if (timerRef.current) clearInterval(timerRef.current);
    detenerPulso();
    setEstado('procesando');

    // En producción: detener expo-av Recording, leer URI, transcribir.
    // MVP: solicitar texto al encuestador mediante un placeholder corto.
    // La integración real usa expo-av + Speech-to-Text.
    const textoSimulado = `[Respuesta oral — pregunta ${preguntaId}]`;
    onTextoListo(textoSimulado);
    setEstado('idle');
    setSegundos(0);
  };

  const handlePress = () => {
    if (estado === 'idle') {
      iniciarGrabacion();
    } else if (estado === 'grabando') {
      detenerGrabacion();
    }
    // Si 'procesando', no hace nada — espera respuesta del backend
  };

  const getIcono = () => {
    if (estado === 'grabando') return 'stop-circle';
    return 'microphone';
  };

  const getColor = () => {
    if (estado === 'grabando') return '#D32F2F';
    return '#1565C0';
  };

  if (estado === 'procesando') {
    return (
      <View style={styles.row}>
        <ActivityIndicator size="small" color="#1565C0" />
        <Text style={styles.label}>Enviando al asistente…</Text>
      </View>
    );
  }

  return (
    <View style={styles.row}>
      <Animated.View style={{ transform: [{ scale: pulsoAnim }] }}>
        <IconButton
          icon={getIcono()}
          iconColor={getColor()}
          size={28}
          onPress={handlePress}
          disabled={disabled}
          style={estado === 'grabando' ? styles.btnGrabando : styles.btn}
        />
      </Animated.View>
      {estado === 'grabando' ? (
        <Text style={[styles.label, { color: '#D32F2F' }]}>
          Grabando {segundos}s — toca para detener
        </Text>
      ) : (
        <Text style={styles.label}>Dictar respuesta</Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 4,
  },
  btn: {
    margin: 0,
  },
  btnGrabando: {
    margin: 0,
    backgroundColor: '#FFEBEE',
    borderRadius: 20,
  },
  label: {
    fontSize: 13,
    color: '#555',
    marginLeft: 4,
  },
});
