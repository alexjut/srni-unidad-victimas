/**
 * Layout principal — sidebar fijo en desktop, drawer con hamburguesa en mobile/tablet
 */
import { useState, useCallback } from 'react';
import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom';
import {
  LayoutDashboard, Home, ClipboardList, BarChart3,
  LogOut, ChevronRight, Menu, X,
} from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';

const NAV_ITEMS = [
  { to: '/dashboard',  icon: LayoutDashboard, label: 'Inicio'    },
  { to: '/hogares',    icon: Home,             label: 'Hogares'   },
  { to: '/encuestas',  icon: ClipboardList,    label: 'Encuestas' },
  { to: '/reportes',   icon: BarChart3,        label: 'Reportes'  },
];

function SidebarContent({ onNavigate, onLogout, usuario }: {
  onNavigate?: () => void;
  onLogout: () => void;
  usuario: ReturnType<typeof useAuthStore>['usuario'];
}) {
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
                  ? 'bg-white/15 text-white'
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

export default function MainLayout() {
  const { usuario, logout } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();
  const [drawerOpen, setDrawerOpen] = useState(false);

  const closeDrawer = useCallback(() => setDrawerOpen(false), []);

  function handleLogout() {
    setDrawerOpen(false);
    logout();
    navigate('/login');
  }

  // Título de la página actual para el topbar mobile
  const currentLabel = NAV_ITEMS.find(i => location.pathname.startsWith(i.to))?.label ?? 'SRNI';

  return (
    <div className="flex h-screen bg-gov-grisTenue">

      {/* ── Sidebar fijo: solo visible en desktop (lg+) ── */}
      <aside className="hidden lg:flex w-64 bg-gov-azulOscuro text-white flex-col shadow-xl shrink-0">
        <SidebarContent onLogout={handleLogout} usuario={usuario} />
      </aside>

      {/* ── Drawer mobile: overlay + panel deslizable ── */}
      {drawerOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={closeDrawer}
          aria-hidden="true"
        />
      )}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-64 bg-gov-azulOscuro text-white flex flex-col shadow-xl transform transition-transform duration-300 ease-in-out lg:hidden ${
          drawerOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Botón cerrar dentro del drawer */}
        <button
          onClick={closeDrawer}
          className="absolute top-4 right-3 text-blue-200 hover:text-white"
          aria-label="Cerrar menú"
        >
          <X size={22} />
        </button>
        <SidebarContent onNavigate={closeDrawer} onLogout={handleLogout} usuario={usuario} />
      </aside>

      {/* ── Columna principal ── */}
      <div className="flex-1 flex flex-col min-w-0">

        {/* Topbar mobile: solo visible en mobile/tablet */}
        <header className="flex lg:hidden items-center gap-3 bg-gov-azulOscuro text-white px-4 py-3 shadow-md">
          <button
            onClick={() => setDrawerOpen(true)}
            aria-label="Abrir menú"
          >
            <Menu size={24} />
          </button>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-semibold text-gov-amarillo tracking-widest uppercase">GOV.CO</p>
            <p className="text-sm font-bold truncate">{currentLabel}</p>
          </div>
          {usuario && (
            <p className="text-xs text-blue-200 truncate max-w-[120px]">{usuario.nombre_completo}</p>
          )}
        </header>

        {/* Contenido principal */}
        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>

    </div>
  );
}
