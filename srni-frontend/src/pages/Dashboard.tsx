/**
 * Dashboard — métricas principales del encuestador (liquid glass sobre fondo claro)
 */
import { useEffect, useState } from 'react';
import {
  Home, ClipboardCheck, Users, TrendingUp, RefreshCw,
  ArrowRight, type LucideIcon,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { reportesApi, type ResumenEncuestador } from '@/api/reportes';
import { useAuthStore } from '@/stores/authStore';
import Alert from '@/components/ui/Alert';

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
function QuickLink({ label, to, onClick }: { label: string; to: string; onClick: (to: string) => void }) {
  return (
    <button
      onClick={() => onClick(to)}
      className="flex items-center justify-between rounded-xl px-4 py-3.5 text-sm font-medium text-gray-700 transition-all duration-200 group hover:bg-white/80 hover:shadow-soft active:scale-[0.98]"
      style={{
        background: 'rgba(255,255,255,0.5)',
        backdropFilter: 'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)',
        border: '1px solid rgba(0,0,0,0.06)',
      }}
    >
      {label}
      <ArrowRight size={14} className="text-gray-400 group-hover:text-gov-azul transition-colors" />
    </button>
  );
}

export default function DashboardPage() {
  const { usuario } = useAuthStore();
  const navigate = useNavigate();
  const [resumen, setResumen] = useState<ResumenEncuestador | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState('');

  async function cargar() {
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
      </div>

      {/* Error */}
      {error && <Alert variant="error" className="mb-6">{error}</Alert>}

      {/* Métricas */}
      {cargando ? (
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
          <GlassCard icon={ClipboardCheck} label="Sesiones completadas"   valor={resumen.sesiones_completadas}   theme="green"  delay={0} />
          <GlassCard icon={TrendingUp}     label="Sesiones en progreso"   valor={resumen.sesiones_en_progreso}   theme="blue"   delay={50} />
          <GlassCard icon={Home}           label="Hogares caracterizados" valor={resumen.hogares_caracterizados} theme="orange" delay={100} />
          <GlassCard icon={Users}          label="Respuestas registradas" valor={resumen.respuestas_total}       theme="purple" delay={150} />
        </div>
      ) : null}

      {/* Accesos rápidos */}
      <div
        className="rounded-3xl p-6 animate-fade-in-up"
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
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <QuickLink label="Hogares"   to="/hogares"   onClick={(to) => navigate(to)} />
          <QuickLink label="Encuestas" to="/encuestas" onClick={(to) => navigate(to)} />
          <QuickLink label="Reportes"  to="/reportes"  onClick={(to) => navigate(to)} />
        </div>
        <p className="text-[11px] text-gray-400 mt-4">
          Sistema protegido bajo Ley 1581 de 2012
        </p>
      </div>
    </div>
  );
}
