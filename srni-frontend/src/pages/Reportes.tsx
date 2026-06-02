/**
 * Reportes del encuestador — resumen + listado paginado + export CSV
 */
import { useEffect, useState } from 'react';
import { Download, ClipboardList } from 'lucide-react';
import { reportesApi, type ResumenEncuestador, type DetalleSesion } from '@/api/reportes';
import Badge, { type BadgeVariant } from '@/components/ui/Badge';
import EmptyState from '@/components/ui/EmptyState';
import Pagination from '@/components/ui/Pagination';
import PageHeader from '@/components/ui/PageHeader';
import Button from '@/components/ui/Button';
import Alert from '@/components/ui/Alert';

const ESTADO_BADGE: Record<string, BadgeVariant> = {
  COMPLETADA:  'verde',
  FINALIZADA:  'verde',
  EN_PROGRESO: 'azul',
  INICIADA:    'naranja',
  SUSPENDIDA:  'rojo',
  CANCELADA:   'rojo',
};

export default function ReportesPage() {
  const [resumen,  setResumen]  = useState<ResumenEncuestador | null>(null);
  const [detalle,  setDetalle]  = useState<DetalleSesion[]>([]);
  const [total,    setTotal]    = useState(0);
  const [pagina,   setPagina]   = useState(1);
  const [cargando, setCargando] = useState(true);
  const [descargando, setDescargando] = useState(false);
  const [error,    setError]    = useState('');

  const totalPags = Math.ceil(total / 20);

  async function cargar(pag: number) {
    setCargando(true);
    try {
      const [resRes, detRes] = await Promise.all([
        reportesApi.resumen(),
        reportesApi.detalle({ page: pag }),
      ]);
      setResumen(resRes.data);
      setDetalle(detRes.data.results);
      setTotal(detRes.data.count);
    } catch {
      setError('No se pudo cargar el reporte.');
    } finally {
      setCargando(false);
    }
  }

  async function exportarCsv() {
    setDescargando(true);
    try {
      const { data } = await reportesApi.exportarCsv();
      const url = URL.createObjectURL(new Blob([data as BlobPart]));
      const a = document.createElement('a');
      a.href = url;
      a.download = `reporte-srni-${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setError('No se pudo descargar el CSV.');
    } finally {
      setDescargando(false);
    }
  }

  useEffect(() => { cargar(pagina); }, [pagina]);

  return (
    <div className="p-6 max-w-5xl mx-auto">

      <PageHeader
        titulo="Mis reportes"
        subtitulo="Producción y estadísticas personales"
        acciones={
          <Button icon={Download} loading={descargando} onClick={exportarCsv} size="sm">
            {descargando ? 'Descargando…' : 'Exportar CSV'}
          </Button>
        }
      />

      {error && <Alert variant="error" className="mb-4">{error}</Alert>}

      {/* Resumen */}
      {resumen && (
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-4 mb-6 animate-fade-in-up">
          {[
            { label: 'Sesiones totales',    valor: resumen.sesiones_total },
            { label: 'Completadas',         valor: resumen.sesiones_completadas },
            { label: 'En progreso',         valor: resumen.sesiones_en_progreso },
            { label: 'Suspendidas',         valor: resumen.sesiones_suspendidas },
            { label: 'Hogares caracterizados', valor: resumen.hogares_caracterizados },
            { label: 'Respuestas totales',  valor: resumen.respuestas_total },
          ].map((m) => (
            <div key={m.label} className="card text-center">
              <p className="text-3xl font-display font-bold text-gov-azul">{m.valor}</p>
              <p className="text-xs text-gray-500 mt-1">{m.label}</p>
            </div>
          ))}
        </div>
      )}

      {/* Tabla detalle */}
      <div className="card overflow-hidden p-0 animate-fade-in-up" style={{ animationDelay: '50ms', animationFillMode: 'both' }}>
        <div className="px-4 py-3 border-b border-gov-borde">
          <p className="font-semibold text-gray-700 text-sm">Detalle de sesiones</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gov-borde">
              <tr>
                {['Hogar','Instrumento','Estado','Progreso','Respuestas','Fecha inicio'].map((h) => (
                  <th key={h} className="text-left px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase tracking-wide">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gov-borde">
              {cargando
                ? Array.from({ length: 6 }).map((_, i) => (
                    <tr key={i}>
                      {Array.from({ length: 6 }).map((_, j) => (
                        <td key={j} className="px-4 py-3">
                          <div className="h-4 bg-gray-200 rounded animate-pulse" />
                        </td>
                      ))}
                    </tr>
                  ))
                : detalle.length === 0 ? (
                    <tr>
                      <td colSpan={6}>
                        <EmptyState
                          icon={ClipboardList}
                          titulo="No hay sesiones registradas aún"
                          descripcion="Las sesiones aparecerán aquí cuando se inicien encuestas."
                        />
                      </td>
                    </tr>
                  ) : detalle.map((d) => (
                    <tr key={d.sesion_id} className="hover:bg-gov-azulTenue/30 transition-all">
                      <td className="px-4 py-3 font-mono text-gov-azul text-xs">{d.hogar_id.slice(0, 8)}</td>
                      <td className="px-4 py-3 text-gray-700 max-w-[160px] truncate">{d.instrumento_nombre}</td>
                      <td className="px-4 py-3">
                        <Badge variant={ESTADO_BADGE[d.estado] ?? 'gris'}>
                          {d.estado_display ?? d.estado.replace('_', ' ')}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-gray-700">{d.porcentaje_completado}%</td>
                      <td className="px-4 py-3 text-gray-500 text-xs">{d.respuestas_total}</td>
                      <td className="px-4 py-3 text-gray-500 text-xs">
                        {new Date(d.fecha_inicio).toLocaleDateString('es-CO')}
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
