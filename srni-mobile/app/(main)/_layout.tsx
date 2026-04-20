/**
 * Layout principal con bottom tabs (encuestador).
 * Si no hay sesión activa → redirige al login.
 * Mientras carga el perfil → splash para evitar flash.
 */
import { View, ActivityIndicator, StyleSheet, Platform } from 'react-native';
import { Tabs, Redirect } from 'expo-router';
import { useTheme } from 'react-native-paper';
import { useAuthStore } from '../../src/stores/authStore';

export default function MainLayout() {
  const theme = useTheme();
  const { usuario, perfilCargado } = useAuthStore();
  const perfil = usuario?.perfil;

  // Esperando a que SecureStore resuelva
  if (!perfilCargado) {
    return (
      <View style={styles.splash}>
        <ActivityIndicator size="large" color="#1565C0" />
      </View>
    );
  }

  // Sin sesión → ir al login
  if (!usuario) {
    return <Redirect href="/(auth)/login" />;
  }

  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: theme.colors.primary,
        tabBarInactiveTintColor: '#9E9E9E',
        tabBarStyle: {
          backgroundColor: '#FFFFFF',
          borderTopColor: '#E0E0E0',
          height: Platform.OS === 'ios' ? 88 : 64,
          paddingBottom: Platform.OS === 'ios' ? 28 : 8,
        },
        headerStyle: { backgroundColor: theme.colors.primary },
        headerTintColor: '#FFFFFF',
        headerTitleStyle: { fontWeight: '600' },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: 'Inicio',
          tabBarIcon: ({ color, size }) => null, // iconos se configuran con expo-vector-icons
        }}
      />

      <Tabs.Screen
        name="busqueda"
        options={{
          title: 'Búsqueda RNI',
          href: perfil?.puede_buscar_rni ? undefined : null,
        }}
      />

      <Tabs.Screen
        name="formulario"
        options={{
          title: 'Formulario',
          href: perfil?.puede_caracterizar ? undefined : null,
        }}
      />

      <Tabs.Screen
        name="hogares"
        options={{
          title: 'Hogares',
          href: perfil?.puede_caracterizar ? undefined : null,
        }}
      />

      <Tabs.Screen
        name="encuestas"
        options={{
          title: 'Encuestas',
          href: perfil?.puede_caracterizar ? undefined : null,
        }}
      />
    </Tabs>
  );
}

const styles = StyleSheet.create({
  splash: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#F5F5F5' },
});
