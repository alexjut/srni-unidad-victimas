/**
 * Lista de sesiones de encuesta — tabla paginada con filtros server-side
 */
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ClipboardList, Eye, X } from 'lucide-react';
import { encuestasApi, type SesionResumen } from '@/api/encuestas';
import Badge, { type BadgeVariant } from '@/components/ui/Badge';
import EmptyState from '@/components/ui/EmptyState';
import Pagination from '@/components/ui/Pagination';
import PageHeader from '@/components/ui/PageHeader';

const ESTADO_BADGE: Record<string, BadgeVariant> = {
  COMPLETADA:  'verde',
  FINALIZADA:  'verde',
  EN_PROGRESO: 'azul',
  INICIADA:    'naranja',
  SUSPENDIDA:  'rojo',
  CANCELADA:   'rojo',
};

const ESTADOS_SESION = [
  { value: '', label: 'Todos los estados' },
  { value: 'COMPLETADA', label: 'Completada' },
  { value: 'EN_PROGRESO', label: 'En progreso' },
  { value: 'INICIADA', label: 'Iniciada' },
  { value: 'SUSPENDIDA', label: 'Suspendida' },
];

function BarraProgreso({ valor }: { valor: number }) {
  const color = valor >= 80 ? 'bg-gov-verde' : valor >= 40 ? 'bg-gov-azul' : 'bg-gov-naranja';
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-gray-100 rounded-full h-2">
        <div className={`h-2 rounded-full ${color}`} style={{ width: `${valor}%` }} />
      </div>
      <span className="text-xs text-gray-500 w-8 text-right">{valor}%</span>
    </div>
  );
}

export default function EncuestasPage() {
  const navigate = useNavigate();
  const [sesiones, setSesiones] = useState<SesionResumen[]>([]);
  const [total,    setTotal]    = useState(0);
  const [pagina,   setPagina]   = useState(1);
  const [cargando, setCargando] = useState(true);
  const [error,    setError]    = useState('');

  // Filtros
  const [filtroEstado, setFiltroEstado] = useState('');

  const porPagina = 20;
  const totalPags = Math.ceil(total / porPagina);

  async function cargar(pag: number) {
    setCargando(true);
    setError('');
    try {
      const params: Record<string, string | number> = { page: pag };
      if (filtroEstado) params.estado = filtroEstado;
      const { data } = await encuestasApi.listar(params);
      setSesiones(data.results);
      setTotal(data.count);
    } catch {
      setError('No se pudieron cargar las encuestas.');
    } finally {
      setCargando(false);
    }
  }

  useEffect(() => { cargar(pagina); }, [pagina, filtroEstado]);

  function handleEstadoChange(valor: string) {
    setFiltroEstado(valor);
    setPagina(1);
  }

  function limpiarFiltros() {
    setFiltroEstado('');
    setPagina(1);
  }

  const hayFiltros = !!filtroEstado;

  return (
    <div className="p-6 max-w-6xl mx-auto">

      <PageHeader titulo="Encuestas" subtitulo={`${total} sesión(es) registradas`} />

      {/* Barra de filtros */}
      <div className="flex flex-col sm:flex-row gap-3 mb-4">
        <select
          value={filtroEstado}
          onChange={(e) => handleEstadoChange(e.target.value)}
          className="input w-full sm:w-52"
        >
          {ESTADOS_SESION.map((e) => (
            <option key={e.value} value={e.value}>{e.label}</option>
          ))}
        </select>
        {hayFiltros && (
          <button onClick={limpiarFiltros} className="btn-secondary flex items-center gap-1 text-sm px-3">
            <X size={14} /> Limpiar
          </button>
        )}
      </div>

      {error && (
        <div className="bg-gov-rojoTenue border border-red-200 text-gov-rojo rounded-lg p-4 mb-4 text-sm">
          {error}
        </div>
      )}

      <div className="card overflow-hidden p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gov-borde">
              <tr>
                {['Instrumento','DT','Progreso','Estado','Encuestador','Fecha',''].map((h) => (
                  <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gov-borde">
              {cargando
                ? Array.from({ length: 8 }).map((_, i) => (
                    <tr key={i}>
                      {Array.from({ length: 7 }).map((_, j) => (
                        <td key={j} className="px-4 py-3">
                          <div className="h-4 bg-gray-100 rounded animate-pulse" />
                        </td>
                      ))}
                    </tr>
                  ))
                : sesiones.length === 0 ? (
                    <tr>
                      <td colSpan={7}>
                        <EmptyState
                          icon={ClipboardList}
                          titulo={hayFiltros ? 'Sin resultados para este filtro' : 'No hay encuestas registradas'}
                          descripcion={hayFiltros ? 'Intenta con otro estado o limpia el filtro.' : 'Las sesiones aparecerán aquí cuando se inicien desde la app móvil.'}
                        />
                      </td>
                    </tr>
                  ) : sesiones.map((s) => (
                    <tr
                      key={s.id}
                      onClick={() => navigate(`/encuestas/${s.id}`)}
                      className="hover:bg-gov-azulTenue/30 transition-colors cursor-pointer"
                    >
                      <td className="px-4 py-3 text-gray-700 max-w-[180px] truncate">{s.instrumento_nombre}</td>
                      <td className="px-4 py-3 text-gray-600 text-xs">{s.direccion_territorial_nombre ?? '—'}</td>
                      <td className="px-4 py-3 min-w-[120px]">
                        <BarraProgreso valor={s.porcentaje_completado} />
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant={ESTADO_BADGE[s.estado] ?? 'gris'}>
                          {s.estado_display ?? s.estado.replace('_', ' ')}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-gray-600 text-xs">{s.encuestador_nombre}</td>
                      <td className="px-4 py-3 text-gray-500 text-xs">
                        {new Date(s.created_at).toLocaleDateString('es-CO')}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={(e) => { e.stopPropagation(); navigate(`/encuestas/${s.id}`); }}
                          className="inline-flex items-center gap-1.5 text-xs font-semibold bg-gov-azul text-white px-3 py-1.5 rounded-md hover:bg-gov-azulOscuro transition-colors"
                        >
                          <Eye size={14} /> Ver detalle
                        </button>
                      </td>
                    </tr>
                  ))}
            </tbody>
          </table>
        </div>

        <Pagination pagina={pagina} totalPaginas={totalPags} onChange={setPagina} />
      </div>
    </div>
  );
}
