/**
 * Pantalla de inicio de sesión — GOV.CO institucional.
 *
 * Fondo: 5 fotos reales de regiones colombianas que ciclan automáticamente
 * cada 5 s en orden ALEATORIO (sin repetir la actual) usando crossfade +
 * efecto Ken Burns (zoom suave). Sin controles manuales de carrusel
 * (sin dots, sin swipe, sin botones de navegación).
 *
 * Rendimiento:
 *   - Imágenes empaquetadas como assets locales (bundled, sin prefetch necesario).
 *   - Ken Burns se pausa cuando la app pasa a background (AppState listener).
 *   - Todos los timers se limpian al desmontar la pantalla.
 */
import { useState, useEffect, useRef } from 'react';
import {
  View, StyleSheet, KeyboardAvoidingView, Platform,
  ScrollView, StatusBar, Pressable, Image,
  Animated, ImageBackground, AppState, Dimensions,
} from 'react-native';
import { Text, TextInput, HelperText, Checkbox } from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import * as SecureStore from 'expo-secure-store';
import * as LocalAuthentication from 'expo-local-authentication';
import { useAuthStore } from '../../src/stores/authStore';
import { GovButton } from '../../src/components/GovButton';
import { GOV, SPACING, RADIUS, SHADOW, FONT } from '../../src/theme/govTheme';
import { APP_NAME, SUBDIRECTION_NAME } from '../../src/config/marca';

// ── Constantes de animación ───────────────────────────────────────────────────
const DURACION_MS  =  5_000;   // tiempo visible de cada foto
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
    imagen: require('../../assets/regiones/caribe.jpg'),
  },
  {
    nombre: 'Andes',
    subtitulo: 'Montañas, café y memoria',
    icono: 'image-filter-hdr' as const,
    imagen: require('../../assets/regiones/andina.jpg'),
  },
  {
    nombre: 'Amazonia',
    subtitulo: 'Selva tropical y grandes ríos',
    icono: 'leaf' as const,
    imagen: require('../../assets/regiones/amazonia.jpg'),
  },
  {
    nombre: 'Orinoquía',
    subtitulo: 'Llanos orientales y sabanas',
    icono: 'grass' as const,
    imagen: require('../../assets/regiones/orinoca.jpg'),
  },
  {
    nombre: 'Insular',
    subtitulo: 'San Andrés, Providencia y Santa Catalina',
    icono: 'island' as const,
    imagen: require('../../assets/regiones/insular.jpg'),
  },
];

const N = REGIONES.length;

// ─────────────────────────────────────────────────────────────────────────────

export default function LoginScreen() {
  const { login, loginBiometrico, cargando, error, limpiarError } = useAuthStore();
  const [codigo, setCodigo]       = useState('');
  const [password, setPassword]   = useState('');
  const [verPassword, setVerPassword] = useState(false);
  const [recordar, setRecordar] = useState(true);
  const [biometricoListo, setBiometricoListo] = useState(false);
  // #22 — biometría OPT-IN: el dispositivo soporta huella/rostro (para mostrar
  // el checkbox) y la preferencia explícita del usuario (default false).
  const [dispositivoBiometrico, setDispositivoBiometrico] = useState(false);
  const [activarBiometria, setActivarBiometria] = useState(false);
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

    // Elige un índice aleatorio distinto al actual (para que se vean todas
    // las regiones sin repetir la que está en pantalla).
    function siguienteAleatorio(actual: number): number {
      if (N <= 1) return actual;
      let n = Math.floor(Math.random() * (N - 1));
      if (n >= actual) n += 1; // salta el índice actual
      return n;
    }

    const timer = setInterval(() => {
      transicionarA(siguienteAleatorio(idxRef.current));
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

  // ── Recordar código de usuario (solo el código, nunca la contraseña) ─────────
  useEffect(() => {
    SecureStore.getItemAsync('codigo_recordado')
      .then((c) => {
        if (c) { setCodigo(c); setRecordar(true); } else { setRecordar(false); }
      })
      .catch(() => { /* silencioso */ });
  }, []);

  // ── Biometría ──────────────────────────────────────────────────────────────
  useEffect(() => {
    async function verificar() {
      try {
        const hw = await LocalAuthentication.hasHardwareAsync();
        if (!hw) return;
        const enrolled = await LocalAuthentication.isEnrolledAsync();
        if (!enrolled) return;
        setDispositivoBiometrico(true); // soportada → mostrar el checkbox opt-in
        const habilitado = await SecureStore.getItemAsync('biometrico_habilitado');
        const token = await SecureStore.getItemAsync('refresh_token');
        // Pre-marcar el checkbox si el usuario ya la había activado antes.
        setActivarBiometria(habilitado === 'true');
        setBiometricoListo(habilitado === 'true' && !!token);
      } catch { /* silencioso */ }
    }
    verificar();
  }, []);

  async function handleLogin() {
    if (!codigo.trim() || !password) return;
    limpiarError();
    try {
      await login(codigo, password, dispositivoBiometrico && activarBiometria);
      // Persistir (o borrar) solo el código de usuario según preferencia.
      if (recordar) await SecureStore.setItemAsync('codigo_recordado', codigo.trim().toUpperCase());
      else await SecureStore.deleteItemAsync('codigo_recordado');
    } catch { /* error ya en store */ }
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

            {/* Logo institucional — Unidad para las Víctimas */}
            <View style={styles.logoWrap}>
              <Image
                source={require('../../assets/logos/logo-unidad-vertical-negativo.png')}
                style={styles.logoImg}
                resizeMode="contain"
                accessibilityLabel="Unidad para las Víctimas"
              />
              {/* Nombre de la APK */}
              <Text style={styles.appTitulo}>{APP_NAME}</Text>
              <Text style={styles.appSubtitulo}>
                Sistema de Caracterización de Víctimas
              </Text>
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

            <Pressable
              style={styles.recordarRow}
              onPress={() => setRecordar((v) => !v)}
              accessibilityRole="checkbox"
              accessibilityState={{ checked: recordar }}
              accessibilityLabel="Recordar mi código de usuario"
            >
              <Checkbox status={recordar ? 'checked' : 'unchecked'} color={GOV.azul} />
              <Text style={styles.recordarTxt}>Recordar mi código de usuario</Text>
            </Pressable>

            {/* #22 — opt-in de biometría: solo si el dispositivo la soporta. */}
            {dispositivoBiometrico && (
              <Pressable
                style={styles.recordarRow}
                onPress={() => setActivarBiometria((v) => !v)}
                accessibilityRole="checkbox"
                accessibilityState={{ checked: activarBiometria }}
                accessibilityLabel="Activar ingreso con huella o rostro"
              >
                <Checkbox status={activarBiometria ? 'checked' : 'unchecked'} color={GOV.azul} />
                <Text style={styles.recordarTxt}>Activar ingreso con huella o rostro</Text>
              </Pressable>
            )}

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
          <Text style={styles.pieInstitucional}>{SUBDIRECTION_NAME}</Text>
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
  logoImg: {
    width: 210,
    height: 200,
    marginBottom: SPACING.xs,
  },
  appTitulo: {
    fontSize: 26,
    fontWeight: '800',
    color: '#FFFFFF',
    textAlign: 'center',
    letterSpacing: 0.3,
    textShadowColor: 'rgba(0,0,0,0.35)',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 3,
  },
  appSubtitulo: {
    fontSize: 12,
    color: 'rgba(255,255,255,0.9)',
    textAlign: 'center',
    paddingHorizontal: SPACING.lg,
    lineHeight: 17,
    letterSpacing: 0.2,
  },
  recordarRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 2,
    marginLeft: -8,
  },
  recordarTxt: {
    fontSize: 13,
    color: GOV.textoP,
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
  pieInstitucional: {
    fontSize: 12,
    fontWeight: '700',
    color: 'rgba(255,255,255,0.92)',
    textAlign: 'center',
    marginTop: SPACING.md,
    paddingHorizontal: SPACING.md,
    letterSpacing: 0.2,
  },
  pie: {
    ...FONT.caption,
    color: 'rgba(255,255,255,0.68)',
    textAlign: 'center',
    marginTop: 4,
    paddingHorizontal: SPACING.md,
    lineHeight: 16,
  },
});
