// Pantalla de estado de sincronización — Sprint 9.
import { useEffect, useState, useCallback } from 'react';
import { View, ScrollView, StyleSheet, RefreshControl } from 'react-native';
import {
  Text, ActivityIndicator, Chip, Divider,
} from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { router } from 'expo-router';
import * as colaDao from '../../src/db/colaDao';
import type { ColaItem, EstadoCola } from '../../src/db/colaDao';
import { useSyncStore, getEstadoSync } from '../../src/stores/syncStore';
import { GovHeader } from '../../src/components/GovHeader';
import { GovButton } from '../../src/components/GovButton';
import { GOV, SPACING, RADIUS, SHADOW, FONT } from '../../src/theme/govTheme';

// ─── Colores de estado ────────────────────────────────────────────────────────

const ESTADO_ITEM: Record<EstadoCola, { color: string; bg: string; icono: string }> = {
  pendiente:  { color: GOV.naranja,  bg: GOV.naranjaTenue, icono: 'clock-outline' },
  enviando:   { color: GOV.azul,     bg: GOV.azulTenue,    icono: 'cloud-upload-outline' },
  enviado:    { color: GOV.verde,    bg: GOV.verdeTenue,   icono: 'check-circle-outline' },
  error:      { color: GOV.rojo,     bg: GOV.rojoTenue,    icono: 'alert-circle-outline' },
};

const TIPO_ETIQUETA: Record<string, string> = {
  CREAR_HOGAR:        'Crear hogar',
  CREAR_SESION:       'Crear sesión',
  RESPONDER_BULK:     'Respuestas',
  RESPONDER_PREGUNTA: 'Respuesta',
  FINALIZAR_SESION:   'Finalizar sesión',
};

const SYNC_GLOBAL: Record<string, { icono: string; color: string; texto: string }> = {
  sincronizando: { icono: 'cloud-sync',    color: GOV.azul,    texto: 'Sincronizando…' },
  pendientes:    { icono: 'cloud-upload',  color: GOV.naranja, texto: 'Hay elementos pendientes' },
  sin_conexion:  { icono: 'wifi-off',      color: '#616161',   texto: 'Sin conexión a internet' },
  error:         { icono: 'cloud-alert',   color: GOV.rojo,    texto: 'Hay errores que requieren atención' },
  sincronizado:  { icono: 'cloud-check',   color: GOV.verde,   texto: 'Todo sincronizado' },
};

// ─── Fila de item ──────────────────────────────────────────────────────────────

function ItemRow({ item }: { item: ColaItem }) {
  const cfg = ESTADO_ITEM[item.estado] ?? ESTADO_ITEM.pendiente;
  const etiqueta = TIPO_ETIQUETA[item.tipo] ?? item.tipo;

  let payload: Record<string, unknown> = {};
  try { payload = JSON.parse(item.payload); } catch { /* ignore */ }

  const detalle = item.estado === 'error'
    ? item.ultimo_error
    : item.retry_after
      ? `Reintento: ${new Date(item.retry_after).toLocaleTimeString('es-CO')}`
      : null;

  return (
    <View style={styles.itemRow}>
      <View style={[styles.itemIconWrap, { backgroundColor: cfg.bg }]}>
        <MaterialCommunityIcons name={cfg.icono as any} size={18} color={cfg.color} />
      </View>
      <View style={styles.itemBody}>
        <View style={styles.itemTop}>
          <Text style={styles.itemTipo}>{etiqueta}</Text>
          <Chip
            compact
            style={{ backgroundColor: cfg.bg }}
            textStyle={{ color: cfg.color, fontSize: 10, fontWeight: '700' }}
          >
            {item.estado}
          </Chip>
        </View>
        {payload.sesion_id ? (
          <Text style={styles.itemMeta}>
            Sesión: {String(payload.sesion_id).slice(0, 8)}…
          </Text>
        ) : null}
        {payload.respuestas && Array.isArray(payload.respuestas) ? (
          <Text style={styles.itemMeta}>
            {(payload.respuestas as unknown[]).length} respuesta(s)
          </Text>
        ) : null}
        {item.intentos > 0 && (
          <Text style={styles.itemMeta}>
            Intentos: {item.intentos}
          </Text>
        )}
        {detalle ? (
          <Text style={[styles.itemMeta, item.estado === 'error' && { color: GOV.rojo }]} numberOfLines={2}>
            {detalle}
          </Text>
        ) : null}
      </View>
    </View>
  );
}

// ─── Pantalla ──────────────────────────────────────────────────────────────────

export default function SyncStatusScreen() {
  const syncStore = useSyncStore();
  const {
    triggerSync, reintentarErrores, refrescarContadores,
    sincronizando, pendientesCola, erroresCola,
  } = syncStore;
  const estado = getEstadoSync(syncStore);
  const globalCfg = SYNC_GLOBAL[estado] ?? SYNC_GLOBAL.sincronizado;

  const [items, setItems] = useState<ColaItem[]>([]);
  const [cargando, setCargando] = useState(true);
  const [refrescando, setRefrescando] = useState(false);

  const cargar = useCallback(async () => {
    const todos = await colaDao.obtenerTodos();
    setItems(todos);
    await refrescarContadores();
    setCargando(false);
    setRefrescando(false);
  }, []);

  useEffect(() => { cargar(); }, []);

  async function onSincronizar() {
    await triggerSync();
    await cargar();
  }

  async function onReintentar() {
    await reintentarErrores();
    await cargar();
  }

  async function onLimpiar() {
    await colaDao.limpiarEnviados();
    await cargar();
  }

  if (cargando) {
    return (
      <View style={styles.root}>
        <GovHeader title="Sincronización" onBack={() => router.back()} />
        <View style={styles.centrado}>
          <ActivityIndicator size="large" color={GOV.azul} />
        </View>
      </View>
    );
  }

  return (
    <View style={styles.root}>
      <GovHeader title="Sincronización" onBack={() => router.back()} />

      <ScrollView
        contentContainerStyle={styles.content}
        refreshControl={
          <RefreshControl
            refreshing={refrescando}
            onRefresh={() => { setRefrescando(true); cargar(); }}
            colors={[GOV.azul]}
          />
        }
      >
        {/* Estado global */}
        <View style={[styles.globalCard, { borderLeftColor: globalCfg.color }]}>
          <View style={styles.globalRow}>
            {sincronizando
              ? <ActivityIndicator size={28} color={globalCfg.color} />
              : <MaterialCommunityIcons name={globalCfg.icono as any} size={28} color={globalCfg.color} />
            }
            <View style={styles.globalTextos}>
              <Text style={[styles.globalEstado, { color: globalCfg.color }]}>
                {globalCfg.texto}
              </Text>
              <Text style={styles.globalMeta}>
                {pendientesCola} pendiente(s) · {erroresCola} error(es)
              </Text>
            </View>
          </View>
        </View>

        {/* Botones de acción */}
        <View style={styles.botonesRow}>
          <View style={styles.btnWrap}>
            <GovButton
              label="Sincronizar"
              icon="cloud-sync"
              loading={sincronizando}
              disabled={sincronizando || estado === 'sin_conexion'}
              onPress={onSincronizar}
            />
          </View>
          {erroresCola > 0 && (
            <View style={styles.btnWrap}>
              <GovButton
                label="Reintentar errores"
                icon="refresh"
                variant="secondary"
                onPress={onReintentar}
              />
            </View>
          )}
        </View>

        {/* Lista de items en cola */}
        {items.length === 0 ? (
          <View style={styles.vacio}>
            <MaterialCommunityIcons name="check-all" size={48} color={GOV.verde} />
            <Text style={styles.vacioTxt}>Cola vacía — todo al día</Text>
          </View>
        ) : (
          <View style={styles.listaCard}>
            <Text style={styles.listaTitulo}>
              En cola ({items.length})
            </Text>
            {items.map((item, i) => (
              <View key={item.id}>
                {i > 0 && <Divider style={styles.divider} />}
                <ItemRow item={item} />
              </View>
            ))}
          </View>
        )}

        {/* Limpiar enviados */}
        {items.some(i => i.estado === 'enviado') && (
          <View style={styles.limpiarWrap}>
            <GovButton
              label="Limpiar enviados"
              icon="delete-sweep"
              variant="secondary"
              onPress={onLimpiar}
            />
          </View>
        )}

      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: GOV.fondoApp,
  },
  centrado: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  content: {
    padding: SPACING.md,
    paddingBottom: SPACING.xxl,
    gap: SPACING.md,
  },
  globalCard: {
    backgroundColor: GOV.superficie,
    borderRadius: RADIUS.md,
    borderLeftWidth: 4,
    padding: SPACING.md,
    ...SHADOW.card,
  },
  globalRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.md,
  },
  globalTextos: {
    flex: 1,
  },
  globalEstado: {
    ...FONT.h3,
    fontWeight: '700',
  },
  globalMeta: {
    ...FONT.caption,
    color: GOV.textoT,
    marginTop: 2,
  },
  botonesRow: {
    flexDirection: 'row',
    gap: SPACING.sm,
  },
  btnWrap: {
    flex: 1,
  },
  listaCard: {
    backgroundColor: GOV.superficie,
    borderRadius: RADIUS.md,
    ...SHADOW.card,
    overflow: 'hidden',
    paddingHorizontal: SPACING.md,
    paddingTop: SPACING.md,
    paddingBottom: SPACING.sm,
  },
  listaTitulo: {
    ...FONT.label,
    color: GOV.textoS,
    textTransform: 'uppercase',
    letterSpacing: 0.8,
    marginBottom: SPACING.sm,
  },
  divider: {
    marginVertical: 4,
  },
  itemRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: SPACING.sm,
    paddingVertical: SPACING.sm,
  },
  itemIconWrap: {
    width: 34,
    height: 34,
    borderRadius: RADIUS.sm,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 2,
  },
  itemBody: {
    flex: 1,
    gap: 2,
  },
  itemTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  itemTipo: {
    ...FONT.body,
    fontWeight: '600',
    color: GOV.textoP,
    flex: 1,
  },
  itemMeta: {
    ...FONT.caption,
    color: GOV.textoT,
  },
  vacio: {
    alignItems: 'center',
    paddingVertical: SPACING.xl,
    gap: SPACING.sm,
  },
  vacioTxt: {
    ...FONT.body,
    color: GOV.textoT,
  },
  limpiarWrap: {
    marginTop: SPACING.xs,
  },
});
