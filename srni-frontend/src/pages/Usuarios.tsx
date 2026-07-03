/**
 * Administración de usuarios — solo administradores.
 * Tabla + crear/editar + activar/desactivar + resetear contraseña.
 */
import { useEffect, useState } from 'react';
import { UserCog, Plus, KeyRound, PowerOff, Power, Pencil, Search } from 'lucide-react';
import { toast } from 'sonner';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import { usuariosApi, type Usuario, type Perfil } from '@/api/usuarios';
import PageHeader from '@/components/ui/PageHeader';
import Table, { type Column } from '@/components/ui/Table';
import Button from '@/components/ui/Button';
import Modal from '@/components/ui/Modal';
import Input from '@/components/ui/Input';
import Select from '@/components/ui/Select';
import Badge, { type BadgeVariant } from '@/components/ui/Badge';
import Alert from '@/components/ui/Alert';

const PAGE_SIZE = 20;

const PERFIL_BADGE: Record<string, BadgeVariant> = {
  ADMINISTRADOR: 'rojo',
  COORDINADOR: 'naranja',
  SUPERVISOR: 'azul',
  ENCUESTADOR: 'verde',
};

const OPCIONES_ESTADO = [
  { value: '', label: 'Todos los estados' },
  { value: 'true', label: 'Activos' },
  { value: 'false', label: 'Inactivos' },
];

interface FormState {
  codigo_usuario: string;
  nombre_completo: string;
  email: string;
  perfil: string;
  activo: boolean;
  es_admin: boolean;
  password: string;
}

const FORM_VACIO: FormState = {
  codigo_usuario: '', nombre_completo: '', email: '',
  perfil: '', activo: true, es_admin: false, password: '',
};

function formatFecha(iso: string | null): string {
  if (!iso) return 'Nunca';
  return format(new Date(iso), "d MMM yyyy", { locale: es });
}

export default function UsuariosPage() {
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [perfiles, setPerfiles] = useState<Perfil[]>([]);
  const [total, setTotal] = useState(0);
  const [pagina, setPagina] = useState(1);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState('');
  const [busqueda, setBusqueda] = useState('');
  const [filtroPerfil, setFiltroPerfil] = useState('');
  const [filtroActivo, setFiltroActivo] = useState('');

  // Modal crear/editar
  const [modalAbierto, setModalAbierto] = useState(false);
  const [editando, setEditando] = useState<Usuario | null>(null);
  const [form, setForm] = useState<FormState>(FORM_VACIO);
  const [guardando, setGuardando] = useState(false);

  // Modal resetear contraseña
  const [resetUser, setResetUser] = useState<Usuario | null>(null);
  const [nuevaPass, setNuevaPass] = useState('');

  function cargar(
    pag: number,
    search = busqueda,
    perfil = filtroPerfil,
    activo = filtroActivo,
  ) {
    setCargando(true);
    setError('');
    usuariosApi.lista({
      page: pag,
      page_size: PAGE_SIZE,
      ordering: 'codigo_usuario',
      ...(search && { search }),
      ...(perfil && { perfil__codigo: perfil }),
      ...(activo !== '' && { activo: activo === 'true' }),
    })
      .then(({ data }) => { setUsuarios(data.results); setTotal(data.count); })
      .catch(() => setError('No se pudieron cargar los usuarios.'))
      .finally(() => setCargando(false));
  }

  useEffect(() => { cargar(pagina); }, [pagina]);
  useEffect(() => {
    usuariosApi.perfiles().then(({ data }) => setPerfiles(data)).catch(() => {});
  }, []);

  function buscar() { setPagina(1); cargar(1); }

  function cambiarFiltroPerfil(codigo: string) {
    setFiltroPerfil(codigo);
    setPagina(1);
    cargar(1, busqueda, codigo, filtroActivo);
  }

  function cambiarFiltroActivo(val: string) {
    setFiltroActivo(val);
    setPagina(1);
    cargar(1, busqueda, filtroPerfil, val);
  }

  function abrirCrear() { setEditando(null); setForm(FORM_VACIO); setModalAbierto(true); }

  function abrirEditar(u: Usuario) {
    setEditando(u);
    setForm({
      codigo_usuario: u.codigo_usuario,
      nombre_completo: u.nombre_completo,
      email: u.email,
      perfil: u.perfil ? String(u.perfil) : '',
      activo: u.activo,
      es_admin: u.es_admin,
      password: '',
    });
    setModalAbierto(true);
  }

  function guardar() {
    if (!editando && form.password.length < 8) {
      toast.error('La contraseña debe tener al menos 8 caracteres.');
      return;
    }
    if (!form.perfil) { toast.error('Selecciona un perfil.'); return; }
    setGuardando(true);
    const perfilId = form.perfil ? Number(form.perfil) : null;
    const peticion = editando
      ? usuariosApi.editar(editando.id, {
          nombre_completo: form.nombre_completo,
          email: form.email,
          perfil: perfilId,
          activo: form.activo,
          es_admin: form.es_admin,
        })
      : usuariosApi.crear({
          codigo_usuario: form.codigo_usuario,
          nombre_completo: form.nombre_completo,
          email: form.email,
          perfil: perfilId,
          activo: form.activo,
          es_admin: form.es_admin,
          password: form.password,
        });
    peticion
      .then(() => {
        toast.success(editando ? 'Usuario actualizado' : 'Usuario creado');
        setModalAbierto(false);
        cargar(pagina);
      })
      .catch((e) => {
        const d = e?.response?.data;
        toast.error(d ? (typeof d === 'string' ? d : Object.values(d).flat().join(' ')) : 'No se pudo guardar.');
      })
      .finally(() => setGuardando(false));
  }

  function toggleActivo(u: Usuario) {
    const fn = u.activo ? usuariosApi.desactivar : usuariosApi.activar;
    fn(u.id)
      .then(() => {
        toast.success(u.activo ? 'Usuario desactivado' : 'Usuario activado');
        cargar(pagina);
      })
      .catch(() => toast.error('No se pudo cambiar el estado.'));
  }

  function guardarReset() {
    if (!resetUser) return;
    if (nuevaPass.length < 8) { toast.error('Mínimo 8 caracteres.'); return; }
    usuariosApi.resetPassword(resetUser.id, nuevaPass)
      .then(() => { toast.success('Contraseña actualizada'); setResetUser(null); setNuevaPass(''); })
      .catch(() => toast.error('No se pudo cambiar la contraseña.'));
  }

  const totalPaginas = Math.ceil(total / PAGE_SIZE);

  const opcionesPerfil = [
    { value: '', label: 'Todos los perfiles' },
    ...perfiles.map((p) => ({ value: p.codigo, label: p.nombre })),
  ];

  const opcionesPerfilForm = perfiles.map((p) => ({ value: String(p.id), label: p.nombre }));

  const columnas: Column<Usuario>[] = [
    {
      key: 'codigo_usuario',
      header: 'Código',
      className: 'w-32',
      render: (u) => (
        <div>
          <span className="font-mono text-sm font-semibold text-gov-azul">{u.codigo_usuario}</span>
          {u.es_admin && (
            <p className="text-[10px] font-semibold text-gov-naranja uppercase tracking-wide mt-0.5">
              Admin Django
            </p>
          )}
        </div>
      ),
    },
    {
      key: 'nombre_completo',
      header: 'Nombre',
      render: (u) => (
        <div>
          <p className="text-sm font-medium text-gray-800">{u.nombre_completo}</p>
          <p className="text-xs text-gray-400">{u.email || '—'}</p>
          <p className="text-[11px] text-gray-300 mt-0.5">
            Último acceso: {formatFecha(u.fecha_ultimo_login)}
          </p>
        </div>
      ),
    },
    {
      key: 'perfil',
      header: 'Perfil',
      className: 'w-40',
      render: (u) => (
        <Badge variant={PERFIL_BADGE[u.perfil_codigo] ?? 'gris'}>
          {u.perfil_nombre || '—'}
        </Badge>
      ),
    },
    {
      key: 'activo',
      header: 'Estado',
      className: 'w-24',
      render: (u) => (
        <Badge variant={u.activo ? 'verde' : 'gris'}>
          {u.activo ? 'Activo' : 'Inactivo'}
        </Badge>
      ),
    },
    {
      key: 'acciones',
      header: 'Acciones',
      className: 'w-36',
      render: (u) => (
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            icon={Pencil}
            onClick={() => abrirEditar(u)}
            title="Editar usuario"
          />
          <Button
            variant="ghost"
            size="sm"
            icon={KeyRound}
            onClick={() => { setResetUser(u); setNuevaPass(''); }}
            title="Resetear contraseña"
          />
          <Button
            variant="ghost"
            size="sm"
            icon={u.activo ? PowerOff : Power}
            onClick={() => toggleActivo(u)}
            title={u.activo ? 'Desactivar usuario' : 'Activar usuario'}
            className={u.activo ? 'text-gov-rojo hover:text-gov-rojo hover:bg-gov-rojoTenue' : 'text-gov-verde hover:text-gov-verde hover:bg-gov-verdeTenue'}
          />
        </div>
      ),
    },
  ];

  return (
    <div className="p-4 sm:p-6 max-w-7xl mx-auto">
      <PageHeader titulo="Administración de usuarios" subtitulo={`${total} usuario(s)`} />

      {/* Barra: búsqueda + filtros + nuevo */}
      <div className="card mb-6 shadow-soft">
        <div className="flex flex-col sm:flex-row gap-3 sm:items-end">
          <div className="flex-1">
            <Input
              label="Buscar"
              icon={Search}
              placeholder="Código, nombre o correo"
              value={busqueda}
              onChange={(e) => setBusqueda(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && buscar()}
            />
          </div>
          <div className="w-full sm:w-44">
            <Select
              label="Perfil"
              options={opcionesPerfil}
              value={filtroPerfil}
              onChange={(e) => cambiarFiltroPerfil(e.target.value)}
            />
          </div>
          <div className="w-full sm:w-40">
            <Select
              label="Estado"
              options={OPCIONES_ESTADO}
              value={filtroActivo}
              onChange={(e) => cambiarFiltroActivo(e.target.value)}
            />
          </div>
          <div className="flex gap-2 shrink-0">
            <Button onClick={buscar} className="h-[38px]">Buscar</Button>
            <Button variant="primary" icon={Plus} onClick={abrirCrear} className="h-[38px]">
              Nuevo
            </Button>
          </div>
        </div>
      </div>

      {error && <Alert variant="warning" className="mb-4">{error}</Alert>}

      <Table
        columns={columnas}
        data={usuarios}
        keyExtractor={(u) => u.id}
        cargando={cargando}
        emptyIcon={UserCog}
        emptyTitulo="Sin usuarios"
        emptyDescripcion="No se encontraron usuarios con los filtros aplicados."
        pagina={pagina}
        totalPaginas={totalPaginas}
        onPaginaChange={setPagina}
      />

      {/* Modal crear / editar */}
      <Modal
        abierto={modalAbierto}
        onCerrar={() => setModalAbierto(false)}
        titulo={editando ? `Editar — ${editando.codigo_usuario}` : 'Nuevo usuario'}
        acciones={
          <>
            <Button variant="secondary" onClick={() => setModalAbierto(false)}>Cancelar</Button>
            <Button onClick={guardar} loading={guardando}>
              {editando ? 'Guardar cambios' : 'Crear usuario'}
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          <Input
            label="Código de usuario"
            value={form.codigo_usuario}
            onChange={(e) => setForm({ ...form, codigo_usuario: e.target.value.toUpperCase() })}
            disabled={!!editando}
            placeholder="Ej: ENC006"
          />
          <Input
            label="Nombre completo"
            value={form.nombre_completo}
            onChange={(e) => setForm({ ...form, nombre_completo: e.target.value })}
          />
          <Input
            label="Correo electrónico"
            type="email"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
          />
          <Select
            label="Perfil"
            options={opcionesPerfilForm}
            placeholder="Selecciona un perfil"
            value={form.perfil}
            onChange={(e) => setForm({ ...form, perfil: e.target.value })}
          />
          {!editando && (
            <Input
              label="Contraseña"
              type="password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              placeholder="Mínimo 8 caracteres"
            />
          )}

          {/* Opciones booleanas */}
          <div className="pt-1 space-y-2 border-t border-gov-borde">
            <label className="flex items-center gap-3 py-2 cursor-pointer group">
              <div className="relative shrink-0">
                <input
                  type="checkbox"
                  className="sr-only peer"
                  checked={form.activo}
                  onChange={(e) => setForm({ ...form, activo: e.target.checked })}
                />
                <div className="w-9 h-5 rounded-full bg-gray-200 peer-checked:bg-gov-azul transition-colors duration-200" />
                <div className="absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform duration-200 peer-checked:translate-x-4" />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-800">Usuario activo</p>
                <p className="text-xs text-gray-400">Puede iniciar sesión en el sistema</p>
              </div>
            </label>
            <label className="flex items-center gap-3 py-2 cursor-pointer group">
              <div className="relative shrink-0">
                <input
                  type="checkbox"
                  className="sr-only peer"
                  checked={form.es_admin}
                  onChange={(e) => setForm({ ...form, es_admin: e.target.checked })}
                />
                <div className="w-9 h-5 rounded-full bg-gray-200 peer-checked:bg-gov-naranja transition-colors duration-200" />
                <div className="absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform duration-200 peer-checked:translate-x-4" />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-800">Administrador Django</p>
                <p className="text-xs text-gray-400">Acceso al panel /admin/ del servidor</p>
              </div>
            </label>
          </div>
        </div>
      </Modal>

      {/* Modal resetear contraseña */}
      <Modal
        abierto={!!resetUser}
        onCerrar={() => setResetUser(null)}
        titulo={resetUser ? `Resetear contraseña — ${resetUser.codigo_usuario}` : ''}
        acciones={
          <>
            <Button variant="secondary" onClick={() => setResetUser(null)}>Cancelar</Button>
            <Button onClick={guardarReset}>Actualizar contraseña</Button>
          </>
        }
      >
        <div className="space-y-3">
          {resetUser && (
            <div className="flex items-center gap-3 p-3 rounded-lg bg-gov-azulTenue border border-blue-100">
              <div className="w-9 h-9 rounded-full bg-gov-azul flex items-center justify-center text-white text-sm font-bold shrink-0">
                {resetUser.nombre_completo.charAt(0)}
              </div>
              <div>
                <p className="text-sm font-semibold text-gray-800">{resetUser.nombre_completo}</p>
                <p className="text-xs font-mono text-gov-azul">{resetUser.codigo_usuario}</p>
              </div>
            </div>
          )}
          <Input
            label="Nueva contraseña"
            type="password"
            value={nuevaPass}
            onChange={(e) => setNuevaPass(e.target.value)}
            placeholder="Mínimo 8 caracteres"
          />
        </div>
      </Modal>
    </div>
  );
}
