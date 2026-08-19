// Detalle de una sesión de encuesta — GOV.CO design system.
// APK-003: fallback offline — si el API falla, muestra el borrador local.
import { useCallback, useState } from 'react';
import { View, ScrollView, StyleSheet, Alert } from 'react-native';
import {
  Text, Chip, ActivityIndicator, Divider,
} from 'react-native-paper';
import { AnimatedProgressBar } from '../../../src/components/AnimatedProgressBar';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { router, useLocalSearchParams, useFocusEffect } from 'expo-router';
import { encuestasApi } from '../../../src/api/encuestas';
import * as borradoresDao from '../../../src/db/borradoresDao';
import { activarPerfil, codigoPorInstrumentoId, listaInstrumentosBundle } from '../../../src/services/instrumentos';
import { GovHeader } from '../../../src/components/GovHeader';
import { GovButton } from '../../../src/components/GovButton';
import { GOV, SPACING, RADIUS, SHADOW, FONT } from '../../../src/theme/govTheme';
import type { SesionDetalle } from '../../../src/types';
import type { BorradorRow, RespuestaRow } from '../../../src/db/borradoresDao';

const ESTADO_COLOR: Record<string, string> = {
  INICIADA:    GOV.azul,
  EN_PROGRESO: GOV.naranja,
  COMPLETADA:  GOV.verde,
  SUSPENDIDA:  '#616161',
};

// ─── Fila de info ─────────────────────────────────────────────────────────────

function InfoFila({ label, valor }: { label: string; valor: string }) {
  return (
    <View style={styles.infoFila}>
      <Text style={styles.infoLabel}>{label}</Text>
      <Text style={styles.infoValor}>{valor || '—'}</Text>
    </View>
  );
}

// ─── Pantalla ─────────────────────────────────────────────────────────────────

/** Datos mínimos del borrador para mostrar offline. */
interface BorradorOffline {
  borrador: BorradorRow;
  respuestas: RespuestaRow[];
  instrumentoNombre: string;
}

export default function SesionDetalleScreen() {
  const { sesionId } = useLocalSearchParams<{ sesionId: string }>();
  const [sesion, setSesion] = useState<SesionDetalle | null>(null);
  const [borradorOffline, setBorradorOffline] = useState<BorradorOffline | null>(null);
  const [cargando, setCargando] = useState(true);
  const [finalizando, setFinalizando] = useState(false);
  const [error, setError] = useState('');

  async function cargar() {
    if (!sesionId) return;
    setCargando(true);
    setError('');
    setBorradorOffline(null);

    try {
      const res = await encuestasApi.detalle(sesionId);
      setSesion(res.data);
    } catch {
      // APK-003: fallback a borrador local
      try {
        const borrador = await borradoresDao.findBySesionId(sesionId);
        if (borrador) {
          const respuestas = await borradoresDao.getRespuestas(borrador.id);
          const instrumentos = listaInstrumentosBundle();
          const nombre = instrumentos.find((i) => i.id === borrador.instrumento_id)?.nombre ?? 'Instrumento';
          setBorradorOffline({ borrador, respuestas, instrumentoNombre: nombre });
        } else {
          setError('No se pudo cargar la sesión y no hay borrador local.');
        }
      } catch {
        setError('No se pudo cargar la sesión.');
      }
    } finally {
      setCargando(false);
    }
  }

  // Se recarga cada vez que la pantalla recupera el foco (p.ej. al volver del formulario).
  useFocusEffect(useCallback(() => { cargar(); }, [sesionId]));

  function confirmarFinalizar() {
    Alert.alert(
      'Finalizar sesión',
      `¿Confirma que desea cerrar esta sesión? Progreso: ${sesion?.porcentaje_completado ?? 0}%.`,
      [
        { text: 'Cancelar', style: 'cancel' },
        { text: 'Finalizar', style: 'destructive', onPress: finalizar },
      ],
    );
  }

  async function finalizar() {
    if (!sesion) return;
    setFinalizando(true);
    try {
      const res = await encuestasApi.finalizar(sesion.id);
      setSesion(res.data);
    } catch (err: any) {
      Alert.alert('Error', err?.response?.data?.detail ?? 'No se pudo finalizar la sesión.');
    } finally {
      setFinalizando(false);
    }
  }

  // ── Cargando ─────────────────────────────────────────────────────────────────

  if (cargando) {
    return (
      <View style={styles.root}>
        <GovHeader title="Sesión de encuesta" onBack={() => router.back()} />
        <View style={styles.centrado}>
          <ActivityIndicator size="large" color={GOV.azul} />
        </View>
      </View>
    );
  }

  // ── Error ─────────────────────────────────────────────────────────────────────

  if (error && !borradorOffline) {
    return (
      <View style={styles.root}>
        <GovHeader title="Sesión de encuesta" onBack={() => router.back()} />
        <View style={styles.centrado}>
          <MaterialCommunityIcons name="alert-circle-outline" size={48} color={GOV.rojo} />
          <Text style={styles.errorTxt}>{error || 'Sesión no encontrada.'}</Text>
          <GovButton label="Volver" variant="secondary" onPress={() => router.back()} />
        </View>
      </View>
    );
  }

  // ── Borrador offline (APK-003) ──────────────────────────────────────────────

  if (borradorOffline && !sesion) {
    const { borrador, respuestas, instrumentoNombre } = borradorOffline;
    return (
      <View style={styles.root}>
        <GovHeader
          title={`Borrador ${borrador.id.slice(0, 8)}…`}
          subtitle={instrumentoNombre}
          onBack={() => router.back()}
        />
        <View style={styles.offlineBanner}>
          <MaterialCommunityIcons name="wifi-off" size={14} color={GOV.naranja} />
          <Text style={styles.offlineTxt}>Sin conexión — datos del borrador local</Text>
        </View>
        <ScrollView contentContainerStyle={styles.content}>
          <View style={styles.card}>
            <View style={styles.estadoRow}>
              <View style={[styles.estadoChip, { backgroundColor: GOV.naranjaTenue }]}>
                <Text style={[styles.estadoTxt, { color: GOV.naranja }]}>Pendiente sync</Text>
              </View>
              <Text style={styles.fecha}>
                {new Date(borrador.updated_at).toLocaleDateString('es-CO')}
              </Text>
            </View>
            <InfoFila label="Instrumento" valor={instrumentoNombre} />
            {borrador.hogar_id && <InfoFila label="Hogar" valor={`${borrador.hogar_id.slice(0, 8)}…`} />}
            <Divider style={styles.divider} />
            <Text style={styles.respuestasMeta}>
              {respuestas.length} respuesta{respuestas.length !== 1 ? 's' : ''} guardada{respuestas.length !== 1 ? 's' : ''} localmente
            </Text>
          </View>

          {/* Continuar formulario offline */}
          <View style={styles.card}>
            <Text style={styles.seccionTitulo}>Continuar</Text>
            <GovButton
              label={`Continuar formulario — ${instrumentoNombre}`}
              icon="clipboard-text"
              onPress={() => {
                if (borrador.instrumento_id) {
                  const codigo = codigoPorInstrumentoId(borrador.instrumento_id);
                  if (codigo) try { activarPerfil(codigo); } catch {}
                }
                router.push({
                  pathname: '/(main)/formulario',
                  params: {
                    sesionServerId: sesionId,
                    instrumentoId: borrador.instrumento_id ?? '',
                    hogarId: borrador.hogar_id ?? '',
                  },
                });
              }}
            />
          </View>

          {/* Respuestas locales */}
          {respuestas.length > 0 && (
            <View style={styles.card}>
              <Text style={styles.seccionTitulo}>
                Respuestas locales ({respuestas.length})
              </Text>
              {respuestas.slice(0, 50).map((r) => (
                <View key={r.id} style={styles.respuestaRow}>
                  <Text style={styles.codigoPregunta}>{r.pregunta_id.slice(0, 8)}…</Text>
                  <Text style={styles.valorRespuesta} numberOfLines={1}>{r.valor || '—'}</Text>
                </View>
              ))}
              {respuestas.length > 50 && (
                <Text style={styles.respuestasMeta}>
                  … y {respuestas.length - 50} más
                </Text>
              )}
            </View>
          )}
        </ScrollView>
      </View>
    );
  }

  if (!sesion) {
    return (
      <View style={styles.root}>
        <GovHeader title="Sesión de encuesta" onBack={() => router.back()} />
        <View style={styles.centrado}>
          <MaterialCommunityIcons name="alert-circle-outline" size={48} color={GOV.rojo} />
          <Text style={styles.errorTxt}>Sesión no encontrada.</Text>
          <GovButton label="Volver" variant="secondary" onPress={() => router.back()} />
        </View>
      </View>
    );
  }

  const colorEstado = ESTADO_COLOR[sesion.estado] ?? '#616161';
  const bgEstado    = colorEstado + '22';
  const estaActiva  = sesion.estado !== 'COMPLETADA' && sesion.estado !== 'SUSPENDIDA';
  const hogarCorto  = sesion.hogar.slice(0, 8);

  return (
    <View style={styles.root}>
      <GovHeader
        title={`Sesión ${sesion.id.slice(0, 8)}…`}
        subtitle={sesion.instrumento_nombre}
        onBack={() => router.back()}
      />

      {/* Miga de pan */}
      <View style={styles.miga}>
        <Text style={styles.migaTxt}>
          Hogares  ›  Hogar {hogarCorto}…  ›  Sesión
        </Text>
      </View>

      <ScrollView contentContainerStyle={styles.content}>

        {/* Encabezado de sesión */}
        <View style={styles.card}>
          <View style={styles.estadoRow}>
            <View style={[styles.estadoChip, { backgroundColor: bgEstado }]}>
              <Text style={[styles.estadoTxt, { color: colorEstado }]}>{sesion.estado_display}</Text>
            </View>
            <Text style={styles.fecha}>
              {new Date(sesion.fecha_inicio).toLocaleDateString('es-CO')}
              {sesion.fecha_fin ? ` — ${new Date(sesion.fecha_fin).toLocaleDateString('es-CO')}` : ''}
            </Text>
          </View>

          <InfoFila label="Hogar"      valor={`${hogarCorto}…`} />
          <InfoFila label="Instrumento" valor={sesion.instrumento_nombre} />

          <Divider style={styles.divider} />

          {/* Barra de progreso — valor tal cual viene, solo acotado a 0–100.
              Ver la nota en encuestas/index.tsx: forzar 100 % en COMPLETADA
              mentía sobre entrevistas cerradas a mitad, y el número bajo que se
              ve es un defecto de `recalcular_porcentaje` en el backend, que no
              evalúa skip-logic. */}
          <View style={styles.progresoRow}>
            <View style={styles.barraWrap}>
              <AnimatedProgressBar
                progress={Math.max(0, Math.min(1, (sesion.porcentaje_completado ?? 0) / 100))}
                color={colorEstado}
                height={8}
              />
            </View>
            <Text style={[styles.pct, { color: colorEstado }]}>
              {Math.max(0, Math.min(100, Math.round(sesion.porcentaje_completado ?? 0)))}%
            </Text>
          </View>
          <Text style={styles.respuestasMeta}>
            {sesion.total_respuestas} respuesta{sesion.total_respuestas !== 1 ? 's' : ''} guardada{sesion.total_respuestas !== 1 ? 's' : ''}
          </Text>
        </View>

        {/* Acciones — solo si la sesión está activa */}
        {estaActiva && (
          <View style={styles.card}>
            <Text style={styles.seccionTitulo}>Continuar</Text>

            <GovButton
              label={`Continuar formulario${sesion.instrumento_nombre ? ` — ${sesion.instrumento_nombre}` : ''}`}
              icon="clipboard-text"
              onPress={() => {
                // Sprint 18 F1B: activar perfil en memoria (instantáneo, sin BD)
                const codigo = (sesion as any).instrumento_codigo as string | undefined;
                if (codigo) {
                  try { activarPerfil(codigo); } catch {}
                }
                router.push({
                  pathname: '/(main)/formulario',
                  params: {
                    sesionServerId: sesion.id,
                    instrumentoId: sesion.instrumento,
                    hogarId: sesion.hogar,
                  },
                });
              }}
            />

            <View style={styles.sepBtn}>
              <GovButton
                label="Finalizar sesión"
                variant="secondary"
                icon="check-circle"
                loading={finalizando}
                disabled={finalizando}
                onPress={confirmarFinalizar}
              />
            </View>
          </View>
        )}

        {/* Respuestas guardadas */}
        {sesion.respuestas.length > 0 && (
          <View style={styles.card}>
            <Text style={styles.seccionTitulo}>
              Respuestas guardadas ({sesion.total_respuestas})
            </Text>
            {sesion.respuestas.map((r) => (
              <View key={r.id} style={styles.respuestaRow}>
                <Text style={styles.codigoPregunta}>[{r.pregunta_codigo}]</Text>
                <Text style={styles.textoPregunta} numberOfLines={1}>{r.pregunta_texto}</Text>
                <Text style={styles.valorRespuesta}>{r.valor || '—'}</Text>
              </View>
            ))}
          </View>
        )}

        {sesion.estado === 'COMPLETADA' && sesion.observaciones ? (
          <View style={styles.card}>
            <Text style={styles.seccionTitulo}>Observaciones</Text>
            <Text style={styles.observaciones}>{sesion.observaciones}</Text>
          </View>
        ) : null}

      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: GOV.fondoApp,
  },
  miga: {
    backgroundColor: GOV.azulTenue,
    paddingHorizontal: SPACING.md,
    paddingVertical: 6,
    borderBottomWidth: 1,
    borderBottomColor: GOV.borde,
  },
  migaTxt: {
    ...FONT.caption,
    color: GOV.azulOscuro,
  },
  offlineBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.xs,
    backgroundColor: GOV.naranjaTenue,
    marginHorizontal: SPACING.md,
    marginTop: SPACING.sm,
    paddingHorizontal: SPACING.sm,
    paddingVertical: 6,
    borderRadius: RADIUS.sm,
  },
  offlineTxt: { ...FONT.caption, color: GOV.naranja, fontWeight: '600' },
  centrado: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: SPACING.xl,
    gap: SPACING.md,
  },
  errorTxt: {
    ...FONT.body,
    color: GOV.rojo,
    textAlign: 'center',
  },
  content: {
    padding: SPACING.md,
    paddingBottom: SPACING.xxl,
  },
  card: {
    backgroundColor: GOV.superficie,
    borderRadius: RADIUS.md,
    padding: SPACING.md,
    marginBottom: SPACING.md,
    ...SHADOW.card,
  },
  estadoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: SPACING.sm,
  },
  estadoChip: {
    borderRadius: RADIUS.pill,
    paddingHorizontal: 10,
    paddingVertical: 3,
  },
  estadoTxt: {
    fontSize: 11,
    fontWeight: '700',
  },
  fecha: {
    ...FONT.caption,
    color: GOV.textoT,
  },
  divider: {
    marginVertical: SPACING.sm,
  },
  progresoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
  },
  barraWrap: {
    flex: 1,
    marginRight: SPACING.sm,
  },
  pct: {
    ...FONT.body,
    fontWeight: '700',
    minWidth: 40,
    textAlign: 'right',
  },
  respuestasMeta: {
    ...FONT.caption,
    color: GOV.textoT,
    marginTop: 2,
  },
  infoFila: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 5,
    borderBottomWidth: 1,
    borderBottomColor: GOV.borde,
  },
  infoLabel: {
    ...FONT.small,
    color: GOV.textoT,
    flex: 1,
  },
  infoValor: {
    ...FONT.small,
    color: GOV.textoP,
    flex: 2,
    textAlign: 'right',
    fontWeight: '500',
  },
  seccionTitulo: {
    ...FONT.label,
    color: GOV.textoS,
    textTransform: 'uppercase',
    letterSpacing: 0.8,
    marginBottom: SPACING.sm,
  },
  sepBtn: {
    marginTop: SPACING.sm,
  },
  respuestaRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    paddingVertical: 5,
    borderBottomWidth: 1,
    borderBottomColor: GOV.borde,
    gap: SPACING.sm,
  },
  codigoPregunta: {
    fontFamily: 'monospace',
    ...FONT.caption,
    color: GOV.azul,
    minWidth: 60,
  },
  textoPregunta: {
    ...FONT.caption,
    color: GOV.textoS,
    flex: 1,
  },
  valorRespuesta: {
    ...FONT.caption,
    color: GOV.textoP,
    fontWeight: '600',
    minWidth: 50,
    textAlign: 'right',
  },
  observaciones: {
    ...FONT.body,
    color: GOV.textoS,
  },
});
