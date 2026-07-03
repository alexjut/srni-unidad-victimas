/**
 * Pantalla: Conformar Hogar
 *
 * Flujo:
 *  1. Al montar: crea el hogar automáticamente en el servidor
 *     (el autorizado queda como primer MiembroHogar — backend lo hace)
 *  2. Muestra la ruta de entrevista y el listado de integrantes (comienza con el autorizado)
 *  3. Formulario para agregar integrantes uno a uno:
 *     Tipo Doc · Número · Primer Nombre · Segundo Nombre ·
 *     Primer Apellido · Segundo Apellido · Fecha Nacimiento · Rol
 *     (Documento oficial §2: el PARENTESCO y el GÉNERO ya NO se piden aquí —
 *      se capturan en el Capítulo B "Datos básicos" para no duplicarlos.
 *      Si el rol es Tutor o Cuidador permanente se exige adjuntar CONSTANCIA.)
 *  4. Botón "Continuar a caracterizaciones" → navega al hub del hogar
 *     (Sprint 14: ya no crea la sesión aquí. La caracterización se inicia
 *      desde el hub, donde el usuario ve el listado de las ya creadas
 *      y puede agregar nuevas con "+ Nueva caracterización".)
 */
import { useState, useEffect, useRef } from 'react';
import {
  View, ScrollView, StyleSheet, Pressable, Modal,
  KeyboardAvoidingView, Platform, Alert,
} from 'react-native';
import {
  Text, TextInput, Button, Divider, Chip, Surface,
  ActivityIndicator, HelperText,
} from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { hogaresApi } from '../../../src/api/hogares';
import * as hogaresOfflineDao from '../../../src/db/hogaresOfflineDao';
import * as miembrosOfflineDao from '../../../src/db/miembrosOfflineDao';
import { cargarMiembrosHogar } from '../../../src/services/miembrosHogar';
import * as colaDao from '../../../src/db/colaDao';
import { useCaracterizacionStore } from '../../../src/stores/caracterizacionStore';
import { useSyncStore } from '../../../src/stores/syncStore';
import { GovHeader } from '../../../src/components/GovHeader';
import { SelectorFecha } from '../../../src/components/SelectorFecha';
import { GovButton } from '../../../src/components/GovButton';
import { GOV, SPACING, RADIUS, SHADOW, FONT } from '../../../src/theme/govTheme';

// ── Catálogos locales ─────────────────────────────────────────────────────────

const TIPOS_DOC = [
  { codigo: 'CC', nombre: 'Cédula de Ciudadanía' },
  { codigo: 'TI', nombre: 'Tarjeta de Identidad' },
  { codigo: 'RC', nombre: 'Registro Civil' },
  { codigo: 'CE', nombre: 'Cédula de Extranjería' },
  { codigo: 'PA', nombre: 'Pasaporte' },
];

// Documento oficial §2: PARENTESCO y GÉNERO ya no se capturan en la conformación
// del hogar (se piden en el Capítulo B "Datos básicos"). Los catálogos se
// eliminaron de esta pantalla para evitar la doble captura.

const RUTAS = [
  { value: 'GENERAL',                   label: 'General' },
  { value: 'ACCIONES_CONSTITUCIONALES', label: 'Acc. Constitucionales' },
  { value: 'MODIFICACION_NUCLEO',       label: 'Mod. Núcleo Familiar' },
  { value: 'ESPECIAL',                  label: 'Ruta Especial' },
];

const ROLES_MIEMBRO = [
  { value: 'MIEMBRO',             label: 'Miembro del hogar' },
  { value: 'TUTOR',               label: 'Tutor — responsable legal de menor' },
  { value: 'CUIDADOR_PERMANENTE', label: 'Cuidador permanente — adulto dependiente' },
];

// Documento oficial §2: al elegir Tutor o Cuidador permanente se debe adjuntar
// una CONSTANCIA (documento/archivo) antes de poder continuar a la entrevista.
const ROLES_CON_CONSTANCIA = ['TUTOR', 'CUIDADOR_PERMANENTE'];
const requiereConstancia = (rol: string) => ROLES_CON_CONSTANCIA.includes(rol);

// ── Tipo local para un integrante ya agregado ─────────────────────────────────

interface IntegranteAgregado {
  key: string;
  es_autorizado: boolean;
  nombre_display: string;        // nombre completo para mostrar
  tipo_documento: string;        // código p.ej. "CC"
  numero_documento: string;
  rol_display: string;
  // §2: parentesco y género ya no se capturan aquí (se piden en el Capítulo B).
  fecha_nacimiento: string;
  /** Nombre de la constancia adjunta (solo Tutor/Cuidador). Vacío si no aplica. */
  constancia_nombre: string;
}

// ── Selector modal genérico ───────────────────────────────────────────────────

interface SelectorModalProps {
  visible: boolean;
  titulo: string;
  opciones: { value: string; label: string }[];
  valorActual: string;
  onSeleccionar: (v: string) => void;
  onCerrar: () => void;
}

function SelectorModal({
  visible, titulo, opciones, valorActual, onSeleccionar, onCerrar,
}: SelectorModalProps) {
  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onCerrar}>
      <Pressable style={styles.modalOverlay} onPress={onCerrar}>
        <View style={styles.modalCard}>
          <View style={styles.modalHandle} />
          <Text style={styles.modalTitulo}>{titulo}</Text>
          {opciones.map((op) => (
            <Pressable
              key={op.value}
              onPress={() => { onSeleccionar(op.value); onCerrar(); }}
              style={[
                styles.modalOpcion,
                op.value === valorActual && styles.modalOpcionActiva,
              ]}
            >
              <Text style={[
                styles.modalOpcionTxt,
                op.value === valorActual && styles.modalOpcionTxtActivo,
              ]}>
                {op.label}
              </Text>
              {op.value === valorActual && (
                <MaterialCommunityIcons name="check" size={18} color={GOV.azul} />
              )}
            </Pressable>
          ))}
        </View>
      </Pressable>
    </Modal>
  );
}

// ── Botón-selector (looks like a TextInput) ───────────────────────────────────

function CampoSelector({
  label, valor, placeholder, error, onPress,
}: { label: string; valor: string; placeholder: string; error?: boolean; onPress: () => void }) {
  return (
    <Pressable onPress={onPress} style={[styles.selectorBtn, error && styles.selectorBtnError]}>
      <Text style={styles.selectorLabel}>{label}</Text>
      <View style={styles.selectorRow}>
        <Text style={[styles.selectorValor, !valor && styles.selectorPlaceholder]} numberOfLines={1}>
          {valor || placeholder}
        </Text>
        <MaterialCommunityIcons name="chevron-down" size={18} color={GOV.textoT} />
      </View>
    </Pressable>
  );
}

// ── Card de integrante ya agregado ────────────────────────────────────────────

function IntegranteCard({ item }: { item: IntegranteAgregado }) {
  return (
    <View style={styles.integranteCard}>
      <View style={styles.integranteIconWrap}>
        <MaterialCommunityIcons
          name={item.es_autorizado ? 'account-star' : 'account'}
          size={20}
          color={item.es_autorizado ? '#FFFFFF' : GOV.azul}
        />
      </View>
      <View style={{ flex: 1 }}>
        <View style={styles.integranteNombreRow}>
          <Text style={styles.integranteNombre} numberOfLines={1}>
            {item.nombre_display}
          </Text>
          {item.es_autorizado && (
            <View style={styles.autorizadoBadge}>
              <Text style={styles.autorizadoBadgeTxt}>★ AUTORIZADO</Text>
            </View>
          )}
        </View>
        <Text style={styles.integranteMeta}>
          {item.tipo_documento} {item.numero_documento}
          {item.rol_display ? `  ·  ${item.rol_display}` : ''}
          {item.fecha_nacimiento ? `  ·  Nac. ${item.fecha_nacimiento}` : ''}
        </Text>
        {item.constancia_nombre ? (
          <View style={styles.constanciaTag}>
            <MaterialCommunityIcons name="paperclip" size={13} color={GOV.verde} />
            <Text style={styles.constanciaTagTxt} numberOfLines={1}>
              Constancia: {item.constancia_nombre}
            </Text>
          </View>
        ) : null}
      </View>
    </View>
  );
}

// ── Pantalla principal ────────────────────────────────────────────────────────

export default function ConformarHogarScreen() {
  const {
    victimaFuente,
    victimaLocalId,
    rutaEntrevista,
    setRutaEntrevista,
    setHogarId,
    limpiar,
  } = useCaracterizacionStore();
  const estaOnline = useSyncStore((s) => s.estaOnline);
  const refrescarContadores = useSyncStore((s) => s.refrescarContadores);

  // Estado del hogar
  const [hogarId, setHogarIdLocal]    = useState<string | null>(null);
  // Fase A: true si el hogar se creó OFFLINE (hogarId es un id_local, no servidor).
  // Determina si agregarIntegrante encola o hace POST directo.
  const [hogarEsLocal, setHogarEsLocal] = useState(false);
  const [creandoHogar, setCreandoHogar] = useState(true);
  const [errorHogar, setErrorHogar]   = useState('');

  // Integrantes ya agregados (el autorizado se agrega al inicio)
  const [integrantes, setIntegrantes] = useState<IntegranteAgregado[]>([]);

  // Formulario nuevo integrante
  const [tipoDoc,      setTipoDoc]      = useState('CC');
  const [numDoc,       setNumDoc]       = useState('');
  const [primerNombre, setPrimerNombre] = useState('');
  const [segNombre,    setSegNombre]    = useState('');
  const [primerApell,  setPrimerApell]  = useState('');
  const [segApell,     setSegApell]     = useState('');
  const [fechaNac,     setFechaNac]     = useState('');
  const [rolMiembro,   setRolMiembro]   = useState('MIEMBRO');
  // §2 — constancia obligatoria para Tutor/Cuidador. Guardamos una referencia
  // del archivo (nombre + uri si el picker existe). Vacío = aún sin adjuntar.
  const [constanciaNombre, setConstanciaNombre] = useState('');
  const [constanciaUri,    setConstanciaUri]    = useState('');
  const [erroresForm,  setErroresForm]  = useState<Record<string, string>>({});
  const [agregando,    setAgregando]    = useState(false);

  // Modales selectores
  const [modalTipoDoc,    setModalTipoDoc]    = useState(false);
  const [modalRol,        setModalRol]        = useState(false);
  const [modalRuta,       setModalRuta]       = useState(false);

  // Continuar al hub de caracterizaciones
  const [continuando, setContinuando] = useState(false);
  const [errorInicio, setErrorInicio] = useState('');

  // ── Crear hogar al montar ─────────────────────────────────────────────────
  useEffect(() => {
    async function crearHogar() {
      if (!victimaLocalId) {
        setErrorHogar('No hay autorizado seleccionado. Vuelve a buscar la víctima.');
        setCreandoHogar(false);
        return;
      }
      // Sin red: crea el hogar OFFLINE (id_local) + encola CREAR_HOGAR, igual que
      // hogares/nuevo.tsx. El autorizado es el victimaLocalId (UUID local o servidor).
      const crearOffline = async () => {
        const hogarLocal = await hogaresOfflineDao.crearHogarOffline({
          jefe_hogar_uuid: victimaLocalId,
          numero_personas: 1,
        });
        await colaDao.encolar('CREAR_HOGAR', hogarLocal.id_local, {
          id_local: hogarLocal.id_local,
          autorizado: victimaLocalId,
          numero_personas: 1,
        });
        await refrescarContadores();
        setHogarIdLocal(hogarLocal.id_local);
        setHogarId(hogarLocal.id_local);
        setHogarEsLocal(true);
      };

      try {
        if (estaOnline) {
          try {
            // Camino feliz online: el backend auto-inserta al autorizado.
            const { data } = await hogaresApi.crear({
              autorizado: victimaLocalId,
              numero_personas: 1,
            });
            setHogarIdLocal(data.id);
            setHogarId(data.id);
            setHogarEsLocal(false);
          } catch (err: any) {
            if (err?.response) throw err; // error real del servidor → propagar
            // Sin respuesta = red caída aunque la bandera dijera online → offline.
            await crearOffline();
          }
        } else {
          await crearOffline();
        }

        // Autorizado como primer integrante (online lo agrega el backend; offline
        // se mostrará y se incluye en numero_personas). Solo es presentación local.
        const v = victimaFuente;
        const nombreAutorizado = v
          ? [v.primer_nombre, v.segundo_nombre, v.primer_apellido, v.segundo_apellido]
              .filter(Boolean).join(' ')
          : 'Autorizado';
        setIntegrantes([{
          key: 'autorizado',
          es_autorizado: true,
          nombre_display: nombreAutorizado,
          tipo_documento: v?.tipo_documento ?? '',
          numero_documento: v?.numero_documento ?? '',
          rol_display: 'Autorizado',
          fecha_nacimiento: '',
          constancia_nombre: '',
        }]);
      } catch (err: any) {
        const detalle = err?.response?.data;
        if (typeof detalle === 'object') {
          setErrorHogar(JSON.stringify(detalle));
        } else {
          const msg = err?.message ? ` (${String(err.message).slice(0, 140)})` : '';
          setErrorHogar(`No se pudo crear el hogar.${msg}`);
        }
      } finally {
        setCreandoHogar(false);
      }
    }
    crearHogar();
  }, []);

  // ── Validar formulario de nuevo integrante ────────────────────────────────
  function validarFormulario(): boolean {
    const e: Record<string, string> = {};
    if (!primerNombre.trim())  e.primerNombre = 'Requerido';
    if (!primerApell.trim())   e.primerApell  = 'Requerido';
    // §2: parentesco y género ya NO se validan aquí (se piden en el Capítulo B).
    // §2: Tutor/Cuidador permanente requieren constancia adjunta para agregarse.
    if (requiereConstancia(rolMiembro) && !constanciaNombre) {
      e.constancia = 'Adjunte la constancia del rol seleccionado';
    }
    if (fechaNac && !/^\d{4}-\d{2}-\d{2}$/.test(fechaNac)) {
      e.fechaNac = 'Formato: AAAA-MM-DD';
    }
    setErroresForm(e);
    return Object.keys(e).length === 0;
  }

  // ── Agregar integrante ────────────────────────────────────────────────────
  async function agregarIntegrante() {
    if (!validarFormulario() || !hogarId) return;
    setAgregando(true);

    const nombreCompleto = [primerNombre, segNombre, primerApell, segApell]
      .map(s => s.trim()).filter(Boolean).join(' ');

    const miembroPayload = {
      nombre_completo: nombreCompleto,
      // #3 — el número de documento se capturaba pero NUNCA se enviaba ni se
      // encolaba (se perdía). El backend lo acepta (write-only, sin exigir el
      // tipo). El tipo_documento es FK por id numérico y el form usa códigos,
      // así que se omite hasta tener el mapeo código→id (paramétrica).
      numero_documento: numDoc.trim() || undefined,
      // §2: parentesco y género ya NO se envían desde la conformación — se
      // capturan en el Capítulo B (Datos básicos). El backend los acepta vacíos.
      rol: rolMiembro as 'MIEMBRO' | 'TUTOR' | 'CUIDADOR_PERMANENTE',
      estado_inclusion: 'NO_INCLUIDO' as const,
      fecha_nacimiento: fechaNac || undefined,
      // §2: referencia de la constancia (Tutor/Cuidador). El backend la ignora
      // por ahora (no está en AgregarMiembroSerializer); viaja en el payload
      // offline/online para no perderla. Pendiente: campo/almacenamiento real.
      ...(requiereConstancia(rolMiembro) && constanciaNombre
        ? { constancia_nombre: constanciaNombre, constancia_uri: constanciaUri || undefined }
        : {}),
    };

    // Guarda el integrante offline (SQLite + cola). Reutilizado por el camino
    // offline directo y por el fallback cuando se cae la red en el camino online.
    const guardarOffline = async () => {
      const miembroLocal = await miembrosOfflineDao.crearMiembroOffline(hogarId, miembroPayload);
      await colaDao.encolar('AGREGAR_MIEMBRO', miembroLocal.id_local, {
        id_local: miembroLocal.id_local,
        hogar: hogarId,
        miembro: miembroPayload,
      });
      await refrescarContadores();
    };

    let guardado = false;
    try {
      if (hogarEsLocal) {
        // Fase A — sin red: el `hogar` se referencia por su id_local;
        // procesarCrearHogar lo remapea a su id de servidor antes de procesar
        // este AGREGAR_MIEMBRO.
        await guardarOffline();
      } else {
        // Online: POST directo al servidor.
        await hogaresApi.agregarMiembro(hogarId, miembroPayload);
      }
      guardado = true;
    } catch (err: any) {
      // El hogar es de servidor pero perdimos la red (o el id aún no propagó):
      // guardar el integrante offline en vez de bloquear al encuestador en campo.
      const sinRed = !err?.response;
      const hogarNoEnServidor = err?.response?.status === 400 || err?.response?.status === 404;
      if (!hogarEsLocal && (sinRed || hogarNoEnServidor)) {
        try {
          await guardarOffline();
          guardado = true;
        } catch { /* fallo de SQLite — se informa abajo */ }
      }
      if (!guardado) {
        Alert.alert(
          'Error al agregar',
          err?.response?.data?.detail ?? 'No se pudo agregar el integrante. Intente nuevamente.',
        );
      }
    }

    if (guardado) {
      const rolLabel = ROLES_MIEMBRO.find(r => r.value === rolMiembro)?.label ?? rolMiembro;
      setIntegrantes(prev => [
        ...prev,
        {
          key: `${Date.now()}`,
          es_autorizado: false,
          nombre_display: nombreCompleto,
          tipo_documento: tipoDoc,
          numero_documento: numDoc,
          rol_display: rolLabel,
          fecha_nacimiento: fechaNac,
          constancia_nombre: requiereConstancia(rolMiembro) ? constanciaNombre : '',
        },
      ]);

      // Limpiar formulario para el siguiente
      setTipoDoc('CC'); setNumDoc(''); setPrimerNombre(''); setSegNombre('');
      setPrimerApell(''); setSegApell(''); setFechaNac('');
      setRolMiembro('MIEMBRO');
      setConstanciaNombre(''); setConstanciaUri('');
      setErroresForm({});
    }
    setAgregando(false);
  }

  // ── Adjuntar constancia (§2) ──────────────────────────────────────────────
  // Tutor/Cuidador permanente deben cargar una constancia antes de continuar.
  //
  // PENDIENTE DE DEPENDENCIA: el selector de archivos real requiere
  // `expo-document-picker` (o `expo-image-picker`), que NO está instalado.
  // Hasta instalarlo, intentamos cargarlo dinámicamente; si no existe, se
  // registra una referencia-marcador para no bloquear el flujo en campo y se
  // informa al usuario. Al instalar la dep, este handler usará el picker real
  // sin más cambios en la UI.
  async function adjuntarConstancia() {
    try {
      // Carga perezosa: si algún día se instala expo-document-picker, se usa.
      // eslint-disable-next-line @typescript-eslint/no-var-requires
      const picker: any = require('expo-document-picker');
      const res = await picker.getDocumentAsync({ copyToCacheDirectory: true });
      // API nueva (SDK 49+): { canceled, assets: [{ name, uri }] }
      const asset = res?.assets?.[0];
      if (res?.canceled || !asset) return;
      setConstanciaNombre(asset.name ?? 'constancia');
      setConstanciaUri(asset.uri ?? '');
      setErroresForm(prev => { const { constancia, ...rest } = prev; return rest; });
    } catch (err: any) {
      // La dependencia no está instalada (MODULE_NOT_FOUND) o el picker falló.
      // Placeholder: registrar una referencia-marcador para desbloquear el flujo
      // y dejar explícito el pendiente. NO simula un archivo real.
      const esModuloFaltante =
        err?.code === 'MODULE_NOT_FOUND' ||
        /Cannot find module|expo-document-picker/i.test(String(err?.message ?? ''));
      const marcador = `constancia-pendiente-${Date.now()}.ref`;
      setConstanciaNombre(marcador);
      setConstanciaUri('');
      setErroresForm(prev => { const { constancia, ...rest } = prev; return rest; });
      Alert.alert(
        'Constancia registrada (pendiente de archivo)',
        esModuloFaltante
          ? 'El selector de archivos aún no está disponible en esta versión. Se '
            + 'registró la exigencia de la constancia para poder continuar; el '
            + 'archivo deberá adjuntarse cuando se habilite el cargador.'
          : 'No se pudo abrir el selector de archivos. Se registró la constancia '
            + 'como pendiente para no bloquear la entrevista.',
      );
    }
  }

  function quitarConstancia() {
    setConstanciaNombre('');
    setConstanciaUri('');
  }

  // ── Continuar al hub de caracterizaciones (Sprint 14) ─────────────────────
  // El hogar ya fue creado al montar la pantalla. Aquí solo navegamos al
  // listado de caracterizaciones del hogar — desde allí el usuario decide
  // si crea una nueva (con instrumento + ruta) o entra a una existente.
  async function continuarACaracterizaciones() {
    if (!hogarId) return;
    setContinuando(true);
    setErrorInicio('');
    try {
      if (hogarEsLocal) {
        // Fase A — sin red: el hub de caracterizaciones requiere GET /hogares/{id}/
        // (404 con un id_local). Vamos directo a seleccionar instrumento y crear
        // la sesión OFFLINE (borrador + cola), saltando el hub que necesita servidor.
        router.replace({
          pathname: '/(main)/caracterizar',
          params: { hogarId },
        });
      } else {
        // Warm-up de la caché de miembros (fix #4/#38): si la red cae justo
        // después de continuar, la caracterización ya tendrá los miembros del
        // servidor para capturar offline. Best-effort, no bloquea el flujo.
        try { await cargarMiembrosHogar(hogarId); }
        catch { /* la caché se poblará al cargar el hub/capítulo online */ }
        router.replace({
          pathname: '/(main)/hogares/[hogarId]/caracterizaciones',
          params: { hogarId },
        });
      }
    } catch (err: any) {
      setErrorInicio('No se pudo continuar. Intente nuevamente.');
    } finally {
      setContinuando(false);
    }
  }

  // Back coherente: vuelve a la pantalla de búsqueda (padre conceptual del flujo).
  // Evita `router.back()` ciego que puede saltar al home si la pila se rompió.
  const volverABusqueda = () => router.push('/(main)/busqueda');

  // ── Render: cargando hogar ────────────────────────────────────────────────
  if (creandoHogar) {
    return (
      <View style={styles.root}>
        <GovHeader title="Conformar Hogar" onBack={volverABusqueda} />
        <View style={styles.miga}>
          <Text style={styles.migaTxt}>Búsqueda  ›  Conformar hogar</Text>
        </View>
        <View style={styles.centrado}>
          <ActivityIndicator size="large" color={GOV.azul} />
          <Text style={styles.cargandoTxt}>
            {estaOnline ? 'Registrando hogar…' : 'Guardando hogar offline…'}
          </Text>
        </View>
      </View>
    );
  }

  if (errorHogar) {
    return (
      <View style={styles.root}>
        <GovHeader title="Conformar Hogar" onBack={volverABusqueda} />
        <View style={styles.miga}>
          <Text style={styles.migaTxt}>Búsqueda  ›  Conformar hogar</Text>
        </View>
        <View style={styles.centrado}>
          <MaterialCommunityIcons name="alert-circle-outline" size={48} color={GOV.rojo} />
          <Text style={[styles.cargandoTxt, { color: GOV.rojo, marginTop: SPACING.sm }]}>
            {errorHogar}
          </Text>
          <Button mode="outlined" onPress={volverABusqueda} style={{ marginTop: SPACING.md }}>
            Volver
          </Button>
        </View>
      </View>
    );
  }

  const rutaLabel = RUTAS.find(r => r.value === rutaEntrevista)?.label ?? 'General';

  // §2 — si en el formulario hay un Tutor/Cuidador a medio capturar sin su
  // constancia, se bloquea Continuar para no perder ese integrante ni saltarse
  // la constancia obligatoria.
  const constanciaPendienteEnForm =
    requiereConstancia(rolMiembro) && !constanciaNombre;

  return (
    <View style={styles.root}>
      <GovHeader
        title="Conformar Hogar"
        subtitle={`${integrantes.length} integrante${integrantes.length !== 1 ? 's' : ''}`}
        onBack={volverABusqueda}
      />

      {/* Miga de pan */}
      <View style={styles.miga}>
        <Text style={styles.migaTxt}>Búsqueda  ›  Conformar hogar</Text>
      </View>

      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <ScrollView
          contentContainerStyle={styles.content}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >

          {hogarEsLocal && (
            <Chip
              icon="wifi-off"
              mode="flat"
              style={styles.offlineBanner}
              textStyle={styles.offlineBannerTxt}
            >
              Sin conexión — hogar e integrantes se guardan localmente y se sincronizan al recuperar señal
            </Chip>
          )}

          {/* ── Ruta de entrevista ── */}
          <Text style={styles.secTitulo}>Ruta de entrevista</Text>
          <CampoSelector
            label="Ruta"
            valor={rutaLabel}
            placeholder="Seleccionar ruta"
            onPress={() => setModalRuta(true)}
          />

          <Divider style={styles.divider} />

          {/* ── Integrantes actuales ── */}
          <Text style={styles.secTitulo}>
            Integrantes del hogar ({integrantes.length})
          </Text>
          {integrantes.map(item => (
            <IntegranteCard key={item.key} item={item} />
          ))}

          <Divider style={styles.divider} />

          {/* ── Formulario agregar integrante ── */}
          <Text style={styles.secTitulo}>Agregar integrante</Text>

          {/* Fila: Tipo Doc + Número Documento */}
          <View style={styles.fila}>
            <View style={{ flex: 1 }}>
              <CampoSelector
                label="Tipo Documento"
                valor={TIPOS_DOC.find(t => t.codigo === tipoDoc)?.nombre ?? tipoDoc}
                placeholder="Tipo Doc"
                onPress={() => setModalTipoDoc(true)}
              />
            </View>
            <View style={{ flex: 2 }}>
              <TextInput
                label="Número de Documento"
                value={numDoc}
                onChangeText={setNumDoc}
                mode="outlined"
                keyboardType="numeric"
                style={styles.input}
                activeOutlineColor={GOV.azul}
              />
            </View>
          </View>

          {/* Fila: Primer Nombre + Segundo Nombre */}
          <View style={styles.fila}>
            <TextInput
              label="Primer Nombre *"
              value={primerNombre}
              onChangeText={setPrimerNombre}
              mode="outlined"
              autoCapitalize="characters"
              style={[styles.input, { flex: 1 }]}
              activeOutlineColor={GOV.azul}
              error={!!erroresForm.primerNombre}
            />
            <TextInput
              label="Segundo Nombre"
              value={segNombre}
              onChangeText={setSegNombre}
              mode="outlined"
              autoCapitalize="characters"
              style={[styles.input, { flex: 1 }]}
              activeOutlineColor={GOV.azul}
            />
          </View>
          {erroresForm.primerNombre
            ? <HelperText type="error">{erroresForm.primerNombre}</HelperText>
            : null}

          {/* Fila: Primer Apellido + Segundo Apellido */}
          <View style={styles.fila}>
            <TextInput
              label="Primer Apellido *"
              value={primerApell}
              onChangeText={setPrimerApell}
              mode="outlined"
              autoCapitalize="characters"
              style={[styles.input, { flex: 1 }]}
              activeOutlineColor={GOV.azul}
              error={!!erroresForm.primerApell}
            />
            <TextInput
              label="Segundo Apellido"
              value={segApell}
              onChangeText={setSegApell}
              mode="outlined"
              autoCapitalize="characters"
              style={[styles.input, { flex: 1 }]}
              activeOutlineColor={GOV.azul}
            />
          </View>
          {erroresForm.primerApell
            ? <HelperText type="error">{erroresForm.primerApell}</HelperText>
            : null}

          {/* Fecha de Nacimiento — Sprint 21: calendario nativo en lugar de input */}
          <View style={styles.input}>
            <SelectorFecha
              valor={fechaNac}
              onChange={setFechaNac}
              label="Fecha de nacimiento"
              permitirFuturo={false}
            />
          </View>
          {erroresForm.fechaNac
            ? <HelperText type="error">{erroresForm.fechaNac}</HelperText>
            : null}

          {/* §2 — Parentesco y Género ya NO se piden aquí: se capturan en el
              Capítulo B (Datos básicos) para evitar la doble captura. */}
          <View style={styles.notaB}>
            <MaterialCommunityIcons name="information-outline" size={16} color={GOV.azulOscuro} />
            <Text style={styles.notaBTxt}>
              El parentesco y el género se registran en el Capítulo B (Datos básicos)
              durante la entrevista.
            </Text>
          </View>

          {/* Rol en el hogar */}
          <CampoSelector
            label="Rol en el hogar"
            valor={ROLES_MIEMBRO.find(r => r.value === rolMiembro)?.label ?? rolMiembro}
            placeholder="Seleccionar rol"
            onPress={() => setModalRol(true)}
          />

          {/* §2 — Constancia obligatoria para Tutor / Cuidador permanente */}
          {requiereConstancia(rolMiembro) && (
            <View style={styles.constanciaBox}>
              <Text style={styles.constanciaTitulo}>
                Constancia obligatoria
              </Text>
              <Text style={styles.constanciaAyuda}>
                El rol seleccionado exige adjuntar el documento que acredita la
                tutoría o el cuidado permanente.
              </Text>

              {constanciaNombre ? (
                <View style={styles.constanciaFila}>
                  <MaterialCommunityIcons name="file-check-outline" size={18} color={GOV.verde} />
                  <Text style={styles.constanciaArchivo} numberOfLines={1}>
                    {constanciaNombre}
                  </Text>
                  <Pressable onPress={quitarConstancia} hitSlop={8}>
                    <MaterialCommunityIcons name="close-circle" size={18} color={GOV.textoT} />
                  </Pressable>
                </View>
              ) : null}

              <Button
                mode="outlined"
                icon="paperclip"
                onPress={adjuntarConstancia}
                style={styles.btnConstancia}
                textColor={GOV.azul}
              >
                {constanciaNombre ? 'Cambiar constancia' : 'Adjuntar constancia'}
              </Button>

              {erroresForm.constancia
                ? <HelperText type="error">{erroresForm.constancia}</HelperText>
                : null}
            </View>
          )}

          {/* Botón Agregar */}
          <Button
            mode="outlined"
            icon={agregando ? undefined : 'account-plus'}
            onPress={agregarIntegrante}
            disabled={agregando || !hogarId}
            loading={agregando}
            style={styles.btnAgregar}
            textColor={GOV.azul}
          >
            {agregando ? 'Agregando…' : 'Agregar al hogar'}
          </Button>

          <Divider style={styles.divider} />

          {/* ── Continuar a caracterizaciones (Sprint 14) ── */}
          {errorInicio ? (
            <Text style={styles.errorTxt}>{errorInicio}</Text>
          ) : null}

          {constanciaPendienteEnForm ? (
            <Text style={styles.errorTxt}>
              Adjunte la constancia del Tutor/Cuidador o cambie su rol antes de continuar.
            </Text>
          ) : null}

          <GovButton
            label={`Continuar a caracterizaciones (${integrantes.length} integrante${integrantes.length !== 1 ? 's' : ''})`}
            icon="arrow-right-circle"
            onPress={continuarACaracterizaciones}
            loading={continuando}
            disabled={!hogarId || continuando || constanciaPendienteEnForm}
          />

          <Button
            mode="text"
            onPress={() => {
              limpiar();
              volverABusqueda();
            }}
            style={{ marginTop: SPACING.xs }}
            textColor={GOV.textoT}
          >
            Cancelar y volver
          </Button>

        </ScrollView>
      </KeyboardAvoidingView>

      {/* ── Modales de selección ── */}
      <SelectorModal
        visible={modalRuta}
        titulo="Ruta de entrevista"
        opciones={RUTAS}
        valorActual={rutaEntrevista ?? 'GENERAL'}
        onSeleccionar={setRutaEntrevista}
        onCerrar={() => setModalRuta(false)}
      />
      <SelectorModal
        visible={modalTipoDoc}
        titulo="Tipo de Documento"
        opciones={TIPOS_DOC.map(t => ({ value: t.codigo, label: t.nombre }))}
        valorActual={tipoDoc}
        onSeleccionar={setTipoDoc}
        onCerrar={() => setModalTipoDoc(false)}
      />
      <SelectorModal
        visible={modalRol}
        titulo="Rol en el hogar"
        opciones={ROLES_MIEMBRO}
        valorActual={rolMiembro}
        onSeleccionar={setRolMiembro}
        onCerrar={() => setModalRol(false)}
      />
    </View>
  );
}

// ── Estilos ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: GOV.fondoApp,
  },
  miga: {
    backgroundColor: GOV.azulTenue,
    paddingHorizontal: SPACING.md,
    paddingVertical: 6,
    borderBottomWidth: 1,
    borderBottomColor: GOV.borde,
  },
  migaTxt: {
    ...FONT.caption,
    color: GOV.azulOscuro,
  },
  centrado: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: SPACING.xl,
  },
  cargandoTxt: {
    marginTop: SPACING.md,
    ...FONT.body,
    color: GOV.textoS,
    textAlign: 'center',
  },
  content: {
    padding: SPACING.md,
    paddingBottom: 48,
  },
  offlineBanner: { marginBottom: SPACING.md, backgroundColor: '#FFF3E0' },
  offlineBannerTxt: { color: '#E65100', fontSize: 12 },
  secTitulo: {
    ...FONT.label,
    color: GOV.textoT,
    textTransform: 'uppercase',
    letterSpacing: 0.8,
    marginBottom: SPACING.sm,
    marginTop: SPACING.xs,
  },
  divider: {
    marginVertical: SPACING.md,
  },

  // ── Selector ──────────────────────────────────────────────────────────────
  selectorBtn: {
    backgroundColor: GOV.superficie,
    borderWidth: 1,
    borderColor: GOV.borde,
    borderRadius: RADIUS.sm,
    paddingHorizontal: SPACING.sm,
    paddingVertical: 10,
    marginBottom: SPACING.sm,
  },
  selectorBtnError: {
    borderColor: GOV.rojo,
  },
  selectorLabel: {
    ...FONT.caption,
    color: GOV.textoT,
    marginBottom: 2,
  },
  selectorRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  selectorValor: {
    ...FONT.body,
    color: GOV.textoP,
    flex: 1,
  },
  selectorPlaceholder: {
    color: GOV.textoT,
  },

  // ── Inputs ────────────────────────────────────────────────────────────────
  fila: {
    flexDirection: 'row',
    gap: SPACING.sm,
    marginBottom: 0,
  },
  input: {
    backgroundColor: '#FFFFFF',
    marginBottom: SPACING.sm,
  },

  // ── Integrante card ───────────────────────────────────────────────────────
  integranteCard: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    backgroundColor: GOV.superficie,
    borderRadius: RADIUS.md,
    padding: SPACING.sm,
    marginBottom: SPACING.sm,
    ...SHADOW.card,
    gap: SPACING.sm,
  },
  integranteIconWrap: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: GOV.azulTenue,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 2,
  },
  integranteNombreRow: {
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: 6,
    marginBottom: 3,
  },
  integranteNombre: {
    ...FONT.body,
    fontWeight: '700',
    color: GOV.textoP,
    flexShrink: 1,
  },
  autorizadoBadge: {
    backgroundColor: GOV.azulOscuro,
    borderRadius: RADIUS.pill,
    paddingHorizontal: 7,
    paddingVertical: 2,
  },
  autorizadoBadgeTxt: {
    fontSize: 9,
    fontWeight: '800',
    color: '#FFFFFF',
    letterSpacing: 0.5,
  },
  integranteMeta: {
    ...FONT.caption,
    color: GOV.textoS,
  },

  // ── Nota Capítulo B (parentesco/género se piden allí) ───────────────────────
  notaB: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 6,
    backgroundColor: GOV.azulTenue,
    borderRadius: RADIUS.sm,
    padding: SPACING.sm,
    marginBottom: SPACING.sm,
  },
  notaBTxt: {
    ...FONT.caption,
    color: GOV.azulOscuro,
    flex: 1,
  },

  // ── Constancia (Tutor/Cuidador) ─────────────────────────────────────────────
  constanciaBox: {
    backgroundColor: GOV.verdeTenue,
    borderRadius: RADIUS.sm,
    borderWidth: 1,
    borderColor: GOV.verde,
    padding: SPACING.sm,
    marginTop: SPACING.sm,
    marginBottom: SPACING.xs,
  },
  constanciaTitulo: {
    ...FONT.label,
    color: GOV.verde,
    fontWeight: '700',
    marginBottom: 2,
  },
  constanciaAyuda: {
    ...FONT.caption,
    color: GOV.textoS,
    marginBottom: SPACING.sm,
  },
  constanciaFila: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: '#FFFFFF',
    borderRadius: RADIUS.sm,
    paddingHorizontal: SPACING.sm,
    paddingVertical: 8,
    marginBottom: SPACING.sm,
  },
  constanciaArchivo: {
    ...FONT.body,
    color: GOV.textoP,
    flex: 1,
  },
  btnConstancia: {
    borderColor: GOV.azul,
    borderRadius: RADIUS.sm,
  },
  constanciaTag: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginTop: 4,
  },
  constanciaTagTxt: {
    ...FONT.caption,
    color: GOV.verde,
    flex: 1,
  },

  // ── Botones ───────────────────────────────────────────────────────────────
  btnAgregar: {
    marginTop: SPACING.xs,
    borderColor: GOV.azul,
    borderRadius: RADIUS.sm,
  },
  errorTxt: {
    ...FONT.small,
    color: GOV.rojo,
    textAlign: 'center',
    marginBottom: SPACING.sm,
  },

  // ── Modal ─────────────────────────────────────────────────────────────────
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.45)',
    justifyContent: 'flex-end',
  },
  modalCard: {
    backgroundColor: '#FFFFFF',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    paddingHorizontal: SPACING.md,
    paddingBottom: 32,
    paddingTop: SPACING.sm,
  },
  modalHandle: {
    width: 36,
    height: 4,
    backgroundColor: GOV.borde,
    borderRadius: 2,
    alignSelf: 'center',
    marginBottom: SPACING.sm,
  },
  modalTitulo: {
    ...FONT.h3,
    fontWeight: '700',
    color: GOV.azulOscuro,
    marginBottom: SPACING.sm,
  },
  modalOpcion: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 13,
    paddingHorizontal: SPACING.sm,
    borderRadius: RADIUS.sm,
    marginBottom: 2,
  },
  modalOpcionActiva: {
    backgroundColor: GOV.azulTenue,
  },
  modalOpcionTxt: {
    ...FONT.body,
    color: GOV.textoP,
  },
  modalOpcionTxtActivo: {
    color: GOV.azul,
    fontWeight: '700',
  },
});
