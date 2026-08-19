/**
 * Lista de sesiones de encuesta del encuestador.
 * Muestra el progreso de cada sesión y permite continuar o ver detalles.
 *
 * APK-003: la lista une DOS fuentes, siempre las dos —
 *   · las sesiones del servidor, cuando responde;
 *   · los borradores locales de SQLite, haya red o no.
 * Un borrador que todavía no subió no existe en el servidor, así que si solo se
 * leyera de allá la encuestadora no vería su propio trabajo del día. El chip de
 * cada tarjeta dice cuál es cuál, y sale del dato (`sesion_id`), nunca escrito
 * fijo.
 */
import { useState, useCallback } from 'react';
import { View, FlatList, StyleSheet, RefreshControl, Pressable } from 'react-native';
import {
  Text, Chip,
  ActivityIndicator, SegmentedButtons,
} from 'react-native-paper';
import { AnimatedProgressBar } from '../../../src/components/AnimatedProgressBar';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { router, useFocusEffect } from 'expo-router';
import { encuestasApi } from '../../../src/api/encuestas';
import * as borradoresDao from '../../../src/db/borradoresDao';
import {
  activarPerfil, codigoPorInstrumentoId, listaInstrumentosBundle,
} from '../../../src/services/instrumentos';
import { useSyncStore } from '../../../src/stores/syncStore';
import { GovHeader } from '../../../src/components/GovHeader';
import { EmptyState } from '../../../src/components/EmptyState';
import { GOV, SPACING, RADIUS, SHADOW, FONT } from '../../../src/theme/govTheme';
import type { SesionResumen } from '../../../src/types';
import type { BorradorRow } from '../../../src/db/borradoresDao';

const ESTADOS = [
  { value: '', label: 'Todas' },
  { value: 'INICIADA', label: 'Iniciadas' },
  { value: 'EN_PROGRESO', label: 'En curso' },
  { value: 'COMPLETADA', label: 'Completadas' },
];

const ESTADO_COLOR: Record<string, string> = {
  INICIADA: '#1565C0',
  EN_PROGRESO: '#E65100',
  COMPLETADA: '#2E7D32',
  SUSPENDIDA: '#616161',
};

type ItemLista =
  | { tipo: 'servidor'; data: SesionResumen }
  | { tipo: 'borrador'; data: BorradorRow; instrumentoNombre: string };

// ─── Tarjeta de borrador offline ──────────────────────────────────────────────

function BorradorCard({ data, instrumentoNombre }: { data: BorradorRow; instrumentoNombre: string }) {
  /**
   * Tocar un borrador tiene que CONTINUARLO. Antes iba a `/caracterizar`, que es
   * el selector de instrumento: la encuestadora tocaba su trabajo a medias y la
   * app le pedía volver a elegir instrumento y hogar desde cero, sin señal de
   * que el borrador seguía ahí.
   *
   * Se va derecho al formulario con `borradorId`, que es el hilo del flujo
   * offline — el mismo camino que ya usa la pantalla de detalle de sesión.
   * `instrumentoId` va también porque sin red es lo único que le permite a
   * `formulario/index` resolver el perfil (`codigoPorInstrumentoId`).
   */
  function continuar() {
    if (data.instrumento_id) {
      const codigo = codigoPorInstrumentoId(data.instrumento_id);
      // Si el perfil no está en el bundle, el formulario lo dice con su propio
      // mensaje; acá no se bloquea la navegación.
      if (codigo) try { activarPerfil(codigo); } catch { /* no-op */ }
    }
    router.push({
      pathname: '/(main)/formulario',
      params: {
        borradorId: data.id,
        instrumentoId: data.instrumento_id ?? '',
        hogarId: data.hogar_id ?? '',
        ...(data.sesion_id ? { sesionServerId: data.sesion_id } : {}),
      },
    });
  }

  /**
   * Lo que dice el chip tiene que salir del dato. Escrito fijo, «Pendiente
   * sync» le decía a la encuestadora que su trabajo no había subido incluso
   * cuando sí: `sesion_id` presente significa que la sesión ya existe en el
   * servidor. Es el mismo defecto que se corrigió en la tarjeta de hogares.
   */
  const guardado = !!data.sesion_id;
  const etiqueta = guardado ? 'Guardado' : 'Pendiente sync';
  const color    = guardado ? GOV.verde : GOV.naranja;
  const colorBg  = guardado ? GOV.verdeTenue : GOV.naranjaTenue;

  return (
    <Pressable
      style={({ pressed }) => [styles.card, pressed && styles.cardPressed]}
      onPress={continuar}
      accessibilityRole="button"
      accessibilityLabel={`${instrumentoNombre} — ${etiqueta}, tocar para continuar`}
    >
      <View style={[styles.cardAccent, { backgroundColor: color }]} />
      <View style={styles.cardBody}>
        <View style={styles.cardHeader}>
          <Text style={styles.instrumento} numberOfLines={1}>{instrumentoNombre}</Text>
          <View style={[styles.estadoChip, { backgroundColor: colorBg }]}>
            <Text style={[styles.estadoTxt, { color }]}>{etiqueta}</Text>
          </View>
        </View>
        {data.hogar_id ? (
          <Text style={styles.hogarId}>Hogar: {data.hogar_id.slice(0, 8)}…</Text>
        ) : null}
        <Text style={styles.fecha}>
          {new Date(data.updated_at).toLocaleDateString('es-CO')}
        </Text>
      </View>
      <MaterialCommunityIcons name="chevron-right" size={20} color={GOV.borde} style={styles.chevron} />
    </Pressable>
  );
}

// ─── Pantalla ─────────────────────────────────────────────────────────────────

export default function EncuestasIndexScreen() {
  const { estaOnline } = useSyncStore();
  const [items, setItems] = useState<ItemLista[]>([]);
  const [cargando, setCargando] = useState(true);
  const [refrescando, setRefrescando] = useState(false);
  const [filtroEstado, setFiltroEstado] = useState('');
  const [error, setError] = useState('');

  const cargar = useCallback(async (esRefresh = false) => {
    if (esRefresh) setRefrescando(true);
    else setCargando(true);
    setError('');

    const servidorItems: ItemLista[] = [];
    const borradorItems: ItemLista[] = [];

    // Intentar cargar del servidor
    const sesionesServidor = new Set<string>();
    let servidorOk = false;
    try {
      const res = await encuestasApi.listar(
        filtroEstado ? { estado: filtroEstado } : undefined
      );
      servidorOk = true;
      for (const s of res.data.results) {
        sesionesServidor.add(s.id);
        servidorItems.push({ tipo: 'servidor', data: s });
      }
    } catch {
      if (estaOnline) setError('No se pudo cargar las sesiones.');
    }

    // Los borradores locales se leen SIEMPRE, haya red o no.
    //
    // Antes esto estaba dentro de `if (!servidorOk)`, y así solo se veían
    // cuando el servidor fallaba — justo al revés de lo que hace falta. Un
    // borrador que todavía no subió no está, por definición, en la respuesta
    // del servidor: su sesión aún no existe allá. Con señal, la encuestadora
    // que acababa de capturar una entrevista sin red entraba a Encuestas y no
    // la veía por ningún lado, sin mensaje. Y si el ítem de cola había quedado
    // en 'error', era invisible de forma permanente mientras hubiera señal. Lo
    // que sigue después de creer que se perdió es volver a capturarla con la
    // víctima enfrente.
    //
    // Con la lectura siempre activa, el `continue` de abajo pasa a ser el
    // dedupe de verdad: antes era código muerto, porque solo corría cuando
    // `sesionesServidor` estaba vacío.
    try {
      const borradores = await borradoresDao.listarBorradores();
      const instrumentos = listaInstrumentosBundle();
      const nombresMap = new Map(instrumentos.map((i) => [i.id, i.nombre]));

      for (const b of borradores) {
        // Ya vinculado a una sesión que el servidor devolvió → esa tarjeta manda.
        if (b.sesion_id && sesionesServidor.has(b.sesion_id)) continue;
        const nombre = (b.instrumento_id ? nombresMap.get(b.instrumento_id) : null) ?? 'Instrumento';
        borradorItems.push({ tipo: 'borrador', data: b, instrumentoNombre: nombre });
      }
    } catch {
      // SQLite no disponible — se queda vacío
    }

    setItems([...borradorItems, ...servidorItems]);
    setCargando(false);
    setRefrescando(false);
  }, [estaOnline, filtroEstado]);

  // useFocusEffect y no useEffect: los tabs conservan la instancia montada, así
  // que con useEffect un borrador recién capturado no aparecía al volver a esta
  // pestaña, y al terminar una sincronización nada volvía a disparar la carga.
  useFocusEffect(
    useCallback(() => {
      cargar();
    }, [cargar]),
  );

  if (cargando) {
    return (
      <View style={styles.root}>
        <GovHeader title="Encuestas" subtitle="Sesiones de caracterización" />
        <View style={styles.centrado}>
          <ActivityIndicator size="large" color={GOV.azul} />
          <Text style={styles.hint}>Cargando encuestas…</Text>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.root}>
      <GovHeader title="Encuestas" subtitle="Sesiones de caracterización" />

      <SegmentedButtons
        value={filtroEstado}
        onValueChange={setFiltroEstado}
        buttons={ESTADOS}
        style={styles.filtro}
        theme={{ colors: { secondaryContainer: GOV.azulTenue, onSecondaryContainer: GOV.azul } }}
      />

      {/* Banner offline */}
      {!estaOnline && (
        <View style={styles.offlineBanner}>
          <MaterialCommunityIcons name="wifi-off" size={14} color={GOV.naranja} />
          <Text style={styles.offlineTxt}>Sin conexión — mostrando borradores locales</Text>
        </View>
      )}

      {error ? <Text style={styles.error}>{error}</Text> : null}

      <FlatList
        data={items}
        keyExtractor={(item) =>
          item.tipo === 'borrador' ? `borrador-${item.data.id}` : item.data.id
        }
        refreshControl={
          <RefreshControl
            refreshing={refrescando}
            onRefresh={() => cargar(true)}
            colors={[GOV.azul]}
            tintColor={GOV.azul}
          />
        }
        ListEmptyComponent={
          error
            ? null  /* APK-003: no mostrar "Sin sesiones" si el servidor falló */
            : <EmptyState
                icon="clipboard-text-outline"
                title="Sin sesiones"
                message="No hay sesiones registradas para los filtros seleccionados."
              />
        }
        renderItem={({ item }) => {
          if (item.tipo === 'borrador') {
            return <BorradorCard data={item.data} instrumentoNombre={item.instrumentoNombre} />;
          }
          const estadoColor = ESTADO_COLOR[item.data.estado] ?? '#616161';
          return (
            <Pressable
              style={({ pressed }) => [styles.card, pressed && styles.cardPressed]}
              onPress={() => router.push({ pathname: '/(main)/encuestas/[sesionId]', params: { sesionId: item.data.id } })}
              accessibilityRole="button"
            >
              <View style={[styles.cardAccent, { backgroundColor: estadoColor }]} />
              <View style={styles.cardBody}>
                <View style={styles.cardHeader}>
                  <Text style={styles.instrumento} numberOfLines={1}>{item.data.instrumento_nombre}</Text>
                  <View style={[styles.estadoChip, { backgroundColor: estadoColor + '22' }]}>
                    <Text style={[styles.estadoTxt, { color: estadoColor }]}>{item.data.estado_display}</Text>
                  </View>
                </View>

                <Text style={styles.hogarId}>Hogar: {item.data.hogar.slice(0, 8)}…</Text>

                {/* El porcentaje se muestra como viene, solo acotado a 0–100.
                    Estuvo un tiempo forzado a 100 cuando el estado era
                    COMPLETADA: eso tapaba el síntoma y de paso mentía, porque
                    el backend NO exige completitud para cerrar una sesión
                    (`finalizar` guarda el porcentaje real junto a COMPLETADA) y
                    una entrevista interrumpida a mitad se cerraba mostrando
                    100 %. El panel web nunca aplicó ese override, así que la
                    misma sesión se veía distinta según quién la mirara.
                    El número igual queda BAJO hasta que se arregle el backend:
                    `recalcular_porcentaje` divide por TODAS las obligatorias
                    del instrumento sin evaluar skip-logic, así que cuenta como
                    faltantes preguntas que la regla ocultó. Esa es la causa de
                    fondo del APK-005 y se arregla allá, no acá. */}
                <View style={styles.progresoRow}>
                  <View style={styles.barraWrap}>
                    <AnimatedProgressBar
                      progress={Math.max(0, Math.min(1, (item.data.porcentaje_completado ?? 0) / 100))}
                      color={estadoColor}
                    />
                  </View>
                  <Text style={styles.pct}>
                    {Math.max(0, Math.min(100, Math.round(item.data.porcentaje_completado ?? 0)))}%
                  </Text>
                </View>

                <Text style={styles.fecha}>
                  {new Date(item.data.fecha_inicio).toLocaleDateString('es-CO')}
                  {item.data.fecha_fin ? ` — ${new Date(item.data.fecha_fin).toLocaleDateString('es-CO')}` : ''}
                </Text>
              </View>
              <MaterialCommunityIcons name="chevron-right" size={20} color={GOV.borde} style={styles.chevron} />
            </Pressable>
          );
        }}
        contentContainerStyle={[styles.lista, items.length === 0 && styles.listaVacia]}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: GOV.fondoApp },
  centrado: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: SPACING.xl },
  filtro: { marginHorizontal: SPACING.md, marginVertical: SPACING.sm },
  lista: { padding: SPACING.md, paddingBottom: SPACING.xl },
  listaVacia: { flexGrow: 1 },
  // Tarjeta
  card: {
    flexDirection: 'row',
    backgroundColor: GOV.superficie,
    borderRadius: RADIUS.md,
    marginBottom: SPACING.sm,
    overflow: 'hidden',
    ...SHADOW.card,
  },
  cardPressed: { opacity: 0.92, transform: [{ scale: 0.99 }] },
  cardAccent: { width: 4 },
  cardBody: { flex: 1, padding: SPACING.md },
  chevron: { alignSelf: 'center', marginRight: SPACING.xs },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 },
  instrumento: { ...FONT.body, fontWeight: '600', color: GOV.textoP, flex: 1 },
  estadoChip: { borderRadius: RADIUS.pill, paddingHorizontal: 8, paddingVertical: 2 },
  estadoTxt: { fontSize: 10, fontWeight: '600' },
  hogarId: { fontFamily: 'monospace', ...FONT.caption, color: GOV.textoT, marginBottom: SPACING.sm },
  progresoRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 4 },
  barraWrap: { flex: 1, marginRight: SPACING.sm },
  pct: { ...FONT.caption, color: GOV.textoS, minWidth: 32, textAlign: 'right' },
  fecha: { ...FONT.caption, color: GOV.textoT },
  offlineBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.xs,
    backgroundColor: GOV.naranjaTenue,
    marginHorizontal: SPACING.md,
    marginBottom: SPACING.sm,
    paddingHorizontal: SPACING.sm,
    paddingVertical: 6,
    borderRadius: RADIUS.sm,
  },
  offlineTxt: { ...FONT.caption, color: GOV.naranja, fontWeight: '600' },
  hint: { marginTop: SPACING.sm, ...FONT.small, color: GOV.textoS },
  error: { ...FONT.small, color: GOV.rojo, textAlign: 'center', margin: SPACING.md },
});
