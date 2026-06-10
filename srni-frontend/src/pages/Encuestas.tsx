/**
 * Lista de sesiones de encuesta — tabla paginada con filtros server-side
 */
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ClipboardList, Eye, X } from 'lucide-react';
import { encuestasApi, type SesionResumen } from '@/api/encuestas';
import Badge, { type BadgeVariant } from '@/components/ui/Badge';
import PageHeader from '@/components/ui/PageHeader';
import Table, { type Column } from '@/components/ui/Table';
import Button from '@/components/ui/Button';
import Dropdown from '@/components/ui/Dropdown';
import Alert from '@/components/ui/Alert';

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
      <div className="flex-1 bg-gray-100 rounded-full h-1.5">
        <div className={`h-1.5 rounded-full transition-all ${color}`} style={{ width: `${valor}%` }} />
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

  const columnas: Column<SesionResumen>[] = [
    { key: 'instrumento', header: 'Instrumento', render: (s) => <span className="text-gray-700 max-w-[180px] truncate block">{s.instrumento_nombre}</span> },
    { key: 'dt', header: 'DT', render: (s) => <span className="text-gray-600 text-xs">{s.direccion_territorial_nombre ?? '—'}</span> },
    { key: 'progreso', header: 'Progreso', render: (s) => <BarraProgreso valor={s.porcentaje_completado} />, className: 'min-w-[120px]' },
    {
      key: 'estado',
      header: 'Estado',
      render: (s) => (
        <Badge variant={ESTADO_BADGE[s.estado] ?? 'gris'}>
          {s.estado_display ?? s.estado.replace('_', ' ')}
        </Badge>
      ),
    },
    { key: 'encuestador', header: 'Encuestador', render: (s) => <span className="text-gray-600 text-xs">{s.encuestador_nombre}</span> },
    { key: 'fecha', header: 'Fecha', render: (s) => <span className="text-gray-500 text-xs">{new Date(s.created_at).toLocaleDateString('es-CO')}</span> },
    {
      key: 'acciones',
      header: '',
      render: (s) => (
        <div className="text-right">
          <Button size="sm" icon={Eye} onClick={(e) => { e.stopPropagation(); navigate(`/encuestas/${s.id}`); }}>
            Ver detalle
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div className="p-6 max-w-6xl mx-auto">

      <PageHeader titulo="Encuestas" subtitulo={`${total} sesión(es) registradas`} />

      {/* Barra de filtros */}
      <div className="card shadow-soft flex flex-col sm:flex-row gap-3 mb-4">
        <div className="w-full sm:w-52">
          <Dropdown
            value={filtroEstado}
            onChange={handleEstadoChange}
            options={ESTADOS_SESION}
          />
        </div>
        {hayFiltros && (
          <Button variant="secondary" size="sm" icon={X} onClick={limpiarFiltros}>
            Limpiar
          </Button>
        )}
      </div>

      {error && <Alert variant="error" className="mb-4">{error}</Alert>}

      <Table<SesionResumen>
        columns={columnas}
        data={sesiones}
        keyExtractor={(s) => s.id}
        cargando={cargando}
        onRowClick={(s) => navigate(`/encuestas/${s.id}`)}
        emptyIcon={ClipboardList}
        emptyTitulo={hayFiltros ? 'Sin resultados para este filtro' : 'No hay encuestas registradas'}
        emptyDescripcion={hayFiltros ? 'Intenta con otro estado o limpia el filtro.' : 'Las sesiones aparecerán aquí cuando se inicien desde la app móvil.'}
        pagina={pagina}
        totalPaginas={totalPags}
        onPaginaChange={setPagina}
      />
    </div>
  );
}
