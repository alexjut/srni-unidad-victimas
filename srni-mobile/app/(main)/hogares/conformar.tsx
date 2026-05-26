/**
 * Pantalla: Conformar Hogar
 *
 * Flujo:
 *  1. Al montar: crea el hogar automáticamente en el servidor
 *     (el autorizado queda como primer MiembroHogar — backend lo hace)
 *  2. Muestra la ruta de entrevista y el listado de integrantes (comienza con el autorizado)
 *  3. Formulario para agregar integrantes uno a uno:
 *     Tipo Doc · Número · Primer Nombre · Segundo Nombre ·
 *     Primer Apellido · Segundo Apellido · Fecha Nacimiento · Parentesco · Género
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
import { useCaracterizacionStore } from '../../../src/stores/caracterizacionStore';
import { GovHeader } from '../../../src/components/GovHeader';
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

const PARENTESCOS = [
  { value: 'CONYUGE',       label: 'Cónyuge / Compañero/a' },
  { value: 'HIJO_A',        label: 'Hijo/a' },
  { value: 'YERNO_NUERA',   label: 'Yerno / Nuera' },
  { value: 'NIETO_A',       label: 'Nieto/a' },
  { value: 'PADRE_MADRE',   label: 'Padre / Madre' },
  { value: 'HERMANO_A',     label: 'Hermano/a' },
  { value: 'OTRO_PARIENTE', label: 'Otro pariente' },
  { value: 'NO_PARIENTE',   label: 'No pariente' },
];

const GENEROS = [
  { value: 'M',  label: 'Masculino' },
  { value: 'F',  label: 'Femenino' },
  { value: 'NB', label: 'No binario' },
  { value: 'ND', label: 'No declara' },
];

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

// ── Tipo local para un integrante ya agregado ─────────────────────────────────

interface IntegranteAgregado {
  key: string;
  es_autorizado: boolean;
  nombre_display: string;        // nombre completo para mostrar
  tipo_documento: string;        // código p.ej. "CC"
  numero_documento: string;
  parentesco_display: string;
  rol_display: string;
  genero: string;
  fecha_nacimiento: string;
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
          {item.parentesco_display ? `  ·  ${item.parentesco_display}` : ''}
          {item.rol_display ? `  ·  ${item.rol_display}` : ''}
          {item.fecha_nacimiento ? `  ·  Nac. ${item.fecha_nacimiento}` : ''}
        </Text>
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

  // Estado del hogar
  const [hogarId, setHogarIdLocal]    = useState<string | null>(null);
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
  const [parentesco,   setParentesco]   = useState('');
  const [genero,       setGenero]       = useState('');
  const [rolMiembro,   setRolMiembro]   = useState('MIEMBRO');
  const [erroresForm,  setErroresForm]  = useState<Record<string, string>>({});
  const [agregando,    setAgregando]    = useState(false);

  // Modales selectores
  const [modalTipoDoc,    setModalTipoDoc]    = useState(false);
  const [modalParentesco, setModalParentesco] = useState(false);
  const [modalGenero,     setModalGenero]     = useState(false);
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
      try {
        const { data } = await hogaresApi.crear({
          autorizado: victimaLocalId,
          numero_personas: 1,
        });
        setHogarIdLocal(data.id);
        setHogarId(data.id);

        // Autorizado como primer integrante (lo agrega el backend, lo mostramos acá)
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
          parentesco_display: '',
          genero: v?.genero ?? '',
          fecha_nacimiento: '',
        }]);
      } catch (err: any) {
        const detalle = err?.response?.data;
        if (typeof detalle === 'object') {
          setErrorHogar(JSON.stringify(detalle));
        } else {
          setErrorHogar('No se pudo crear el hogar. Verifique la conexión.');
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
    if (!parentesco)           e.parentesco   = 'Seleccione parentesco';
    if (!genero)               e.genero       = 'Seleccione género';
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

    try {
      await hogaresApi.agregarMiembro(hogarId, {
        nombre_completo: nombreCompleto,
        parentesco,
        genero,
        rol: rolMiembro as 'MIEMBRO' | 'TUTOR' | 'CUIDADOR_PERMANENTE',
        estado_inclusion: 'NO_INCLUIDO',
        fecha_nacimiento: fechaNac || undefined,
      });

      const parentescoLabel = PARENTESCOS.find(p => p.value === parentesco)?.label ?? parentesco;
      const rolLabel        = ROLES_MIEMBRO.find(r => r.value === rolMiembro)?.label ?? rolMiembro;
      setIntegrantes(prev => [
        ...prev,
        {
          key: `${Date.now()}`,
          es_autorizado: false,
          nombre_display: nombreCompleto,
          tipo_documento: tipoDoc,
          numero_documento: numDoc,
          parentesco_display: parentescoLabel,
          rol_display: rolLabel,
          genero,
          fecha_nacimiento: fechaNac,
        },
      ]);

      // Limpiar formulario para el siguiente
      setTipoDoc('CC'); setNumDoc(''); setPrimerNombre(''); setSegNombre('');
      setPrimerApell(''); setSegApell(''); setFechaNac('');
      setParentesco(''); setGenero(''); setRolMiembro('MIEMBRO'); setErroresForm({});
    } catch (err: any) {
      Alert.alert(
        'Error al agregar',
        err?.response?.data?.detail ?? 'No se pudo agregar el integrante. Intente nuevamente.',
      );
    } finally {
      setAgregando(false);
    }
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
      router.replace({
        pathname: '/(main)/hogares/[hogarId]/caracterizaciones',
        params: { hogarId },
      });
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
          <Text style={styles.cargandoTxt}>Registrando hogar…</Text>
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

          {/* Fecha de Nacimiento */}
          <TextInput
            label="Fecha Nacimiento (AAAA-MM-DD)"
            value={fechaNac}
            onChangeText={setFechaNac}
            mode="outlined"
            placeholder="1990-01-15"
            keyboardType="numeric"
            style={styles.input}
            activeOutlineColor={GOV.azul}
            error={!!erroresForm.fechaNac}
          />
          {erroresForm.fechaNac
            ? <HelperText type="error">{erroresForm.fechaNac}</HelperText>
            : null}

          {/* Fila: Parentesco + Género */}
          <View style={styles.fila}>
            <View style={{ flex: 1 }}>
              <CampoSelector
                label="Parentesco *"
                valor={PARENTESCOS.find(p => p.value === parentesco)?.label ?? ''}
                placeholder="Seleccionar"
                error={!!erroresForm.parentesco}
                onPress={() => setModalParentesco(true)}
              />
              {erroresForm.parentesco
                ? <HelperText type="error">{erroresForm.parentesco}</HelperText>
                : null}
            </View>
            <View style={{ flex: 1 }}>
              <CampoSelector
                label="Género *"
                valor={GENEROS.find(g => g.value === genero)?.label ?? ''}
                placeholder="Seleccionar"
                error={!!erroresForm.genero}
                onPress={() => setModalGenero(true)}
              />
              {erroresForm.genero
                ? <HelperText type="error">{erroresForm.genero}</HelperText>
                : null}
            </View>
          </View>

          {/* Rol en el hogar */}
          <CampoSelector
            label="Rol en el hogar"
            valor={ROLES_MIEMBRO.find(r => r.value === rolMiembro)?.label ?? rolMiembro}
            placeholder="Seleccionar rol"
            onPress={() => setModalRol(true)}
          />

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

          <GovButton
            label={`Continuar a caracterizaciones (${integrantes.length} integrante${integrantes.length !== 1 ? 's' : ''})`}
            icon="arrow-right-circle"
            onPress={continuarACaracterizaciones}
            loading={continuando}
            disabled={!hogarId || continuando}
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
        visible={modalParentesco}
        titulo="Parentesco con el autorizado"
        opciones={PARENTESCOS}
        valorActual={parentesco}
        onSeleccionar={setParentesco}
        onCerrar={() => setModalParentesco(false)}
      />
      <SelectorModal
        visible={modalGenero}
        titulo="Género"
        opciones={GENEROS}
        valorActual={genero}
        onSeleccionar={setGenero}
        onCerrar={() => setModalGenero(false)}
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
    ...FONT.subtitle,
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
