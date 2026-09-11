/**
 * Recaracterizaciones sobre ficha vigente — el punto de control.
 *
 * ─── Por qué esta pantalla existe ─────────────────────────────────────────
 * El 11-sep-2026 se retiró el bloqueo por ficha vigente. El encuestador ya no se
 * detiene ante nada y no hay autorización que pedir. Lo único que quedó es el
 * registro automático, y **un registro que nadie mira equivale a no tenerlo**.
 * Esta pantalla es la que lo mira.
 *
 * ─── Las dos vistas, y por qué son dos ────────────────────────────────────
 * · **Por persona** es la que abre, y es deliberado. Lo que hay que ver son las
 *   fichas reescritas varias veces en pocas semanas, y en una lista cronológica
 *   esos casos quedan repartidos entre miles de filas: nadie los encuentra.
 *   Agrupado por persona saltan en la primera pantalla.
 * · **Cronológico** responde «qué pasó ayer», que es la otra pregunta legítima.
 *
 * ─── El número que hay que leer al revés ──────────────────────────────────
 * `dias_restantes` cuenta los días que le FALTABAN a la ficha por vencer. El
 * número más ALTO es la recaracterización más temprana, y por tanto la más grave:
 * 723 significa que la caracterización anterior tenía una semana. Mostrarlo así
 * sería pedirle al supervisor que haga la resta, así que la pantalla muestra la
 * antigüedad de la ficha —«hace 7 días»— y ordena por gravedad.
 */
import { useEffect, useState } from 'react';
import {
  History, Users, AlertTriangle, MapPin, UserCheck, Trash2, Clock,
} from 'lucide-react';
import {
  recaracterizacionesApi, RUTAS_ENTREVISTA, antiguedadDeLaFichaEnDias,
  type Recaracterizacion, type PersonaRecaracterizada,
  type ResumenRecaracterizaciones, type FiltrosRecaracterizaciones,
} from '@/api/recaracterizaciones';
import PageHeader from '@/components/ui/PageHeader';
import Table, { type Column } from '@/components/ui/Table';
import Button from '@/components/ui/Button';
import Card from '@/components/ui/Card';
import Badge from '@/components/ui/Badge';
import Dropdown from '@/components/ui/Dropdown';
import Alert from '@/components/ui/Alert';

const PAGE_SIZE = 20;

type Vista = 'personas' | 'cronologico';

/**
 * Cómo se lee la antigüedad de la ficha que se reescribió.
 *
 * Las franjas no son decorativas: separan «la actualizaron a los tres días» de
 * «a los 22 meses», y son dos hechos distintos. Un promedio los mezcla hasta
 * volver invisible el primero, que es justo el que hay que ver.
 */
function gravedad(diasRestantes: number | null): {
  variant: 'rojo' | 'naranja' | 'amarillo' | 'gris';
  texto: string;
} {
  const antiguedad = antiguedadDeLaFichaEnDias(diasRestantes);
  if (antiguedad === null) return { variant: 'gris', texto: 'sin dato' };
  if (antiguedad <= 7) return { variant: 'rojo', texto: `hace ${antiguedad} día(s)` };
  if (antiguedad <= 30) return { variant: 'naranja', texto: `hace ${antiguedad} días` };
  if (antiguedad <= 182) {
    return { variant: 'amarillo', texto: `hace ${Math.round(antiguedad / 30)} meses` };
  }
  return { variant: 'gris', texto: `hace ${Math.round(antiguedad / 30)} meses` };
}

function fechaCorta(iso: string | null): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('es-CO', {
    day: '2-digit', month: 'short', year: 'numeric',
  });
}

function fechaHora(iso: string): string {
  return new Date(iso).toLocaleDateString('es-CO', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

export default function RecaracterizacionesPage() {
  const [vista, setVista] = useState<Vista>('personas');
  const [resumen, setResumen] = useState<ResumenRecaracterizaciones | null>(null);
  const [personas, setPersonas] = useState<PersonaRecaracterizada[]>([]);
  const [eventos, setEventos] = useState<Recaracterizacion[]>([]);
  const [total, setTotal] = useState(0);
  const [pagina, setPagina] = useState(1);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState('');
  const [sinPermiso, setSinPermiso] = useState(false);

  // Filtros
  const [filtroDesde, setFiltroDesde] = useState('');
  const [filtroHasta, setFiltroHasta] = useState('');
  const [filtroUsuario, setFiltroUsuario] = useState('');
  const [filtroRuta, setFiltroRuta] = useState('');
  const [soloGraves, setSoloGraves] = useState(false);

  const hayFiltros = !!(filtroDesde || filtroHasta || filtroUsuario || filtroRuta || soloGraves);

  function filtrosActuales(): FiltrosRecaracterizaciones {
    return {
      ...(filtroDesde && { fecha_desde: filtroDesde }),
      ...(filtroHasta && { fecha_hasta: filtroHasta }),
      ...(filtroUsuario && { codigo_usuario: filtroUsuario }),
      ...(filtroRuta && { ruta: filtroRuta }),
      // 700 días restantes = la ficha tenía 30 días o menos. Es el corte de «la
      // recaracterizaron casi enseguida», que es lo que un supervisor busca.
      ...(soloGraves && { dias_restantes_min: 700 }),
    };
  }

  function cargar(pag: number, v: Vista) {
    setCargando(true);
    setError('');
    const filtros = filtrosActuales();

    // El resumen y la tabla se piden en paralelo: son dos consultas al mismo
    // conjunto y encadenarlas duplicaría la espera sin ganar nada.
    const pedirTabla = v === 'personas'
      ? recaracterizacionesApi.personas({ ...filtros, page: pag, page_size: PAGE_SIZE })
      : recaracterizacionesApi.listar({
        ...filtros, page: pag, page_size: PAGE_SIZE,
        // Con el filtro de gravedad activo, lo grave primero; si no, lo reciente.
        ordering: soloGraves ? '-dias_restantes' : '-realizada_at',
      });

    Promise.all([recaracterizacionesApi.resumen(filtros), pedirTabla])
      .then(([res, tabla]) => {
        setResumen(res.data);
        setTotal(tabla.data.count);
        if (v === 'personas') {
          setPersonas(tabla.data.results as PersonaRecaracterizada[]);
        } else {
          setEventos(tabla.data.results as Recaracterizacion[]);
        }
      })
      .catch((err) => {
        // 403 no es un error de red: es que este usuario no supervisa. Decirlo
        // así evita que alguien reporte una falla que no existe.
        if (err?.response?.status === 403) {
          setSinPermiso(true);
        } else {
          setError('No se pudieron cargar las recaracterizaciones. Intente de nuevo.');
        }
      })
      .finally(() => setCargando(false));
  }

  useEffect(() => {
    cargar(pagina, vista);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pagina, vista]);

  function aplicarFiltros() {
    setPagina(1);
    cargar(1, vista);
  }

  function limpiarFiltros() {
    setFiltroDesde('');
    setFiltroHasta('');
    setFiltroUsuario('');
    setFiltroRuta('');
    setSoloGraves(false);
    setPagina(1);
    setCargando(true);
    setError('');
    Promise.all([
      recaracterizacionesApi.resumen(),
      vista === 'personas'
        ? recaracterizacionesApi.personas({ page: 1, page_size: PAGE_SIZE })
        : recaracterizacionesApi.listar({
          page: 1, page_size: PAGE_SIZE, ordering: '-realizada_at',
        }),
    ])
      .then(([res, tabla]) => {
        setResumen(res.data);
        setTotal(tabla.data.count);
        if (vista === 'personas') setPersonas(tabla.data.results as PersonaRecaracterizada[]);
        else setEventos(tabla.data.results as Recaracterizacion[]);
      })
      .catch(() => setError('No se pudieron cargar las recaracterizaciones.'))
      .finally(() => setCargando(false));
  }

  function cambiarVista(v: Vista) {
    if (v === vista) return;
    setPagina(1);
    setVista(v);
  }

  const totalPaginas = Math.ceil(total / PAGE_SIZE);

  // ── Columnas: por persona ──────────────────────────────────────────────────
  const columnasPersonas: Column<PersonaRecaracterizada>[] = [
    {
      key: 'veces',
      header: 'Veces',
      className: 'w-20',
      render: (p) => (
        <Badge variant={p.veces >= 4 ? 'rojo' : p.veces === 3 ? 'naranja' : 'amarillo'}>
          {p.veces}
        </Badge>
      ),
    },
    {
      key: 'documento_hash',
      header: 'Persona',
      render: (p) => (
        <div>
          {/* El documento va hasheado desde el servidor. Se muestran los últimos
              caracteres: alcanzan para distinguir dos filas en pantalla y para
              cruzar con otra consulta, sin exponer el documento de la víctima. */}
          <p className="font-mono text-xs text-gov-azul">
            …{p.documento_hash.slice(-12)}
          </p>
          <p className="text-xs text-gray-400">
            {p.autores === 1 ? '1 encuestador' : `${p.autores} encuestadores distintos`}
          </p>
        </div>
      ),
    },
    {
      key: 'gravedad',
      header: 'Ficha más fresca reescrita',
      className: 'w-52',
      render: (p) => {
        const g = gravedad(p.menor_dias_restantes);
        return (
          <div className="flex items-center gap-2">
            <Badge variant={g.variant}>{g.texto}</Badge>
          </div>
        );
      },
    },
    {
      key: 'primera',
      header: 'Primera',
      className: 'hidden md:table-cell w-32',
      render: (p) => (
        <span className="text-xs text-gray-500 whitespace-nowrap">{fechaCorta(p.primera)}</span>
      ),
    },
    {
      key: 'ultima',
      header: 'Última',
      className: 'w-32',
      render: (p) => (
        <span className="text-xs text-gray-600 whitespace-nowrap">{fechaCorta(p.ultima)}</span>
      ),
    },
  ];

  // ── Columnas: cronológico ──────────────────────────────────────────────────
  const columnasEventos: Column<Recaracterizacion>[] = [
    {
      key: 'realizada_at',
      header: 'Cuándo',
      className: 'w-40',
      render: (e) => (
        <span className="text-xs text-gray-500 whitespace-nowrap">{fechaHora(e.realizada_at)}</span>
      ),
    },
    {
      key: 'realizada_por_codigo',
      header: 'Quién',
      className: 'w-36',
      render: (e) => (
        <div>
          <p className="font-mono text-sm text-gov-azul">{e.realizada_por_codigo || '—'}</p>
          {e.realizada_por_nombre && (
            <p className="text-xs text-gray-400">{e.realizada_por_nombre}</p>
          )}
        </div>
      ),
    },
    {
      key: 'documento_hash',
      header: 'Persona',
      render: (e) => (
        <div>
          <p className="font-mono text-xs text-gov-azul">…{e.documento_hash.slice(-12)}</p>
          {e.veces_esta_persona > 1 && (
            /* El dato que permite ver, leyendo el listado corriente, que esta es
               la tercera vez sobre la misma persona. Sin él hay que ir a la otra
               vista a sospecharlo, y nadie va. */
            <p className="text-xs text-gov-naranja font-semibold">
              {e.veces_esta_persona}ª vez
            </p>
          )}
        </div>
      ),
    },
    {
      key: 'gravedad',
      header: 'Ficha anterior',
      className: 'w-44',
      render: (e) => {
        const g = gravedad(e.dias_restantes);
        return (
          <div>
            <Badge variant={g.variant}>{g.texto}</Badge>
            <p className="text-xs text-gray-400 mt-0.5">
              {fechaCorta(e.fecha_ult_caracterizacion)}
            </p>
          </div>
        );
      },
    },
    {
      key: 'ruta_display',
      header: 'Ruta',
      className: 'hidden lg:table-cell w-44',
      render: (e) => <span className="text-sm text-gray-700">{e.ruta_display || '—'}</span>,
    },
    {
      key: 'territorial',
      header: 'Territorial',
      className: 'hidden md:table-cell',
      render: (e) => (
        <div>
          <p className="text-sm text-gray-700">{e.departamento_nombre || '—'}</p>
          <p className="text-xs text-gray-400">{e.municipio_nombre}</p>
        </div>
      ),
    },
    {
      key: 'codigo_hogar',
      header: 'Hogar',
      className: 'hidden xl:table-cell w-32',
      render: (e) => (
        <span className="text-xs font-mono text-gray-500">{e.codigo_hogar || '—'}</span>
      ),
    },
  ];

  if (sinPermiso) {
    return (
      <div className="p-4 sm:p-6 max-w-3xl mx-auto">
        <PageHeader titulo="Recaracterizaciones" subtitulo="Punto de control" />
        <Alert variant="warning">
          Esta consulta es de supervisión. Se requiere perfil administrador o
          supervisor con permiso de reportes.
        </Alert>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 max-w-7xl mx-auto">
      <PageHeader
        titulo="Recaracterizaciones"
        subtitulo="Caracterizaciones hechas sobre una ficha que aún estaba vigente"
      />

      {/* Los cuatro números que responden el informe de control */}
      {resumen && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <Card
            icon={History}
            label="Recaracterizaciones"
            valor={resumen.total}
            color="bg-gov-azul"
          />
          <Card
            icon={Users}
            label="Personas distintas"
            valor={resumen.personas_distintas}
            color="bg-gov-verde"
          />
          <Card
            icon={AlertTriangle}
            label="Ficha de 30 días o menos"
            valor={resumen.anticipacion.hasta_7_dias + resumen.anticipacion.hasta_30_dias}
            color="bg-gov-naranja"
          />
          <Card
            icon={UserCheck}
            label="Promedio por persona"
            valor={resumen.promedio_por_persona}
            color="bg-gov-gris"
          />
        </div>
      )}

      {/* Filtros */}
      <div className="card mb-6 shadow-soft animate-fade-in-up">
        <div className="flex flex-col lg:flex-row gap-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 flex-1">
            <div>
              <label className="block text-xs font-semibold text-gray-600 uppercase tracking-wide mb-1">
                Desde
              </label>
              <input
                type="date"
                value={filtroDesde}
                onChange={(e) => setFiltroDesde(e.target.value)}
                className="input"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-600 uppercase tracking-wide mb-1">
                Hasta
              </label>
              <input
                type="date"
                value={filtroHasta}
                onChange={(e) => setFiltroHasta(e.target.value)}
                className="input"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-600 uppercase tracking-wide mb-1">
                Encuestador
              </label>
              <input
                type="text"
                placeholder="Código de usuario"
                value={filtroUsuario}
                onChange={(e) => setFiltroUsuario(e.target.value.toUpperCase())}
                className="input"
              />
            </div>
            <div>
              <Dropdown
                label="Ruta"
                value={filtroRuta}
                onChange={setFiltroRuta}
                options={[
                  { value: '', label: 'Todas' },
                  ...RUTAS_ENTREVISTA.map((r) => ({ value: r.valor, label: r.etiqueta })),
                ]}
              />
            </div>
          </div>

          <div className="flex items-end gap-2">
            <Button onClick={aplicarFiltros} className="h-[38px] flex-1 lg:flex-none">
              Filtrar
            </Button>
            {hayFiltros && (
              <Button
                variant="danger"
                icon={Trash2}
                onClick={limpiarFiltros}
                className="h-[38px] flex-1 lg:flex-none"
              >
                Limpiar
              </Button>
            )}
          </div>
        </div>

        {/*
          El corte de «la recaracterizaron casi enseguida». Es un botón y no un
          campo numérico a propósito: pedirle al supervisor los días restantes lo
          obliga a saber que 700 significa 30, y nadie debería tener que saber eso.
        */}
        <label className="flex items-center gap-2 mt-3 text-sm text-gray-600 cursor-pointer">
          <input
            type="checkbox"
            checked={soloGraves}
            onChange={(e) => setSoloGraves(e.target.checked)}
            className="rounded border-gray-300"
          />
          <Clock size={14} className="text-gov-naranja" />
          Solo las hechas sobre una ficha de 30 días o menos
        </label>
      </div>

      {error && <Alert variant="warning" className="mb-4">{error}</Alert>}

      {/* Las dos vistas */}
      <div className="flex gap-2 mb-4">
        <button
          onClick={() => cambiarVista('personas')}
          className={`px-4 py-2 text-sm font-semibold rounded-lg transition-colors ${
            vista === 'personas'
              ? 'bg-gov-azul text-white shadow-soft'
              : 'bg-white text-gray-600 hover:bg-gray-50 border border-gray-200'
          }`}
        >
          Por persona
        </button>
        <button
          onClick={() => cambiarVista('cronologico')}
          className={`px-4 py-2 text-sm font-semibold rounded-lg transition-colors ${
            vista === 'cronologico'
              ? 'bg-gov-azul text-white shadow-soft'
              : 'bg-white text-gray-600 hover:bg-gray-50 border border-gray-200'
          }`}
        >
          Cronológico
        </button>
      </div>

      {vista === 'personas' && (
        <p className="text-xs text-gray-400 mb-3 flex items-center gap-2">
          <MapPin size={13} />
          Solo personas recaracterizadas más de una vez, de más a menos.
        </p>
      )}

      {vista === 'personas' ? (
        <Table
          columns={columnasPersonas}
          data={personas}
          keyExtractor={(p) => p.victima}
          cargando={cargando}
          emptyIcon={History}
          emptyTitulo="Ninguna persona recaracterizada más de una vez"
          emptyDescripcion={
            hayFiltros
              ? 'No hay personas que coincidan con los filtros aplicados.'
              : 'Cada persona del registro tiene una sola recaracterización. Es el escenario deseable.'
          }
          pagina={pagina}
          totalPaginas={totalPaginas}
          onPaginaChange={setPagina}
        />
      ) : (
        <Table
          columns={columnasEventos}
          data={eventos}
          keyExtractor={(e) => e.id}
          cargando={cargando}
          emptyIcon={History}
          emptyTitulo="Sin recaracterizaciones registradas"
          emptyDescripcion={
            hayFiltros
              ? 'No hay registros que coincidan con los filtros aplicados.'
              : 'No se ha caracterizado a ninguna persona que tuviera ficha vigente.'
          }
          pagina={pagina}
          totalPaginas={totalPaginas}
          onPaginaChange={setPagina}
        />
      )}

      {/* Quién hizo cuántas y en qué territorial — lo que va en el informe */}
      {resumen && resumen.total > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-6">
          <div className="card shadow-soft">
            <h3 className="text-sm font-semibold text-gray-700 mb-3">Por encuestador</h3>
            {resumen.por_autor.slice(0, 10).map((a) => (
              <div key={a.codigo_usuario} className="flex items-center justify-between py-1.5 border-b border-gray-100 last:border-0">
                <div>
                  <p className="font-mono text-xs text-gov-azul">{a.codigo_usuario || '—'}</p>
                  {a.nombre && <p className="text-xs text-gray-400">{a.nombre}</p>}
                </div>
                <span className="text-sm font-semibold text-gray-700">{a.veces}</span>
              </div>
            ))}
          </div>

          <div className="card shadow-soft">
            <h3 className="text-sm font-semibold text-gray-700 mb-3">Por territorial</h3>
            {resumen.por_territorial.slice(0, 10).map((t) => (
              <div key={t.departamento} className="flex items-center justify-between py-1.5 border-b border-gray-100 last:border-0">
                <span className="text-sm text-gray-700">{t.departamento}</span>
                <span className="text-sm font-semibold text-gray-700">{t.veces}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/*
        Se dice de frente lo que es. Un registro que hubiera que ocultar sería un
        registro que no se puede usar después, y es justamente para usarlo que
        existe: para responder a control interno el día que pregunte.
      */}
      <p className="flex items-start gap-2 mt-6 text-xs text-gray-400">
        <History size={14} className="mt-0.5 shrink-0" />
        <span>
          El sistema escribe estos registros solo, al cerrar cada encuesta. No
          detienen a nadie y el encuestador no interviene. Existen para poder
          responder, ante control interno o externo, cuántas recaracterizaciones se
          hicieron sobre fichas vigentes, quién las hizo y con cuánta anticipación.
        </span>
      </p>
    </div>
  );
}
