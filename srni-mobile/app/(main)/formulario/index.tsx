// Lista de capítulos — Sprint 8: progreso real por capítulo + estado visual.
import { useEffect, useState, useMemo, useCallback } from 'react';
import { View, FlatList, StyleSheet, Pressable, Alert, Modal, KeyboardAvoidingView, Platform } from 'react-native';
import { Text, ProgressBar, ActivityIndicator, TextInput } from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { router, useLocalSearchParams, useFocusEffect } from 'expo-router';
import * as instrumentos from '../../../src/services/instrumentos';
import * as borradoresDao from '../../../src/db/borradoresDao';
import { calcularProgresoOffline, type MiembroRef } from '../../../src/services/progreso';
import * as colaDao from '../../../src/db/colaDao';
import type { CapituloRow, InstrumentoMeta } from '../../../src/db/instrumentoDao';
import { useIAStore } from '../../../src/stores/iaStore';
import { useSyncStore } from '../../../src/stores/syncStore';
import { cargarMiembrosHogar } from '../../../src/services/miembrosHogar';
import { encuestasApi } from '../../../src/api/encuestas';
import { reportarError } from '../../../src/services/errorReporter';
import { GovHeader } from '../../../src/components/GovHeader';
import { GovButton } from '../../../src/components/GovButton';
import { EmptyState } from '../../../src/components/EmptyState';
import { GOV, SPACING, RADIUS, SHADOW, FONT } from '../../../src/theme/govTheme';

// ─── Tipos ────────────────────────────────────────────────────────────────────

type EstadoCap = 'pendiente' | 'en_progreso' | 'completado';

interface CapProgress {
  estado: EstadoCap;
  respondidas: number;
  obligatorias: number;
}

const ESTADO_ICONO: Record<EstadoCap, string> = {
  pendiente:    'circle-outline',
  en_progreso:  'progress-clock',
  completado:   'check-circle',
};

const ESTADO_COLOR: Record<EstadoCap, string> = {
  pendiente:   GOV.borde,
  en_progreso: GOV.naranja,
  completado:  GOV.verde,
};

// ─── Tarjeta de capítulo ──────────────────────────────────────────────────────

function CapituloCard({
  capitulo,
  index,
  progress,
  sesionServerId,
  instrumentoId,
  hogarId,
  borradorId,
  modoIA,
}: {
  capitulo: CapituloRow;
  index: number;
  progress: CapProgress;
  sesionServerId?: string;
  instrumentoId?: string;
  hogarId?: string;
  borradorId?: string;
  modoIA: boolean;
}) {
  const colorEstado = ESTADO_COLOR[progress.estado];
  const iconoEstado = ESTADO_ICONO[progress.estado];

  function handlePress() {
    if (modoIA) {
      router.push({
        pathname: '/(main)/formulario/grabacion-entrevista' as any,
        params: {
          temaId: capitulo.id,
          capituloNombre: capitulo.nombre,
          ...(sesionServerId ? { sesionServerId } : {}),
          ...(instrumentoId  ? { instrumentoId }  : {}),
          // #15 — hogarId/borradorId deben viajar por TODO el flujo IA para que
          // al caer a manual se carguen los miembros y el borrador offline.
          ...(hogarId        ? { hogarId }         : {}),
          ...(borradorId     ? { borradorId }     : {}),
        },
      });
    } else {
      router.push({
        pathname: '/(main)/formulario/[temaId]',
        params: {
          temaId: capitulo.id,
          ...(sesionServerId ? { sesionServerId } : {}),
          ...(instrumentoId  ? { instrumentoId }  : {}),
          ...(hogarId        ? { hogarId }         : {}),
          ...(borradorId     ? { borradorId }     : {}),
        },
      });
    }
  }

  const esCompleto    = progress.estado === 'completado';
  const esEnProgreso  = progress.estado === 'en_progreso';
  const esPendiente   = progress.estado === 'pendiente';
  const faltan        = Math.max(0, progress.obligatorias - progress.respondidas);

  return (
    <Pressable
      onPress={handlePress}
      style={({ pressed }) => [
        styles.card,
        esCompleto && styles.cardCompletado,
        esEnProgreso && styles.cardEnProgreso,
        pressed && styles.cardPressed,
      ]}
      accessibilityRole="button"
      accessibilityLabel={
        `Capítulo ${index + 1}: ${capitulo.nombre}. ` +
        (esCompleto ? 'Completo' : esEnProgreso ? `Faltan ${faltan} preguntas` : 'Sin iniciar')
      }
    >
      {/* Círculo izquierdo: número o check según estado */}
      <View style={[
        styles.numCircle,
        esCompleto && styles.numCircleCompleto,
        esEnProgreso && styles.numCircleEnProgreso,
      ]}>
        {esCompleto ? (
          <MaterialCommunityIcons name="check" size={22} color="#FFFFFF" />
        ) : esEnProgreso ? (
          <MaterialCommunityIcons name="progress-clock" size={20} color={GOV.naranja} />
        ) : (
          <Text style={styles.numTxt}>{String(index + 1).padStart(2, '0')}</Text>
        )}
      </View>

      <View style={styles.cardTexto}>
        {/* Encabezado: nombre + chip de estado */}
        <View style={styles.cardEncabezado}>
          <Text
            style={[styles.capNombre, esCompleto && styles.capNombreOk]}
            numberOfLines={2}
          >
            {capitulo.nombre}
          </Text>
          <View style={[
            styles.chipEstado,
            esCompleto && styles.chipEstadoOk,
            esEnProgreso && styles.chipEstadoProgreso,
            esPendiente && styles.chipEstadoPendiente,
          ]}>
            <MaterialCommunityIcons
              name={iconoEstado as any}
              size={11}
              color={
                esCompleto ? GOV.verde
                : esEnProgreso ? GOV.naranja
                : GOV.textoT
              }
            />
            <Text style={[
              styles.chipEstadoTxt,
              esCompleto && { color: GOV.verde },
              esEnProgreso && { color: GOV.naranja },
              esPendiente && { color: GOV.textoT },
            ]}>
              {esCompleto ? 'Completo' : esEnProgreso ? `Faltan ${faltan}` : 'Sin iniciar'}
            </Text>
          </View>
        </View>

        <Text style={styles.capCodigo}>
          [{capitulo.codigo}]  ·  {capitulo.nivel === 'PERSONA' ? 'Por persona' : 'Por hogar'}
        </Text>

        {/* Barra de progreso + contador con % explícito */}
        {progress.obligatorias > 0 && (
          <View style={styles.capProgresoWrap}>
            <ProgressBar
              progress={Math.min(1, progress.respondidas / progress.obligatorias)}
              style={styles.capProgressBar}
              color={colorEstado}
            />
            <Text style={[styles.capProgresoPct, { color: colorEstado }]}>
              {progress.respondidas}/{progress.obligatorias} · {Math.round((progress.respondidas / progress.obligatorias) * 100)}%
            </Text>
          </View>
        )}
      </View>

      {modoIA ? (
        <MaterialCommunityIcons name="robot" size={16} color={GOV.azul} style={{ marginRight: 4 }} />
      ) : null}
      <MaterialCommunityIcons
        name="chevron-right"
        size={20}
        color={esCompleto ? GOV.verde : GOV.borde}
      />
    </Pressable>
  );
}

// ─── Pantalla ─────────────────────────────────────────────────────────────────

export default function FormularioIndexScreen() {
  const { sesionServerId, instrumentoId, hogarId, borradorId: borradorIdParam } = useLocalSearchParams<{
    sesionServerId?: string;
    instrumentoId?: string;
    hogarId?: string;
    borradorId?: string;
  }>();

  const { activo: iaActivo } = useIAStore();
  const estaOnline = useSyncStore((s) => s.estaOnline);
  const refrescarContadores = useSyncStore((s) => s.refrescarContadores);

  // Borrador local que hila todo el flujo OFFLINE. Online (con sesionServerId)
  // no lo necesita: el capítulo resuelve su borrador por findBySesionId.
  const [borradorId, setBorradorId] = useState<string | null>(borradorIdParam ?? null);
  // Estado del borrador resuelto. Interesa uno solo: CERRADO_LOCAL significa que
  // la encuestadora ya cerró la entrevista y el FINALIZAR está esperando señal.
  // Volver a ofrecerle «Finalizar» encolaría un segundo cierre que el servidor
  // rechaza con 400 y deja un ítem en 'error' que nunca se limpia.
  const [borradorEstado, setBorradorEstado] = useState<string | null>(null);
  const cerradaSinEnviar = borradorEstado === 'CERRADO_LOCAL';

  const [capitulos, setCapitulos] = useState<CapituloRow[]>([]);
  const [meta, setMeta] = useState<InstrumentoMeta | null>(null);
  const [cargando, setCargando] = useState(true);
  const [modoIA, setModoIA] = useState<boolean | null>(null);

  // Progreso por capítulo — fix #8/#18: el denominador ahora es OBLIGATORIAS
  // VISIBLES (evaluando skip-logic), no el conteo estático que inflaba el total
  // con obligatorias ocultas y dejaba el progreso atascado bajo 100%.
  //   - respuestasCompuesto: mapa `pregunta_id|miembro_id` → valor del borrador.
  //   - miembrosRef: miembros del hogar (PERSONA se cuenta por miembro).
  const [respuestasCompuesto, setRespuestasCompuesto] = useState<Record<string, string>>({});
  const [miembrosRef, setMiembrosRef] = useState<MiembroRef[]>([]);

  // Finalizar sesión
  const [modalFinalizar, setModalFinalizar] = useState(false);
  const [observaciones, setObservaciones] = useState('');
  const [finalizando, setFinalizando] = useState(false);

  const [descargando, setDescargando] = useState(false);
  const [errorDescarga, setErrorDescarga] = useState('');

  // Sprint 18 Fase B: instrumento_codigo de la sesión es AUTORIDAD ÚNICA.
  // Prioridad de resolución:
  //   1. encuestasApi.detalle(sesionId).instrumento_codigo (backend, fuente)
  //   2. codigoPorInstrumentoId(instrumentoId param) — offline-friendly,
  //      busca el UUID en el bundle local y devuelve el código del perfil
  // Si ninguna funciona → ERROR explícito, bloquear formulario.
  // NUNCA caer a 'TERRITORIAL' como default: el encuestador podría capturar
  // contra el instrumento equivocado y corromper datos en silencio.
  async function cargarTodo() {
    setCargando(true);
    setErrorDescarga('');
    try {
      let codigoPerfil: string | null = null;
      let origen = 'desconocido';

      if (sesionServerId) {
        try {
          const { data: sesion } = await encuestasApi.detalle(sesionServerId);
          codigoPerfil = (sesion as any).instrumento_codigo ?? null;
          if (codigoPerfil) origen = 'backend';
        } catch (e) {
          reportarError({
            nivel: 'warn',
            mensaje: 'encuestasApi.detalle falló — intentando fallback offline via instrumentoId',
            pantalla: 'formulario/index',
            contexto: { sesionServerId },
          });
        }
      }

      // Fallback OFFLINE: usar el instrumentoId que vino como param para
      // buscar el código en el bundle local.
      if (!codigoPerfil && instrumentoId) {
        codigoPerfil = instrumentos.codigoPorInstrumentoId(instrumentoId);
        if (codigoPerfil) origen = 'bundle-by-uuid';
      }

      // Sin ninguna fuente confiable → ERROR. NO caer a TERRITORIAL.
      if (!codigoPerfil) {
        setErrorDescarga(
          'No se pudo determinar el instrumento de esta sesión. ' +
          'Conéctate a internet para sincronizar o vuelve a crear la caracterización.'
        );
        reportarError({
          nivel: 'error',
          mensaje: 'No se pudo determinar codigo de instrumento (sin backend ni instrumentoId match)',
          pantalla: 'formulario/index',
          contexto: { sesionServerId, instrumentoId, hogarId },
        });
        return;
      }

      try {
        instrumentos.activarPerfil(codigoPerfil);
      } catch (e) {
        setErrorDescarga(
          `El instrumento "${codigoPerfil}" no está disponible en este dispositivo. ` +
          'Reinstala la aplicación para obtener los instrumentos más recientes.'
        );
        reportarError({
          nivel: 'error',
          mensaje: 'activarPerfil falló',
          stack: (e as Error)?.stack,
          pantalla: 'formulario/index',
          contexto: { codigoPerfil, origen },
        });
        return;
      }

      // Leer de memoria — instantáneo
      setCapitulos(instrumentos.getCapitulos());
      setMeta(instrumentos.getMeta());

      if (sesionServerId) {
        const borrador = await borradoresDao.findBySesionId(sesionServerId);
        if (borrador) {
          setBorradorId(borrador.id);
          setBorradorEstado(borrador.estado);
          setRespuestasCompuesto(await borradoresDao.getRespuestaMapCompuesto(borrador.id));
        }
      } else if (hogarId && instrumentoId) {
        // ── OFFLINE: resolver UN ÚNICO borrador para (hogar, instrumento) ──────
        // Reutilizar el que llegó por param, o el existente para ese hogar+
        // instrumento, o crear uno nuevo. Así todos los capítulos comparten el
        // mismo borrador y el progreso se lee localmente (sin servidor).
        let bid = borradorIdParam ?? null;
        let fila = null;
        if (!bid) {
          fila = await borradoresDao.findBorradorOfflinePorHogarInstrumento(hogarId, instrumentoId);
          bid = fila?.id ?? null;
        }
        if (!bid) {
          fila = await borradoresDao.crearBorrador(instrumentoId, hogarId);
          bid = fila.id;
        }
        if (!fila) fila = await borradoresDao.getBorrador(bid);
        setBorradorId(bid);
        setBorradorEstado(fila?.estado ?? null);
        setRespuestasCompuesto(await borradoresDao.getRespuestaMapCompuesto(bid));
      }
    } catch (e) {
      reportarError({
        nivel: 'error',
        mensaje: 'formulario/index cargarTodo falló: ' + ((e as Error)?.message ?? String(e)),
        stack: (e as Error)?.stack,
        pantalla: 'formulario/index',
        contexto: { sesionServerId, instrumentoId, hogarId },
      });
    } finally {
      setCargando(false);
    }
  }

  useEffect(() => {
    cargarTodo();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sesionServerId, hogarId, instrumentoId]);

  // Sprint 21 fix — cargar miembros del hogar para calcular bien el progreso.
  // Tolerante a red (fix #4/#38): online → caché; offline-local →
  // construirMiembrosOffline; online caído → caché del servidor. Se guardan los
  // IDS (no solo el conteo) porque el progreso PERSONA lee la respuesta de cada
  // miembro por su clave `pregunta_id|miembro_id`. Si no hay miembros, queda
  // vacío y el servicio de progreso usa un miembro fantasma (≡ Math.max(N, 1)).
  useEffect(() => {
    if (!hogarId) return;
    let activo = true;
    cargarMiembrosHogar(hogarId)
      .then((ms) => { if (activo) setMiembrosRef(ms.map((m) => ({ id: m.id }))); })
      .catch(() => { /* sin datos: queda vacío (miembro fantasma en el cálculo) */ });
    return () => { activo = false; };
  }, [hogarId]);

  // Sprint 21 fix — recalcular progreso al volver al pantalla (no solo
  // al cambiar sesionServerId). El bug anterior: el useEffect con
  // [sesionServerId] solo corría una vez; al volver del capítulo el
  // contador seguía mostrando '0/N Sin iniciar' aunque hubieras respondido.
  // useFocusEffect se dispara cada vez que la pantalla recupera el foco.
  //
  // Sprint 21 fix #2: garantizar que el perfil esté activado en memoria
  // antes de contar. Si el cache se desactivó (al cambiar de caracterización
  // o al rotar app), getCapituloIdDePregunta devuelve null para todas las
  // preguntas y el conteo queda en 0 falsamente. Reactivamos siempre.
  useFocusEffect(
    useCallback(() => {
      let vivo = true;
      (async () => {
        try {
          // 1. Asegurar que el perfil correcto está activo en memoria
          const metaActual = instrumentos.getMeta();
          if (metaActual?.perfil_codigo) {
            try { instrumentos.activarPerfil(metaActual.perfil_codigo); }
            catch { /* perfil no en bundle — se mantiene el cache previo */ }
          }

          // 2. Resolver borrador local
          //    Online: por sesion del servidor. Offline: el borrador único de
          //    este (hogar, instrumento) que ya resolvió cargarTodo.
          let borradorRef: borradoresDao.BorradorRow | null = null;
          if (sesionServerId) {
            borradorRef = await borradoresDao.findBySesionId(sesionServerId);
          } else if (borradorId) {
            borradorRef = await borradoresDao.getBorrador(borradorId);
          }
          if (!borradorRef || !vivo) {
            console.log('[formulario/index] useFocusEffect: borrador no encontrado',
              { sesionServerId, borradorId });
            return;
          }

          // 3. Releer respuestas del borrador (clave pregunta_id|miembro_id).
          //    El progreso real (obligatorias VISIBLES respondidas) se calcula
          //    en el memo de abajo con calcularProgresoOffline.
          const mapa = await borradoresDao.getRespuestaMapCompuesto(borradorRef.id);
          console.log('[formulario/index] useFocusEffect: respuestas recargadas',
            { borradorId: borradorRef.id, respuestas: Object.keys(mapa).length });

          if (vivo) setRespuestasCompuesto(mapa);
        } catch (err) {
          console.warn('[formulario/index] useFocusEffect ERROR:', err);
        }
      })();
      return () => { vivo = false; };
    }, [sesionServerId, borradorId]),
  );

  // ── Progreso global ─────────────────────────────────────────────────────────
  // Fix #8/#18 — el denominador son las obligatorias VISIBLES (evaluando
  // skip-logic contra el estado actual del borrador), no el conteo estático.
  // Antes, una obligatoria oculta por una regla HABILITAR no disparada inflaba
  // el total y el progreso se atascaba sin llegar nunca a 100%.
  // El cálculo (HOGAR 1×, PERSONA por miembro) es el MISMO que el de la
  // pantalla de capítulo, centralizado en services/progreso para que coincidan.
  const progresoData = useMemo(
    () => calcularProgresoOffline(
      capitulos,
      instrumentos.getPreguntas,
      instrumentos.getReglas(),
      miembrosRef,
      respuestasCompuesto,
    ),
    // getPreguntas/getReglas leen el perfil activo en memoria; `capitulos`
    // cambia al activarlo, así que basta con depender de él aquí.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [capitulos, miembrosRef, respuestasCompuesto],
  );

  const progresoGlobal = progresoData.progreso;
  const capsCompletados = progresoData.capsCompletados;

  function getCapProgress(capId: string): CapProgress {
    const pc = progresoData.porCapitulo[capId];
    if (!pc || pc.obligVisibles === 0) {
      return { estado: 'pendiente', respondidas: 0, obligatorias: 0 };
    }
    // Capar respondidas al máximo de obligatorias para que la barra y el chip
    // sean consistentes (mostrar 7/7, nunca 10/7).
    return {
      estado: pc.estado,
      respondidas: Math.min(pc.obligRespondidas, pc.obligVisibles),
      obligatorias: pc.obligVisibles,
    };
  }

  async function handleFinalizar() {
    // Ya cerrada en el teléfono: no hay nada que finalizar de nuevo, solo que
    // esperar a que la cola la suba.
    if (cerradaSinEnviar) { setModalFinalizar(false); return; }
    const bid = borradorId ?? borradorIdParam ?? null;
    // Online (con sesión de servidor) intentamos cerrar directo. Offline, o si el
    // borrador aún no tiene sesión en el servidor, encolamos FINALIZAR_SESION: la
    // sincronización inyecta el sesion_id tras CREAR_SESION y cierra la encuesta.
    if (!sesionServerId && !bid) return;
    setFinalizando(true);

    const observ = observaciones.trim() || undefined;
    const cerrarOk = (offline: boolean) => {
      setModalFinalizar(false);
      Alert.alert(
        offline ? 'Caracterización finalizada (offline)' : 'Sesión finalizada',
        offline
          ? 'La caracterización quedó cerrada en el dispositivo. Se enviará al servidor automáticamente cuando recuperes conexión.'
          : 'La sesión ha sido cerrada exitosamente.',
        [{ text: 'Aceptar', onPress: () => router.back() }],
      );
    };

    // Encola la finalización para que la cola la procese (offline o tras fallo online).
    const encolarFinalizar = async () => {
      if (!bid) return false;
      const borrador = await borradoresDao.getBorrador(bid);
      await colaDao.encolar('FINALIZAR_SESION', bid, {
        borrador_id: bid,
        sesion_id: sesionServerId ?? borrador?.sesion_id ?? null,
        observaciones: observ,
      });
      // CERRADO_LOCAL, no COMPLETADO: acá todavía no salió nada del teléfono.
      // Marcarlo como completado lo sacaba de `listarBorradores` y de
      // `findBorradorOfflinePorHogarInstrumento`, o sea que la encuestadora
      // finalizaba en modo avión y su entrevista desaparecía de la lista.
      await borradoresDao.marcarCerradoLocal(bid);
      await refrescarContadores();
      return true;
    };

    try {
      if (sesionServerId && estaOnline) {
        try {
          await encuestasApi.finalizar(sesionServerId, { observaciones: observ });
          if (bid) { try { await borradoresDao.marcarCompletado(bid); } catch { /* no-op */ } }
          cerrarOk(false);
          return;
        } catch (err: any) {
          // Error real del servidor (4xx) → informar. Error de red → caer a la cola.
          if (err?.response) {
            Alert.alert('Error', err.response.data?.detail ?? 'No se pudo finalizar la sesión.');
            return;
          }
        }
      }
      // Offline (o red caída en el intento online): encolar.
      const encolado = await encolarFinalizar();
      if (encolado) cerrarOk(true);
      else Alert.alert('Error', 'No se pudo finalizar la caracterización.');
    } catch (err: any) {
      Alert.alert('Error', err?.response?.data?.detail ?? 'No se pudo finalizar la sesión.');
    } finally {
      setFinalizando(false);
    }
  }

  // Sprint 21 — Cerrar con nota de anulación, con doble confirmación.
  // #17 — Honestidad: el backend NO tiene aún un estado "ANULADA"; esta acción
  // CIERRA la entrevista como COMPLETADA con una observación de anulación, así
  // que SÍ queda registrada. El texto lo deja claro para no engañar al encuestador.
  function handleAnular() {
    if (!sesionServerId) return;
    Alert.alert(
      '¿Cerrar con anulación?',
      'No se podrá continuar ni recuperar las respuestas. La entrevista quedará CERRADA (completada) con una nota de anulación — seguirá registrada para auditoría. ¿Continuar?',
      [
        { text: 'No, cancelar', style: 'cancel' },
        {
          text: 'Sí, cerrar',
          style: 'destructive',
          onPress: () => {
            Alert.alert(
              'Última confirmación',
              'Última oportunidad para volver atrás. Si continúas, la entrevista se cerrará con la nota de anulación.',
              [
                { text: 'Volver', style: 'cancel' },
                {
                  text: 'Cerrar definitivamente',
                  style: 'destructive',
                  onPress: confirmarAnular,
                },
              ],
            );
          },
        },
      ],
    );
  }

  async function confirmarAnular() {
    if (!sesionServerId) return;
    setFinalizando(true);
    try {
      // El backend acepta PATCH con estado=SUSPENDIDA como "anulada" desde
      // el cliente. Si el endpoint de anular es distinto, ajustar acá.
      await encuestasApi.actualizar(sesionServerId, { /* el campo estado se ajusta vía PATCH si el backend lo expone */ } as any);
      // Hasta que haya un endpoint específico, usamos finalizar con observación de anulación
      await encuestasApi.finalizar(sesionServerId, {
        observaciones: '[ANULADA POR ENCUESTADOR] ' + (observaciones.trim() || 'Sin motivo registrado'),
      });
      Alert.alert(
        'Sesión anulada',
        'La sesión fue marcada como cerrada con observación de anulación.',
        [{ text: 'Aceptar', onPress: () => router.back() }],
      );
    } catch (err: any) {
      Alert.alert('Error', err?.response?.data?.detail ?? 'No se pudo anular la sesión.');
    } finally {
      setFinalizando(false);
    }
  }

  const subtitulo = hogarId
    ? `Hogar ${hogarId.slice(0, 8)}… · ${capitulos.length} capítulos`
    : `${capitulos.length} capítulos`;

  // Miga: muestra el contexto del flujo (Sesión › Capítulos), con Hogar si está disponible.
  // El back nativo de router.back() es correcto porque venimos de [sesionId].
  const sesionCorta = sesionServerId ? String(sesionServerId).slice(0, 8) : null;
  const hogarCorto  = hogarId ? String(hogarId).slice(0, 8) : null;
  const renderMiga = () => (
    <View style={styles.miga}>
      <Text style={styles.migaTxt}>
        {hogarCorto ? `Hogar ${hogarCorto}…  ›  ` : ''}
        {sesionCorta ? `Sesión ${sesionCorta}…  ›  ` : ''}
        Capítulos
      </Text>
    </View>
  );

  if (cargando) {
    return (
      <View style={styles.root}>
        <GovHeader title="Formulario" subtitle="Instrumento de caracterización" onBack={() => router.back()} />
        {renderMiga()}
        <View style={styles.centrado}>
          <ActivityIndicator size="large" color={GOV.azul} />
          <Text style={styles.cargandoTxt}>
            {descargando ? 'Descargando instrumento…' : 'Cargando instrumento…'}
          </Text>
        </View>
      </View>
    );
  }

  if (capitulos.length === 0) {
    return (
      <View style={styles.root}>
        <GovHeader title="Formulario" subtitle="Instrumento de caracterización" onBack={() => router.back()} />
        {renderMiga()}
        <EmptyState
          icon="clipboard-alert-outline"
          title="Sin instrumento"
          message={
            errorDescarga
              || 'No hay instrumento cargado en el dispositivo. Toca "Reintentar descarga" si tienes conexión.'
          }
          actionLabel="Reintentar descarga"
          onAction={cargarTodo}
        />
      </View>
    );
  }

  const mostrarSelectorModo = modoIA === null && !!sesionServerId;

  return (
    <View style={styles.root}>
      <GovHeader
        title={meta ? `${meta.perfil_codigo} ${meta.version}` : 'Formulario'}
        subtitle={subtitulo}
        onBack={() => router.back()}
      />

      {/* Miga de pan */}
      {renderMiga()}

      {/* ── Selector de modo ────────────────────────────────────────────────── */}
      {mostrarSelectorModo && (
        <View style={styles.selectorModo}>
          <Text style={styles.selectorTitulo}>Seleccione el modo de captura</Text>
          <View style={styles.selectorBotones}>
            <Pressable
              style={({ pressed }) => [styles.modoCard, pressed && styles.modoCardPressed]}
              onPress={() => setModoIA(false)}
              accessibilityRole="button"
            >
              <MaterialCommunityIcons name="pencil" size={28} color={GOV.azulOscuro} />
              <Text style={styles.modoCardTitulo}>Manual</Text>
              <Text style={styles.modoCardDesc}>Responda cada pregunta directamente.</Text>
            </Pressable>

            {iaActivo ? (
              <Pressable
                style={({ pressed }) => [styles.modoCard, styles.modoCardIA, pressed && styles.modoCardPressed]}
                onPress={() => setModoIA(true)}
                accessibilityRole="button"
              >
                <MaterialCommunityIcons name="robot" size={28} color={GOV.azul} />
                <Text style={[styles.modoCardTitulo, { color: GOV.azul }]}>Asistido por IA</Text>
                <Text style={styles.modoCardDesc}>Transcriba la entrevista.</Text>
              </Pressable>
            ) : (
              <Pressable
                style={[styles.modoCard, styles.modoCardIADesactivado]}
                onPress={() =>
                  router.push({
                    pathname: '/(main)/formulario/consentimiento-ia',
                    params: { sesionEncuestaId: sesionServerId ?? '' },
                  })
                }
                accessibilityRole="button"
              >
                <MaterialCommunityIcons name="robot-off" size={28} color={GOV.textoT} />
                <Text style={[styles.modoCardTitulo, { color: GOV.textoS }]}>Asistido por IA</Text>
                <Text style={styles.modoCardDesc}>Toque para activar el consentimiento IA.</Text>
              </Pressable>
            )}
          </View>
        </View>
      )}

      {/* ── Banner de modo activo ────────────────────────────────────────────── */}
      {modoIA !== null && (
        <View style={[styles.modoActivoBanner, modoIA ? styles.modoActivoIA : styles.modoActivoManual]}>
          <MaterialCommunityIcons
            name={modoIA ? 'robot' : 'pencil'}
            size={14}
            color={modoIA ? GOV.azul : GOV.textoS}
          />
          <Text style={[styles.modoActivoTxt, { color: modoIA ? GOV.azul : GOV.textoS }]}>
            Modo {modoIA ? 'asistido por IA' : 'manual'} activo
          </Text>
          <Pressable onPress={() => setModoIA(null)} style={styles.cambiarModo}>
            <Text style={styles.cambiarModoTxt}>Cambiar</Text>
          </Pressable>
        </View>
      )}

      {/* ── Progreso global ──────────────────────────────────────────────────── */}
      <View style={styles.progresoWrap}>
        <View style={styles.progresoRow}>
          <Text style={styles.progresoLabel}>
            {capsCompletados} de {capitulos.length} capítulos completados
          </Text>
          <Text style={[styles.progresoLabel, {
            fontWeight: '700',
            color: progresoGlobal === 1 ? GOV.verde : GOV.azul,
          }]}>
            {Math.round(progresoGlobal * 100)}%
          </Text>
        </View>
        <ProgressBar
          progress={progresoGlobal}
          style={styles.progressBar}
          color={progresoGlobal === 1 ? GOV.verde : GOV.azul}
        />
      </View>

      <FlatList
        data={capitulos}
        keyExtractor={(item) => item.id}
        renderItem={({ item, index }) => (
          <CapituloCard
            capitulo={item}
            index={index}
            progress={getCapProgress(item.id)}
            sesionServerId={sesionServerId}
            instrumentoId={instrumentoId}
            hogarId={hogarId}
            borradorId={borradorId ?? undefined}
            modoIA={modoIA === true}
          />
        )}
        contentContainerStyle={styles.lista}
        ListFooterComponent={
          // Finalizar disponible online (sesión de servidor) Y offline (borrador
          // local) — sin esto no se podía cerrar la caracterización sin red.
          (sesionServerId || borradorId) ? (
            <View style={styles.footerFinalizar}>
              {cerradaSinEnviar ? (
                // Cerrada acá, todavía sin subir. Se avisa en vez de ofrecer el
                // botón: puede revisar sus respuestas, pero volver a cerrarla
                // encolaría un segundo FINALIZAR que el servidor rechaza y que
                // envenena la cola de ese teléfono.
                <View style={styles.avisoCerrada}>
                  <MaterialCommunityIcons name="check-circle" size={18} color={GOV.verde} />
                  <Text style={styles.avisoCerradaTxt}>
                    Caracterización cerrada. Se enviará sola cuando haya conexión.
                  </Text>
                </View>
              ) : (
                <GovButton
                  label="Finalizar caracterización"
                  variant="secondary"
                  icon="check-circle-outline"
                  onPress={() => setModalFinalizar(true)}
                />
              )}
              {/* Anular requiere servidor (PATCH/finalizar online) → solo online. */}
              {sesionServerId ? (
                <>
                  <View style={{ height: 8 }} />
                  <Pressable
                    onPress={handleAnular}
                    disabled={finalizando}
                    style={({ pressed }) => [
                      styles.btnAnular,
                      pressed && { opacity: 0.85 },
                      finalizando && { opacity: 0.5 },
                    ]}
                  >
                    <MaterialCommunityIcons name="close-circle-outline" size={18} color={GOV.rojo} />
                    <Text style={styles.btnAnularTxt}>Anular entrevista</Text>
                  </Pressable>
                </>
              ) : null}
            </View>
          ) : null
        }
      />

      {/* Modal de finalización */}
      <Modal
        visible={modalFinalizar}
        transparent
        animationType="slide"
        onRequestClose={() => setModalFinalizar(false)}
      >
        <KeyboardAvoidingView
          style={styles.modalOverlay}
          behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        >
          <View style={styles.modalCard}>
            <Text style={styles.modalTitulo}>Finalizar sesión</Text>
            <Text style={styles.modalCuerpo}>
              Al finalizar, la sesión quedará en estado{' '}
              <Text style={styles.modalDestacado}>COMPLETADA</Text> y no podrá
              modificarse.{'\n\n'}
              Progreso actual: <Text style={styles.modalDestacado}>{Math.round(progresoGlobal * 100)}%</Text>
              {' '}({capsCompletados}/{capitulos.length} capítulos).
            </Text>

            <Text style={styles.modalLabel}>Observaciones (opcional)</Text>
            <TextInput
              value={observaciones}
              onChangeText={setObservaciones}
              placeholder="Notas adicionales sobre la entrevista…"
              multiline
              numberOfLines={3}
              style={styles.modalTextArea}
              editable={!finalizando}
            />

            <View style={styles.modalBotones}>
              <GovButton
                label="Cancelar"
                variant="secondary"
                fullWidth={false}
                onPress={() => setModalFinalizar(false)}
                disabled={finalizando}
              />
              <GovButton
                label="Finalizar"
                variant="primary"
                icon="check"
                fullWidth={false}
                onPress={handleFinalizar}
                loading={finalizando}
                disabled={finalizando}
              />
            </View>
          </View>
        </KeyboardAvoidingView>
      </Modal>
    </View>
  );
}

// ─── Estilos ──────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: GOV.fondoApp },
  miga: {
    backgroundColor: GOV.azulTenue,
    paddingHorizontal: SPACING.md,
    paddingVertical: 6,
    borderBottomWidth: 1,
    borderBottomColor: GOV.borde,
  },
  migaTxt: { ...FONT.caption, color: GOV.azulOscuro },
  centrado: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: SPACING.xl },
  cargandoTxt: { ...FONT.small, color: GOV.textoS, marginTop: SPACING.sm },

  selectorModo: {
    backgroundColor: GOV.superficie,
    padding: SPACING.md,
    borderBottomWidth: 1,
    borderBottomColor: GOV.borde,
  },
  selectorTitulo: { ...FONT.h3, color: GOV.azulOscuro, marginBottom: SPACING.sm },
  selectorBotones: { flexDirection: 'row', gap: SPACING.sm },
  modoCard: {
    flex: 1,
    backgroundColor: GOV.fondoApp,
    borderRadius: RADIUS.md,
    padding: SPACING.md,
    alignItems: 'center',
    borderWidth: 1.5,
    borderColor: GOV.borde,
    gap: SPACING.xs,
    ...SHADOW.card,
  },
  modoCardIA:           { borderColor: GOV.azul + '66', backgroundColor: GOV.azulTenue },
  modoCardIADesactivado:{ opacity: 0.6 },
  modoCardPressed:      { opacity: 0.85, transform: [{ scale: 0.98 }] },
  modoCardTitulo:       { ...FONT.h3, color: GOV.azulOscuro, textAlign: 'center' },
  modoCardDesc:         { ...FONT.caption, color: GOV.textoS, textAlign: 'center' },

  modoActivoBanner:  { flexDirection: 'row', alignItems: 'center', paddingHorizontal: SPACING.md, paddingVertical: 6, gap: SPACING.xs },
  modoActivoIA:      { backgroundColor: GOV.azulTenue },
  modoActivoManual:  { backgroundColor: GOV.fondoApp, borderBottomWidth: 1, borderBottomColor: GOV.borde },
  modoActivoTxt:     { ...FONT.caption, flex: 1 },
  cambiarModo:       { paddingHorizontal: SPACING.sm },
  cambiarModoTxt:    { ...FONT.caption, color: GOV.azul, fontWeight: '600' },

  progresoWrap: {
    backgroundColor: GOV.superficie,
    paddingHorizontal: SPACING.md,
    paddingVertical: SPACING.sm,
    borderBottomWidth: 1,
    borderBottomColor: GOV.borde,
  },
  progresoRow:   { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 6 },
  progresoLabel: { ...FONT.caption, color: GOV.textoS },
  progressBar:   { height: 6, borderRadius: 3, backgroundColor: GOV.borde },

  lista: { padding: SPACING.md, paddingBottom: SPACING.sm },
  footerFinalizar: { paddingVertical: SPACING.md, paddingBottom: SPACING.xl },
  avisoCerrada: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.sm,
    backgroundColor: GOV.verdeTenue,
    borderRadius: RADIUS.sm,
    paddingHorizontal: SPACING.md,
    paddingVertical: SPACING.sm,
  },
  avisoCerradaTxt: { ...FONT.caption, color: GOV.verde, flex: 1 },
  btnAnular: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    paddingVertical: 10,
    borderRadius: RADIUS.md,
    borderWidth: 1,
    borderColor: GOV.rojo + '66',
    backgroundColor: 'transparent',
  },
  btnAnularTxt: { ...FONT.body, color: GOV.rojo, fontWeight: '600' },

  card: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: GOV.superficie,
    borderRadius: RADIUS.md,
    padding: SPACING.md,
    marginBottom: SPACING.sm,
    ...SHADOW.card,
    borderLeftWidth: 4,
    borderLeftColor: GOV.borde,
  },
  cardCompletado: {
    borderLeftColor: GOV.verde,
    backgroundColor: GOV.verdeTenue,
    borderLeftWidth: 6,
  },
  cardEnProgreso: {
    borderLeftColor: GOV.naranja,
    borderLeftWidth: 6,
  },
  cardPressed:    { opacity: 0.9, transform: [{ scale: 0.99 }] },

  // Encabezado: nombre + chip de estado en la misma fila
  cardEncabezado: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: SPACING.sm,
    marginBottom: 2,
  },

  numCircle: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: GOV.azulTenue,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: SPACING.md,
    borderWidth: 1.5,
    borderColor: GOV.borde,
  },
  numCircleCompleto: {
    backgroundColor: GOV.verde,
    borderColor: GOV.verde,
  },
  numCircleEnProgreso: {
    backgroundColor: GOV.naranjaTenue,
    borderColor: GOV.naranja,
  },
  numTxt: { fontSize: 13, fontWeight: '800', color: GOV.azul },

  cardTexto: { flex: 1 },
  capNombre:   { ...FONT.body, fontWeight: '600', color: GOV.textoP, flex: 1 },
  capNombreOk: { color: GOV.verde },
  capCodigo:   { ...FONT.caption, color: GOV.textoT, fontFamily: 'monospace', marginBottom: 4 },

  // Chip de estado: Completo / Faltan N / Sin iniciar
  chipEstado: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 3,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: RADIUS.pill,
    borderWidth: 1,
  },
  chipEstadoOk:        { backgroundColor: GOV.verdeTenue, borderColor: GOV.verde },
  chipEstadoProgreso:  { backgroundColor: GOV.naranjaTenue, borderColor: GOV.naranja },
  chipEstadoPendiente: { backgroundColor: GOV.fondoApp, borderColor: GOV.borde },
  chipEstadoTxt:       { fontSize: 10, fontWeight: '700' },

  capProgresoWrap: { flexDirection: 'row', alignItems: 'center', gap: SPACING.xs, marginTop: 4 },
  capProgressBar:  { flex: 1, height: 4, borderRadius: 2 },
  capProgresoPct:  { fontSize: 10, fontWeight: '700', minWidth: 40, textAlign: 'right' },

  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.45)', justifyContent: 'flex-end' },
  modalCard: {
    backgroundColor: GOV.superficie,
    borderTopLeftRadius: RADIUS.lg,
    borderTopRightRadius: RADIUS.lg,
    padding: SPACING.lg,
    paddingBottom: SPACING.xl,
    gap: SPACING.sm,
  },
  modalTitulo:    { ...FONT.h2, color: GOV.azulOscuro },
  modalCuerpo:    { ...FONT.body, color: GOV.textoS, lineHeight: 22 },
  modalDestacado: { fontWeight: '700', color: GOV.azulOscuro },
  modalLabel:     { ...FONT.label, color: GOV.textoT, marginTop: SPACING.xs },
  modalTextArea:  { backgroundColor: GOV.fondoApp, minHeight: 80, textAlignVertical: 'top', fontSize: 14 },
  modalBotones:   { flexDirection: 'row', justifyContent: 'flex-end', gap: SPACING.sm, marginTop: SPACING.sm },
});
