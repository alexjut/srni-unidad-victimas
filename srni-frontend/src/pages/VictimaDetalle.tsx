/**
 * Detalle de víctima — datos PII descifrados por el backend
 */
import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, User, Calendar, MapPin, Shield, FileText, AlertTriangle,
} from 'lucide-react';
import { victimasApi, type VictimaDetalle } from '@/api/victimas';
import Spinner from '@/components/ui/Spinner';
import PageHeader from '@/components/ui/PageHeader';
import Badge from '@/components/ui/Badge';
import Button from '@/components/ui/Button';
import Alert from '@/components/ui/Alert';
import Breadcrumb from '@/components/ui/Breadcrumb';
import EmptyState from '@/components/ui/EmptyState';

const GENERO_LABEL: Record<string, string> = {
  M: 'Masculino',
  F: 'Femenino',
  NB: 'No binario',
  ND: 'No definido',
};

const ESTADO_RUV_BADGE: Record<string, { variant: 'verde' | 'azul' | 'amarillo' | 'rojo' | 'gris'; label: string }> = {
  INCLUIDO:      { variant: 'verde',    label: 'Incluido en RUV' },
  NO_INCLUIDO:   { variant: 'gris',     label: 'No incluido' },
  EN_PROCESO:    { variant: 'amarillo', label: 'En proceso' },
  EXCLUIDO:      { variant: 'rojo',     label: 'Excluido' },
  NO_VERIFICADO: { variant: 'azul',     label: 'Sin verificar en RUV' },
};

export default function VictimaDetallePage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [victima, setVictima] = useState<VictimaDetalle | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!id) return;
    setCargando(true);
    victimasApi.detalle(id)
      .then(({ data }) => setVictima(data))
      .catch((err) => {
        if (err?.response?.status === 403) {
          setError('No tiene permisos para ver el detalle de esta víctima.');
        } else {
          setError('No se pudo cargar el detalle de la víctima.');
        }
      })
      .finally(() => setCargando(false));
  }, [id]);

  if (cargando) {
    return (
      <div className="flex items-center justify-center py-20">
        <Spinner size="lg" />
      </div>
    );
  }

  if (error || !victima) {
    return (
      <div className="p-6 max-w-4xl mx-auto">
        <Alert variant="error">{error || 'Víctima no encontrada.'}</Alert>
        <Button variant="secondary" size="sm" onClick={() => navigate('/victimas')} className="mt-4">
          Volver a Búsqueda
        </Button>
      </div>
    );
  }

  const nombreCompleto = [
    victima.primer_nombre,
    victima.segundo_nombre,
    victima.primer_apellido,
    victima.segundo_apellido,
  ].filter(Boolean).join(' ');

  const ruvInfo = ESTADO_RUV_BADGE[victima.estado_ruv];

  return (
    <div className="p-4 sm:p-6 max-w-4xl mx-auto">
      <Breadcrumb items={[
        { label: 'Inicio', to: '/dashboard' },
        { label: 'Víctimas', to: '/victimas' },
        { label: nombreCompleto || 'Detalle' },
      ]} />

      <PageHeader
        titulo={nombreCompleto}
        subtitulo={`${victima.tipo_documento.codigo} · ${victima.numero_documento}`}
        acciones={
          <Button variant="secondary" size="sm" icon={ArrowLeft} onClick={() => navigate('/victimas')}>
            Volver
          </Button>
        }
      />

      {/* Badges de estado */}
      <div className="flex flex-wrap gap-2 mb-6">
        {ruvInfo && <Badge variant={ruvInfo.variant}>{ruvInfo.label}</Badge>}
        {victima.discapacidad && <Badge variant="naranja">Discapacidad</Badge>}
      </div>

      {/* Datos personales */}
      <div className="card mb-6 animate-fade-in-up">
        <h3 className="font-display font-semibold text-gray-700 mb-4 flex items-center gap-2">
          <User size={18} className="text-gov-azul" />
          Datos personales
        </h3>
        <dl className="grid grid-cols-2 sm:grid-cols-3 gap-x-6 gap-y-3 text-sm">
          <DatoItem label="Primer nombre" valor={victima.primer_nombre} />
          <DatoItem label="Segundo nombre" valor={victima.segundo_nombre || '—'} />
          <DatoItem label="Primer apellido" valor={victima.primer_apellido} />
          <DatoItem label="Segundo apellido" valor={victima.segundo_apellido || '—'} />
          <DatoItem label="Tipo documento" valor={victima.tipo_documento.nombre} />
          <DatoItem label="Número documento" valor={victima.numero_documento} mono />
          <DatoItem label="Fecha nacimiento" valor={victima.fecha_nacimiento ? new Date(victima.fecha_nacimiento).toLocaleDateString('es-CO') : '—'} />
          <DatoItem label="Género" valor={GENERO_LABEL[victima.genero] ?? victima.genero} />
          <DatoItem label="Estado civil" valor={victima.estado_civil ? victima.estado_civil.replace('_', ' ').toLowerCase() : '—'} />
        </dl>
      </div>

      {/* Información adicional */}
      <div className="card mb-6 animate-fade-in-up" style={{ animationDelay: '50ms', animationFillMode: 'both' }}>
        <h3 className="font-display font-semibold text-gray-700 mb-4 flex items-center gap-2">
          <Shield size={18} className="text-gov-azul" />
          Información complementaria
        </h3>
        <dl className="grid grid-cols-2 sm:grid-cols-3 gap-x-6 gap-y-3 text-sm">
          <DatoItem label="Pertenencia étnica" valor={victima.pertenencia_etnica.replace('_', ' ').toLowerCase()} />
          {victima.pueblo_indigena && (
            <DatoItem label="Pueblo indígena" valor={victima.pueblo_indigena} />
          )}
          <DatoItem label="Discapacidad" valor={victima.discapacidad ? 'Sí' : 'No'} />
          {victima.tipo_discapacidad && (
            <DatoItem label="Tipo discapacidad" valor={victima.tipo_discapacidad} />
          )}
          <DatoItem
            label="Municipio residencia"
            valor={victima.municipio_residencia
              ? `${victima.municipio_residencia.nombre}, ${victima.municipio_residencia.departamento_nombre}`
              : '—'}
          />
          <DatoItem label="Estado RUV" valor={ruvInfo?.label ?? victima.estado_ruv} />
        </dl>
      </div>

      {/* Hechos victimizantes */}
      <div className="card overflow-hidden p-0 mb-6 animate-fade-in-up" style={{ animationDelay: '100ms', animationFillMode: 'both' }}>
        <div className="px-4 py-3 border-b border-gov-borde flex items-center gap-2">
          <AlertTriangle size={16} className="text-gov-naranja" />
          <p className="font-semibold text-gray-700 text-sm">
            Hechos victimizantes ({victima.hechos_victimizantes.length})
          </p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gov-borde">
              <tr>
                {['Hecho', 'Fecha', 'Lugar', 'Fuente'].map((h) => (
                  <th key={h} className="text-left px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase tracking-wide">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gov-borde">
              {victima.hechos_victimizantes.length === 0 ? (
                <tr>
                  <td colSpan={4}>
                    <EmptyState
                      icon={FileText}
                      titulo="Sin hechos victimizantes registrados"
                    />
                  </td>
                </tr>
              ) : victima.hechos_victimizantes.map((hv) => (
                <tr key={hv.id} className="hover:bg-gov-azulTenue/30 transition-all">
                  <td className="px-4 py-3 text-gray-800">{hv.hecho.nombre}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs">
                    {hv.fecha_hecho ? new Date(hv.fecha_hecho).toLocaleDateString('es-CO') : '—'}
                  </td>
                  <td className="px-4 py-3 text-gray-600 text-xs">
                    {hv.lugar_hecho
                      ? `${hv.lugar_hecho.nombre}, ${hv.lugar_hecho.departamento_nombre}`
                      : '—'}
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant="gris">{hv.fuente}</Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Metadatos */}
      <div className="card animate-fade-in-up" style={{ animationDelay: '150ms', animationFillMode: 'both' }}>
        <h3 className="font-display font-semibold text-gray-700 mb-4 flex items-center gap-2">
          <Calendar size={18} className="text-gov-azul" />
          Registro
        </h3>
        <dl className="grid grid-cols-2 sm:grid-cols-3 gap-x-6 gap-y-3 text-sm">
          <DatoItem label="Creado por" valor={victima.creado_por_nombre ?? '—'} />
          <DatoItem label="Fecha creación" valor={new Date(victima.created_at).toLocaleDateString('es-CO')} />
          <DatoItem label="Última actualización" valor={new Date(victima.updated_at).toLocaleDateString('es-CO')} />
        </dl>
      </div>
    </div>
  );
}

function DatoItem({ label, valor, mono }: { label: string; valor: string; mono?: boolean }) {
  return (
    <div>
      <dt className="text-xs text-gray-500">{label}</dt>
      <dd className={`text-gray-800 font-medium ${mono ? 'font-mono' : ''}`}>{valor}</dd>
    </div>
  );
}
