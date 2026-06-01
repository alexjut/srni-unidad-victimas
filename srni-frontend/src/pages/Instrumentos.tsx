/**
 * Instrumentos — lista de formularios + árbol de capítulos y preguntas (solo lectura)
 */
import { useEffect, useState } from 'react';
import {
  FileText, ChevronDown, ChevronRight, BookOpen, HelpCircle,
  CheckCircle, Circle, List,
} from 'lucide-react';
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

const TIPO_BADGE: Record<string, string> = {
  TEXTO: 'Texto',
  TEXTO_LARGO: 'Texto largo',
  NUMERICO: 'Numérico',
  FECHA: 'Fecha',
  BOOLEAN: 'Sí/No',
  RADIO: 'Opción única',
  LISTA: 'Lista',
  LISTA_MULTIPLE: 'Múltiple',
  COMBO_DINAMICO: 'Dinámico',
};

export default function InstrumentosPage() {
  const [instrumentos, setInstrumentos] = useState<Instrumento[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState('');

  // Instrumento expandido
  const [expandido, setExpandido] = useState<string | null>(null);

  useEffect(() => {
    formularioApi.instrumentos()
      .then(({ data }) => setInstrumentos(data.results))
      .catch(() => setError('No se pudieron cargar los instrumentos.'))
      .finally(() => setCargando(false));
  }, []);

  function toggleInstrumento(id: string) {
    setExpandido(expandido === id ? null : id);
  }

  return (
    <div className="p-4 sm:p-6 max-w-5xl mx-auto">
      <PageHeader
        titulo="Instrumentos"
        subtitulo={`${instrumentos.length} formulario(s) de caracterización`}
      />

      {error && <Alert variant="error" className="mb-4">{error}</Alert>}

      {cargando ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="card animate-pulse h-20 bg-gray-100" />
          ))}
        </div>
      ) : instrumentos.length === 0 ? (
        <EmptyState
          icon={FileText}
          titulo="No hay instrumentos cargados"
          descripcion="Los instrumentos aparecerán aquí cuando se configuren en el backend."
        />
      ) : (
        <div className="space-y-3">
          {instrumentos.map((inst) => (
            <InstrumentoCard
              key={inst.id}
              instrumento={inst}
              expandido={expandido === inst.id}
              onToggle={() => toggleInstrumento(inst.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// --- Card de instrumento ---

function InstrumentoCard({
  instrumento,
  expandido,
  onToggle,
}: {
  instrumento: Instrumento;
  expandido: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="card p-0 overflow-hidden">
      {/* Header clickeable */}
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-4 px-4 py-4 text-left hover:bg-gray-50 transition-colors"
      >
        <div className="w-10 h-10 rounded-lg bg-gov-azulTenue flex items-center justify-center shrink-0">
          <FileText size={20} className="text-gov-azul" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-gray-800 truncate">{instrumento.nombre}</p>
          <p className="text-xs text-gray-500">
            {instrumento.codigo} · v{instrumento.version} · {instrumento.total_capitulos} capítulo(s)
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <Badge variant={instrumento.vigente ? 'verde' : 'gris'}>
            {instrumento.vigente ? 'Vigente' : 'No vigente'}
          </Badge>
          {expandido ? <ChevronDown size={18} className="text-gray-400" /> : <ChevronRight size={18} className="text-gray-400" />}
        </div>
      </button>

      {/* Capítulos expandidos */}
      {expandido && (
        <div className="border-t border-gov-borde">
          {/* Info del instrumento */}
          <div className="px-4 py-3 bg-gray-50 text-xs text-gray-500 flex flex-wrap gap-x-6 gap-y-1">
            <span>Vigente desde: <strong className="text-gray-700">{new Date(instrumento.vigente_desde).toLocaleDateString('es-CO')}</strong></span>
            {instrumento.vigente_hasta && (
              <span>Hasta: <strong className="text-gray-700">{new Date(instrumento.vigente_hasta).toLocaleDateString('es-CO')}</strong></span>
            )}
            {instrumento.fuente_documental && (
              <span>Fuente: <strong className="text-gray-700">{instrumento.fuente_documental}</strong></span>
            )}
          </div>

          {/* Lista de capítulos */}
          {instrumento.capitulos.length === 0 ? (
            <div className="px-4 py-6 text-center text-sm text-gray-400">
              Sin capítulos configurados
            </div>
          ) : (
            <div className="divide-y divide-gov-borde">
              {instrumento.capitulos.map((cap) => (
                <CapituloRow key={cap.id} capitulo={cap} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// --- Fila de capítulo (expandible a preguntas) ---

function CapituloRow({ capitulo }: { capitulo: CapituloResumen }) {
  const [expandido, setExpandido] = useState(false);
  const [detalle, setDetalle] = useState<CapituloDetalle | null>(null);
  const [cargando, setCargando] = useState(false);

  async function toggle() {
    if (expandido) {
      setExpandido(false);
      return;
    }

    // Cargar preguntas si no las tenemos
    if (!detalle) {
      setCargando(true);
      try {
        const { data } = await formularioApi.capituloDetalle(capitulo.id);
        setDetalle(data);
      } catch {
        // silencioso — mostrará vacío
      } finally {
        setCargando(false);
      }
    }
    setExpandido(true);
  }

  return (
    <div>
      <button
        onClick={toggle}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-gov-azulTenue/20 transition-colors"
      >
        <BookOpen size={16} className="text-gov-azul shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="text-sm text-gray-700">
            <span className="font-mono text-xs text-gov-azul mr-1.5">{capitulo.codigo}</span>
            {capitulo.nombre}
          </p>
        </div>
        <span className="text-xs text-gray-400 shrink-0">{capitulo.total_preguntas} preg.</span>
        {cargando ? (
          <Spinner size="sm" />
        ) : expandido ? (
          <ChevronDown size={16} className="text-gray-400" />
        ) : (
          <ChevronRight size={16} className="text-gray-400" />
        )}
      </button>

      {/* Preguntas */}
      {expandido && detalle && (
        <div className="bg-gray-50 border-t border-gov-borde">
          {detalle.objetivo && (
            <p className="px-4 py-2 text-xs text-gray-500 italic border-b border-gov-borde">
              {detalle.objetivo}
            </p>
          )}
          {detalle.preguntas.length === 0 ? (
            <p className="px-4 py-4 text-xs text-gray-400 text-center">Sin preguntas</p>
          ) : (
            <div className="divide-y divide-gray-200">
              {detalle.preguntas.map((p) => (
                <div key={p.id} className="px-4 py-2.5 flex items-start gap-3">
                  <div className="shrink-0 mt-0.5">
                    {p.obligatoria ? (
                      <CheckCircle size={14} className="text-gov-verde" />
                    ) : (
                      <Circle size={14} className="text-gray-300" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="font-mono text-xs text-gov-azul">{p.no_pregunta}</span>
                      <Badge variant="gris">{TIPO_BADGE[p.tipo] ?? p.tipo}</Badge>
                      <Badge variant={p.nivel === 'HOGAR' ? 'azul' : 'naranja'}>
                        {p.nivel === 'HOGAR' ? 'Hogar' : 'Persona'}
                      </Badge>
                      {!p.activa && <Badge variant="rojo">Inactiva</Badge>}
                    </div>
                    <p className="text-sm text-gray-700 leading-snug">{p.texto}</p>
                    {p.descripcion_ayuda && (
                      <p className="text-xs text-gray-400 mt-0.5 flex items-start gap-1">
                        <HelpCircle size={10} className="shrink-0 mt-0.5" />
                        {p.descripcion_ayuda}
                      </p>
                    )}
                    {p.opciones.length > 0 && (
                      <div className="mt-1.5 flex flex-wrap gap-1">
                        {p.opciones.slice(0, 6).map((o) => (
                          <span key={o.id} className="text-xs bg-white border border-gray-200 rounded px-1.5 py-0.5 text-gray-600">
                            {o.etiqueta}
                          </span>
                        ))}
                        {p.opciones.length > 6 && (
                          <span className="text-xs text-gray-400">+{p.opciones.length - 6} más</span>
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
