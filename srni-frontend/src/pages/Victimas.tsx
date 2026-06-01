/**
 * Búsqueda de víctimas — consulta al RNI por tipo y número de documento
 */
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, User, MapPin, Shield, Eye } from 'lucide-react';
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

  function limpiar() {
    setNumDoc('');
    setResultado(null);
    setNoEncontrada(false);
    setError('');
    setBuscado(false);
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
        <form onSubmit={handleBuscar} className="flex flex-col sm:flex-row gap-3">
          <div className="sm:w-48">
            <label className="block text-xs font-semibold text-gray-600 uppercase tracking-wide mb-1">
              Tipo documento
            </label>
            <select
              value={tipoDoc}
              onChange={(e) => setTipoDoc(e.target.value)}
              className="input"
              disabled={cargandoTipos || buscando}
            >
              {cargandoTipos ? (
                <option>Cargando...</option>
              ) : (
                tiposDoc.map((t) => (
                  <option key={t.codigo} value={t.codigo}>{t.codigo} — {t.nombre}</option>
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
      {resultado && (
        <div className="card">
          <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 mb-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-full bg-gov-azul flex items-center justify-center">
                <User size={22} className="text-white" />
              </div>
              <div>
                <p className="text-sm text-gray-500">
                  {resultado.tipo_documento_codigo} · Víctima registrada
                </p>
                <div className="flex items-center gap-2 mt-1">
                  {ruvInfo && (
                    <Badge variant={ruvInfo.variant}>{ruvInfo.label}</Badge>
                  )}
                  {resultado.discapacidad && (
                    <Badge variant="naranja">Discapacidad</Badge>
                  )}
                </div>
              </div>
            </div>
            <Button
              icon={Eye}
              size="sm"
              onClick={() => navigate(`/victimas/${resultado.id}`)}
            >
              Ver detalle
            </Button>
          </div>

          <dl className="grid grid-cols-2 sm:grid-cols-3 gap-x-6 gap-y-3 text-sm">
            <DatoItem
              icon={User}
              label="Género"
              valor={GENERO_LABEL[resultado.genero] ?? resultado.genero}
            />
            <DatoItem
              icon={Shield}
              label="Pertenencia étnica"
              valor={resultado.pertenencia_etnica.replace('_', ' ')}
            />
            <DatoItem
              icon={MapPin}
              label="Municipio residencia"
              valor={resultado.municipio_residencia_nombre
                ? `${resultado.municipio_residencia_nombre}${resultado.departamento_nombre ? `, ${resultado.departamento_nombre}` : ''}`
                : '—'}
            />
          </dl>

          {resultado.hogar_activo && (
            <div className="mt-4 pt-4 border-t border-gov-borde">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                Hogar activo
              </p>
              <div className="flex items-center gap-4 text-sm">
                <span className="text-gray-700">
                  <strong>{resultado.hogar_activo.total_miembros}</strong> miembros
                </span>
                <span className="text-gray-700">
                  <strong>{resultado.hogar_activo.total_sesiones}</strong> sesiones
                </span>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => navigate(`/hogares/${resultado.hogar_activo!.id}`)}
                >
                  Ir al hogar
                </Button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Estado inicial */}
      {!buscado && !error && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <div className="w-16 h-16 rounded-full bg-gray-100 flex items-center justify-center mb-4">
            <Search size={28} className="text-gray-400" />
          </div>
          <p className="text-sm font-medium text-gray-500">
            Ingrese el tipo y número de documento para buscar
          </p>
          <p className="text-xs text-gray-400 mt-1">
            La consulta se realiza de forma segura contra el Registro Nacional de Información
          </p>
        </div>
      )}
    </div>
  );
}

function DatoItem({ icon: Icon, label, valor }: {
  icon: React.ElementType;
  label: string;
  valor: string;
}) {
  return (
    <div className="flex items-start gap-2">
      <Icon size={14} className="text-gray-400 mt-0.5 shrink-0" />
      <div>
        <dt className="text-xs text-gray-500">{label}</dt>
        <dd className="text-gray-800 font-medium capitalize">{valor.toLowerCase()}</dd>
      </div>
    </div>
  );
}
