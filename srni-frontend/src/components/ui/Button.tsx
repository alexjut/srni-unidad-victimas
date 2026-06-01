import { type LucideIcon } from 'lucide-react';
import Spinner from './Spinner';

type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost';
type ButtonSize = 'sm' | 'md' | 'lg';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  icon?: LucideIcon;
}

const variantStyles: Record<ButtonVariant, string> = {
  primary:   'bg-gov-azul hover:bg-gov-azulOscuro text-white',
  secondary: 'border border-gov-azul text-gov-azul hover:bg-gov-azulTenue',
  danger:    'bg-gov-rojo hover:bg-red-900 text-white',
  ghost:     'text-gray-600 hover:bg-gray-100',
};

const sizeStyles: Record<ButtonSize, string> = {
  sm: 'text-xs px-3 py-1.5 gap-1.5',
  md: 'text-sm px-4 py-2 gap-2',
  lg: 'text-base px-5 py-2.5 gap-2',
};

const iconSizes: Record<ButtonSize, number> = {
  sm: 14,
  md: 16,
  lg: 18,
};

export default function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  icon: Icon,
  children,
  disabled,
  className = '',
  ...rest
}: ButtonProps) {
  return (
    <button
      className={`inline-flex items-center justify-center font-semibold rounded-md transition-colors duration-150 disabled:opacity-50 disabled:cursor-not-allowed ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
      disabled={disabled || loading}
      {...rest}
    >
      {loading ? (
        <Spinner size="sm" />
      ) : Icon ? (
        <Icon size={iconSizes[size]} />
      ) : null}
      {children}
    </button>
  );
}
