/**
 * GovButton — Botón institucional GOV.CO
 *
 * Variantes:
 *   primary   — relleno azul #1565C0 (acción principal)
 *   secondary — outline azul (acción secundaria)
 *   danger    — relleno rojo (acciones destructivas)
 *   ghost     — solo texto azul (acción terciaria)
 */
import { Pressable, View, StyleSheet, ActivityIndicator } from 'react-native';
import { Text } from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { GOV, RADIUS, SPACING } from '../theme/govTheme';

type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost';

interface GovButtonProps {
  label: string;
  onPress: () => void;
  variant?: ButtonVariant;
  icon?: string;
  loading?: boolean;
  disabled?: boolean;
  fullWidth?: boolean;
  accessibilityLabel?: string;
}

export function GovButton({
  label,
  onPress,
  variant = 'primary',
  icon,
  loading = false,
  disabled = false,
  fullWidth = true,
  accessibilityLabel,
}: GovButtonProps) {
  const isDisabled = disabled || loading;

  const containerStyle = [
    styles.base,
    fullWidth && styles.fullWidth,
    variant === 'primary'   && styles.primary,
    variant === 'secondary' && styles.secondary,
    variant === 'danger'    && styles.danger,
    variant === 'ghost'     && styles.ghost,
    isDisabled              && styles.disabled,
  ];

  const textColor =
    variant === 'primary'   ? '#FFFFFF' :
    variant === 'danger'    ? '#FFFFFF' :
    variant === 'secondary' ? GOV.azul  :
    GOV.azul;

  return (
    <Pressable
      onPress={isDisabled ? undefined : onPress}
      style={({ pressed }) => [
        ...containerStyle,
        pressed && !isDisabled && styles.pressed,
      ]}
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel ?? label}
      accessibilityState={{ disabled: isDisabled }}
    >
      {loading ? (
        <ActivityIndicator
          size="small"
          color={variant === 'primary' || variant === 'danger' ? '#FFFFFF' : GOV.azul}
        />
      ) : (
        <View style={styles.inner}>
          {icon ? (
            <MaterialCommunityIcons
              name={icon as any}
              size={20}
              color={textColor}
              style={styles.icon}
            />
          ) : null}
          <Text style={[styles.label, { color: textColor }]}>{label}</Text>
        </View>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    height: 48,
    borderRadius: RADIUS.md - 2,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: SPACING.md,
    minHeight: 48,  // WCAG touch target
  },
  fullWidth: {
    width: '100%',
  },
  primary: {
    backgroundColor: GOV.azul,
  },
  secondary: {
    backgroundColor: 'transparent',
    borderWidth: 1.5,
    borderColor: GOV.azul,
  },
  danger: {
    backgroundColor: GOV.rojo,
  },
  ghost: {
    backgroundColor: 'transparent',
  },
  disabled: {
    opacity: 0.45,
  },
  pressed: {
    transform: [{ scale: 0.98 }],
    opacity: 0.88,
  },
  inner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  icon: {
    marginRight: 2,
  },
  label: {
    fontSize: 15,
    fontWeight: '600',
    letterSpacing: 0.3,
  },
});
