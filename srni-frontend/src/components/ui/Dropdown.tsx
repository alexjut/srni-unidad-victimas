/**
 * Dropdown — selector personalizado con diseño Apple-style GOV.CO
 * Para filtros y selects de UI (no para react-hook-form, usar Select para formularios)
 */
import { useState, useRef, useEffect } from 'react';
import { ChevronDown, Check } from 'lucide-react';

export interface DropdownOption {
  value: string;
  label: string;
}

interface DropdownProps {
  value: string;
  onChange: (value: string) => void;
  options: DropdownOption[];
  label?: string;
  disabled?: boolean;
  className?: string;
}

export default function Dropdown({
  value,
  onChange,
  options,
  label,
  disabled = false,
  className = '',
}: DropdownProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const selected = options.find((o) => o.value === value) ?? options[0];

  // Cerrar al hacer clic fuera
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Cerrar con Escape
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false);
    }
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  function handleSelect(val: string) {
    onChange(val);
    setOpen(false);
  }

  return (
    <div ref={ref} className={`relative ${className}`}>
      {label && (
        <label className="block text-xs font-semibold text-gray-600 uppercase tracking-wide mb-1">
          {label}
        </label>
      )}

      {/* Mobile: select nativo */}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className="sm:hidden input"
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>

      {/* Desktop: dropdown personalizado */}
      <button
        type="button"
        onClick={() => !disabled && setOpen(!open)}
        disabled={disabled}
        className={`
          hidden sm:flex w-full items-center justify-between gap-2
          px-3 py-2 text-sm rounded-lg border transition-all
          bg-white text-left
          ${open
            ? 'border-gov-azul ring-2 ring-gov-azul/20'
            : 'border-gov-borde/60 hover:border-gray-400'
          }
          ${disabled ? 'opacity-50 cursor-not-allowed bg-gray-50' : 'cursor-pointer'}
        `}
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <span className={`truncate ${selected?.value ? 'text-gray-800' : 'text-gray-400'}`}>
          {selected?.label ?? '—'}
        </span>
        <ChevronDown
          size={15}
          className={`shrink-0 text-gray-400 transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
        />
      </button>

      {/* Panel */}
      {open && (
        <div
          role="listbox"
          className="absolute z-50 mt-1.5 min-w-full w-max bg-white border border-gov-borde/60 rounded-xl shadow-soft-md overflow-hidden animate-slide-down"
        >
          <ul className="py-1 max-h-60 overflow-y-auto">
            {options.map((opt) => {
              const isSelected = opt.value === value;
              return (
                <li
                  key={opt.value}
                  role="option"
                  aria-selected={isSelected}
                  onClick={() => handleSelect(opt.value)}
                  className={`
                    flex items-center justify-between gap-2 px-3 py-2 text-sm cursor-pointer transition-all
                    ${isSelected
                      ? 'bg-gov-azulTenue text-gov-azul font-medium'
                      : 'text-gray-700 hover:bg-gov-azulTenue/40'
                    }
                  `}
                >
                  <span className="whitespace-nowrap">{opt.label}</span>
                  {isSelected && <Check size={14} className="shrink-0 text-gov-azul" />}
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}
