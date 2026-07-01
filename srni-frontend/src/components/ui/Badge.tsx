export type BadgeVariant = 'verde' | 'azul' | 'amarillo' | 'rojo' | 'gris' | 'naranja';

interface BadgeProps {
  variant: BadgeVariant;
  children: React.ReactNode;
  className?: string;
}

const styles: Record<BadgeVariant, string> = {
  verde:    'bg-gov-verdeTenue    text-gov-verde   border-green-200/60',
  azul:     'bg-gov-azulTenue    text-gov-azul    border-blue-200/60',
  amarillo: 'bg-gov-amarilloTenue text-yellow-700  border-yellow-200/60',
  rojo:     'bg-gov-rojoTenue    text-gov-rojo    border-red-200/60',
  gris:     'bg-gray-100         text-gov-gris    border-gray-200/60',
  naranja:  'bg-gov-naranjaTenue text-gov-naranja border-orange-200/60',
};

export default function Badge({ variant, children, className = '' }: BadgeProps) {
  return (
    <span className={`inline-flex items-center text-xs font-semibold px-2.5 py-0.5 rounded-full border ${styles[variant]} ${className}`}>
      {children}
    </span>
  );
}
