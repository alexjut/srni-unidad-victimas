import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard, Home, ClipboardList, BarChart3,
  LogOut, ChevronRight,
} from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';

export const NAV_ITEMS = [
  { to: '/dashboard',  icon: LayoutDashboard, label: 'Inicio'    },
  { to: '/hogares',    icon: Home,             label: 'Hogares'   },
  { to: '/encuestas',  icon: ClipboardList,    label: 'Encuestas' },
  { to: '/reportes',   icon: BarChart3,        label: 'Reportes'  },
];

interface SidebarProps {
  onNavigate?: () => void;
  onLogout: () => void;
}

export default function Sidebar({ onNavigate, onLogout }: SidebarProps) {
  const { usuario } = useAuthStore();

  return (
    <>
      {/* Logo + franja amarilla GOV.CO */}
      <div className="border-b-4 border-gov-amarillo px-5 py-4">
        <p className="text-xs font-semibold text-gov-amarillo tracking-widest uppercase mb-0.5">
          GOV.CO
        </p>
        <h1 className="font-display text-base font-bold leading-tight">
          Unidad para las Víctimas
        </h1>
        <p className="text-xs text-blue-200 mt-0.5">SRNI · Panel Web</p>
      </div>

      {/* Navegación */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            onClick={onNavigate}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors duration-150 ${
                isActive
                  ? 'bg-gov-azul text-white shadow-sm'
                  : 'text-blue-200 hover:bg-white/10 hover:text-white'
              }`
            }
          >
            <Icon size={18} />
            {label}
            <ChevronRight size={14} className="ml-auto opacity-40" />
          </NavLink>
        ))}
      </nav>

      {/* Usuario + cerrar sesión */}
      <div className="border-t border-white/10 px-4 py-4">
        {usuario && (
          <div className="mb-3">
            <p className="text-xs text-blue-300">Encuestador</p>
            <p className="text-sm font-semibold truncate">{usuario.nombre_completo}</p>
            {usuario.perfil && (
              <p className="text-xs text-blue-300">{usuario.perfil.nombre}</p>
            )}
          </div>
        )}
        <button
          onClick={onLogout}
          className="flex items-center gap-2 text-sm text-blue-200 hover:text-white transition-colors w-full"
        >
          <LogOut size={16} />
          Cerrar sesión
        </button>
      </div>
    </>
  );
}
