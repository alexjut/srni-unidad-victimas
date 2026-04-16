/**
 * Detalle de un hogar: información general, lista de miembros y acceso a encuestas.
 */
import { useEffect, useState } from 'react';
import { View, ScrollView, StyleSheet, Alert } from 'react-native';
import {
  Text, Card, Chip, Button, Divider,
  ActivityIndicator, List, FAB,
} from 'react-native-paper';
import { router, useLocalSearchParams, Stack } from 'expo-router';
import { hogaresApi } from '../../../src/api/hogares';
import { encuestasApi } from '../../../src/api/encuestas';
import type { HogarDetalle, MiembroHogarResumen } from '../../../src/types';

const PARENTESCO_LABEL: Record<string, string> = {
  JEFE: 'Jefe/a', CONYUGE: 'Cónyuge', HIJO_A: 'Hijo/a',
  YERNO_NUERA: 'Yerno/Nuera', NIETO_A: 'Nieto/a',
  PADRE_MADRE: 'Padre/Madre', HERMANO_A: 'Hermano/a',
  OTRO_PARIENTE: 'Pariente', NO_PARIENTE: 'Sin parentesco',
};

export default function HogarDetalleScreen() {
  const { hogarId } = useLocalSearchParams<{ hogarId: string }>();
  const [hogar, setHogar] = useState<HogarDetalle | null>(null);
  const [cargando, setCargando] = useState(true);
  const [iniciandoSesion, setIniciandoSesion] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!hogarId) return;
    hogaresApi.detalle(hogarId)
      .then((res) => setHogar(res.data))
      .catch(() => setError('No se pudo cargar el hogar.'))
      .finally(() => setCargando(false));
  }, [hogarId]);

  async function iniciarEncuesta() {
    if (!hogar) return;
    // El instrumento 1 es el PAARI por defecto — en producción se selecciona dinámicamente
    const INSTRUMENTO_PAARI = 1;
    setIniciandoSesion(true);
    try {
      const res = await encuestasApi.crear({
        hogar: hogar.id,
        instrumento: INSTRUMENTO_PAARI,
      });
      router.push({
        pathname: '/(main)/encuestas/[sesionId]',
        params: { sesionId: res.data.id },
      });
    } catch (err: any) {
      const msg = err?.response?.data?.detail ?? 'No se pudo iniciar la sesión.';
      Alert.alert('Error', msg);
    } finally {
      setIniciandoSesion(false);
    }
  }

  if (cargando) {
    return (
      <View style={styles.centrado}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  if (error || !hogar) {
    return (
      <View style={styles.centrado}>
        <Text style={styles.errorTxt}>{error || 'Hogar no encontrado.'}</Text>
        <Button onPress={() => router.back()}>Volver</Button>
      </View>
    );
  }

  return (
    <>
      <Stack.Screen options={{ title: `Hogar ${hogar.id.slice(0, 8)}…` }} />
      <ScrollView style={styles.root} contentContainerStyle={styles.content}>

        {/* Estado */}
        <View style={styles.estadoRow}>
          <Chip
            mode="flat"
            style={{ backgroundColor: hogar.estado === 'ACTIVO' ? '#E8F5E9' : '#FFF3E0' }}
            textStyle={{ color: hogar.estado === 'ACTIVO' ? '#2E7D32' : '#E65100' }}
          >
            {hogar.estado_display}
          </Chip>
          <Text variant="labelSmall" style={styles.fecha}>
            {new Date(hogar.created_at).toLocaleDateString('es-CO')}
          </Text>
        </View>

        {/* Datos de vivienda */}
        <Card style={styles.card}>
          <Card.Title title="Datos de vivienda" />
          <Card.Content>
            <Fila label="Tipo" valor={hogar.tipo_vivienda_display} />
            <Fila label="Ocupación" valor={hogar.condicion_ocupacion_display} />
            <Fila label="Estrato" valor={String(hogar.estrato)} />
            <Fila label="Cuartos" valor={String(hogar.numero_cuartos)} />
            <Fila label="Personas" valor={String(hogar.numero_personas)} />
            {hogar.observaciones ? (
              <Fila label="Obs." valor={hogar.observaciones} />
            ) : null}
          </Card.Content>
        </Card>

        {/* Miembros */}
        <Card style={styles.card}>
          <Card.Title
            title="Miembros del hogar"
            subtitle={`${hogar.miembros.length} registrado${hogar.miembros.length !== 1 ? 's' : ''}`}
          />
          <Card.Content>
            {hogar.miembros.length === 0 ? (
              <Text variant="bodySmall" style={styles.sinMiembros}>
                No se han registrado miembros aún.
              </Text>
            ) : (
              hogar.miembros.map((m) => <MiembroItem key={m.id} miembro={m} />)
            )}
          </Card.Content>
        </Card>

        {/* Sesiones */}
        <Card style={styles.card}>
          <Card.Title
            title="Encuestas"
            subtitle={`${hogar.total_sesiones} sesión${hogar.total_sesiones !== 1 ? 'es' : ''}`}
          />
          <Card.Content>
            <Button
              mode="contained"
              icon="clipboard-text-play"
              loading={iniciandoSesion}
              disabled={iniciandoSesion}
              onPress={iniciarEncuesta}
            >
              Nueva sesión PAARI
            </Button>
            {hogar.total_sesiones > 0 && (
              <Button
                mode="outlined"
                icon="clipboard-list"
                style={{ marginTop: 8 }}
                onPress={() =>
                  router.push({
                    pathname: '/(main)/encuestas',
                    params: { hogar: hogar.id },
                  })
                }
              >
                Ver sesiones de este hogar
              </Button>
            )}
          </Card.Content>
        </Card>

        <Button
          mode="text"
          icon="chevron-left"
          onPress={() => router.back()}
          style={styles.volver}
        >
          Volver a la lista
        </Button>
      </ScrollView>
    </>
  );
}

function Fila({ label, valor }: { label: string; valor: string }) {
  return (
    <View style={filaStyles.root}>
      <Text variant="labelSmall" style={filaStyles.label}>{label}</Text>
      <Text variant="bodySmall" style={filaStyles.valor}>{valor || '—'}</Text>
    </View>
  );
}

const filaStyles = StyleSheet.create({
  root: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 3 },
  label: { color: '#9E9E9E', flex: 1 },
  valor: { flex: 2, textAlign: 'right', color: '#212121' },
});

function MiembroItem({ miembro }: { miembro: MiembroHogarResumen }) {
  return (
    <View style={miembroStyles.root}>
      <Text variant="bodySmall" style={miembroStyles.parentesco}>
        {PARENTESCO_LABEL[miembro.parentesco] ?? miembro.parentesco}
      </Text>
      <Text variant="bodySmall" style={miembroStyles.dato}>
        {miembro.genero} · {miembro.edad != null ? `${miembro.edad} años` : 'edad N/D'}
      </Text>
    </View>
  );
}

const miembroStyles = StyleSheet.create({
  root: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 4,
    borderBottomWidth: 1,
    borderBottomColor: '#F0F0F0',
  },
  parentesco: { color: '#1565C0', fontWeight: '600' },
  dato: { color: '#616161' },
});

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#F5F5F5' },
  content: { padding: 16, paddingBottom: 40 },
  centrado: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 32 },
  estadoRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
  fecha: { color: '#9E9E9E' },
  card: { marginBottom: 12, backgroundColor: '#FFFFFF' },
  sinMiembros: { color: '#9E9E9E', fontStyle: 'italic' },
  errorTxt: { color: '#C62828', marginBottom: 16 },
  volver: { marginTop: 8 },
});
