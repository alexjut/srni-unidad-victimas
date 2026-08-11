/**
 * Búsqueda en el RNI — Registro Único de Víctimas.
 *
 * Flujo:
 * 1. Encuestador ingresa tipo documento + número + ruta de entrevista → Consultar RNI
 * 2a. Encontrado y habilitado → Seleccionar instrumento → Conformar hogar
 * 2b. Encontrado pero no habilitado → Mostrar estado RUV
 * 2c. No está en el padrón → Ofrecer alta manual (condición en el RUV por verificar)
 *
 * La consulta va SIEMPRE al servidor. No se cachea PII localmente.
 */
import { useState, useCallback } from 'react';
import { View, ScrollView, StyleSheet, Pressable, Modal, ImageBackground } from 'react-native';
import {
  Text, TextInput, Button, SegmentedButtons,
  ActivityIndicator, HelperText, Chip, Divider, Surface, Menu,
} from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { router, useFocusEffect } from 'expo-router';

import * as DocumentPicker from 'expo-document-picker';

import { GovHeader } from '../../src/components/GovHeader';
import { SelectorFecha } from '../../src/components/SelectorFecha';

// Fondo: caficultor colombiano en la montaña. Imagen LOCAL (bundled) → carga
// offline, sin depender de red, coherente con la marca SICAV Móvil.
const IMAGEN_FONDO = require('../../assets/fondo-busqueda.jpg');
import { GOV, SPACING, RADIUS, SHADOW, FONT } from '../../src/theme/govTheme';
import { victimasApi } from '../../src/api/victimas';
import apiClient from '../../src/api/client';
import { useCaracterizacionStore } from '../../src/stores/caracterizacionStore';
import { useSyncStore } from '../../src/stores/syncStore';
import * as precargaDao from '../../src/db/precargaDao';
import type { PadronRow } from '../../src/db/precargaDao';
import * as victimasOfflineDao from '../../src/db/victimasOfflineDao';
import * as colaDao from '../../src/db/colaDao';
import { reportarError } from '../../src/services/errorReporter';
import * as filtroUniverso from '../../src/services/filtroUniverso';
import type { ResultadoBusquedaFuente, VictimaResumenFuente } from '../../src/types';

// ── Tipos de documento ───────────────────────────────────────────────────────

type TipoDoc = 'CC' | 'TI' | 'RC' | 'CE' | 'PA';

const TIPOS_DOC: Record<TipoDoc, { nombre: string; icono: string }> = {
  CC: { nombre: 'Cédula de Ciudadanía',   icono: 'card-account-details' },
  TI: { nombre: 'Tarjeta de Identidad',    icono: 'card-account-details-outline' },
  RC: { nombre: 'Registro Civil',          icono: 'file-document-outline' },
  CE: { nombre: 'Cédula de Extranjería',   icono: 'earth' },
  PA: { nombre: 'Pasaporte',               icono: 'passport' },
};

interface SelectTipoDocProps {
  valor: TipoDoc;
  onChange: (v: TipoDoc) => void;
}

function SelectTipoDoc({ valor, onChange }: SelectTipoDocProps) {
  const [visible, setVisible] = useState(false);
  const seleccionado = TIPOS_DOC[valor];

  return (
    <>
      {/* Trigger — se ve como un campo de formulario */}
      <Pressable
        onPress={() => setVisible(true)}
        style={({ pressed }) => [styles.selectTrigger, pressed && { opacity: 0.85 }]}
        accessibilityRole="combobox"
        accessibilityLabel={`Tipo de documento: ${seleccionado.nombre}`}
      >
        <View style={styles.selectIconoWrap}>
          <MaterialCommunityIcons
            name={seleccionado.icono as any}
            size={20}
            color={GOV.azul}
          />
        </View>
        <View style={styles.selectTextos}>
          <Text style={styles.selectLabel}>Tipo de documento</Text>
          <Text style={styles.selectValor} numberOfLines={1}>{seleccionado.nombre}</Text>
        </View>
        <MaterialCommunityIcons name="chevron-down" size={22} color={GOV.textoT} />
      </Pressable>

      {/* Modal de selección */}
      <Modal
        visible={visible}
        transparent
        animationType="slide"
        onRequestClose={() => setVisible(false)}
      >
        <Pressable style={styles.modalOverlay} onPress={() => setVisible(false)}>
          <View style={styles.modalCard}>
            <View style={styles.modalHandle} />
            <Text style={styles.excTitulo}>Tipo de documento</Text>

            {(Object.entries(TIPOS_DOC) as [TipoDoc, typeof TIPOS_DOC[TipoDoc]][]).map(([code, info]) => (
              <Pressable
                key={code}
                onPress={() => { onChange(code); setVisible(false); }}
                style={({ pressed }) => [
                  styles.modalOpcion,
                  valor === code && styles.modalOpcionActiva,
                  pressed && { opacity: 0.8 },
                ]}
              >
                <View style={[styles.modalOpcionIcono, valor === code && styles.modalOpcionIconoActivo]}>
                  <MaterialCommunityIcons
                    name={info.icono as any}
                    size={20}
                    color={valor === code ? '#FFF' : GOV.azul}
                  />
                </View>
                <View style={styles.modalOpcionTextos}>
                  <Text style={[styles.modalOpcionCodigo, valor === code && styles.modalOpcionCodigoActivo]}>
                    {code}
                  </Text>
                  <Text style={[styles.modalOpcionNombre, valor === code && styles.modalOpcionNombreActivo]}>
                    {info.nombre}
                  </Text>
                </View>
                {valor === code && (
                  <MaterialCommunityIcons name="check-circle" size={22} color={GOV.azul} />
                )}
              </Pressable>
            ))}
          </View>
        </Pressable>
      </Modal>
    </>
  );
}

// ── Rutas de entrevista ───────────────────────────────────────────────────────

const RUTAS = [
  { value: 'GENERAL',                   label: 'General' },
  { value: 'ACCIONES_CONSTITUCIONALES', label: 'Acc. Constitucionales' },
  { value: 'MODIFICACION_NUCLEO',       label: 'Mod. Núcleo Familiar' },
  { value: 'ESPECIAL',                  label: 'Ruta Especial' },
];

// ── Instrumentos ──────────────────────────────────────────────────────────────

interface InstrumentoResumen {
  id: string;
  codigo: string;
  nombre: string;
  version: string;
  activo: boolean;
  vigente: boolean;
  total_capitulos: number;
}

const ICONO_INSTRUMENTO: Record<string, string> = {
  TERRITORIAL:   'map-marker-multiple',
  BUENAVENTURA:  'city-variant',
  SAN_ANDRES:    'island',
  TELEFONICO:    'phone-in-talk',
  URBANO_ETNICO: 'home-city',
  RURAL_ETNICO:  'tree',
  ASISTENCIA:    'hand-heart',
};

function TarjetaInstrumentoItem({
  item,
  activo,
  onPress,
}: {
  item: InstrumentoResumen;
  activo: boolean;
  onPress: () => void;
}) {
  const icono = (ICONO_INSTRUMENTO[item.codigo] ?? 'clipboard-outline') as any;
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [
        styles.instrCard,
        activo && styles.instrCardActivo,
        pressed && { opacity: 0.88 },
      ]}
      accessibilityRole="radio"
      accessibilityState={{ selected: activo }}
      accessibilityLabel={item.nombre}
    >
      <View style={[styles.instrIcono, activo && styles.instrIconoActivo]}>
        <MaterialCommunityIcons name={icono} size={22} color={activo ? '#FFF' : GOV.azul} />
      </View>
      <View style={styles.instrTexto}>
        <Text style={[styles.instrNombre, activo && styles.instrNombreActivo]} numberOfLines={2}>
          {item.nombre}
        </Text>
        <Text style={styles.instrMeta}>{item.version}  ·  {item.total_capitulos} capítulos</Text>
      </View>
      <MaterialCommunityIcons
        name={activo ? 'check-circle' : 'chevron-right'}
        size={20}
        color={activo ? GOV.azul : GOV.borde}
      />
    </Pressable>
  );
}

interface SeccionInstrumentosProps {
  instrumentos: InstrumentoResumen[];
  cargando: boolean;
  seleccionado: InstrumentoResumen | null;
  onSelect: (i: InstrumentoResumen) => void;
}

function SeccionInstrumentos({ instrumentos, cargando, seleccionado, onSelect }: SeccionInstrumentosProps) {
  return (
    <View style={styles.seccionInstr}>
      <Text style={styles.seccionInstrTitulo}>Selecciona el tipo de caracterización</Text>
      {cargando ? (
        <ActivityIndicator animating color={GOV.azul} style={{ marginVertical: SPACING.md }} />
      ) : instrumentos.length === 0 ? (
        <Text style={styles.sinInstrTxt}>
          No hay instrumentos disponibles. Verifique la conexión con el servidor.
        </Text>
      ) : (
        instrumentos.map((item) => (
          <TarjetaInstrumentoItem
            key={item.id}
            item={item}
            activo={seleccionado?.id === item.id}
            onPress={() => onSelect(item)}
          />
        ))
      )}
    </View>
  );
}

// ── Helpers ───────────────────────────────────────────────────────────────────

type EstadoRuv = VictimaResumenFuente['estado_ruv'];

function colorEstadoRuv(estado: EstadoRuv): string {
  switch (estado) {
    case 'INCLUIDO':    return GOV.verde;
    case 'EXCLUIDO':    return GOV.rojo;
    case 'NO_INCLUIDO': return GOV.naranja;
    case 'NO_VERIFICADO': return GOV.azul;
    case 'EN_PROCESO':  return GOV.azul;
    default:            return GOV.textoS;
  }
}

function fondoEstadoRuv(estado: EstadoRuv): string {
  switch (estado) {
    case 'INCLUIDO':    return GOV.verdeTenue;
    case 'EXCLUIDO':    return GOV.rojoTenue;
    case 'NO_INCLUIDO': return GOV.naranjaTenue;
    case 'NO_VERIFICADO': return GOV.azulTenue;
    case 'EN_PROCESO':  return GOV.azulTenue;
    default:            return GOV.fondoApp;
  }
}

function nombreCompleto(v: VictimaResumenFuente): string {
  return [v.primer_nombre, v.segundo_nombre, v.primer_apellido, v.segundo_apellido]
    .filter(Boolean).join(' ').trim();
}

// ── Rutas que OMITEN la regla de vigencia (Manual UARIV §5.1.1, pág. 22) ─────
//
// La ruta GENERAL no está acá a propósito: es la única que RESPETA los dos años,
// y es el caso por defecto. Si estuviera en esta lista, la regla de vigencia
// sería opcional en la práctica.
const RUTAS_EXCEPCION = [
  { valor: 'ACCIONES_CONSTITUCIONALES', etiqueta: 'Acción constitucional',
    ayuda: 'Fallo, tutela o auto de seguimiento' },
  { valor: 'MODIFICACION_NUCLEO', etiqueta: 'Modificación del núcleo familiar',
    ayuda: 'Diferencias en la conformación del hogar' },
  { valor: 'ESPECIAL', etiqueta: 'Ruta especial',
    ayuda: 'Protección especial o urgencia manifiesta' },
];

// ── Tarjeta: no habilitado ────────────────────────────────────────────────────

function TarjetaNoHabilitado({ resultado, onUsarExcepcion }: {
  resultado: ResultadoBusquedaFuente;
  onUsarExcepcion?: () => void;
}) {
  const v = resultado.victima!;
  // Ficha vigente NO es un callejón: el manual autoriza tres rutas a omitir la
  // regla de los dos años. Antes acá terminaba el camino y el caso se escalaba
  // a soporte, que es lo contrario de para lo que existen esas rutas.
  const puedeExcepcion = resultado.motivo === 'FICHA_VIGENTE' && !!onUsarExcepcion;
  return (
    <Surface style={[styles.tarjeta, styles.tarjetaNaranja]}>
      <View style={styles.tarjetaEncabezado}>
        <MaterialCommunityIcons name="account-cancel" size={32} color={GOV.naranja} style={styles.icono} />
        <Text style={[styles.tarjetaTitulo, { color: GOV.naranja }]}>
          No habilitado para caracterización
        </Text>
      </View>
      <Text style={styles.tarjetaMensaje}>{resultado.mensaje}</Text>
      <View style={styles.chipsFila}>
        <Chip
          style={[styles.chip, { backgroundColor: fondoEstadoRuv(v.estado_ruv) }]}
          textStyle={{ ...FONT.label, color: colorEstadoRuv(v.estado_ruv) }}
        >
          {v.estado_ruv.replace('_', ' ')}
        </Chip>
      </View>
      {puedeExcepcion && (
        <>
          <Divider style={{ marginVertical: SPACING.md }} />
          <Text style={styles.tarjetaMensaje}>
            Si cuenta con un fallo, tutela o auto de seguimiento, puede
            caracterizarla por una ruta de excepción adjuntando el soporte.
          </Text>
          <Button
            mode="contained"
            icon="file-document-edit"
            onPress={onUsarExcepcion}
            style={{ marginTop: SPACING.sm }}
            buttonColor={GOV.azul}
          >
            Caracterizar por ruta de excepción
          </Button>
        </>
      )}
      <Text style={styles.tarjetaFuente}>Fuente: {resultado.fuente}</Text>
    </Surface>
  );
}

// ── Tarjeta: habilitado (solo info — el CTA está en el nivel de pantalla) ─────

function TarjetaHabilitado({ resultado }: { resultado: ResultadoBusquedaFuente }) {
  const v = resultado.victima!;
  const etnia = v.pertenencia_etnica?.toUpperCase();
  const mostrarEtnia = etnia && etnia !== 'NINGUNA' && etnia !== '' && etnia !== 'ND';

  return (
    <Surface style={[styles.tarjeta, styles.tarjetaVerde]}>
      <View style={styles.tarjetaEncabezado}>
        <MaterialCommunityIcons name="account-check" size={32} color={GOV.verde} style={styles.icono} />
        <Text style={[styles.tarjetaTitulo, { color: GOV.verde }]}>
          Persona habilitada para caracterización
        </Text>
      </View>

      <Text style={styles.nombreCompleto}>{nombreCompleto(v)}</Text>

      <View style={styles.chipsFila}>
        <Chip
          style={[styles.chip, { backgroundColor: fondoEstadoRuv(v.estado_ruv) }]}
          textStyle={{ ...FONT.label, color: colorEstadoRuv(v.estado_ruv) }}
        >
          {v.estado_ruv.replace('_', ' ')}
        </Chip>
        {v.discapacidad && (
          <Chip
            style={[styles.chip, { backgroundColor: GOV.rojoTenue }]}
            textStyle={{ ...FONT.label, color: GOV.rojo }}
            icon="wheelchair-accessibility"
          >
            Discapacidad
          </Chip>
        )}
        {mostrarEtnia && (
          <Chip
            style={[styles.chip, { backgroundColor: GOV.azulTenue }]}
            textStyle={{ ...FONT.label, color: GOV.azul }}
          >
            {v.pertenencia_etnica}
          </Chip>
        )}
      </View>

      <Text style={styles.datoSecundario}>
        {v.municipio_residencia_nombre ?? 'Municipio no registrado'}
      </Text>
      <Text style={styles.datoSecundario}>
        {v.hechos_victimizantes.length} hecho(s) victimizante(s) registrado(s)
      </Text>
    </Surface>
  );
}

// ── Tarjeta: no está en el padrón + formulario de alta manual ───────────────────

interface TarjetaNoEncontradoProps {
  resultado: ResultadoBusquedaFuente;
  tipoDoc: string;
  documento: string;
  cargandoRegistro: boolean;
  onRegistrarAltaManual: (datos: DatosAltaManual) => void;
}

interface DatosAltaManual {
  primerNombre: string;
  segundoNombre: string;
  primerApellido: string;
  segundoApellido: string;
  fechaNacimiento: string;
  genero: 'M' | 'F' | 'NB' | 'ND';
}

function TarjetaNoEncontrado({
  resultado, tipoDoc, documento, cargandoRegistro, onRegistrarAltaManual,
}: TarjetaNoEncontradoProps) {
  const [mostrarForm, setMostrarForm] = useState(false);
  const [primerNombre, setPrimerNombre] = useState('');
  const [segundoNombre, setSegundoNombre] = useState('');
  const [primerApellido, setPrimerApellido] = useState('');
  const [segundoApellido, setSegundoApellido] = useState('');
  const [fechaNacimiento, setFechaNacimiento] = useState('');
  const [genero, setGenero] = useState<'M' | 'F' | 'NB' | 'ND'>('ND');

  /** La encontró el filtro del universo, sin conexión y sin ficha en el padrón. */
  const enUniverso = resultado.fuente === 'UNIVERSO_RUV_OFFLINE';

  function puedeAgregar() {
    return primerNombre.trim() && primerApellido.trim() && fechaNacimiento.match(/^\d{4}-\d{2}-\d{2}$/);
  }

  return (
    <Surface style={[styles.tarjeta, styles.tarjetaGris]}>
      <View style={styles.tarjetaEncabezado}>
        <MaterialCommunityIcons
          name={resultado.no_identificante ? 'alert-circle-outline' : 'account-search-outline'}
          size={32}
          color={resultado.no_identificante ? GOV.naranja : GOV.textoS}
          style={styles.icono}
        />
        {/*
          Dos situaciones distintas, y el título tiene que distinguirlas. "No está
          en el padrón" invita a dar de alta a la persona; pero si el número es un
          valor de relleno, quizá SÍ está y solo hace falta el documento correcto.
          Decir lo mismo en los dos casos manda a crear un duplicado.
        */}
        {/*
          Tercer caso, añadido con el filtro del universo: la persona SÍ está en
          el RUV y solo le falta la ficha. Decirle "No está en el padrón" —que es
          cierto y suena a "no es víctima"— es exactamente la confusión que el
          filtro vino a quitar. Aquí el encuestador debe entender que procede.
        */}
        <Text style={styles.tarjetaTitulo}>
          {resultado.no_identificante
            ? 'Este número no identifica a una persona'
            : enUniverso
              ? 'Está en el RUV, sin caracterizar'
              : 'No está en el padrón'}
        </Text>
      </View>
      <Text style={styles.tarjetaMensaje}>{resultado.mensaje}</Text>
      {resultado.no_identificante && (
        <Text style={[styles.tarjetaMensaje, { fontWeight: '700' }]}>
          Verifique el documento con la persona antes de darla de alta.
        </Text>
      )}
      {enUniverso && (
        // El precio del filtro, dicho donde se toma la decisión y no en un
        // manual: ~1 de cada 1.000 aciertos es falso. No invalida el alta —el
        // backend revalida al sincronizar— pero el encuestador tiene que saber
        // que esto es una coincidencia probable, no una identificación.
        <Text style={[styles.tarjetaMensaje, { fontWeight: '700' }]}>
          Coincidencia encontrada sin conexión. Se confirma al sincronizar.
        </Text>
      )}
      <Text style={styles.tarjetaFuente}>Fuente: {resultado.fuente}</Text>

      <Divider style={styles.divider} />

      {!mostrarForm ? (
        <Button
          mode="outlined"
          icon="account-plus-outline"
          onPress={() => setMostrarForm(true)}
          style={styles.botonAccion}
          textColor={GOV.naranja}
        >
          Registrar y caracterizar
        </Button>
      ) : (
        <View>
          <Text style={styles.formTitulo}>Alta manual</Text>
          <Text style={styles.formSubtitulo}>
            {tipoDoc}  ·  {documento}
          </Text>

          <TextInput
            mode="outlined" label="Primer nombre *"
            value={primerNombre} onChangeText={(t) => setPrimerNombre(t.toUpperCase())}
            autoCapitalize="characters" style={styles.formInput}
            outlineColor={GOV.borde} activeOutlineColor={GOV.azul}
          />
          <TextInput
            mode="outlined" label="Segundo nombre"
            value={segundoNombre} onChangeText={(t) => setSegundoNombre(t.toUpperCase())}
            autoCapitalize="characters" style={styles.formInput}
            outlineColor={GOV.borde} activeOutlineColor={GOV.azul}
          />
          <TextInput
            mode="outlined" label="Primer apellido *"
            value={primerApellido} onChangeText={(t) => setPrimerApellido(t.toUpperCase())}
            autoCapitalize="characters" style={styles.formInput}
            outlineColor={GOV.borde} activeOutlineColor={GOV.azul}
          />
          <TextInput
            mode="outlined" label="Segundo apellido"
            value={segundoApellido} onChangeText={(t) => setSegundoApellido(t.toUpperCase())}
            autoCapitalize="characters" style={styles.formInput}
            outlineColor={GOV.borde} activeOutlineColor={GOV.azul}
          />
          {/* Sprint 21: calendario nativo en lugar de input AAAA-MM-DD */}
          <View style={styles.formInput}>
            <SelectorFecha
              valor={fechaNacimiento}
              onChange={setFechaNacimiento}
              label="Fecha de nacimiento *"
              permitirFuturo={false}
            />
          </View>

          <Text style={styles.formLabel}>Género</Text>
          <SegmentedButtons
            value={genero}
            onValueChange={(v) => setGenero(v as typeof genero)}
            buttons={[
              { value: 'M',  label: 'Masc.' },
              { value: 'F',  label: 'Fem.' },
              { value: 'NB', label: 'NB' },
              { value: 'ND', label: 'N/D' },
            ]}
            style={styles.segmentedGenero}
          />

          <View style={styles.formBotones}>
            <Button
              mode="outlined"
              onPress={() => setMostrarForm(false)}
              style={{ flex: 1, marginRight: SPACING.xs }}
              textColor={GOV.textoS}
            >
              Cancelar
            </Button>
            <Button
              mode="contained"
              icon="account-plus"
              onPress={() => onRegistrarAltaManual({ primerNombre, segundoNombre, primerApellido, segundoApellido, fechaNacimiento, genero })}
              disabled={!puedeAgregar() || cargandoRegistro}
              loading={cargandoRegistro}
              buttonColor={GOV.naranja}
              textColor="#FFF"
              style={{ flex: 2 }}
            >
              Agregar víctima
            </Button>
          </View>
        </View>
      )}
    </Surface>
  );
}

// ── Búsqueda OFFLINE: arma un ResultadoBusquedaFuente desde el padrón local ───
// Cuando no hay red (o el server falla) buscamos en el padrón precargado. Si la
// persona viene en la jornada del día usamos el VictimaResumenFuente COMPLETO;
// si solo está en el padrón liviano, construimos un resumen mínimo suficiente
// para mostrar estado (nombre, ubicación, hechos, RUV/habilitada/caracterizada).
function resultadoDesdePadron(
  p: PadronRow,
  jornada: VictimaResumenFuente | null,
): ResultadoBusquedaFuente {
  if (jornada) {
    return {
      encontrado: true,
      victima: jornada,
      fuente: 'OFFLINE (jornada)',
      mensaje: p.ya_caracterizada
        ? 'Persona ya caracterizada (datos offline).'
        : 'Persona encontrada en datos offline.',
    };
  }

  const partes = (p.nombre ?? '').trim().split(/\s+/);
  const victima: VictimaResumenFuente = {
    cons_persona: p.cons_persona,
    tipo_documento: p.tipo_documento,
    numero_documento: `••••${p.documento_display}`,
    primer_nombre: partes[0] ?? p.nombre ?? '',
    segundo_nombre: '',
    primer_apellido: partes.slice(1).join(' '),
    segundo_apellido: '',
    fecha_nacimiento: '',
    genero: 'ND',
    estado_ruv: p.en_ruv ? 'INCLUIDO' : 'NO_VERIFICADO',
    habilitado_para_caracterizacion: p.habilitada && !p.ya_caracterizada,
    fecha_ult_caracterizacion: null,
    pertenencia_etnica: 'NINGUNA',
    pueblo_indigena: '',
    discapacidad: false,
    tipo_discapacidad: '',
    hechos_victimizantes: Array.from({ length: Math.max(0, p.cantidad_hechos) }, () => ({
      codigo: '',
      nombre: 'Hecho registrado',
      fecha_hecho: null,
      municipio_hecho: p.ubicacion || null,
    })),
    municipio_residencia_codigo: null,
    municipio_residencia_nombre: p.ubicacion || null,
    fuente_origen: 'OFFLINE',
  };

  return {
    encontrado: true,
    victima,
    fuente: 'OFFLINE (padrón)',
    mensaje: p.ya_caracterizada
      ? 'Persona YA CARACTERIZADA (datos offline).'
      : 'Persona encontrada en el padrón offline.',
  };
}

// ── Pantalla principal ────────────────────────────────────────────────────────

export default function BusquedaScreen() {
  const [tipoDoc, setTipoDoc] = useState<TipoDoc>('CC');
  const [documento, setDocumento] = useState('');
  const [menuRutaVisible, setMenuRutaVisible] = useState(false);
  const [cargando, setCargando] = useState(false);
  const [cargandoRegistro, setCargandoRegistro] = useState(false);
  const [resultado, setResultado] = useState<ResultadoBusquedaFuente | null>(null);
  // Ruta de excepción: se elige acá pero el soporte se envía mucho después,
  // cuando ya existe la sesión a la que colgarlo (por eso va al store).
  const [modalExcepcion, setModalExcepcion] = useState(false);
  const [rutaElegida, setRutaElegida] = useState('');
  const [soporteNombre, setSoporteNombre] = useState('');
  const [soporteUri, setSoporteUri] = useState('');
  const [errorExcepcion, setErrorExcepcion] = useState('');
  const [verificandoExcepcion, setVerificandoExcepcion] = useState(false);
  const [errorBusqueda, setErrorBusqueda] = useState<string | null>(null);
  // Personas distintas que comparten el documento buscado. Mientras esta lista
  // tenga algo, NO hay resultado: falta que el encuestador confirme cuál es.
  const [candidatos, setCandidatos] = useState<PadronRow[]>([]);
  // Lo mismo, pero cuando la ambigüedad la reporta el servidor: `consultarFuente`
  // devuelve 200 con `candidatos`, y antes ese dato se descartaba — la pregunta
  // aparecía sin red y desaparecía con red, que es la peor combinación posible.
  const [candidatosOnline, setCandidatosOnline] = useState<VictimaResumenFuente[]>([]);

  const [instrumentos, setInstrumentos] = useState<InstrumentoResumen[]>([]);
  const [cargandoInstrumentos, setCargandoInstrumentos] = useState(false);
  const [instrumentoSeleccionado, setInstrumentoSeleccionado] = useState<InstrumentoResumen | null>(null);

  const { rutaEntrevista, setRutaEntrevista, victimaFuente } = useCaracterizacionStore();
  const rutaLabel = RUTAS.find((r) => r.value === rutaEntrevista)?.label ?? 'General';
  const estaOnline = useSyncStore((s) => s.estaOnline);
  const refrescarContadores = useSyncStore((s) => s.refrescarContadores);

  const [altaManualRegistrada, setAltaManualRegistrada] = useState(false);

  // ── Sprint 16: limpiar el estado al volver a la pantalla si ya hubo un
  // flujo completado previamente. Detecta el "regreso desde el hub" leyendo
  // victimaLocalId del store — si está poblado significa que ya conformamos
  // un hogar y la sigueinte vez que entremos a la búsqueda, debe quedar limpia.
  useFocusEffect(
    useCallback(() => {
      const { victimaLocalId, hogarId, limpiar } = useCaracterizacionStore.getState();
      if (victimaLocalId || hogarId) {
        // Reset completo del formulario y del store del flujo anterior
        setDocumento('');
        setResultado(null);
        setErrorBusqueda(null);
        setCandidatos([]);
        setCandidatosOnline([]);
        setInstrumentoSeleccionado(null);
        setAltaManualRegistrada(false);
        limpiar();
      }
    }, []),
  );

  async function cargarInstrumentos() {
    if (instrumentos.length > 0) return; // Ya cargados
    setCargandoInstrumentos(true);
    try {
      const { data } = await apiClient.get<{ results: InstrumentoResumen[] }>('/api/formulario/instrumentos/');
      setInstrumentos(data.results.filter((i) => i.activo && i.vigente));
    } catch {
      setInstrumentos([]);
    } finally {
      setCargandoInstrumentos(false);
    }
  }

  /**
   * Fase 0 offline: busca en el padrón local. Devuelve true si encontró y ya
   * pintó el resultado; false si no hay nada local (para mostrar el error de red).
   */
  /**
   * Parámetros del filtro del universo, si hay uno descargado y usable.
   *
   * Devuelve `null` cuando no lo hay, y en ese caso la búsqueda offline se
   * comporta exactamente como antes. Es deliberado: el filtro es un accesorio
   * que amplía lo que la APK reconoce, no un requisito para funcionar.
   */
  async function obtenerParametrosFiltro() {
    try {
      return filtroUniverso.parsearParametros(
        await precargaDao.getParametrosBloom(),
      );
    } catch {
      return null;
    }
  }

  async function buscarOffline(): Promise<boolean> {
    try {
      const doc = documento.trim();
      const r = await precargaDao.buscarCandidatosEnPadron(doc);

      // Documento de relleno ('99', '0'): no identifica a nadie. No es "no está"
      // —la persona puede existir— y sobre todo no se puede mostrar a uno de los
      // miles que comparten ese número como si fuera quien está enfrente.
      if (r.noIdentificante) {
        setCandidatos([]);
        setCandidatosOnline([]);
        setErrorBusqueda(
          'Este número no identifica a una persona: en el padrón figura como valor ' +
            'de relleno, compartido por muchos registros. Verifique el documento o ' +
            'regístrela por alta manual.',
        );
        return true;
      }

      // El padrón local no la tiene. Antes esto era el final del camino: se
      // respondía "no está en los datos offline" y la pantalla no ofrecía nada
      // más. Pero el padrón solo trae a quien YA fue entrevistado — 8,12 M de
      // víctimas reconocidas nunca lo fueron, y decirle a una de ellas que no
      // existe, teniéndola enfrente, es el error que este bloque corrige.
      if (r.candidatos.length === 0) {
        const params = await obtenerParametrosFiltro();
        if (params && filtroUniverso.estaEnUniverso(doc, params)) {
          setResultado({
            encontrado: false,
            victima: null,
            // `motivo` es lo que la tarjeta usa para decidir qué ofrecer:
            // NO_EN_PADRON ya habilita el alta manual, y este caso es ese mismo
            // camino con una certeza distinta que la pantalla debe transmitir.
            motivo: 'NO_EN_PADRON',
            fuente: 'UNIVERSO_RUV_OFFLINE',
            mensaje:
              'No tiene ficha, pero figura en el universo del RUV. Puede ' +
              'registrarla por alta manual. La coincidencia se confirma al ' +
              'sincronizar.',
          } as ResultadoBusquedaFuente);
          return true;
        }
        return false;
      }

      // Varias personas con el mismo documento: decide quien la tiene enfrente.
      // Elegir por ella sería entregarle los datos de otra sin que se entere, y
      // sin señal no tiene con qué verificarlo.
      if (r.requiereConfirmacion) {
        setCandidatos(r.candidatos);
        return true;
      }

      const jornada = await precargaDao.buscarEnJornada(doc);
      setResultado(resultadoDesdePadron(r.candidatos[0], jornada));
      return true;
    } catch {
      return false;
    }
  }

  /** El encuestador eligió cuál de los candidatos es la persona que atiende. */
  async function elegirCandidato(p: PadronRow) {
    setCandidatos([]);
    // Con `cons_persona`: la jornada tiene una fila por persona, y sin este dato
    // devolvería cualquiera de las que comparten el documento — pisando justo la
    // elección que el encuestador acaba de hacer.
    const jornada = await precargaDao.buscarEnJornada(documento.trim(), p.cons_persona);
    setResultado(resultadoDesdePadron(p, jornada));
  }

  /** El encuestador eligió entre los candidatos que devolvió el servidor. */
  function elegirCandidatoOnline(v: VictimaResumenFuente) {
    setCandidatosOnline([]);
    setResultado({
      encontrado: true,
      victima: v,
      fuente: 'RNI',
      mensaje: '',
    });
  }

  async function buscar() {
    if (!documento.trim()) return;
    setCargando(true);
    setResultado(null);
    setErrorBusqueda(null);
    setCandidatos([]);
    setCandidatosOnline([]);
    setInstrumentoSeleccionado(null);
    setAltaManualRegistrada(false);

    // Si no hay red, ni intentamos el server: vamos directo al padrón offline.
    if (!estaOnline) {
      const ok = await buscarOffline();
      if (!ok) {
        setErrorBusqueda(
          'Sin conexión y la persona no está en los datos offline. Conéctese e intente de nuevo.',
        );
      }
      setCargando(false);
      return;
    }

    try {
      const { data } = await victimasApi.consultarFuente(tipoDoc, documento.trim());
      // Si el servidor devolvió más de una persona para el documento, no hay un
      // resultado que mostrar: hay una pregunta que hacer.
      if (data?.encontrado && (data.candidatos?.length ?? 0) > 0 && data.victima) {
        setCandidatosOnline([data.victima, ...(data.candidatos ?? [])]);
      } else {
        setResultado(data);
      }
      // Sprint 17: ya NO se cargan instrumentos aquí. El selector vive en el hub
      // de caracterizaciones tras conformar el hogar (flujo cosido Sprint 14).
    } catch {
      // El server falló aunque creíamos estar online → fallback al padrón local.
      const ok = await buscarOffline();
      if (!ok) {
        setErrorBusqueda('Error al consultar el RNI. Verifique la conexión.');
      }
    } finally {
      setCargando(false);
    }
  }

  // true si el error es de RED (el servidor no respondió: timeout / sin conexión).
  // axios deja err.response indefinido en errores de red. Sirve para caer a offline
  // aunque la bandera `estaOnline` esté desactualizada (modo avión reciente).
  function esErrorDeRed(err: any): boolean {
    return !err?.response;
  }

  async function conformarHogar() {
    const v = resultado?.victima;
    if (!v) return;
    setCargandoRegistro(true);
    try {
      if (estaOnline) {
        try {
          const { data } = await victimasApi.registrarDesdeFuente(v);
          useCaracterizacionStore.getState().setVictimaFuente(v);
          useCaracterizacionStore.getState().setVictimaLocalId(data.victima_id);
        } catch (err) {
          if (!esErrorDeRed(err)) throw err; // error real del servidor → propagar
          // La bandera estaba desactualizada: el servidor no respondió → offline.
          await registrarVictimaOffline(v);
        }
      } else {
        // Sin red: registrar la víctima OFFLINE. El id_local actúa como
        // `autorizado` del hogar; REGISTRAR_VICTIMA la creará en el servidor al
        // recuperar señal y remapeará el UUID en el CREAR_HOGAR pendiente.
        await registrarVictimaOffline(v);
      }
      router.push('/(main)/hogares/conformar');
    } catch (err: any) {
      // No mostramos el mensaje técnico de axios al encuestador; lo enviamos a reportarError.
      reportarError({
        nivel: 'warn',
        mensaje: 'conformarHogar — registrarDesdeFuente falló: ' + (err?.message ?? String(err)),
        stack: err?.stack,
        pantalla: 'busqueda',
      });
      setErrorBusqueda('No se pudo registrar. Revisa la conexión e intenta de nuevo.');
    } finally {
      setCargandoRegistro(false);
    }
  }

  /** Abre el selector de archivo para adjuntar el soporte de la excepción. */
  async function adjuntarSoporte() {
    try {
      const res = await DocumentPicker.getDocumentAsync({ copyToCacheDirectory: true });
      if (res.canceled || !res.assets?.length) return;
      setSoporteNombre(res.assets[0].name);
      setSoporteUri(res.assets[0].uri);
      setErrorExcepcion('');
    } catch (err: any) {
      reportarError({
        nivel: 'warn',
        mensaje: 'adjuntarSoporte falló: ' + (err?.message ?? String(err)),
        pantalla: 'busqueda',
      });
      setErrorExcepcion('No se pudo adjuntar el archivo. Intente de nuevo.');
    }
  }

  /**
   * Vuelve a preguntar al servidor, ahora diciendo POR QUÉ RUTA.
   *
   * No se habilita a la persona desde el cliente: se consulta de nuevo y manda
   * lo que responda el servidor. Decidirlo acá dejaría la regla de vigencia en
   * manos de la app, que es exactamente lo que hay que evitar.
   */
  async function confirmarExcepcion() {
    if (!rutaElegida) {
      setErrorExcepcion('Seleccione la ruta que corresponde al caso.');
      return;
    }
    if (!soporteUri) {
      // El soporte no es opcional: es lo que deja rastro de haberse saltado un
      // control. Sin él, la regla de vigencia sería opcional en la práctica.
      setErrorExcepcion('Adjunte el soporte (fallo, tutela o auto).');
      return;
    }
    setVerificandoExcepcion(true);
    try {
      const { data } = await victimasApi.consultarFuente(
        tipoDoc, documento.trim(), rutaElegida);
      if (!data.victima?.habilitado_para_caracterizacion) {
        setErrorExcepcion(data.mensaje ||
          'Esa ruta no habilita este caso. Verifique con su supervisor.');
        return;
      }
      const store = useCaracterizacionStore.getState();
      store.setRutaEntrevista(rutaElegida);
      store.setSoporteExcepcion({
        ruta: rutaElegida, uri: soporteUri, nombre: soporteNombre,
      });
      setResultado(data);
      setModalExcepcion(false);
    } catch (err: any) {
      reportarError({
        nivel: 'warn',
        mensaje: 'confirmarExcepcion falló: ' + (err?.message ?? String(err)),
        pantalla: 'busqueda',
      });
      setErrorExcepcion('No se pudo verificar con el servidor. Revise la conexión.');
    } finally {
      setVerificandoExcepcion(false);
    }
  }

  /** Crea la víctima offline + encola REGISTRAR_VICTIMA y deja el store listo. */
  async function registrarVictimaOffline(v: VictimaResumenFuente) {
    const victimaLocal = await victimasOfflineDao.crearVictimaOffline(v);
    await colaDao.encolar('REGISTRAR_VICTIMA', victimaLocal.id_local, {
      id_local: victimaLocal.id_local,
      victima: v,
    });
    useCaracterizacionStore.getState().setVictimaFuente(v);
    useCaracterizacionStore.getState().setVictimaLocalId(victimaLocal.id_local);
    await refrescarContadores();
  }

  // Víctima ya registrada por alta manual — directo a conformar hogar
  function conformarHogarAltaManual() {
    router.push('/(main)/hogares/conformar');
  }

  async function registrarAltaManual(datos: DatosAltaManual) {
    setCargandoRegistro(true);
    try {
      const payload: VictimaResumenFuente = {
        cons_persona: null,
        tipo_documento: tipoDoc,
        numero_documento: documento.trim(),
        primer_nombre: datos.primerNombre,
        segundo_nombre: datos.segundoNombre,
        primer_apellido: datos.primerApellido,
        segundo_apellido: datos.segundoApellido,
        fecha_nacimiento: datos.fechaNacimiento,
        genero: datos.genero,
        // No es 'NO_INCLUIDO': lo único verificado es que no está en el padrón.
        estado_ruv: 'NO_VERIFICADO',
        habilitado_para_caracterizacion: true,
        fecha_ult_caracterizacion: null,
        pertenencia_etnica: 'NINGUNA',
        pueblo_indigena: '',
        discapacidad: false,
        tipo_discapacidad: '',
        hechos_victimizantes: [],
        municipio_residencia_codigo: null,
        municipio_residencia_nombre: null,
        fuente_origen: 'MANUAL',
      };
      if (estaOnline) {
        try {
          const { data } = await victimasApi.registrarDesdeFuente(payload);
          useCaracterizacionStore.getState().setVictimaFuente(payload);
          useCaracterizacionStore.getState().setVictimaLocalId(data.victima_id);
        } catch (err) {
          if (!esErrorDeRed(err)) throw err;
          await registrarVictimaOffline(payload);
        }
      } else {
        // Sin red: registrar el alta manual OFFLINE (id_local + cola).
        await registrarVictimaOffline(payload);
      }
      setAltaManualRegistrada(true);
    } catch (err: any) {
      // No mostramos el mensaje técnico de axios al encuestador; lo enviamos a reportarError.
      reportarError({
        nivel: 'warn',
        mensaje: 'registrarAltaManual — registrarDesdeFuente falló: ' + (err?.message ?? String(err)),
        stack: err?.stack,
        pantalla: 'busqueda',
      });
      setErrorBusqueda('No se pudo registrar. Revisa la conexión e intenta de nuevo.');
    } finally {
      setCargandoRegistro(false);
    }
  }

  /**
   * Varias personas comparten el documento buscado. La pantalla NO elige: pone
   * las opciones y espera. Sin señal no hay a quién preguntarle, así que la
   * confirmación la hace el encuestador contra la persona que tiene enfrente.
   */
  function renderCandidatos() {
    if (candidatos.length === 0) return null;

    return (
      <Surface style={[styles.tarjeta, styles.tarjetaNaranja]}>
        <View style={styles.tarjetaEncabezado}>
          <MaterialCommunityIcons
            name="account-question-outline"
            size={32}
            color={GOV.naranja}
            style={styles.icono}
          />
          <Text style={[styles.tarjetaTitulo, { color: GOV.naranja }]}>
            {candidatos.length} personas con este documento
          </Text>
        </View>
        <Text style={styles.tarjetaMensaje}>
          El número {tipoDoc} {documento} está registrado a nombre de más de una
          persona. Confirme el nombre con quien tiene enfrente antes de continuar.
        </Text>

        <Divider style={{ marginVertical: SPACING.sm }} />

        {candidatos.map((c, i) => (
          <Pressable
            key={`${c.documento_hash}-${c.cons_persona ?? i}`}
            onPress={() => elegirCandidato(c)}
            style={({ pressed }) => [styles.candidato, pressed && { opacity: 0.85 }]}
            accessibilityRole="button"
            accessibilityLabel={`Seleccionar a ${c.nombre}`}
          >
            <View style={styles.candidatoTextos}>
              <Text style={styles.candidatoNombre} numberOfLines={2}>
                {c.nombre || 'Sin nombre registrado'}
              </Text>
              <Text style={styles.candidatoMeta}>
                {c.ubicacion || 'Sin ubicación'}
                {c.ya_caracterizada ? '  ·  Ya caracterizada' : ''}
                {c.en_ruv ? '  ·  Incluida en RUV' : ''}
              </Text>
            </View>
            <MaterialCommunityIcons name="chevron-right" size={24} color={GOV.azul} />
          </Pressable>
        ))}
      </Surface>
    );
  }

  /**
   * Misma pregunta que `renderCandidatos`, pero con los datos del servidor, que
   * SÍ traen nombre completo y fecha de nacimiento — o sea que acá el
   * encuestador puede confirmar sin abrir nada más.
   */
  function renderCandidatosOnline() {
    return (
      <Surface style={[styles.tarjeta, styles.tarjetaNaranja]}>
        <View style={styles.tarjetaEncabezado}>
          <MaterialCommunityIcons
            name="account-question-outline"
            size={32}
            color={GOV.naranja}
            style={styles.icono}
          />
          <Text style={[styles.tarjetaTitulo, { color: GOV.naranja }]}>
            {candidatosOnline.length} personas con este documento
          </Text>
        </View>
        <Text style={styles.tarjetaMensaje}>
          El número {tipoDoc} {documento} está registrado a nombre de más de una
          persona. Confirme el nombre y la fecha de nacimiento con quien tiene
          enfrente antes de continuar.
        </Text>

        <Divider style={{ marginVertical: SPACING.sm }} />

        {candidatosOnline.map((v, i) => {
          const nombre = [v.primer_nombre, v.segundo_nombre, v.primer_apellido, v.segundo_apellido]
            .filter(Boolean).join(' ');
          return (
            <Pressable
              key={`${v.cons_persona ?? i}`}
              onPress={() => elegirCandidatoOnline(v)}
              style={({ pressed }) => [styles.candidato, pressed && { opacity: 0.85 }]}
              accessibilityRole="button"
              accessibilityLabel={`Seleccionar a ${nombre}`}
            >
              <View style={styles.candidatoTextos}>
                <Text style={styles.candidatoNombre} numberOfLines={2}>
                  {nombre || 'Sin nombre registrado'}
                </Text>
                <Text style={styles.candidatoMeta}>
                  {v.fecha_nacimiento ? `Nac. ${v.fecha_nacimiento}` : 'Sin fecha de nacimiento'}
                  {v.municipio_residencia_nombre ? `  ·  ${v.municipio_residencia_nombre}` : ''}
                </Text>
              </View>
              <MaterialCommunityIcons name="chevron-right" size={24} color={GOV.azul} />
            </Pressable>
          );
        })}
      </Surface>
    );
  }

  function renderTarjeta() {
    if (candidatos.length > 0) return renderCandidatos();
    if (candidatosOnline.length > 0) return renderCandidatosOnline();
    if (!resultado) return null;

    if (!resultado.encontrado) {
      // Si ya se dio de alta a mano → mostrar resumen + selección de instrumento
      if (altaManualRegistrada) {
        const nombre = [
          victimaFuente?.primer_nombre,
          victimaFuente?.segundo_nombre,
          victimaFuente?.primer_apellido,
          victimaFuente?.segundo_apellido,
        ].filter(Boolean).join(' ');

        return (
          <>
            <Surface style={[styles.tarjeta, styles.tarjetaNaranja]}>
              <View style={styles.tarjetaEncabezado}>
                <MaterialCommunityIcons name="account-plus-outline" size={32} color={GOV.naranja} style={styles.icono} />
                <Text style={[styles.tarjetaTitulo, { color: GOV.naranja }]}>
                  Registrada para caracterización
                </Text>
              </View>
              {nombre ? <Text style={styles.nombreCompleto}>{nombre}</Text> : null}
              <Text style={styles.tarjetaMensaje}>{tipoDoc}  ·  {documento}</Text>
              <Text style={styles.tarjetaFuente}>Su condición en el RUV queda por verificar</Text>
            </Surface>

            <Button
              mode="contained"
              icon="home-plus"
              onPress={conformarHogarAltaManual}
              buttonColor={GOV.naranja}
              textColor="#FFFFFF"
              style={[styles.botonAccion, styles.botonConformar]}
              contentStyle={styles.botonAccionContent}
            >
              Conformar hogar
            </Button>
          </>
        );
      }

      return (
        <TarjetaNoEncontrado
          resultado={resultado}
          tipoDoc={tipoDoc}
          documento={documento}
          cargandoRegistro={cargandoRegistro}
          onRegistrarAltaManual={registrarAltaManual}
        />
      );
    }

    if (!resultado.victima?.habilitado_para_caracterizacion) {
      return (
        <TarjetaNoHabilitado
          resultado={resultado}
          onUsarExcepcion={() => {
            setRutaElegida('');
            setSoporteNombre('');
            setSoporteUri('');
            setErrorExcepcion('');
            setModalExcepcion(true);
          }}
        />
      );
    }

    // Regla universal: 1 víctima → 1 hogar. El backend devuelve hogar_activo si existe.
    const hogarActivo = (resultado.victima as any)?.hogar_activo as
      | { id: string; estado: string; total_miembros: number; total_sesiones: number }
      | null
      | undefined;

    // Habilitado: 2 casos según haya o no hogar activo previo.
    return (
      <>
        <TarjetaHabilitado resultado={resultado} />

        {hogarActivo ? (
          // CASO A — Ya tiene hogar activo → continuar caracterización
          <Button
            mode="contained"
            icon="home-search"
            onPress={() => router.push({
              pathname: '/(main)/hogares/[hogarId]/caracterizaciones',
              params: { hogarId: hogarActivo.id },
            })}
            buttonColor={GOV.naranja}
            textColor="#FFFFFF"
            style={[styles.botonAccion, styles.botonConformar]}
            contentStyle={styles.botonAccionContent}
          >
            Ver hogar registrado  ({hogarActivo.total_sesiones} caracterización{hogarActivo.total_sesiones !== 1 ? 'es' : ''})
          </Button>
        ) : (
          // CASO B — Sin hogar → flujo normal de conformar
          <Button
            mode="contained"
            icon="home-plus"
            onPress={conformarHogar}
            disabled={cargandoRegistro}
            loading={cargandoRegistro}
            buttonColor={GOV.azul}
            textColor="#FFFFFF"
            style={[styles.botonAccion, styles.botonConformar]}
            contentStyle={styles.botonAccionContent}
          >
            {cargandoRegistro ? 'Registrando…' : 'Conformar hogar'}
          </Button>
        )}
      </>
    );
  }

  return (
    <View style={styles.root}>
      <GovHeader title="ENTREVISTA DE CARACTERIZACIÓN" subtitle="Conformación del hogar" />

      <ImageBackground source={IMAGEN_FONDO} style={styles.imagenFondo} resizeMode="cover">
        {/* Gradiente sobre la imagen — oscurece hacia abajo para legibilidad */}
        <LinearGradient
          colors={['rgba(0,35,78,0.08)', 'rgba(0,35,78,0.55)', 'rgba(0,35,78,0.92)']}
          locations={[0, 0.45, 1]}
          style={StyleSheet.absoluteFillObject}
        />

        <ScrollView
          style={styles.scroll}
          contentContainerStyle={styles.contenido}
          keyboardShouldPersistTaps="handled"
        >
          {/* Texto hero sobre la imagen */}
          <View style={styles.heroTexto}>
            <Text style={styles.heroTitulo}>Caracterización de Víctimas</Text>
            <Text style={styles.heroSubtitulo}>
              Ingresa el documento de la persona a caracterizar para iniciar el proceso
            </Text>
          </View>

          {/* Tarjeta flotante con el formulario */}
          <View style={styles.cardBusqueda}>
            {!estaOnline && (
              <Chip
                icon="wifi-off"
                mode="flat"
                style={styles.offlineBanner}
                textStyle={styles.offlineBannerTxt}
              >
                Sin conexión — se buscará en los datos offline y se sincronizará al recuperar señal
              </Chip>
            )}

            {/* Tipo de documento */}
            <SelectTipoDoc valor={tipoDoc} onChange={setTipoDoc} />

            {/* Número de documento */}
            <TextInput
              mode="outlined"
              label="Número de documento"
              value={documento}
              onChangeText={setDocumento}
              keyboardType="numeric"
              onSubmitEditing={buscar}
              returnKeyType="search"
              style={styles.input}
              outlineColor={GOV.borde}
              activeOutlineColor={GOV.azul}
              right={documento ? <TextInput.Icon icon="close" onPress={() => setDocumento('')} /> : undefined}
            />

            {/* Ruta de entrevista */}
            <Menu
              visible={menuRutaVisible}
              onDismiss={() => setMenuRutaVisible(false)}
              anchor={
                <Button
                  mode="outlined"
                  icon="routes"
                  onPress={() => setMenuRutaVisible(true)}
                  style={styles.botonRuta}
                  contentStyle={styles.botonRutaContent}
                  textColor={GOV.textoP}
                >
                  Ruta: {rutaLabel}
                </Button>
              }
            >
              {RUTAS.map((r) => (
                <Menu.Item
                  key={r.value}
                  title={r.label}
                  leadingIcon={rutaEntrevista === r.value ? 'check' : undefined}
                  onPress={() => { setRutaEntrevista(r.value); setMenuRutaVisible(false); }}
                />
              ))}
            </Menu>

            {/* Error */}
            {errorBusqueda && (
              <HelperText type="error" visible style={styles.helperError}>
                {errorBusqueda}
              </HelperText>
            )}

            {/* Botón consultar */}
            <Button
              mode="contained"
              icon="magnify"
              onPress={buscar}
              disabled={cargando || !documento.trim()}
              loading={cargando}
              buttonColor={GOV.azul}
              textColor="#FFFFFF"
              style={styles.botonConsultar}
              contentStyle={styles.botonConsultarContent}
            >
              {cargando ? 'Consultando…' : 'Consultar RNI'}
            </Button>
          </View>

          {cargando && (
            <ActivityIndicator animating color="#FFFFFF" size="large" style={styles.spinner} />
          )}

          {!cargando && renderTarjeta()}
        </ScrollView>

        {/* ── Ruta de excepción a la regla de vigencia (Manual §5.1.1) ─────── */}
        <Modal
          visible={modalExcepcion}
          transparent
          animationType="slide"
          onRequestClose={() => setModalExcepcion(false)}
        >
          <View style={styles.excFondo}>
            <Surface style={styles.excCaja}>
              <Text style={styles.excTitulo}>Ruta de excepción</Text>
              <Text style={styles.excAyuda}>
                Esta persona tiene una caracterización vigente. Solo puede
                caracterizarla por una de estas rutas, y debe adjuntar el soporte.
              </Text>

              {RUTAS_EXCEPCION.map((r) => (
                <Pressable
                  key={r.valor}
                  onPress={() => { setRutaElegida(r.valor); setErrorExcepcion(''); }}
                  style={[
                    styles.opcionRuta,
                    rutaElegida === r.valor && styles.opcionRutaActiva,
                  ]}
                >
                  <MaterialCommunityIcons
                    name={rutaElegida === r.valor ? 'radiobox-marked' : 'radiobox-blank'}
                    size={22}
                    color={rutaElegida === r.valor ? GOV.azul : GOV.textoS}
                  />
                  <View style={{ flex: 1, marginLeft: SPACING.sm }}>
                    <Text style={styles.opcionRutaTitulo}>{r.etiqueta}</Text>
                    <Text style={styles.opcionRutaAyuda}>{r.ayuda}</Text>
                  </View>
                </Pressable>
              ))}

              <Button
                mode="outlined"
                icon={soporteNombre ? 'check-circle' : 'paperclip'}
                onPress={adjuntarSoporte}
                style={{ marginTop: SPACING.md }}
              >
                {soporteNombre ? `Adjunto: ${soporteNombre}` : 'Adjuntar soporte'}
              </Button>

              {!!errorExcepcion && (
                <HelperText type="error" visible>{errorExcepcion}</HelperText>
              )}

              <View style={styles.excBotones}>
                <Button
                  mode="text"
                  onPress={() => setModalExcepcion(false)}
                  disabled={verificandoExcepcion}
                >
                  Cancelar
                </Button>
                <Button
                  mode="contained"
                  onPress={confirmarExcepcion}
                  loading={verificandoExcepcion}
                  disabled={verificandoExcepcion}
                  buttonColor={GOV.azul}
                >
                  Continuar
                </Button>
              </View>
            </Surface>
          </View>
        </Modal>
      </ImageBackground>
    </View>
  );
}

// ── Estilos ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  excFondo: {
    flex: 1, backgroundColor: 'rgba(0,0,0,0.55)',
    justifyContent: 'center', padding: SPACING.lg,
  },
  excCaja: {
    backgroundColor: '#FFFFFF', borderRadius: RADIUS.lg, padding: SPACING.lg,
  },
  excTitulo: { ...FONT.h2, color: GOV.azul, marginBottom: SPACING.xs },
  excAyuda: { ...FONT.body, color: GOV.textoS, marginBottom: SPACING.md },
  opcionRuta: {
    flexDirection: 'row', alignItems: 'center', padding: SPACING.sm,
    borderRadius: RADIUS.md, borderWidth: 1, borderColor: '#E0E0E0',
    marginBottom: SPACING.xs,
  },
  opcionRutaActiva: { borderColor: GOV.azul, backgroundColor: '#F0F6FC' },
  opcionRutaTitulo: { ...FONT.label, color: GOV.textoS },
  opcionRutaAyuda: { ...FONT.caption, color: '#757575' },
  excBotones: {
    flexDirection: 'row', justifyContent: 'flex-end',
    gap: SPACING.sm, marginTop: SPACING.md,
  },
  root: { flex: 1, backgroundColor: '#00234E' },
  imagenFondo: { flex: 1 },
  scroll: { flex: 1 },
  contenido: { padding: SPACING.md, paddingBottom: SPACING.xl },

  // Hero sobre la imagen
  heroTexto: {
    alignItems: 'center',
    paddingTop: SPACING.lg,
    paddingBottom: SPACING.md,
    paddingHorizontal: SPACING.md,
  },
  heroTitulo: {
    fontSize: 21,
    fontWeight: '800',
    color: '#FFFFFF',
    textAlign: 'center',
    letterSpacing: 0.5,
    marginBottom: SPACING.xs,
    textShadowColor: 'rgba(0,0,0,0.6)',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 6,
  },
  heroSubtitulo: {
    fontSize: 13,
    color: 'rgba(255,255,255,0.88)',
    textAlign: 'center',
    lineHeight: 19,
    textShadowColor: 'rgba(0,0,0,0.5)',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 4,
  },

  // Tarjeta flotante del formulario
  cardBusqueda: {
    backgroundColor: '#FFFFFF',
    borderRadius: RADIUS.lg,
    padding: SPACING.md,
    ...SHADOW.fab,
    marginBottom: SPACING.md,
  },

  input: { marginBottom: SPACING.sm, backgroundColor: GOV.superficie },

  offlineBanner: { marginBottom: SPACING.sm, backgroundColor: '#FFF3E0' },
  offlineBannerTxt: { color: '#E65100', fontSize: 12 },

  botonRuta: {
    marginBottom: SPACING.sm,
    borderColor: GOV.borde,
    borderRadius: RADIUS.sm,
    justifyContent: 'flex-start',
  },
  botonRutaContent: { justifyContent: 'flex-start' },

  helperError: { marginBottom: SPACING.xs },
  botonConsultar: { marginTop: SPACING.xs, borderRadius: RADIUS.sm },
  botonConsultarContent: { paddingVertical: SPACING.xs },
  spinner: { marginTop: SPACING.xl },

  // Tarjetas resultado
  tarjeta: { marginTop: SPACING.lg, padding: SPACING.md, borderRadius: RADIUS.md, ...SHADOW.card },
  tarjetaGris:   { borderLeftWidth: 4, borderLeftColor: GOV.textoS },
  tarjetaNaranja:{ borderLeftWidth: 4, borderLeftColor: GOV.naranja },
  tarjetaVerde:  { borderLeftWidth: 4, borderLeftColor: GOV.verde },

  tarjetaEncabezado: { flexDirection: 'row', alignItems: 'center', marginBottom: SPACING.sm, gap: SPACING.sm },
  icono: { marginRight: SPACING.xs },
  tarjetaTitulo: { ...FONT.h3, flex: 1, flexWrap: 'wrap' },
  tarjetaMensaje:{ ...FONT.small, marginBottom: SPACING.xs },
  tarjetaFuente: { ...FONT.caption, marginTop: SPACING.xs },

  // Selección entre personas que comparten documento. Área de toque holgada:
  // se usa en campo, de pie y a veces con guantes.
  candidato: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: SPACING.sm,
    paddingHorizontal: SPACING.xs,
    borderRadius: RADIUS.md,
    borderWidth: 1,
    borderColor: GOV.borde,
    marginBottom: SPACING.xs,
    minHeight: 56,
  },
  candidatoTextos: { flex: 1, paddingRight: SPACING.xs },
  candidatoNombre: { ...FONT.body, fontWeight: '700' },
  candidatoMeta: { ...FONT.caption, marginTop: 2 },

  nombreCompleto: { ...FONT.h3, marginBottom: SPACING.sm },
  chipsFila: { flexDirection: 'row', flexWrap: 'wrap', gap: SPACING.xs, marginBottom: SPACING.sm },
  chip: { height: 28 },
  datoSecundario:{ ...FONT.small, marginBottom: SPACING.xs },
  divider: { marginVertical: SPACING.md, backgroundColor: GOV.borde },

  botonAccion: { borderRadius: RADIUS.sm },
  botonAccionContent: { paddingVertical: SPACING.xs },

  // Sección instrumento
  seccionInstr: {
    marginTop: SPACING.lg,
    backgroundColor: GOV.superficie,
    borderRadius: RADIUS.md,
    padding: SPACING.md,
    ...SHADOW.card,
  },
  seccionInstrTitulo: {
    ...FONT.h3,
    color: GOV.azulOscuro,
    marginBottom: SPACING.md,
  },
  sinInstrTxt: {
    ...FONT.small,
    color: GOV.textoT,
    textAlign: 'center',
    paddingVertical: SPACING.md,
    fontStyle: 'italic',
  },

  // Tarjeta instrumento item
  instrCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: GOV.fondoApp,
    borderRadius: RADIUS.sm,
    padding: SPACING.sm,
    marginBottom: SPACING.xs,
    borderWidth: 2,
    borderColor: 'transparent',
  },
  instrCardActivo: {
    borderColor: GOV.azul,
    backgroundColor: GOV.azulTenue,
  },
  instrIcono: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: GOV.azulTenue,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: SPACING.sm,
    borderWidth: 1,
    borderColor: `${GOV.azul}33`,
  },
  instrIconoActivo: {
    backgroundColor: GOV.azul,
    borderColor: GOV.azul,
  },
  instrTexto: { flex: 1 },
  instrNombre: { ...FONT.small, fontWeight: '600', color: GOV.textoP, marginBottom: 2 },
  instrNombreActivo: { color: GOV.azulOscuro, fontWeight: '700' },
  instrMeta: { ...FONT.caption, color: GOV.textoT, fontFamily: 'monospace' },

  // Botón conformar hogar
  botonConformar: { marginTop: SPACING.md },

  // Select tipo documento
  selectTrigger: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: GOV.superficie,
    borderRadius: RADIUS.sm,
    borderWidth: 1,
    borderColor: GOV.borde,
    paddingHorizontal: SPACING.sm,
    paddingVertical: 10,
    marginBottom: SPACING.sm,
    gap: SPACING.sm,
  },
  selectIconoWrap: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: GOV.azulTenue,
    justifyContent: 'center',
    alignItems: 'center',
  },
  selectTextos: { flex: 1 },
  selectLabel: {
    fontSize: 11,
    color: GOV.textoT,
    fontWeight: '500',
    marginBottom: 1,
  },
  selectValor: {
    fontSize: 15,
    color: GOV.textoP,
    fontWeight: '600',
  },

  // Modal selección
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.45)',
    justifyContent: 'flex-end',
  },
  modalCard: {
    backgroundColor: '#FFFFFF',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    paddingHorizontal: SPACING.md,
    paddingBottom: SPACING.xl,
    paddingTop: SPACING.sm,
    ...SHADOW.fab,
  },
  modalHandle: {
    width: 40,
    height: 4,
    borderRadius: 2,
    backgroundColor: GOV.borde,
    alignSelf: 'center',
    marginBottom: SPACING.md,
  },
  modalTitulo: {
    ...FONT.h3,
    color: GOV.azulOscuro,
    marginBottom: SPACING.sm,
    paddingHorizontal: SPACING.xs,
  },
  modalOpcion: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    paddingHorizontal: SPACING.xs,
    borderRadius: RADIUS.sm,
    gap: SPACING.sm,
    marginBottom: 2,
  },
  modalOpcionActiva: {
    backgroundColor: GOV.azulTenue,
  },
  modalOpcionIcono: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: GOV.azulTenue,
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalOpcionIconoActivo: {
    backgroundColor: GOV.azul,
  },
  modalOpcionTextos: { flex: 1 },
  modalOpcionCodigo: {
    fontSize: 12,
    fontWeight: '700',
    color: GOV.textoT,
    letterSpacing: 0.5,
  },
  modalOpcionCodigoActivo: { color: GOV.azulOscuro },
  modalOpcionNombre: {
    fontSize: 14,
    fontWeight: '500',
    color: GOV.textoP,
  },
  modalOpcionNombreActivo: { color: GOV.azulOscuro, fontWeight: '600' },

  // Formulario de alta manual
  formTitulo: { ...FONT.h3, color: GOV.naranja, marginBottom: 2 },
  formSubtitulo: { ...FONT.caption, color: GOV.textoS, marginBottom: SPACING.sm, fontFamily: 'monospace' },
  formInput: { marginBottom: SPACING.sm, backgroundColor: GOV.superficie },
  formLabel: { ...FONT.label, color: GOV.textoS, marginBottom: SPACING.xs },
  segmentedGenero: { marginBottom: SPACING.md },
  formBotones: { flexDirection: 'row', gap: SPACING.xs },
});
