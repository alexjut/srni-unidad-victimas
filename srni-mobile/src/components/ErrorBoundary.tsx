/**
 * ErrorBoundary global — Sprint 17.
 *
 * Captura errores no manejados de React y los muestra en pantalla con:
 *  - Mensaje + stack visible
 *  - Botón "Copiar al portapapeles" para mandar el error a soporte
 *  - Botón "Reintentar" que resetea el boundary
 *  - Envío automático al backend (/api/_debug/log/) para que el
 *    desarrollador lo vea en la terminal del Django runserver
 *
 * Se envuelve en el RootLayout (app/_layout.tsx).
 *
 * IMPORTANTE: ErrorBoundary NO captura errores async, errores de event
 * handlers, ni SSR. Para esos casos usa reportarExcepcion() del servicio.
 */
import React, { Component, ReactNode } from 'react';
import { View, ScrollView, StyleSheet, Pressable, TextInput } from 'react-native';
import { Text } from 'react-native-paper';
import { reportarError } from '../services/errorReporter';

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
  info: { componentStack?: string | null } | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null, info: null };

  static getDerivedStateFromError(error: Error): State {
    return { error, info: null };
  }

  componentDidCatch(error: Error, info: { componentStack?: string | null }): void {
    this.setState({ info });
    // Envío al backend — silencioso
    reportarError({
      nivel: 'error',
      mensaje: error.message,
      stack: `${error.stack}\n\n--- componentStack ---\n${info.componentStack ?? ''}`,
      pantalla: '[ErrorBoundary]',
    });
  }

  reset = (): void => {
    this.setState({ error: null, info: null });
  };

  render(): ReactNode {
    if (!this.state.error) return this.props.children;

    const error = this.state.error;
    const info = this.state.info;
    const textoCompleto = [
      `Error: ${error.message}`,
      '',
      'Stack:',
      error.stack ?? '(sin stack)',
      '',
      'Component Stack:',
      info?.componentStack ?? '(sin component stack)',
    ].join('\n');

    return (
      <View style={styles.root}>
        <View style={styles.header}>
          <Text style={styles.headerTxt}>⚠️ Se produjo un error</Text>
          <Text style={styles.headerSubTxt}>
            Mantén presionado el texto abajo para copiar y enviarlo a soporte.
            También se envió al backend (consola del servidor Django).
          </Text>
        </View>
        <ScrollView contentContainerStyle={styles.scroll}>
          <Text style={styles.label}>Mensaje:</Text>
          <Text selectable style={styles.mensaje}>{error.message}</Text>

          <Text style={styles.label}>Texto completo (mantén presionado para copiar):</Text>
          <TextInput
            value={textoCompleto}
            editable={false}
            multiline
            scrollEnabled
            style={styles.stackInput}
          />
        </ScrollView>
        <View style={styles.footer}>
          <Pressable style={styles.btn} onPress={this.reset}>
            <Text style={styles.btnTxt}>Reintentar</Text>
          </Pressable>
        </View>
      </View>
    );
  }
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#FFEBEE' },
  header: {
    backgroundColor: '#D32F2F',
    paddingVertical: 16,
    paddingHorizontal: 16,
    paddingTop: 48,
  },
  headerTxt: {
    color: '#FFFFFF',
    fontSize: 18,
    fontWeight: '700',
  },
  headerSubTxt: {
    color: '#FFCDD2',
    fontSize: 12,
    marginTop: 4,
    lineHeight: 16,
  },
  scroll: { padding: 16, paddingBottom: 24 },
  label: {
    fontSize: 12,
    fontWeight: '700',
    color: '#B71C1C',
    marginTop: 12,
    marginBottom: 4,
    textTransform: 'uppercase',
  },
  mensaje: {
    fontSize: 14,
    color: '#1A1A1A',
    fontWeight: '500',
    backgroundColor: '#FFFFFF',
    padding: 10,
    borderRadius: 6,
  },
  stackInput: {
    fontFamily: 'monospace',
    fontSize: 11,
    color: '#444',
    backgroundColor: '#FFFFFF',
    padding: 10,
    borderRadius: 6,
    lineHeight: 16,
    minHeight: 240,
    textAlignVertical: 'top',
    borderWidth: 1,
    borderColor: '#FFCDD2',
  },
  footer: {
    flexDirection: 'row',
    gap: 8,
    padding: 16,
    borderTopWidth: 1,
    borderTopColor: '#FFCDD2',
    backgroundColor: '#FFFFFF',
  },
  btn: {
    flex: 1,
    backgroundColor: '#D32F2F',
    paddingVertical: 12,
    borderRadius: 6,
    alignItems: 'center',
  },
  btnTxt: { color: '#FFFFFF', fontWeight: '700', fontSize: 14 },
});
