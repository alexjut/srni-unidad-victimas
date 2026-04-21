/**
 * Layout principal con bottom tabs (encuestador).
 * Si no hay sesión activa → redirige al login.
 * Mientras carga el perfil → splash para evitar flash.
 */
import { View, ActivityIndicator, StyleSheet, Platform } from 'react-native';
import { Tabs, Redirect } from 'expo-router';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useAuthStore } from '../../src/stores/authStore';

type IconProps = { color: string; size: number };

export default function MainLayout() {
  const { usuario, perfilCargado } = useAuthStore();
  const perfil = usuario?.perfil;

  if (!perfilCargado) {
    return (
      <View style={styles.splash}>
        <ActivityIndicator size="large" color="#1565C0" />
      </View>
    );
  }

  if (!usuario) {
    return <Redirect href="/(auth)/login" />;
  }

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: '#1565C0',
        tabBarInactiveTintColor: '#757575',
        tabBarStyle: {
          backgroundColor: '#FFFFFF',
          borderTopColor: '#E0E0E0',
          borderTopWidth: 1,
          height: Platform.OS === 'ios' ? 82 : 60,
          paddingBottom: Platform.OS === 'ios' ? 24 : 6,
          paddingTop: 4,
        },
        tabBarLabelStyle: {
          fontSize: 11,
          fontWeight: '500',
        },
      }}
    >
      {/* ── Tabs visibles ──────────────────────────────────────────────────── */}

      <Tabs.Screen
        name="index"
        options={{
          title: 'Inicio',
          tabBarIcon: ({ color, size }: IconProps) => (
            <MaterialCommunityIcons name="home" size={size} color={color} />
          ),
        }}
      />

      <Tabs.Screen
        name="busqueda"
        options={{
          title: 'Buscar',
          href: perfil?.puede_buscar_rni ? undefined : null,
          tabBarIcon: ({ color, size }: IconProps) => (
            <MaterialCommunityIcons name="magnify" size={size} color={color} />
          ),
        }}
      />

      <Tabs.Screen
        name="hogares"
        options={{
          title: 'Hogares',
          href: perfil?.puede_caracterizar ? undefined : null,
          tabBarIcon: ({ color, size }: IconProps) => (
            <MaterialCommunityIcons name="home-group" size={size} color={color} />
          ),
        }}
      />

      <Tabs.Screen
        name="encuestas"
        options={{
          title: 'Encuestas',
          href: perfil?.puede_caracterizar ? undefined : null,
          tabBarIcon: ({ color, size }: IconProps) => (
            <MaterialCommunityIcons name="clipboard-list" size={size} color={color} />
          ),
        }}
      />

      <Tabs.Screen
        name="formulario"
        options={{
          title: 'Formulario',
          href: perfil?.puede_caracterizar ? undefined : null,
          tabBarIcon: ({ color, size }: IconProps) => (
            <MaterialCommunityIcons name="file-document" size={size} color={color} />
          ),
        }}
      />

      {/* ── Rutas ocultas (subrutas — no deben aparecer como tabs) ─────────── */}

      <Tabs.Screen
        name="hogares/[hogarId]"
        options={{ href: null }}
      />

      <Tabs.Screen
        name="hogares/nuevo"
        options={{ href: null }}
      />

      <Tabs.Screen
        name="encuestas/[sesionId]"
        options={{ href: null }}
      />

      <Tabs.Screen
        name="formulario/[temaId]"
        options={{ href: null }}
      />

      <Tabs.Screen
        name="formulario/consentimiento-ia"
        options={{ href: null }}
      />
    </Tabs>
  );
}

const styles = StyleSheet.create({
  splash: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#F5F5F5' },
});
