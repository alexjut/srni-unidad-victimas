/**
 * Pantalla de inicio de sesión — estilo GOV.CO institucional.
 */
import { useState } from 'react';
import {
  View, StyleSheet, KeyboardAvoidingView,
  Platform, ScrollView, StatusBar,
} from 'react-native';
import { Text, TextInput, HelperText } from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useAuthStore } from '../../src/stores/authStore';
import { GovButton } from '../../src/components/GovButton';
import { GOV, SPACING, RADIUS, SHADOW, FONT } from '../../src/theme/govTheme';

export default function LoginScreen() {
  const { login, cargando, error, limpiarError } = useAuthStore();
  const [codigo, setCodigo] = useState('');
  const [password, setPassword] = useState('');
  const [verPassword, setVerPassword] = useState(false);
  const insets = useSafeAreaInsets();

  async function handleLogin() {
    if (!codigo.trim() || !password) return;
    limpiarError();
    await login(codigo, password);
  }

  return (
    <>
      <StatusBar backgroundColor={GOV.amarillo} barStyle="dark-content" />
      <KeyboardAvoidingView
        style={styles.root}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        {/* Franja GOV.CO amarilla */}
        <View style={[styles.govStripe, { paddingTop: insets.top }]}>
          <Text style={styles.govText}>GOV.CO</Text>
        </View>

        <ScrollView
          contentContainerStyle={styles.scroll}
          keyboardShouldPersistTaps="handled"
        >
          {/* Logo institucional */}
          <View style={styles.logoWrap}>
            <View style={styles.logoCircle}>
              <MaterialCommunityIcons
                name="shield-account"
                size={48}
                color={GOV.azul}
              />
            </View>
            <Text style={styles.appTitle}>SRNI</Text>
            <Text style={styles.appSubtitle}>
              Sistema de Caracterización de Víctimas
            </Text>
            <Text style={styles.entidad}>
              Unidad para las Víctimas
            </Text>
          </View>

          {/* Card de login */}
          <View style={styles.card}>
            <Text style={styles.cardTitle}>Iniciar sesión</Text>
            <Text style={styles.cardSubtitle}>Ingresa tus credenciales institucionales</Text>

            <TextInput
              label="Usuario"
              value={codigo}
              onChangeText={setCodigo}
              autoCapitalize="characters"
              autoCorrect={false}
              returnKeyType="next"
              left={<TextInput.Icon icon="account-circle-outline" color={GOV.azul} />}
              style={styles.input}
              outlineStyle={{ borderRadius: RADIUS.sm }}
              mode="outlined"
              activeOutlineColor={GOV.azul}
              accessibilityLabel="Código de usuario"
            />

            <TextInput
              label="Contraseña"
              value={password}
              onChangeText={setPassword}
              secureTextEntry={!verPassword}
              returnKeyType="done"
              onSubmitEditing={handleLogin}
              left={<TextInput.Icon icon="lock-outline" color={GOV.azul} />}
              right={
                <TextInput.Icon
                  icon={verPassword ? 'eye-off-outline' : 'eye-outline'}
                  color={GOV.textoS}
                  onPress={() => setVerPassword((v) => !v)}
                />
              }
              style={styles.input}
              outlineStyle={{ borderRadius: RADIUS.sm }}
              mode="outlined"
              activeOutlineColor={GOV.azul}
              accessibilityLabel="Contraseña"
            />

            {error ? (
              <HelperText type="error" visible style={styles.errorText}>
                {error}
              </HelperText>
            ) : null}

            <View style={styles.btnWrap}>
              <GovButton
                label="Ingresar"
                onPress={handleLogin}
                loading={cargando}
                disabled={!codigo.trim() || !password}
                icon="login"
              />
            </View>
          </View>

          {/* Pie de página */}
          <View style={styles.footer}>
            <Text style={styles.footerText}>
              Unidad para la Atención y Reparación Integral a las Víctimas
            </Text>
            <Text style={styles.footerVersion}>SRNI v1.0.0 — Uso exclusivo institucional</Text>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: '#FFFFFF',
  },
  govStripe: {
    backgroundColor: GOV.amarillo,
    paddingHorizontal: SPACING.md,
    paddingBottom: 8,
    justifyContent: 'flex-end',
    minHeight: 36,
  },
  govText: {
    fontSize: 11,
    fontWeight: '700',
    color: GOV.azulOscuro,
    letterSpacing: 1.5,
  },
  scroll: {
    flexGrow: 1,
    paddingHorizontal: SPACING.md,
    paddingBottom: SPACING.xl,
  },
  logoWrap: {
    alignItems: 'center',
    paddingTop: SPACING.xl,
    paddingBottom: SPACING.lg,
  },
  logoCircle: {
    width: 88,
    height: 88,
    borderRadius: 44,
    backgroundColor: GOV.azulTenue,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: SPACING.md,
    borderWidth: 2,
    borderColor: GOV.azul,
  },
  appTitle: {
    fontSize: 28,
    fontWeight: '800',
    color: GOV.azulOscuro,
    letterSpacing: 2,
    marginBottom: 4,
  },
  appSubtitle: {
    ...FONT.body,
    color: GOV.textoS,
    textAlign: 'center',
    marginBottom: 4,
  },
  entidad: {
    ...FONT.small,
    color: GOV.azul,
    fontWeight: '600',
    textAlign: 'center',
  },
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: RADIUS.md,
    padding: SPACING.lg,
    ...SHADOW.card,
    borderWidth: 1,
    borderColor: GOV.borde,
  },
  cardTitle: {
    ...FONT.h2,
    marginBottom: 4,
  },
  cardSubtitle: {
    ...FONT.small,
    color: GOV.textoS,
    marginBottom: SPACING.md,
  },
  input: {
    marginBottom: SPACING.sm,
    backgroundColor: '#FFFFFF',
  },
  errorText: {
    marginBottom: SPACING.xs,
  },
  btnWrap: {
    marginTop: SPACING.xs,
  },
  footer: {
    alignItems: 'center',
    paddingTop: SPACING.xl,
    gap: 4,
  },
  footerText: {
    ...FONT.caption,
    color: GOV.textoT,
    textAlign: 'center',
  },
  footerVersion: {
    ...FONT.caption,
    color: GOV.borde,
    textAlign: 'center',
  },
});
