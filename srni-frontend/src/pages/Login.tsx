/**
 * Página de Login — liquid glass / glassmorphism
 * Fondo gradiente + orbes decorativos + tarjeta glass con backdrop-blur
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { authApi } from '@/api/auth';
import { useAuthStore } from '@/stores/authStore';
import { Eye, EyeOff, ArrowRight, Shield } from 'lucide-react';
import { toast } from 'sonner';
import LogoHorizontal from '@/assets/LogoColor.svg';

const BG_IMAGES = [
  '/img/1.avif', '/img/2.avif', '/img/3.avif', '/img/4.avif',
  '/img/5.avif', '/img/6.avif', '/img/7.avif',
];

export default function LoginPage() {
  const navigate = useNavigate();
  const { setTokens, setUsuario } = useAuthStore();

  const [bgIdx, setBgIdx] = useState(0);
  const [usuario, setUsuarioField] = useState('');
  const [password, setPassword] = useState('');
  const [showPass, setShowPass] = useState(false);
  const [cargando, setCargando] = useState(false);

  useEffect(() => {
    const timer = setInterval(() => {
      setBgIdx((i) => (i + 1) % BG_IMAGES.length);
    }, 5000);
    return () => clearInterval(timer);
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!usuario.trim() || !password.trim()) {
      toast.error('Ingrese usuario y contraseña.');
      return;
    }
    setCargando(true);
    const inicio = Date.now();
    try {
      const { data: tokens } = await authApi.login({
        codigo_usuario: usuario.trim().toUpperCase(),
        password,
      });
      setTokens(tokens.access, tokens.refresh);
      const { data: perfil } = await authApi.perfil();
      setUsuario(perfil);
      const espera = Math.max(0, 700 - (Date.now() - inicio));
      await new Promise((r) => setTimeout(r, espera));
      navigate('/dashboard');
    } catch (err: any) {
      const espera = Math.max(0, 700 - (Date.now() - inicio));
      await new Promise((r) => setTimeout(r, espera));
      toast.error('La combinación de usuario y contraseña no es correcta.');
    } finally {
      setCargando(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden bg-[#0a1628]">

      {/* Franja GOV.CO */}
      <div className="fixed top-0 inset-x-0 h-1 bg-gov-amarillo z-50" aria-hidden="true" />

      {/* ── Fondo slideshow ── */}
      {BG_IMAGES.map((src, i) => (
        <div
          key={src}
          className="absolute inset-0 bg-cover bg-center transition-opacity duration-1000"
          style={{ backgroundImage: `url(${src})`, opacity: i === bgIdx ? 1 : 0 }}
        />
      ))}
      {/* Overlay oscuro para legibilidad */}
      <div className="absolute inset-0 bg-[#0a1628]/65" />

      {/* ── Contenido central ── */}
      <div className="relative z-10 w-full max-w-[440px] px-5 animate-fade-in-up">

        {/* Identidad institucional */}
        <div className="text-center mb-7">
          <img src={LogoHorizontal} alt="Logo institucional" className="h-40 mx-auto mb-4" />
          <p className="text-white text-[15px] tracking-wide">
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
          <p className="text-white text-xs font-semibold uppercase tracking-widest mb-5">
            Iniciar sesión
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
                placeholder="Ingrese su usuario"
                value={usuario}
                onChange={(e) => setUsuarioField(e.target.value)}
                autoComplete="username"
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
                  placeholder="Ingrese su contraseña"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  disabled={cargando}
                />
                <button
                  type="button"
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-white hover:text-white transition-colors"
                  onClick={() => setShowPass(!showPass)}
                  aria-label={showPass ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                >
                  {showPass ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {/* Botón */}
            <button
              type="submit"
              className="w-full flex items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-bold transition-all duration-200 active:scale-[0.97] disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100 mt-2"
              style={{
                background: 'linear-gradient(135deg, #FFCC03, #F5BF04)',
                color: '#003A80',
                boxShadow: '0 4px 20px rgba(245, 191, 4, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.25)',
              }}
              disabled={cargando}
            >
              {cargando ? (
                <>
                  <span className="w-4 h-4 border-2 border-gov-azulOscuro/30 border-t-gov-azulOscuro rounded-full animate-spin" />
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
            <Shield size={12} className="text-white" />
            <p className="text-[11px] text-white">
              Acceso restringido · Ley 1581 de 2012
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
