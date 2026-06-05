/**
 * Dashboard — métricas principales del encuestador
 */
import { useEffect, useState } from 'react';
import { Home, ClipboardCheck, Users, TrendingUp, RefreshCw } from 'lucide-react';
import { reportesApi, type ResumenEncuestador } from '@/api/reportes';
import { useAuthStore } from '@/stores/authStore';
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import Alert from '@/components/ui/Alert';

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
    <div className="p-4 sm:p-6 max-w-5xl mx-auto">

      {/* Encabezado */}
      <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h2 className="font-display text-xl sm:text-2xl font-bold text-gray-800">
            Hola, {primerNombre} 👋
          </h2>
          <p className="text-gray-500 text-sm mt-0.5">
            {usuario?.perfil?.nombre ?? 'Sin perfil asignado'} ·{' '}
            <span className="text-gov-azul font-medium">{usuario?.codigo_usuario}</span>
          </p>
        </div>
        <Button
          variant="secondary"
          size="sm"
          onClick={cargar}
          loading={cargando}
          icon={RefreshCw}
          className="self-start sm:self-auto"
        >
          Actualizar
        </Button>
      </div>

      {error && (
        <Alert variant="error" className="mb-6">{error}</Alert>
      )}

      {/* Métricas */}
      {cargando ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1,2,3,4].map((i) => (
            <div key={i} className="card animate-pulse h-24 bg-gray-200" />
          ))}
        </div>
      ) : resumen ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8 animate-fade-in-up">
          <Card icon={ClipboardCheck} label="Sesiones completadas" valor={resumen.sesiones_completadas} color="bg-gov-verde" />
          <Card icon={TrendingUp} label="Sesiones en progreso" valor={resumen.sesiones_en_progreso} color="bg-gov-azul" />
          <Card icon={Home} label="Hogares caracterizados" valor={resumen.hogares_caracterizados} color="bg-gov-naranja" />
          <Card icon={Users} label="Respuestas registradas" valor={resumen.respuestas_total} color="bg-purple-600" />
        </div>
      ) : null}

      {/* Info adicional */}
      <div className="card shadow-soft animate-fade-in-up" style={{ animationDelay: '50ms', animationFillMode: 'both' }}>
        <h3 className="font-display font-semibold text-gray-700 mb-3">
          Accesos rápidos
        </h3>
        <p className="text-sm text-gray-500">
          Utilice el menú lateral para navegar entre Hogares, Encuestas y Reportes.
        </p>
        <p className="text-xs text-gray-400 mt-2">
          Sistema protegido bajo Ley 1581 de 2012
        </p>
      </div>

    </div>
  );
}
