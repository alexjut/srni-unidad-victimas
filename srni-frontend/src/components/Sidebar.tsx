import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard, Home, ClipboardList, BarChart3, Search, Eye,
  FileText, Database, Shield, ChevronRight,
} from 'lucide-react';

export const NAV_ITEMS = [
  { to: '/dashboard',    icon: LayoutDashboard, label: 'Inicio'        },
  { to: '/victimas',     icon: Search,          label: 'Víctimas'      },
  { to: '/hogares',      icon: Home,            label: 'Hogares'       },
  { to: '/encuestas',    icon: ClipboardList,   label: 'Encuestas'     },
  { to: '/reportes',     icon: BarChart3,       label: 'Reportes'      },
  { to: '/supervision',  icon: Eye,             label: 'Supervisión'   },
  { to: '/instrumentos', icon: FileText,        label: 'Instrumentos'  },
  { to: '/parametricas', icon: Database,        label: 'Paramétricas'  },
  { to: '/auditoria',    icon: Shield,          label: 'Auditoría'     },
];

interface SidebarProps {
  onNavigate?: () => void;
}

export default function Sidebar({ onNavigate }: SidebarProps) {
  return (
    <>
      {/* Logo + identidad GOV.CO */}
      <div className="px-5 py-5 border-b border-white/[0.08]">
        <div className="flex items-center gap-2 mb-2.5">
          <div className="w-1 h-4 rounded-full bg-gov-amarillo shrink-0" />
          <p className="text-[11px] font-semibold text-gov-amarillo tracking-widest uppercase">
            GOV.CO
          </p>
        </div>
        <h1 className="font-display text-[15px] font-bold leading-tight text-white">
          Unidad para las Víctimas
        </h1>
        <p className="text-[11px] text-white mt-1 tracking-wide">SRNI · Panel Web</p>
      </div>

      {/* Navegación */}
      <nav className="flex-1 px-3 py-3 space-y-0.5 overflow-y-auto" aria-label="Menú principal">
        {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            onClick={onNavigate}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 border ${
                isActive
                  ? 'bg-gov-azul/20 border-gov-azul/30 text-white'
                  : 'border-transparent text-white hover:bg-white/[0.07] hover:text-white'
              }`
            }
          >
            <Icon size={17} />
            <span className="flex-1">{label}</span>
            <ChevronRight size={13} className="opacity-20 shrink-0" />
          </NavLink>
        ))}
      </nav>

      {/* Versión */}
      <div className="px-5 py-3 border-t border-white/[0.06]">
        <p className="text-[10px] text-white font-mono">v2026.01</p>
      </div>
    </>
  );
}
