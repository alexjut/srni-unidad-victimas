/**
 * Sprint 20 — Selector de municipio con search bar para preguntas COMBO_DINAMICO.
 *
 * Las preguntas Z2 / Z5A / Z15 / A23A / HV3 / Lud_encuesta son todas pedidos
 * de un municipio DANE. Antes el motor las trataba como LISTA y renderizaba
 * dropdown vacío (porque las opciones no van en el bundle: 1102 muns DANE).
 *
 * Este componente:
 *   - Carga los 1102 municipios al primer uso via parametricasCacheado.
 *   - Cachea en memoria (1 sola petición por sesión de la app).
 *   - Muestra dropdown bottom-sheet con search bar (filtra por nombre).
 *   - Guarda el codigo_dane del municipio elegido (ej. "05001").
 *   - Funciona offline si ya se cacheó antes.
 */
import { useEffect, useMemo, useState } from 'react';
import { View, StyleSheet, Pressable, Modal, FlatList, TextInput as RNTextInput } from 'react-native';
import { Text, ActivityIndicator } from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { parametricasCacheado, type Municipio } from '../api/parametricas';
import { GOV, SPACING, RADIUS, SHADOW, FONT } from '../theme/govTheme';

interface Props {
  /** codigo_dane del municipio actualmente seleccionado, o '' si nada. */
  valor: string;
  /** Llamado con el codigo_dane elegido (ej. "05001"). */
  onChange: (codigoDane: string) => void;
  /** Etiqueta corta a mostrar arriba del trigger. */
  label?: string;
  /** Texto cuando no hay nada seleccionado. */
  placeholder?: string;
}

export function SelectorMunicipio({
  valor,
  onChange,
  label = 'Municipio',
  placeholder = 'Tocar para seleccionar',
}: Props) {
  const [municipios, setMunicipios] = useState<Municipio[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [abierto, setAbierto] = useState(false);
  const [busqueda, setBusqueda] = useState('');

  useEffect(() => {
    let activo = true;
    parametricasCacheado
      .getMunicipiosTodos()
      .then((data) => {
        if (activo) setMunicipios(data);
      })
      .catch(() => {
        if (activo) {
          setError('No se pudo cargar el catálogo de municipios. Verifica tu conexión.');
        }
      })
      .finally(() => { if (activo) setCargando(false); });
    return () => { activo = false; };
  }, []);

  const seleccionado = useMemo(
    () => municipios.find((m) => m.codigo_dane === valor) ?? null,
    [municipios, valor],
  );

  const filtrados = useMemo(() => {
    const q = busqueda.trim().toUpperCase();
    if (!q) return municipios;
    return municipios.filter(
      (m) => m.nombre.toUpperCase().includes(q)
          || (m.departamento_nombre ?? '').toUpperCase().includes(q)
          || m.codigo_dane.includes(q),
    );
  }, [municipios, busqueda]);

  return (
    <View>
      <Pressable
        onPress={() => municipios.length > 0 && setAbierto(true)}
        disabled={cargando || municipios.length === 0}
        style={({ pressed }) => [
          styles.trigger,
          (cargando || error) && styles.triggerDisabled,
          pressed && { opacity: 0.85 },
        ]}
        accessibilityRole="combobox"
        accessibilityLabel={`${label}: ${seleccionado?.nombre ?? placeholder}`}
      >
        <View style={styles.iconoWrap}>
          <MaterialCommunityIcons name="city-variant-outline" size={20} color={GOV.azul} />
        </View>
        <View style={styles.textos}>
          <Text style={styles.label}>{label}</Text>
          {seleccionado ? (
            <Text style={styles.valor} numberOfLines={1}>
              {seleccionado.nombre}
              {seleccionado.departamento_nombre ? `  ·  ${seleccionado.departamento_nombre}` : ''}
            </Text>
          ) : (
            <Text style={styles.placeholder} numberOfLines={1}>
              {cargando ? 'Cargando municipios…' : (error ?? placeholder)}
            </Text>
          )}
        </View>
        {cargando ? (
          <ActivityIndicator size={18} color={GOV.azul} />
        ) : (
          <MaterialCommunityIcons name="chevron-down" size={22} color={GOV.textoT} />
        )}
      </Pressable>

      <Modal
        visible={abierto}
        transparent
        animationType="slide"
        onRequestClose={() => setAbierto(false)}
      >
        <Pressable style={styles.overlay} onPress={() => setAbierto(false)}>
          <Pressable style={styles.card} onPress={(e) => e.stopPropagation()}>
            <View style={styles.handle} />
            <Text style={styles.titulo}>{label}</Text>

            <View style={styles.searchWrap}>
              <MaterialCommunityIcons name="magnify" size={20} color={GOV.textoT} />
              <RNTextInput
                value={busqueda}
                onChangeText={setBusqueda}
                placeholder="Buscar por nombre, departamento o código"
                placeholderTextColor={GOV.textoT}
                style={styles.searchInput}
                autoFocus={false}
              />
              {busqueda ? (
                <Pressable onPress={() => setBusqueda('')}>
                  <MaterialCommunityIcons name="close-circle" size={20} color={GOV.textoT} />
                </Pressable>
              ) : null}
            </View>

            <Text style={styles.contador}>
              {filtrados.length} de {municipios.length}
            </Text>

            <FlatList
              data={filtrados}
              keyExtractor={(item) => item.codigo_dane}
              keyboardShouldPersistTaps="handled"
              style={{ maxHeight: 360 }}
              renderItem={({ item }) => {
                const activo = valor === item.codigo_dane;
                return (
                  <Pressable
                    onPress={() => {
                      onChange(item.codigo_dane);
                      setAbierto(false);
                      setBusqueda('');
                    }}
                    style={({ pressed }) => [
                      styles.opcion,
                      activo && styles.opcionActiva,
                      pressed && { opacity: 0.85 },
                    ]}
                  >
                    <View style={{ flex: 1 }}>
                      <Text style={[styles.opcionNombre, activo && styles.opcionNombreActivo]}>
                        {item.nombre}
                      </Text>
                      <Text style={styles.opcionDepto}>
                        {item.departamento_nombre ?? '—'}  ·  {item.codigo_dane}
                      </Text>
                    </View>
                    {activo && (
                      <MaterialCommunityIcons name="check-circle" size={22} color={GOV.azul} />
                    )}
                  </Pressable>
                );
              }}
              ListEmptyComponent={
                <Text style={styles.vacio}>
                  Sin resultados para "{busqueda}".
                </Text>
              }
            />
          </Pressable>
        </Pressable>
      </Modal>
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
  triggerDisabled: { opacity: 0.6 },
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

  overlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.45)', justifyContent: 'flex-end' },
  card: {
    backgroundColor: GOV.superficie,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    padding: SPACING.md,
    paddingTop: SPACING.sm,
    paddingBottom: SPACING.lg,
    maxHeight: '85%',
  },
  handle: {
    alignSelf: 'center',
    width: 40, height: 4, borderRadius: 2,
    backgroundColor: GOV.borde,
    marginBottom: SPACING.sm,
  },
  titulo: { ...FONT.h3, color: GOV.textoP, marginBottom: SPACING.sm },

  searchWrap: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.sm,
    backgroundColor: GOV.fondoApp,
    borderRadius: RADIUS.md,
    paddingHorizontal: SPACING.md,
    paddingVertical: 8,
    marginBottom: SPACING.sm,
    borderWidth: 1,
    borderColor: GOV.borde,
  },
  searchInput: { flex: 1, ...FONT.body, color: GOV.textoP, padding: 0 },
  contador: { ...FONT.caption, color: GOV.textoT, marginBottom: 4 },

  opcion: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: SPACING.sm,
    paddingHorizontal: SPACING.sm,
    borderRadius: RADIUS.sm,
    gap: SPACING.sm,
    borderBottomWidth: 1,
    borderBottomColor: GOV.borde,
  },
  opcionActiva: { backgroundColor: GOV.azulTenue },
  opcionNombre: { ...FONT.body, color: GOV.textoP, fontWeight: '600' },
  opcionNombreActivo: { color: GOV.azulOscuro },
  opcionDepto: { ...FONT.caption, color: GOV.textoT, marginTop: 2 },
  vacio: { ...FONT.caption, color: GOV.textoT, textAlign: 'center', padding: SPACING.md },
});
