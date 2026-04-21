/**
 * EmptyState — Estado vacío ilustrado con mensaje cálido.
 */
import { View, StyleSheet } from 'react-native';
import { Text } from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { GovButton } from './GovButton';
import { GOV, SPACING, FONT } from '../theme/govTheme';

interface EmptyStateProps {
  icon?: string;
  title: string;
  message: string;
  actionLabel?: string;
  onAction?: () => void;
}

export function EmptyState({
  icon = 'folder-open-outline',
  title,
  message,
  actionLabel,
  onAction,
}: EmptyStateProps) {
  return (
    <View style={styles.root}>
      <View style={styles.iconWrap}>
        <MaterialCommunityIcons name={icon as any} size={64} color={GOV.borde} />
      </View>
      <Text style={styles.title}>{title}</Text>
      <Text style={styles.message}>{message}</Text>
      {actionLabel && onAction ? (
        <View style={styles.actionWrap}>
          <GovButton label={actionLabel} onPress={onAction} fullWidth={false} />
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: SPACING.xl,
  },
  iconWrap: {
    width: 100,
    height: 100,
    borderRadius: 50,
    backgroundColor: GOV.fondoApp,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: SPACING.lg,
    borderWidth: 1,
    borderColor: GOV.borde,
  },
  title: {
    ...FONT.h3,
    textAlign: 'center',
    marginBottom: SPACING.sm,
  },
  message: {
    ...FONT.body,
    textAlign: 'center',
    color: GOV.textoS,
    lineHeight: 22,
    marginBottom: SPACING.lg,
  },
  actionWrap: {
    marginTop: SPACING.sm,
  },
});
