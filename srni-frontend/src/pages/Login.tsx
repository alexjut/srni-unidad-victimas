/**
 * Página de Login — estilo GOV.CO
 * Fondo azul oscuro + franja amarilla + logo Unidad para las Víctimas
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { authApi } from '@/api/auth';
import { useAuthStore } from '@/stores/authStore';
import { Eye, EyeOff, LogIn } from 'lucide-react';

export default function LoginPage() {
  const navigate   = useNavigate();
  const { setTokens, setUsuario } = useAuthStore();

  const [usuario,    setUsuarioField] = useState('');
  const [password,   setPassword]     = useState('');
  const [showPass,   setShowPass]     = useState(false);
  const [cargando,   setCargando]     = useState(false);
  const [error,      setError]        = useState('');

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

      // Cargar perfil del usuario
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
    <div className="min-h-screen flex bg-gov-azulOscuro">

      {/* ── Panel izquierdo: identidad institucional ── */}
      <div className="hidden lg:flex lg:w-1/2 flex-col justify-between p-12 text-white">
        <div>
          {/* Franja GOV.CO */}
          <div className="flex items-center gap-3 mb-10">
            <div className="w-1 h-10 bg-gov-amarillo rounded-full" />
            <div>
              <p className="text-gov-amarillo font-bold text-xs tracking-widest uppercase">
                GOV.CO
              </p>
              <p className="text-blue-200 text-xs">
                Portal del Estado Colombiano
              </p>
            </div>
          </div>

          <h1 className="font-display text-4xl font-bold leading-tight mb-4">
            Unidad para las<br />Víctimas
          </h1>
          <p className="text-blue-200 text-lg leading-relaxed max-w-sm">
            Sistema de Registro Nacional de Información — SRNI
          </p>
          <p className="text-blue-300 text-sm mt-4 max-w-sm">
            Panel de supervisión y seguimiento de la caracterización socioeconómica
            de las víctimas del conflicto armado.
          </p>
        </div>
      </div>

      {/* ── Panel derecho: formulario ── */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-6">
        <div className="w-full max-w-md">

          {/* Header móvil */}
          <div className="lg:hidden mb-8 text-white text-center">
            <div className="inline-block border-b-4 border-gov-amarillo pb-2 mb-3">
              <span className="text-gov-amarillo font-bold text-xs tracking-widest uppercase">
                GOV.CO
              </span>
            </div>
            <h1 className="font-display text-2xl font-bold">Unidad para las Víctimas</h1>
            <p className="text-blue-300 text-sm mt-1">SRNI · Panel Web</p>
          </div>

          <div className="bg-white rounded-2xl shadow-2xl p-8">
            <h2 className="font-display text-xl font-bold text-gray-800 mb-1">
              Iniciar sesión
            </h2>
            <p className="text-gray-500 text-sm mb-6">
              Ingrese sus credenciales institucionales
            </p>

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Usuario */}
              <div>
                <label className="block text-xs font-semibold text-gray-600 uppercase tracking-wide mb-1">
                  Código de usuario
                </label>
                <input
                  type="text"
                  className="input"
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
                <label className="block text-xs font-semibold text-gray-600 uppercase tracking-wide mb-1">
                  Contraseña
                </label>
                <div className="relative">
                  <input
                    type={showPass ? 'text' : 'password'}
                    className="input pr-10"
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete="current-password"
                    disabled={cargando}
                  />
                  <button
                    type="button"
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    onClick={() => setShowPass(!showPass)}
                    tabIndex={-1}
                  >
                    {showPass ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              {/* Error */}
              {error && (
                <div className="bg-gov-rojoTenue border border-red-200 text-gov-rojo text-sm rounded-lg p-3">
                  {error}
                </div>
              )}

              {/* Botón */}
              <button
                type="submit"
                className="btn-primary w-full flex items-center justify-center gap-2 py-3"
                disabled={cargando}
              >
                <LogIn size={18} />
                {cargando ? 'Verificando…' : 'Ingresar al sistema'}
              </button>
            </form>

            {/* Nota de seguridad */}
            <p className="text-xs text-gray-400 text-center mt-5">
              🔒 Acceso restringido a funcionarios autorizados.<br />
              Datos protegidos por la Ley 1581 de 2012.
            </p>
          </div>
        </div>
      </div>

    </div>
  );
}
