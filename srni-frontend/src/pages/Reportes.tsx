/**
 * Reportes del encuestador — resumen + listado paginado + export CSV
 */
import { useEffect, useState } from 'react';
import { FileSpreadsheet, ClipboardList } from 'lucide-react';
import { reportesApi, type ResumenEncuestador, type DetalleSesion } from '@/api/reportes';
import { formularioApi } from '@/api/formulario';
import Badge, { type BadgeVariant } from '@/components/ui/Badge';
import EmptyState from '@/components/ui/EmptyState';
import Pagination from '@/components/ui/Pagination';
import PageHeader from '@/components/ui/PageHeader';
import Button from '@/components/ui/Button';
import Alert from '@/components/ui/Alert';
import Modal from '@/components/ui/Modal';

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

  const hoy        = new Date().toISOString().slice(0, 10);
  const hace3Meses = new Date(Date.now() - 90 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
  const [modalExportar,    setModalExportar]    = useState(false);
  const [filtroDesde,      setFiltroDesde]      = useState(hace3Meses);
  const [filtroHasta,      setFiltroHasta]      = useState(hoy);
  const [filtroEstado,     setFiltroEstado]     = useState('');
  const [filtroInstrumento, setFiltroInstrumento] = useState('');
  const [instrumentos,     setInstrumentos]     = useState<string[]>([]);

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

  async function fetchTodoDetalle(params?: { desde?: string; hasta?: string }): Promise<DetalleSesion[]> {
    const first = await reportesApi.detalle({ page: 1, ...params });
    const { results, pages } = first.data;
    if (pages <= 1) return results;
    const rest = await Promise.all(
      Array.from({ length: pages - 1 }, (_, i) =>
        reportesApi.detalle({ page: i + 2, ...params })
      )
    );
    return [...results, ...rest.flatMap(r => r.data.results)];
  }

  async function exportarExcel() {
    setModalExportar(false);
    setDescargando(true);
    setError('');
    try {
      const todasSesiones = await fetchTodoDetalle({
        desde: filtroDesde || undefined,
        hasta: filtroHasta || undefined,
      });

      const sesiones = todasSesiones
        .filter(s => !filtroEstado     || s.estado === filtroEstado)
        .filter(s => !filtroInstrumento || s.instrumento_nombre === filtroInstrumento);

      const { default: ExcelJS } = await import('exceljs');

      const wb = new ExcelJS.Workbook();
      wb.creator = 'SRNI — Unidad para las Víctimas';
      wb.created = new Date();

      const headerBorder = {
        top:    { style: 'thin' as const, color: { argb: 'FF1565C0' } },
        left:   { style: 'thin' as const, color: { argb: 'FF1565C0' } },
        bottom: { style: 'thin' as const, color: { argb: 'FF1565C0' } },
        right:  { style: 'thin' as const, color: { argb: 'FF1565C0' } },
      };
      const dataBorder = {
        top:    { style: 'thin' as const, color: { argb: 'FFE0E0E0' } },
        left:   { style: 'thin' as const, color: { argb: 'FFE0E0E0' } },
        bottom: { style: 'thin' as const, color: { argb: 'FFE0E0E0' } },
        right:  { style: 'thin' as const, color: { argb: 'FFE0E0E0' } },
      };

      // ── Hoja 1: Detalle de Sesiones ──────────────────────────────────
      const ws = wb.addWorksheet('Detalle de Sesiones');
      ws.columns = [
        { header: 'ID Hogar',         key: 'hogar_id',              width: 38 },
        { header: 'Instrumento',      key: 'instrumento_nombre',    width: 36 },
        { header: 'Perfil',           key: 'perfil_codigo',         width: 14 },
        { header: 'Estado',           key: 'estado_display',        width: 18 },
        { header: 'Progreso (%)',     key: 'porcentaje_completado', width: 14 },
        { header: 'Respuestas',       key: 'respuestas_total',      width: 13 },
        { header: 'Fecha inicio',     key: 'fecha_inicio',          width: 14 },
        { header: 'Fecha fin',        key: 'fecha_fin',             width: 14 },
        { header: 'Duración (min)',   key: 'duracion_minutos',      width: 15 },
      ];

      ws.getRow(1).eachCell((cell) => {
        cell.fill      = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF1565C0' } };
        cell.font      = { bold: true, color: { argb: 'FFFFFFFF' }, size: 11, name: 'Calibri' };
        cell.alignment = { vertical: 'middle', horizontal: 'center' };
        cell.border    = headerBorder;
      });
      ws.getRow(1).height = 30;

      sesiones.forEach((s, idx) => {
        const row = ws.addRow({
          hogar_id:              s.hogar_id,
          instrumento_nombre:    s.instrumento_nombre,
          perfil_codigo:         s.perfil_codigo,
          estado_display:        s.estado_display ?? s.estado.replace('_', ' '),
          porcentaje_completado: s.porcentaje_completado,
          respuestas_total:      s.respuestas_total,
          fecha_inicio:          new Date(s.fecha_inicio).toLocaleDateString('es-CO'),
          fecha_fin:             s.fecha_fin ? new Date(s.fecha_fin).toLocaleDateString('es-CO') : '—',
          duracion_minutos:      s.duracion_minutos ?? '—',
        });
        const bg = idx % 2 === 0 ? 'FFFFFFFF' : 'FFE3F2FD';
        row.height = 22;
        row.eachCell((cell) => {
          cell.fill      = { type: 'pattern', pattern: 'solid', fgColor: { argb: bg } };
          cell.border    = dataBorder;
          cell.alignment = { vertical: 'middle' };
          cell.font      = { name: 'Calibri', size: 10 };
        });
      });

      ws.views = [{ state: 'frozen', ySplit: 1 }];

      // ── Hoja 2: Resumen ───────────────────────────────────────────────
      if (resumen) {
        const wsR = wb.addWorksheet('Resumen');
        wsR.columns = [
          { header: 'Métrica', key: 'label', width: 30 },
          { header: 'Valor',   key: 'valor', width: 20 },
        ];
        wsR.getRow(1).eachCell((cell) => {
          cell.fill      = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF1565C0' } };
          cell.font      = { bold: true, color: { argb: 'FFFFFFFF' }, size: 11, name: 'Calibri' };
          cell.alignment = { vertical: 'middle', horizontal: 'center' };
          cell.border    = headerBorder;
        });
        wsR.getRow(1).height = 30;

        const metricas: [string, string | number][] = [
          ['Sesiones totales',        resumen.sesiones_total],
          ['Completadas',             resumen.sesiones_completadas],
          ['En progreso',             resumen.sesiones_en_progreso],
          ['Suspendidas',             resumen.sesiones_suspendidas],
          ['Hogares caracterizados',  resumen.hogares_caracterizados],
          ['Respuestas totales',      resumen.respuestas_total],
          ['Promedio completado (%)', resumen.promedio_completado],
          ['Período desde',           resumen.periodo_desde],
          ['Período hasta',           resumen.periodo_hasta],
        ];
        metricas.forEach(([label, valor], idx) => {
          const row = wsR.addRow({ label, valor });
          const bg = idx % 2 === 0 ? 'FFFFFFFF' : 'FFE3F2FD';
          row.height = 22;
          row.eachCell((cell) => {
            cell.fill      = { type: 'pattern', pattern: 'solid', fgColor: { argb: bg } };
            cell.border    = dataBorder;
            cell.alignment = { vertical: 'middle' };
            cell.font      = { name: 'Calibri', size: 10 };
          });
        });
        wsR.views = [{ state: 'frozen', ySplit: 1 }];
      }

      // ── Descarga ──────────────────────────────────────────────────────
      const buffer = await wb.xlsx.writeBuffer();
      const blob = new Blob([buffer], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `reporte-srni-${new Date().toISOString().slice(0, 10)}.xlsx`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (err) {
      console.error(err);
      setError('No se pudo generar el Excel.');
    } finally {
      setDescargando(false);
    }
  }

  useEffect(() => { cargar(pagina); }, [pagina]);

  useEffect(() => {
    formularioApi.instrumentos()
      .then(r => setInstrumentos(
        r.data.results.filter(i => i.activo).map(i => i.nombre).sort()
      ))
      .catch(() => {});
  }, []);

  return (
    <div className="p-6 max-w-5xl mx-auto">

      <PageHeader
        titulo="Mis reportes"
        subtitulo="Producción y estadísticas personales"
        acciones={
          <Button icon={FileSpreadsheet} loading={descargando} onClick={() => setModalExportar(true)}>
            {descargando ? 'Generando…' : 'Exportar Excel'}
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

      {/* Modal filtros de exportación */}
      <Modal
        abierto={modalExportar}
        onCerrar={() => setModalExportar(false)}
        titulo="Configurar exportación Excel"
        acciones={
          <>
            <Button variant="secondary" size="sm" onClick={() => setModalExportar(false)}>
              Cancelar
            </Button>
            <Button icon={FileSpreadsheet} size="sm" onClick={exportarExcel}>
              Descargar Excel
            </Button>
          </>
        }
      >
        <div className="space-y-6">

          {/* Período */}
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Período</p>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="filtro-desde" className="block text-xs text-gray-400 mb-1">Desde</label>
                <input
                  id="filtro-desde"
                  type="date"
                  value={filtroDesde}
                  max={filtroHasta || hoy}
                  onChange={e => setFiltroDesde(e.target.value)}
                  className="input w-full text-sm"
                />
              </div>
              <div>
                <label htmlFor="filtro-hasta" className="block text-xs text-gray-400 mb-1">Hasta</label>
                <input
                  id="filtro-hasta"
                  type="date"
                  value={filtroHasta}
                  min={filtroDesde}
                  max={hoy}
                  onChange={e => setFiltroHasta(e.target.value)}
                  className="input w-full text-sm"
                />
              </div>
            </div>
          </div>

          {/* Estado — pills */}
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Estado</p>
            <div className="flex flex-wrap gap-2">
              {[
                { value: '',            label: 'Todos' },
                { value: 'COMPLETADA',  label: 'Completada' },
                { value: 'EN_PROGRESO', label: 'En progreso' },
                { value: 'INICIADA',    label: 'Iniciada' },
                { value: 'SUSPENDIDA',  label: 'Suspendida' },
                { value: 'CANCELADA',   label: 'Cancelada' },
              ].map(opt => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setFiltroEstado(opt.value)}
                  className={`px-3 py-1.5 text-sm rounded-lg border transition-all ${
                    filtroEstado === opt.value
                      ? 'bg-gov-azul border-gov-azul text-white font-medium'
                      : 'bg-white border-gov-borde text-gray-600 hover:border-gov-azul hover:text-gov-azul'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Instrumento — pills */}
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Instrumento</p>
            <div className="flex flex-wrap gap-2">
              {[
                { value: '', label: 'Todos' },
                ...(instrumentos.length > 0
                  ? instrumentos
                  : [...new Set(detalle.map(d => d.instrumento_nombre))].sort()
                ).map(n => ({ value: n, label: n })),
              ].map(opt => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setFiltroInstrumento(opt.value)}
                  className={`px-3 py-1.5 text-sm rounded-lg border transition-all ${
                    filtroInstrumento === opt.value
                      ? 'bg-gov-azul border-gov-azul text-white font-medium'
                      : 'bg-white border-gov-borde text-gray-600 hover:border-gov-azul hover:text-gov-azul'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

        </div>
      </Modal>
    </div>
  );
}
