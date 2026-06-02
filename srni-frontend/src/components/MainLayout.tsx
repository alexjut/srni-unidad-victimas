/**
 * Layout principal — sidebar fijo en desktop, drawer con hamburguesa en mobile/tablet
 */
import { useState, useCallback, useRef, useEffect } from 'react';
import { Outlet, useNavigate, useLocation, NavLink } from 'react-router-dom';
import { Menu, X, KeyRound, LogOut, ChevronDown } from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';
import { authApi } from '@/api/auth';
import Sidebar, { NAV_ITEMS } from '@/components/Sidebar';

export default function MainLayout() {
  const { usuario, logout } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);

  const closeDrawer = useCallback(() => setDrawerOpen(false), []);

  // Cerrar dropdown al hacer clic fuera
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setUserMenuOpen(false);
      }
    }
    if (userMenuOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [userMenuOpen]);

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

      {/* Skip to content — a11y */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:z-[100] focus:top-2 focus:left-2 focus:bg-gov-azul focus:text-white focus:px-4 focus:py-2 focus:rounded-md focus:text-sm focus:font-semibold"
      >
        Ir al contenido principal
      </a>

      {/* ── Sidebar fijo: solo visible en desktop (lg+) ── */}
      <aside className="hidden lg:flex w-64 bg-gov-azulOscuro text-white flex-col shadow-xl shrink-0">
        <Sidebar />
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
        <Sidebar onNavigate={closeDrawer} />
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
            <button
              onClick={() => setUserMenuOpen(true)}
              className="w-9 h-9 rounded-full bg-gov-azul flex items-center justify-center text-white text-sm font-bold ring-2 ring-white/20"
              aria-haspopup="dialog"
              aria-label="Menú de usuario"
            >
              {usuario.nombre_completo?.charAt(0) ?? '?'}
            </button>
          )}
        </header>

        {/* Bottom sheet mobile — menú de usuario */}
        {userMenuOpen && (
          <>
            <div
              className="fixed inset-0 z-50 bg-black/40 lg:hidden"
              onClick={() => setUserMenuOpen(false)}
              aria-hidden="true"
            />
            <div className="fixed inset-x-0 bottom-0 z-50 lg:hidden animate-slide-up">
              <div className="bg-white rounded-t-2xl shadow-soft-xl pb-safe">
                {/* Handle */}
                <div className="flex justify-center pt-3 pb-1">
                  <div className="w-10 h-1 rounded-full bg-gray-300" />
                </div>

                {/* Info usuario */}
                <div className="flex items-center gap-3 px-5 py-4 border-b border-gov-borde">
                  <div className="w-11 h-11 rounded-full bg-gov-azul flex items-center justify-center text-white text-base font-bold shrink-0">
                    {usuario?.nombre_completo?.charAt(0) ?? '?'}
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-bold text-gov-azulOscuro truncate">{usuario?.nombre_completo}</p>
                    {usuario?.perfil && (
                      <p className="text-xs text-gov-gris">{usuario.perfil.nombre}</p>
                    )}
                    <p className="text-xs font-medium text-gov-azul mt-0.5">Sesión activa</p>
                  </div>
                </div>

                {/* Acciones */}
                <div className="px-3 py-2">
                  <NavLink
                    to="/perfil/cambiar-password"
                    onClick={() => setUserMenuOpen(false)}
                    className="flex items-center gap-3 px-4 py-3.5 rounded-xl text-sm font-medium text-gov-azulOscuro active:bg-gov-azulTenue transition-colors"
                  >
                    <KeyRound size={18} className="text-gov-azul" />
                    Cambiar contraseña
                  </NavLink>
                  <button
                    onClick={handleLogout}
                    className="flex items-center gap-3 px-4 py-3.5 rounded-xl text-sm font-medium text-gov-rojo active:bg-gov-rojoTenue transition-colors w-full"
                  >
                    <LogOut size={18} />
                    Cerrar sesión
                  </button>
                </div>

                {/* Botón cancelar */}
                <div className="px-3 pb-4 pt-1">
                  <button
                    onClick={() => setUserMenuOpen(false)}
                    className="w-full py-3 rounded-xl bg-gray-100 text-sm font-semibold text-gov-gris active:bg-gray-200 transition-colors"
                  >
                    Cancelar
                  </button>
                </div>
              </div>
            </div>
          </>
        )}

        {/* Header desktop */}
        <header className="hidden lg:flex items-center justify-between bg-white border-b border-gov-borde px-6 py-3 shrink-0">
          <p className="text-sm font-display font-semibold text-gray-800">{currentLabel}</p>
          {usuario && (
            <div className="relative" ref={userMenuRef}>
              <button
                onClick={() => setUserMenuOpen(prev => !prev)}
                className={`flex items-center gap-3 rounded-lg px-3 py-2 border transition-colors ${
                  userMenuOpen
                    ? 'bg-gov-azulTenue border-gov-azul/30'
                    : 'border-transparent hover:bg-gov-azulTenue/50 hover:border-gov-azul/20'
                }`}
                aria-haspopup="true"
                aria-expanded={userMenuOpen}
              >
                <div className="w-8 h-8 rounded-full bg-gov-azul flex items-center justify-center text-white text-xs font-bold shrink-0">
                  {usuario.nombre_completo?.charAt(0) ?? '?'}
                </div>
                <div className="text-left">
                  <p className="text-sm font-semibold text-gov-azulOscuro">{usuario.nombre_completo}</p>
                  <p className="text-xs text-gov-gris">{usuario.perfil?.nombre ?? usuario.codigo_usuario}</p>
                </div>
                <ChevronDown size={16} className={`text-gov-azul transition-transform ${userMenuOpen ? 'rotate-180' : ''}`} />
              </button>

              {userMenuOpen && (
                <div className="absolute right-0 top-full mt-1.5 w-60 bg-white rounded-2xl shadow-soft-lg border border-gov-borde/60 py-1 z-50 animate-slide-down">
                  <div className="px-4 py-3 border-b border-gov-borde">
                    <p className="text-xs font-medium text-gov-azul uppercase tracking-wide">Sesión activa</p>
                    <p className="text-sm font-bold text-gov-azulOscuro truncate mt-0.5">{usuario.nombre_completo}</p>
                    {usuario.perfil && (
                      <p className="text-xs text-gov-gris">{usuario.perfil.nombre}</p>
                    )}
                  </div>
                  <div className="py-1">
                    <NavLink
                      to="/perfil/cambiar-password"
                      onClick={() => setUserMenuOpen(false)}
                      className="flex items-center gap-2.5 px-4 py-2.5 text-sm font-medium text-gov-azulOscuro hover:bg-gov-azulTenue transition-colors"
                    >
                      <KeyRound size={16} className="text-gov-azul" />
                      Cambiar contraseña
                    </NavLink>
                    <button
                      onClick={handleLogout}
                      className="flex items-center gap-2.5 px-4 py-2.5 text-sm font-medium text-gov-rojo hover:bg-gov-rojoTenue transition-colors w-full"
                    >
                      <LogOut size={16} />
                      Cerrar sesión
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </header>

        {/* Contenido principal */}
        <main id="main-content" className="flex-1 overflow-y-auto" role="main">
          <div key={location.pathname} className="page-content">
            <Outlet />
          </div>
        </main>
      </div>

    </div>
  );
}
