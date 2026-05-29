export type BadgeVariant = 'verde' | 'azul' | 'rojo' | 'gris' | 'naranja';

interface BadgeProps {
  variant: BadgeVariant;
  children: React.ReactNode;
  className?: string;
}

const styles: Record<BadgeVariant, string> = {
  verde:   'bg-gov-verdeTenue text-gov-verde',
  azul:    'bg-gov-azulTenue text-gov-azul',
  rojo:    'bg-gov-rojoTenue text-gov-rojo',
  gris:    'bg-gray-100 text-gov-gris',
  naranja: 'bg-gov-naranjaTenue text-gov-naranja',
};

export default function Badge({ variant, children, className = '' }: BadgeProps) {
  return (
    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${styles[variant]} ${className}`}>
      {children}
    </span>
  );
}
