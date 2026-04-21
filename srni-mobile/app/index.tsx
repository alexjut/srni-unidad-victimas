/**
 * Punto de entrada de la app.
 * Muestra un splash mientras cargarPerfil() resuelve el token guardado,
 * luego redirige al grupo correcto sin ninguna navegación imperativa.
 */
import { View, ActivityIndicator, StyleSheet } from 'react-native';
import { Redirect } from 'expo-router';
import { useAuthStore } from '../src/stores/authStore';

export default function Index() {
  const { usuario, perfilCargado } = useAuthStore();

  // Todavía leyendo SecureStore → mostrar splash
  if (!perfilCargado) {
    return (
      <View style={styles.splash}>
        <ActivityIndicator size="large" color="#1565C0" />
      </View>
    );
  }

  // Perfil cargado → redirigir según estado de sesión
  if (usuario) {
    return <Redirect href="/(main)" />;
  }

  return <Redirect href="/(auth)/login" />;
}

const styles = StyleSheet.create({
  splash: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#F5F5F5',
  },
});
