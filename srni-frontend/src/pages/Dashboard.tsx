/**
 * Dashboard — métricas principales del encuestador
 */
import { useEffect, useState } from 'react';
import { Home, ClipboardCheck, Users, TrendingUp, RefreshCw } from 'lucide-react';
import { reportesApi, type ResumenEncuestador } from '@/api/reportes';
import { useAuthStore } from '@/stores/authStore';

function MetricCard({
  icon: Icon, label, valor, color,
}: {
  icon: React.ElementType;
  label: string;
  valor: number | string;
  color: string;
}) {
  return (
    <div className="card flex items-center gap-4">
      <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${color}`}>
        <Icon size={22} className="text-white" />
      </div>
      <div>
        <p className="text-2xl font-display font-bold text-gray-800">{valor}</p>
        <p className="text-sm text-gray-500">{label}</p>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const { usuario } = useAuthStore();
  const [resumen, setResumen] = useState<ResumenEncuestador | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState('');

  async function cargar() {
    setCargando(true);
    setError('');
    try {
      const { data } = await reportesApi.resumen();
      setResumen(data);
    } catch {
      setError('No se pudieron cargar las métricas. Verifique la conexión.');
    } finally {
      setCargando(false);
    }
  }

  useEffect(() => { cargar(); }, []);

  const nombre = usuario?.nombre_completo ?? '—';
  const primerNombre = nombre.split(' ')[0];

  return (
    <div className="p-6 max-w-5xl mx-auto">

      {/* Encabezado */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="font-display text-2xl font-bold text-gray-800">
            Hola, {primerNombre} 👋
          </h2>
          <p className="text-gray-500 text-sm mt-0.5">
            {usuario?.perfil?.nombre ?? 'Sin perfil asignado'} ·{' '}
            <span className="text-gov-azul font-medium">{usuario?.codigo_usuario}</span>
          </p>
        </div>
        <button
          onClick={cargar}
          disabled={cargando}
          className="btn-secondary flex items-center gap-2 text-sm"
        >
          <RefreshCw size={15} className={cargando ? 'animate-spin' : ''} />
          Actualizar
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-gov-rojoTenue border border-red-200 text-gov-rojo rounded-lg p-4 mb-6 text-sm">
          {error}
        </div>
      )}

      {/* Métricas */}
      {cargando ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[1,2,3,4].map((i) => (
            <div key={i} className="card animate-pulse h-24 bg-gray-100" />
          ))}
        </div>
      ) : resumen ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <MetricCard
            icon={ClipboardCheck}
            label="Sesiones finalizadas"
            valor={resumen.sesiones_finalizadas}
            color="bg-gov-verde"
          />
          <MetricCard
            icon={TrendingUp}
            label="Sesiones en proceso"
            valor={resumen.sesiones_en_proceso}
            color="bg-gov-azul"
          />
          <MetricCard
            icon={Home}
            label="Hogares registrados"
            valor={resumen.hogares_total}
            color="bg-gov-naranja"
          />
          <MetricCard
            icon={Users}
            label="Víctimas caracterizadas"
            valor={resumen.victimas_caracterizadas}
            color="bg-purple-600"
          />
        </div>
      ) : null}

      {/* Info adicional */}
      <div className="card">
        <h3 className="font-display font-semibold text-gray-700 mb-3">
          Accesos rápidos
        </h3>
        <p className="text-sm text-gray-500">
          Utilice el menú lateral para navegar entre Hogares, Encuestas y Reportes.
        </p>
        <p className="text-xs text-gray-400 mt-2">
          Contrato 2226-2026 · Sistema protegido bajo Ley 1581 de 2012
        </p>
      </div>

    </div>
  );
}
