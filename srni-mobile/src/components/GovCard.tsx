/**
 * GovCard — Tarjeta institucional GOV.CO
 *
 * Variantes:
 *   default  — tarjeta blanca con sombra sutil
 *   accent   — borde izquierdo azul (sección destacada)
 *   warning  — borde izquierdo amarillo (acción pendiente)
 *   success  — borde izquierdo verde (completado)
 *   offline  — borde izquierdo naranja (pendiente sync)
 */
import { View, StyleSheet, Pressable } from 'react-native';
import { GOV, RADIUS, SHADOW, SPACING } from '../theme/govTheme';

type CardVariant = 'default' | 'accent' | 'warning' | 'success' | 'offline';

const VARIANT_COLOR: Record<CardVariant, string> = {
  default: 'transparent',
  accent:  GOV.azul,
  warning: GOV.amarillo,
  success: GOV.verde,
  offline: GOV.naranja,
};

interface GovCardProps {
  children: React.ReactNode;
  variant?: CardVariant;
  onPress?: () => void;
  style?: object;
}

export function GovCard({ children, variant = 'default', onPress, style }: GovCardProps) {
  const borderColor = VARIANT_COLOR[variant];
  const hasBorder = variant !== 'default';

  const inner = (
    <View
      style={[
        styles.card,
        hasBorder && { borderLeftWidth: 4, borderLeftColor: borderColor },
        style,
      ]}
    >
      {children}
    </View>
  );

  if (onPress) {
    return (
      <Pressable
        onPress={onPress}
        style={({ pressed }) => [{ opacity: pressed ? 0.92 : 1 }]}
        accessibilityRole="button"
      >
        {inner}
      </Pressable>
    );
  }

  return inner;
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: GOV.superficie,
    borderRadius: RADIUS.md,
    padding: SPACING.md,
    marginBottom: SPACING.sm,
    ...SHADOW.card,
  },
});
