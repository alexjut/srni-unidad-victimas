import { AlertCircle, CheckCircle, Info, AlertTriangle } from 'lucide-react';

type AlertVariant = 'error' | 'exito' | 'info' | 'warning';

interface AlertProps {
  variant: AlertVariant;
  children: React.ReactNode;
  className?: string;
}

const config: Record<AlertVariant, { bg: string; border: string; text: string; accent: string; icon: typeof AlertCircle }> = {
  error:   { bg: 'bg-gov-rojoTenue',    border: 'border-red-200/60',    text: 'text-gov-rojo',    accent: 'bg-gov-rojo',    icon: AlertCircle },
  exito:   { bg: 'bg-gov-verdeTenue',   border: 'border-green-200/60',  text: 'text-gov-verde',   accent: 'bg-gov-verde',   icon: CheckCircle },
  info:    { bg: 'bg-gov-azulTenue',    border: 'border-blue-200/60',   text: 'text-gov-azul',    accent: 'bg-gov-azul',    icon: Info },
  warning: { bg: 'bg-gov-amarilloTenue', border: 'border-yellow-200/60', text: 'text-yellow-700',  accent: 'bg-gov-amarillo', icon: AlertTriangle },
};

export default function Alert({ variant, children, className = '' }: AlertProps) {
  const { bg, border, text, accent, icon: Icon } = config[variant];

  return (
    <div className={`${bg} border ${border} ${text} rounded-xl p-4 text-sm flex items-start gap-3 relative overflow-hidden animate-fade-in ${className}`}>
      <div className={`absolute left-0 top-0 bottom-0 w-1 ${accent} rounded-l-xl`} />
      <Icon size={18} className="shrink-0 mt-0.5 ml-1" />
      <div>{children}</div>
    </div>
  );
}
