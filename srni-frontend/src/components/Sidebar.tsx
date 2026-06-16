import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard, Home, ClipboardList, BarChart3, Search, Eye,
  FileText, Database, Shield, ChevronRight, UserCog,
} from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';
import LogoHorizontalColor from '@/assets/LogoHorizontalNegativo.svg';

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
  { to: '/usuarios',     icon: UserCog,         label: 'Usuarios',      adminOnly: true },
];

interface SidebarProps {
  onNavigate?: () => void;
}

export default function Sidebar({ onNavigate }: SidebarProps) {
  const usuario = useAuthStore((s) => s.usuario);
  const esAdmin = !!usuario?.perfil?.puede_administrar;
  const items = NAV_ITEMS.filter((i) => !('adminOnly' in i && i.adminOnly) || esAdmin);
  return (
    <>
      {/* Logo */}
      <div className="px-5 py-5 border-b border-white/[0.08]">
        <img src={LogoHorizontalColor} alt="Unidad para las Víctimas" className="h-10 w-auto" />
      
        </div>

      {/* Navegación */}
      <nav className="flex-1 px-3 py-3 space-y-0.5 overflow-y-auto" aria-label="Menú principal">
        {items.map(({ to, icon: Icon, label }) => (
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
