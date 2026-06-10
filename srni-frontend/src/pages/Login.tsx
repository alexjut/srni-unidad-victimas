/**
 * Página de Login — liquid glass / glassmorphism
 * Fondo gradiente + orbes decorativos + tarjeta glass con backdrop-blur
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { authApi } from '@/api/auth';
import { useAuthStore } from '@/stores/authStore';
import { Eye, EyeOff, ArrowRight, Shield } from 'lucide-react';

export default function LoginPage() {
  const navigate = useNavigate();
  const { setTokens, setUsuario } = useAuthStore();

  const [usuario, setUsuarioField] = useState('');
  const [password, setPassword] = useState('');
  const [showPass, setShowPass] = useState(false);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!usuario.trim() || !password.trim()) {
      setError('Ingrese usuario y contraseña.');
      return;
    }
    setCargando(true);
    setError('');
    try {
      const { data: tokens } = await authApi.login({
        codigo_usuario: usuario.trim().toUpperCase(),
        password,
      });
      setTokens(tokens.access, tokens.refresh);
      const { data: perfil } = await authApi.perfil();
      setUsuario(perfil);
      navigate('/dashboard');
    } catch (err: any) {
      const detalle = err?.response?.data?.detail;
      setError(detalle ?? 'Credenciales incorrectas. Verifique e intente de nuevo.');
    } finally {
      setCargando(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden bg-[#0a1628]">

      {/* ── Fondo gradiente ── */}
      <div className="absolute inset-0 bg-gradient-to-br from-[#0a1628] via-[#0d2847] to-[#0a1628]" />

      {/* ── Orbes decorativos ── */}
      <div className="absolute top-[-20%] left-[-10%] w-[600px] h-[600px] rounded-full bg-gov-azul/20 blur-[120px] animate-pulse" style={{ animationDuration: '8s' }} />
      <div className="absolute bottom-[-15%] right-[-5%] w-[500px] h-[500px] rounded-full bg-blue-400/15 blur-[100px] animate-pulse" style={{ animationDuration: '10s' }} />
      <div className="absolute top-[20%] right-[15%] w-[300px] h-[300px] rounded-full bg-gov-amarillo/10 blur-[80px] animate-pulse" style={{ animationDuration: '12s' }} />

      {/* ── Contenido central ── */}
      <div className="relative z-10 w-full max-w-[440px] px-5 animate-fade-in-up">

        {/* Identidad institucional */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 mb-5">
            <div className="w-0.5 h-6 bg-gov-amarillo rounded-full" />
            <span className="text-gov-amarillo font-bold text-[10px] tracking-[0.2em] uppercase">
              GOV.CO
            </span>
          </div>
          <h1 className="font-display text-white text-2xl sm:text-3xl font-bold tracking-tight mb-2">
            Unidad para las Víctimas
          </h1>
          <p className="text-white text-sm">
            Sistema de Registro Nacional de Información
          </p>
        </div>

        {/* ── Tarjeta glass ── */}
        <div
          className="rounded-3xl p-7 sm:p-8 animate-scale-in"
          style={{
            background: 'rgba(255, 255, 255, 0.06)',
            backdropFilter: 'blur(40px) saturate(1.4)',
            WebkitBackdropFilter: 'blur(40px) saturate(1.4)',
            border: '1px solid rgba(255, 255, 255, 0.12)',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.1)',
          }}
        >
          <h2 className="font-display text-white text-lg font-semibold mb-1">
            Iniciar sesión
          </h2>
          <p className="text-white text-sm mb-6">
            Credenciales institucionales
          </p>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Usuario */}
            <div>
              <label htmlFor="codigo-usuario" className="block text-[11px] font-medium text-white uppercase tracking-wider mb-1.5">
                Código de usuario
              </label>
              <input
                id="codigo-usuario"
                type="text"
                className="w-full rounded-xl px-4 py-3 text-sm text-white placeholder-white/25 outline-none transition-all duration-200 focus:ring-2 focus:ring-white/20"
                style={{
                  background: 'rgba(255, 255, 255, 0.07)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                }}
                onFocus={(e) => { e.currentTarget.style.background = 'rgba(255, 255, 255, 0.10)'; e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.2)'; }}
                onBlur={(e) => { e.currentTarget.style.background = 'rgba(255, 255, 255, 0.07)'; e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.1)'; }}
                placeholder="Ej. ALEXJUT"
                value={usuario}
                onChange={(e) => setUsuarioField(e.target.value.toUpperCase())}
                autoComplete="username"
                autoCapitalize="characters"
                disabled={cargando}
              />
            </div>

            {/* Contraseña */}
            <div>
              <label htmlFor="password" className="block text-[11px] font-medium text-white uppercase tracking-wider mb-1.5">
                Contraseña
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={showPass ? 'text' : 'password'}
                  className="w-full rounded-xl px-4 py-3 pr-11 text-sm text-white placeholder-white/25 outline-none transition-all duration-200 focus:ring-2 focus:ring-white/20"
                  style={{
                    background: 'rgba(255, 255, 255, 0.07)',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                  }}
                  onFocus={(e) => { e.currentTarget.style.background = 'rgba(255, 255, 255, 0.10)'; e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.2)'; }}
                  onBlur={(e) => { e.currentTarget.style.background = 'rgba(255, 255, 255, 0.07)'; e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.1)'; }}
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  disabled={cargando}
                />
                <button
                  type="button"
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-white/30 hover:text-white/60 transition-colors"
                  onClick={() => setShowPass(!showPass)}
                  aria-label={showPass ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                >
                  {showPass ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {/* Error */}
            {error && (
              <div
                className="rounded-xl px-4 py-3 text-sm text-red-200 animate-fade-in"
                style={{
                  background: 'rgba(220, 38, 38, 0.15)',
                  border: '1px solid rgba(220, 38, 38, 0.25)',
                }}
              >
                {error}
              </div>
            )}

            {/* Botón */}
            <button
              type="submit"
              className="w-full flex items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-semibold text-white transition-all duration-200 active:scale-[0.97] disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100 mt-2"
              style={{
                background: 'linear-gradient(135deg, #1565C0, #1976D2)',
                boxShadow: '0 4px 20px rgba(21, 101, 192, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.15)',
              }}
              disabled={cargando}
            >
              {cargando ? (
                <>
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Verificando…
                </>
              ) : (
                <>
                  Ingresar
                  <ArrowRight size={16} />
                </>
              )}
            </button>
          </form>

          {/* Nota de seguridad */}
          <div className="flex items-center justify-center gap-1.5 mt-6">
            <Shield size={12} className="text-white/20" />
            <p className="text-[11px] text-white">
              Acceso restringido · Ley 1581 de 2012
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
