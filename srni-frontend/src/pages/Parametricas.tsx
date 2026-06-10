/**
 * Parametricas — consulta de tablas de referencia (departamentos, municipios, DTs, puntos, tipos doc)
 * Responsive fixes: filtros, tabs, mapa, botones limpiar
 */
import { useEffect, useState } from 'react';
import {
  MapPin, Building2, Navigation, Landmark, FileText, Trash2,
} from 'lucide-react';
import {
  ComposableMap,
  Geographies,
  Geography,
} from 'react-simple-maps';
import {
  parametricasApi,
  type Departamento,
  type Municipio,
  type DireccionTerritorial,
  type PuntoAtencion,
  type TipoDocumento,
} from '@/api/parametricas';
import PageHeader from '@/components/ui/PageHeader';
import Alert from '@/components/ui/Alert';
import Badge from '@/components/ui/Badge';
import Button from '@/components/ui/Button';
import Dropdown from '@/components/ui/Dropdown';
import Spinner from '@/components/ui/Spinner';

const GEO_URL = '/geo/colombia.json';

// --- Tabs ---

const TABS = [
  { key: 'departamentos',  label: 'Departamentos',      labelCorto: 'Deptos.',   icon: MapPin },
  { key: 'municipios',     label: 'Municipios',          labelCorto: 'Munis.',    icon: Building2 },
  { key: 'dts',            label: 'Dir. Territoriales',  labelCorto: 'Dir. Ter.', icon: Navigation },
  { key: 'puntos',         label: 'Puntos atención',     labelCorto: 'Puntos',    icon: Landmark },
  { key: 'tipos_doc',      label: 'Tipos documento',     labelCorto: 'Tipos doc.',icon: FileText },
] as const;

type TabKey = typeof TABS[number]['key'];

export default function ParametricasPage() {
  const [tab, setTab] = useState<TabKey>('departamentos');

  return (
    <div className="p-4 sm:p-6 max-w-7xl mx-auto">
      <PageHeader
        titulo="Paramétricas"
        subtitulo="Tablas de referencia del sistema"
      />

      {/* Tabs — sticky, scroll horizontal en mobile */}
      <div
        className="flex gap-1 overflow-x-auto border-b border-gov-borde mb-6 pb-px sticky top-0 z-20 bg-gov-grisTenue pt-1 -mt-1"
        role="tablist"
      >
        {TABS.map(({ key, label, labelCorto, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            role="tab"
            aria-selected={tab === key}
            aria-label={label}
            title={label}
            className={`flex items-center gap-1.5 px-3 sm:px-4 py-2.5 text-sm font-medium whitespace-nowrap border-b-2 transition-all ${
              tab === key
                ? 'border-gov-azul text-gov-azul'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            <Icon size={16} />
            {/* En mobile muestra label corto; en sm+ muestra label completo */}
            <span className="sm:hidden">{labelCorto}</span>
            <span className="hidden sm:inline">{label}</span>
          </button>
        ))}
      </div>

      {/* Contenido del tab activo */}
      {tab === 'departamentos' && <TabDepartamentos />}
      {tab === 'municipios'    && <TabMunicipios />}
      {tab === 'dts'           && <TabDireccionesTerritoriales />}
      {tab === 'puntos'        && <TabPuntosAtencion />}
      {tab === 'tipos_doc'     && <TabTiposDocumento />}
    </div>
  );
}

// --- Wrapper de tabla simple ---

function TablaSimple({
  headers,
  children,
  cargando,
  error,
  total,
}: {
  headers: string[];
  children: React.ReactNode;
  cargando: boolean;
  error: string;
  total: number;
}) {
  return (
    <>
      {error && <Alert variant="error" className="mb-4">{error}</Alert>}

      <div className="card p-0 overflow-hidden">
        {cargando ? (
          <div className="flex items-center justify-center py-16">
            <Spinner size="lg" />
          </div>
        ) : (
          <>
            <div className="px-4 py-2.5 bg-gray-50 border-b border-gov-borde text-xs text-gray-500">
              {total} registro(s)
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 border-b border-gov-borde">
                    {headers.map((h) => (
                      <th
                        key={h}
                        className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide"
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gov-borde/40">
                  {children}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </>
  );
}

// --- Tab: Departamentos (mapa + tabla) ---

function normalizarNombre(nombre: string) {
  return nombre
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim();
}

function TabDepartamentos() {
  const [datos, setDatos] = useState<Departamento[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState('');
  const [hoveredGeo, setHoveredGeo] = useState<string | null>(null);
  const [selectedDepto, setSelectedDepto] = useState<Departamento | null>(null);

  useEffect(() => {
    parametricasApi.departamentos()
      .then(({ data }) => setDatos(data.results))
      .catch(() => setError('No se pudieron cargar los departamentos.'))
      .finally(() => setCargando(false));
  }, []);

  function findDepto(geoName: string): Departamento | undefined {
    const norm = normalizarNombre(geoName);
    return datos.find((d) => {
      const apiNorm = normalizarNombre(d.nombre);
      return apiNorm === norm
        || norm.includes(apiNorm)
        || apiNorm.includes(norm);
    });
  }

  return (
    <>
      {error && <Alert variant="error" className="mb-4">{error}</Alert>}

      {cargando ? (
        <div className="flex items-center justify-center py-16">
          <Spinner size="lg" />
        </div>
      ) : (
        <div className="flex flex-col lg:flex-row gap-6">

          {/* Mapa */}
          <div className="card p-0 overflow-hidden lg:w-[420px] shrink-0 shadow-soft">
            <div className="px-4 py-3 bg-gray-50 border-b border-gov-borde">
              <div className="flex items-center justify-between mb-2">
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                  Mapa de departamentos
                </p>
                <p className="text-xs text-gray-400">{datos.length} deptos.</p>
              </div>
              <div className="flex flex-wrap gap-3">
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded-sm" style={{ background: '#90CAF9' }} />
                  <span className="text-xs text-gray-500">Registrado</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded-sm" style={{ background: '#1565C0' }} />
                  <span className="text-xs text-gray-500">Seleccionado</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded-sm" style={{ background: '#E0E0E0' }} />
                  <span className="text-xs text-gray-500">Sin registro</span>
                </div>
              </div>
            </div>

            {/* Banner de departamento seleccionado */}
            {selectedDepto ? (
              <div className="mx-3 mt-3 flex flex-col xs:flex-row items-start xs:items-center justify-between gap-2 bg-gov-azulTenue border border-blue-100 rounded-xl px-4 py-3">
                <div>
                  <p className="text-sm font-semibold text-gov-azul">{selectedDepto.nombre}</p>
                  <p className="text-xs text-gray-500">
                    Código DANE:{' '}
                    <span className="font-mono font-medium text-gray-700">
                      {selectedDepto.codigo_dane}
                    </span>
                  </p>
                </div>
                <Button
                  variant="danger"
                  size="sm"
                  icon={Trash2}
                  onClick={() => setSelectedDepto(null)}
                  className="w-full xs:w-auto shrink-0"
                >
                  Limpiar
                </Button>
              </div>
            ) : (
              <p className="mx-3 mt-3 text-xs text-gray-400 text-center">
                Click en un departamento para seleccionarlo
              </p>
            )}

            {/* Mapa SVG — altura limitada en mobile para no colapsar la vista */}
            <div className="flex items-center justify-center p-2 max-h-[320px] sm:max-h-[400px] lg:max-h-none overflow-hidden">
              <ComposableMap
                projection="geoMercator"
                projectionConfig={{ scale: 1800, center: [-73.5, 4.5] }}
                width={500}
                height={600}
                style={{ width: '100%', height: 'auto' }}
              >
                <Geographies geography={GEO_URL}>
                  {({ geographies }) =>
                    geographies.map((geo) => {
                      const geoName = geo.properties.name || '';
                      const geoId = geo.properties.id || '';
                      const depto = findDepto(geoName);
                      const isSelected =
                        selectedDepto && depto && selectedDepto.id === depto.id;

                      return (
                        <Geography
                          key={geo.rsmKey}
                          geography={geo}
                          onMouseEnter={() => setHoveredGeo(geoId)}
                          onMouseLeave={() => setHoveredGeo(null)}
                          onClick={() => setSelectedDepto(depto || null)}
                          style={{
                            default: {
                              fill: isSelected ? '#1565C0' : depto ? '#90CAF9' : '#E0E0E0',
                              stroke: '#fff',
                              strokeWidth: 0.8,
                              outline: 'none',
                            },
                            hover: {
                              fill: isSelected ? '#0D47A1' : '#1565C0',
                              stroke: '#fff',
                              strokeWidth: 1.2,
                              outline: 'none',
                              cursor: 'pointer',
                            },
                            pressed: {
                              fill: '#0D47A1',
                              stroke: '#fff',
                              strokeWidth: 1.2,
                              outline: 'none',
                            },
                          }}
                        />
                      );
                    })
                  }
                </Geographies>
              </ComposableMap>
            </div>
          </div>

          {/* Tabla al lado derecho */}
          <div className="flex-1 min-w-0">
            <div className="card p-0 overflow-hidden">
              <div className="px-4 py-2.5 bg-gray-50 border-b border-gov-borde text-xs text-gray-500">
                {datos.length} registro(s)
              </div>
              <div className="overflow-y-auto max-h-[320px] sm:max-h-[460px] lg:max-h-[600px]">
                <table className="w-full text-sm">
                  <thead className="sticky top-0 z-10">
                    <tr className="bg-gray-50 border-b border-gov-borde">
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                        Código DANE
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                        Nombre
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gov-borde/40">
                    {datos.map((d) => (
                      <tr
                        key={d.id}
                        className={`hover:bg-gov-azulTenue/30 transition-all cursor-pointer ${
                          selectedDepto?.id === d.id ? 'bg-gov-azulTenue' : ''
                        }`}
                        onClick={() =>
                          setSelectedDepto(selectedDepto?.id === d.id ? null : d)
                        }
                      >
                        <td className="px-4 py-3 font-mono text-gov-azul">{d.codigo_dane}</td>
                        <td className="px-4 py-3 text-gray-700">{d.nombre}</td>
                      </tr>
                    ))}
                    {datos.length === 0 && (
                      <tr>
                        <td colSpan={2} className="px-4 py-8 text-center text-gray-400">
                          Sin departamentos
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

        </div>
      )}
    </>
  );
}

// --- Tab: Municipios ---

function TabMunicipios() {
  const [deptos, setDeptos] = useState<Departamento[]>([]);
  const [deptoSel, setDeptoSel] = useState<number | ''>('');
  const [todos, setTodos] = useState<Municipio[]>([]);
  const [filtrados, setFiltrados] = useState<Municipio[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([
      parametricasApi.departamentos(),
      parametricasApi.municipiosTodos(),
    ])
      .then(([deptosRes, munisRes]) => {
        setDeptos(deptosRes.data.results);
        const munis = Array.isArray(munisRes.data)
          ? munisRes.data
          : (munisRes.data as any).results ?? [];
        setTodos(munis);
        setFiltrados(munis);
      })
      .catch(() => setError('No se pudieron cargar los municipios.'))
      .finally(() => setCargando(false));
  }, []);

  useEffect(() => {
    if (deptoSel === '') {
      setFiltrados(todos);
    } else {
      setFiltrados(todos.filter((m) => m.departamento === deptoSel));
    }
  }, [deptoSel, todos]);

  const deptoNombre =
    deptoSel !== '' ? deptos.find((d) => d.id === deptoSel)?.nombre : null;

  return (
    <>
      {/* Filtro — stack en mobile, fila en sm+ */}
      <div className="flex flex-col sm:flex-row sm:items-end gap-2 sm:gap-3 mb-4">
        <div className="w-full sm:flex-1 sm:max-w-sm">
          <Dropdown
            label="Filtrar por departamento"
            value={String(deptoSel)}
            onChange={(val) => setDeptoSel(val ? Number(val) : '')}
            options={[
              { value: '', label: 'Todos los departamentos' },
              ...deptos.map((d) => ({ value: String(d.id), label: d.nombre })),
            ]}
            disabled={cargando}
          />
        </div>
        {deptoSel !== '' && (
          <Button
            variant="danger"
            size="md"
            icon={Trash2}
            onClick={() => setDeptoSel('')}
            className="w-full sm:w-auto"
          >
            Limpiar filtro
          </Button>
        )}
      </div>

      {deptoNombre && (
        <div className="mb-4 flex items-center gap-2 bg-gov-azulTenue border border-blue-100 rounded-xl px-4 py-2.5">
          <Building2 size={14} className="text-gov-azul shrink-0" />
          <span className="text-sm text-gov-azul min-w-0">
            Mostrando municipios de <strong>{deptoNombre}</strong>
          </span>
          <span className="text-xs text-gray-400 shrink-0">
            ({filtrados.length} resultado{filtrados.length !== 1 ? 's' : ''})
          </span>
        </div>
      )}

      <TablaSimple
        headers={['Código DANE', 'Nombre', 'Departamento']}
        cargando={cargando}
        error={error}
        total={filtrados.length}
      >
        {filtrados.map((m) => (
          <tr key={m.id} className="hover:bg-gov-azulTenue/30 transition-all">
            <td className="px-4 py-3 font-mono text-gov-azul">{m.codigo_dane}</td>
            <td className="px-4 py-3 text-gray-700">{m.nombre}</td>
            <td className="px-4 py-3 text-gray-500">{m.departamento_nombre}</td>
          </tr>
        ))}
        {!cargando && filtrados.length === 0 && (
          <tr>
            <td colSpan={3} className="px-4 py-8 text-center text-gray-400">
              Sin municipios{deptoNombre ? ` para ${deptoNombre}` : ''}
            </td>
          </tr>
        )}
      </TablaSimple>
    </>
  );
}

// --- Tab: Direcciones Territoriales ---

function TabDireccionesTerritoriales() {
  const [datos, setDatos] = useState<DireccionTerritorial[]>([]);
  const [busqueda, setBusqueda] = useState('');
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    parametricasApi.direccionesTerritoriales()
      .then(({ data }) => setDatos(data.results))
      .catch(() => setError('No se pudieron cargar las direcciones territoriales.'))
      .finally(() => setCargando(false));
  }, []);

  const filtrados = busqueda.trim()
    ? datos.filter((d) => {
        const term = busqueda.toLowerCase();
        return (
          d.nombre.toLowerCase().includes(term) ||
          d.codigo.toLowerCase().includes(term)
        );
      })
    : datos;

  return (
    <>
      {/* Filtro — stack en mobile, fila en sm+ */}
      <div className="flex flex-col sm:flex-row sm:items-end gap-2 sm:gap-3 mb-4">
        <div className="w-full sm:flex-1 sm:max-w-sm">
          <label className="block text-xs font-semibold text-gray-600 uppercase tracking-wide mb-1">
            Buscar dirección territorial
          </label>
          <input
            type="text"
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            placeholder="Nombre o código..."
            className="input w-full"
            disabled={cargando}
          />
        </div>
        {busqueda && (
          <Button
            variant="danger"
            size="md"
            icon={Trash2}
            onClick={() => setBusqueda('')}
            className="w-full sm:w-auto"
          >
            Limpiar filtro
          </Button>
        )}
      </div>

      {busqueda.trim() && (
        <div className="mb-4 flex items-center gap-2 bg-gov-azulTenue border border-blue-100 rounded-xl px-4 py-2.5">
          <Navigation size={14} className="text-gov-azul shrink-0" />
          <span className="text-sm text-gov-azul min-w-0 truncate">
            Buscando: <strong>"{busqueda.trim()}"</strong>
          </span>
          <span className="text-xs text-gray-400 shrink-0">
            ({filtrados.length} resultado{filtrados.length !== 1 ? 's' : ''})
          </span>
        </div>
      )}

      <TablaSimple
        headers={['Código', 'Nombre']}
        cargando={cargando}
        error={error}
        total={filtrados.length}
      >
        {filtrados.map((d) => (
          <tr key={d.id} className="hover:bg-gov-azulTenue/30 transition-all">
            <td className="px-4 py-3 font-mono text-gov-azul">{d.codigo}</td>
            <td className="px-4 py-3 text-gray-700">{d.nombre}</td>
          </tr>
        ))}
        {!cargando && filtrados.length === 0 && (
          <tr>
            <td colSpan={2} className="px-4 py-8 text-center text-gray-400">
              Sin resultados{busqueda ? ` para "${busqueda}"` : ''}
            </td>
          </tr>
        )}
      </TablaSimple>
    </>
  );
}

// --- Tab: Puntos de Atención ---

function TabPuntosAtencion() {
  const [dts, setDts] = useState<DireccionTerritorial[]>([]);
  const [dtSel, setDtSel] = useState<number | ''>('');
  const [todos, setTodos] = useState<PuntoAtencion[]>([]);
  const [filtrados, setFiltrados] = useState<PuntoAtencion[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([
      parametricasApi.direccionesTerritoriales(),
      parametricasApi.puntosAtencion(),
    ])
      .then(([dtsRes, puntosRes]) => {
        setDts(dtsRes.data.results);
        const puntos = puntosRes.data.results;
        setTodos(puntos);
        setFiltrados(puntos);
      })
      .catch(() => setError('No se pudieron cargar los puntos de atención.'))
      .finally(() => setCargando(false));
  }, []);

  useEffect(() => {
    if (dtSel === '') {
      setFiltrados(todos);
    } else {
      setFiltrados(todos.filter((p) => p.direccion_territorial === dtSel));
    }
  }, [dtSel, todos]);

  const dtNombre =
    dtSel !== '' ? dts.find((d) => d.id === dtSel)?.nombre : null;

  return (
    <>
      {/* Filtro — stack en mobile, fila en sm+ */}
      <div className="flex flex-col sm:flex-row sm:items-end gap-2 sm:gap-3 mb-4">
        <div className="w-full sm:flex-1 sm:max-w-sm">
          <Dropdown
            label="Filtrar por dirección territorial"
            value={String(dtSel)}
            onChange={(val) => setDtSel(val ? Number(val) : '')}
            options={[
              { value: '', label: 'Todas las direcciones territoriales' },
              ...dts.map((d) => ({ value: String(d.id), label: d.nombre })),
            ]}
            disabled={cargando}
          />
        </div>
        {dtSel !== '' && (
          <Button
            variant="danger"
            size="md"
            icon={Trash2}
            onClick={() => setDtSel('')}
            className="w-full sm:w-auto"
          >
            Limpiar filtro
          </Button>
        )}
      </div>

      {dtNombre && (
        <div className="mb-4 flex items-center gap-2 bg-gov-azulTenue border border-blue-100 rounded-xl px-4 py-2.5">
          <Landmark size={14} className="text-gov-azul shrink-0" />
          <span className="text-sm text-gov-azul min-w-0">
            Mostrando puntos de <strong>{dtNombre}</strong>
          </span>
          <span className="text-xs text-gray-400 shrink-0">
            ({filtrados.length} resultado{filtrados.length !== 1 ? 's' : ''})
          </span>
        </div>
      )}

      <TablaSimple
        headers={['Código', 'Nombre', 'Dirección Territorial']}
        cargando={cargando}
        error={error}
        total={filtrados.length}
      >
        {filtrados.map((p) => (
          <tr key={p.id} className="hover:bg-gov-azulTenue/30 transition-all">
            <td className="px-4 py-3 font-mono text-gov-azul">{p.codigo}</td>
            <td className="px-4 py-3 text-gray-700">{p.nombre}</td>
            <td className="px-4 py-3 text-gray-500">{p.direccion_territorial_nombre}</td>
          </tr>
        ))}
        {!cargando && filtrados.length === 0 && (
          <tr>
            <td colSpan={3} className="px-4 py-8 text-center text-gray-400">
              Sin puntos de atención{dtNombre ? ` para ${dtNombre}` : ''}
            </td>
          </tr>
        )}
      </TablaSimple>
    </>
  );
}

// --- Tab: Tipos de Documento ---

function TabTiposDocumento() {
  const [datos, setDatos] = useState<TipoDocumento[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    parametricasApi.tiposDocumento()
      .then(({ data }) => setDatos(data.results))
      .catch(() => setError('No se pudieron cargar los tipos de documento.'))
      .finally(() => setCargando(false));
  }, []);

  return (
    <TablaSimple
      headers={['Código', 'Nombre', 'Estado']}
      cargando={cargando}
      error={error}
      total={datos.length}
    >
      {datos.map((t) => (
        <tr key={t.codigo} className="hover:bg-gov-azulTenue/30 transition-all">
          <td className="px-4 py-3 font-mono text-gov-azul">{t.codigo}</td>
          <td className="px-4 py-3 text-gray-700">{t.nombre}</td>
          <td className="px-4 py-3">
            <Badge variant={t.activo ? 'verde' : 'gris'}>
              {t.activo ? 'Activo' : 'Inactivo'}
            </Badge>
          </td>
        </tr>
      ))}
      {!cargando && datos.length === 0 && (
        <tr>
          <td colSpan={3} className="px-4 py-8 text-center text-gray-400">
            Sin tipos de documento
          </td>
        </tr>
      )}
    </TablaSimple>
  );
}