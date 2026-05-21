/**
 * Pantalla de inicio de sesión — diseño profesional GOV.CO + biometría.
 * Inspirado en apps bancarias institucionales.
 */
import { useState, useEffect } from 'react';
import {
  View, StyleSheet, KeyboardAvoidingView,
  Platform, ScrollView, StatusBar, Pressable,
} from 'react-native';
import { Text, TextInput, HelperText } from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import * as SecureStore from 'expo-secure-store';
import * as LocalAuthentication from 'expo-local-authentication';
import { useAuthStore } from '../../src/stores/authStore';
import { GovButton } from '../../src/components/GovButton';
import { GOV, SPACING, RADIUS, SHADOW, FONT } from '../../src/theme/govTheme';

// ── Regiones decorativas ──────────────────────────────────────────────────────

const REGIONES = [
  { nombre: 'Pacífico',  icono: 'waves',          color: '#01579B', bg: '#003A6B' },
  { nombre: 'Caribe',    icono: 'palm-tree',       color: '#E8F5E9', bg: '#00695C' },
  { nombre: 'Andes',     icono: 'mountain',        color: '#FFF8E1', bg: '#4E342E' },
  { nombre: 'Amazonia',  icono: 'leaf',            color: '#F1F8E9', bg: '#2E7D32' },
  { nombre: 'Orinoquía', icono: 'nature',          color: '#FFF3E0', bg: '#827717' },
  { nombre: 'Insular',   icono: 'island',          color: '#E1F5FE', bg: '#0277BD' },
];

// ── Pantalla ──────────────────────────────────────────────────────────────────

export default function LoginScreen() {
  const { login, loginBiometrico, cargando, error, limpiarError } = useAuthStore();
  const [codigo, setCodigo] = useState('');
  const [password, setPassword] = useState('');
  const [verPassword, setVerPassword] = useState(false);
  const [biometricoListo, setBiometricoListo] = useState(false);
  const insets = useSafeAreaInsets();

  useEffect(() => {
    async function verificar() {
      try {
        const hw = await LocalAuthentication.hasHardwareAsync();
        if (!hw) return;
        const enrolled = await LocalAuthentication.isEnrolledAsync();
        if (!enrolled) return;
        const habilitado = await SecureStore.getItemAsync('biometrico_habilitado');
        const token = await SecureStore.getItemAsync('refresh_token');
        setBiometricoListo(habilitado === 'true' && !!token);
      } catch { /* silencioso */ }
    }
    verificar();
  }, []);

  async function handleLogin() {
    if (!codigo.trim() || !password) return;
    limpiarError();
    try {
      await login(codigo, password);
    } catch { /* error ya en store */ }
  }

  async function handleBiometrico() {
    limpiarError();
    try {
      await loginBiometrico();
    } catch { /* error ya en store */ }
  }

  return (
    <>
      <StatusBar backgroundColor="transparent" translucent barStyle="light-content" />
      <KeyboardAvoidingView
        style={styles.root}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        {/* ── Hero con gradiente ── */}
        <LinearGradient
          colors={['#00234E', '#003A80', '#1565C0']}
          style={[styles.hero, { paddingTop: insets.top + 8 }]}
        >
          {/* Franja GOV.CO */}
          <View style={styles.govStripe}>
            <Text style={styles.govText}>GOV.CO</Text>
          </View>

          {/* Regiones decorativas */}
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.regionesFila}
            style={styles.regionesScroll}
          >
            {REGIONES.map((r) => (
              <View key={r.nombre} style={[styles.regionTile, { backgroundColor: r.bg }]}>
                <MaterialCommunityIcons name={r.icono as any} size={16} color="#FFFFFF" />
                <Text style={styles.regionNombre}>{r.nombre}</Text>
              </View>
            ))}
          </ScrollView>

          {/* Logo institucional */}
          <View style={styles.logoWrap}>
            <View style={styles.escudoCirculo}>
              <MaterialCommunityIcons name="shield-account" size={44} color="#FFFFFF" />
            </View>
            <Text style={styles.appTitle}>SRNI</Text>
            <Text style={styles.appSubtitulo}>Sistema de Caracterización de Víctimas</Text>
            <View style={styles.entidadBadge}>
              <MaterialCommunityIcons name="domain" size={12} color={GOV.amarillo} />
              <Text style={styles.entidadTxt}>Unidad para las Víctimas — Colombia</Text>
            </View>
          </View>
        </LinearGradient>

        {/* ── Card de formulario ── */}
        <ScrollView
          style={styles.cardScroll}
          contentContainerStyle={styles.cardContenido}
          keyboardShouldPersistTaps="handled"
          bounces={false}
        >
          <View style={styles.card}>
            <Text style={styles.cardTitulo}>Bienvenido/a</Text>
            <Text style={styles.cardSubtitulo}>Ingresa tus credenciales institucionales</Text>

            {/* Usuario */}
            <TextInput
              label="Código de usuario"
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

            {/* Contraseña */}
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
              <HelperText type="error" visible style={styles.errorTxt}>
                {error}
              </HelperText>
            ) : null}

            {/* Botón principal */}
            <View style={styles.btnWrap}>
              <GovButton
                label="Ingresar"
                onPress={handleLogin}
                loading={cargando}
                disabled={!codigo.trim() || !password}
                icon="login"
              />
            </View>

            {/* Separador biometría */}
            {biometricoListo && (
              <>
                <View style={styles.separador}>
                  <View style={styles.separadorLinea} />
                  <Text style={styles.separadorTxt}>o ingresa con</Text>
                  <View style={styles.separadorLinea} />
                </View>

                {/* Botón huella — círculo prominente estilo banca moderna */}
                <Pressable
                  onPress={handleBiometrico}
                  disabled={cargando}
                  style={({ pressed }) => [
                    styles.btnBio,
                    cargando && styles.btnBioDeshabilitado,
                  ]}
                  accessibilityLabel="Acceder con huella digital"
                  accessibilityRole="button"
                >
                  {({ pressed }) => (
                    <>
                      <View style={[styles.btnBioCirculo, pressed && styles.btnBioCirculoPresionado]}>
                        <MaterialCommunityIcons name="fingerprint" size={38} color="#FFFFFF" />
                      </View>
                      <Text style={styles.btnBioTxt}>Huella digital</Text>
                    </>
                  )}
                </Pressable>
              </>
            )}
          </View>

          {/* Pie institucional */}
          <Text style={styles.pie}>
            Sistema protegido — Ley 1581 de 2012 · Datos de víctimas confidenciales
          </Text>
        </ScrollView>
      </KeyboardAvoidingView>
    </>
  );
}

// ── Estilos ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: '#1565C0',
  },

  // Hero
  hero: {
    paddingBottom: SPACING.lg,
  },
  govStripe: {
    height: 28,
    backgroundColor: GOV.amarillo,
    justifyContent: 'center',
    paddingHorizontal: SPACING.md,
  },
  govText: {
    fontSize: 11,
    fontWeight: '700',
    color: GOV.azulOscuro,
    letterSpacing: 1.5,
  },

  // Regiones decorativas
  regionesScroll: {
    marginTop: SPACING.md,
    marginBottom: SPACING.sm,
  },
  regionesFila: {
    paddingHorizontal: SPACING.md,
    gap: SPACING.xs,
  },
  regionTile: {
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    width: 68,
    height: 56,
    borderRadius: RADIUS.sm,
    gap: 2,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.15)',
  },
  regionNombre: {
    fontSize: 9,
    color: '#FFFFFF',
    fontWeight: '600',
    letterSpacing: 0.3,
  },

  // Logo
  logoWrap: {
    alignItems: 'center',
    paddingTop: SPACING.md,
    paddingBottom: SPACING.sm,
  },
  escudoCirculo: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: 'rgba(255,255,255,0.15)',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: SPACING.sm,
    borderWidth: 2,
    borderColor: 'rgba(255,255,255,0.4)',
  },
  appTitle: {
    fontSize: 32,
    fontWeight: '800',
    color: '#FFFFFF',
    letterSpacing: 4,
    marginBottom: 4,
  },
  appSubtitulo: {
    fontSize: 13,
    color: 'rgba(255,255,255,0.85)',
    textAlign: 'center',
    paddingHorizontal: SPACING.xl,
    marginBottom: SPACING.sm,
    lineHeight: 18,
  },
  entidadBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: 'rgba(0,0,0,0.25)',
    paddingHorizontal: SPACING.sm,
    paddingVertical: 4,
    borderRadius: RADIUS.pill,
  },
  entidadTxt: {
    fontSize: 11,
    color: GOV.amarillo,
    fontWeight: '600',
    letterSpacing: 0.3,
  },

  // Card formulario
  cardScroll: {
    flex: 1,
    backgroundColor: GOV.fondoApp,
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    marginTop: -2,
  },
  cardContenido: {
    padding: SPACING.md,
    paddingBottom: SPACING.xxl,
  },
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: RADIUS.lg,
    padding: SPACING.lg,
    ...SHADOW.card,
    marginTop: SPACING.md,
    borderWidth: 1,
    borderColor: GOV.borde,
  },
  cardTitulo: {
    fontSize: 22,
    fontWeight: '700',
    color: GOV.azulOscuro,
    marginBottom: 4,
  },
  cardSubtitulo: {
    ...FONT.small,
    color: GOV.textoS,
    marginBottom: SPACING.md,
  },
  input: {
    marginBottom: SPACING.sm,
    backgroundColor: '#FFFFFF',
  },
  errorTxt: {
    marginBottom: SPACING.xs,
  },
  btnWrap: {
    marginTop: SPACING.xs,
  },

  // Separador
  separador: {
    flexDirection: 'row',
    alignItems: 'center',
    marginVertical: SPACING.md,
    gap: SPACING.sm,
  },
  separadorLinea: {
    flex: 1,
    height: 1,
    backgroundColor: GOV.borde,
  },
  separadorTxt: {
    ...FONT.caption,
    color: GOV.textoT,
    fontWeight: '500',
  },

  // Botón huella — Bancolombia style: círculo grande con ícono prominent
  btnBio: {
    alignItems: 'center',
    justifyContent: 'center',
    gap: SPACING.xs,
    paddingVertical: SPACING.sm,
  },
  btnBioCirculo: {
    width: 68,
    height: 68,
    borderRadius: 34,
    backgroundColor: GOV.azul,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: SPACING.xs,
    shadowColor: GOV.azul,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.35,
    shadowRadius: 8,
    elevation: 8,
  },
  btnBioCirculoPresionado: {
    backgroundColor: GOV.azulOscuro,
    elevation: 4,
  },
  btnBioDeshabilitado: {
    opacity: 0.4,
  },
  btnBioTxt: {
    fontSize: 13,
    fontWeight: '600',
    color: GOV.azul,
    letterSpacing: 0.3,
  },

  // Pie
  pie: {
    ...FONT.caption,
    color: GOV.textoT,
    textAlign: 'center',
    marginTop: SPACING.lg,
    paddingHorizontal: SPACING.md,
    lineHeight: 16,
  },
});
