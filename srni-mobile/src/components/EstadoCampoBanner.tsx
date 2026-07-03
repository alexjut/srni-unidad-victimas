/**
 * EstadoCampoBanner — indicador claro de "listo para campo".
 *
 * Le dice al encuestador, de un vistazo, si puede trabajar sin internet:
 *   🟢 Conectado · datos al día (en línea)
 *   🟡 Sin conexión · listo para campo (N víctimas precargadas)
 *   🔴 Sin conexión · SIN datos precargados → conéctate antes de salir
 */
import { useEffect, useState } from 'react';
import { View, StyleSheet } from 'react-native';
import { Text } from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useSyncStore } from '../stores/syncStore';
import * as precargaDao from '../db/precargaDao';
import { GOV, SPACING, RADIUS, FONT } from '../theme/govTheme';

export function EstadoCampoBanner() {
  const estaOnline = useSyncStore((s) => s.estaOnline);
  const [padron, setPadron] = useState<number | null>(null);

  useEffect(() => {
    let activo = true;
    precargaDao
      .contarPrecarga()
      .then((c) => { if (activo) setPadron(c.padron); })
      .catch(() => { if (activo) setPadron(0); });
    return () => { activo = false; };
  }, [estaOnline]);

  const hayDatos = (padron ?? 0) > 0;

  const cfg = estaOnline
    ? {
        icon: 'cloud-check' as const,
        color: GOV.verde,
        bg: GOV.verdeTenue,
        titulo: 'Conectado',
        sub: 'Datos al día · se sincroniza en línea',
      }
    : hayDatos
    ? {
        icon: 'cloud-check' as const,
        color: GOV.naranja,
        bg: GOV.naranjaTenue,
        titulo: 'Sin conexión · listo para campo',
        sub: `${padron} víctimas precargadas · puedes trabajar offline`,
      }
    : {
        icon: 'alert-circle' as const,
        color: GOV.rojo,
        bg: GOV.rojoTenue,
        titulo: 'Sin conexión · sin datos',
        sub: 'Conéctate para descargar la jornada antes de salir a campo',
      };

  return (
    <View style={[styles.wrap, { backgroundColor: cfg.bg, borderColor: cfg.color }]}>
      <MaterialCommunityIcons name={cfg.icon} size={24} color={cfg.color} />
      <View style={styles.txtWrap}>
        <Text style={[styles.titulo, { color: cfg.color }]} numberOfLines={1}>
          {cfg.titulo}
        </Text>
        <Text style={styles.sub} numberOfLines={2}>{cfg.sub}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.sm,
    padding: SPACING.md,
    borderRadius: RADIUS.md,
    borderWidth: 1,
    marginBottom: SPACING.md,
  },
  txtWrap: { flex: 1 },
  titulo: { ...FONT.h3, fontWeight: '700' },
  sub: { ...FONT.caption, color: GOV.textoS, marginTop: 1 },
});
