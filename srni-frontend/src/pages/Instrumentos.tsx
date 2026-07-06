/**
 * Instrumentos — grid de cards con drill-down a detalle
 */
import { useEffect, useState } from 'react';
import { FileText, ChevronDown, ChevronRight, BookOpen, HelpCircle, ArrowLeft } from 'lucide-react';
import {
  formularioApi,
  type Instrumento,
  type CapituloResumen,
  type CapituloDetalle,
} from '@/api/formulario';
import PageHeader from '@/components/ui/PageHeader';
import Badge from '@/components/ui/Badge';
import Spinner from '@/components/ui/Spinner';
import Alert from '@/components/ui/Alert';
import EmptyState from '@/components/ui/EmptyState';
import Button from '@/components/ui/Button';

const TIPO_BADGE: Record<string, string> = {
  TEXTO:          'Texto',
  TEXTO_LARGO:    'Texto largo',
  NUMERICO:       'Numérico',
  FECHA:          'Fecha',
  BOOLEAN:        'Sí / No',
  RADIO:          'Opción única',
  LISTA:          'Lista',
  LISTA_MULTIPLE: 'Múltiple',
  COMBO_DINAMICO: 'Dinámico',
};

/* Colores de acento por instrumento (rotación) */
const ACCENTS = [
  { bar: '#1565C0', bg: 'rgba(21,101,192,0.05)',  border: 'rgba(21,101,192,0.12)' },
  { bar: '#2E7D32', bg: 'rgba(46,125,50,0.05)',   border: 'rgba(46,125,50,0.12)'  },
  { bar: '#E65100', bg: 'rgba(230,81,0,0.05)',     border: 'rgba(230,81,0,0.12)'   },
  { bar: '#7C3AED', bg: 'rgba(124,58,237,0.05)',   border: 'rgba(124,58,237,0.12)' },
  { bar: '#C62828', bg: 'rgba(198,40,40,0.05)',    border: 'rgba(198,40,40,0.12)'  },
  { bar: '#0277BD', bg: 'rgba(2,119,189,0.05)',    border: 'rgba(2,119,189,0.12)'  },
  { bar: '#F9A825', bg: 'rgba(249,168,37,0.05)',   border: 'rgba(249,168,37,0.12)' },
  { bar: '#4527A0', bg: 'rgba(69,39,160,0.05)',    border: 'rgba(69,39,160,0.12)'  },
];

export default function InstrumentosPage() {
  const [instrumentos, setInstrumentos] = useState<Instrumento[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState('');
  const [seleccionado, setSeleccionado] = useState<string | null>(null);

  useEffect(() => {
    formularioApi.instrumentos()
      .then(({ data }) => setInstrumentos(data.results))
      .catch(() => setError('No se pudieron cargar los instrumentos.'))
      .finally(() => setCargando(false));
  }, []);

  const instActual = instrumentos.find((i) => i.id === seleccionado) ?? null;
  const accentIdx = instActual ? instrumentos.indexOf(instActual) : 0;

  // ── Vista detalle ──
  if (instActual) {
    return (
      <div className="p-4 sm:p-6 max-w-5xl mx-auto animate-fade-in">
        <button
          onClick={() => setSeleccionado(null)}
          className="inline-flex items-center gap-1.5 text-sm font-medium text-gov-azul hover:text-gov-azulOscuro transition-colors mb-4"
        >
          <ArrowLeft size={15} />
          Todos los instrumentos
        </button>

        <InstrumentoDetalle
          instrumento={instActual}
          accent={ACCENTS[accentIdx % ACCENTS.length]}
        />
      </div>
    );
  }

  // ── Vista grilla ──
  return (
    <div className="p-4 sm:p-6 max-w-5xl mx-auto">
      <PageHeader
        titulo="Instrumentos"
        subtitulo={cargando ? 'Cargando…' : `${instrumentos.length} formularios de caracterización`}
      />

      {error && <Alert variant="error" className="mb-4">{error}</Alert>}

      {cargando ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
            <div key={i} className="rounded-2xl h-40 animate-pulse bg-gray-100" />
          ))}
        </div>
      ) : instrumentos.length === 0 ? (
        <EmptyState
          icon={FileText}
          titulo="No hay instrumentos cargados"
          descripcion="Los instrumentos aparecerán aquí cuando se configuren en el backend."
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          {instrumentos.map((inst, idx) => (
            <InstrumentoCard
              key={inst.id}
              instrumento={inst}
              accent={ACCENTS[idx % ACCENTS.length]}
              delay={idx * 40}
              onClick={() => setSeleccionado(inst.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ── Card de instrumento ───────────────────────────────────────────────────────

function InstrumentoCard({
  instrumento: inst,
  accent,
  delay,
  onClick,
}: {
  instrumento: Instrumento;
  accent: typeof ACCENTS[number];
  delay: number;
  onClick: () => void;
}) {
  const totalPreguntas = inst.capitulos.reduce((s, c) => s + c.total_preguntas, 0);

  return (
    <button
      onClick={onClick}
      className="card p-0 overflow-hidden text-left group hover:-translate-y-1 hover:shadow-soft-md transition-all duration-200 active:scale-[0.98] animate-fade-in-up"
      style={{ animationDelay: `${delay}ms`, animationFillMode: 'both' }}
    >
      <div className="p-4 flex flex-col gap-3">
        {/* Nombre */}
        <div>
          <p className="font-display font-bold text-gray-800 text-sm leading-snug group-hover:text-gov-azul transition-colors">
            {inst.nombre}
          </p>
          <p className="text-[11px] text-gray-400 font-mono mt-1">
            {inst.codigo} · v{inst.version}
          </p>
        </div>

        {/* Stats */}
        <div className="flex items-center gap-1 text-xs text-gray-500">
          <span className="px-2 py-0.5 rounded-md bg-gray-50 border border-gray-100">
            {inst.total_capitulos} capítulos
          </span>
          <span className="px-2 py-0.5 rounded-md bg-gray-50 border border-gray-100">
            {totalPreguntas} preguntas
          </span>
        </div>

        {/* Vigencia */}
        <div className="flex items-center justify-between mt-auto">
          <Badge variant={inst.vigente ? 'verde' : 'gris'}>
            {inst.vigente ? 'Vigente' : 'No vigente'}
          </Badge>
          <span className="text-[10px] text-gray-400">
            v. {new Date(inst.vigente_desde).getFullYear()}
          </span>
        </div>
      </div>
    </button>
  );
}

// ── Detalle del instrumento ───────────────────────────────────────────────────

function InstrumentoDetalle({
  instrumento: inst,
  accent,
}: {
  instrumento: Instrumento;
  accent: typeof ACCENTS[number];
}) {
  const totalPreguntas = inst.capitulos.reduce((s, c) => s + c.total_preguntas, 0);

  return (
    <div>
      {/* Encabezado */}
      <div
        className="rounded-2xl p-5 mb-4"
        style={{ background: accent.bg, border: `1px solid ${accent.border}` }}
      >
        <div className="flex items-start justify-between gap-3 flex-wrap">
          <div>
            <h2 className="font-display font-bold text-gray-800 text-lg leading-snug">{inst.nombre}</h2>
            <p className="text-xs text-gray-500 mt-1.5">
              <span className="font-mono">{inst.codigo}</span>
              {' · v'}{inst.version}
              {' · Vigente desde '}
              {new Date(inst.vigente_desde).toLocaleDateString('es-CO', { year: 'numeric', month: 'long' })}
            </p>
          </div>
          <Badge variant={inst.vigente ? 'verde' : 'gris'} className="shrink-0">
            {inst.vigente ? 'Vigente' : 'No vigente'}
          </Badge>
        </div>

        {/* Métricas rápidas */}
        <div className="flex items-center gap-3 mt-4">
          <div className="flex items-center gap-1.5 text-xs text-gray-600 bg-white/70 rounded-lg px-3 py-1.5" style={{ border: `1px solid ${accent.border}` }}>
            <BookOpen size={13} style={{ color: accent.bar }} />
            <span className="font-semibold">{inst.total_capitulos}</span> capítulos
          </div>
          <div className="flex items-center gap-1.5 text-xs text-gray-600 bg-white/70 rounded-lg px-3 py-1.5" style={{ border: `1px solid ${accent.border}` }}>
            <FileText size={13} style={{ color: accent.bar }} />
            <span className="font-semibold">{totalPreguntas}</span> preguntas
          </div>
        </div>

        {inst.fuente_documental && (
          <p className="text-[11px] text-gray-400 mt-3 truncate" title={inst.fuente_documental}>
            Fuente: {inst.fuente_documental}
          </p>
        )}
      </div>

      {/* Capítulos */}
      {inst.capitulos.length === 0 ? (
        <EmptyState
          icon={BookOpen}
          titulo="Sin capítulos"
          descripcion="Este instrumento no tiene capítulos configurados."
        />
      ) : (
        <div className="card p-0 overflow-hidden">
          <div className="divide-y divide-gov-borde">
            {inst.capitulos.map((cap, i) => (
              <CapituloRow key={cap.id} capitulo={cap} defaultOpen={i === 0} accent={accent} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Capítulo expandible ───────────────────────────────────────────────────────

function CapituloRow({
  capitulo,
  defaultOpen,
  accent,
}: {
  capitulo: CapituloResumen;
  defaultOpen?: boolean;
  accent: typeof ACCENTS[number];
}) {
  const [expandido, setExpandido] = useState(defaultOpen ?? false);
  const [detalle,   setDetalle]   = useState<CapituloDetalle | null>(null);
  const [cargando,  setCargando]  = useState(false);

  async function toggle() {
    if (expandido) { setExpandido(false); return; }
    if (!detalle) {
      setCargando(true);
      try {
        const { data } = await formularioApi.capituloDetalle(capitulo.id);
        setDetalle(data);
      } catch {
        // silencioso
      } finally {
        setCargando(false);
      }
    }
    setExpandido(true);
  }

  // Abrir automáticamente si defaultOpen y no cargado aún
  useEffect(() => {
    if (defaultOpen && !detalle) {
      setCargando(true);
      formularioApi.capituloDetalle(capitulo.id)
        .then(({ data }) => setDetalle(data))
        .catch(() => {})
        .finally(() => setCargando(false));
    }
  }, []);

  return (
    <div>
      <button
        onClick={toggle}
        className="w-full flex items-center gap-3 px-5 py-3.5 text-left hover:bg-gray-50/80 transition-colors duration-150 group"
      >
        <div
          className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0"
          style={{ background: accent.bg, border: `1px solid ${accent.border}` }}
        >
          <BookOpen size={14} style={{ color: accent.bar }} />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm text-gray-800 font-medium truncate">
            <span className="font-mono text-[11px] mr-1.5" style={{ color: accent.bar }}>{capitulo.codigo}</span>
            {capitulo.nombre}
          </p>
        </div>
        <span className="text-xs text-gray-400 shrink-0 hidden sm:block">{capitulo.total_preguntas} preguntas</span>
        {cargando ? (
          <Spinner size="sm" />
        ) : (
          <ChevronDown
            size={15}
            className={`text-gray-400 shrink-0 transition-transform duration-200 ${expandido ? 'rotate-0' : '-rotate-90'}`}
          />
        )}
      </button>

      {expandido && detalle && (
        <div className="border-t border-gov-borde/50 animate-fade-in">
          {detalle.objetivo && (
            <div className="px-5 py-2.5 text-xs text-gray-500 bg-gray-50/50 border-b border-gov-borde/40 italic">
              {detalle.objetivo}
            </div>
          )}
          {detalle.preguntas.length === 0 ? (
            <p className="px-5 py-6 text-xs text-gray-400 text-center">Sin preguntas</p>
          ) : (
            <div>
              {detalle.preguntas.map((p, i) => (
                <div
                  key={p.id}
                  className={`flex items-start gap-3 px-5 py-3 ${i < detalle.preguntas.length - 1 ? 'border-b border-gov-borde/20' : ''}`}
                >
                  {/* Dot: naranja = obligatoria, gris = opcional */}
                  <span
                    className={`w-2 h-2 rounded-full shrink-0 mt-1.5 ${p.obligatoria ? 'bg-gov-naranja' : 'bg-gray-200'}`}
                    title={p.obligatoria ? 'Obligatoria' : 'Opcional'}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap mb-1">
                      <span className="font-mono text-xs" style={{ color: accent.bar }}>{p.no_pregunta}</span>
                      <Badge variant="gris">{TIPO_BADGE[p.tipo] ?? p.tipo}</Badge>
                      <Badge variant={p.nivel === 'HOGAR' ? 'azul' : 'naranja'}>
                        {p.nivel === 'HOGAR' ? 'Hogar' : 'Persona'}
                      </Badge>
                      {!p.activa && <Badge variant="rojo">Inactiva</Badge>}
                    </div>
                    <p className="text-sm text-gray-700 leading-snug">{p.texto}</p>
                    {p.descripcion_ayuda && (
                      <p className="flex items-start gap-1 text-xs text-gray-400 mt-1">
                        <HelpCircle size={10} className="shrink-0 mt-0.5" />
                        {p.descripcion_ayuda}
                      </p>
                    )}
                    {p.opciones.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1.5">
                        {p.opciones.slice(0, 6).map((o) => (
                          <span key={o.id} className="text-xs bg-gray-50 border border-gray-100 rounded-md px-1.5 py-0.5 text-gray-500">
                            {o.etiqueta}
                          </span>
                        ))}
                        {p.opciones.length > 6 && (
                          <span className="text-xs text-gray-400 self-center">+{p.opciones.length - 6} más</span>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
