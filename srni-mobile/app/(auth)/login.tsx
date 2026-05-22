/**
 * Pantalla de inicio de sesión — diseño profesional GOV.CO + biometría.
 * Carrusel de regiones colombianas con gradientes representativos.
 * Para usar fotos reales: reemplazar <LinearGradient> por <ImageBackground source={require(...)} />
 */
import { useState, useEffect, useRef } from 'react';
import {
  View, StyleSheet, KeyboardAvoidingView,
  Platform, ScrollView, StatusBar, Pressable,
  FlatList, Dimensions,
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

const { width: SW } = Dimensions.get('window');
const CAROUSEL_H = 170;
const INTERVALO_MS = 3200;

// ── Regiones colombianas — gradientes representativos ────────────────────────
// Para fotos reales: agregar campo `imagen: require('../../assets/regiones/pacifico.jpg')`
// y en RegionSlide usar <ImageBackground source={r.imagen}> en lugar del <LinearGradient>

const REGIONES = [
  {
    nombre: 'Pacífico',
    subtitulo: 'Costa, selva y biodiversidad',
    icono: 'waves' as const,
    gradiente: ['#003B5C', '#006994', '#00B4D8'] as const,
    acento: '#48CAE4',
  },
  {
    nombre: 'Caribe',
    subtitulo: 'Mar, playas y cultura vallenata',
    icono: 'palm-tree' as const,
    gradiente: ['#7B2D00', '#C1440E', '#F4A261'] as const,
    acento: '#FFD166',
  },
  {
    nombre: 'Andes',
    subtitulo: 'Montañas, café y páramos',
    icono: 'image-filter-hdr' as const,
    gradiente: ['#1A3A1A', '#2D6A4F', '#74C69D'] as const,
    acento: '#B7E4C7',
  },
  {
    nombre: 'Amazonia',
    subtitulo: 'Selva tropical y grandes ríos',
    icono: 'leaf' as const,
    gradiente: ['#0A2E0A', '#1B4332', '#52B788'] as const,
    acento: '#95D5B2',
  },
  {
    nombre: 'Orinoquía',
    subtitulo: 'Llanos orientales y sabanas',
    icono: 'grass' as const,
    gradiente: ['#4A2800', '#8B5E00', '#DAA520'] as const,
    acento: '#F2D06B',
  },
  {
    nombre: 'Insular',
    subtitulo: 'San Andrés, Providencia y Santa Catalina',
    icono: 'island' as const,
    gradiente: ['#001F5B', '#023E8A', '#48CAE4'] as const,
    acento: '#90E0EF',
  },
];

// ── Slide individual del carrusel ─────────────────────────────────────────────

function RegionSlide({ region }: { region: typeof REGIONES[0] }) {
  return (
    <LinearGradient
      colors={region.gradiente}
      start={{ x: 0, y: 0 }}
      end={{ x: 1, y: 1 }}
      style={styles.slide}
    >
      {/* Patrón de puntos decorativos */}
      <View style={styles.slidePatron} />

      <View style={styles.slideContenido}>
        <View style={[styles.slideIconoCirculo, { borderColor: region.acento + '60' }]}>
          <MaterialCommunityIcons name={region.icono} size={32} color={region.acento} />
        </View>
        <Text style={styles.slideNombre}>{region.nombre}</Text>
        <Text style={styles.slideSubtitulo}>{region.subtitulo}</Text>
      </View>

      {/* Etiqueta Colombia */}
      <View style={styles.slideBadge}>
        <MaterialCommunityIcons name="map-marker" size={10} color={region.acento} />
        <Text style={[styles.slideBadgeTxt, { color: region.acento }]}>Colombia</Text>
      </View>
    </LinearGradient>
  );
}

// ── Pantalla principal ────────────────────────────────────────────────────────

export default function LoginScreen() {
  const { login, loginBiometrico, cargando, error, limpiarError } = useAuthStore();
  const [codigo, setCodigo] = useState('');
  const [password, setPassword] = useState('');
  const [verPassword, setVerPassword] = useState(false);
  const [biometricoListo, setBiometricoListo] = useState(false);
  const [regionActiva, setRegionActiva] = useState(0);
  const flatListRef = useRef<FlatList>(null);
  const insets = useSafeAreaInsets();

  // Verificar biometría disponible
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

  // Auto-scroll del carrusel
  useEffect(() => {
    const timer = setInterval(() => {
      setRegionActiva((prev) => {
        const next = (prev + 1) % REGIONES.length;
        flatListRef.current?.scrollToIndex({ index: next, animated: true });
        return next;
      });
    }, INTERVALO_MS);
    return () => clearInterval(timer);
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
        {/* ── Hero con gradiente de fondo ── */}
        <LinearGradient
          colors={['#00234E', '#003A80', '#1565C0']}
          style={[styles.hero, { paddingTop: insets.top }]}
        >
          {/* Franja GOV.CO */}
          <View style={styles.govStripe}>
            <Text style={styles.govText}>GOV.CO</Text>
          </View>

          {/* Carrusel de regiones */}
          <FlatList
            ref={flatListRef}
            data={REGIONES}
            keyExtractor={(r) => r.nombre}
            horizontal
            pagingEnabled
            showsHorizontalScrollIndicator={false}
            scrollEnabled={true}
            onMomentumScrollEnd={(e) => {
              const idx = Math.round(e.nativeEvent.contentOffset.x / SW);
              setRegionActiva(idx);
            }}
            renderItem={({ item }) => <RegionSlide region={item} />}
            style={styles.flatList}
            getItemLayout={(_, index) => ({
              length: SW, offset: SW * index, index,
            })}
          />

          {/* Dots de paginación */}
          <View style={styles.dots}>
            {REGIONES.map((_, i) => (
              <Pressable
                key={i}
                onPress={() => {
                  flatListRef.current?.scrollToIndex({ index: i, animated: true });
                  setRegionActiva(i);
                }}
                style={[styles.dot, i === regionActiva && styles.dotActivo]}
              />
            ))}
          </View>

          {/* Logo institucional */}
          <View style={styles.logoWrap}>
            <View style={styles.escudoCirculo}>
              <MaterialCommunityIcons name="shield-account" size={36} color="#FFFFFF" />
            </View>
            <Text style={styles.appTitle}>SRNI</Text>
            <Text style={styles.appSubtitulo}>Sistema de Caracterización de Víctimas</Text>
            <View style={styles.entidadBadge}>
              <MaterialCommunityIcons name="domain" size={11} color={GOV.amarillo} />
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

            <View style={styles.btnWrap}>
              <GovButton
                label="Ingresar"
                onPress={handleLogin}
                loading={cargando}
                disabled={!codigo.trim() || !password}
                icon="login"
              />
            </View>

            {biometricoListo && (
              <>
                <View style={styles.separador}>
                  <View style={styles.separadorLinea} />
                  <Text style={styles.separadorTxt}>o ingresa con</Text>
                  <View style={styles.separadorLinea} />
                </View>

                <Pressable
                  onPress={handleBiometrico}
                  disabled={cargando}
                  style={[styles.btnBio, cargando && styles.btnBioDeshabilitado]}
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
    paddingBottom: SPACING.sm,
  },
  govStripe: {
    height: 26,
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

  // Carrusel
  flatList: {
    height: CAROUSEL_H,
  },
  slide: {
    width: SW,
    height: CAROUSEL_H,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: SPACING.xl,
  },
  slidePatron: {
    position: 'absolute',
    inset: 0,
    opacity: 0.06,
    backgroundColor: 'transparent',
    // Patrón visual sutil — se puede cambiar por ImageBackground con foto real
  },
  slideContenido: {
    alignItems: 'center',
    gap: SPACING.xs,
  },
  slideIconoCirculo: {
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: 'rgba(255,255,255,0.12)',
    borderWidth: 1.5,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: SPACING.xs,
  },
  slideNombre: {
    fontSize: 26,
    fontWeight: '800',
    color: '#FFFFFF',
    letterSpacing: 1,
    textShadowColor: 'rgba(0,0,0,0.4)',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 4,
  },
  slideSubtitulo: {
    fontSize: 12,
    color: 'rgba(255,255,255,0.80)',
    textAlign: 'center',
    letterSpacing: 0.3,
  },
  slideBadge: {
    position: 'absolute',
    bottom: SPACING.sm,
    right: SPACING.md,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 3,
    backgroundColor: 'rgba(0,0,0,0.30)',
    paddingHorizontal: SPACING.xs,
    paddingVertical: 3,
    borderRadius: RADIUS.pill,
  },
  slideBadgeTxt: {
    fontSize: 10,
    fontWeight: '600',
    letterSpacing: 0.5,
  },

  // Dots
  dots: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    gap: 6,
    paddingVertical: SPACING.xs,
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: 'rgba(255,255,255,0.35)',
  },
  dotActivo: {
    width: 18,
    backgroundColor: '#FFFFFF',
  },

  // Logo
  logoWrap: {
    alignItems: 'center',
    paddingTop: SPACING.xs,
    paddingBottom: SPACING.sm,
  },
  escudoCirculo: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: 'rgba(255,255,255,0.15)',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: SPACING.xs,
    borderWidth: 2,
    borderColor: 'rgba(255,255,255,0.4)',
  },
  appTitle: {
    fontSize: 28,
    fontWeight: '800',
    color: '#FFFFFF',
    letterSpacing: 4,
    marginBottom: 2,
  },
  appSubtitulo: {
    fontSize: 12,
    color: 'rgba(255,255,255,0.85)',
    textAlign: 'center',
    paddingHorizontal: SPACING.xl,
    marginBottom: SPACING.xs,
  },
  entidadBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: 'rgba(0,0,0,0.25)',
    paddingHorizontal: SPACING.sm,
    paddingVertical: 3,
    borderRadius: RADIUS.pill,
  },
  entidadTxt: {
    fontSize: 10,
    color: GOV.amarillo,
    fontWeight: '600',
    letterSpacing: 0.3,
  },

  // Card formulario
  cardScroll: {
    flex: 1,
    backgroundColor: GOV.fondoApp,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
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
    fontSize: 20,
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

  // Separador biometría
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

  // Botón huella
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
