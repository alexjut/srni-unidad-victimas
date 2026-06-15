/**
 * Administración de usuarios — solo administradores.
 * Tabla + crear/editar + activar/desactivar + resetear contraseña.
 */
import { useEffect, useState } from 'react';
import { UserCog, Plus, KeyRound, Power, Pencil, Search } from 'lucide-react';
import { toast } from 'sonner';
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

export default function UsuariosPage() {
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [perfiles, setPerfiles] = useState<Perfil[]>([]);
  const [total, setTotal] = useState(0);
  const [pagina, setPagina] = useState(1);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState('');
  const [busqueda, setBusqueda] = useState('');

  // Modal crear/editar
  const [modalAbierto, setModalAbierto] = useState(false);
  const [editando, setEditando] = useState<Usuario | null>(null);
  const [form, setForm] = useState<FormState>(FORM_VACIO);
  const [guardando, setGuardando] = useState(false);

  // Modal resetear contraseña
  const [resetUser, setResetUser] = useState<Usuario | null>(null);
  const [nuevaPass, setNuevaPass] = useState('');

  function cargar(pag: number, search = busqueda) {
    setCargando(true);
    setError('');
    usuariosApi.lista({
      page: pag, page_size: PAGE_SIZE, ordering: 'codigo_usuario',
      ...(search && { search }),
    })
      .then(({ data }) => { setUsuarios(data.results); setTotal(data.count); })
      .catch(() => setError('No se pudieron cargar los usuarios.'))
      .finally(() => setCargando(false));
  }

  useEffect(() => { cargar(pagina); }, [pagina]);
  useEffect(() => { usuariosApi.perfiles().then(({ data }) => setPerfiles(data)).catch(() => {}); }, []);

  function buscar() { setPagina(1); cargar(1); }

  function abrirCrear() { setEditando(null); setForm(FORM_VACIO); setModalAbierto(true); }

  function abrirEditar(u: Usuario) {
    setEditando(u);
    setForm({
      codigo_usuario: u.codigo_usuario, nombre_completo: u.nombre_completo, email: u.email,
      perfil: u.perfil ? String(u.perfil) : '', activo: u.activo, es_admin: u.es_admin, password: '',
    });
    setModalAbierto(true);
  }

  function guardar() {
    if (!editando && form.password.length < 8) { toast.error('La contraseña debe tener al menos 8 caracteres.'); return; }
    if (!form.perfil) { toast.error('Selecciona un perfil.'); return; }
    setGuardando(true);
    const perfilId = form.perfil ? Number(form.perfil) : null;
    const peticion = editando
      ? usuariosApi.editar(editando.id, {
          nombre_completo: form.nombre_completo, email: form.email,
          perfil: perfilId, activo: form.activo, es_admin: form.es_admin,
        })
      : usuariosApi.crear({
          codigo_usuario: form.codigo_usuario, nombre_completo: form.nombre_completo, email: form.email,
          perfil: perfilId, activo: form.activo, es_admin: form.es_admin, password: form.password,
        });
    peticion
      .then(() => { toast.success(editando ? 'Usuario actualizado' : 'Usuario creado'); setModalAbierto(false); cargar(pagina); })
      .catch((e) => {
        const d = e?.response?.data;
        toast.error(d ? (typeof d === 'string' ? d : Object.values(d).flat().join(' ')) : 'No se pudo guardar.');
      })
      .finally(() => setGuardando(false));
  }

  function toggleActivo(u: Usuario) {
    const fn = u.activo ? usuariosApi.desactivar : usuariosApi.activar;
    fn(u.id)
      .then(() => { toast.success(u.activo ? 'Usuario desactivado' : 'Usuario activado'); cargar(pagina); })
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

  const columnas: Column<Usuario>[] = [
    {
      key: 'codigo_usuario', header: 'Código', className: 'w-32',
      render: (u) => <span className="font-mono text-sm text-gov-azul">{u.codigo_usuario}</span>,
    },
    {
      key: 'nombre_completo', header: 'Nombre',
      render: (u) => (
        <div>
          <p className="text-sm text-gray-800">{u.nombre_completo}</p>
          <p className="text-xs text-gray-400">{u.email}</p>
        </div>
      ),
    },
    {
      key: 'perfil', header: 'Perfil', className: 'w-40',
      render: (u) => (
        <Badge variant={PERFIL_BADGE[u.perfil_codigo] ?? 'gris'}>{u.perfil_nombre || '—'}</Badge>
      ),
    },
    {
      key: 'activo', header: 'Estado', className: 'w-24',
      render: (u) => (
        <span className={`text-xs font-semibold ${u.activo ? 'text-gov-verde' : 'text-gray-400'}`}>
          {u.activo ? 'Activo' : 'Inactivo'}
        </span>
      ),
    },
    {
      key: 'acciones', header: 'Acciones', className: 'w-40',
      render: (u) => (
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="sm" icon={Pencil} onClick={() => abrirEditar(u)} title="Editar" />
          <Button variant="ghost" size="sm" icon={KeyRound} onClick={() => { setResetUser(u); setNuevaPass(''); }} title="Resetear contraseña" />
          <Button variant="ghost" size="sm" icon={Power} onClick={() => toggleActivo(u)} title={u.activo ? 'Desactivar' : 'Activar'} />
        </div>
      ),
    },
  ];

  const opcionesPerfil = perfiles.map((p) => ({ value: String(p.id), label: p.nombre }));

  return (
    <div className="p-4 sm:p-6 max-w-7xl mx-auto">
      <PageHeader titulo="Administración de usuarios" subtitulo={`${total} usuario(s)`} />

      {/* Barra: búsqueda + nuevo */}
      <div className="card mb-6 shadow-soft flex flex-col sm:flex-row gap-3 sm:items-end">
        <div className="flex-1">
          <Input
            label="Buscar" icon={Search} placeholder="Código, nombre o correo"
            value={busqueda} onChange={(e) => setBusqueda(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && buscar()}
          />
        </div>
        <div className="flex gap-2">
          <Button onClick={buscar} className="h-[38px]">Buscar</Button>
          <Button variant="primary" icon={Plus} onClick={abrirCrear} className="h-[38px]">Nuevo usuario</Button>
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
        emptyDescripcion="No se encontraron usuarios."
        pagina={pagina}
        totalPaginas={totalPaginas}
        onPaginaChange={setPagina}
      />

      {/* Modal crear / editar */}
      <Modal
        abierto={modalAbierto}
        onCerrar={() => setModalAbierto(false)}
        titulo={editando ? `Editar ${editando.codigo_usuario}` : 'Nuevo usuario'}
        acciones={
          <>
            <Button variant="secondary" onClick={() => setModalAbierto(false)}>Cancelar</Button>
            <Button onClick={guardar} loading={guardando}>{editando ? 'Guardar' : 'Crear'}</Button>
          </>
        }
      >
        <div className="space-y-3">
          <Input
            label="Código de usuario"
            value={form.codigo_usuario}
            onChange={(e) => setForm({ ...form, codigo_usuario: e.target.value.toUpperCase() })}
            disabled={!!editando}
            placeholder="EJ: ENC006"
          />
          <Input
            label="Nombre completo"
            value={form.nombre_completo}
            onChange={(e) => setForm({ ...form, nombre_completo: e.target.value })}
          />
          <Input
            label="Correo electrónico" type="email"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
          />
          <Select
            label="Perfil"
            options={opcionesPerfil}
            placeholder="Selecciona un perfil"
            value={form.perfil}
            onChange={(e) => setForm({ ...form, perfil: e.target.value })}
          />
          {!editando && (
            <Input
              label="Contraseña" type="password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              placeholder="Mínimo 8 caracteres"
            />
          )}
          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input type="checkbox" checked={form.activo} onChange={(e) => setForm({ ...form, activo: e.target.checked })} />
            Activo
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input type="checkbox" checked={form.es_admin} onChange={(e) => setForm({ ...form, es_admin: e.target.checked })} />
            Acceso al panel de administración de Django (/admin/)
          </label>
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
            <Button onClick={guardarReset}>Actualizar</Button>
          </>
        }
      >
        <Input
          label="Nueva contraseña" type="password"
          value={nuevaPass}
          onChange={(e) => setNuevaPass(e.target.value)}
          placeholder="Mínimo 8 caracteres"
        />
      </Modal>
    </div>
  );
}
