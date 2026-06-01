import { type LucideIcon } from 'lucide-react';

interface EmptyStateProps {
  icon: LucideIcon;
  titulo: string;
  descripcion?: string;
}

export default function EmptyState({ icon: Icon, titulo, descripcion }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4">
      <div className="w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center mb-4">
        <Icon size={24} className="text-gray-400" />
      </div>
      <p className="text-sm font-medium text-gray-500">{titulo}</p>
      {descripcion && (
        <p className="text-xs text-gray-400 mt-1 max-w-xs text-center">{descripcion}</p>
      )}
    </div>
  );
}
