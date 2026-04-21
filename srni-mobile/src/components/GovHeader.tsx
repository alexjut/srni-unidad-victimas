/**
 * GovHeader — Cabecera institucional GOV.CO
 *
 * Estructura:
 *   ┌─────────────────────────────────┐  ← safe area top
 *   │ GOV.CO            (amarillo)    │  28 px
 *   ├─────────────────────────────────┤
 *   │ ← [título]      [right slot]   │  56 px  (azul)
 *   │   [subtítulo]                   │
 *   └─────────────────────────────────┘
 */
import { View, StyleSheet, StatusBar, Platform } from 'react-native';
import { Text, IconButton } from 'react-native-paper';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { GOV } from '../theme/govTheme';

interface GovHeaderProps {
  title: string;
  subtitle?: string;
  onBack?: () => void;
  right?: React.ReactNode;
}

export function GovHeader({ title, subtitle, onBack, right }: GovHeaderProps) {
  const insets = useSafeAreaInsets();
  // En Android el StatusBar ocupa espacio; en iOS usamos el inset real
  const topPad = Platform.OS === 'android'
    ? (StatusBar.currentHeight ?? 24)
    : insets.top;

  return (
    <View style={[styles.wrapper, { paddingTop: topPad }]}>
      {/* Franja amarilla GOV.CO */}
      <View style={styles.govStripe}>
        <Text style={styles.govText}>GOV.CO</Text>
      </View>

      {/* Barra azul con título */}
      <View style={styles.blueBar}>
        {onBack && (
          <IconButton
            icon="arrow-left"
            iconColor="#FFFFFF"
            size={22}
            onPress={onBack}
            style={styles.backBtn}
            accessibilityLabel="Volver"
          />
        )}
        <View style={[styles.titleWrap, !onBack && styles.titleWrapNoPad]}>
          <Text style={styles.title} numberOfLines={1}>{title}</Text>
          {subtitle ? (
            <Text style={styles.subtitle} numberOfLines={1}>{subtitle}</Text>
          ) : null}
        </View>
        {right ? <View style={styles.rightSlot}>{right}</View> : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    backgroundColor: GOV.azul,    // visible detrás de la franja amarilla en el inset
  },
  govStripe: {
    height: GOV.alturaFranjaGov,
    backgroundColor: GOV.amarillo,
    justifyContent: 'center',
    paddingHorizontal: 16,
  },
  govText: {
    fontSize: 11,
    fontWeight: '700',
    color: GOV.azulOscuro,
    letterSpacing: 1.5,
  },
  blueBar: {
    height: 56,
    backgroundColor: GOV.azul,
    flexDirection: 'row',
    alignItems: 'center',
    paddingRight: 8,
  },
  backBtn: {
    margin: 0,
    marginLeft: 4,
  },
  titleWrap: {
    flex: 1,
    paddingLeft: 4,
    justifyContent: 'center',
  },
  titleWrapNoPad: {
    paddingLeft: 16,
  },
  title: {
    fontSize: 17,
    fontWeight: '700',
    color: '#FFFFFF',
    lineHeight: 22,
  },
  subtitle: {
    fontSize: 12,
    color: 'rgba(255,255,255,0.75)',
    lineHeight: 16,
    marginTop: 1,
  },
  rightSlot: {
    flexDirection: 'row',
    alignItems: 'center',
  },
});
