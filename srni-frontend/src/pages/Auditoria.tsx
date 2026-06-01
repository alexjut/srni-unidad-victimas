/**
 * Auditoría — logs de acceso inmutables (solo lectura)
 * NOTA: El endpoint GET /api/auditoria/logs/ aún no está implementado en el backend.
 * Página lista para funcionar cuando Javier lo implemente.
 */
import { useEffect, useState } from 'react';
import { Shield, Trash2 } from 'lucide-react';
import { auditoriaApi, type LogAuditoria } from '@/api/auditoria';
import PageHeader from '@/components/ui/PageHeader';
import Table, { type Column } from '@/components/ui/Table';
import Alert from '@/components/ui/Alert';

const PAGE_SIZE = 20;

const ACCION_BADGE: Record<string, string> = {
  BUSQUEDA_RNI: 'bg-purple-50 text-purple-700',
  VER_VICTIMA: 'bg-gov-azulTenue text-gov-azul',
  LOGIN: 'bg-gov-verdeTenue text-gov-verde',
  LOGOUT: 'bg-gray-100 text-gray-600',
  CREAR_HOGAR: 'bg-gov-naranjaTenue text-gov-naranja',
  CREAR_SESION: 'bg-gov-naranjaTenue text-gov-naranja',
  FINALIZAR_SESION: 'bg-gov-verdeTenue text-gov-verde',
};

const RESULTADO_BADGE: Record<string, string> = {
  EXITO: 'text-gov-verde',
  ERROR: 'text-gov-rojo',
  DENEGADO: 'text-gov-naranja',
};

export default function AuditoriaPage() {
  const [logs, setLogs] = useState<LogAuditoria[]>([]);
  const [total, setTotal] = useState(0);
  const [pagina, setPagina] = useState(1);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState('');

  // Filtros
  const [filtroAccion, setFiltroAccion] = useState('');
  const [filtroDesde, setFiltroDesde] = useState('');
  const [filtroHasta, setFiltroHasta] = useState('');

  const hayFiltros = filtroAccion || filtroDesde || filtroHasta;

  function cargar(pag: number) {
    setCargando(true);
    setError('');
    auditoriaApi.logs({
      page: pag,
      ...(filtroAccion && { accion: filtroAccion }),
      ...(filtroDesde && { fecha_desde: filtroDesde }),
      ...(filtroHasta && { fecha_hasta: filtroHasta }),
    })
      .then(({ data }) => {
        setLogs(data.results);
        setTotal(data.count);
      })
      .catch(() => setError('El endpoint de auditoría aún no está disponible. Contacte al administrador del backend.'))
      .finally(() => setCargando(false));
  }

  useEffect(() => {
    cargar(pagina);
  }, [pagina]);

  function aplicarFiltros() {
    setPagina(1);
    cargar(1);
  }

  function limpiarFiltros() {
    setFiltroAccion('');
    setFiltroDesde('');
    setFiltroHasta('');
    setPagina(1);
    setCargando(true);
    setError('');
    auditoriaApi.logs({ page: 1 })
      .then(({ data }) => {
        setLogs(data.results);
        setTotal(data.count);
      })
      .catch(() => setError('El endpoint de auditoría aún no está disponible. Contacte al administrador del backend.'))
      .finally(() => setCargando(false));
  }

  const totalPaginas = Math.ceil(total / PAGE_SIZE);

  const columnas: Column<LogAuditoria>[] = [
    {
      key: 'timestamp',
      header: 'Fecha',
      className: 'w-40',
      render: (log) => (
        <span className="text-xs text-gray-500 whitespace-nowrap">
          {new Date(log.timestamp).toLocaleDateString('es-CO', {
            day: '2-digit',
            month: 'short',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
          })}
        </span>
      ),
    },
    {
      key: 'usuario',
      header: 'Usuario',
      className: 'w-36',
      render: (log) => (
        <div>
          <p className="font-mono text-sm text-gov-azul">{log.codigo_usuario}</p>
          {log.usuario_nombre && (
            <p className="text-xs text-gray-400">{log.usuario_nombre}</p>
          )}
        </div>
      ),
    },
    {
      key: 'accion',
      header: 'Acción',
      className: 'w-36',
      render: (log) => (
        <span className={`inline-block text-xs font-medium px-2 py-0.5 rounded-full ${ACCION_BADGE[log.accion] ?? 'bg-gray-100 text-gray-600'}`}>
          {log.accion.replace(/_/g, ' ')}
        </span>
      ),
    },
    {
      key: 'recurso',
      header: 'Recurso',
      render: (log) => (
        <span className="text-sm text-gray-700">{log.recurso}</span>
      ),
    },
    {
      key: 'resultado',
      header: 'Resultado',
      className: 'w-24',
      render: (log) => (
        <span className={`text-xs font-semibold ${RESULTADO_BADGE[log.resultado] ?? 'text-gray-500'}`}>
          {log.resultado}
        </span>
      ),
    },
    {
      key: 'ip_origen',
      header: 'IP',
      className: 'w-32',
      render: (log) => (
        <span className="text-xs font-mono text-gray-500">{log.ip_origen}</span>
      ),
    },
    {
      key: 'detalle',
      header: 'Detalle',
      render: (log) => (
        <span className="text-xs text-gray-400 line-clamp-2">{log.detalle || '—'}</span>
      ),
    },
  ];

  return (
    <div className="p-4 sm:p-6 max-w-7xl mx-auto">
      <PageHeader
        titulo="Auditoría"
        subtitulo={`Registro de accesos al sistema · ${total} evento(s)`}
      />

      {/* Filtros */}
      <div className="card mb-6">
        <div className="flex flex-col sm:flex-row gap-3 items-end">
          <div className="sm:w-48">
            <label className="block text-xs font-semibold text-gray-600 uppercase tracking-wide mb-1">
              Acción
            </label>
            <select
              value={filtroAccion}
              onChange={(e) => setFiltroAccion(e.target.value)}
              className="input"
            >
              <option value="">Todas</option>
              <option value="LOGIN">Login</option>
              <option value="LOGOUT">Logout</option>
              <option value="BUSQUEDA_RNI">Búsqueda RNI</option>
              <option value="VER_VICTIMA">Ver víctima</option>
              <option value="CREAR_HOGAR">Crear hogar</option>
              <option value="CREAR_SESION">Crear sesión</option>
              <option value="FINALIZAR_SESION">Finalizar sesión</option>
            </select>
          </div>

          <div className="sm:w-44">
            <label className="block text-xs font-semibold text-gray-600 uppercase tracking-wide mb-1">
              Desde
            </label>
            <input
              type="date"
              value={filtroDesde}
              onChange={(e) => setFiltroDesde(e.target.value)}
              className="input"
            />
          </div>

          <div className="sm:w-44">
            <label className="block text-xs font-semibold text-gray-600 uppercase tracking-wide mb-1">
              Hasta
            </label>
            <input
              type="date"
              value={filtroHasta}
              onChange={(e) => setFiltroHasta(e.target.value)}
              className="input"
            />
          </div>

          <button
            onClick={aplicarFiltros}
            className="btn-primary h-[38px] px-4 text-sm"
          >
            Filtrar
          </button>

          {hayFiltros && (
            <button
              onClick={limpiarFiltros}
              className="flex items-center gap-1 text-xs text-white bg-gov-rojo hover:bg-red-700 border border-gov-rojo rounded-md px-2.5 py-2 transition-colors h-[38px]"
            >
              <Trash2 size={12} />
              Limpiar
            </button>
          )}
        </div>
      </div>

      {error && <Alert variant="warning" className="mb-4">{error}</Alert>}

      {/* Nota de inmutabilidad */}
      <div className="flex items-center gap-2 mb-4 text-xs text-gray-400">
        <Shield size={14} />
        <span>Los registros de auditoría son inmutables y no pueden ser modificados ni eliminados.</span>
      </div>

      <Table
        columns={columnas}
        data={logs}
        keyExtractor={(log) => log.id}
        cargando={cargando}
        emptyIcon={Shield}
        emptyTitulo="Sin registros de auditoría"
        emptyDescripcion={hayFiltros ? 'No hay registros que coincidan con los filtros aplicados.' : 'Los registros aparecerán aquí cuando el endpoint esté disponible en el backend.'}
        pagina={pagina}
        totalPaginas={totalPaginas}
        onPaginaChange={setPagina}
      />
    </div>
  );
}
