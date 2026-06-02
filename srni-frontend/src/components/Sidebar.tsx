import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard, Home, ClipboardList, BarChart3, Search, Eye,
  FileText, Database, Shield, ChevronRight,
} from 'lucide-react';

export const NAV_ITEMS = [
  { to: '/dashboard',   icon: LayoutDashboard, label: 'Inicio'       },
  { to: '/victimas',    icon: Search,           label: 'Víctimas'     },
  { to: '/hogares',     icon: Home,             label: 'Hogares'      },
  { to: '/encuestas',   icon: ClipboardList,    label: 'Encuestas'    },
  { to: '/reportes',    icon: BarChart3,        label: 'Reportes'     },
  { to: '/supervision',  icon: Eye,              label: 'Supervisión'  },
  { to: '/instrumentos', icon: FileText,         label: 'Instrumentos' },
  { to: '/parametricas', icon: Database,         label: 'Paramétricas' },
  { to: '/auditoria',   icon: Shield,           label: 'Auditoría'    },
];

interface SidebarProps {
  onNavigate?: () => void;
}

export default function Sidebar({ onNavigate }: SidebarProps) {
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
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto" aria-label="Menú principal">
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
    </>
  );
}
