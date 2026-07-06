/**
 * Dashboard — métricas y accesos rápidos según el rol del usuario
 */
import { useEffect, useState } from 'react';
import {
  Home, ClipboardCheck, Users, TrendingUp, RefreshCw,
  ArrowRight, type LucideIcon,
  Search, ClipboardList, BarChart3, Eye, Shield, UserCog,
  Loader2, CheckCircle2,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { reportesApi, type ResumenEncuestador } from '@/api/reportes';
import { useAuthStore } from '@/stores/authStore';
import Alert from '@/components/ui/Alert';

/* ── Detección de rol ── */
type RolTipo = 'encuestador' | 'supervisor' | 'coordinador' | 'admin';

function detectarRol(perfil: { codigo?: string; puede_ver_reportes?: boolean; puede_administrar?: boolean } | null): RolTipo {
  if (!perfil) return 'encuestador';
  if (perfil.puede_administrar) return 'admin';
  if (perfil.codigo === 'COORDINADOR') return 'coordinador';
  if (perfil.puede_ver_reportes) return 'supervisor';
  return 'encuestador';
}

/* ── Accesos rápidos por rol ── */
const QUICK_LINKS: Record<RolTipo, { label: string; to: string; icon: LucideIcon }[]> = {
  encuestador: [
    { label: 'Víctimas',    to: '/victimas',    icon: Search },
    { label: 'Hogares',     to: '/hogares',     icon: Home },
    { label: 'Encuestas',   to: '/encuestas',   icon: ClipboardList },
    { label: 'Reportes',    to: '/reportes',    icon: BarChart3 },
  ],
  supervisor: [
    { label: 'Supervisión', to: '/supervision', icon: Eye },
    { label: 'Reportes',    to: '/reportes',    icon: BarChart3 },
    { label: 'Encuestas',   to: '/encuestas',   icon: ClipboardList },
    { label: 'Hogares',     to: '/hogares',     icon: Home },
  ],
  coordinador: [
    { label: 'Supervisión', to: '/supervision', icon: Eye },
    { label: 'Auditoría',   to: '/auditoria',   icon: Shield },
    { label: 'Reportes',    to: '/reportes',    icon: BarChart3 },
    { label: 'Víctimas',    to: '/victimas',    icon: Search },
  ],
  admin: [
    { label: 'Usuarios',    to: '/usuarios',    icon: UserCog },
    { label: 'Supervisión', to: '/supervision', icon: Eye },
    { label: 'Auditoría',   to: '/auditoria',   icon: Shield },
    { label: 'Reportes',    to: '/reportes',    icon: BarChart3 },
  ],
};

/* ── Info contextual por rol ── */
const ROL_INFO: Record<RolTipo, {
  label: string;
  descripcion: string;
  accentBg: string;
  accentBorder: string;
  accentText: string;
  dotColor: string;
}> = {
  encuestador: {
    label: 'Encuestador de campo',
    descripcion: 'Registras y caracterizas hogares de víctimas del conflicto armado. Cada encuesta que completas alimenta directamente el Registro Nacional de Información.',
    accentBg: 'rgba(21,101,192,0.06)',
    accentBorder: 'rgba(21,101,192,0.15)',
    accentText: '#1565C0',
    dotColor: '#1565C0',
  },
  supervisor: {
    label: 'Supervisor de campo',
    descripcion: 'Supervisas el trabajo de tu equipo de encuestadores y monitoreas el avance de la caracterización en tu área de responsabilidad.',
    accentBg: 'rgba(46,125,50,0.06)',
    accentBorder: 'rgba(46,125,50,0.15)',
    accentText: '#2E7D32',
    dotColor: '#2E7D32',
  },
  coordinador: {
    label: 'Coordinador territorial',
    descripcion: 'Coordinas operaciones territoriales con acceso a la auditoría completa de actividad del sistema y supervisión de todos los equipos.',
    accentBg: 'rgba(230,81,0,0.06)',
    accentBorder: 'rgba(230,81,0,0.15)',
    accentText: '#E65100',
    dotColor: '#E65100',
  },
  admin: {
    label: 'Administrador del sistema',
    descripcion: 'Administras usuarios, perfiles y configuración del sistema. Tienes acceso completo a todos los módulos del panel SRNI.',
    accentBg: 'rgba(124,58,237,0.06)',
    accentBorder: 'rgba(124,58,237,0.15)',
    accentText: '#7C3AED',
    dotColor: '#7C3AED',
  },
};

/* ── Colores por card ── */
const CARD_THEMES = {
  green:  { bg: 'rgba(46,125,50,0.08)',  border: 'rgba(46,125,50,0.15)',  iconBg: '#2E7D32', glow: '0 4px 20px rgba(46,125,50,0.10)'  },
  blue:   { bg: 'rgba(21,101,192,0.08)', border: 'rgba(21,101,192,0.15)', iconBg: '#1565C0', glow: '0 4px 20px rgba(21,101,192,0.10)' },
  orange: { bg: 'rgba(230,81,0,0.08)',   border: 'rgba(230,81,0,0.15)',   iconBg: '#E65100', glow: '0 4px 20px rgba(230,81,0,0.10)'   },
  purple: { bg: 'rgba(128,90,213,0.08)', border: 'rgba(128,90,213,0.15)', iconBg: '#7C3AED', glow: '0 4px 20px rgba(128,90,213,0.10)' },
} as const;

function GlassCard({
  icon: Icon,
  label,
  valor,
  theme,
  delay = 0,
}: {
  icon: LucideIcon;
  label: string;
  valor: number | string;
  theme: keyof typeof CARD_THEMES;
  delay?: number;
}) {
  const t = CARD_THEMES[theme];
  return (
    <div
      className="rounded-2xl p-5 flex items-center gap-4 transition-all duration-300 hover:-translate-y-0.5 animate-fade-in-up cursor-default"
      style={{
        background: t.bg,
        backdropFilter: 'blur(20px) saturate(1.2)',
        WebkitBackdropFilter: 'blur(20px) saturate(1.2)',
        border: `1px solid ${t.border}`,
        boxShadow: `${t.glow}, inset 0 1px 0 rgba(255,255,255,0.6)`,
        animationDelay: `${delay}ms`,
        animationFillMode: 'both',
      }}
    >
      <div
        className="w-11 h-11 rounded-xl flex items-center justify-center shrink-0"
        style={{ background: t.iconBg, boxShadow: t.glow }}
      >
        <Icon size={20} className="text-white" />
      </div>
      <div>
        <p className="text-2xl font-display font-bold text-gray-800">{valor}</p>
        <p className="text-sm text-gray-500">{label}</p>
      </div>
    </div>
  );
}

/* ── Link rápido ── */
function QuickLink({ label, to, icon: Icon, onClick }: { label: string; to: string; icon: LucideIcon; onClick: (to: string) => void }) {
  return (
    <button
      onClick={() => onClick(to)}
      className="flex items-center gap-3 rounded-xl px-4 py-3.5 text-sm font-medium text-gray-700 transition-all duration-200 group hover:bg-white/80 hover:shadow-soft active:scale-[0.98]"
      style={{
        background: 'rgba(255,255,255,0.5)',
        backdropFilter: 'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)',
        border: '1px solid rgba(0,0,0,0.06)',
      }}
    >
      <Icon size={16} className="text-gray-400 group-hover:text-gov-azul transition-colors shrink-0" />
      <span className="flex-1 text-left">{label}</span>
      <ArrowRight size={14} className="text-gray-400 group-hover:text-gov-azul transition-colors shrink-0" />
    </button>
  );
}

export default function DashboardPage() {
  const { usuario } = useAuthStore();
  const navigate = useNavigate();
  const [resumen, setResumen] = useState<ResumenEncuestador | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState('');

  const perfil = usuario?.perfil ?? null;
  const rol = detectarRol(perfil);
  const rolInfo = ROL_INFO[rol];
  // Solo mostrar métricas personales si el usuario ES encuestador de campo.
  // Coordinadores y admins tienen puede_caracterizar=true pero no hacen trabajo de campo.
  const puedeCaracterizar = rol === 'encuestador' && !!perfil?.puede_caracterizar;

  async function cargar() {
    if (!puedeCaracterizar) { setCargando(false); return; }
    setCargando(true);
    setError('');
    try {
      const { data } = await reportesApi.resumen();
      setResumen(data);
    } catch {
      setError('No se pudieron cargar las métricas. Verifique la conexión.');
    } finally {
      setCargando(false);
    }
  }

  useEffect(() => { cargar(); }, []);

  const nombre = usuario?.nombre_completo ?? '—';
  const primerNombre = nombre.split(' ')[0];
  const links = QUICK_LINKS[rol];

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-5xl mx-auto">

      {/* Encabezado */}
      <div className="mb-8 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 animate-fade-in-up">
        <div>
          <h2 className="font-display text-2xl sm:text-3xl font-bold text-gray-800 tracking-tight">
            Hola, {primerNombre}
          </h2>
          <p className="text-gray-400 text-sm mt-1">
            {usuario?.perfil?.nombre ?? 'Sin perfil asignado'} · <span className="text-gov-azul font-medium">{usuario?.codigo_usuario}</span>
          </p>
        </div>
        {puedeCaracterizar && (
          <button
            onClick={cargar}
            disabled={cargando}
            className="self-start sm:self-auto flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium text-gray-600 transition-all duration-200 active:scale-[0.97] disabled:opacity-50 hover:bg-white hover:shadow-soft"
            style={{
              background: 'rgba(255,255,255,0.6)',
              backdropFilter: 'blur(12px)',
              WebkitBackdropFilter: 'blur(12px)',
              border: '1px solid rgba(0,0,0,0.08)',
            }}
          >
            <RefreshCw size={14} className={cargando ? 'animate-spin' : ''} />
            Actualizar
          </button>
        )}
      </div>

      {/* Error métricas */}
      {error && <Alert variant="error" className="mb-6">{error}</Alert>}

      {/* Métricas — solo encuestadores */}
      {puedeCaracterizar && (
        cargando ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            {[1,2,3,4].map((i) => (
              <div
                key={i}
                className="rounded-2xl h-[88px] animate-pulse bg-gray-100"
                style={{ border: '1px solid rgba(0,0,0,0.04)' }}
              />
            ))}
          </div>
        ) : resumen ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <GlassCard icon={ClipboardCheck} label="Sesiones completadas"   valor={resumen.sesiones_completadas}   theme="green"  delay={0}   />
            <GlassCard icon={TrendingUp}     label="Sesiones en progreso"   valor={resumen.sesiones_en_progreso}   theme="blue"   delay={50}  />
            <GlassCard icon={Home}           label="Hogares caracterizados" valor={resumen.hogares_caracterizados} theme="orange" delay={100} />
            <GlassCard icon={Users}          label="Respuestas registradas" valor={resumen.respuestas_total}       theme="purple" delay={150} />
          </div>
        ) : null
      )}

      {/* CTA Supervisión — para roles sin métricas propias */}
      {!puedeCaracterizar && (
        <div
          className="rounded-2xl p-5 mb-8 flex items-center justify-between gap-4 animate-fade-in-up"
          style={{
            background: 'rgba(21,101,192,0.06)',
            border: '1px solid rgba(21,101,192,0.15)',
          }}
        >
          <div>
            <p className="text-sm font-semibold text-gov-azul">Ver estadísticas del equipo</p>
            <p className="text-xs text-gray-500 mt-0.5">Las métricas agregadas de todos los encuestadores están disponibles en el módulo de Supervisión.</p>
          </div>
          <button
            onClick={() => navigate('/supervision')}
            className="shrink-0 flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold text-gov-azul border border-gov-azul/30 hover:bg-gov-azul hover:text-white transition-all duration-200 active:scale-[0.97]"
          >
            Ir a Supervisión
            <ArrowRight size={14} />
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">

        {/* Tarjeta de contexto del rol */}
        <div
          className="lg:col-span-2 rounded-3xl p-6 flex flex-col gap-4 animate-fade-in-up"
          style={{
            background: rolInfo.accentBg,
            border: `1px solid ${rolInfo.accentBorder}`,
            animationDelay: '50ms',
            animationFillMode: 'both',
          }}
        >
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full shrink-0" style={{ background: rolInfo.dotColor }} />
            <p className="text-xs font-semibold uppercase tracking-widest" style={{ color: rolInfo.accentText }}>
              Tu perfil
            </p>
          </div>
          <div>
            <p className="font-display font-bold text-gray-800 text-base leading-snug">{rolInfo.label}</p>
            <p className="text-sm text-gray-500 mt-2 leading-relaxed">{rolInfo.descripcion}</p>
          </div>

          {/* Actividad reciente — solo para encuestadores */}
          {puedeCaracterizar && (
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-400 mb-3">Tu actividad reciente</p>
              {cargando ? (
                <div className="space-y-2">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="h-8 rounded-lg animate-pulse bg-white/50" />
                  ))}
                </div>
              ) : resumen ? (
                <div className="space-y-2">
                  <div
                    className="flex items-center gap-3 rounded-xl px-3 py-2.5"
                    style={{ background: 'rgba(255,255,255,0.6)', border: `1px solid ${rolInfo.accentBorder}` }}
                  >
                    <Loader2 size={15} className="shrink-0" style={{ color: rolInfo.accentText }} />
                    <span className="text-sm text-gray-600 flex-1">En curso</span>
                    <span className="font-display font-bold text-gray-800 text-base">{resumen.sesiones_en_progreso}</span>
                    <span className="text-xs text-gray-400">sesiones</span>
                  </div>
                  <div
                    className="flex items-center gap-3 rounded-xl px-3 py-2.5"
                    style={{ background: 'rgba(255,255,255,0.6)', border: `1px solid ${rolInfo.accentBorder}` }}
                  >
                    <CheckCircle2 size={15} className="shrink-0 text-gov-verde" />
                    <span className="text-sm text-gray-600 flex-1">Completadas</span>
                    <span className="font-display font-bold text-gray-800 text-base">{resumen.sesiones_completadas}</span>
                    <span className="text-xs text-gray-400">sesiones</span>
                  </div>
                  <div
                    className="flex items-center gap-3 rounded-xl px-3 py-2.5"
                    style={{ background: 'rgba(255,255,255,0.6)', border: `1px solid ${rolInfo.accentBorder}` }}
                  >
                    <Home size={15} className="shrink-0" style={{ color: rolInfo.accentText }} />
                    <span className="text-sm text-gray-600 flex-1">Hogares</span>
                    <span className="font-display font-bold text-gray-800 text-base">{resumen.hogares_caracterizados}</span>
                    <span className="text-xs text-gray-400">caracterizados</span>
                  </div>
                </div>
              ) : null}
            </div>
          )}
        </div>

        {/* Accesos rápidos */}
        <div
          className="lg:col-span-3 rounded-3xl p-6 animate-fade-in-up"
          style={{
            background: 'rgba(255,255,255,0.5)',
            backdropFilter: 'blur(40px) saturate(1.4)',
            WebkitBackdropFilter: 'blur(40px) saturate(1.4)',
            border: '1px solid rgba(0,0,0,0.06)',
            boxShadow: '0 2px 12px rgba(0,0,0,0.04), inset 0 1px 0 rgba(255,255,255,0.8)',
            animationDelay: '100ms',
            animationFillMode: 'both',
          }}
        >
          <h3 className="font-display font-semibold text-gray-700 mb-4">
            Accesos rápidos
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {links.map(({ label, to, icon }) => (
              <QuickLink key={to} label={label} to={to} icon={icon} onClick={(p) => navigate(p)} />
            ))}
          </div>
          <p className="text-[11px] text-gray-400 mt-4">
            Sistema protegido bajo Ley 1581 de 2012
          </p>
        </div>

      </div>
    </div>
  );
}
