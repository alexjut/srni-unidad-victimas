import { View, ActivityIndicator, StyleSheet } from 'react-native';
import { Tabs, Redirect } from 'expo-router';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useAuthStore } from '../../src/stores/authStore';

type IconProps = { color: string; size: number };

export default function MainLayout() {
  const { usuario, perfilCargado } = useAuthStore();
  const insets = useSafeAreaInsets();

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

  // Altura del tab bar: 58 px visibles + inset del sistema operativo
  const TAB_HEIGHT = 58 + insets.bottom;

  return (
    <Tabs
      initialRouteName="busqueda"
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: '#1565C0',
        tabBarInactiveTintColor: '#9E9E9E',
        tabBarStyle: {
          backgroundColor: '#FFFFFF',
          // Esquinas superiores redondeadas — estilo moderno tipo banca
          borderTopLeftRadius: 20,
          borderTopRightRadius: 20,
          borderTopWidth: 0,
          height: TAB_HEIGHT,
          paddingBottom: insets.bottom + 4,
          paddingTop: 6,
          // Sombra pronunciada para que flote sobre el contenido
          shadowColor: '#1565C0',
          shadowOffset: { width: 0, height: -4 },
          shadowOpacity: 0.12,
          shadowRadius: 12,
          elevation: 14,
        },
        tabBarLabelStyle: {
          fontSize: 10,
          fontWeight: '600',
          marginTop: 1,
        },
        tabBarIconStyle: {
          marginBottom: -2,
        },
      }}
    >
      {/* ── Tab 1: Buscar Víctima — pantalla inicial ── */}
      <Tabs.Screen
        name="busqueda"
        options={{
          title: 'Víctimas',
          tabBarIcon: ({ color, size }: IconProps) => (
            <MaterialCommunityIcons name="account-search" size={size} color={color} />
          ),
        }}
      />

      {/* ── Tab 2: Hogares ── */}
      <Tabs.Screen
        name="hogares/index"
        options={{
          title: 'Hogares',
          tabBarIcon: ({ color, size }: IconProps) => (
            <MaterialCommunityIcons name="home-group" size={size} color={color} />
          ),
        }}
      />

      {/* ── Tab 3: Encuestas ── */}
      <Tabs.Screen
        name="encuestas/index"
        options={{
          title: 'Encuestas',
          tabBarIcon: ({ color, size }: IconProps) => (
            <MaterialCommunityIcons name="clipboard-list" size={size} color={color} />
          ),
        }}
      />

      {/* ── Tab 4: Menú / perfil / dashboard ── */}
      <Tabs.Screen
        name="index"
        options={{
          title: 'Menú',
          tabBarIcon: ({ color, size }: IconProps) => (
            <MaterialCommunityIcons name="dots-grid" size={size} color={color} />
          ),
        }}
      />

      {/* ── Rutas ocultas (no aparecen en el tab bar) ── */}
      <Tabs.Screen name="hogares/[hogarId]"               options={{ href: null }} />
      <Tabs.Screen name="hogares/nuevo"                   options={{ href: null }} />
      <Tabs.Screen name="encuestas/[sesionId]"            options={{ href: null }} />
      <Tabs.Screen name="caracterizar/index"              options={{ href: null }} />
      <Tabs.Screen name="formulario/index"                options={{ href: null }} />
      <Tabs.Screen name="formulario/[temaId]"             options={{ href: null }} />
      <Tabs.Screen name="formulario/consentimiento-ia"    options={{ href: null }} />
      <Tabs.Screen name="formulario/grabacion-entrevista" options={{ href: null }} />
      <Tabs.Screen name="formulario/revision-ia"         options={{ href: null }} />
    </Tabs>
  );
}

const styles = StyleSheet.create({
  splash: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#F5F5F5' },
});
