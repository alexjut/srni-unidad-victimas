// Pantalla de reportes de producción del encuestador — Sprint 10.
import { useEffect, useState, useCallback } from 'react';
import { View, ScrollView, StyleSheet, RefreshControl, Linking } from 'react-native';
import { Text, ProgressBar, ActivityIndicator, Chip, Divider } from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { reportesApi } from '../../src/api/reportes';
import type { ProduccionResumen, SesionReporte, ResumenInstrumento } from '../../src/api/reportes';
import { useAuthStore } from '../../src/stores/authStore';
import { GovHeader } from '../../src/components/GovHeader';
import { GovButton } from '../../src/components/GovButton';
import { GOV, SPACING, RADIUS, SHADOW, FONT } from '../../src/theme/govTheme';

// ─── Período ──────────────────────────────────────────────────────────────────

type Periodo = 'mes' | 'semana' | 'todo';

function calcularPeriodo(periodo: Periodo): { desde: string; hasta: string } {
  const hoy = new Date();
  const fmt = (d: Date) => d.toISOString().slice(0, 10);

  if (periodo === 'semana') {
    const lunes = new Date(hoy);
    lunes.setDate(hoy.getDate() - ((hoy.getDay() + 6) % 7));
    return { desde: fmt(lunes), hasta: fmt(hoy) };
  }
  if (periodo === 'mes') {
    return { desde: fmt(new Date(hoy.getFullYear(), hoy.getMonth(), 1)), hasta: fmt(hoy) };
  }
  // todo
  return { desde: '2020-01-01', hasta: fmt(hoy) };
}

// ─── Tarjeta de métrica ───────────────────────────────────────────────────────

function MetricaCard({
  icono, valor, etiqueta, color,
}: { icono: string; valor: number | string; etiqueta: string; color: string }) {
  return (
    <View style={[styles.metricaCard, { borderTopColor: color }]}>
      <MaterialCommunityIcons name={icono as any} size={22} color={color} />
      <Text style={[styles.metricaValor, { color }]}>{valor}</Text>
      <Text style={styles.metricaEtiqueta}>{etiqueta}</Text>
    </View>
  );
}

// ─── Fila de sesión ───────────────────────────────────────────────────────────

const ESTADO_COLOR: Record<string, string> = {
  COMPLETADA:  GOV.verde,
  EN_PROGRESO: GOV.naranja,
  INICIADA:    GOV.azul,
  SUSPENDIDA:  '#616161',
};

function SesionFila({ sesion }: { sesion: SesionReporte }) {
  const color = ESTADO_COLOR[sesion.estado] ?? '#616161';
  return (
    <View style={styles.sesionFila}>
      <View style={[styles.sesionEstadoDot, { backgroundColor: color }]} />
      <View style={styles.sesionBody}>
        <View style={styles.sesionTop}>
          <Text style={styles.sesionInstr} numberOfLines={1}>
            {sesion.instrumento_nombre || sesion.perfil_codigo}
          </Text>
          <Text style={[styles.sesionPct, { color }]}>
            {sesion.porcentaje_completado}%
          </Text>
        </View>
        <ProgressBar
          progress={sesion.porcentaje_completado / 100}
          style={styles.sesionBarra}
          color={color}
        />
        <View style={styles.sesionMeta}>
          <Text style={styles.sesionMetaTxt}>
            {new Date(sesion.fecha_inicio).toLocaleDateString('es-CO')}
          </Text>
          {sesion.duracion_minutos != null && (
            <Text style={styles.sesionMetaTxt}>
              {sesion.duracion_minutos < 60
                ? `${sesion.duracion_minutos} min`
                : `${(sesion.duracion_minutos / 60).toFixed(1)} h`}
            </Text>
          )}
          <Text style={styles.sesionMetaTxt}>
            {sesion.respuestas_total} resp.
          </Text>
        </View>
      </View>
    </View>
  );
}

// ─── Pantalla ─────────────────────────────────────────────────────────────────

export default function ReportesScreen() {
  const { usuario } = useAuthStore();
  const [reporte, setReporte] = useState<ProduccionResumen | null>(null);
  const [cargando, setCargando] = useState(true);
  const [refrescando, setRefrescando] = useState(false);
  const [error, setError] = useState('');
  const [periodo, setPeriodo] = useState<Periodo>('mes');

  const cargar = useCallback(async (p: Periodo = periodo) => {
    setError('');
    const filtros = calcularPeriodo(p);
    try {
      const { data } = await reportesApi.resumen(filtros);
      setReporte(data);
    } catch {
      setError('No se pudo cargar el reporte. Verifica tu conexión.');
    } finally {
      setCargando(false);
      setRefrescando(false);
    }
  }, [periodo]);

  useEffect(() => { cargar(periodo); }, [periodo]);

  function cambiarPeriodo(p: Periodo) {
    setPeriodo(p);
    setCargando(true);
  }

  async function exportar() {
    const filtros = calcularPeriodo(periodo);
    const url = reportesApi.exportUrl(filtros);
    try {
      await Linking.openURL(url);
    } catch {
      // Silencioso — el navegador nativo lo manejará
    }
  }

  if (cargando) {
    return (
      <View style={styles.root}>
        <GovHeader title="Mis reportes" onBack={() => router.back()} />
        <View style={styles.centrado}>
          <ActivityIndicator size="large" color={GOV.azul} />
        </View>
      </View>
    );
  }

  if (error || !reporte) {
    return (
      <View style={styles.root}>
        <GovHeader title="Mis reportes" onBack={() => router.back()} />
        <View style={styles.centrado}>
          <MaterialCommunityIcons name="wifi-off" size={48} color={GOV.textoT} />
          <Text style={styles.errorTxt}>{error || 'Sin datos.'}</Text>
          <GovButton label="Reintentar" variant="secondary" onPress={() => cargar(periodo)} />
        </View>
      </View>
    );
  }

  return (
    <View style={styles.root}>
      <GovHeader
        title="Mis reportes"
        subtitle={reporte.encuestador_nombre}
        onBack={() => router.back()}
      />

      <ScrollView
        contentContainerStyle={styles.content}
        refreshControl={
          <RefreshControl
            refreshing={refrescando}
            onRefresh={() => { setRefrescando(true); cargar(periodo); }}
            colors={[GOV.azul]}
          />
        }
      >
        {/* Selector de período */}
        <View style={styles.periodosRow}>
          {(['semana', 'mes', 'todo'] as Periodo[]).map((p) => (
            <Chip
              key={p}
              selected={periodo === p}
              onPress={() => cambiarPeriodo(p)}
              style={[styles.periodoChip, periodo === p && styles.periodoChipActivo]}
              textStyle={[styles.periodoTxt, periodo === p && styles.periodoTxtActivo]}
            >
              {p === 'semana' ? 'Esta semana' : p === 'mes' ? 'Este mes' : 'Todo'}
            </Chip>
          ))}
        </View>

        {/* Métricas principales */}
        <View style={styles.metricasGrid}>
          <MetricaCard
            icono="check-circle"
            valor={reporte.sesiones_completadas}
            etiqueta="Completadas"
            color={GOV.verde}
          />
          <MetricaCard
            icono="progress-clock"
            valor={reporte.sesiones_en_progreso}
            etiqueta="En progreso"
            color={GOV.naranja}
          />
          <MetricaCard
            icono="home-group"
            valor={reporte.hogares_caracterizados}
            etiqueta="Hogares"
            color={GOV.azul}
          />
          <MetricaCard
            icono="format-list-checks"
            valor={reporte.respuestas_total.toLocaleString('es-CO')}
            etiqueta="Respuestas"
            color="#7B1FA2"
          />
        </View>

        {/* Progreso promedio */}
        <View style={styles.card}>
          <Text style={styles.cardTitulo}>Promedio completado</Text>
          <View style={styles.progresoRow}>
            <ProgressBar
              progress={reporte.promedio_completado / 100}
              style={styles.barraGlobal}
              color={GOV.azul}
            />
            <Text style={styles.progresoPct}>{reporte.promedio_completado}%</Text>
          </View>
          <Text style={styles.cardMeta}>
            {reporte.sesiones_total} sesión{reporte.sesiones_total !== 1 ? 'es' : ''} en el período
          </Text>
        </View>

        {/* Por instrumento */}
        {reporte.por_instrumento.length > 0 && (
          <View style={styles.card}>
            <Text style={styles.cardTitulo}>Por instrumento</Text>
            {reporte.por_instrumento.map((instr: ResumenInstrumento, i) => (
              <View key={instr.instrumento_id.toString()}>
                {i > 0 && <Divider style={styles.divider} />}
                <View style={styles.instrFila}>
                  <View style={styles.instrTextos}>
                    <Text style={styles.instrNombre} numberOfLines={1}>
                      {instr.instrumento_nombre || instr.perfil_codigo}
                    </Text>
                    <Text style={styles.instrMeta}>
                      {instr.completadas}/{instr.total} completadas · {instr.promedio_completado}% prom.
                    </Text>
                  </View>
                  <ProgressBar
                    progress={instr.total > 0 ? instr.completadas / instr.total : 0}
                    style={styles.instrBarra}
                    color={GOV.verde}
                  />
                </View>
              </View>
            ))}
          </View>
        )}

        {/* Sesiones recientes */}
        {reporte.sesiones_recientes.length > 0 && (
          <View style={styles.card}>
            <View style={styles.cardHeader}>
              <Text style={styles.cardTitulo}>Sesiones recientes</Text>
              <Chip
                compact
                onPress={() => router.push('/(main)/encuestas')}
                style={styles.verTodas}
                textStyle={styles.verTodasTxt}
              >
                Ver todas
              </Chip>
            </View>
            {reporte.sesiones_recientes.map((s, i) => (
              <View key={s.id}>
                {i > 0 && <Divider style={styles.divider} />}
                <SesionFila sesion={s} />
              </View>
            ))}
          </View>
        )}

        {/* Exportar CSV */}
        <GovButton
          label="Exportar CSV"
          icon="file-download"
          variant="secondary"
          onPress={exportar}
        />

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
    padding: SPACING.xl,
    gap: SPACING.md,
  },
  errorTxt: {
    ...FONT.body,
    color: GOV.textoT,
    textAlign: 'center',
  },
  content: {
    padding: SPACING.md,
    paddingBottom: SPACING.xxl,
    gap: SPACING.md,
  },
  periodosRow: {
    flexDirection: 'row',
    gap: SPACING.sm,
  },
  periodoChip: {
    backgroundColor: GOV.superficie,
    borderRadius: RADIUS.pill,
  },
  periodoChipActivo: {
    backgroundColor: GOV.azulTenue,
  },
  periodoTxt: {
    ...FONT.caption,
    color: GOV.textoS,
  },
  periodoTxtActivo: {
    color: GOV.azul,
    fontWeight: '700',
  },
  metricasGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: SPACING.sm,
  },
  metricaCard: {
    flex: 1,
    minWidth: '45%',
    backgroundColor: GOV.superficie,
    borderRadius: RADIUS.md,
    borderTopWidth: 3,
    padding: SPACING.md,
    alignItems: 'center',
    gap: 4,
    ...SHADOW.card,
  },
  metricaValor: {
    fontSize: 26,
    fontWeight: '800',
    lineHeight: 32,
  },
  metricaEtiqueta: {
    ...FONT.caption,
    color: GOV.textoT,
    textAlign: 'center',
  },
  card: {
    backgroundColor: GOV.superficie,
    borderRadius: RADIUS.md,
    padding: SPACING.md,
    ...SHADOW.card,
    gap: SPACING.sm,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  cardTitulo: {
    ...FONT.label,
    color: GOV.textoS,
    textTransform: 'uppercase',
    letterSpacing: 0.8,
  },
  cardMeta: {
    ...FONT.caption,
    color: GOV.textoT,
  },
  progresoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.sm,
  },
  barraGlobal: {
    flex: 1,
    height: 10,
    borderRadius: 5,
  },
  progresoPct: {
    ...FONT.body,
    fontWeight: '700',
    color: GOV.azul,
    minWidth: 44,
    textAlign: 'right',
  },
  divider: {
    marginVertical: 4,
  },
  instrFila: {
    gap: 4,
    paddingVertical: SPACING.sm,
  },
  instrTextos: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: SPACING.sm,
  },
  instrNombre: {
    ...FONT.small,
    color: GOV.textoP,
    fontWeight: '600',
    flex: 1,
  },
  instrMeta: {
    ...FONT.caption,
    color: GOV.textoT,
  },
  instrBarra: {
    height: 6,
    borderRadius: 3,
  },
  sesionFila: {
    flexDirection: 'row',
    gap: SPACING.sm,
    paddingVertical: SPACING.sm,
  },
  sesionEstadoDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginTop: 6,
    flexShrink: 0,
  },
  sesionBody: {
    flex: 1,
    gap: 4,
  },
  sesionTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  sesionInstr: {
    ...FONT.small,
    color: GOV.textoP,
    fontWeight: '600',
    flex: 1,
  },
  sesionPct: {
    ...FONT.small,
    fontWeight: '700',
    minWidth: 36,
    textAlign: 'right',
  },
  sesionBarra: {
    height: 4,
    borderRadius: 2,
  },
  sesionMeta: {
    flexDirection: 'row',
    gap: SPACING.md,
  },
  sesionMetaTxt: {
    ...FONT.caption,
    color: GOV.textoT,
  },
  verTodas: {
    backgroundColor: GOV.azulTenue,
    borderRadius: RADIUS.pill,
  },
  verTodasTxt: {
    ...FONT.caption,
    color: GOV.azul,
    fontWeight: '600',
  },
});
