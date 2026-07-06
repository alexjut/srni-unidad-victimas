import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard, Home, ClipboardList, BarChart3, Search, Eye,
  FileText, Database, Shield, ChevronRight, UserCog,
} from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';
import LogoHorizontalNegativo from '@/assets/LogoHorizontalnegativo.svg';

export const NAV_ITEMS = [
  { to: '/dashboard',    icon: LayoutDashboard, label: 'Inicio'        },
  { to: '/victimas',     icon: Search,          label: 'Víctimas'      },
  { to: '/hogares',      icon: Home,            label: 'Hogares',       caracterizadorOnly: true },
  { to: '/encuestas',    icon: ClipboardList,   label: 'Encuestas',     caracterizadorOnly: true },
  { to: '/reportes',     icon: BarChart3,       label: 'Reportes',      caracterizadorOnly: true },
  { to: '/supervision',  icon: Eye,             label: 'Supervisión',   supervisorOnly: true },
  { to: '/instrumentos', icon: FileText,        label: 'Instrumentos'  },
  { to: '/parametricas', icon: Database,        label: 'Paramétricas'  },
  { to: '/auditoria',    icon: Shield,          label: 'Auditoría',     coordinadorOnly: true },
  { to: '/usuarios',     icon: UserCog,         label: 'Usuarios',      adminOnly: true },
];

interface SidebarProps {
  onNavigate?: () => void;
}

export default function Sidebar({ onNavigate }: SidebarProps) {
  const usuario = useAuthStore((s) => s.usuario);
  const esAdmin            = !!usuario?.perfil?.puede_administrar;
  const puedeSupervisar    = !!usuario?.perfil?.puede_ver_reportes;
  const puedeCaracterizar  = !!usuario?.perfil?.puede_caracterizar;
  const codigoPerfil       = usuario?.perfil?.codigo ?? '';
  const puedeVerAuditoria  = ['COORDINADOR', 'ADMINISTRADOR'].includes(codigoPerfil);
  const items = NAV_ITEMS.filter((i) => {
    if ('adminOnly'         in i && i.adminOnly         && !esAdmin)           return false;
    if ('supervisorOnly'    in i && i.supervisorOnly    && !puedeSupervisar)   return false;
    if ('coordinadorOnly'   in i && i.coordinadorOnly   && !puedeVerAuditoria) return false;
    if ('caracterizadorOnly' in i && i.caracterizadorOnly && !puedeCaracterizar) return false;
    return true;
  });
  return (
    <>
      {/* Logo */}
      <div className="px-5 py-5">
        <img src={LogoHorizontalNegativo} alt="Unidad para las Víctimas" className="h-10 w-auto" />
      </div>

      {/* Navegación */}
      <nav className="flex-1 px-3 py-3 space-y-0.5 overflow-y-auto" aria-label="Menú principal">
        {items.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            onClick={onNavigate}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 border-l-2 ${
                isActive
                  ? 'border-gov-amarillo bg-white/10 text-white'
                  : 'border-transparent text-white/70 hover:bg-white/[0.07] hover:text-white'
              }`
            }
          >
            {({ isActive }) => (
              <>
                <Icon size={17} />
                <span className="flex-1">{label}</span>
                <ChevronRight
                  size={13}
                  className={`shrink-0 transition-colors duration-150 ${isActive ? 'text-gov-amarillo' : 'opacity-20'}`}
                />
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Versión */}
      <div className="px-5 py-3 border-t border-white/[0.06]">
        <div className="flex items-center gap-1.5">
          <div className="w-1.5 h-1.5 rounded-full bg-gov-amarillo shrink-0" />
          <p className="text-[10px] text-white/50 font-mono">v2026.01</p>
        </div>
      </div>
    </>
  );
}
