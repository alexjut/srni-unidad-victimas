// Motor de captura offline de un capítulo — Sprint 8: carga previa, validación, bulk sync, progreso.
import { useEffect, useState, useMemo, useCallback, useRef } from 'react';
import { View, FlatList, StyleSheet, Alert, Pressable } from 'react-native';
import {
  Text, TextInput, RadioButton, Checkbox,
  ActivityIndicator, Chip, IconButton, ProgressBar,
} from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useLocalSearchParams, router } from 'expo-router';
import * as instrumentos from '../../../src/services/instrumentos';
import * as borradoresDao from '../../../src/db/borradoresDao';
import * as colaDao from '../../../src/db/colaDao';
import { calcularVisibles } from '../../../src/services/skipLogic';
import { useSyncStore } from '../../../src/stores/syncStore';
import { useIAStore } from '../../../src/stores/iaStore';
import { useCaracterizacionStore } from '../../../src/stores/caracterizacionStore';
import { encuestasApi } from '../../../src/api/encuestas';
import { hogaresApi } from '../../../src/api/hogares';
import { AudioRecorder } from '../../../src/components/AudioRecorder';
import { SugerenciaIA } from '../../../src/components/SugerenciaIA';
import { GovHeader } from '../../../src/components/GovHeader';
import { GovButton } from '../../../src/components/GovButton';
import { SelectorMunicipio } from '../../../src/components/SelectorMunicipio';
import { SelectorFecha } from '../../../src/components/SelectorFecha';
import { GOV, SPACING, RADIUS, SHADOW, FONT } from '../../../src/theme/govTheme';
import type { PreguntaRow, OpcionRow, ReglaSkipLogicRow } from '../../../src/db/instrumentoDao';
import type { MiembroHogarResumen } from '../../../src/types';

// Sprint 21 — clave compuesta para indexar respuestas por (pregunta, miembro).
// Miembro vacío = pregunta nivel HOGAR (única para toda la sesión).
function claveResp(preguntaId: string, miembroId: string | null | undefined): string {
  return `${preguntaId}|${miembroId ?? ''}`;
}

interface ItemLista {
  type: 'header-hogar' | 'header-miembro' | 'pregunta';
  /** preguntas tipo 'pregunta' */
  pregunta?: PreguntaRow;
  /** índice global dentro del cap (para numeración) */
  indexGlobal?: number;
  /** total visible global */
  totalGlobal?: number;
  /** miembro al que aplica la pregunta (null = HOGAR) */
  miembro?: MiembroHogarResumen | null;
  /** llave única para FlatList */
  key: string;
}

// ─────────────────────────────────────────────────────────────────────────────

export default function CapituloScreen() {
  const {
    temaId,
    borradorId: borradorIdParam,
    hogarId,
    sesionServerId,
    instrumentoId,
  } = useLocalSearchParams<{
    temaId: string;
    borradorId?: string;
    hogarId?: string;
    sesionServerId?: string;
    instrumentoId?: string;
  }>();

  const { estaOnline, refrescarContadores } = useSyncStore();
  const rutaEntrevista = useCaracterizacionStore((s) => s.rutaEntrevista);
  const {
    activo: iaActivo,
    estado: estadoIA,
    sugerencia,
    preguntaActivaId,
    iniciarGrabacion,
    enviarTexto,
    aceptarSugerencia,
    rechazarSugerencia,
    resetear: resetearIA,
  } = useIAStore();

  const [preguntas, setPreguntas] = useState<PreguntaRow[]>([]);
  const [opciones, setOpciones] = useState<Record<string, OpcionRow[]>>({});
  const [reglas, setReglas] = useState<ReglaSkipLogicRow[]>([]);
  // Sprint 21 — respuestas indexadas por clave compuesta `preguntaId|miembroId`.
  // Para HOGAR la clave es `preguntaId|` (miembro vacío).
  const [respuestas, setRespuestasState] = useState<Record<string, string>>({});
  const [borradorId, setBorradorId] = useState<string | null>(borradorIdParam ?? null);
  const [capituloNombre, setCapituloNombre] = useState('');
  const [cargando, setCargando] = useState(true);
  const [sincronizando, setSincronizando] = useState(false);
  // Sprint 21 — miembros del hogar para instanciar preguntas PERSONA.
  // Si no hay hogar resuelto o se está offline sin caché, queda en [] y el
  // motor cae a comportamiento HOGAR-only (degradación segura).
  const [miembros, setMiembros] = useState<MiembroHogarResumen[]>([]);
  // Sprint 21 Fase F — wizard por miembro. 0 = primer miembro activo.
  // Solo se renderiza el miembro en este índice (no todos en scroll).
  const [miembroIdx, setMiembroIdx] = useState(0);
  const flatRef = useRef<FlatList | null>(null);

  // Sprint 21 Fase F — al cambiar miembro, scroll al inicio para que el
  // encuestador vea desde la primera pregunta del nuevo miembro.
  useEffect(() => {
    flatRef.current?.scrollToOffset?.({ offset: 0, animated: true });
  }, [miembroIdx]);

  // ── Cargar datos del capítulo + borradores previos ──────────────────────────
  useEffect(() => {
    if (!temaId) return;

    (async () => {
      // Sprint 18 F1B: TODO viene de memoria (bundle), no SQLite.
      const caps = instrumentos.getCapitulos();
      const cap = caps.find((c) => c.id === temaId);
      setCapituloNombre(cap?.nombre ?? '');

      const pgs = instrumentos.getPreguntas(temaId);
      setPreguntas(pgs);
      if (pgs.length > 0) {
        setOpciones(instrumentos.getOpcionesBatch(pgs.map((p) => p.id)));
      }

      setReglas(instrumentos.getReglasPorCapitulo(temaId));

      // ── Resolver borrador ─────────────────────────────────────────────────
      const meta = instrumentos.getMeta();
      const instrId = instrumentoId ?? meta?.instrumento_id ?? '';

      if (borradorIdParam) {
        // Ya tenemos un borrador local — cargar sus respuestas (clave compuesta)
        setRespuestasState(await borradoresDao.getRespuestaMapCompuesto(borradorIdParam));
        setBorradorId(borradorIdParam);

      } else if (sesionServerId) {
        // Buscar si ya existe un borrador vinculado a esta sesión
        const existente = await borradoresDao.findBySesionId(sesionServerId);

        if (existente) {
          setBorradorId(existente.id);
          setRespuestasState(await borradoresDao.getRespuestaMapCompuesto(existente.id));
        } else {
          // Crear nuevo borrador y vincularlo
          const nuevo = await borradoresDao.crearBorrador(instrId, hogarId);
          await borradoresDao.vincularSesionServidor(nuevo.id, sesionServerId);
          setBorradorId(nuevo.id);

          // Si hay conexión, descargar respuestas previas del servidor
          if (estaOnline) {
            try {
              const { data: previas } = await encuestasApi.getRespuestas(sesionServerId);
              for (const r of previas) {
                if (r.valor) {
                  // Sprint 21: r.miembro puede venir del backend; usar para indexar
                  const mid = (r as any).miembro ?? null;
                  await borradoresDao.upsertRespuesta(nuevo.id, r.pregunta, r.valor, mid);
                }
              }
              setRespuestasState(await borradoresDao.getRespuestaMapCompuesto(nuevo.id));
            } catch { /* sin red — empieza en blanco */ }
          }
        }

      } else {
        // Sesión sin id de servidor — borrador completamente nuevo
        const nuevo = await borradoresDao.crearBorrador(instrId, hogarId);
        setBorradorId(nuevo.id);
        if (hogarId && instrId) {
          await colaDao.encolar('CREAR_SESION', nuevo.id, {
            borrador_id: nuevo.id,
            hogar: hogarId,
            instrumento: instrId,
            ruta_entrevista: rutaEntrevista,
          });
          await refrescarContadores();
        }
      }

      setCargando(false);
    })().catch(() => setCargando(false));
  }, [temaId]);

  // ── Sprint 21 — cargar miembros del hogar ──────────────────────────────────
  useEffect(() => {
    if (!hogarId) return;
    let activo = true;
    hogaresApi.detalle(hogarId)
      .then(({ data }) => {
        if (!activo) return;
        // Ordenar: autorizado primero, después por parentesco/orden natural.
        const ordenados = [...(data.miembros ?? [])].sort((a, b) => {
          if (a.es_autorizado && !b.es_autorizado) return -1;
          if (!a.es_autorizado && b.es_autorizado) return 1;
          return 0;
        });
        setMiembros(ordenados);
      })
      .catch(() => {
        // Offline o sin permisos — degradación: queda en [] y solo HOGAR funciona.
      });
    return () => { activo = false; };
  }, [hogarId]);

  // ── Skip logic ──────────────────────────────────────────────────────────────
  // Sprint 21: la skip logic evalúa a nivel de pregunta (no por miembro).
  // Para HOGAR usamos su única respuesta. Para PERSONA usamos la primera
  // respuesta no vacía como representante — suficiente para reglas globales
  // del tipo "si el hogar tiene X, mostrar Y". Reglas por miembro quedarían
  // para iteración futura.
  const respuestasParaSkip = useMemo<Record<string, string>>(() => {
    const m: Record<string, string> = {};
    for (const p of preguntas) {
      const claveHogar = claveResp(p.id, null);
      if (respuestas[claveHogar]) {
        m[p.codigo_externo] = respuestas[claveHogar];
        continue;
      }
      // PERSONA: buscar primera respuesta no vacía entre miembros
      for (const miembro of miembros) {
        const val = respuestas[claveResp(p.id, miembro.id)];
        if (val) { m[p.codigo_externo] = val; break; }
      }
      if (!m[p.codigo_externo]) m[p.codigo_externo] = '';
    }
    return m;
  }, [preguntas, respuestas, miembros]);

  const { visibles } = useMemo(
    () => calcularVisibles(preguntas, reglas, respuestasParaSkip),
    [preguntas, reglas, respuestasParaSkip],
  );

  const preguntasVisibles = useMemo(
    () => preguntas.filter((p) => visibles.has(p.codigo_externo)),
    [preguntas, visibles],
  );

  // Sprint 21 — separar visibles por nivel
  const visiblesHogar = useMemo(
    () => preguntasVisibles.filter((p) => p.nivel === 'HOGAR'),
    [preguntasVisibles],
  );
  const visiblesPersona = useMemo(
    () => preguntasVisibles.filter((p) => p.nivel === 'PERSONA'),
    [preguntasVisibles],
  );

  // Sprint 21 Fase F — wizard por miembro.
  // La FlatList renderea:
  //   - todas las preguntas HOGAR (siempre arriba)
  //   - SOLO el miembro activo (miembroIdx), no todos
  // El usuario navega con botones 'Anterior/Siguiente miembro'.
  const miembroActivo = miembros[miembroIdx] ?? null;
  const items = useMemo<ItemLista[]>(() => {
    const out: ItemLista[] = [];
    let idx = 0;
    const totalGlobal =
      visiblesHogar.length + visiblesPersona.length * Math.max(miembros.length, 0);

    if (visiblesHogar.length > 0) {
      out.push({ type: 'header-hogar', key: 'hdr-hogar' });
      for (const p of visiblesHogar) {
        out.push({
          type: 'pregunta', pregunta: p, miembro: null,
          indexGlobal: idx++, totalGlobal,
          key: `q-${p.id}-`,
        });
      }
    }

    if (visiblesPersona.length > 0) {
      if (miembros.length === 0) {
        out.push({ type: 'header-miembro', miembro: null, key: 'hdr-sin-miembros' });
      } else if (miembroActivo) {
        // Solo el miembro activo: header + sus preguntas PERSONA
        out.push({ type: 'header-miembro', miembro: miembroActivo, key: `hdr-${miembroActivo.id}` });
        for (const p of visiblesPersona) {
          out.push({
            type: 'pregunta', pregunta: p, miembro: miembroActivo,
            indexGlobal: idx++, totalGlobal,
            key: `q-${p.id}-${miembroActivo.id}`,
          });
        }
      }
    }
    return out;
  }, [visiblesHogar, visiblesPersona, miembros, miembroActivo]);

  // Sprint 21 Fase F — completitud del miembro activo (para habilitar avance).
  const obligPersonaActivo = useMemo(() => {
    if (!miembroActivo) return { total: 0, faltan: 0 };
    const oblig = visiblesPersona.filter((p) => p.obligatoria === 1);
    let faltan = 0;
    for (const p of oblig) {
      if (!respuestas[claveResp(p.id, miembroActivo.id)]?.trim()) faltan++;
    }
    return { total: oblig.length, faltan };
  }, [visiblesPersona, respuestas, miembroActivo]);

  // ── Progreso del capítulo ───────────────────────────────────────────────────
  const { totalOblig, respondidoOblig } = useMemo(() => {
    const obligHogar = visiblesHogar.filter((p) => p.obligatoria === 1);
    const obligPersona = visiblesPersona.filter((p) => p.obligatoria === 1);
    const totalOblig = obligHogar.length + obligPersona.length * miembros.length;

    let respondidoOblig = 0;
    for (const p of obligHogar) {
      if (respuestas[claveResp(p.id, null)]?.trim()) respondidoOblig++;
    }
    for (const p of obligPersona) {
      for (const m of miembros) {
        if (respuestas[claveResp(p.id, m.id)]?.trim()) respondidoOblig++;
      }
    }
    return { totalOblig, respondidoOblig };
  }, [visiblesHogar, visiblesPersona, miembros, respuestas]);

  const progresoCap = totalOblig > 0 ? respondidoOblig / totalOblig : 0;

  // ── Guardar respuesta en SQLite + encolar ───────────────────────────────────
  // Sprint 21: miembroId es opcional. null/undefined para preguntas HOGAR.
  const setRespuesta = useCallback(async (
    preguntaId: string,
    valor: string,
    miembroId: string | null = null,
  ) => {
    const clave = claveResp(preguntaId, miembroId);
    setRespuestasState((prev) => ({ ...prev, [clave]: valor }));

    const bid = borradorId ?? borradorIdParam;
    if (!bid) return;

    borradoresDao.upsertRespuesta(bid, preguntaId, valor, miembroId).catch(() => {});

    const borrador = await borradoresDao.getBorrador(bid);
    if (borrador) {
      await colaDao.encolar('RESPONDER_PREGUNTA', bid, {
        borrador_id: bid,
        sesion_id: borrador.sesion_id ?? null,
        pregunta_id: preguntaId,
        miembro_id: miembroId,
        valor,
      });
      await refrescarContadores();
    }
  }, [borradorId, borradorIdParam]);

  // ── Asistente IA ────────────────────────────────────────────────────────────
  const handleTextoTranscrito = useCallback(async (preguntaId: string, texto: string) => {
    const bid = borradorId ?? borradorIdParam;
    if (!bid) return;
    iniciarGrabacion(preguntaId);
    const borrador = await borradoresDao.getBorrador(bid);
    await enviarTexto(borrador?.sesion_id ?? '', preguntaId, texto);
  }, [borradorId, borradorIdParam, iniciarGrabacion, enviarTexto]);

  const handleAceptarSugerencia = useCallback((preguntaId: string) => {
    const resultado = aceptarSugerencia();
    if (resultado?.sugerencia) setRespuesta(preguntaId, resultado.sugerencia);
  }, [aceptarSugerencia, setRespuesta]);

  useEffect(() => { return () => { resetearIA(); }; }, []);

  // ── Guardar capítulo: bulk sync (online) o encolar (offline) → volver ─────────
  async function guardarYVolver() {
    const bid = borradorId ?? borradorIdParam;

    if (bid && sesionServerId) {
      setSincronizando(true);
      try {
        // Sprint 21 — leer TODAS las respuestas (HOGAR + PERSONA × N miembros)
        // y mandarlas con su miembro_id correspondiente.
        const rows = await borradoresDao.getRespuestas(bid);
        const arr = rows
          .filter((r) => r.valor.trim() !== '')
          .map((r) => ({
            pregunta_id: r.pregunta_id,
            miembro_id: r.miembro_id,  // null para HOGAR
            valor: r.valor,
          }));

        if (arr.length > 0) {
          if (estaOnline) {
            await encuestasApi.responderBulk(sesionServerId, arr);
          } else {
            // Sin red: encolar para sincronizar cuando vuelva la conexión
            await colaDao.encolar('RESPONDER_BULK', bid, {
              sesion_id: sesionServerId,
              borrador_id: bid,
              respuestas: arr,
            });
          }
        }
      } catch { /* silencioso — la cola lo reintentará */ }
      finally { setSincronizando(false); }
    }

    await refrescarContadores();
    volverAListaCapitulos();
  }

  // Sprint 21 fix — navegación explícita a la lista de capítulos.
  // Antes usábamos router.back() que con los router.replace() del flujo
  // cosido (ubicacion-atencion → hub) podía caer al home en lugar de la
  // lista de capítulos. Ahora pasamos pathname + params explícitos.
  function volverAListaCapitulos() {
    if (sesionServerId) {
      router.replace({
        pathname: '/(main)/formulario',
        params: {
          sesionServerId,
          ...(instrumentoId ? { instrumentoId } : {}),
          ...(hogarId ? { hogarId } : {}),
        },
      });
    } else {
      // Fallback: si no tenemos sesionServerId, volver al hub del hogar
      if (hogarId) {
        router.replace({
          pathname: '/(main)/hogares/[hogarId]/caracterizaciones',
          params: { hogarId },
        });
      } else {
        router.back();
      }
    }
  }

  async function finalizarCapitulo() {
    // Sprint 21 — preguntas obligatorias sin respuesta, considerando HOGAR
    // (1 por pregunta) y PERSONA (1 por pregunta × miembro).
    let faltantes = 0;
    for (const p of visiblesHogar) {
      if (p.obligatoria !== 1) continue;
      if (!respuestas[claveResp(p.id, null)]?.trim()) faltantes++;
    }
    for (const p of visiblesPersona) {
      if (p.obligatoria !== 1) continue;
      for (const m of miembros) {
        if (!respuestas[claveResp(p.id, m.id)]?.trim()) faltantes++;
      }
    }

    if (faltantes > 0) {
      Alert.alert(
        'Preguntas requeridas',
        `Hay ${faltantes} pregunta${faltantes > 1 ? 's' : ''} obligatoria${faltantes > 1 ? 's' : ''} sin responder (contando todos los miembros del hogar).\n\n¿Desea guardar de todas formas?`,
        [
          { text: 'Revisar', style: 'cancel' },
          { text: 'Guardar igual', onPress: guardarYVolver },
        ],
      );
      return;
    }
    await guardarYVolver();
  }

  // ── Render ──────────────────────────────────────────────────────────────────
  if (cargando) {
    return (
      <View style={styles.root}>
        <GovHeader title="Cargando…" onBack={() => router.back()} />
        <View style={styles.centrado}>
          <ActivityIndicator size="large" color={GOV.azul} />
        </View>
      </View>
    );
  }

  // Sprint 21 — total visible incluye HOGAR (1×) + PERSONA (N miembros)
  const totalVisible = visiblesHogar.length + visiblesPersona.length * Math.max(miembros.length, 1);
  const migaContexto = hogarId
    ? `Hogar ${hogarId.slice(0, 8)}…  ›  ${capituloNombre || 'Capítulo'}`
    : capituloNombre || 'Capítulo';

  return (
    <View style={styles.root}>
      <GovHeader
        title={capituloNombre || 'Capítulo'}
        subtitle={`${totalVisible} pregunta${totalVisible !== 1 ? 's' : ''}`}
        onBack={volverAListaCapitulos}
        right={
          <View style={styles.headerActions}>
            {!estaOnline && (
              <Chip compact icon="wifi-off" style={styles.offlineChip} textStyle={styles.offlineTxt}>
                Offline
              </Chip>
            )}
            {iaActivo ? (
              <Chip
                compact
                icon="microphone"
                style={styles.iaActivoChip}
                textStyle={styles.iaActivoTxt}
                onClose={() => useIAStore.getState().desactivar()}
              >
                IA
              </Chip>
            ) : (
              <IconButton
                icon="robot"
                size={20}
                iconColor="#FFFFFF"
                onPress={() => router.push({
                  pathname: '/(main)/formulario/consentimiento-ia',
                  params: { sesionEncuestaId: borradorId ?? borradorIdParam ?? '' },
                })}
              />
            )}
          </View>
        }
      />

      {/* Miga de pan */}
      <View style={styles.miga}>
        <Text style={styles.migaTxt}>Formulario  ›  {migaContexto}</Text>
      </View>

      {/* Barra de progreso del capítulo */}
      <View style={styles.progresoWrap}>
        <View style={styles.progresoRow}>
          <Text style={styles.progresoLabel}>
            {respondidoOblig} / {totalOblig} obligatoria{totalOblig !== 1 ? 's' : ''} respondida{totalOblig !== 1 ? 's' : ''}
          </Text>
          <Text style={[styles.progresoLabel, { color: progresoCap === 1 ? GOV.verde : GOV.azul, fontWeight: '700' }]}>
            {Math.round(progresoCap * 100)}%
          </Text>
        </View>
        <ProgressBar
          progress={progresoCap}
          style={styles.progressBar}
          color={progresoCap === 1 ? GOV.verde : GOV.azul}
        />
      </View>

      <FlatList
        ref={flatRef}
        data={items}
        keyExtractor={(it) => it.key}
        renderItem={({ item }) => {
          if (item.type === 'header-hogar') {
            return (
              <View style={styles.seccionHeader}>
                <MaterialCommunityIcons name="home-variant" size={18} color={GOV.azul} />
                <Text style={styles.seccionTitulo}>Datos del hogar</Text>
              </View>
            );
          }
          if (item.type === 'header-miembro') {
            if (!item.miembro) {
              return (
                <View style={styles.seccionHeaderWarning}>
                  <MaterialCommunityIcons name="alert-circle-outline" size={18} color={GOV.naranja} />
                  <Text style={styles.seccionTituloWarning}>
                    Este capítulo tiene preguntas por persona, pero no se pudieron cargar los miembros del hogar.
                  </Text>
                </View>
              );
            }
            const m = item.miembro;
            // Sprint 21 — header con nombre: "Autorizado · Juan Pérez" o
            // "Miembro · María García". Si nombre_completo vino vacío,
            // mostramos solo el rol (fallback seguro).
            const rolPrefijo = m.es_autorizado ? 'Autorizado' : 'Miembro';
            const nombre = (m.nombre_completo ?? '').trim();
            const titulo = nombre
              ? `${rolPrefijo} · ${nombre}`
              : `${rolPrefijo} · ${m.rol_display || 'sin nombre'}`;
            return (
              <View style={styles.seccionHeader}>
                <MaterialCommunityIcons
                  name={m.es_autorizado ? 'account-star' : 'account'}
                  size={18}
                  color={GOV.azul}
                />
                <Text style={styles.seccionTitulo}>{titulo}</Text>
              </View>
            );
          }
          // type === 'pregunta'
          const p = item.pregunta!;
          const miembroId = item.miembro?.id ?? null;
          const clave = claveResp(p.id, miembroId);
          const valor = respuestas[clave] ?? '';
          // IA: solo se asocia con HOGAR por ahora (clave preguntaId solo)
          const iaPreguntaKey = miembroId ? null : p.id;
          return (
            <PreguntaItem
              pregunta={p}
              index={item.indexGlobal ?? 0}
              total={item.totalGlobal ?? 0}
              opciones={opciones[p.id] ?? []}
              valor={valor}
              onChange={(v) => setRespuesta(p.id, v, miembroId)}
              iaActivo={iaActivo && !miembroId}
              onTextoIA={iaPreguntaKey ? (texto) => handleTextoTranscrito(p.id, texto) : undefined}
              sugerenciaActiva={
                iaPreguntaKey && sugerencia && preguntaActivaId === p.id && estadoIA === 'sugerida'
                  ? sugerencia
                  : null
              }
              onAceptarIA={iaPreguntaKey ? () => handleAceptarSugerencia(p.id) : undefined}
              onRechazarIA={rechazarSugerencia}
            />
          );
        }}
        contentContainerStyle={styles.lista}
        ListEmptyComponent={
          <Text style={styles.sinPreguntas}>No hay preguntas en este capítulo.</Text>
        }
        ListFooterComponent={
          // Sprint 21 Fase F — navegador wizard entre miembros.
          // Solo aparece si el capítulo tiene preguntas PERSONA y hay >1 miembro.
          visiblesPersona.length > 0 && miembros.length > 0 ? (
            <View style={styles.navMiembros}>
              <View style={styles.navMiembrosCounter}>
                <MaterialCommunityIcons name="account-group" size={16} color={GOV.azulOscuro} />
                <Text style={styles.navMiembrosTxt}>
                  Persona {miembroIdx + 1} de {miembros.length}
                </Text>
                {obligPersonaActivo.total > 0 && (
                  <Text style={[
                    styles.navMiembrosFaltan,
                    obligPersonaActivo.faltan === 0 && { color: GOV.verde },
                  ]}>
                    {obligPersonaActivo.faltan === 0
                      ? '✓ completa'
                      : `${obligPersonaActivo.faltan} obligatoria${obligPersonaActivo.faltan > 1 ? 's' : ''} sin responder`}
                  </Text>
                )}
              </View>
              <View style={styles.navMiembrosBotones}>
                <Pressable
                  onPress={() => setMiembroIdx((i) => Math.max(0, i - 1))}
                  disabled={miembroIdx === 0}
                  style={({ pressed }) => [
                    styles.navBtn,
                    styles.navBtnSecundario,
                    miembroIdx === 0 && styles.navBtnDisabled,
                    pressed && miembroIdx > 0 && { opacity: 0.85 },
                  ]}
                >
                  <MaterialCommunityIcons name="chevron-left" size={20}
                    color={miembroIdx === 0 ? GOV.textoT : GOV.azulOscuro} />
                  <Text style={[
                    styles.navBtnTxt,
                    miembroIdx === 0 && { color: GOV.textoT },
                  ]}>Anterior</Text>
                </Pressable>

                {miembroIdx < miembros.length - 1 ? (
                  <Pressable
                    onPress={() => setMiembroIdx((i) => Math.min(miembros.length - 1, i + 1))}
                    style={({ pressed }) => [
                      styles.navBtn,
                      styles.navBtnPrimario,
                      pressed && { opacity: 0.88 },
                    ]}
                  >
                    <Text style={styles.navBtnTxtPrimario}>Siguiente miembro</Text>
                    <MaterialCommunityIcons name="chevron-right" size={20} color="#FFF" />
                  </Pressable>
                ) : (
                  <View style={[styles.navBtn, styles.navBtnUltimo]}>
                    <MaterialCommunityIcons name="check-circle-outline" size={18} color={GOV.verde} />
                    <Text style={styles.navBtnUltimoTxt}>Último miembro</Text>
                  </View>
                )}
              </View>
            </View>
          ) : null
        }
      />

      <View style={styles.footerBar}>
        <GovButton
          label={sincronizando ? 'Sincronizando…' : 'Guardar y volver'}
          icon={sincronizando ? undefined : 'check'}
          loading={sincronizando}
          disabled={sincronizando}
          onPress={finalizarCapitulo}
        />
      </View>
    </View>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Componente de pregunta individual
// ─────────────────────────────────────────────────────────────────────────────

// Sprint 17: alineado con el backend, que espera "true"/"false" como string.
// Pero al leer aceptamos también formatos viejos ('1'/'0') para retro-compat.
const BOOLEAN_OPCIONES = [
  { valor: 'true',  etiqueta: 'Sí' },
  { valor: 'false', etiqueta: 'No' },
];

function leerBooleanGuardado(valor: string): string {
  // Retro-compat: '1' → 'true', '0' → 'false'
  if (valor === '1' || valor === 'true')  return 'true';
  if (valor === '0' || valor === 'false') return 'false';
  return '';
}

/** Parsea LISTA_MULTIPLE: acepta JSON nuevo o CSV viejo. */
function parseMultiValor(valor: string): string[] {
  if (!valor) return [];
  const trimmed = valor.trim();
  if (trimmed.startsWith('[')) {
    try {
      const parsed = JSON.parse(trimmed);
      return Array.isArray(parsed) ? parsed.map(String) : [];
    } catch {
      return [];
    }
  }
  // CSV viejo (retro-compat)
  return trimmed.split(',').map(s => s.trim()).filter(Boolean);
}

function PreguntaItem({
  pregunta,
  index,
  total,
  opciones,
  valor,
  onChange,
  iaActivo,
  onTextoIA,
  sugerenciaActiva,
  onAceptarIA,
  onRechazarIA,
}: {
  pregunta: PreguntaRow;
  index: number;
  total: number;
  opciones: OpcionRow[];
  valor: string;
  onChange: (v: string) => void;
  iaActivo?: boolean;
  onTextoIA?: (texto: string) => void;
  sugerenciaActiva?: import('../../../src/api/ia').MapearAudioResponse | null;
  onAceptarIA?: () => void;
  onRechazarIA?: () => void;
}) {
  const esTexto    = pregunta.tipo === 'TEXTO' || pregunta.tipo === 'TEXTO_LARGO';
  const esNumerico = pregunta.tipo === 'NUMERICO';
  const esFecha    = pregunta.tipo === 'FECHA';
  // Sprint 20: COMBO_DINAMICO ya no se trata como LISTA — se renderiza con
  // SelectorMunicipio (consume /api/parametricas/municipios/todos/).
  const esRadio    = pregunta.tipo === 'RADIO' || pregunta.tipo === 'LISTA';
  const esCombo    = pregunta.tipo === 'COMBO_DINAMICO';
  const esMultiple = pregunta.tipo === 'LISTA_MULTIPLE';
  const esBoolean  = pregunta.tipo === 'BOOLEAN';

  const tieneRespuesta = !!valor?.trim();
  const esObligatoria  = pregunta.obligatoria === 1;

  return (
    <View style={[
      styles.preguntaCard,
      esObligatoria && !tieneRespuesta && styles.preguntaCardPendiente,
      tieneRespuesta && styles.preguntaCardRespondida,
    ]}>
      <View style={styles.preguntaHeader}>
        <View style={[styles.numBadge, tieneRespuesta && styles.numBadgeOk]}>
          {tieneRespuesta
            ? <MaterialCommunityIcons name="check" size={13} color="#FFFFFF" />
            : <Text style={styles.numBadgeTxt}>{index + 1}</Text>
          }
        </View>
        <Text style={styles.numTotal}>de {total}</Text>
        {esObligatoria && (
          <View style={[styles.requeridoChip, tieneRespuesta && styles.requeridoChipOk]}>
            <Text style={[styles.requeridoTxt, tieneRespuesta && styles.requeridoTxtOk]}>
              {tieneRespuesta ? 'Respondida' : 'Requerida'}
            </Text>
          </View>
        )}
        {pregunta.no_pregunta ? (
          <Text style={styles.codigoTxt}>{pregunta.no_pregunta}</Text>
        ) : null}
      </View>

      <Text style={styles.textoPregunta}>{pregunta.texto}</Text>

      {pregunta.descripcion_ayuda ? (
        <Text style={styles.ayuda}>{pregunta.descripcion_ayuda}</Text>
      ) : null}

      {/* Asistente de voz */}
      {iaActivo && onTextoIA && (
        <AudioRecorder
          preguntaId={pregunta.id}
          onTextoListo={onTextoIA}
          disabled={!!sugerenciaActiva}
        />
      )}
      {sugerenciaActiva && onAceptarIA && onRechazarIA && (
        <SugerenciaIA
          sugerencia={sugerenciaActiva}
          onAceptar={() => onAceptarIA()}
          onRechazar={onRechazarIA}
        />
      )}

      {/* Controles por tipo — Sprint 21 fix UX: estilo consistente GOV.CO */}
      {(esTexto || esNumerico) && (
        <TextInput
          mode="outlined"
          value={valor}
          onChangeText={onChange}
          keyboardType={esNumerico ? 'numeric' : 'default'}
          multiline={pregunta.tipo === 'TEXTO_LARGO'}
          numberOfLines={pregunta.tipo === 'TEXTO_LARGO' ? 4 : 1}
          placeholder={esNumerico ? 'Escribe el número' : 'Escribe la respuesta'}
          outlineColor={GOV.borde}
          activeOutlineColor={GOV.azul}
          style={styles.inputTexto}
        />
      )}

      {esFecha && (
        <SelectorFecha
          valor={valor}
          onChange={onChange}
          label={pregunta.no_pregunta ? `${pregunta.no_pregunta} · Fecha` : 'Fecha'}
          permitirFuturo={false}
        />
      )}

      {esBoolean && (
        <View style={styles.opcionesWrap}>
          {BOOLEAN_OPCIONES.map((o) => {
            const seleccionado = leerBooleanGuardado(valor) === o.valor;
            return (
              <Pressable
                key={o.valor}
                onPress={() => onChange(o.valor)}
                style={({ pressed }) => [
                  styles.opcionItem,
                  seleccionado && styles.opcionItemActiva,
                  pressed && { opacity: 0.85 },
                ]}
                accessibilityRole="radio"
                accessibilityState={{ selected: seleccionado }}
              >
                <View style={[styles.opcionRadio, seleccionado && styles.opcionRadioActivo]}>
                  {seleccionado && <View style={styles.opcionRadioInner} />}
                </View>
                <Text style={[styles.opcionTxt, seleccionado && styles.opcionTxtActivo]}>
                  {o.etiqueta}
                </Text>
              </Pressable>
            );
          })}
        </View>
      )}

      {esRadio && (
        opciones.length === 0 ? (
          <Text style={styles.sinOpciones}>
            ⚠ Esta pregunta no tiene opciones cargadas — contacte al administrador.
          </Text>
        ) : (
          <View style={styles.opcionesWrap}>
            {opciones.map((o) => {
              const seleccionado = valor === o.valor;
              return (
                <Pressable
                  key={o.id}
                  onPress={() => onChange(o.valor)}
                  style={({ pressed }) => [
                    styles.opcionItem,
                    seleccionado && styles.opcionItemActiva,
                    pressed && { opacity: 0.85 },
                  ]}
                  accessibilityRole="radio"
                  accessibilityState={{ selected: seleccionado }}
                >
                  <View style={[styles.opcionRadio, seleccionado && styles.opcionRadioActivo]}>
                    {seleccionado && <View style={styles.opcionRadioInner} />}
                  </View>
                  <Text style={[styles.opcionTxt, seleccionado && styles.opcionTxtActivo]}>
                    {o.etiqueta}
                  </Text>
                </Pressable>
              );
            })}
          </View>
        )
      )}

      {/* Sprint 20: COMBO_DINAMICO = municipio (Z2/Z5A/Z15/A23A/HV3/Lud_encuesta).
          Consume /api/parametricas/municipios/todos/ con caché en memoria. */}
      {esCombo && (
        <SelectorMunicipio
          valor={valor}
          onChange={onChange}
          label={pregunta.no_pregunta ? `${pregunta.no_pregunta} · Municipio` : 'Municipio'}
        />
      )}

      {esMultiple && (
        opciones.length === 0 ? (
          <Text style={styles.sinOpciones}>
            ⚠ Esta pregunta no tiene opciones cargadas — contacte al administrador.
          </Text>
        ) : (() => {
          const seleccionados = parseMultiValor(valor);
          return (
            <View>
              <Text style={styles.multiHint}>
                Selecciona todas las que apliquen
                {seleccionados.length > 0 && ` (${seleccionados.length} seleccionada${seleccionados.length !== 1 ? 's' : ''})`}
              </Text>
              <View style={styles.opcionesWrap}>
                {opciones.map((o) => {
                  const marcado = seleccionados.includes(o.valor);
                  return (
                    <Pressable
                      key={o.id}
                      onPress={() => {
                        const sel = [...seleccionados];
                        const idx = sel.indexOf(o.valor);
                        if (idx >= 0) sel.splice(idx, 1);
                        else sel.push(o.valor);
                        onChange(sel.length > 0 ? JSON.stringify(sel) : '');
                      }}
                      style={({ pressed }) => [
                        styles.opcionItem,
                        marcado && styles.opcionItemActiva,
                        pressed && { opacity: 0.85 },
                      ]}
                      accessibilityRole="checkbox"
                      accessibilityState={{ checked: marcado }}
                    >
                      <View style={[styles.opcionCheck, marcado && styles.opcionCheckActivo]}>
                        {marcado && (
                          <MaterialCommunityIcons name="check" size={14} color="#FFFFFF" />
                        )}
                      </View>
                      <Text style={[styles.opcionTxt, marcado && styles.opcionTxtActivo]}>
                        {o.etiqueta}
                      </Text>
                    </Pressable>
                  );
                })}
              </View>
            </View>
          );
        })()
      )}
    </View>
  );
}

// ─── Estilos ──────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: GOV.fondoApp },
  centrado: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  headerActions: { flexDirection: 'row', alignItems: 'center', gap: 2 },
  offlineChip: { backgroundColor: GOV.naranjaTenue },
  offlineTxt:  { color: GOV.naranja, fontSize: 10 },
  iaActivoChip: { backgroundColor: GOV.azulTenue },
  iaActivoTxt:  { color: GOV.azul, fontSize: 10 },
  miga: {
    backgroundColor: GOV.azulTenue,
    paddingHorizontal: SPACING.md,
    paddingVertical: 6,
    borderBottomWidth: 1,
    borderBottomColor: GOV.borde,
  },
  migaTxt: { ...FONT.caption, color: GOV.azulOscuro },

  // Progreso del capítulo
  progresoWrap: {
    backgroundColor: GOV.superficie,
    paddingHorizontal: SPACING.md,
    paddingVertical: SPACING.sm,
    borderBottomWidth: 1,
    borderBottomColor: GOV.borde,
  },
  progresoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 6,
  },
  progresoLabel: { ...FONT.caption, color: GOV.textoS },
  progressBar: { height: 6, borderRadius: 3, backgroundColor: GOV.borde },

  lista: { padding: SPACING.md, paddingBottom: 96 },
  sinPreguntas: { textAlign: 'center', color: GOV.textoT, marginTop: SPACING.xl, ...FONT.body },

  // Sprint 21 — headers de sección (Datos del hogar / Datos de cada miembro)
  seccionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.sm,
    backgroundColor: GOV.azulTenue,
    paddingHorizontal: SPACING.md,
    paddingVertical: SPACING.sm + 2,
    borderRadius: RADIUS.md,
    marginTop: SPACING.md,
    marginBottom: SPACING.sm,
    borderLeftWidth: 4,
    borderLeftColor: GOV.azul,
  },
  seccionTitulo: { ...FONT.body, fontWeight: '700', color: GOV.azulOscuro, flex: 1 },
  seccionHeaderWarning: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.sm,
    backgroundColor: '#FFF3E0',
    paddingHorizontal: SPACING.md,
    paddingVertical: SPACING.sm,
    borderRadius: RADIUS.md,
    marginTop: SPACING.md,
    marginBottom: SPACING.sm,
    borderLeftWidth: 4,
    borderLeftColor: GOV.naranja,
  },
  seccionTituloWarning: { ...FONT.caption, color: GOV.textoP, flex: 1 },

  // Sprint 21 Fase F — navegador wizard entre miembros
  navMiembros: {
    marginTop: SPACING.md,
    backgroundColor: GOV.superficie,
    borderRadius: RADIUS.md,
    padding: SPACING.md,
    borderWidth: 1,
    borderColor: GOV.borde,
    gap: SPACING.sm,
  },
  navMiembrosCounter: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.xs,
    paddingBottom: SPACING.xs,
    borderBottomWidth: 1,
    borderBottomColor: GOV.borde,
  },
  navMiembrosTxt: { ...FONT.body, fontWeight: '700', color: GOV.azulOscuro },
  navMiembrosFaltan: {
    ...FONT.caption,
    color: GOV.naranja,
    marginLeft: 'auto',
    fontWeight: '600',
  },
  navMiembrosBotones: {
    flexDirection: 'row',
    gap: SPACING.sm,
  },
  navBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 4,
    paddingVertical: SPACING.sm + 2,
    borderRadius: RADIUS.md,
  },
  navBtnSecundario: {
    backgroundColor: GOV.azulTenue,
    borderWidth: 1,
    borderColor: GOV.azul,
  },
  navBtnPrimario: { backgroundColor: GOV.azul },
  navBtnDisabled: { backgroundColor: GOV.fondoApp, borderColor: GOV.borde },
  navBtnUltimo: {
    backgroundColor: GOV.verdeTenue,
    borderWidth: 1,
    borderColor: GOV.verde,
  },
  navBtnTxt: { ...FONT.body, fontWeight: '700', color: GOV.azulOscuro },
  navBtnTxtPrimario: { ...FONT.body, fontWeight: '700', color: '#FFF' },
  navBtnUltimoTxt: { ...FONT.body, fontWeight: '700', color: GOV.verde },

  // Tarjeta de pregunta
  preguntaCard: {
    backgroundColor: GOV.superficie,
    borderRadius: RADIUS.md,
    padding: SPACING.md,
    marginBottom: SPACING.sm,
    borderLeftWidth: 4,
    borderLeftColor: GOV.borde,
    ...SHADOW.card,
  },
  preguntaCardPendiente: {
    borderLeftColor: GOV.naranja,
  },
  preguntaCardRespondida: {
    borderLeftColor: GOV.verde,
  },
  preguntaHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: SPACING.sm,
    gap: SPACING.xs,
  },
  numBadge: {
    width: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: GOV.azul,
    justifyContent: 'center',
    alignItems: 'center',
  },
  numBadgeOk: { backgroundColor: GOV.verde },
  numBadgeTxt: { fontSize: 11, fontWeight: '800', color: '#FFFFFF' },
  numTotal: { ...FONT.caption, color: GOV.textoT },
  requeridoChip: {
    marginLeft: 'auto' as any,
    backgroundColor: GOV.rojoTenue,
    borderRadius: RADIUS.pill,
    paddingHorizontal: 8,
    paddingVertical: 2,
  },
  requeridoChipOk: { backgroundColor: GOV.verdeTenue },
  requeridoTxt:    { fontSize: 10, fontWeight: '600', color: GOV.rojo },
  requeridoTxtOk:  { color: GOV.verde },
  codigoTxt: { ...FONT.caption, color: GOV.textoT, fontFamily: 'monospace' },
  textoPregunta: { ...FONT.body, fontWeight: '600', color: GOV.textoP, marginBottom: SPACING.sm },
  ayuda: { ...FONT.small, color: GOV.textoS, marginBottom: SPACING.sm },
  inputTexto: { backgroundColor: GOV.superficie, marginTop: 2 },
  multiHint: {
    ...FONT.caption,
    color: GOV.azul,
    fontWeight: '600',
    marginBottom: SPACING.xs,
    fontStyle: 'italic',
  },

  // Sprint 21 fix UX — opciones como tarjetas tocables (RADIO/LISTA/BOOLEAN/MULTIPLE)
  opcionesWrap: {
    gap: SPACING.xs,
    marginTop: 2,
  },
  opcionItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.sm,
    paddingVertical: SPACING.sm,
    paddingHorizontal: SPACING.md,
    backgroundColor: GOV.superficie,
    borderRadius: RADIUS.md,
    borderWidth: 1,
    borderColor: GOV.borde,
  },
  opcionItemActiva: {
    borderColor: GOV.azul,
    backgroundColor: GOV.azulTenue,
    borderWidth: 2,
  },
  opcionRadio: {
    width: 22,
    height: 22,
    borderRadius: 11,
    borderWidth: 2,
    borderColor: GOV.borde,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: GOV.superficie,
  },
  opcionRadioActivo: { borderColor: GOV.azul },
  opcionRadioInner: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: GOV.azul,
  },
  opcionCheck: {
    width: 22,
    height: 22,
    borderRadius: 4,
    borderWidth: 2,
    borderColor: GOV.borde,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: GOV.superficie,
  },
  opcionCheckActivo: {
    borderColor: GOV.azul,
    backgroundColor: GOV.azul,
  },
  opcionTxt: { ...FONT.body, color: GOV.textoP, flex: 1 },
  opcionTxtActivo: { color: GOV.azulOscuro, fontWeight: '600' },
  sinOpciones: {
    ...FONT.small,
    color: GOV.naranja,
    fontStyle: 'italic',
    padding: SPACING.sm,
    backgroundColor: GOV.naranjaTenue,
    borderRadius: RADIUS.sm,
  },
  footerBar: {
    backgroundColor: GOV.superficie,
    padding: SPACING.md,
    borderTopWidth: 1,
    borderTopColor: GOV.borde,
  },
});
