import { ChevronLeft, ChevronRight } from 'lucide-react';

interface PaginationProps {
  pagina: number;
  totalPaginas: number;
  onChange: (pagina: number) => void;
}

export default function Pagination({ pagina, totalPaginas, onChange }: PaginationProps) {
  if (totalPaginas <= 1) return null;

  return (
    <div className="flex items-center justify-between px-4 py-3 border-t border-gov-borde">
      <p className="text-xs text-gray-500">
        Página {pagina} de {totalPaginas}
      </p>
      <div className="flex gap-2">
        <button
          onClick={() => onChange(Math.max(1, pagina - 1))}
          disabled={pagina === 1}
          className="btn-secondary flex items-center gap-1 text-xs py-1 px-2"
        >
          <ChevronLeft size={14} /> Anterior
        </button>
        <button
          onClick={() => onChange(Math.min(totalPaginas, pagina + 1))}
          disabled={pagina === totalPaginas}
          className="btn-secondary flex items-center gap-1 text-xs py-1 px-2"
        >
          Siguiente <ChevronRight size={14} />
        </button>
      </div>
    </div>
  );
}
