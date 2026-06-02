import { useEffect, useState } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import { authApi } from '@/api/auth';
import Spinner from '@/components/ui/Spinner';
import LoginPage from '@/pages/Login';
import DashboardPage from '@/pages/Dashboard';
import HogaresPage from '@/pages/Hogares';
import EncuestasPage from '@/pages/Encuestas';
import ReportesPage from '@/pages/Reportes';
import VictimasPage from '@/pages/Victimas';
import VictimaDetallePage from '@/pages/VictimaDetalle';
import SupervisionPage from '@/pages/Supervision';
import HogarDetallePage from '@/pages/HogarDetalle';
import SesionDetallePage from '@/pages/SesionDetalle';
import InstrumentosPage from '@/pages/Instrumentos';
import ParametricasPage from '@/pages/Parametricas';
import AuditoriaPage from '@/pages/Auditoria';
import CambiarPasswordPage from '@/pages/CambiarPassword';
import NotFound from '@/pages/NotFound';
import MainLayout from '@/components/MainLayout';

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
        <Route path="dashboard"  element={<DashboardPage />} />
        <Route path="victimas"   element={<VictimasPage />} />
        <Route path="victimas/:id" element={<VictimaDetallePage />} />
        <Route path="hogares"    element={<HogaresPage />} />
        <Route path="hogares/:id" element={<HogarDetallePage />} />
        <Route path="encuestas"  element={<EncuestasPage />} />
        <Route path="encuestas/:id" element={<SesionDetallePage />} />
        <Route path="reportes"   element={<ReportesPage />} />
        <Route path="supervision" element={<SupervisionPage />} />
        <Route path="instrumentos" element={<InstrumentosPage />} />
        <Route path="parametricas" element={<ParametricasPage />} />
        <Route path="auditoria" element={<AuditoriaPage />} />
        <Route path="perfil/cambiar-password" element={<CambiarPasswordPage />} />
      </Route>

      {/* Ruta catch-all → 404 */}
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
