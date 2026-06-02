import { type LucideIcon } from 'lucide-react';

interface EmptyStateProps {
  icon: LucideIcon;
  titulo: string;
  descripcion?: string;
}

export default function EmptyState({ icon: Icon, titulo, descripcion }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 animate-fade-in">
      <div className="w-16 h-16 rounded-2xl bg-gray-100 flex items-center justify-center mb-4">
        <Icon size={28} className="text-gray-400" />
      </div>
      <p className="text-sm font-semibold text-gray-500">{titulo}</p>
      {descripcion && (
        <p className="text-xs text-gray-400 mt-1.5 max-w-xs text-center leading-relaxed">{descripcion}</p>
      )}
    </div>
  );
}
