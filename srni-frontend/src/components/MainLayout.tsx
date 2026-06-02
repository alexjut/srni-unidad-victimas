/**
 * Layout principal — sidebar fijo en desktop, drawer con hamburguesa en mobile/tablet
 */
import { useState, useCallback } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Menu, X } from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';
import { authApi } from '@/api/auth';
import Sidebar, { NAV_ITEMS } from '@/components/Sidebar';

export default function MainLayout() {
  const { usuario, logout } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();
  const [drawerOpen, setDrawerOpen] = useState(false);

  const closeDrawer = useCallback(() => setDrawerOpen(false), []);

  function handleLogout() {
    setDrawerOpen(false);
    const refresh = useAuthStore.getState().refreshToken;
    if (refresh) {
      authApi.logout(refresh).catch(() => {});
    }
    logout();
    navigate('/login');
  }

  const currentLabel = NAV_ITEMS.find(i => location.pathname.startsWith(i.to))?.label ?? 'SRNI';

  return (
    <div className="flex h-screen bg-gov-grisTenue">

      {/* ── Sidebar fijo: solo visible en desktop (lg+) ── */}
      <aside className="hidden lg:flex w-64 bg-gov-azulOscuro text-white flex-col shadow-xl shrink-0">
        <Sidebar onLogout={handleLogout} />
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
        <button
          onClick={closeDrawer}
          className="absolute top-4 right-3 text-blue-200 hover:text-white"
          aria-label="Cerrar menú"
        >
          <X size={22} />
        </button>
        <Sidebar onNavigate={closeDrawer} onLogout={handleLogout} />
      </aside>

      {/* ── Columna principal ── */}
      <div className="flex-1 flex flex-col min-w-0">

        {/* Topbar mobile */}
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

        {/* Header desktop */}
        <header className="hidden lg:flex items-center justify-between bg-white border-b border-gov-borde px-6 py-3 shrink-0">
          <p className="text-sm font-display font-semibold text-gray-800">{currentLabel}</p>
          {usuario && (
            <div className="flex items-center gap-3">
              <div className="text-right">
                <p className="text-sm font-medium text-gray-700">{usuario.nombre_completo}</p>
                <p className="text-xs text-gray-400">{usuario.perfil?.nombre ?? usuario.codigo_usuario}</p>
              </div>
              <div className="w-8 h-8 rounded-full bg-gov-azul flex items-center justify-center text-white text-xs font-bold">
                {usuario.nombre_completo?.charAt(0) ?? '?'}
              </div>
            </div>
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
