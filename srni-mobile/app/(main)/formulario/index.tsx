/**
 * Lista de temas del formulario de caracterización PAARI.
 * Los temas se cargan desde la BD local SQLite (sincronizada con el servidor).
 */
import { useEffect, useState } from 'react';
import { View, FlatList, StyleSheet } from 'react-native';
import { Card, Text, ProgressBar, Button, ActivityIndicator } from 'react-native-paper';
import { router } from 'expo-router';
import * as SQLite from 'expo-sqlite';
import { DB_NAME } from '../../../src/db/schema';

interface Tema {
  id: number;
  codigo: string;
  nombre: string;
  orden: number;
}

export default function FormularioIndexScreen() {
  const [temas, setTemas] = useState<Tema[]>([]);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    SQLite.openDatabaseAsync(DB_NAME)
      .then(async (db) => {
        const rows = await db.getAllAsync<Tema>(
          'SELECT id, codigo, nombre, orden FROM temas WHERE activo = 1 ORDER BY orden',
        );
        setTemas(rows);
      })
      .catch(console.error)
      .finally(() => setCargando(false));
  }, []);

  if (cargando) {
    return (
      <View style={styles.centrado}>
        <ActivityIndicator size="large" />
        <Text style={styles.cargandoTexto}>Cargando instrumento…</Text>
      </View>
    );
  }

  if (temas.length === 0) {
    return (
      <View style={styles.centrado}>
        <Text variant="bodyLarge">No hay instrumento cargado.</Text>
        <Text variant="bodyMedium" style={styles.hint}>
          Sincronice con el servidor para descargar el formulario.
        </Text>
      </View>
    );
  }

  return (
    <View style={styles.root}>
      <Text variant="titleMedium" style={styles.cabecera}>
        {temas.length} módulos — PAARI v1.0
      </Text>
      <ProgressBar progress={0} style={styles.progreso} />

      <FlatList
        data={temas}
        keyExtractor={(item) => String(item.id)}
        renderItem={({ item, index }) => (
          <Card
            style={styles.card}
            onPress={() =>
              router.push({
                pathname: '/(main)/formulario/[temaId]',
                params: { temaId: item.id },
              })
            }
          >
            <Card.Content style={styles.cardContent}>
              <View style={styles.numeroBadge}>
                <Text variant="labelLarge" style={styles.numero}>
                  {String(index + 1).padStart(2, '0')}
                </Text>
              </View>
              <View style={styles.cardTexto}>
                <Text variant="bodyLarge" numberOfLines={2}>
                  {item.nombre}
                </Text>
                <Text variant="bodySmall" style={styles.codigo}>
                  {item.codigo}
                </Text>
              </View>
            </Card.Content>
          </Card>
        )}
        contentContainerStyle={styles.lista}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#F5F5F5' },
  centrado: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 32 },
  cargandoTexto: { marginTop: 12, color: '#757575' },
  hint: { textAlign: 'center', color: '#9E9E9E', marginTop: 8 },
  cabecera: { margin: 16, fontWeight: '600', color: '#1565C0' },
  progreso: { marginHorizontal: 16, marginBottom: 8, height: 6, borderRadius: 3 },
  lista: { padding: 12, paddingBottom: 32 },
  card: { marginBottom: 8, backgroundColor: '#FFFFFF' },
  cardContent: { flexDirection: 'row', alignItems: 'center' },
  numeroBadge: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: '#E3F2FD',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  numero: { color: '#1565C0', fontWeight: '700' },
  cardTexto: { flex: 1 },
  codigo: { color: '#9E9E9E', marginTop: 2 },
});
