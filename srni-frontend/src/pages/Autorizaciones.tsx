/**
 * Autorizar excepciones de vigencia — pantalla de coordinación.
 *
 * Vive dentro del panel y no como página aparte: hereda header, menú, footer y
 * la sesión. La primera versión se sirvió desde Django y se veía como otra
 * aplicación — quien la abría perdía la navegación entera.
 *
 * Tres pasos en una sola pantalla: buscar (una cédula o muchas), marcar a quién
 * se autoriza, y el soporte que las cubre a todas.
 */
import { useEffect, useState } from 'react';
import { FileCheck, Search, ShieldCheck } from 'lucide-react';
import { toast } from 'sonner';
import {
  habilitacionesApi, RUTAS_EXCEPCION, ESTADOS_HABILITACION,
  type Habilitacion, type PersonaBuscada, type ResultadoBusqueda,
} from '@/api/habilitaciones';
import PageHeader from '@/components/ui/PageHeader';
import Table, { type Column } from '@/components/ui/Table';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import Select from '@/components/ui/Select';
import Alert from '@/components/ui/Alert';
import Badge from '@/components/ui/Badge';

const TIPOS_DOC = ['CC', 'TI', 'CE', 'RC', 'PA', 'PEP'].map((v) => ({ value: v, label: v }));

/**
 * Base del chip de estado.
 *
 * Se escribe con utilidades y no con una clase `.badge`: el proyecto solo
 * define variantes con color fijo (`.badge-verde`, `.badge-rojo`…) y no una
 * base neutra, así que `badge` a secas no aplicaría nada. Es el mismo patrón
 * que usa la página de Auditoría.
 */
const CHIP = 'inline-block text-xs font-medium px-2 py-0.5 rounded-md';

const ESTADO_BADGE: Record<string, string> = {
  VIGENTE: 'bg-gov-verdeTenue text-gov-verde',
  USADA:   'bg-gray-100 text-gray-600',
  ANULADA: 'bg-gov-rojoTenue text-gov-rojo',
};

function fecha(iso: string | null): string {
  if (!iso) return '—';
  const [a, m, d] = iso.slice(0, 10).split('-');
  return d ? `${d}/${m}/${a}` : iso;
}

/** El texto de error de DRF: `detail`, o los errores por campo. */
function mensajeError(err: unknown, porDefecto: string): string {
  const datos = (err as { response?: { data?: Record<string, unknown> } })?.response?.data;
  if (!datos) return porDefecto;
  if (typeof datos.detail === 'string') return datos.detail;
  const porCampo = Object.entries(datos)
    .filter(([k]) => k !== 'omitidas' && k !== 'autorizadas')
    .map(([k, v]) => `${k}: ${[v].flat().join(' ')}`);
  return porCampo.length ? porCampo.join(' · ') : porDefecto;
}

export default function AutorizacionesPage() {
  // Búsqueda
  const [tipoDoc, setTipoDoc] = useState('CC');
  const [documentos, setDocumentos] = useState('');
  const [buscando, setBuscando] = useState(false);
  const [resultado, setResultado] = useState<ResultadoBusqueda | null>(null);
  const [marcadas, setMarcadas] = useState<Set<string>>(new Set());

  // Formulario de autorización
  const [ruta, setRuta] = useState(RUTAS_EXCEPCION[0].value);
  const [radicado, setRadicado] = useState('');
  const [motivo, setMotivo] = useState('');
  const [soporte, setSoporte] = useState<File | null>(null);
  const [autorizando, setAutorizando] = useState(false);
  const [errorForm, setErrorForm] = useState('');

  // Listado
  const [habilitaciones, setHabilitaciones] = useState<Habilitacion[]>([]);
  const [filtroEstado, setFiltroEstado] = useState('VIGENTE');
  const [cargandoLista, setCargandoLista] = useState(true);

  useEffect(() => { cargarLista(); }, [filtroEstado]);   // eslint-disable-line react-hooks/exhaustive-deps

  function cargarLista() {
    setCargandoLista(true);
    habilitacionesApi.listar(filtroEstado)
      .then(({ data }) => {
        setHabilitaciones(Array.isArray(data) ? data : data.results ?? []);
      })
      .catch(() => toast.error('No se pudo cargar el listado de excepciones.'))
      .finally(() => setCargandoLista(false));
  }

  function buscar(e: React.FormEvent) {
    e.preventDefault();
    const lista = documentos.split(/[\s,;]+/).filter(Boolean);
    if (!lista.length) return;

    setBuscando(true);
    setMarcadas(new Set());
    habilitacionesApi.buscar(tipoDoc, lista)
      .then(({ data }) => setResultado(data))
      .catch((err) => {
        // H-027 — que el aviso diga algo útil y no se duplique. El interceptor
        // global (client.ts) ya muestra un toast para red/timeout, 500 y 403;
        // repetir acá daba dos avisos contradictorios para el mismo evento. Solo
        // se agrega mensaje propio cuando el servidor respondió algo que el
        // interceptor no cubre (un 4xx con detalle), o para orientar al usuario
        // cuando la búsqueda se corta por tiempo con muchos documentos.
        const res = (err as { response?: { status?: number } })?.response;
        if (!res) {
          // Sin respuesta: red o corte por tiempo. El interceptor ya avisó; solo
          // se orienta si la consulta era grande.
          if (lista.length > 1) {
            toast.info('La búsqueda tardó demasiado. Intenta con menos documentos a la vez.');
          }
          return;
        }
        if (res.status && res.status >= 500) return;   // ya avisó el interceptor
        if (res.status === 403) return;                // ya avisó el interceptor
        toast.error(mensajeError(err, 'No se pudo buscar.'));
      })
      .finally(() => setBuscando(false));
  }

  /**
   * Clave de la fila. No se puede usar `id` a secas: quien viene del corte del
   * RUV todavía no tiene ficha en el padrón y llega con `id: null`. Se marca el
   * origen en la clave para poder separarlos al enviar — el backend los recibe
   * en dos listas distintas porque a unos hay que crearles la ficha.
   */
  function claveDe(p: PersonaBuscada): string {
    return p.origen === 'UNIVERSO' ? `u:${p.universo_id}` : `p:${p.id}`;
  }

  /** Solo tiene sentido marcar a quien tiene ficha vigente y no está habilitada. */
  const autorizables = (resultado?.resultados ?? [])
    .filter((p) => p.requiere_excepcion && !p.habilitacion_vigente);

  function alternar(id: string) {
    setMarcadas((prev) => {
      const s = new Set(prev);
      if (s.has(id)) s.delete(id); else s.add(id);
      return s;
    });
  }

  function autorizar(e: React.FormEvent) {
    e.preventDefault();
    setErrorForm('');

    if (!marcadas.size) {
      setErrorForm('Marque al menos una persona en los resultados.');
      return;
    }
    if (!radicado.trim()) {
      setErrorForm('El radicado del soporte es obligatorio: es lo que permite ir a buscar el documento después.');
      return;
    }
    if (motivo.trim().length < 10) {
      setErrorForm('Escriba el motivo de la excepción (mínimo 10 caracteres). Es lo que queda como justificación de haber levantado la regla.');
      return;
    }

    setAutorizando(true);
    habilitacionesApi.autorizar({
      // Dos listas: a los del corte del RUV el backend les crea la ficha al
      // autorizar, y por eso no pueden ir mezclados con los que ya la tienen.
      victima_ids: [...marcadas].filter((k) => k.startsWith('p:')).map((k) => k.slice(2)),
      universo_ids: [...marcadas].filter((k) => k.startsWith('u:')).map((k) => k.slice(2)),
      ruta,
      radicado: radicado.trim(),
      observacion: motivo.trim(),
      soporte,
    })
      .then(({ data }) => terminar(data.total_autorizadas, data.total_omitidas, data.omitidas))
      .catch((err) => {
        // El 409 con todas omitidas trae el detalle de cada una: se muestra
        // igual, porque "no se pudo" sin decir de quién no le sirve a nadie.
        const datos = err?.response?.data;
        if (err?.response?.status === 409 && datos?.omitidas) {
          terminar(datos.total_autorizadas ?? 0, datos.total_omitidas ?? 0, datos.omitidas);
          return;
        }
        setErrorForm(mensajeError(err, 'No se pudo autorizar.'));
      })
      .finally(() => setAutorizando(false));
  }

  function terminar(
    autorizadas: number,
    omitidas: number,
    detalleOmitidas: Array<{ motivo: string; detail?: string }>,
  ) {
    if (autorizadas) {
      toast.success(
        autorizadas === 1
          ? 'Excepción autorizada. La persona ya puede actualizarse; el encuestador la verá al sincronizar.'
          : `${autorizadas} excepciones autorizadas. El encuestador las verá al sincronizar.`);
    }
    if (omitidas) {
      toast.warning(
        `Se omitieron ${omitidas}: ` +
        detalleOmitidas.map((o) => o.detail || o.motivo).join(' · '));
    }
    if (autorizadas) {
      setResultado(null);
      setMarcadas(new Set());
      setDocumentos('');
      setRadicado('');
      setMotivo('');
      setSoporte(null);
    }
    cargarLista();
  }

  function anular(h: Habilitacion) {
    const motivoAnulacion = window.prompt(
      'Anular deja sin efecto la autorización, pero no la borra: queda el registro '
      + 'de quién la otorgó y quién la retiró.\n\n¿Por qué se anula? (mínimo 10 caracteres)');
    if (motivoAnulacion === null) return;
    if (motivoAnulacion.trim().length < 10) {
      toast.error('Indique el motivo — mínimo 10 caracteres.');
      return;
    }
    habilitacionesApi.anular(h.id, motivoAnulacion.trim())
      .then(() => { toast.success('Excepción anulada.'); cargarLista(); })
      .catch((err) => toast.error(mensajeError(err, 'No se pudo anular.')));
  }

  // ── Columnas ──────────────────────────────────────────────────────────────

  const columnasResultados: Column<PersonaBuscada>[] = [
    {
      key: 'marca',
      header: '',
      className: 'w-10',
      render: (p) => (
        p.requiere_excepcion && !p.habilitacion_vigente ? (
          <input
            type="checkbox"
            className="h-4 w-4 accent-gov-azul cursor-pointer"
            checked={marcadas.has(claveDe(p))}
            onChange={() => alternar(claveDe(p))}
            aria-label={`Autorizar a ${p.nombre}`}
          />
        ) : null
      ),
    },
    {
      key: 'persona',
      header: 'Persona',
      render: (p) => (
        <div>
          <div className="flex items-center gap-2">
            <p className="font-medium text-gray-800">{p.nombre || '(sin nombre)'}</p>
            {p.origen === 'UNIVERSO' && (
              <Badge variant="azul">Del RUV · sin ficha</Badge>
            )}
          </div>
          <p className="text-xs text-gray-500 font-mono">
            {p.tipo_documento || '—'} {p.numero_documento}
            {p.fecha_nacimiento ? ` · ${p.fecha_nacimiento}` : ''}
          </p>
          {/* 1,04 M de víctimas están cargadas sin tipo de documento. Cuando la
              coincidencia es solo por número, quien autoriza tiene que mirar la
              identidad antes de decidir — es el mismo aviso que la app le da al
              encuestador en campo. */}
          {p.coincide_solo_por_numero && (
            <p className="mt-1 text-xs text-gov-naranja">
              Coincide por número, pero el tipo de documento registrado no es{' '}
              {tipoDoc}. <strong>VERIFIQUE la identidad.</strong>
            </p>
          )}
          {p.origen === 'UNIVERSO' && (
            <p className="mt-1 text-xs text-gray-500">
              Está en el corte del RUV pero no tiene ficha en el padrón. Al
              autorizar se le crea con estos datos.
            </p>
          )}
        </div>
      ),
    },
    {
      key: 'situacion',
      header: 'Situación',
      render: (p) => {
        if (p.habilitacion_vigente) {
          return (
            <div>
              <span className={`${CHIP} ${ESTADO_BADGE.VIGENTE}`}>Ya habilitada</span>
              <p className="text-xs text-gray-500 mt-1">
                radicado {p.habilitacion_vigente.radicado || '—'} · por{' '}
                {p.habilitacion_vigente.autorizada_por_codigo || '—'}
              </p>
            </div>
          );
        }
        if (p.motivo === 'FICHA_VIGENTE') {
          return (
            <div>
              <span className={`${CHIP} bg-gov-naranjaTenue text-gov-naranja`}>Ficha vigente</span>
              <p className="text-xs text-gray-500 mt-1">
                hasta el {fecha(p.ficha_vigente_hasta)}
              </p>
            </div>
          );
        }
        if (p.motivo === 'EXCLUIDA_RUV') {
          return (
            <div>
              <span className={`${CHIP} ${ESTADO_BADGE.ANULADA}`}>Excluida del RUV</span>
              <p className="text-xs text-gray-500 mt-1">ninguna ruta la habilita</p>
            </div>
          );
        }
        if (p.motivo === 'ELEGIBLE') {
          return (
            <div>
              <span className={`${CHIP} ${ESTADO_BADGE.VIGENTE}`}>Ya puede caracterizarse</span>
              <p className="text-xs text-gray-500 mt-1">no necesita excepción</p>
            </div>
          );
        }
        return <span className={`${CHIP} bg-gray-100 text-gray-600`}>{p.motivo}</span>;
      },
    },
  ];

  const columnasListado: Column<Habilitacion>[] = [
    {
      key: 'persona',
      header: 'Persona',
      render: (h) => (
        <div>
          <p className="font-medium text-gray-800">{h.victima_nombre || '—'}</p>
          <p className="text-xs text-gray-500 font-mono">{h.victima_documento}</p>
        </div>
      ),
    },
    { key: 'ruta', header: 'Ruta', render: (h) => <span className="text-sm">{h.ruta_display}</span> },
    { key: 'radicado', header: 'Radicado', render: (h) => <span className="font-mono text-sm">{h.radicado || '—'}</span> },
    {
      key: 'estado',
      header: 'Estado',
      render: (h) => <span className={`${CHIP} ${ESTADO_BADGE[h.estado] ?? ''}`}>{h.estado}</span>,
    },
    { key: 'autorizo', header: 'Autorizó', render: (h) => <span className="font-mono text-xs">{h.autorizada_por_codigo || '—'}</span> },
    { key: 'fecha', header: 'Fecha', render: (h) => <span className="text-sm">{fecha(h.created_at)}</span> },
    {
      key: 'acciones',
      header: '',
      render: (h) => (
        h.estado === 'VIGENTE'
          ? <Button variant="ghost" size="sm" onClick={() => anular(h)}>Anular</Button>
          : null
      ),
    },
  ];

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div>
      <PageHeader
        titulo="Autorizar excepciones de vigencia"
        subtitulo="Habilita la actualización de una caracterización vigente cuando hay un fallo, tutela o auto que lo ordena."
      />

      {/* 1. Buscar */}
      <div className="card p-5 mb-5">
        <h3 className="font-semibold text-gray-800 mb-1">1. Buscar a las personas</h3>
        <p className="text-sm text-gray-500 mb-4">
          Una cédula o muchas — un fallo suele amparar a un hogar entero. Sepárelas
          por espacios, comas o una por línea.
        </p>
        <form onSubmit={buscar} className="flex flex-col sm:flex-row gap-3 sm:items-end">
          <div className="sm:w-28">
            <Select label="Tipo" options={TIPOS_DOC} value={tipoDoc}
                    onChange={(e) => setTipoDoc(e.target.value)} />
          </div>
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1.5">
              Números de documento
            </label>
            <textarea
              className="input min-h-[76px]"
              value={documentos}
              onChange={(e) => setDocumentos(e.target.value)}
              placeholder={'1115724047\n1030547250'}
            />
          </div>
          <Button type="submit" icon={Search} loading={buscando}
                  disabled={buscando || !documentos.trim()}>
            Buscar
          </Button>
        </form>
      </div>

      {/* Resultados */}
      {resultado && (
        <div className="mb-5">
          {resultado.sin_coincidencia.length > 0 && (
            <Alert variant="error" className="mb-3">
              Sin coincidencia en el padrón:{' '}
              <span className="font-mono">{resultado.sin_coincidencia.join(', ')}</span>.
              Pueden ser víctimas igual — verifique en Vivanto.
            </Alert>
          )}

          <Table
            columns={columnasResultados}
            data={resultado.resultados}
            keyExtractor={(p) => claveDe(p)}
            emptyIcon={Search}
            emptyTitulo="Ninguno de esos documentos está en el padrón"
          />

          {resultado.total > 0 && autorizables.length === 0 && (
            <Alert variant="info" className="mt-3">
              Ninguna de estas personas necesita excepción, o ya la tiene.
            </Alert>
          )}
        </div>
      )}

      {/* 2. Autorizar */}
      {autorizables.length > 0 && (
        <div className="card p-5 mb-5">
          <h3 className="font-semibold text-gray-800 mb-1">2. Autorizar la excepción</h3>
          <p className="text-sm text-gray-500 mb-4">
            {marcadas.size === 0
              ? 'Marque en la tabla a quién se le autoriza.'
              : marcadas.size === 1
                ? 'Se autorizará sobre 1 persona, con este soporte.'
                : `Se autorizará sobre ${marcadas.size} personas, todas con el mismo soporte.`}
          </p>

          {errorForm && <Alert variant="error" className="mb-4">{errorForm}</Alert>}

          <form onSubmit={autorizar} className="space-y-4">
            <Select label="Ruta que omite la vigencia" options={RUTAS_EXCEPCION}
                    value={ruta} onChange={(e) => setRuta(e.target.value)} />

            <Input label="Radicado del soporte" value={radicado} placeholder="T-2026-451"
                   onChange={(e) => setRadicado(e.target.value)} />

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">Motivo</label>
              <textarea
                className="input min-h-[80px]"
                value={motivo}
                onChange={(e) => setMotivo(e.target.value)}
                placeholder="Fallo de tutela que ordena caracterizar de nuevo al hogar."
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                Documento de soporte <span className="text-gray-400">(opcional)</span>
              </label>
              <input
                type="file"
                className="text-sm"
                onChange={(e) => setSoporte(e.target.files?.[0] ?? null)}
              />
              <p className="text-xs text-gray-500 mt-1">
                Si lo tiene en el computador. No es obligatorio: hay casos que llegan
                por correo o por teléfono.
              </p>
            </div>

            <Button type="submit" icon={ShieldCheck} loading={autorizando}
                    disabled={autorizando || marcadas.size === 0}>
              {marcadas.size <= 1 ? 'Autorizar' : `Autorizar las ${marcadas.size}`}
            </Button>
          </form>
        </div>
      )}

      {/* 3. Listado */}
      <div className="card p-5">
        <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3 mb-4">
          <div>
            <h3 className="font-semibold text-gray-800 mb-1">Excepciones autorizadas</h3>
            <p className="text-sm text-gray-500">
              Una habilitación se consume al usarse. Anular no borra: queda el registro.
            </p>
          </div>
          <div className="sm:w-52">
            <Select
              label="Estado"
              options={[{ value: '', label: 'Todas' }, ...ESTADOS_HABILITACION]}
              value={filtroEstado}
              onChange={(e) => setFiltroEstado(e.target.value)}
            />
          </div>
        </div>

        <Table
          columns={columnasListado}
          data={habilitaciones}
          keyExtractor={(h) => h.id}
          cargando={cargandoLista}
          emptyIcon={FileCheck}
          emptyTitulo="Sin excepciones"
          emptyDescripcion="Las que se autoricen aparecerán acá."
        />
      </div>
    </div>
  );
}
