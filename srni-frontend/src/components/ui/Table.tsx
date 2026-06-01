import { type LucideIcon } from 'lucide-react';
import EmptyState from './EmptyState';
import Pagination from './Pagination';

export interface Column<T> {
  key: string;
  header: string;
  render: (item: T) => React.ReactNode;
  className?: string;
}

interface TableProps<T> {
  columns: Column<T>[];
  data: T[];
  keyExtractor: (item: T) => string;
  cargando?: boolean;
  onRowClick?: (item: T) => void;
  // Empty state
  emptyIcon?: LucideIcon;
  emptyTitulo?: string;
  emptyDescripcion?: string;
  // Pagination
  pagina?: number;
  totalPaginas?: number;
  onPaginaChange?: (pagina: number) => void;
  // Skeleton
  skeletonRows?: number;
}

export default function Table<T>({
  columns,
  data,
  keyExtractor,
  cargando = false,
  onRowClick,
  emptyIcon,
  emptyTitulo = 'Sin datos',
  emptyDescripcion,
  pagina,
  totalPaginas,
  onPaginaChange,
  skeletonRows = 8,
}: TableProps<T>) {
  return (
    <div className="card overflow-hidden p-0">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gov-borde">
            <tr>
              {columns.map((col) => (
                <th
                  key={col.key}
                  className={`text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide ${col.className ?? ''}`}
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gov-borde">
            {cargando
              ? Array.from({ length: skeletonRows }).map((_, i) => (
                  <tr key={i}>
                    {columns.map((col) => (
                      <td key={col.key} className="px-4 py-3">
                        <div className="h-4 bg-gray-100 rounded animate-pulse" />
                      </td>
                    ))}
                  </tr>
                ))
              : data.length === 0
                ? (
                    <tr>
                      <td colSpan={columns.length}>
                        {emptyIcon ? (
                          <EmptyState
                            icon={emptyIcon}
                            titulo={emptyTitulo}
                            descripcion={emptyDescripcion}
                          />
                        ) : (
                          <div className="py-12 text-center text-sm text-gray-400">
                            {emptyTitulo}
                          </div>
                        )}
                      </td>
                    </tr>
                  )
                : data.map((item) => (
                    <tr
                      key={keyExtractor(item)}
                      onClick={onRowClick ? () => onRowClick(item) : undefined}
                      className={
                        onRowClick
                          ? 'hover:bg-gov-azulTenue/30 transition-colors cursor-pointer'
                          : ''
                      }
                    >
                      {columns.map((col) => (
                        <td key={col.key} className={`px-4 py-3 ${col.className ?? ''}`}>
                          {col.render(item)}
                        </td>
                      ))}
                    </tr>
                  ))}
          </tbody>
        </table>
      </div>

      {pagina != null && totalPaginas != null && onPaginaChange && (
        <Pagination
          pagina={pagina}
          totalPaginas={totalPaginas}
          onChange={onPaginaChange}
        />
      )}
    </div>
  );
}
