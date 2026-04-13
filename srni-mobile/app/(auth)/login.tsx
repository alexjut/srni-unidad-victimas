import { useState } from 'react';
import { View, StyleSheet, KeyboardAvoidingView, Platform, ScrollView } from 'react-native';
import {
  TextInput,
  Button,
  Text,
  HelperText,
  Surface,
  ActivityIndicator,
} from 'react-native-paper';
import { useAuthStore } from '../../src/stores/authStore';

export default function LoginScreen() {
  const { login, cargando, error, limpiarError } = useAuthStore();
  const [codigo, setCodigo] = useState('');
  const [password, setPassword] = useState('');
  const [verPassword, setVerPassword] = useState(false);

  async function handleLogin() {
    if (!codigo.trim() || !password) return;
    limpiarError();
    await login(codigo, password);
  }

  return (
    <KeyboardAvoidingView
      style={styles.root}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
        <View style={styles.header}>
          <Text variant="headlineMedium" style={styles.titulo}>
            SRNI
          </Text>
          <Text variant="bodyMedium" style={styles.subtitulo}>
            Sistema de Caracterización de Víctimas{'\n'}Unidad para las Víctimas
          </Text>
        </View>

        <Surface style={styles.card} elevation={2}>
          <Text variant="titleMedium" style={styles.cardTitulo}>
            Iniciar sesión
          </Text>

          <TextInput
            label="Código de usuario"
            value={codigo}
            onChangeText={setCodigo}
            autoCapitalize="characters"
            autoCorrect={false}
            returnKeyType="next"
            left={<TextInput.Icon icon="account" />}
            style={styles.input}
          />

          <TextInput
            label="Contraseña"
            value={password}
            onChangeText={setPassword}
            secureTextEntry={!verPassword}
            returnKeyType="done"
            onSubmitEditing={handleLogin}
            left={<TextInput.Icon icon="lock" />}
            right={
              <TextInput.Icon
                icon={verPassword ? 'eye-off' : 'eye'}
                onPress={() => setVerPassword((v) => !v)}
              />
            }
            style={styles.input}
          />

          {error ? (
            <HelperText type="error" visible style={styles.error}>
              {error}
            </HelperText>
          ) : null}

          <Button
            mode="contained"
            onPress={handleLogin}
            disabled={cargando || !codigo.trim() || !password}
            style={styles.boton}
            contentStyle={styles.botonContent}
          >
            {cargando ? <ActivityIndicator color="#fff" size={20} /> : 'Ingresar'}
          </Button>
        </Surface>

        <Text variant="bodySmall" style={styles.version}>
          SRNI v1.0.0 — Uso exclusivo institucional
        </Text>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#1565C0' },
  scroll: { flexGrow: 1, justifyContent: 'center', padding: 24 },
  header: { alignItems: 'center', marginBottom: 32 },
  titulo: { color: '#FFFFFF', fontWeight: '700', fontSize: 36 },
  subtitulo: { color: '#BBDEFB', textAlign: 'center', marginTop: 8 },
  card: { borderRadius: 12, padding: 24, backgroundColor: '#FFFFFF' },
  cardTitulo: { marginBottom: 16, fontWeight: '600', color: '#1565C0' },
  input: { marginBottom: 12, backgroundColor: '#FAFAFA' },
  error: { marginBottom: 8 },
  boton: { marginTop: 8, borderRadius: 8 },
  botonContent: { paddingVertical: 6 },
  version: { textAlign: 'center', color: '#90CAF9', marginTop: 32 },
});
