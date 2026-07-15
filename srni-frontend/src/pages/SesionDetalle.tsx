import { Fragment, useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, ClipboardList, Calendar, MapPin, FileText,
  BarChart3, Users, Home,
} from 'lucide-react';
import { encuestasApi, type SesionDetalle, type RespuestaEncuesta } from '@/api/encuestas';
import { hogaresApi, type MiembroResumen } from '@/api/hogares';
import Badge, { type BadgeVariant } from '@/components/ui/Badge';
import Spinner from '@/components/ui/Spinner';
import EmptyState from '@/components/ui/EmptyState';
import PageHeader from '@/components/ui/PageHeader';
import Button from '@/components/ui/Button';
import Alert from '@/components/ui/Alert';
import Breadcrumb from '@/components/ui/Breadcrumb';

const ESTADO_BADGE: Record<string, BadgeVariant> = {
  COMPLETADA: 'verde',
  EN_PROGRESO: 'amarillo',
  INICIADA: 'naranja',
  SUSPENDIDA: 'rojo',
};

function BarraProgreso({ valor }: { valor: number }) {
  // Clamp 0–100 + redondeo: evita que el relleno o el % desborden el riel.
  const pct = Math.max(0, Math.min(100, Math.round(valor || 0)));
  const color = pct >= 80 ? 'bg-gov-verde' : pct >= 40 ? 'bg-gov-azul' : 'bg-gov-naranja';
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 bg-gray-100 rounded-full h-3 overflow-hidden">
        <div className={`h-3 rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-sm font-semibold text-gray-700 w-12 text-right shrink-0">{pct}%</span>
    </div>
  );
}

export default function SesionDetallePage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [sesion, setSesion] = useState<SesionDetalle | null>(null);
  const [miembrosMap, setMiembrosMap] = useState<Record<string, string>>({});
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!id) return;
    setCargando(true);
    encuestasApi.detalle(id)
      .then(({ data }) => {
        setSesion(data);
        // Cargar miembros del hogar para mapear UUID → nombre
        return hogaresApi.detalle(data.hogar)
          .then(({ data: hogar }) => {
            const map: Record<string, string> = {};
            hogar.miembros.forEach((m) => { map[m.id] = m.nombre_completo || 'Sin nombre'; });
            setMiembrosMap(map);
          })
          .catch(() => {}); // Si falla, las respuestas se muestran sin nombre
      })
      .catch(() => setError('No se pudo cargar el detalle de la sesión.'))
      .finally(() => setCargando(false));
  }, [id]);

  if (cargando) {
    return (
      <div className="flex items-center justify-center py-20">
        <Spinner size="lg" />
      </div>
    );
  }

  if (error || !sesion) {
    return (
      <div className="p-6 max-w-4xl mx-auto">
        <Alert variant="error">{error || 'Sesión no encontrada.'}</Alert>
        <Button variant="secondary" size="sm" onClick={() => navigate('/encuestas')} className="mt-4">
          Volver a Encuestas
        </Button>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 max-w-4xl mx-auto">
      <Breadcrumb items={[
        { label: 'Inicio', to: '/dashboard' },
        { label: 'Encuestas', to: '/encuestas' },
        { label: sesion.instrumento_nombre ?? 'Sesión' },
      ]} />
      <PageHeader
        titulo={sesion.instrumento_nombre ?? 'Sesión de encuesta'}
        subtitulo={`${sesion.instrumento_codigo ?? ''} ${sesion.instrumento_numero ? `· ${sesion.instrumento_numero}` : ''}`}
        acciones={
          <Button variant="secondary" size="sm" icon={ArrowLeft} onClick={() => navigate('/encuestas')}>
            Volver
          </Button>
        }
      />

      {/* Cards de info */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4 mb-6 animate-fade-in-up">
        <InfoCard icon={ClipboardList} label="Estado">
          <Badge variant={ESTADO_BADGE[sesion.estado] ?? 'gris'}>
            {sesion.estado_display ?? sesion.estado}
          </Badge>
        </InfoCard>
        <InfoCard icon={BarChart3} label="Progreso">
          <p className="text-sm font-semibold text-gray-800">{sesion.porcentaje_completado}%</p>
        </InfoCard>
        <InfoCard icon={Calendar} label="Inicio" valor={new Date(sesion.fecha_inicio).toLocaleDateString('es-CO')} />
        <InfoCard
          icon={Calendar}
          label="Fin"
          valor={sesion.fecha_fin ? new Date(sesion.fecha_fin).toLocaleDateString('es-CO') : 'En curso'}
        />
      </div>

      {/* Barra de progreso grande */}
      <div className="card mb-6 shadow-soft animate-fade-in-up" style={{ animationDelay: '50ms', animationFillMode: 'both' }}>
        <p className="text-xs text-gray-500 mb-2 font-semibold uppercase tracking-wide">Progreso general</p>
        <BarraProgreso valor={sesion.porcentaje_completado} />
      </div>

      {/* Datos de la sesión */}
      <div className="card mb-6 animate-fade-in-up" style={{ animationDelay: '100ms', animationFillMode: 'both' }}>
        <h3 className="font-display font-semibold text-gray-700 mb-4">Información de la sesión</h3>
        <dl className="grid grid-cols-2 sm:grid-cols-3 gap-x-6 gap-y-3 text-sm">
          <DatoItem label="Ruta de entrevista" valor={sesion.ruta_entrevista} />
          <DatoItem label="Dirección Territorial" valor={sesion.direccion_territorial_nombre ?? '—'} />
          <DatoItem label="Departamento" valor={sesion.departamento_atencion_nombre ?? '—'} />
          <DatoItem label="Municipio" valor={sesion.municipio_atencion_nombre ?? '—'} />
          <DatoItem label="Punto de atención" valor={sesion.punto_atencion_nombre ?? '—'} />
          <DatoItem label="Total respuestas" valor={String(sesion.total_respuestas)} />
        </dl>
        {sesion.observaciones && (
          <p className="text-sm text-gray-500 mt-4 border-t border-gov-borde pt-3">
            {sesion.observaciones}
          </p>
        )}
      </div>

      {/* Botón ir al hogar */}
      <div className="card mb-6">
        <Button icon={MapPin} onClick={() => navigate(`/hogares/${sesion.hogar}`)}>
          Ver hogar asociado
        </Button>
      </div>

      {/* Respuestas agrupadas por miembro */}
      <RespuestasAgrupadas
        respuestas={sesion.respuestas}
        total={sesion.total_respuestas}
        miembrosMap={miembrosMap}
      />
    </div>
  );
}

function RespuestasAgrupadas({
  respuestas,
  total,
  miembrosMap,
}: {
  respuestas: RespuestaEncuesta[];
  total: number;
  miembrosMap: Record<string, string>;
}) {
  // Agrupar: null → "hogar", UUID → miembro
  const grupos = new Map<string, RespuestaEncuesta[]>();
  for (const r of respuestas) {
    const key = r.miembro ?? '__hogar__';
    if (!grupos.has(key)) grupos.set(key, []);
    grupos.get(key)!.push(r);
  }

  // Ordenar: hogar primero, luego miembros por nombre
  const keys = Array.from(grupos.keys()).sort((a, b) => {
    if (a === '__hogar__') return -1;
    if (b === '__hogar__') return 1;
    return (miembrosMap[a] ?? a).localeCompare(miembrosMap[b] ?? b);
  });

  return (
    <div className="card overflow-hidden p-0 animate-fade-in-up" style={{ animationDelay: '150ms', animationFillMode: 'both' }}>
      <div className="px-4 py-3 border-b border-gov-borde">
        <p className="font-semibold text-gray-700 text-sm">
          Respuestas ({total})
        </p>
      </div>

      {respuestas.length === 0 ? (
        <EmptyState
          icon={FileText}
          titulo="Sin respuestas aún"
          descripcion="Las respuestas aparecerán aquí a medida que se diligencia la encuesta."
        />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gov-borde">
              <tr>
                {['Código', 'Pregunta', 'Respuesta'].map((h) => (
                  <th key={h} className="text-left px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase tracking-wide">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gov-borde">
              {keys.map((key) => {
                const items = grupos.get(key)!;
                const isHogar = key === '__hogar__';
                const nombre = isHogar ? 'Hogar (general)' : (miembrosMap[key] ?? `Miembro ${key.slice(0, 8)}`);
                const IconGrupo = isHogar ? Home : Users;
                return (
                  <Fragment key={key}>
                    <tr className="bg-gray-50/80">
                      <td colSpan={3} className="px-4 py-2">
                        <span className="flex items-center gap-2 text-xs font-semibold text-gray-600 uppercase tracking-wide">
                          <IconGrupo size={14} className="text-gray-400" />
                          {nombre}
                          <span className="text-gray-400 font-normal normal-case">({items.length} respuestas)</span>
                        </span>
                      </td>
                    </tr>
                    {items.map((r) => (
                      <tr key={r.id} className="hover:bg-gov-azulTenue/30 transition-all">
                        <td className="px-4 py-3 font-mono text-gov-azul text-xs">{r.pregunta_codigo}</td>
                        <td className="px-4 py-3 text-gray-700 max-w-[300px]">
                          <p className="line-clamp-2">{r.pregunta_texto}</p>
                        </td>
                        <td className="px-4 py-3 text-gray-800 font-medium max-w-[200px] truncate">
                          {r.valor}
                        </td>
                      </tr>
                    ))}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function InfoCard({ icon: Icon, label, valor, children }: {
  icon: React.ElementType;
  label: string;
  valor?: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="card flex items-center gap-3">
      <Icon size={18} className="text-gov-azul shrink-0" />
      <div>
        <p className="text-xs text-gray-500">{label}</p>
        {children ?? <p className="text-sm font-semibold text-gray-800">{valor}</p>}
      </div>
    </div>
  );
}

function DatoItem({ label, valor }: { label: string; valor: string }) {
  return (
    <div>
      <dt className="text-xs text-gray-500">{label}</dt>
      <dd className="text-gray-800 font-medium">{valor}</dd>
    </div>
  );
}
