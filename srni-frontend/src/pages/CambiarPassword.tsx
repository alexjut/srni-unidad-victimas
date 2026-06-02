import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { z } from 'zod/v4';
import { zodResolver } from '@hookform/resolvers/zod';
import { Lock, ArrowLeft, CheckCircle } from 'lucide-react';
import { authApi } from '@/api/auth';
import PageHeader from '@/components/ui/PageHeader';
import Button from '@/components/ui/Button';
import Alert from '@/components/ui/Alert';
import Breadcrumb from '@/components/ui/Breadcrumb';

const schema = z.object({
  password_actual: z.string().min(1, 'Ingrese su contraseña actual'),
  password_nueva: z
    .string()
    .min(8, 'Mínimo 8 caracteres')
    .regex(/[A-Z]/, 'Debe contener al menos una mayúscula')
    .regex(/[0-9]/, 'Debe contener al menos un número'),
  confirmar: z.string().min(1, 'Confirme la nueva contraseña'),
}).refine((d) => d.password_nueva === d.confirmar, {
  message: 'Las contraseñas no coinciden',
  path: ['confirmar'],
});

type FormData = z.infer<typeof schema>;

export default function CambiarPasswordPage() {
  const navigate = useNavigate();
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState('');
  const [exito, setExito] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  async function onSubmit(data: FormData) {
    setEnviando(true);
    setError('');
    try {
      await authApi.cambiarPassword({
        password_actual: data.password_actual,
        password_nueva: data.password_nueva,
      });
      setExito(true);
      reset();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        ?? 'No se pudo cambiar la contraseña. Verifique su contraseña actual.';
      setError(msg);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="p-4 sm:p-6 max-w-lg mx-auto">
      <Breadcrumb items={[
        { label: 'Inicio', to: '/dashboard' },
        { label: 'Cambiar contraseña' },
      ]} />
      <PageHeader
        titulo="Cambiar contraseña"
        subtitulo="Actualice su contraseña de acceso al sistema"
        acciones={
          <Button variant="secondary" size="sm" icon={ArrowLeft} onClick={() => navigate(-1)}>
            Volver
          </Button>
        }
      />

      {exito && (
        <Alert variant="exito" className="mb-4">
          <span className="flex items-center gap-2">
            <CheckCircle size={16} />
            Contraseña actualizada correctamente.
          </span>
        </Alert>
      )}

      {error && <Alert variant="error" className="mb-4">{error}</Alert>}

      <div className="card">
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label htmlFor="password_actual" className="block text-xs font-semibold text-gray-600 uppercase tracking-wide mb-1">
              Contraseña actual
            </label>
            <div className="relative">
              <Lock size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                id="password_actual"
                type="password"
                autoComplete="current-password"
                className={`input pl-9 ${errors.password_actual ? 'border-gov-rojo focus:ring-gov-rojo' : ''}`}
                {...register('password_actual')}
              />
            </div>
            {errors.password_actual && (
              <p className="text-xs text-gov-rojo mt-1">{errors.password_actual.message}</p>
            )}
          </div>

          <div>
            <label htmlFor="password_nueva" className="block text-xs font-semibold text-gray-600 uppercase tracking-wide mb-1">
              Nueva contraseña
            </label>
            <div className="relative">
              <Lock size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                id="password_nueva"
                type="password"
                autoComplete="new-password"
                className={`input pl-9 ${errors.password_nueva ? 'border-gov-rojo focus:ring-gov-rojo' : ''}`}
                {...register('password_nueva')}
              />
            </div>
            {errors.password_nueva && (
              <p className="text-xs text-gov-rojo mt-1">{errors.password_nueva.message}</p>
            )}
            <p className="text-xs text-gray-400 mt-1">Mínimo 8 caracteres, al menos 1 mayúscula y 1 número</p>
          </div>

          <div>
            <label htmlFor="confirmar" className="block text-xs font-semibold text-gray-600 uppercase tracking-wide mb-1">
              Confirmar nueva contraseña
            </label>
            <div className="relative">
              <Lock size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                id="confirmar"
                type="password"
                autoComplete="new-password"
                className={`input pl-9 ${errors.confirmar ? 'border-gov-rojo focus:ring-gov-rojo' : ''}`}
                {...register('confirmar')}
              />
            </div>
            {errors.confirmar && (
              <p className="text-xs text-gov-rojo mt-1">{errors.confirmar.message}</p>
            )}
          </div>

          <div className="pt-2">
            <Button type="submit" loading={enviando} className="w-full">
              Cambiar contraseña
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
