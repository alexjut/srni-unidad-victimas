/**
 * Sprint 21 — Selector de fecha con calendario nativo.
 *
 * Reemplaza el TextInput numérico con placeholder AAAA-MM-DD que tenía el
 * motor del formulario. Usa el datetimepicker nativo del SO (Android/iOS).
 *
 * - Guarda el valor como string ISO YYYY-MM-DD (compatible con backend Django).
 * - max=hoy por defecto (válido para fecha de nacimiento, fecha de hecho).
 * - Si la pregunta no tiene fecha previa, abre en el día actual.
 * - Si no se puede usar el picker (web/SSR), cae al TextInput como fallback.
 */
import { useState } from 'react';
import { View, Pressable, StyleSheet, Platform } from 'react-native';
import { Text, TextInput as PaperTextInput } from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import DateTimePicker, { type DateTimePickerEvent } from '@react-native-community/datetimepicker';
import { GOV, SPACING, RADIUS, SHADOW, FONT } from '../theme/govTheme';

interface Props {
  /** Fecha actual en formato ISO YYYY-MM-DD, o '' si no se ha seleccionado. */
  valor: string;
  /** Llamado con la fecha elegida en formato ISO YYYY-MM-DD. */
  onChange: (isoDate: string) => void;
  /** Etiqueta visible. */
  label?: string;
  /** Si la pregunta es 'fecha de nacimiento' u 'ocurrencia del hecho', no permitimos futuro. */
  permitirFuturo?: boolean;
}

const MESES = [
  'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
  'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre',
];

function formatearLargo(iso: string): string {
  // iso = 'YYYY-MM-DD'
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
  if (!m) return iso;
  const [, y, mm, dd] = m;
  const mes = MESES[Number(mm) - 1] ?? mm;
  return `${Number(dd)} de ${mes} de ${y}`;
}

function parseIso(iso: string): Date {
  if (!iso) return new Date();
  const d = new Date(iso + 'T00:00:00');
  return isNaN(d.getTime()) ? new Date() : d;
}

function toIso(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${dd}`;
}

export function SelectorFecha({
  valor,
  onChange,
  label = 'Fecha',
  permitirFuturo = false,
}: Props) {
  const [abierto, setAbierto] = useState(false);

  function manejarCambio(_event: DateTimePickerEvent, fecha?: Date) {
    // Android: el picker se cierra automáticamente al seleccionar/cancelar
    // iOS: queda abierto (lo cerramos manualmente abajo).
    if (Platform.OS === 'android') setAbierto(false);
    if (_event.type === 'dismissed') return;
    if (fecha) onChange(toIso(fecha));
  }

  if (Platform.OS === 'web') {
    // Web: el datetimepicker no está disponible. Caemos al TextInput.
    return (
      <PaperTextInput
        value={valor}
        onChangeText={onChange}
        placeholder="AAAA-MM-DD"
        keyboardType="numeric"
        style={styles.fallback}
        dense
        right={<PaperTextInput.Icon icon="calendar" />}
      />
    );
  }

  return (
    <View>
      <Pressable
        onPress={() => setAbierto(true)}
        style={({ pressed }) => [styles.trigger, pressed && { opacity: 0.85 }]}
        accessibilityRole="button"
        accessibilityLabel={`${label}: ${valor || 'sin seleccionar'}`}
      >
        <View style={styles.iconoWrap}>
          <MaterialCommunityIcons name="calendar-blank" size={20} color={GOV.azul} />
        </View>
        <View style={styles.textos}>
          <Text style={styles.label}>{label}</Text>
          {valor ? (
            <Text style={styles.valor} numberOfLines={1}>{formatearLargo(valor)}</Text>
          ) : (
            <Text style={styles.placeholder} numberOfLines={1}>Tocar para abrir el calendario</Text>
          )}
        </View>
        <MaterialCommunityIcons name="chevron-down" size={22} color={GOV.textoT} />
      </Pressable>

      {abierto && (
        <>
          <DateTimePicker
            value={parseIso(valor)}
            mode="date"
            display={Platform.OS === 'ios' ? 'inline' : 'default'}
            maximumDate={permitirFuturo ? undefined : new Date()}
            minimumDate={new Date(1900, 0, 1)}
            onChange={manejarCambio}
            locale="es-CO"
          />
          {Platform.OS === 'ios' && (
            <Pressable onPress={() => setAbierto(false)} style={styles.cerrarBtn}>
              <Text style={styles.cerrarTxt}>Cerrar calendario</Text>
            </Pressable>
          )}
        </>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  trigger: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: GOV.superficie,
    borderRadius: RADIUS.md,
    paddingHorizontal: SPACING.md,
    paddingVertical: SPACING.sm,
    borderWidth: 1,
    borderColor: GOV.borde,
    ...SHADOW.card,
  },
  iconoWrap: {
    width: 36, height: 36, borderRadius: 18,
    backgroundColor: GOV.azulTenue,
    justifyContent: 'center', alignItems: 'center',
    marginRight: SPACING.sm,
  },
  textos: { flex: 1 },
  label: { ...FONT.caption, color: GOV.textoT, marginBottom: 2 },
  valor: { ...FONT.body, fontWeight: '600', color: GOV.textoP },
  placeholder: { ...FONT.body, color: GOV.textoT, fontStyle: 'italic' },

  fallback: { backgroundColor: GOV.superficie, marginTop: 4 },

  cerrarBtn: {
    alignItems: 'center',
    paddingVertical: SPACING.sm,
    marginTop: 4,
    backgroundColor: GOV.azulTenue,
    borderRadius: RADIUS.sm,
  },
  cerrarTxt: { ...FONT.caption, color: GOV.azulOscuro, fontWeight: '700' },
});
