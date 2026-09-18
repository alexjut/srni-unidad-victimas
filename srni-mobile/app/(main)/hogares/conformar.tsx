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
  View, ScrollView, StyleSheet, Pressable,
  KeyboardAvoidingView, Platform, Alert,
} from 'react-native';
import {
  Text, Button, Divider, Chip,
  ActivityIndicator,
} from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { hogaresApi } from '../../../src/api/hogares';
import type { MiembroHogarResumen } from '../../../src/types';
import * as hogaresOfflineDao from '../../../src/db/hogaresOfflineDao';
import { cargarMiembrosHogar } from '../../../src/services/miembrosHogar';
import * as colaDao from '../../../src/db/colaDao';
import { useCaracterizacionStore } from '../../../src/stores/caracterizacionStore';
import { useSyncStore } from '../../../src/stores/syncStore';
import { GovHeader } from '../../../src/components/GovHeader';
import {
  FormularioIntegrante, SelectorModal, CampoSelector, type IntegranteNuevo,
} from '../../../src/components/FormularioIntegrante';
import { GovButton } from '../../../src/components/GovButton';
import { GOV, SPACING, RADIUS, SHADOW, FONT } from '../../../src/theme/govTheme';
import { interpretarError } from '../../../src/utils/errores';
import { reportarError } from '../../../src/services/errorReporter';

// ── Catálogos locales ─────────────────────────────────────────────────────────

// Documento oficial §2: PARENTESCO y GÉNERO ya no se capturan en la conformación
// del hogar (se piden en el Capítulo B "Datos básicos"). Los catálogos se
// eliminaron de esta pantalla para evitar la doble captura.

const RUTAS = [
  { value: 'GENERAL',                   label: 'General' },
  { value: 'ACCIONES_CONSTITUCIONALES', label: 'Acc. Constitucionales' },
  { value: 'MODIFICACION_NUCLEO',       label: 'Mod. Núcleo Familiar' },
  { value: 'ESPECIAL',                  label: 'Ruta Especial' },
];

// ── Tipo local para un integrante ya agregado ─────────────────────────────────

interface IntegranteAgregado {
  key: string;
  /**
   * Id en el servidor. Solo lo tienen los que se agregaron con señal — es lo
   * que permite quitarlos (APK-004). Los guardados offline todavía no existen
   * allá, así que no hay qué borrar hasta que sincronicen.
   */
  miembro_id?: string;
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

// ── Card de integrante ya agregado ────────────────────────────────────────────

function IntegranteCard({ item, onQuitar }: {
  item: IntegranteAgregado;
  /** APK-004 — sin esto, un integrante capturado por error se quedaba adentro. */
  onQuitar?: (item: IntegranteAgregado) => void;
}) {
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
      {/*
        Al autorizado no se le ofrece: es el titular del hogar y quitarlo lo
        dejaría sin dueño. El servidor lo rechaza igual, pero mostrar un botón
        que siempre falla es peor que no mostrarlo.
      */}
      {!item.es_autorizado && onQuitar && (
        <Pressable
          onPress={() => onQuitar(item)}
          hitSlop={10}
          accessibilityLabel={`Quitar a ${item.nombre_display}`}
          style={styles.quitarBtn}
        >
          <MaterialCommunityIcons name="close-circle-outline" size={22} color={GOV.rojo} />
        </Pressable>
      )}
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

  // §2 — el formulario avisa si hay un Tutor/Cuidador sin su constancia.
  const [constanciaPendienteEnForm, setConstanciaPendienteEnForm] = useState(false);

  // Modales selectores
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
      // Lo que el servidor ya conoce del hogar. Con el control de vigencia
      // retirado, conformar el hogar de alguien que ya lo tenia devuelve el hogar
      // EXISTENTE con su familia completa (HTTP 200), y hasta el 11-sep-2026 esta
      // pantalla descartaba esa lista y pintaba un solo integrante.
      //
      // El dano no era cosmetico: la encuestadora veia «1 integrante» sobre una
      // familia de cinco y volvia a teclear al conyuge y a los hijos. `agregar
      // miembro` no deduplica —no pasa por el servicio que verifica el vinculo— y
      // el unico constraint es el del autorizado, asi que cada persona quedaba dos
      // veces en el hogar. Es corrupcion de datos silenciosa, y aparecia justo en
      // el caso que el retiro del control volvio corriente.
      let miembrosServidor: MiembroHogarResumen[] = [];

      const crearOffline = async () => {
        // APK-003 — sin señal, esta función creaba un hogar NUEVO cada vez. Volver
        // a buscar la misma cédula dejaba dos hogares del mismo autorizado y dos
        // altas en la cola. Con señal no pasa: el backend devuelve el que ya existe.
        const existente = await hogaresOfflineDao.buscarPorAutorizado(victimaLocalId);
        if (existente) {
          // Si ya sincronizó, se sigue con el id del servidor: es el mismo hogar y
          // desde ahí los integrantes van por POST directo, no por la cola.
          const yaEnServidor = !!existente.id_servidor;
          setHogarIdLocal(yaEnServidor ? existente.id_servidor! : existente.id_local);
          setHogarId(yaEnServidor ? existente.id_servidor! : existente.id_local);
          setHogarEsLocal(!yaEnServidor);
          return;
        }

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
            miembrosServidor = data.miembros ?? [];
          } catch (err: any) {
            if (err?.response) throw err; // error real del servidor → propagar
            // Sin respuesta = red caída aunque la bandera dijera online → offline.
            await crearOffline();
          }
        } else {
          await crearOffline();
        }

        // La lista de integrantes.
        //
        // Si el servidor devolvio un hogar que YA tenia familia, se siembra con
        // ella: es la unica forma de que la encuestadora vea a quien ya esta
        // registrado y no lo capture de nuevo. Los retirados se muestran tambien,
        // marcados, para que se entienda por que el hogar tiene los que tiene.
        const v = victimaFuente;
        const nombreAutorizado = v
          ? [v.primer_nombre, v.segundo_nombre, v.primer_apellido, v.segundo_apellido]
              .filter(Boolean).join(' ')
          : 'Autorizado';

        if (miembrosServidor.length > 0) {
          setIntegrantes(miembrosServidor.map((m) => ({
            key: m.id,
            es_autorizado: !!m.es_autorizado,
            // El autorizado se nombra desde la ficha buscada, que es el dato
            // confirmado con la persona que esta enfrente; los demas, con lo que
            // manda el servidor.
            nombre_display: m.es_autorizado
              ? nombreAutorizado
              : ((m.nombre_completo || '').trim() || 'Integrante sin nombre'),
            tipo_documento: m.tipo_documento_codigo ?? '',
            numero_documento: m.numero_documento ?? '',
            rol_display: m.es_autorizado
              ? 'Autorizado'
              : (m.retirado_en
                ? `${m.motivo_retiro_display || 'Retirado'} · desde ${m.retirado_en}`
                : (m.parentesco_display || m.rol_display || 'Integrante')),
            fecha_nacimiento: m.fecha_nacimiento ?? '',
            constancia_nombre: '',
          })));
        } else {
          // Hogar nuevo, u offline: el autorizado es el unico que se conoce. Online
          // lo inserta el backend; sin senial se muestra y cuenta en numero_personas.
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
        }
      } catch (err: any) {
        // APK-002. Antes acá iba `JSON.stringify(err.response.data)`, que le
        // ponía al encuestador el JSON crudo del servidor — y con el cuerpo
        // vacío, la palabra «null», porque `typeof null === 'object'`.
        const info = interpretarError(err, 'No se pudo crear el hogar.');
        setErrorHogar(info.mensaje);
        // El diagnóstico va al reporte, no a la pantalla: es lo que le faltaba
        // a soporte para saber si fue un 409, un 500 o falta de señal.
        if (!info.sinRed) {
          reportarError({
            nivel: 'error',
            mensaje: `conformar/crearHogar — ${info.diagnostico}`,
            pantalla: 'hogares/conformar',
            contexto: { autorizado_id: victimaLocalId ?? '' },
          });
        }
      } finally {
        setCreandoHogar(false);
      }
    }
    crearHogar();
  }, []);

  // ── Integrante agregado desde el formulario ──────────────────────────────
  function alAgregarIntegrante(nuevo: IntegranteNuevo) {
    setIntegrantes(prev => [
      ...prev,
      {
        key: `${Date.now()}`,
        miembro_id: nuevo.miembro_id,
        es_autorizado: false,
        nombre_display: nuevo.nombre_display,
        tipo_documento: nuevo.tipo_documento,
        numero_documento: nuevo.numero_documento,
        rol_display: nuevo.rol_display,
        fecha_nacimiento: nuevo.fecha_nacimiento,
        constancia_nombre: nuevo.constancia_nombre,
      },
    ]);
  }

  /**
   * Quita un integrante capturado por error (APK-004).
   *
   * Confirma con el nombre adentro: en una lista de cinco personas, un
   * "¿Confirma quitar?" a secas no dice a cuál.
   *
   * Solo se ofrece para los que ya están en el servidor. Un integrante guardado
   * offline todavía tiene su alta en la cola: borrarlo solo de la pantalla lo
   * haría reaparecer al sincronizar, que es peor que no poder quitarlo.
   */
  function quitarIntegrante(item: IntegranteAgregado) {
    // Sin hogar en el servidor no hay a quién pedirle el borrado. Se trata igual
    // que el integrante sin sincronizar: mismo aviso, misma salida.
    if (!item.miembro_id || !hogarId) {
      Alert.alert(
        'Todavía no se puede quitar',
        'Este integrante se guardó sin señal y aún no ha sincronizado. Cuando '
        + 'haya conexión podrá quitarlo desde el detalle del hogar.',
      );
      return;
    }

    Alert.alert(
      'Quitar integrante',
      `¿Quitar a ${item.nombre_display} del hogar? Esto es para corregir una `
      + 'captura equivocada; no se usa cuando la persona dejó de vivir en el hogar.',
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Quitar',
          style: 'destructive',
          onPress: async () => {
            try {
              await hogaresApi.quitarMiembro(hogarId, item.miembro_id!);
              setIntegrantes(prev => prev.filter(i => i.key !== item.key));
            } catch (err: any) {
              const info = interpretarError(err, 'No se pudo quitar el integrante.');
              Alert.alert('No se pudo quitar', info.mensaje);
              if (!info.sinRed) {
                reportarError({
                  nivel: 'warn',
                  mensaje: `conformar/quitarMiembro — ${info.diagnostico}`,
                  pantalla: 'hogares/conformar',
                  contexto: { hogar_id: String(hogarId ?? '') },
                });
              }
            }
          },
        },
      ],
    );
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
            <IntegranteCard key={item.key} item={item} onQuitar={quitarIntegrante} />
          ))}

          <Divider style={styles.divider} />

          {/* ── Formulario agregar integrante ── */}
          <Text style={styles.secTitulo}>Agregar integrante</Text>

          <FormularioIntegrante
            hogarId={hogarId}
            hogarEsLocal={hogarEsLocal}
            onAgregado={alAgregarIntegrante}
            onConstanciaPendienteChange={setConstanciaPendienteEnForm}
            documentosExistentes={integrantes.map(i => i.numero_documento)}
            pantalla="hogares/conformar"
          />

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
  // Alineado arriba, junto al nombre: es la línea que identifica a quién se
  // está quitando. Centrado quedaría a la altura de los metadatos.
  quitarBtn: {
    paddingTop: 2,
    paddingLeft: SPACING.xs,
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
