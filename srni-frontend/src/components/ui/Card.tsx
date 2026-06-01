import { type LucideIcon } from 'lucide-react';

interface CardProps {
  icon: LucideIcon;
  label: string;
  valor: number | string;
  color: string;
}

export default function Card({ icon: Icon, label, valor, color }: CardProps) {
  return (
    <div className="card flex items-center gap-4">
      <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${color}`}>
        <Icon size={22} className="text-white" />
      </div>
      <div>
        <p className="text-2xl font-display font-bold text-gray-800">{valor}</p>
        <p className="text-sm text-gray-500">{label}</p>
      </div>
    </div>
  );
}
