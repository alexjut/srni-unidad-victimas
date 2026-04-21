/**
 * SugerenciaIA — card con valor sugerido por el asistente IA.
 *
 * Muestra:
 *   - El valor sugerido
 *   - Indicador de confianza (barra de color)
 *   - Botón [✓ Aceptar] y [✗ Rechazar]
 *
 * El encuestador siempre tiene la última palabra.
 */
import React from 'react';
import { View, StyleSheet } from 'react-native';
import { Card, Text, Button, Chip } from 'react-native-paper';
import type { MapearAudioResponse } from '../api/ia';

interface SugerenciaIAProps {
  sugerencia: MapearAudioResponse;
  onAceptar: (valor: string) => void;
  onRechazar: () => void;
}

export function SugerenciaIA({ sugerencia, onAceptar, onRechazar }: SugerenciaIAProps) {
  const confianzaPorcentaje = Math.round(sugerencia.confianza * 100);
  const colorConfianza =
    sugerencia.confianza >= 0.9
      ? '#2E7D32'
      : sugerencia.confianza >= 0.6
      ? '#F57F17'
      : '#C62828';

  return (
    <Card style={styles.card} elevation={2}>
      <Card.Content>
        <View style={styles.header}>
          <Text variant="labelMedium" style={styles.titulo}>
            Sugerencia del asistente IA
          </Text>
          <Chip
            compact
            style={[styles.chip, { backgroundColor: colorConfianza + '22' }]}
            textStyle={{ color: colorConfianza, fontSize: 11 }}
          >
            {confianzaPorcentaje}% confianza
          </Chip>
        </View>

        <Text variant="titleMedium" style={styles.valorSugerido}>
          {sugerencia.sugerencia || '(sin valor)'}
        </Text>

        <Text variant="bodySmall" style={styles.modelo}>
          Modelo: {sugerencia.modelo}
        </Text>
      </Card.Content>

      <Card.Actions style={styles.acciones}>
        <Button
          mode="contained"
          compact
          onPress={() => onAceptar(sugerencia.sugerencia)}
          style={styles.btnAceptar}
          icon="check"
        >
          Aceptar
        </Button>
        <Button
          mode="outlined"
          compact
          onPress={onRechazar}
          style={styles.btnRechazar}
          icon="close"
        >
          Rechazar
        </Button>
      </Card.Actions>
    </Card>
  );
}

const styles = StyleSheet.create({
  card: {
    marginTop: 8,
    marginBottom: 4,
    backgroundColor: '#E8F5E9',
    borderLeftWidth: 4,
    borderLeftColor: '#2E7D32',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  titulo: {
    color: '#1B5E20',
    fontWeight: '600',
  },
  chip: {
    height: 24,
  },
  valorSugerido: {
    fontWeight: 'bold',
    color: '#1B5E20',
    marginBottom: 4,
  },
  modelo: {
    color: '#888',
    fontSize: 11,
  },
  acciones: {
    justifyContent: 'flex-start',
    paddingTop: 0,
    gap: 8,
  },
  btnAceptar: {
    backgroundColor: '#2E7D32',
  },
  btnRechazar: {
    borderColor: '#C62828',
  },
});
