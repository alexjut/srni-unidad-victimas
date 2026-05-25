/**
 * Lista de hogares — tabla paginada con filtros
 */
import { useEffect, useState } from 'react';
import { Search, ChevronLeft, ChevronRight } from 'lucide-react';
import { hogaresApi, type HogarResumen } from '@/api/hogares';

const ESTADO_BADGE: Record<string, string> = {
  ACTIVO:    'badge-verde',
  INACTIVO:  'badge-gris',
  ARCHIVADO: 'badge-rojo',
};

export default function HogaresPage() {
  const [hogares,  setHogares]  = useState<HogarResumen[]>([]);
  const [total,    setTotal]    = useState(0);
  const [pagina,   setPagina]   = useState(1);
  const [cargando, setCargando] = useState(true);
  const [error,    setError]    = useState('');

  const porPagina = 20;
  const totalPags = Math.ceil(total / porPagina);

  async function cargar(pag: number) {
    setCargando(true);
    setError('');
    try {
      const { data } = await hogaresApi.listar({ page: pag });
      setHogares(data.results);
      setTotal(data.count);
    } catch {
      setError('No se pudieron cargar los hogares.');
    } finally {
      setCargando(false);
    }
  }

  useEffect(() => { cargar(pagina); }, [pagina]);

  return (
    <div className="p-6 max-w-6xl mx-auto">

      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="font-display text-2xl font-bold text-gray-800">Hogares</h2>
          <p className="text-gray-500 text-sm mt-0.5">{total} registro(s) en total</p>
        </div>
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
                {['Código','Autorizado','Municipio','Personas','Estado','Fecha'].map((h) => (
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
                      {Array.from({ length: 6 }).map((_, j) => (
                        <td key={j} className="px-4 py-3">
                          <div className="h-4 bg-gray-100 rounded animate-pulse" />
                        </td>
                      ))}
                    </tr>
                  ))
                : hogares.map((h) => (
                    <tr key={h.id} className="hover:bg-gov-azulTenue/30 transition-colors">
                      <td className="px-4 py-3 font-mono text-gov-azul font-medium">{h.codigo}</td>
                      <td className="px-4 py-3 text-gray-800">{h.autorizado_nombre}</td>
                      <td className="px-4 py-3 text-gray-600">{h.municipio_nombre ?? '—'}</td>
                      <td className="px-4 py-3 text-center text-gray-700">{h.numero_personas}</td>
                      <td className="px-4 py-3">
                        <span className={ESTADO_BADGE[h.estado] ?? 'badge-gris'}>
                          {h.estado}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-500">
                        {new Date(h.created_at).toLocaleDateString('es-CO')}
                      </td>
                    </tr>
                  ))}
            </tbody>
          </table>
        </div>

        {/* Paginación */}
        {totalPags > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-gov-borde">
            <p className="text-xs text-gray-500">
              Página {pagina} de {totalPags}
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => setPagina((p) => Math.max(1, p - 1))}
                disabled={pagina === 1}
                className="btn-secondary flex items-center gap-1 text-xs py-1 px-2"
              >
                <ChevronLeft size={14} /> Anterior
              </button>
              <button
                onClick={() => setPagina((p) => Math.min(totalPags, p + 1))}
                disabled={pagina === totalPags}
                className="btn-secondary flex items-center gap-1 text-xs py-1 px-2"
              >
                Siguiente <ChevronRight size={14} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
