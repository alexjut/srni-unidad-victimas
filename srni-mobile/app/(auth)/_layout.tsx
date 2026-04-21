/**
 * Layout del grupo de autenticación.
 * Si el usuario ya tiene sesión activa → redirige a (main).
 * Mientras carga el perfil → splash (View vacío) para evitar flash al login.
 */
import { View, ActivityIndicator, StyleSheet } from 'react-native';
import { Stack, Redirect } from 'expo-router';
import { useAuthStore } from '../../src/stores/authStore';

export default function AuthLayout() {
  const { usuario, perfilCargado } = useAuthStore();

  // Esperando a que SecureStore resuelva el token guardado
  if (!perfilCargado) {
    return (
      <View style={styles.splash}>
        <ActivityIndicator size="large" color="#1565C0" />
      </View>
    );
  }

  // Usuario autenticado → salir del grupo auth
  if (usuario) {
    return <Redirect href="/(main)" />;
  }

  return <Stack screenOptions={{ headerShown: false }} />;
}

const styles = StyleSheet.create({
  splash: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#F5F5F5' },
});
