import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, Home, Users, ClipboardList, Calendar, MapPin,
} from 'lucide-react';
import { hogaresApi, type HogarDetalle } from '@/api/hogares';
import Badge, { type BadgeVariant } from '@/components/ui/Badge';
import Spinner from '@/components/ui/Spinner';
import EmptyState from '@/components/ui/EmptyState';
import PageHeader from '@/components/ui/PageHeader';
import Button from '@/components/ui/Button';
import Alert from '@/components/ui/Alert';
import Breadcrumb from '@/components/ui/Breadcrumb';

const ESTADO_HOGAR: Record<string, BadgeVariant> = {
  ACTIVO: 'verde',
  BORRADOR: 'naranja',
  ARCHIVADO: 'gris',
};

const ESTADO_SESION: Record<string, BadgeVariant> = {
  COMPLETADA: 'verde',
  EN_PROGRESO: 'azul',
  INICIADA: 'naranja',
  SUSPENDIDA: 'rojo',
};

export default function HogarDetallePage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [hogar, setHogar] = useState<HogarDetalle | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!id) return;
    setCargando(true);
    hogaresApi.detalle(id)
      .then(({ data }) => setHogar(data))
      .catch(() => setError('No se pudo cargar el detalle del hogar.'))
      .finally(() => setCargando(false));
  }, [id]);

  if (cargando) {
    return (
      <div className="flex items-center justify-center py-20">
        <Spinner size="lg" />
      </div>
    );
  }

  if (error || !hogar) {
    return (
      <div className="p-6 max-w-4xl mx-auto">
        <Alert variant="error">{error || 'Hogar no encontrado.'}</Alert>
        <Button variant="secondary" size="sm" onClick={() => navigate('/hogares')} className="mt-4">
          Volver a Hogares
        </Button>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 max-w-4xl mx-auto">
      <Breadcrumb items={[
        { label: 'Inicio', to: '/dashboard' },
        { label: 'Hogares', to: '/hogares' },
        { label: hogar.codigo_hogar ?? hogar.id.slice(0, 8) },
      ]} />
      <PageHeader
        titulo={hogar.codigo_hogar ?? `Hogar ${hogar.id.slice(0, 8)}`}
        subtitulo={hogar.municipio_nombre ?? 'Sin municipio'}
        acciones={
          <Button variant="secondary" size="sm" icon={ArrowLeft} onClick={() => navigate('/hogares')}>
            Volver
          </Button>
        }
      />

      {/* Info general */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4 mb-6">
        <InfoCard icon={Home} label="Estado">
          <Badge variant={ESTADO_HOGAR[hogar.estado] ?? 'gris'}>
            {hogar.estado_display ?? hogar.estado}
          </Badge>
        </InfoCard>
        <InfoCard icon={Users} label="Miembros" valor={String(hogar.total_miembros)} />
        <InfoCard icon={MapPin} label="Municipio" valor={hogar.municipio_nombre ?? '—'} />
        <InfoCard icon={Calendar} label="Creado" valor={new Date(hogar.created_at).toLocaleDateString('es-CO')} />
      </div>

      {/* Datos del hogar */}
      <div className="card mb-6">
        <h3 className="font-display font-semibold text-gray-700 mb-4">Datos del hogar</h3>
        <dl className="grid grid-cols-2 sm:grid-cols-3 gap-x-6 gap-y-3 text-sm">
          <DatoItem label="Tipo vivienda" valor={hogar.tipo_vivienda_display} />
          <DatoItem label="Ocupación" valor={hogar.condicion_ocupacion_display} />
          <DatoItem label="Estrato" valor={String(hogar.estrato)} />
          <DatoItem label="Personas" valor={String(hogar.numero_personas)} />
          <DatoItem label="Cuartos" valor={String(hogar.numero_cuartos)} />
          <DatoItem label="Encuestador" valor={hogar.encuestador_nombre ?? '—'} />
        </dl>
        {hogar.observaciones && (
          <p className="text-sm text-gray-500 mt-4 border-t border-gov-borde pt-3">
            {hogar.observaciones}
          </p>
        )}
      </div>

      {/* Tabla de miembros */}
      <div className="card overflow-hidden p-0 mb-6">
        <div className="px-4 py-3 border-b border-gov-borde">
          <p className="font-semibold text-gray-700 text-sm">
            Miembros del hogar ({hogar.total_miembros})
          </p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gov-borde">
              <tr>
                {['Nombre', 'Parentesco', 'Rol', 'Género', 'RUV', ''].map((h) => (
                  <th key={h} className="text-left px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase tracking-wide">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gov-borde">
              {hogar.miembros.length === 0 ? (
                <tr>
                  <td colSpan={6}>
                    <EmptyState icon={Users} titulo="Sin miembros registrados" />
                  </td>
                </tr>
              ) : hogar.miembros.map((m) => (
                <tr key={m.id} className="hover:bg-gov-azulTenue/30 transition-colors">
                  <td className="px-4 py-3 text-gray-800 font-medium">
                    {m.nombre_completo || '—'}
                    {m.es_autorizado && (
                      <Badge variant="azul" className="ml-2">Autorizado</Badge>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-600">{m.parentesco_display}</td>
                  <td className="px-4 py-3 text-gray-600">{m.rol_display}</td>
                  <td className="px-4 py-3 text-gray-600">{m.genero}</td>
                  <td className="px-4 py-3">
                    <Badge variant={m.incluido_ruv ? 'verde' : 'gris'}>
                      {m.incluido_ruv ? 'Incluido' : 'No'}
                    </Badge>
                  </td>
                  <td className="px-4 py-3"></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Tabla de sesiones */}
      <div className="card overflow-hidden p-0">
        <div className="px-4 py-3 border-b border-gov-borde">
          <p className="font-semibold text-gray-700 text-sm">
            Sesiones de encuesta ({hogar.total_sesiones})
          </p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gov-borde">
              <tr>
                {['Instrumento', 'Estado', 'Progreso', 'Encuestador', 'Fecha inicio'].map((h) => (
                  <th key={h} className="text-left px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase tracking-wide">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gov-borde">
              {hogar.sesiones.length === 0 ? (
                <tr>
                  <td colSpan={5}>
                    <EmptyState icon={ClipboardList} titulo="Sin sesiones registradas" />
                  </td>
                </tr>
              ) : hogar.sesiones.map((s) => (
                <tr
                  key={s.id}
                  onClick={() => navigate(`/encuestas/${s.id}`)}
                  className="hover:bg-gov-azulTenue/30 transition-colors cursor-pointer"
                >
                  <td className="px-4 py-3 text-gray-700">{s.instrumento_nombre}</td>
                  <td className="px-4 py-3">
                    <Badge variant={ESTADO_SESION[s.estado] ?? 'gris'}>
                      {s.estado_display ?? s.estado}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-gray-700">{s.porcentaje_completado}%</td>
                  <td className="px-4 py-3 text-gray-600 text-xs">{s.encuestador_nombre}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs">
                    {new Date(s.fecha_inicio).toLocaleDateString('es-CO')}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
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
