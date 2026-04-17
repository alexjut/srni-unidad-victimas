/**
 * Formulario para crear un nuevo hogar.
 * El encuestador proporciona el UUID del jefe de hogar (obtenido desde búsqueda RNI).
 */
import { useState } from 'react';
import { View, ScrollView, StyleSheet } from 'react-native';
import {
  Text, TextInput, Button, SegmentedButtons,
  HelperText, Divider, ActivityIndicator,
} from 'react-native-paper';
import { router } from 'expo-router';
import { hogaresApi } from '../../../src/api/hogares';

const TIPOS_VIVIENDA = [
  { value: 'CASA', label: 'Casa' },
  { value: 'APARTAMENTO', label: 'Apto.' },
  { value: 'CUARTO', label: 'Cuarto' },
  { value: 'CAMBUCHE', label: 'Cambuche' },
  { value: 'OTRO', label: 'Otro' },
];

const CONDICIONES = [
  { value: 'PROPIA', label: 'Propia' },
  { value: 'PROPIA_PAGANDO', label: 'Pagando' },
  { value: 'ARRIENDO', label: 'Arriendo' },
  { value: 'FAMILIAR', label: 'Familiar' },
  { value: 'INVASION', label: 'Invasión' },
  { value: 'OTRO', label: 'Otro' },
];

export default function NuevoHogarScreen() {
  const [jefeHogar, setJefeHogar] = useState('');
  const [municipio, setMunicipio] = useState('');
  const [tipoVivienda, setTipoVivienda] = useState('CASA');
  const [condicion, setCondicion] = useState('ARRIENDO');
  const [estrato, setEstrato] = useState('');
  const [cuartos, setCuartos] = useState('');
  const [personas, setPersonas] = useState('1');
  const [observaciones, setObservaciones] = useState('');

  const [guardando, setGuardando] = useState(false);
  const [errores, setErrores] = useState<Record<string, string>>({});
  const [errorGeneral, setErrorGeneral] = useState('');

  function validar(): boolean {
    const e: Record<string, string> = {};
    if (!jefeHogar.trim()) e.jefeHogar = 'Ingrese el UUID del jefe de hogar.';
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    if (jefeHogar.trim() && !uuidRegex.test(jefeHogar.trim())) {
      e.jefeHogar = 'Formato de UUID inválido (ej: a1b2c3d4-…).';
    }
    const pers = parseInt(personas, 10);
    if (!personas || isNaN(pers) || pers < 1) e.personas = 'Ingrese al menos 1 persona.';
    setErrores(e);
    return Object.keys(e).length === 0;
  }

  async function guardar() {
    if (!validar()) return;
    setGuardando(true);
    setErrorGeneral('');
    try {
      await hogaresApi.crear({
        jefe_hogar: jefeHogar.trim(),
        municipio: municipio ? parseInt(municipio, 10) : undefined,
        tipo_vivienda: tipoVivienda,
        condicion_ocupacion: condicion,
        estrato: estrato ? parseInt(estrato, 10) : 0,
        numero_cuartos: cuartos ? parseInt(cuartos, 10) : 0,
        numero_personas: parseInt(personas, 10),
        observaciones,
      });
      router.back();
    } catch (err: any) {
      const detalle = err?.response?.data;
      if (typeof detalle === 'object') {
        const msgs: Record<string, string> = {};
        for (const [k, v] of Object.entries(detalle)) {
          msgs[k] = Array.isArray(v) ? v.join(' ') : String(v);
        }
        setErrores(msgs);
      } else {
        setErrorGeneral('No se pudo guardar el hogar. Intente nuevamente.');
      }
    } finally {
      setGuardando(false);
    }
  }

  return (
    <ScrollView style={styles.root} contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
      <Text variant="titleMedium" style={styles.seccion}>Jefe de hogar</Text>
      <TextInput
        label="UUID del jefe de hogar *"
        value={jefeHogar}
        onChangeText={setJefeHogar}
        mode="outlined"
        autoCapitalize="none"
        autoCorrect={false}
        placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
        error={!!errores.jefeHogar}
      />
      {errores.jefeHogar && <HelperText type="error">{errores.jefeHogar}</HelperText>}
      <HelperText type="info">
        Obtenga el UUID desde la pantalla de Búsqueda RNI.
      </HelperText>

      <Divider style={styles.divider} />
      <Text variant="titleMedium" style={styles.seccion}>Ubicación</Text>
      <TextInput
        label="ID de municipio"
        value={municipio}
        onChangeText={setMunicipio}
        mode="outlined"
        keyboardType="numeric"
        placeholder="Ej: 11001"
      />

      <Divider style={styles.divider} />
      <Text variant="titleMedium" style={styles.seccion}>Tipo de vivienda</Text>
      <SegmentedButtons
        value={tipoVivienda}
        onValueChange={setTipoVivienda}
        buttons={TIPOS_VIVIENDA}
        style={styles.segmented}
      />

      <Text variant="titleMedium" style={[styles.seccion, { marginTop: 16 }]}>Condición de ocupación</Text>
      <SegmentedButtons
        value={condicion}
        onValueChange={setCondicion}
        buttons={CONDICIONES}
        style={styles.segmented}
      />

      <Divider style={styles.divider} />
      <Text variant="titleMedium" style={styles.seccion}>Características</Text>
      <View style={styles.fila}>
        <TextInput
          label="Estrato"
          value={estrato}
          onChangeText={setEstrato}
          mode="outlined"
          keyboardType="numeric"
          style={styles.inputMitad}
        />
        <TextInput
          label="N.º cuartos"
          value={cuartos}
          onChangeText={setCuartos}
          mode="outlined"
          keyboardType="numeric"
          style={styles.inputMitad}
        />
      </View>
      <TextInput
        label="Personas en la vivienda *"
        value={personas}
        onChangeText={setPersonas}
        mode="outlined"
        keyboardType="numeric"
        error={!!errores.personas}
      />
      {errores.personas && <HelperText type="error">{errores.personas}</HelperText>}

      <Divider style={styles.divider} />
      <TextInput
        label="Observaciones"
        value={observaciones}
        onChangeText={setObservaciones}
        mode="outlined"
        multiline
        numberOfLines={3}
      />

      {errorGeneral ? <Text style={styles.error}>{errorGeneral}</Text> : null}

      <Button
        mode="contained"
        onPress={guardar}
        disabled={guardando}
        style={styles.boton}
        icon={guardando ? undefined : 'home-plus'}
      >
        {guardando ? <ActivityIndicator size="small" color="#FFF" /> : 'Guardar hogar'}
      </Button>

      <Button mode="outlined" onPress={() => router.back()} style={styles.cancelar}>
        Cancelar
      </Button>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#F5F5F5' },
  content: { padding: 16, paddingBottom: 40 },
  seccion: { fontWeight: '600', color: '#1565C0', marginBottom: 8 },
  divider: { marginVertical: 16 },
  segmented: { marginBottom: 4 },
  fila: { flexDirection: 'row', gap: 12, marginBottom: 12 },
  inputMitad: { flex: 1 },
  boton: { marginTop: 24 },
  cancelar: { marginTop: 8 },
  error: { color: '#C62828', marginTop: 12, textAlign: 'center' },
});
