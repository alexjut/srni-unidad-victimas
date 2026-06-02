/**
 * Búsqueda de víctimas — consulta al RNI por tipo y número de documento
 */
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search, User, MapPin, Shield, Eye, Clock, Lock, FileText, Home,
  Calendar, X,
} from 'lucide-react';
import {
  victimasApi,
  tiposDocumentoApi,
  type VictimaResumen,
  type TipoDocumento,
} from '@/api/victimas';
import PageHeader from '@/components/ui/PageHeader';
import Button from '@/components/ui/Button';
import Alert from '@/components/ui/Alert';
import Badge from '@/components/ui/Badge';

const GENERO_LABEL: Record<string, string> = {
  M: 'Masculino',
  F: 'Femenino',
  NB: 'No binario',
  ND: 'No definido',
};

const ESTADO_RUV_BADGE: Record<string, { variant: 'verde' | 'azul' | 'naranja' | 'rojo' | 'gris'; label: string }> = {
  INCLUIDO:    { variant: 'verde',   label: 'Incluido en RUV' },
  NO_INCLUIDO: { variant: 'gris',    label: 'No incluido' },
  EN_PROCESO:  { variant: 'naranja', label: 'En proceso' },
  EXCLUIDO:    { variant: 'rojo',    label: 'Excluido' },
};

const ETNIA_LABEL: Record<string, string> = {
  NINGUNA: 'Ninguna',
  INDIGENA: 'Indígena',
  AFROCOLOMBIANO: 'Afrocolombiano',
  ROM: 'Rom',
  RAIZAL: 'Raizal',
  PALENQUERO: 'Palenquero',
};

// --- Búsquedas recientes en sessionStorage ---

interface BusquedaReciente {
  tipoDoc: string;
  numDoc: string;
  nombre: string;
  estado_ruv: string;
  victima_id: string;
  fecha: string;
}

const STORAGE_KEY = 'srni_busquedas_recientes';
const MAX_RECIENTES = 5;

function getRecientes(): BusquedaReciente[] {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function guardarReciente(item: BusquedaReciente) {
  const recientes = getRecientes().filter(
    (r) => !(r.tipoDoc === item.tipoDoc && r.numDoc === item.numDoc)
  );
  recientes.unshift(item);
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(recientes.slice(0, MAX_RECIENTES)));
}

function limpiarRecientes() {
  sessionStorage.removeItem(STORAGE_KEY);
}

// --- Componente principal ---

export default function VictimasPage() {
  const navigate = useNavigate();

  // Tipos de documento
  const [tiposDoc, setTiposDoc] = useState<TipoDocumento[]>([]);
  const [cargandoTipos, setCargandoTipos] = useState(true);

  // Formulario
  const [tipoDoc, setTipoDoc] = useState('');
  const [numDoc, setNumDoc] = useState('');

  // Resultado
  const [buscando, setBuscando] = useState(false);
  const [resultado, setResultado] = useState<VictimaResumen | null>(null);
  const [noEncontrada, setNoEncontrada] = useState(false);
  const [error, setError] = useState('');
  const [buscado, setBuscado] = useState(false);

  // Recientes
  const [recientes, setRecientes] = useState<BusquedaReciente[]>(getRecientes());

  useEffect(() => {
    tiposDocumentoApi.listar()
      .then(({ data }) => {
        setTiposDoc(data.results);
        if (data.results.length > 0) setTipoDoc(data.results[0].codigo);
      })
      .catch(() => setError('No se pudieron cargar los tipos de documento.'))
      .finally(() => setCargandoTipos(false));
  }, []);

  async function handleBuscar(e: React.FormEvent) {
    e.preventDefault();
    if (!tipoDoc || !numDoc.trim()) {
      setError('Seleccione un tipo de documento e ingrese el número.');
      return;
    }

    setBuscando(true);
    setError('');
    setResultado(null);
    setNoEncontrada(false);
    setBuscado(true);

    try {
      const { data } = await victimasApi.buscar(tipoDoc, numDoc.trim());
      setResultado(data);

      // Guardar en recientes
      guardarReciente({
        tipoDoc,
        numDoc: numDoc.trim(),
        nombre: `${tipoDoc} ${numDoc.trim()}`,
        estado_ruv: data.estado_ruv,
        victima_id: data.id,
        fecha: new Date().toISOString(),
      });
      setRecientes(getRecientes());
    } catch (err: any) {
      if (err?.response?.status === 404) {
        setNoEncontrada(true);
      } else if (err?.response?.status === 403) {
        setError('No tiene permisos para buscar en el RNI.');
      } else {
        setError('Error al buscar. Verifique la conexión e intente de nuevo.');
      }
    } finally {
      setBuscando(false);
    }
  }

  function buscarReciente(item: BusquedaReciente) {
    setTipoDoc(item.tipoDoc);
    setNumDoc(item.numDoc);
    // Submit programático
    setTimeout(() => {
      const form = document.getElementById('form-busqueda') as HTMLFormElement;
      form?.requestSubmit();
    }, 0);
  }

  function limpiar() {
    setNumDoc('');
    setResultado(null);
    setNoEncontrada(false);
    setError('');
    setBuscado(false);
  }

  function handleLimpiarRecientes() {
    limpiarRecientes();
    setRecientes([]);
  }

  const ruvInfo = resultado ? ESTADO_RUV_BADGE[resultado.estado_ruv] : null;

  return (
    <div className="p-4 sm:p-6 max-w-4xl mx-auto">
      <PageHeader
        titulo="Búsqueda de víctimas"
        subtitulo="Consulta al Registro Nacional de Información"
      />

      {/* Formulario de búsqueda */}
      <div className="card mb-6">
        <form id="form-busqueda" onSubmit={handleBuscar} className="flex flex-col sm:flex-row gap-3">
          <div className="min-w-0 sm:w-56 sm:shrink-0">
            <label htmlFor="tipo-documento" className="block text-xs font-semibold text-gray-600 uppercase tracking-wide mb-1">
              Tipo documento
            </label>
            <select
              id="tipo-documento"
              value={tipoDoc}
              onChange={(e) => setTipoDoc(e.target.value)}
              className="input"
              disabled={cargandoTipos || buscando}
            >
              {cargandoTipos ? (
                <option>Cargando...</option>
              ) : (
                tiposDoc.map((t) => (
                  <option key={t.codigo} value={t.codigo} title={t.nombre}>
                    {t.codigo} — {t.nombre}
                  </option>
                ))
              )}
            </select>
          </div>

          <div className="flex-1">
            <label className="block text-xs font-semibold text-gray-600 uppercase tracking-wide mb-1">
              Número de documento
            </label>
            <input
              type="text"
              value={numDoc}
              onChange={(e) => setNumDoc(e.target.value)}
              placeholder="Ingrese el número de documento"
              className="input font-mono"
              disabled={buscando}
            />
          </div>

          <div className="flex items-end gap-2">
            <Button type="submit" icon={Search} loading={buscando}>
              Buscar
            </Button>
            {buscado && (
              <Button variant="ghost" onClick={limpiar} type="button">
                Limpiar
              </Button>
            )}
          </div>
        </form>
      </div>

      {/* Error */}
      {error && <Alert variant="error" className="mb-4">{error}</Alert>}

      {/* No encontrada */}
      {noEncontrada && (
        <Alert variant="warning" className="mb-4">
          No se encontró ninguna víctima con ese documento. Verifique los datos e intente de nuevo.
        </Alert>
      )}

      {/* Resultado */}
      {resultado && <ResultadoCard resultado={resultado} navigate={navigate} />}

      {/* Estado inicial (sin búsqueda activa) */}
      {!buscado && !error && (
        <>
          {/* Búsquedas recientes */}
          {recientes.length > 0 && (
            <div className="mb-6">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
                  <Clock size={16} className="text-gray-400" />
                  Búsquedas recientes
                </h3>
                <button
                  onClick={handleLimpiarRecientes}
                  className="text-xs text-gray-400 hover:text-gray-600 flex items-center gap-1 transition-all"
                >
                  <X size={12} /> Limpiar historial
                </button>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {recientes.map((r, i) => {
                  const ruv = ESTADO_RUV_BADGE[r.estado_ruv];
                  return (
                    <button
                      key={i}
                      onClick={() => buscarReciente(r)}
                      className="card text-left hover:border-gov-azul hover:shadow-soft-md transition-all group"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-mono text-sm font-medium text-gov-azul group-hover:underline">
                          {r.tipoDoc} {r.numDoc}
                        </span>
                        {ruv && <Badge variant={ruv.variant}>{ruv.label}</Badge>}
                      </div>
                      <p className="text-xs text-gray-400">
                        {new Date(r.fecha).toLocaleDateString('es-CO', {
                          day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
                        })}
                      </p>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Tarjetas informativas */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <InfoCard
              icon={Search}
              titulo="Búsqueda segura"
              descripcion="El número de documento se transmite cifrado. La consulta usa hash SHA-256 para proteger la identidad."
            />
            <InfoCard
              icon={Lock}
              titulo="Datos protegidos"
              descripcion="La información personal está cifrada en base de datos y solo se descifra con autorización. Ley 1581 de 2012."
            />
            <InfoCard
              icon={FileText}
              titulo="Registro completo"
              descripcion="Consulte datos personales, estado RUV, hechos victimizantes, hogares y sesiones de caracterización."
            />
          </div>
        </>
      )}
    </div>
  );
}

// --- Resultado enriquecido ---

function ResultadoCard({
  resultado,
  navigate,
}: {
  resultado: VictimaResumen;
  navigate: ReturnType<typeof import('react-router-dom').useNavigate>;
}) {
  const ruvInfo = ESTADO_RUV_BADGE[resultado.estado_ruv];

  return (
    <div className="card mb-6 animate-fade-in-up">
      {/* Header del resultado */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 mb-5">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-full bg-gov-azul flex items-center justify-center">
            <User size={22} className="text-white" />
          </div>
          <div>
            <p className="text-sm text-gray-500">
              {resultado.tipo_documento_codigo} · Víctima registrada
            </p>
            <div className="flex flex-wrap items-center gap-2 mt-1">
              {ruvInfo && <Badge variant={ruvInfo.variant}>{ruvInfo.label}</Badge>}
              {resultado.discapacidad && <Badge variant="naranja">Discapacidad</Badge>}
              {resultado.es_victima_pruebas && <Badge variant="gris">Datos de prueba</Badge>}
            </div>
          </div>
        </div>
        <Button
          icon={Eye}
          size="sm"
          onClick={() => navigate(`/victimas/${resultado.id}`)}
        >
          Ver detalle completo
        </Button>
      </div>

      {/* Datos principales */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-5">
        <DatoCard
          icon={User}
          label="Género"
          valor={GENERO_LABEL[resultado.genero] ?? resultado.genero}
        />
        <DatoCard
          icon={Shield}
          label="Pertenencia étnica"
          valor={ETNIA_LABEL[resultado.pertenencia_etnica] ?? resultado.pertenencia_etnica.replace('_', ' ')}
        />
        <DatoCard
          icon={MapPin}
          label="Municipio"
          valor={resultado.municipio_residencia_nombre ?? '—'}
        />
        <DatoCard
          icon={Calendar}
          label="Registrado"
          valor={new Date(resultado.created_at).toLocaleDateString('es-CO')}
        />
      </div>

      {/* Departamento si existe */}
      {resultado.departamento_nombre && (
        <div className="flex items-center gap-2 text-sm text-gray-500 mb-4">
          <MapPin size={14} className="text-gray-400" />
          <span>Departamento: <strong className="text-gray-700">{resultado.departamento_nombre}</strong></span>
        </div>
      )}

      {/* Discapacidad detalle */}
      {resultado.discapacidad && resultado.tipo_discapacidad && (
        <div className="bg-gov-naranjaTenue border border-orange-200 rounded-2xl p-3 mb-4 text-sm text-gov-naranja">
          Tipo de discapacidad: {resultado.tipo_discapacidad}
        </div>
      )}

      {/* Hogar activo */}
      {resultado.hogar_activo && (
        <div className="border-t border-gov-borde pt-4">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3 flex items-center gap-1.5">
            <Home size={14} />
            Hogar activo
          </p>
          <div className="flex flex-col sm:flex-row sm:items-center gap-4">
            <div className="flex items-center gap-6 text-sm">
              <div>
                <span className="text-2xl font-display font-bold text-gray-800">{resultado.hogar_activo.total_miembros}</span>
                <p className="text-xs text-gray-500">miembros</p>
              </div>
              <div>
                <span className="text-2xl font-display font-bold text-gray-800">{resultado.hogar_activo.total_sesiones}</span>
                <p className="text-xs text-gray-500">sesiones</p>
              </div>
              <Badge variant={resultado.hogar_activo.estado === 'ACTIVO' ? 'verde' : 'gris'}>
                {resultado.hogar_activo.estado}
              </Badge>
            </div>
            <Button
              variant="secondary"
              size="sm"
              icon={Home}
              onClick={() => navigate(`/hogares/${resultado.hogar_activo!.id}`)}
            >
              Ir al hogar
            </Button>
          </div>
        </div>
      )}

      {/* Sin hogar */}
      {!resultado.hogar_activo && (
        <div className="border-t border-gov-borde pt-4">
          <p className="text-sm text-gray-400 flex items-center gap-2">
            <Home size={14} />
            Sin hogar activo asociado
          </p>
        </div>
      )}
    </div>
  );
}

// --- Componentes auxiliares ---

function DatoCard({ icon: Icon, label, valor }: {
  icon: React.ElementType;
  label: string;
  valor: string;
}) {
  return (
    <div className="bg-gray-50 rounded-xl p-3">
      <div className="flex items-center gap-1.5 mb-1">
        <Icon size={12} className="text-gray-400" />
        <span className="text-xs text-gray-500">{label}</span>
      </div>
      <p className="text-sm font-medium text-gray-800">{valor}</p>
    </div>
  );
}

function InfoCard({ icon: Icon, titulo, descripcion }: {
  icon: React.ElementType;
  titulo: string;
  descripcion: string;
}) {
  return (
    <div className="card text-center">
      <div className="w-10 h-10 rounded-full bg-gov-azulTenue flex items-center justify-center mx-auto mb-3">
        <Icon size={20} className="text-gov-azul" />
      </div>
      <h4 className="text-sm font-semibold text-gray-700 mb-1">{titulo}</h4>
      <p className="text-xs text-gray-500 leading-relaxed">{descripcion}</p>
    </div>
  );
}
