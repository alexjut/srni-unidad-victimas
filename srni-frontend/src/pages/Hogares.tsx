/**
 * Lista de hogares — tabla paginada con filtros server-side
 */
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Home, Eye, X } from 'lucide-react';
import { hogaresApi, type HogarResumen } from '@/api/hogares';
import Badge, { type BadgeVariant } from '@/components/ui/Badge';
import EmptyState from '@/components/ui/EmptyState';
import Pagination from '@/components/ui/Pagination';
import PageHeader from '@/components/ui/PageHeader';

const ESTADO_BADGE: Record<string, BadgeVariant> = {
  ACTIVO:    'verde',
  BORRADOR:  'naranja',
  ARCHIVADO: 'gris',
};

const ESTADOS_HOGAR = [
  { value: '', label: 'Todos los estados' },
  { value: 'ACTIVO', label: 'Activo' },
  { value: 'BORRADOR', label: 'Borrador' },
  { value: 'ARCHIVADO', label: 'Archivado' },
];

export default function HogaresPage() {
  const navigate = useNavigate();
  const [hogares,  setHogares]  = useState<HogarResumen[]>([]);
  const [total,    setTotal]    = useState(0);
  const [pagina,   setPagina]   = useState(1);
  const [cargando, setCargando] = useState(true);
  const [error,    setError]    = useState('');

  // Filtros
  const [filtroEstado, setFiltroEstado] = useState('');
  const [busqueda, setBusqueda] = useState('');
  const [busquedaActiva, setBusquedaActiva] = useState('');

  const porPagina = 20;
  const totalPags = Math.ceil(total / porPagina);

  async function cargar(pag: number) {
    setCargando(true);
    setError('');
    try {
      const params: Record<string, string | number> = { page: pag };
      if (filtroEstado) params.estado = filtroEstado;
      if (busquedaActiva) params.busqueda = busquedaActiva;
      const { data } = await hogaresApi.listar(params);
      setHogares(data.results);
      setTotal(data.count);
    } catch {
      setError('No se pudieron cargar los hogares.');
    } finally {
      setCargando(false);
    }
  }

  useEffect(() => { cargar(pagina); }, [pagina, filtroEstado, busquedaActiva]);

  function handleEstadoChange(valor: string) {
    setFiltroEstado(valor);
    setPagina(1);
  }

  function handleBuscar(e: React.FormEvent) {
    e.preventDefault();
    setBusquedaActiva(busqueda.trim());
    setPagina(1);
  }

  function limpiarFiltros() {
    setFiltroEstado('');
    setBusqueda('');
    setBusquedaActiva('');
    setPagina(1);
  }

  const hayFiltros = !!filtroEstado || !!busquedaActiva;

  return (
    <div className="p-6 max-w-6xl mx-auto">

      <PageHeader titulo="Hogares" subtitulo={`${total} registro(s) en total`} />

      {/* Barra de filtros */}
      <div className="flex flex-col sm:flex-row gap-3 mb-4">
        <form onSubmit={handleBuscar} className="flex-1 flex gap-2">
          <div className="relative flex-1">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              value={busqueda}
              onChange={(e) => setBusqueda(e.target.value)}
              placeholder="Buscar por código de hogar..."
              className="input pl-9"
            />
          </div>
          <button type="submit" className="btn-primary text-sm px-4">
            Buscar
          </button>
        </form>
        <select
          value={filtroEstado}
          onChange={(e) => handleEstadoChange(e.target.value)}
          className="input w-full sm:w-48"
        >
          {ESTADOS_HOGAR.map((e) => (
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
                {['Código','Encuestador','Municipio','Personas','Estado','Fecha',''].map((h) => (
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
                : hogares.length === 0 ? (
                    <tr>
                      <td colSpan={7}>
                        <EmptyState
                          icon={Home}
                          titulo={hayFiltros ? 'Sin resultados para estos filtros' : 'No hay hogares registrados'}
                          descripcion={hayFiltros ? 'Intenta con otros filtros o limpia la búsqueda.' : 'Los hogares aparecerán aquí cuando se creen desde la app móvil.'}
                        />
                      </td>
                    </tr>
                  ) : hogares.map((h) => (
                    <tr
                      key={h.id}
                      onClick={() => navigate(`/hogares/${h.id}`)}
                      className="hover:bg-gov-azulTenue/30 transition-colors cursor-pointer"
                    >
                      <td className="px-4 py-3 font-mono text-gov-azul font-medium">
                        {h.codigo_hogar ?? h.id.slice(0, 8)}
                      </td>
                      <td className="px-4 py-3 text-gray-800">{h.encuestador_nombre ?? '—'}</td>
                      <td className="px-4 py-3 text-gray-600">{h.municipio_nombre ?? '—'}</td>
                      <td className="px-4 py-3 text-center text-gray-700">{h.total_miembros}</td>
                      <td className="px-4 py-3">
                        <Badge variant={ESTADO_BADGE[h.estado] ?? 'gris'}>
                          {h.estado_display ?? h.estado}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-gray-500">
                        {new Date(h.created_at).toLocaleDateString('es-CO')}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={(e) => { e.stopPropagation(); navigate(`/hogares/${h.id}`); }}
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
