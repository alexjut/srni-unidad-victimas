/**
 * Reportes del encuestador — resumen + listado paginado + export CSV
 */
import { useEffect, useState } from 'react';
import { Download, ChevronLeft, ChevronRight } from 'lucide-react';
import { reportesApi, type ResumenEncuestador, type DetalleSesion } from '@/api/reportes';

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

      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="font-display text-2xl font-bold text-gray-800">Mis reportes</h2>
          <p className="text-gray-500 text-sm mt-0.5">Producción y estadísticas personales</p>
        </div>
        <button
          onClick={exportarCsv}
          disabled={descargando}
          className="btn-primary flex items-center gap-2 text-sm"
        >
          <Download size={16} />
          {descargando ? 'Descargando…' : 'Exportar CSV'}
        </button>
      </div>

      {error && (
        <div className="bg-gov-rojoTenue border border-red-200 text-gov-rojo rounded-lg p-4 mb-4 text-sm">
          {error}
        </div>
      )}

      {/* Resumen */}
      {resumen && (
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
          {[
            { label: 'Sesiones totales',      valor: resumen.sesiones_total },
            { label: 'Finalizadas',           valor: resumen.sesiones_finalizadas },
            { label: 'En proceso',            valor: resumen.sesiones_en_proceso },
            { label: 'Hogares',               valor: resumen.hogares_total },
            { label: 'Víctimas caracterizadas', valor: resumen.victimas_caracterizadas },
          ].map((m) => (
            <div key={m.label} className="card text-center">
              <p className="text-3xl font-display font-bold text-gov-azul">{m.valor}</p>
              <p className="text-xs text-gray-500 mt-1">{m.label}</p>
            </div>
          ))}
        </div>
      )}

      {/* Tabla detalle */}
      <div className="card overflow-hidden p-0">
        <div className="px-4 py-3 border-b border-gov-borde">
          <p className="font-semibold text-gray-700 text-sm">Detalle de sesiones</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gov-borde">
              <tr>
                {['Hogar','Instrumento','Ruta','Estado','Progreso','Fecha inicio'].map((h) => (
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
                          <div className="h-4 bg-gray-100 rounded animate-pulse" />
                        </td>
                      ))}
                    </tr>
                  ))
                : detalle.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-4 py-8 text-center text-gray-400 text-sm">
                        No hay sesiones registradas aún.
                      </td>
                    </tr>
                  ) : detalle.map((d) => (
                    <tr key={d.sesion_id} className="hover:bg-gov-azulTenue/30">
                      <td className="px-4 py-3 font-mono text-gov-azul">{d.hogar_codigo}</td>
                      <td className="px-4 py-3 text-gray-700 max-w-[130px] truncate">{d.instrumento}</td>
                      <td className="px-4 py-3 text-gray-500 text-xs">{d.ruta_entrevista}</td>
                      <td className="px-4 py-3">
                        <span className={d.estado === 'FINALIZADA' ? 'badge-verde' : d.estado === 'EN_PROCESO' ? 'badge-azul' : 'badge-rojo'}>
                          {d.estado}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-700">{d.porcentaje_completado}%</td>
                      <td className="px-4 py-3 text-gray-500 text-xs">
                        {new Date(d.fecha_inicio).toLocaleDateString('es-CO')}
                      </td>
                    </tr>
                  ))}
            </tbody>
          </table>
        </div>

        {totalPags > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-gov-borde">
            <p className="text-xs text-gray-500">Página {pagina} de {totalPags}</p>
            <div className="flex gap-2">
              <button onClick={() => setPagina(p => Math.max(1, p - 1))} disabled={pagina === 1}
                className="btn-secondary flex items-center gap-1 text-xs py-1 px-2">
                <ChevronLeft size={14} /> Anterior
              </button>
              <button onClick={() => setPagina(p => Math.min(totalPags, p + 1))} disabled={pagina === totalPags}
                className="btn-secondary flex items-center gap-1 text-xs py-1 px-2">
                Siguiente <ChevronRight size={14} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
