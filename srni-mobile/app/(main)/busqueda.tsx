/**
 * Pantalla de búsqueda en el RNI.
 * La búsqueda se ejecuta SIEMPRE en el servidor — NUNCA en el cliente.
 * No se cachea ningún resultado de búsqueda en el dispositivo.
 */
import { useState } from 'react';
import { View, FlatList, StyleSheet } from 'react-native';
import {
  Searchbar,
  Card,
  Text,
  SegmentedButtons,
  ActivityIndicator,
  HelperText,
} from 'react-native-paper';
import apiClient from '../../src/api/client';

interface ResultadoBusqueda {
  id: string;
  tipo_documento: string;
  estado_ruv: string;
  genero: string;
  pertenencia_etnica: string;
}

export default function BusquedaScreen() {
  const [tipoDoc, setTipoDoc] = useState('CC');
  const [documento, setDocumento] = useState('');
  const [resultados, setResultados] = useState<ResultadoBusqueda[]>([]);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [buscado, setBuscado] = useState(false);

  async function buscar() {
    if (!documento.trim()) return;
    setCargando(true);
    setError(null);
    setBuscado(true);
    try {
      const { data } = await apiClient.get('/api/victimas/buscar/', {
        params: { tipo_doc: tipoDoc, documento: documento.trim() },
      });
      setResultados(data.results ?? []);
    } catch {
      setError('Error al consultar el RNI. Verifique la conexión.');
      setResultados([]);
    } finally {
      setCargando(false);
    }
  }

  return (
    <View style={styles.root}>
      <SegmentedButtons
        value={tipoDoc}
        onValueChange={setTipoDoc}
        buttons={[
          { value: 'CC', label: 'C.C.' },
          { value: 'TI', label: 'T.I.' },
          { value: 'RC', label: 'R.C.' },
          { value: 'CE', label: 'C.E.' },
        ]}
        style={styles.segmented}
      />

      <Searchbar
        placeholder="Número de documento"
        value={documento}
        onChangeText={setDocumento}
        onSubmitEditing={buscar}
        keyboardType="numeric"
        style={styles.buscador}
        loading={cargando}
      />

      {error && (
        <HelperText type="error" visible>
          {error}
        </HelperText>
      )}

      {cargando && <ActivityIndicator style={styles.spinner} />}

      {!cargando && buscado && resultados.length === 0 && !error && (
        <Text style={styles.sinResultados}>No se encontraron registros en el RNI.</Text>
      )}

      <FlatList
        data={resultados}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <Card style={styles.resultado}>
            <Card.Content>
              <Text variant="bodyMedium">Tipo doc: {item.tipo_documento}</Text>
              <Text variant="bodyMedium">Estado RUV: {item.estado_ruv}</Text>
              <Text variant="bodySmall" style={styles.subtexto}>
                Género: {item.genero} — Etnia: {item.pertenencia_etnica}
              </Text>
            </Card.Content>
          </Card>
        )}
        contentContainerStyle={styles.lista}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#F5F5F5', padding: 16 },
  segmented: { marginBottom: 12 },
  buscador: { marginBottom: 8, backgroundColor: '#FFFFFF' },
  spinner: { marginTop: 32 },
  sinResultados: { textAlign: 'center', color: '#757575', marginTop: 32 },
  lista: { paddingBottom: 32 },
  resultado: { marginBottom: 8, backgroundColor: '#FFFFFF' },
  subtexto: { color: '#757575', marginTop: 4 },
});
