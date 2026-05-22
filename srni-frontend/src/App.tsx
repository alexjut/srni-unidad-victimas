import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import LoginPage from '@/pages/Login';
import DashboardPage from '@/pages/Dashboard';
import HogaresPage from '@/pages/Hogares';
import EncuestasPage from '@/pages/Encuestas';
import ReportesPage from '@/pages/Reportes';
import MainLayout from '@/components/MainLayout';

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { accessToken } = useAuthStore();
  if (!accessToken) return <Navigate to="/login" replace />;
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
        <Route path="hogares"    element={<HogaresPage />} />
        <Route path="encuestas"  element={<EncuestasPage />} />
        <Route path="reportes"   element={<ReportesPage />} />
      </Route>

      {/* Ruta catch-all */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
