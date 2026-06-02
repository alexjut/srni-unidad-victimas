import { useEffect, useRef } from 'react';
import { X } from 'lucide-react';

interface ModalProps {
  abierto: boolean;
  onCerrar: () => void;
  titulo: string;
  children: React.ReactNode;
  acciones?: React.ReactNode;
}

export default function Modal({ abierto, onCerrar, titulo, children, acciones }: ModalProps) {
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!abierto) return;

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') onCerrar();
    }

    document.addEventListener('keydown', handleKeyDown);
    document.body.style.overflow = 'hidden';

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [abierto, onCerrar]);

  // Focus trap: focus the dialog when opened
  useEffect(() => {
    if (abierto && dialogRef.current) {
      dialogRef.current.focus();
    }
  }, [abierto]);

  if (!abierto) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Overlay con blur */}
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm animate-fade-in"
        onClick={onCerrar}
        aria-hidden="true"
      />

      {/* Dialog */}
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label={titulo}
        tabIndex={-1}
        className="relative bg-white rounded-2xl shadow-soft-xl w-full max-w-lg max-h-[90vh] flex flex-col outline-none animate-scale-in"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gov-borde/60">
          <h3 className="font-display text-lg font-bold text-gray-800">{titulo}</h3>
          <button
            onClick={onCerrar}
            className="w-8 h-8 rounded-full flex items-center justify-center text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-all"
            aria-label="Cerrar"
          >
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-5 overflow-y-auto flex-1">
          {children}
        </div>

        {/* Footer / Acciones */}
        {acciones && (
          <div className="flex items-center justify-end gap-2 px-6 py-4 border-t border-gov-borde/60">
            {acciones}
          </div>
        )}
      </div>
    </div>
  );
}
