/**
 * Motor de renderizado de preguntas de un tema.
 * Implementa la misma lógica del APK original:
 *   - PREDEPENDE / RESHABILITA / RESFINALIZA → aquí como PreguntaDerivada
 *   - Las preguntas ocultas no se muestran hasta que la condición se cumple
 */
import { useEffect, useState, useMemo } from 'react';
import { View, FlatList, StyleSheet } from 'react-native';
import { Text, TextInput, RadioButton, Checkbox, Button, ActivityIndicator } from 'react-native-paper';
import { useLocalSearchParams, router } from 'expo-router';
import * as SQLite from 'expo-sqlite';
import { DB_NAME } from '../../../src/db/schema';

interface Pregunta {
  id: number;
  codigo: string;
  texto: string;
  texto_ayuda: string;
  tipo_respuesta: string;
  orden: number;
  requerida: number;
}

interface Opcion {
  id: number;
  pregunta_id: number;
  codigo: string;
  texto: string;
  orden: number;
}

interface Derivada {
  pregunta_padre_id: number;
  pregunta_hija_id: number;
  operador: string;
  valor_condicion: string;
}

type Respuestas = Record<number, string>;

function evaluarCondicion(
  operador: string,
  valorRespuesta: string,
  valorCondicion: string,
): boolean {
  switch (operador) {
    case 'EQ':
      return valorRespuesta === valorCondicion;
    case 'NEQ':
      return valorRespuesta !== valorCondicion;
    case 'NOTNULL':
      return valorRespuesta.trim() !== '';
    case 'GT':
      return Number(valorRespuesta) > Number(valorCondicion);
    case 'GTE':
      return Number(valorRespuesta) >= Number(valorCondicion);
    case 'LT':
      return Number(valorRespuesta) < Number(valorCondicion);
    case 'LTE':
      return Number(valorRespuesta) <= Number(valorCondicion);
    case 'IN':
      return valorCondicion.split(',').includes(valorRespuesta);
    default:
      return false;
  }
}

export default function TemaScreen() {
  const { temaId } = useLocalSearchParams<{ temaId: string }>();
  const [preguntas, setPreguntas] = useState<Pregunta[]>([]);
  const [opciones, setOpciones] = useState<Record<number, Opcion[]>>({});
  const [derivadas, setDerivadas] = useState<Derivada[]>([]);
  const [respuestas, setRespuestas] = useState<Respuestas>({});
  const [cargando, setCargando] = useState(true);
  const [temaNombre, setTemaNombre] = useState('');

  useEffect(() => {
    if (!temaId) return;
    SQLite.openDatabaseAsync(DB_NAME)
      .then(async (db) => {
        const tema = await db.getFirstAsync<{ nombre: string }>(
          'SELECT nombre FROM temas WHERE id = ?',
          [Number(temaId)],
        );
        setTemaNombre(tema?.nombre ?? '');

        const pgs = await db.getAllAsync<Pregunta>(
          'SELECT * FROM preguntas WHERE tema_id = ? AND activa = 1 ORDER BY orden',
          [Number(temaId)],
        );
        setPreguntas(pgs);

        if (pgs.length > 0) {
          const ids = pgs.map((p) => p.id);
          const placeholders = ids.map(() => '?').join(',');
          const opts = await db.getAllAsync<Opcion>(
            `SELECT * FROM opciones_respuesta WHERE pregunta_id IN (${placeholders}) ORDER BY orden`,
            ids,
          );
          const grouped: Record<number, Opcion[]> = {};
          opts.forEach((o) => {
            if (!grouped[o.pregunta_id]) grouped[o.pregunta_id] = [];
            grouped[o.pregunta_id].push(o);
          });
          setOpciones(grouped);

          const derivs = await db.getAllAsync<Derivada>(
            `SELECT * FROM preguntas_derivadas WHERE pregunta_padre_id IN (${placeholders})`,
            ids,
          );
          setDerivadas(derivs);
        }
      })
      .catch(console.error)
      .finally(() => setCargando(false));
  }, [temaId]);

  // Calcular qué preguntas son visibles según skip logic
  const preguntasVisibles = useMemo(() => {
    const hijasCondicionales = new Set(derivadas.map((d) => d.pregunta_hija_id));

    return preguntas.filter((p) => {
      if (!hijasCondicionales.has(p.id)) return true;
      // Mostrar solo si ALGUNA condición padre se cumple
      return derivadas.some(
        (d) =>
          d.pregunta_hija_id === p.id &&
          evaluarCondicion(d.operador, respuestas[d.pregunta_padre_id] ?? '', d.valor_condicion),
      );
    });
  }, [preguntas, derivadas, respuestas]);

  function setRespuesta(preguntaId: number, valor: string) {
    setRespuestas((prev) => ({ ...prev, [preguntaId]: valor }));
  }

  if (cargando) {
    return (
      <View style={styles.centrado}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  return (
    <View style={styles.root}>
      <Text variant="titleMedium" style={styles.cabecera}>
        {temaNombre}
      </Text>
      <FlatList
        data={preguntasVisibles}
        keyExtractor={(item) => String(item.id)}
        renderItem={({ item }) => (
          <PreguntaItem
            pregunta={item}
            opciones={opciones[item.id] ?? []}
            valor={respuestas[item.id] ?? ''}
            onChange={(v) => setRespuesta(item.id, v)}
          />
        )}
        contentContainerStyle={styles.lista}
      />
      <Button mode="contained" style={styles.siguiente} onPress={() => router.back()}>
        Guardar y volver
      </Button>
    </View>
  );
}

function PreguntaItem({
  pregunta,
  opciones,
  valor,
  onChange,
}: {
  pregunta: Pregunta;
  opciones: Opcion[];
  valor: string;
  onChange: (v: string) => void;
}) {
  return (
    <View style={styles.preguntaCard}>
      <Text variant="bodyMedium" style={styles.textoPregunta}>
        {pregunta.requerida ? '* ' : ''}{pregunta.texto}
      </Text>
      {pregunta.texto_ayuda ? (
        <Text variant="bodySmall" style={styles.ayuda}>
          {pregunta.texto_ayuda}
        </Text>
      ) : null}

      {pregunta.tipo_respuesta === 'TEXTO' || pregunta.tipo_respuesta === 'NUMERICO' ? (
        <TextInput
          value={valor}
          onChangeText={onChange}
          keyboardType={pregunta.tipo_respuesta === 'NUMERICO' ? 'numeric' : 'default'}
          style={styles.inputTexto}
          dense
        />
      ) : pregunta.tipo_respuesta === 'OPCION_UNICA' || pregunta.tipo_respuesta === 'SINO' ? (
        <RadioButton.Group value={valor} onValueChange={onChange}>
          {opciones.map((o) => (
            <RadioButton.Item key={o.id} label={o.texto} value={o.codigo} />
          ))}
        </RadioButton.Group>
      ) : pregunta.tipo_respuesta === 'OPCION_MULTIPLE' ? (
        <View>
          {opciones.map((o) => (
            <Checkbox.Item
              key={o.id}
              label={o.texto}
              status={valor.split(',').includes(o.codigo) ? 'checked' : 'unchecked'}
              onPress={() => {
                const sel = valor ? valor.split(',') : [];
                const idx = sel.indexOf(o.codigo);
                if (idx >= 0) sel.splice(idx, 1);
                else sel.push(o.codigo);
                onChange(sel.filter(Boolean).join(','));
              }}
            />
          ))}
        </View>
      ) : (
        <TextInput value={valor} onChangeText={onChange} style={styles.inputTexto} dense />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#F5F5F5' },
  centrado: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  cabecera: { margin: 16, fontWeight: '600', color: '#1565C0' },
  lista: { padding: 12, paddingBottom: 80 },
  preguntaCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 8,
    padding: 16,
    marginBottom: 8,
    borderLeftWidth: 3,
    borderLeftColor: '#1565C0',
  },
  textoPregunta: { fontWeight: '600', marginBottom: 8 },
  ayuda: { color: '#757575', marginBottom: 8 },
  inputTexto: { backgroundColor: '#FAFAFA' },
  siguiente: { margin: 16, borderRadius: 8 },
});
