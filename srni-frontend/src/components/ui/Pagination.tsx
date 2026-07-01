import { ChevronLeft, ChevronRight } from 'lucide-react';

interface PaginationProps {
  pagina: number;
  totalPaginas: number;
  onChange: (pagina: number) => void;
}

export default function Pagination({ pagina, totalPaginas, onChange }: PaginationProps) {
  if (totalPaginas <= 1) return null;

  return (
    <div className="flex items-center justify-between px-4 py-3 border-t border-gov-borde/60">
      <div className="flex items-center gap-1.5">
        <div className="w-1.5 h-1.5 rounded-full bg-gov-amarillo shrink-0" />
        <p className="text-xs text-gray-500">
          Página <span className="font-semibold text-gray-700">{pagina}</span> de {totalPaginas}
        </p>
      </div>
      <div className="flex gap-1.5">
        <button
          onClick={() => onChange(Math.max(1, pagina - 1))}
          disabled={pagina === 1}
          className="flex items-center gap-1 text-xs font-medium text-gray-600 hover:text-gov-azul hover:bg-gov-azulTenue px-2.5 py-1.5 rounded-lg transition-all disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-transparent disabled:hover:text-gray-600"
        >
          <ChevronLeft size={14} /> Anterior
        </button>
        <button
          onClick={() => onChange(Math.min(totalPaginas, pagina + 1))}
          disabled={pagina === totalPaginas}
          className="flex items-center gap-1 text-xs font-medium text-gray-600 hover:text-gov-azul hover:bg-gov-azulTenue px-2.5 py-1.5 rounded-lg transition-all disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-transparent disabled:hover:text-gray-600"
        >
          Siguiente <ChevronRight size={14} />
        </button>
      </div>
    </div>
  );
}
