/**
 * Pantalla de inicio de sesión — GOV.CO institucional.
 *
 * Fondo: 5 fotos reales de regiones colombianas que ciclan automáticamente
 * cada 30 s usando crossfade + efecto Ken Burns (zoom suave). Sin controles
 * manuales de carrusel (sin dots, sin swipe, sin botones de navegación).
 *
 * Rendimiento:
 *   - Imágenes empaquetadas como assets locales (bundled, sin prefetch necesario).
 *   - Ken Burns se pausa cuando la app pasa a background (AppState listener).
 *   - Todos los timers se limpian al desmontar la pantalla.
 */
import { useState, useEffect, useRef } from 'react';
import {
  View, StyleSheet, KeyboardAvoidingView, Platform,
  ScrollView, StatusBar, Pressable,
  Animated, ImageBackground, AppState, Dimensions,
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

// ── Constantes de animación ───────────────────────────────────────────────────
const DURACION_MS  = 30_000;   // tiempo visible de cada foto
const FADE_MS      =  2_000;   // duración del crossfade entre fotos
const KB_MITAD_MS  = 40_000;   // Ken Burns: 1.0→1.08 en 40 s, luego 1.08→1.0

const { height: SH } = Dimensions.get('window');

// ── Regiones con foto real disponible ────────────────────────────────────────
// Orden de ciclo: Caribe → Andes → Amazonia → Orinoquía → Insular
// (Pacífico pendiente de foto: agregar 'pacifico.png' cuando esté disponible)
const REGIONES = [
  {
    nombre: 'Caribe',
    subtitulo: 'Mar, playas y cultura vallenata',
    icono: 'palm-tree' as const,
    imagen: require('../../assets/regiones/caribe.png'),
  },
  {
    nombre: 'Andes',
    subtitulo: 'Montañas, café y memoria',
    icono: 'image-filter-hdr' as const,
    imagen: require('../../assets/regiones/andina.png'),
  },
  {
    nombre: 'Amazonia',
    subtitulo: 'Selva tropical y grandes ríos',
    icono: 'leaf' as const,
    imagen: require('../../assets/regiones/amazonia.png'),
  },
  {
    nombre: 'Orinoquía',
    subtitulo: 'Llanos orientales y sabanas',
    icono: 'grass' as const,
    imagen: require('../../assets/regiones/orinoca.png'),
  },
  {
    nombre: 'Insular',
    subtitulo: 'San Andrés, Providencia y Santa Catalina',
    icono: 'island' as const,
    imagen: require('../../assets/regiones/insular.png'),
  },
];

const N = REGIONES.length;

// ─────────────────────────────────────────────────────────────────────────────

export default function LoginScreen() {
  const { login, loginBiometrico, cargando, error, limpiarError } = useAuthStore();
  const [codigo, setCodigo]       = useState('');
  const [password, setPassword]   = useState('');
  const [verPassword, setVerPassword] = useState(false);
  const [biometricoListo, setBiometricoListo] = useState(false);
  const [idxActivo, setIdxActivo] = useState(0);
  const insets = useSafeAreaInsets();

  // ── Animated values (un par por región) ─────────────────────────────────────
  // opacidades[i]: 1 cuando la foto i es visible, 0 cuando está oculta
  // escalas[i]:    Ken Burns — loop 1.0 ↔ 1.08
  const opacidades = useRef(
    REGIONES.map((_, i) => new Animated.Value(i === 0 ? 1 : 0)),
  ).current;
  const escalas = useRef(
    REGIONES.map(() => new Animated.Value(1)),
  ).current;
  // Fade del indicador de región (icono + nombre sobre el fondo)
  const opLabel = useRef(new Animated.Value(1)).current;

  // Refs internas (no causan re-render)
  const kbAnims      = useRef<(Animated.CompositeAnimation | null)[]>(Array(N).fill(null));
  const enTransicion = useRef(false);
  const idxRef       = useRef(0);   // espejo de idxActivo sin cierre de estado

  // ── Ciclo de animaciones + AppState ─────────────────────────────────────────
  useEffect(() => {
    // ── Ken Burns helpers ────────────────────────────────────────────────────
    function iniciarKB(idx: number) {
      kbAnims.current[idx]?.stop();
      escalas[idx].setValue(1.0);
      const anim = Animated.loop(
        Animated.sequence([
          Animated.timing(escalas[idx], {
            toValue: 1.08, duration: KB_MITAD_MS, useNativeDriver: true,
          }),
          Animated.timing(escalas[idx], {
            toValue: 1.0,  duration: KB_MITAD_MS, useNativeDriver: true,
          }),
        ]),
      );
      kbAnims.current[idx] = anim;
      anim.start();
    }

    function detenerKB(idx: number) {
      kbAnims.current[idx]?.stop();
      kbAnims.current[idx] = null;
    }

    // ── Crossfade ────────────────────────────────────────────────────────────
    function transicionarA(next: number) {
      if (enTransicion.current) return;
      enTransicion.current = true;

      const prev = idxRef.current;
      idxRef.current = next;

      // Fade out del indicador de región → cambiar texto → fade in
      Animated.timing(opLabel, { toValue: 0, duration: 350, useNativeDriver: true })
        .start(() => {
          setIdxActivo(next);
          Animated.timing(opLabel, { toValue: 1, duration: 450, useNativeDriver: true }).start();
        });

      // Iniciar Ken Burns del slide entrante
      iniciarKB(next);

      // Crossfade entre fotos
      Animated.parallel([
        Animated.timing(opacidades[prev], {
          toValue: 0, duration: FADE_MS, useNativeDriver: true,
        }),
        Animated.timing(opacidades[next], {
          toValue: 1, duration: FADE_MS, useNativeDriver: true,
        }),
      ]).start(() => {
        // Liberar recursos del slide saliente
        detenerKB(prev);
        enTransicion.current = false;
      });
    }

    // ── Arranque ─────────────────────────────────────────────────────────────
    iniciarKB(0);

    const timer = setInterval(() => {
      transicionarA((idxRef.current + 1) % N);
    }, DURACION_MS);

    // Pausa KB cuando la app va a background para ahorrar batería
    const appSub = AppState.addEventListener('change', (state) => {
      if (state !== 'active') {
        kbAnims.current.forEach((a) => a?.stop());
      } else {
        iniciarKB(idxRef.current);
      }
    });

    return () => {
      clearInterval(timer);
      kbAnims.current.forEach((a) => a?.stop());
      appSub.remove();
    };
  }, []); // solo al montar — todas las dependencias son refs estables

  // ── Biometría ──────────────────────────────────────────────────────────────
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
    try { await login(codigo, password); } catch { /* error ya en store */ }
  }

  async function handleBiometrico() {
    limpiarError();
    try { await loginBiometrico(); } catch { /* error ya en store */ }
  }

  const region = REGIONES[idxActivo];

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <>
      <StatusBar backgroundColor="transparent" translucent barStyle="light-content" />

      {/* ── Capas de fondo (absolute, detrás de todo) ── */}
      <View style={[StyleSheet.absoluteFill, styles.fondoContenedor]} pointerEvents="none">
        {REGIONES.map((r, i) => (
          <Animated.View
            key={r.nombre}
            style={[
              StyleSheet.absoluteFill,
              { opacity: opacidades[i], transform: [{ scale: escalas[i] }] },
            ]}
          >
            <ImageBackground
              source={r.imagen}
              style={StyleSheet.absoluteFill}
              resizeMode="cover"
            />
          </Animated.View>
        ))}

        {/* Gradiente oscuro: sutil arriba, más denso abajo para legibilidad del card */}
        <LinearGradient
          colors={[
            'rgba(0,0,0,0.08)',
            'rgba(0,0,0,0.42)',
            'rgba(0,0,0,0.78)',
          ]}
          style={StyleSheet.absoluteFill}
          start={{ x: 0, y: 0 }}
          end={{ x: 0, y: 1 }}
        />
      </View>

      {/* ── UI sobre el fondo ── */}
      <KeyboardAvoidingView
        style={styles.root}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        {/* Franja GOV.CO — siempre visible en la parte superior */}
        <View style={[styles.govStripe, { paddingTop: insets.top, height: 26 + insets.top }]}>
          <Text style={styles.govText}>GOV.CO</Text>
        </View>

        <ScrollView
          style={{ flex: 1 }}
          contentContainerStyle={[
            styles.scrollContent,
            { minHeight: SH - 26 - insets.top },
          ]}
          keyboardShouldPersistTaps="handled"
          bounces={false}
          showsVerticalScrollIndicator={false}
        >
          {/* Área superior: indicador de región + logo SRNI — crece para empujar card abajo */}
          <View style={styles.areaTop}>

            {/* Indicador de región (cambia con fade sincronizado al crossfade de fondo) */}
            <Animated.View style={[styles.regionPill, { opacity: opLabel }]}>
              <View style={styles.regionIconCirculo}>
                <MaterialCommunityIcons name={region.icono} size={14} color="#FFFFFF" />
              </View>
              <View style={{ marginLeft: 8 }}>
                <Text style={styles.regionNombre}>{region.nombre}</Text>
                <Text style={styles.regionSubtitulo}>{region.subtitulo}</Text>
              </View>
            </Animated.View>

            {/* Logo institucional SRNI */}
            <View style={styles.logoWrap}>
              <View style={styles.escudoCirculo}>
                <MaterialCommunityIcons name="shield-account" size={38} color="#FFFFFF" />
              </View>
              <Text style={styles.appTitle}>SRNI</Text>
              <Text style={styles.appSubtitulo}>
                Sistema de Caracterización de Víctimas
              </Text>
              <View style={styles.entidadBadge}>
                <MaterialCommunityIcons name="domain" size={11} color={GOV.amarillo} />
                <Text style={styles.entidadTxt}>Unidad para las Víctimas — Colombia</Text>
              </View>
            </View>
          </View>

          {/* ── Card de login ── */}
          <View style={styles.card}>
            <Text style={styles.cardTitulo}>Bienvenido/a</Text>
            <Text style={styles.cardSubtitulo}>
              Ingresa tus credenciales institucionales
            </Text>

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
              autoCapitalize="none"
              autoCorrect={false}
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
                  style={[styles.btnBio, cargando && { opacity: 0.4 }]}
                  accessibilityLabel="Acceder con huella digital"
                  accessibilityRole="button"
                >
                  {({ pressed }) => (
                    <>
                      <View style={[
                        styles.btnBioCirculo,
                        pressed && { backgroundColor: GOV.azulOscuro, elevation: 4 },
                      ]}>
                        <MaterialCommunityIcons name="fingerprint" size={38} color="#FFFFFF" />
                      </View>
                      <Text style={styles.btnBioTxt}>Huella digital</Text>
                    </>
                  )}
                </Pressable>
              </>
            )}
          </View>

          {/* Pie de página */}
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
  // Contenedor raíz de las imágenes de fondo — overflow hidden para recortar
  // el desborde del efecto Ken Burns (scale 1.08)
  fondoContenedor: {
    overflow: 'hidden',
  },

  root: {
    flex: 1,
  },

  // Franja GOV.CO amarilla
  govStripe: {
    backgroundColor: GOV.amarillo,
    justifyContent: 'flex-end',
    paddingHorizontal: SPACING.md,
    paddingBottom: 5,
  },
  govText: {
    fontSize: 11,
    fontWeight: '700',
    color: GOV.azulOscuro,
    letterSpacing: 1.5,
  },

  // ScrollView content
  scrollContent: {
    paddingHorizontal: SPACING.md,
    paddingBottom: SPACING.xl,
    flexGrow: 1,
  },

  // Área superior — flex:1 para empujar el card hacia abajo
  areaTop: {
    flex: 1,
    paddingTop: SPACING.md,
    alignItems: 'flex-start',
    gap: SPACING.lg,
    justifyContent: 'center',
  },

  // Indicador de región
  regionPill: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(0,0,0,0.38)',
    paddingHorizontal: SPACING.sm,
    paddingVertical: 7,
    borderRadius: RADIUS.pill,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.22)',
  },
  regionIconCirculo: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: 'rgba(255,255,255,0.18)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  regionNombre: {
    fontSize: 13,
    fontWeight: '700',
    color: '#FFFFFF',
    letterSpacing: 0.4,
  },
  regionSubtitulo: {
    fontSize: 10,
    color: 'rgba(255,255,255,0.72)',
    letterSpacing: 0.2,
  },

  // Logo SRNI
  logoWrap: {
    alignItems: 'center',
    width: '100%',
    paddingVertical: SPACING.md,
    gap: 4,
  },
  escudoCirculo: {
    width: 74,
    height: 74,
    borderRadius: 37,
    backgroundColor: 'rgba(255,255,255,0.15)',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: 'rgba(255,255,255,0.42)',
    marginBottom: SPACING.xs,
  },
  appTitle: {
    fontSize: 34,
    fontWeight: '800',
    color: '#FFFFFF',
    letterSpacing: 7,
    textShadowColor: 'rgba(0,0,0,0.55)',
    textShadowOffset: { width: 0, height: 2 },
    textShadowRadius: 8,
  },
  appSubtitulo: {
    fontSize: 12,
    color: 'rgba(255,255,255,0.85)',
    textAlign: 'center',
    paddingHorizontal: SPACING.lg,
    lineHeight: 17,
  },
  entidadBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: 'rgba(0,0,0,0.32)',
    paddingHorizontal: SPACING.sm,
    paddingVertical: 4,
    borderRadius: RADIUS.pill,
    marginTop: SPACING.xs,
  },
  entidadTxt: {
    fontSize: 10,
    color: GOV.amarillo,
    fontWeight: '600',
    letterSpacing: 0.3,
  },

  // Card de login
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: RADIUS.lg,
    padding: SPACING.lg,
    ...SHADOW.card,
    marginTop: SPACING.lg,
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
  btnBioTxt: {
    fontSize: 13,
    fontWeight: '600',
    color: GOV.azul,
    letterSpacing: 0.3,
  },

  // Pie
  pie: {
    ...FONT.caption,
    color: 'rgba(255,255,255,0.68)',
    textAlign: 'center',
    marginTop: SPACING.md,
    paddingHorizontal: SPACING.md,
    lineHeight: 16,
  },
});
