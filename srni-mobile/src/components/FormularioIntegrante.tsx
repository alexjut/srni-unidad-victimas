/**
 * Formulario para agregar UN integrante al hogar (con señal o sin ella).
 *
 * Vivía dentro de `hogares/conformar.tsx`, que era el único lugar donde se podía
 * agregar a alguien. QA reportó el 16-sep-2026 que si llega una persona del
 * hogar a mitad de la caracterización —o se salieron de la conformación por
 * error— no había forma de agregarla. Se sacó a este componente para usarlo
 * también desde la entrevista (`hogares/[hogarId]/agregar-integrante`) sin
 * duplicar la captura, la constancia de Tutor/Cuidador ni el camino offline.
 *
 * Campos: Tipo Doc · Número · Nombres · Apellidos · Fecha de nacimiento · Rol.
 * (Documento oficial §2: parentesco y género NO se piden aquí — se capturan en
 * el Capítulo B «Datos básicos» para no duplicarlos.)
 */
import { useEffect, useState } from 'react';
import { View, StyleSheet, Pressable, Modal, Alert } from 'react-native';
import { Text, TextInput, Button, HelperText } from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { hogaresApi } from '../api/hogares';
import * as miembrosOfflineDao from '../db/miembrosOfflineDao';
import * as colaDao from '../db/colaDao';
import { useSyncStore } from '../stores/syncStore';
import { SelectorFecha } from './SelectorFecha';
import { GOV, SPACING, RADIUS, FONT } from '../theme/govTheme';
import { interpretarError } from '../utils/errores';
import { reportarError } from '../services/errorReporter';

// ── Catálogos ─────────────────────────────────────────────────────────────────

export const TIPOS_DOC = [
  { codigo: 'CC', nombre: 'Cédula de Ciudadanía' },
  { codigo: 'TI', nombre: 'Tarjeta de Identidad' },
  { codigo: 'RC', nombre: 'Registro Civil' },
  { codigo: 'CE', nombre: 'Cédula de Extranjería' },
  { codigo: 'PA', nombre: 'Pasaporte' },
];

export const ROLES_MIEMBRO = [
  { value: 'MIEMBRO',             label: 'Miembro del hogar' },
  { value: 'TUTOR',               label: 'Tutor — responsable legal de menor' },
  { value: 'CUIDADOR_PERMANENTE', label: 'Cuidador permanente — adulto dependiente' },
];

// Documento oficial §2: al elegir Tutor o Cuidador permanente se debe adjuntar
// una CONSTANCIA (documento/archivo) antes de poder continuar a la entrevista.
const ROLES_CON_CONSTANCIA = ['TUTOR', 'CUIDADOR_PERMANENTE'];
export const requiereConstancia = (rol: string) => ROLES_CON_CONSTANCIA.includes(rol);

/** Solo dígitos y letras, en mayúscula: «1.030.547» y «1030547» son el mismo documento. */
export function normalizarDocumento(doc: string | null | undefined): string {
  return (doc ?? '').replace(/[^0-9a-z]/gi, '').toUpperCase();
}

// ── Integrante recién agregado (lo que recibe la pantalla que lo usa) ─────────

export interface IntegranteNuevo {
  /** Id en el servidor. Solo si se agregó con señal (permite quitarlo después). */
  miembro_id?: string;
  nombre_display: string;
  tipo_documento: string;
  numero_documento: string;
  rol_display: string;
  fecha_nacimiento: string;
  /** Nombre de la constancia adjunta (solo Tutor/Cuidador). Vacío si no aplica. */
  constancia_nombre: string;
  /** true si quedó en la cola por falta de señal. */
  offline: boolean;
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

export function SelectorModal({
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

// ── Botón-selector (se ve como un TextInput) ──────────────────────────────────

export function CampoSelector({
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

// ── Formulario ────────────────────────────────────────────────────────────────

interface Props {
  hogarId: string | null;
  /** true si el hogar se creó sin red: su id es local y el alta va directo a la cola. */
  hogarEsLocal: boolean;
  onAgregado: (integrante: IntegranteNuevo) => void;
  /** Avisa si hay un Tutor/Cuidador a medio capturar sin su constancia. */
  onConstanciaPendienteChange?: (pendiente: boolean) => void;
  /**
   * Documentos de quienes ya están en el hogar. `agregar-miembro` no deduplica en
   * el servidor, así que un mismo documento dos veces deja a la persona duplicada.
   */
  documentosExistentes?: string[];
  /** Nombre de la pantalla para los reportes de error. */
  pantalla: string;
  textoBoton?: string;
}

export function FormularioIntegrante({
  hogarId, hogarEsLocal, onAgregado, onConstanciaPendienteChange,
  documentosExistentes = [], pantalla, textoBoton = 'Agregar al hogar',
}: Props) {
  const refrescarContadores = useSyncStore((s) => s.refrescarContadores);

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

  const [modalTipoDoc, setModalTipoDoc] = useState(false);
  const [modalRol,     setModalRol]     = useState(false);

  const constanciaPendiente = requiereConstancia(rolMiembro) && !constanciaNombre;
  useEffect(() => {
    onConstanciaPendienteChange?.(constanciaPendiente);
  }, [constanciaPendiente, onConstanciaPendienteChange]);

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
    const doc = normalizarDocumento(numDoc);
    if (doc && documentosExistentes.some((d) => normalizarDocumento(d) === doc)) {
      e.numDoc = 'Ya hay un integrante con este documento en el hogar';
    }
    setErroresForm(e);
    return Object.keys(e).length === 0;
  }

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
      // El integrante se captura a mano, sin cruzarlo contra el padrón: su
      // condición en el RUV queda por verificar, no negada.
      estado_inclusion: 'NO_VERIFICADO' as const,
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
    let offline = false;
    let idEnServidor: string | undefined;
    try {
      if (hogarEsLocal) {
        // Fase A — sin red: el `hogar` se referencia por su id_local;
        // procesarCrearHogar lo remapea a su id de servidor antes de procesar
        // este AGREGAR_MIEMBRO.
        await guardarOffline();
        offline = true;
      } else {
        // Online: POST directo al servidor. Se guarda el id que devuelve —sin
        // él después no hay a quién borrar si lo agregaron por error (APK-004).
        const { data } = await hogaresApi.agregarMiembro(hogarId, miembroPayload);
        idEnServidor = data?.id;
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
          offline = true;
        } catch { /* fallo de SQLite — se informa abajo */ }
      }
      if (!guardado) {
        // `data.detail` solo existe en algunos errores. Sin esto, un 400 de
        // validación por campo caía al texto genérico y el encuestador no sabía
        // QUÉ dato estaba mal.
        const info = interpretarError(
          err, 'No se pudo agregar el integrante. Intente nuevamente.');
        Alert.alert('Error al agregar', info.mensaje);
        if (!info.sinRed) {
          reportarError({
            nivel: 'error',
            mensaje: `${pantalla}/agregarMiembro — ${info.diagnostico}`,
            pantalla,
            contexto: { hogar_id: String(hogarId ?? '') },
          });
        }
      }
    }

    if (guardado) {
      const rolLabel = ROLES_MIEMBRO.find(r => r.value === rolMiembro)?.label ?? rolMiembro;
      onAgregado({
        miembro_id: idEnServidor,
        nombre_display: nombreCompleto,
        tipo_documento: tipoDoc,
        numero_documento: numDoc,
        rol_display: rolLabel,
        fecha_nacimiento: fechaNac,
        constancia_nombre: requiereConstancia(rolMiembro) ? constanciaNombre : '',
        offline,
      });

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
  // PENDIENTE DE DEPENDENCIA: el selector de archivos real requiere
  // `expo-document-picker` (o `expo-image-picker`), que NO está instalado.
  // Hasta instalarlo, intentamos cargarlo dinámicamente; si no existe, se
  // registra una referencia-marcador para no bloquear el flujo en campo y se
  // informa al usuario. Al instalar la dep, este handler usará el picker real
  // sin más cambios en la UI.
  async function adjuntarConstancia() {
    try {
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

  return (
    <View>
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
            error={!!erroresForm.numDoc}
          />
        </View>
      </View>
      {erroresForm.numDoc
        ? <HelperText type="error">{erroresForm.numDoc}</HelperText>
        : null}

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
        {agregando ? 'Agregando…' : textoBoton}
      </Button>

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

  // ── Botón ─────────────────────────────────────────────────────────────────
  btnAgregar: {
    marginTop: SPACING.xs,
    borderColor: GOV.azul,
    borderRadius: RADIUS.sm,
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
