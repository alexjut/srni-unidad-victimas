/**
 * Panel de supervisión — métricas por encuestador + gráficas de producción
 */
import { useEffect, useState } from 'react';
import { Users, ClipboardCheck, Home, TrendingUp, RefreshCw } from 'lucide-react';
import {
  ResponsiveContainer, LineChart, Line, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
} from 'recharts';
import {
  supervisionApi,
  type SupervisorResponse,
  type DashboardSeriesResponse,
} from '@/api/supervision';
import PageHeader from '@/components/ui/PageHeader';
import Card from '@/components/ui/Card';
import Table, { type Column } from '@/components/ui/Table';
import Badge from '@/components/ui/Badge';
import Button from '@/components/ui/Button';
import Alert from '@/components/ui/Alert';

function formatFecha(iso: string) {
  return new Date(iso).toLocaleDateString('es-CO', { day: '2-digit', month: 'short' });
}

export default function SupervisionPage() {
  const [supervisor, setSupervisor] = useState<SupervisorResponse | null>(null);
  const [series, setSeries] = useState<DashboardSeriesResponse | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState('');

  // Filtros de fecha
  const [desde, setDesde] = useState('');
  const [hasta, setHasta] = useState('');

  async function cargar() {
    setCargando(true);
    setError('');
    try {
      const params: Record<string, string> = {};
      if (desde) params.desde = desde;
      if (hasta) params.hasta = hasta;

      const [supRes, serRes] = await Promise.all([
        supervisionApi.resumen(params),
        supervisionApi.series(params),
      ]);
      setSupervisor(supRes.data);
      setSeries(serRes.data);
    } catch (err: any) {
      if (err?.response?.status === 403) {
        setError('No tiene permisos para ver el panel de supervisión.');
      } else {
        setError('No se pudo cargar la información de supervisión.');
      }
    } finally {
      setCargando(false);
    }
  }

  useEffect(() => { cargar(); }, []);

  function aplicarFiltros(e: React.FormEvent) {
    e.preventDefault();
    cargar();
  }

  const columnas: Column<SupervisorResponse['encuestadores'][0]>[] = [
    {
      key: 'nombre',
      header: 'Encuestador',
      render: (e) => (
        <div>
          <p className="text-gray-800 font-medium">{e.nombre_completo}</p>
          <p className="text-xs text-gray-400 font-mono">{e.codigo_usuario}</p>
        </div>
      ),
    },
    { key: 'sesiones', header: 'Sesiones', render: (e) => <span className="text-gray-700 font-semibold">{e.sesiones_total}</span> },
    {
      key: 'completadas',
      header: 'Completadas',
      render: (e) => <Badge variant="verde">{e.sesiones_completadas}</Badge>,
    },
    {
      key: 'en_progreso',
      header: 'En progreso',
      render: (e) => <Badge variant="azul">{e.sesiones_en_progreso}</Badge>,
    },
    { key: 'hogares', header: 'Hogares', render: (e) => <span className="text-gray-700">{e.hogares_caracterizados}</span> },
    {
      key: 'promedio',
      header: 'Avance',
      render: (e) => (
        <div className="flex items-center gap-2">
          <div className="flex-1 bg-gray-100 rounded-full h-2 max-w-[80px]">
            <div
              className={`h-2 rounded-full ${e.promedio_completado >= 80 ? 'bg-gov-verde' : e.promedio_completado >= 40 ? 'bg-gov-azul' : 'bg-gov-naranja'}`}
              style={{ width: `${Math.min(100, e.promedio_completado)}%` }}
            />
          </div>
          <span className="text-xs text-gray-500 w-10 text-right">{e.promedio_completado}%</span>
        </div>
      ),
    },
    {
      key: 'actividad',
      header: 'Última actividad',
      render: (e) => (
        <span className="text-xs text-gray-500">
          {e.ultima_actividad ? new Date(e.ultima_actividad).toLocaleDateString('es-CO') : '—'}
        </span>
      ),
    },
  ];

  return (
    <div className="p-4 sm:p-6 max-w-6xl mx-auto">
      <PageHeader
        titulo="Supervisión"
        subtitulo={supervisor ? `${supervisor.encuestadores_activos} encuestador(es) activos · ${supervisor.periodo_desde} a ${supervisor.periodo_hasta}` : 'Panel de supervisión'}
        acciones={
          <Button variant="secondary" size="sm" icon={RefreshCw} loading={cargando} onClick={cargar}>
            Actualizar
          </Button>
        }
      />

      {/* Filtros de fecha */}
      <form onSubmit={aplicarFiltros} className="flex flex-col sm:flex-row gap-3 mb-6">
        <div>
          <label className="block text-xs font-semibold text-gray-600 uppercase tracking-wide mb-1">Desde</label>
          <input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} className="input" />
        </div>
        <div>
          <label className="block text-xs font-semibold text-gray-600 uppercase tracking-wide mb-1">Hasta</label>
          <input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} className="input" />
        </div>
        <div className="flex items-end">
          <Button type="submit" size="sm">Filtrar</Button>
        </div>
      </form>

      {error && <Alert variant="error" className="mb-6">{error}</Alert>}

      {/* Cards de totales */}
      {supervisor && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <Card icon={ClipboardCheck} label="Sesiones totales" valor={supervisor.totales.sesiones_total} color="bg-gov-azul" />
          <Card icon={TrendingUp} label="Completadas" valor={supervisor.totales.sesiones_completadas} color="bg-gov-verde" />
          <Card icon={Home} label="Hogares caracterizados" valor={supervisor.totales.hogares_caracterizados} color="bg-gov-naranja" />
          <Card icon={Users} label="Encuestadores activos" valor={supervisor.encuestadores_activos} color="bg-purple-600" />
        </div>
      )}

      {/* Gráficas */}
      {series && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
          {/* Serie temporal */}
          <div className="card">
            <h3 className="font-display font-semibold text-gray-700 mb-4 text-sm">
              Actividad diaria
            </h3>
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={series.serie_diaria}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E0E0E0" />
                <XAxis dataKey="fecha" tickFormatter={formatFecha} tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                <Tooltip
                  labelFormatter={(v) => new Date(v).toLocaleDateString('es-CO', { weekday: 'short', day: '2-digit', month: 'short' })}
                />
                <Legend iconSize={10} wrapperStyle={{ fontSize: 12 }} />
                <Line type="monotone" dataKey="sesiones_iniciadas" name="Iniciadas" stroke="#1565C0" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="sesiones_completadas" name="Completadas" stroke="#2E7D32" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Distribución por instrumento */}
          <div className="card">
            <h3 className="font-display font-semibold text-gray-700 mb-4 text-sm">
              Sesiones por instrumento
            </h3>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={series.distribucion_por_instrumento} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#E0E0E0" />
                <XAxis type="number" tick={{ fontSize: 11 }} allowDecimals={false} />
                <YAxis
                  type="category"
                  dataKey="instrumento_nombre"
                  tick={{ fontSize: 10 }}
                  width={140}
                />
                <Tooltip />
                <Bar dataKey="total" name="Sesiones" fill="#1565C0" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Tabla de encuestadores */}
      {supervisor && (
        <>
          <h3 className="font-display font-semibold text-gray-700 mb-3 text-sm">
            Detalle por encuestador
          </h3>
          <Table
            columns={columnas}
            data={supervisor.encuestadores}
            keyExtractor={(e) => e.id}
            cargando={cargando}
            emptyIcon={Users}
            emptyTitulo="No hay encuestadores activos en este período"
            skeletonRows={5}
          />
        </>
      )}
    </div>
  );
}
