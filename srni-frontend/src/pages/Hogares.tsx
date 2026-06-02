/**
 * Lista de hogares — tabla paginada con filtros server-side
 */
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Home, Eye, X } from 'lucide-react';
import { hogaresApi, type HogarResumen } from '@/api/hogares';
import Badge, { type BadgeVariant } from '@/components/ui/Badge';
import PageHeader from '@/components/ui/PageHeader';
import Table, { type Column } from '@/components/ui/Table';
import Button from '@/components/ui/Button';
import Alert from '@/components/ui/Alert';

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

  const columnas: Column<HogarResumen>[] = [
    {
      key: 'codigo',
      header: 'Código',
      render: (h) => (
        <span className="font-mono text-gov-azul font-medium">
          {h.codigo_hogar || h.id.slice(0, 8)}
        </span>
      ),
    },
    { key: 'encuestador', header: 'Encuestador', render: (h) => <span className="text-gray-800">{h.encuestador_nombre ?? '—'}</span> },
    { key: 'municipio', header: 'Municipio', render: (h) => <span className="text-gray-600">{h.municipio_nombre ?? '—'}</span> },
    { key: 'personas', header: 'Personas', render: (h) => <span className="text-gray-700">{h.total_miembros}</span> },
    {
      key: 'estado',
      header: 'Estado',
      render: (h) => (
        <Badge variant={ESTADO_BADGE[h.estado] ?? 'gris'}>
          {h.estado_display ?? h.estado}
        </Badge>
      ),
    },
    { key: 'fecha', header: 'Fecha', render: (h) => <span className="text-gray-500">{new Date(h.created_at).toLocaleDateString('es-CO')}</span> },
    {
      key: 'acciones',
      header: '',
      render: (h) => (
        <div className="text-right">
          <Button size="sm" icon={Eye} onClick={(e) => { e.stopPropagation(); navigate(`/hogares/${h.id}`); }}>
            Ver detalle
          </Button>
        </div>
      ),
    },
  ];

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
          <Button type="submit" size="sm">Buscar</Button>
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
          <Button variant="secondary" size="sm" icon={X} onClick={limpiarFiltros}>
            Limpiar
          </Button>
        )}
      </div>

      {error && <Alert variant="error" className="mb-4">{error}</Alert>}

      <Table<HogarResumen>
        columns={columnas}
        data={hogares}
        keyExtractor={(h) => h.id}
        cargando={cargando}
        onRowClick={(h) => navigate(`/hogares/${h.id}`)}
        emptyIcon={Home}
        emptyTitulo={hayFiltros ? 'Sin resultados para estos filtros' : 'No hay hogares registrados'}
        emptyDescripcion={hayFiltros ? 'Intenta con otros filtros o limpia la búsqueda.' : 'Los hogares aparecerán aquí cuando se creen desde la app móvil.'}
        pagina={pagina}
        totalPaginas={totalPags}
        onPaginaChange={setPagina}
      />
    </div>
  );
}
