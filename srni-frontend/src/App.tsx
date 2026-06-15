import { lazy, Suspense, useEffect, useState } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import { authApi } from '@/api/auth';
import Spinner from '@/components/ui/Spinner';
import LoginPage from '@/pages/Login';
import DashboardPage from '@/pages/Dashboard';
import MainLayout from '@/components/MainLayout';

const HogaresPage         = lazy(() => import('@/pages/Hogares'));
const HogarDetallePage    = lazy(() => import('@/pages/HogarDetalle'));
const EncuestasPage       = lazy(() => import('@/pages/Encuestas'));
const SesionDetallePage   = lazy(() => import('@/pages/SesionDetalle'));
const ReportesPage        = lazy(() => import('@/pages/Reportes'));
const VictimasPage        = lazy(() => import('@/pages/Victimas'));
const VictimaDetallePage  = lazy(() => import('@/pages/VictimaDetalle'));
const SupervisionPage     = lazy(() => import('@/pages/Supervision'));
const InstrumentosPage    = lazy(() => import('@/pages/Instrumentos'));
const ParametricasPage    = lazy(() => import('@/pages/Parametricas'));
const AuditoriaPage       = lazy(() => import('@/pages/Auditoria'));
const UsuariosPage        = lazy(() => import('@/pages/Usuarios'));
const CambiarPasswordPage = lazy(() => import('@/pages/CambiarPassword'));
const NotFound            = lazy(() => import('@/pages/NotFound'));

function PageSpinner() {
  return (
    <div className="flex h-64 items-center justify-center">
      <Spinner size="lg" />
    </div>
  );
}

function SuspensePage({ children }: { children: React.ReactNode }) {
  return <Suspense fallback={<PageSpinner />}>{children}</Suspense>;
}

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { accessToken, usuario, setUsuario, logout } = useAuthStore();
  const [cargando, setCargando] = useState(!usuario && !!accessToken);

  useEffect(() => {
    if (!accessToken || usuario) return;
    authApi.perfil()
      .then(({ data }) => setUsuario(data))
      .catch(() => logout())
      .finally(() => setCargando(false));
  }, [accessToken, usuario, setUsuario, logout]);

  if (!accessToken) return <Navigate to="/login" replace />;
  if (cargando) return (
    <div className="flex h-screen items-center justify-center bg-gov-grisTenue">
      <Spinner size="lg" />
    </div>
  );
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route
        path="/"
        element={
          <RequireAuth>
            <MainLayout />
          </RequireAuth>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard"   element={<DashboardPage />} />
        <Route path="victimas"    element={<SuspensePage><VictimasPage /></SuspensePage>} />
        <Route path="victimas/:id" element={<SuspensePage><VictimaDetallePage /></SuspensePage>} />
        <Route path="hogares"     element={<SuspensePage><HogaresPage /></SuspensePage>} />
        <Route path="hogares/:id" element={<SuspensePage><HogarDetallePage /></SuspensePage>} />
        <Route path="encuestas"   element={<SuspensePage><EncuestasPage /></SuspensePage>} />
        <Route path="encuestas/:id" element={<SuspensePage><SesionDetallePage /></SuspensePage>} />
        <Route path="reportes"    element={<SuspensePage><ReportesPage /></SuspensePage>} />
        <Route path="supervision" element={<SuspensePage><SupervisionPage /></SuspensePage>} />
        <Route path="instrumentos" element={<SuspensePage><InstrumentosPage /></SuspensePage>} />
        <Route path="parametricas" element={<SuspensePage><ParametricasPage /></SuspensePage>} />
        <Route path="auditoria"   element={<SuspensePage><AuditoriaPage /></SuspensePage>} />
        <Route path="usuarios"    element={<SuspensePage><UsuariosPage /></SuspensePage>} />
        <Route path="perfil/cambiar-password" element={<SuspensePage><CambiarPasswordPage /></SuspensePage>} />
      </Route>

      {/* Ruta catch-all → 404 */}
      <Route path="*" element={<SuspensePage><NotFound /></SuspensePage>} />
    </Routes>
  );
}
