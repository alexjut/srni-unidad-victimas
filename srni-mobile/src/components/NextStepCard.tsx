/**
 * NextStepCard — Tarjeta "Siguiente paso" del Dashboard.
 *
 * Muestra la acción más relevante para el encuestador:
 *   - Si hay sesiones en curso → continuar la última
 *   - Si no → invitar a crear el primer hogar
 */
import { View, StyleSheet, Pressable } from 'react-native';
import { Text } from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { GOV, RADIUS, SHADOW, SPACING, FONT } from '../theme/govTheme';

interface NextStepCardProps {
  title: string;
  description: string;
  icon?: string;
  onPress: () => void;
  progress?: number;   // 0–1, si hay encuesta en curso
}

export function NextStepCard({
  title,
  description,
  icon = 'arrow-right-circle',
  onPress,
  progress,
}: NextStepCardProps) {
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [styles.card, pressed && styles.pressed]}
      accessibilityRole="button"
      accessibilityLabel={title}
    >
      {/* Barra amarilla decorativa izquierda */}
      <View style={styles.accentBar} />

      <View style={styles.body}>
        <View style={styles.header}>
          <View style={styles.labelRow}>
            <Text style={styles.labelTag}>SIGUIENTE PASO</Text>
          </View>
          <MaterialCommunityIcons
            name={icon as any}
            size={28}
            color={GOV.azul}
          />
        </View>

        <Text style={styles.title}>{title}</Text>
        <Text style={styles.description}>{description}</Text>

        {progress != null && (
          <View style={styles.progressWrap}>
            <View style={[styles.progressBar, { width: `${Math.round(progress * 100)}%` }]} />
            <Text style={styles.progressLabel}>{Math.round(progress * 100)}% completado</Text>
          </View>
        )}
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    flexDirection: 'row',
    backgroundColor: GOV.superficie,
    borderRadius: RADIUS.md,
    marginBottom: SPACING.md,
    overflow: 'hidden',
    ...SHADOW.card,
  },
  pressed: {
    transform: [{ scale: 0.99 }],
    opacity: 0.9,
  },
  accentBar: {
    width: 5,
    backgroundColor: GOV.amarillo,
  },
  body: {
    flex: 1,
    padding: SPACING.md,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: SPACING.xs,
  },
  labelRow: {
    backgroundColor: GOV.amarilloTenue,
    borderRadius: 4,
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
  labelTag: {
    fontSize: 10,
    fontWeight: '700',
    color: GOV.azulOscuro,
    letterSpacing: 1,
  },
  title: {
    ...FONT.h3,
    marginBottom: SPACING.xs,
    color: GOV.azulOscuro,
  },
  description: {
    ...FONT.small,
    color: GOV.textoS,
    lineHeight: 20,
  },
  progressWrap: {
    marginTop: SPACING.sm,
  },
  progressBar: {
    height: 4,
    backgroundColor: GOV.azul,
    borderRadius: 2,
    marginBottom: 4,
  },
  progressLabel: {
    ...FONT.caption,
    color: GOV.textoT,
  },
});
