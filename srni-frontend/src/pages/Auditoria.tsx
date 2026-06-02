/**
 * Auditoría — logs de acceso inmutables (solo lectura)
 */
import { useEffect, useState } from 'react';
import { Shield, Trash2 } from 'lucide-react';
import { auditoriaApi, ACCIONES_AUDITORIA, type LogAuditoria } from '@/api/auditoria';
import PageHeader from '@/components/ui/PageHeader';
import Table, { type Column } from '@/components/ui/Table';
import Button from '@/components/ui/Button';
import Alert from '@/components/ui/Alert';

const PAGE_SIZE = 20;

const ACCION_BADGE: Record<string, string> = {
  LOGIN: 'bg-gov-verdeTenue text-gov-verde',
  LOGOUT: 'bg-gray-100 text-gray-600',
  LOGIN_FALLIDO: 'bg-gov-rojoTenue text-gov-rojo',
  BUSQUEDA_RNI: 'bg-purple-50 text-purple-700',
  VER_VICTIMA: 'bg-gov-azulTenue text-gov-azul',
  CREAR_HOGAR: 'bg-gov-naranjaTenue text-gov-naranja',
  AGREGAR_MIEMBRO: 'bg-gov-naranjaTenue text-gov-naranja',
  RESPONDER_PREGUNTA: 'bg-gov-azulTenue text-gov-azul',
  FINALIZAR_ENCUESTA: 'bg-gov-verdeTenue text-gov-verde',
  EXPORTAR: 'bg-blue-50 text-blue-700',
  CAMBIO_PASSWORD: 'bg-yellow-50 text-yellow-700',
  CAMBIO_USUARIO: 'bg-yellow-50 text-yellow-700',
  ACCESO_DENEGADO: 'bg-gov-rojoTenue text-gov-rojo',
  LLAMADA_GEMINI: 'bg-purple-50 text-purple-700',
  CONSENTIMIENTO_IA: 'bg-purple-50 text-purple-700',
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
  const [filtroResultado, setFiltroResultado] = useState('');
  const [filtroDesde, setFiltroDesde] = useState('');
  const [filtroHasta, setFiltroHasta] = useState('');

  const hayFiltros = filtroAccion || filtroResultado || filtroDesde || filtroHasta;

  function cargar(pag: number) {
    setCargando(true);
    setError('');
    auditoriaApi.logs({
      page: pag,
      page_size: PAGE_SIZE,
      ordering: '-timestamp',
      ...(filtroAccion && { accion: filtroAccion }),
      ...(filtroResultado && { resultado: filtroResultado }),
      ...(filtroDesde && { fecha_desde: filtroDesde }),
      ...(filtroHasta && { fecha_hasta: filtroHasta }),
    })
      .then(({ data }) => {
        setLogs(data.results);
        setTotal(data.count);
      })
      .catch(() => setError('No se pudieron cargar los registros de auditoría.'))
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
    setFiltroResultado('');
    setFiltroDesde('');
    setFiltroHasta('');
    setPagina(1);
    setCargando(true);
    setError('');
    auditoriaApi.logs({ page: 1, page_size: PAGE_SIZE, ordering: '-timestamp' })
      .then(({ data }) => {
        setLogs(data.results);
        setTotal(data.count);
      })
      .catch(() => setError('No se pudieron cargar los registros de auditoría.'))
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
      className: 'w-44',
      render: (log) => (
        <span className={`inline-block text-xs font-medium px-2 py-0.5 rounded-md ${ACCION_BADGE[log.accion] ?? 'bg-gray-100 text-gray-600'}`}>
          {log.accion_display}
        </span>
      ),
    },
    {
      key: 'recurso',
      header: 'Recurso',
      className: 'hidden md:table-cell',
      render: (log) => (
        <span className="text-sm text-gray-700">{log.recurso || '—'}</span>
      ),
    },
    {
      key: 'resultado',
      header: 'Resultado',
      className: 'w-24',
      render: (log) => (
        <span className={`text-xs font-semibold ${RESULTADO_BADGE[log.resultado] ?? 'text-gray-500'}`}>
          {log.resultado_display}
        </span>
      ),
    },
    {
      key: 'ip_origen',
      header: 'IP',
      className: 'hidden lg:table-cell w-32',
      render: (log) => (
        <span className="text-xs font-mono text-gray-500">{log.ip_origen}</span>
      ),
    },
    {
      key: 'detalle',
      header: 'Detalle',
      className: 'hidden lg:table-cell',
      render: (log) => (
        <span className="text-xs text-gray-400 line-clamp-2">
          {log.detalle ? Object.entries(log.detalle).map(([k, v]) => `${k}: ${v}`).join(', ') : '—'}
        </span>
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
      <div className="card mb-6 shadow-soft animate-fade-in-up">
        <div className="flex flex-col lg:flex-row gap-3">
          {/* Filtros — en mobile grid 1col, tablet 2col, desktop se expanden */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 flex-1">
            <div>
              <label className="block text-xs font-semibold text-gray-600 uppercase tracking-wide mb-1">
                Acción
              </label>
              <select
                value={filtroAccion}
                onChange={(e) => setFiltroAccion(e.target.value)}
                className="input"
              >
                <option value="">Todas</option>
                {ACCIONES_AUDITORIA.map((a) => (
                  <option key={a} value={a}>{a.replace(/_/g, ' ')}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-600 uppercase tracking-wide mb-1">
                Resultado
              </label>
              <select
                value={filtroResultado}
                onChange={(e) => setFiltroResultado(e.target.value)}
                className="input"
              >
                <option value="">Todos</option>
                <option value="EXITO">Éxito</option>
                <option value="ERROR">Error</option>
                <option value="DENEGADO">Denegado</option>
              </select>
            </div>

            <div>
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

            <div>
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
          </div>

          {/* Botones — en desktop al lado, en mobile/tablet fila completa */}
          <div className="flex items-end gap-2">
            <Button onClick={aplicarFiltros} className="h-[38px] flex-1 lg:flex-none">Filtrar</Button>
            {hayFiltros && (
              <Button variant="danger" icon={Trash2} onClick={limpiarFiltros} className="h-[38px] flex-1 lg:flex-none">
                Limpiar
              </Button>
            )}
          </div>
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
        emptyDescripcion={hayFiltros ? 'No hay registros que coincidan con los filtros aplicados.' : 'No se encontraron registros de auditoría.'}
        pagina={pagina}
        totalPaginas={totalPaginas}
        onPaginaChange={setPagina}
      />
    </div>
  );
}
