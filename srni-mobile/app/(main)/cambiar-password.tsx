/**
 * Cambiar la contraseña desde el teléfono.
 *
 * El servicio existe desde siempre y el panel web ya tenía su pantalla, pero la
 * APK no: solo la llamada, sin dónde usarla. Y quien recibe una clave
 * **provisional** —las 10 encuestadoras que llegaron de VIVANTO el 16-sep-2026—
 * trabaja en el teléfono, no en el panel. Hasta hoy, para cambiarla tenía que
 * entrar al panel o pedirle a desarrollo que se la cambiara: una clave que
 * terminaba circulando por WhatsApp y que nadie podía retirar.
 *
 * El servidor invalida la sesión al cambiarla (revoca el token de refresco que se
 * le manda), así que después hay que ingresar de nuevo. La pantalla lo dice antes,
 * no después: en campo, cerrar sesión sin avisar se lee como que la app falló.
 */
import { useState } from 'react';
import {
  View, ScrollView, StyleSheet, KeyboardAvoidingView, Platform, Alert,
} from 'react-native';
import { Text, TextInput, HelperText } from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { router } from 'expo-router';
import * as SecureStore from 'expo-secure-store';

import { authApi } from '../../src/api/auth';
import { useAuthStore } from '../../src/stores/authStore';
import { GovHeader } from '../../src/components/GovHeader';
import { GovButton } from '../../src/components/GovButton';
import { GOV, SPACING, RADIUS, SHADOW, FONT } from '../../src/theme/govTheme';
import { interpretarError } from '../../src/utils/errores';
import { validarCambioPassword, LARGO_MINIMO } from '../../src/utils/cambioPassword';
import { reportarError } from '../../src/services/errorReporter';

export default function CambiarPasswordScreen() {
  const usuario = useAuthStore((s) => s.usuario);
  const logout = useAuthStore((s) => s.logout);

  const [actual, setActual] = useState('');
  const [nueva, setNueva] = useState('');
  const [confirmacion, setConfirmacion] = useState('');
  const [verActual, setVerActual] = useState(false);
  const [verNueva, setVerNueva] = useState(false);
  const [errores, setErrores] = useState<Record<string, string>>({});
  const [guardando, setGuardando] = useState(false);

  function validar(): boolean {
    const e = validarCambioPassword({ actual, nueva, confirmacion });
    setErrores(e);
    return Object.keys(e).length === 0;
  }

  async function guardar() {
    if (!validar()) return;
    setGuardando(true);
    try {
      // El `refresh` va a propósito: es lo que el servidor revoca para que la
      // sesión vieja no siga sirviendo con la contraseña anterior.
      const refresh = (await SecureStore.getItemAsync('refresh_token')) ?? undefined;

      await authApi.cambiarPassword({
        password_actual: actual,
        password_nuevo: nueva,
        password_nuevo_confirmacion: confirmacion,
        ...(refresh ? { refresh } : {}),
      });

      Alert.alert(
        'Contraseña actualizada',
        'Ingrese de nuevo con su contraseña nueva.',
        [{
          text: 'Aceptar',
          onPress: async () => {
            await logout();
            router.replace('/(auth)/login');
          },
        }],
        { cancelable: false },
      );
    } catch (err: any) {
      // El servidor responde por campo: la contraseña actual equivocada y las
      // reglas de la nueva son cosas distintas y se marcan donde corresponde.
      const data = err?.response?.data;
      if (err?.response?.status === 400 && data && typeof data === 'object') {
        const deCampo = (k: string) => (Array.isArray(data[k]) ? String(data[k][0]) : undefined);
        const e: Record<string, string> = {};
        const actualMsg = deCampo('password_actual');
        const nuevaMsg = deCampo('password_nuevo');
        const confMsg = deCampo('password_nuevo_confirmacion');
        if (actualMsg) e.actual = actualMsg;
        if (nuevaMsg) e.nueva = nuevaMsg;
        if (confMsg) e.confirmacion = confMsg;
        if (Object.keys(e).length > 0) {
          setErrores(e);
          return;
        }
      }
      const info = interpretarError(err, 'No se pudo cambiar la contraseña. Intente de nuevo.');
      Alert.alert('No se pudo cambiar', info.mensaje);
      if (!info.sinRed) {
        reportarError({
          nivel: 'warn',
          mensaje: `cambiar-password — ${info.diagnostico}`,
          pantalla: 'cambiar-password',
        });
      }
    } finally {
      setGuardando(false);
    }
  }

  return (
    <View style={styles.root}>
      <GovHeader
        title="Cambiar contraseña"
        subtitle={usuario?.codigo_usuario ?? ''}
        onBack={() => router.back()}
      />

      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
          <View style={styles.aviso}>
            <MaterialCommunityIcons name="information-outline" size={18} color={GOV.azulOscuro} />
            <Text style={styles.avisoTxt}>
              Al cambiarla se cierra la sesión y deberá ingresar de nuevo. Hágalo
              con señal y antes de salir a campo.
            </Text>
          </View>

          <TextInput
            label="Contraseña actual"
            value={actual}
            onChangeText={setActual}
            mode="outlined"
            secureTextEntry={!verActual}
            autoCapitalize="none"
            autoComplete="current-password"
            style={styles.input}
            activeOutlineColor={GOV.azul}
            error={!!errores.actual}
            right={
              <TextInput.Icon
                icon={verActual ? 'eye-off' : 'eye'}
                onPress={() => setVerActual((v) => !v)}
                forceTextInputFocus={false}
              />
            }
          />
          {errores.actual ? <HelperText type="error">{errores.actual}</HelperText> : null}

          <TextInput
            label="Contraseña nueva"
            value={nueva}
            onChangeText={setNueva}
            mode="outlined"
            secureTextEntry={!verNueva}
            autoCapitalize="none"
            autoComplete="new-password"
            style={styles.input}
            activeOutlineColor={GOV.azul}
            error={!!errores.nueva}
            right={
              <TextInput.Icon
                icon={verNueva ? 'eye-off' : 'eye'}
                onPress={() => setVerNueva((v) => !v)}
                forceTextInputFocus={false}
              />
            }
          />
          {errores.nueva
            ? <HelperText type="error">{errores.nueva}</HelperText>
            : <HelperText type="info">Mínimo {LARGO_MINIMO} caracteres.</HelperText>}

          <TextInput
            label="Repita la contraseña nueva"
            value={confirmacion}
            onChangeText={setConfirmacion}
            mode="outlined"
            secureTextEntry={!verNueva}
            autoCapitalize="none"
            autoComplete="new-password"
            style={styles.input}
            activeOutlineColor={GOV.azul}
            error={!!errores.confirmacion}
          />
          {errores.confirmacion ? <HelperText type="error">{errores.confirmacion}</HelperText> : null}

          <GovButton
            label="Cambiar contraseña"
            icon="lock-reset"
            onPress={guardar}
            loading={guardando}
            disabled={guardando}
          />

          <Text style={styles.nota}>
            Si recibió una contraseña provisional, cámbiela la primera vez que
            ingrese. Es personal: no la comparta.
          </Text>
        </ScrollView>
      </KeyboardAvoidingView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: GOV.fondoApp },
  content: { padding: SPACING.md, paddingBottom: 48, gap: 2 },
  aviso: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 6,
    backgroundColor: GOV.azulTenue,
    borderRadius: RADIUS.sm,
    padding: SPACING.sm,
    marginBottom: SPACING.md,
    ...SHADOW.card,
  },
  avisoTxt: { ...FONT.caption, color: GOV.azulOscuro, flex: 1 },
  input: { backgroundColor: '#FFFFFF', marginTop: SPACING.xs },
  nota: { ...FONT.caption, color: GOV.textoT, marginTop: SPACING.md },
});
