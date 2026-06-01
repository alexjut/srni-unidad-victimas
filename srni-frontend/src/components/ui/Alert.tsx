import { AlertCircle, CheckCircle, Info, AlertTriangle } from 'lucide-react';

type AlertVariant = 'error' | 'exito' | 'info' | 'warning';

interface AlertProps {
  variant: AlertVariant;
  children: React.ReactNode;
  className?: string;
}

const config: Record<AlertVariant, { bg: string; border: string; text: string; icon: typeof AlertCircle }> = {
  error:   { bg: 'bg-gov-rojoTenue',    border: 'border-red-200',    text: 'text-gov-rojo',    icon: AlertCircle },
  exito:   { bg: 'bg-gov-verdeTenue',   border: 'border-green-200',  text: 'text-gov-verde',   icon: CheckCircle },
  info:    { bg: 'bg-gov-azulTenue',    border: 'border-blue-200',   text: 'text-gov-azul',    icon: Info },
  warning: { bg: 'bg-gov-naranjaTenue', border: 'border-orange-200', text: 'text-gov-naranja', icon: AlertTriangle },
};

export default function Alert({ variant, children, className = '' }: AlertProps) {
  const { bg, border, text, icon: Icon } = config[variant];

  return (
    <div className={`${bg} border ${border} ${text} rounded-lg p-4 text-sm flex items-start gap-3 ${className}`}>
      <Icon size={18} className="shrink-0 mt-0.5" />
      <div>{children}</div>
    </div>
  );
}
