// Crear nuevo hogar — online (POST directo) u offline (cola de sync).
import { useState } from 'react';
import { View, ScrollView, StyleSheet } from 'react-native';
import {
  Text, TextInput, Button, SegmentedButtons,
  HelperText, Divider, ActivityIndicator, Chip, Surface,
} from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { hogaresApi } from '../../../src/api/hogares';
import { encuestasApi } from '../../../src/api/encuestas';
import * as hogaresOfflineDao from '../../../src/db/hogaresOfflineDao';
import * as colaDao from '../../../src/db/colaDao';
import { useSyncStore } from '../../../src/stores/syncStore';
import { useCaracterizacionStore } from '../../../src/stores/caracterizacionStore';

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
  const { estaOnline, refrescarContadores } = useSyncStore();
  const { victimaFuente, victimaLocalId, limpiar, setHogarId, instrumentoId, rutaEntrevista } = useCaracterizacionStore();
  const tieneAutorizadoPrecargado = !!victimaLocalId;

  const [autorizadoUuid, setAutorizadoUuid] = useState(victimaLocalId ?? '');
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
    if (!tieneAutorizadoPrecargado) {
      if (!autorizadoUuid.trim()) e.autorizado = 'Ingrese el UUID del autorizado/titular.';
      const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
      if (autorizadoUuid.trim() && !uuidRegex.test(autorizadoUuid.trim())) {
        e.autorizado = 'Formato de UUID inválido (ej: a1b2c3d4-…).';
      }
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

    const campos = {
      autorizado_uuid: autorizadoUuid.trim(),
      municipio_id: municipio ? parseInt(municipio, 10) : undefined,
      tipo_vivienda: tipoVivienda,
      condicion_ocupacion: condicion,
      estrato: estrato ? parseInt(estrato, 10) : 0,
      numero_cuartos: cuartos ? parseInt(cuartos, 10) : 0,
      numero_personas: parseInt(personas, 10),
      observaciones,
    };

    try {
      if (estaOnline) {
        // Camino feliz: crear hogar directamente en servidor.
        // El backend auto-inserta al autorizado como primer MiembroHogar.
        const { data: hogarCreado } = await hogaresApi.crear({
          autorizado: campos.autorizado_uuid,
          municipio: campos.municipio_id,
          tipo_vivienda: campos.tipo_vivienda,
          condicion_ocupacion: campos.condicion_ocupacion,
          estrato: campos.estrato,
          numero_cuartos: campos.numero_cuartos,
          numero_personas: campos.numero_personas,
          observaciones: campos.observaciones,
        });
        setHogarId(hogarCreado.id);

        // Si viene del flujo búsqueda con instrumento pre-seleccionado: crear sesión y arrancar
        if (instrumentoId) {
          const { data: sesion } = await encuestasApi.crear({
            hogar: hogarCreado.id,
            instrumento: instrumentoId,
            ruta_entrevista: rutaEntrevista,
          });
          limpiar();
          router.replace({ pathname: '/(main)/encuestas/[sesionId]', params: { sesionId: sesion.id } });
          return;
        }

        // Sin instrumento pre-seleccionado: ir al detalle del hogar (flujo normal)
        router.replace({ pathname: '/(main)/hogares/[hogarId]', params: { hogarId: hogarCreado.id } });
        return;
      } else {
        // Sin red: guardar localmente y encolar.
        // El DAO usa jefe_hogar_uuid (nombre histórico de la columna SQLite);
        // en el dominio actual ese UUID es el del autorizado.
        const hogarLocal = await hogaresOfflineDao.crearHogarOffline({
          jefe_hogar_uuid: campos.autorizado_uuid,
          municipio_id: campos.municipio_id,
          tipo_vivienda: campos.tipo_vivienda,
          condicion_ocupacion: campos.condicion_ocupacion,
          estrato: campos.estrato,
          numero_cuartos: campos.numero_cuartos,
          numero_personas: campos.numero_personas,
          observaciones: campos.observaciones,
        });
        await colaDao.encolar('CREAR_HOGAR', hogarLocal.id_local, {
          id_local: hogarLocal.id_local,
          autorizado: campos.autorizado_uuid,
          municipio: campos.municipio_id,
          tipo_vivienda: campos.tipo_vivienda,
          condicion_ocupacion: campos.condicion_ocupacion,
          estrato: campos.estrato,
          numero_cuartos: campos.numero_cuartos,
          numero_personas: campos.numero_personas,
          observaciones: campos.observaciones,
        });
        await refrescarContadores();
        limpiar();
        router.back();
      }
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

      {!estaOnline && (
        <Chip
          icon="wifi-off"
          mode="flat"
          style={styles.offlineBanner}
          textStyle={styles.offlineTxt}
        >
          Sin conexión — se guardará localmente y sincronizará al recuperar señal
        </Chip>
      )}

      <Text variant="titleMedium" style={styles.seccion}>Autorizado / Titular</Text>
      {tieneAutorizadoPrecargado && victimaFuente ? (
        <Surface style={styles.jefeCard} elevation={2}>
          <View style={styles.jefeCardRow}>
            <MaterialCommunityIcons name="account-check" size={28} color="#2E7D32" style={styles.jefeCardIcon} />
            <View style={styles.jefeCardTextos}>
              <Text style={styles.jefeCardTitulo}>Autorizado / Titular confirmado</Text>
              <Text style={styles.jefeCardNombre}>
                {[
                  victimaFuente.primer_nombre,
                  victimaFuente.segundo_nombre,
                  victimaFuente.primer_apellido,
                  victimaFuente.segundo_apellido,
                ].filter(Boolean).join(' ')}
              </Text>
              <Text style={styles.jefeCardDoc}>
                {victimaFuente.tipo_documento} — *** (datos protegidos)
              </Text>
              <Text style={styles.jefeCardUuid}>
                UUID: {victimaLocalId?.slice(0, 8)}…
              </Text>
            </View>
          </View>
        </Surface>
      ) : (
        <>
          <TextInput
            label="UUID del autorizado / titular *"
            value={autorizadoUuid}
            onChangeText={setAutorizadoUuid}
            mode="outlined"
            autoCapitalize="none"
            autoCorrect={false}
            placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
            error={!!errores.autorizado}
          />
          {errores.autorizado && <HelperText type="error">{errores.autorizado}</HelperText>}
          <HelperText type="info">Obtenga el UUID desde la pantalla de Búsqueda RNI.</HelperText>
        </>
      )}

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
        icon={guardando ? undefined : estaOnline ? 'home-plus' : 'home-clock'}
      >
        {guardando
          ? <ActivityIndicator size="small" color="#FFF" />
          : estaOnline ? 'Guardar hogar' : 'Guardar offline'}
      </Button>

      <Button mode="outlined" onPress={() => { limpiar(); router.back(); }} style={styles.cancelar}>
        Cancelar
      </Button>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#F5F5F5' },
  content: { padding: 16, paddingBottom: 40 },
  offlineBanner: { marginBottom: 16, backgroundColor: '#FFF3E0' },
  offlineTxt: { color: '#E65100', fontSize: 12 },
  seccion: { fontWeight: '600', color: '#1565C0', marginBottom: 8 },
  divider: { marginVertical: 16 },
  segmented: { marginBottom: 4 },
  fila: { flexDirection: 'row', gap: 12, marginBottom: 12 },
  inputMitad: { flex: 1 },
  boton: { marginTop: 24 },
  cancelar: { marginTop: 8 },
  error: { color: '#C62828', marginTop: 12, textAlign: 'center' },
  // Jefe de hogar precargado
  jefeCard: {
    borderRadius: 12,
    padding: 16,
    backgroundColor: '#E8F5E9',
    marginBottom: 4,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.08,
    shadowRadius: 4,
  },
  jefeCardRow: { flexDirection: 'row', alignItems: 'flex-start' },
  jefeCardIcon: { marginRight: 12, marginTop: 2 },
  jefeCardTextos: { flex: 1 },
  jefeCardTitulo: { fontWeight: '700', color: '#2E7D32', fontSize: 14, marginBottom: 4 },
  jefeCardNombre: { fontSize: 15, color: '#212121', marginBottom: 2 },
  jefeCardDoc: { fontSize: 13, color: '#616161', marginBottom: 2 },
  jefeCardUuid: { fontSize: 12, color: '#1565C0' },
});
