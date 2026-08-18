import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard, Home, ClipboardList, BarChart3, Search, Eye,
  FileText, Database, Shield, ChevronRight, UserCog, FileCheck,
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
  // Excepciones de vigencia (14-ago-2026). Es una página del panel como
  // cualquier otra: la primera versión se servía desde Django y se veía como
  // otra aplicación —sin header, sin menú, sin footer—, así que quien la abría
  // perdía la navegación entera.
  { to: '/autorizaciones', icon: FileCheck, label: 'Autorizaciones',
    autorizadorOnly: true },
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
  // Del flag del perfil y no del código: el permiso lo tienen coordinación,
  // supervisión y administración, pero también cualquier perfil nuevo al que se
  // lo enciendan. Listar códigos a mano deja el menú desactualizado el día que
  // se cree una cuenta más, y un menú que aparece de más termina en un 403.
  const puedeAutorizar     = !!usuario?.perfil?.puede_autorizar_excepciones
    || esAdmin;
  const items = NAV_ITEMS.filter((i) => {
    if ('adminOnly'         in i && i.adminOnly         && !esAdmin)           return false;
    if ('supervisorOnly'    in i && i.supervisorOnly    && !puedeSupervisar)   return false;
    if ('coordinadorOnly'   in i && i.coordinadorOnly   && !puedeVerAuditoria) return false;
    if ('caracterizadorOnly' in i && i.caracterizadorOnly && !puedeCaracterizar) return false;
    if ('autorizadorOnly'   in i && i.autorizadorOnly   && !puedeAutorizar)    return false;
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
        {items.map((item) => {
          const { to, icon: Icon, label } = item;
          return (
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
          );
        })}
      </nav>

      {/* Info institucional + versión */}
      <div className="px-5 py-3 border-t border-white/[0.06] space-y-2">
        <p className="text-[10px] text-white/40 leading-relaxed">
          Subdirección Red Nacional de Información
        </p>
        <div className="flex items-center gap-1.5">
          <div className="w-1.5 h-1.5 rounded-full bg-gov-amarillo shrink-0" />
          <p className="text-[10px] text-white/50 font-mono">v2026.01</p>
        </div>
      </div>
    </>
  );
}
