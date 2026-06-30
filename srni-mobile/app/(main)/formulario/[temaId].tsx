// Motor de captura offline de un capítulo — Sprint 8: carga previa, validación, bulk sync, progreso.
import { useEffect, useState, useMemo, useCallback, useRef, memo } from 'react';
import { View, FlatList, StyleSheet, Alert, Pressable, KeyboardAvoidingView, Platform } from 'react-native';
import {
  Text, TextInput,
  ActivityIndicator, Chip, IconButton, ProgressBar,
} from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useLocalSearchParams, router } from 'expo-router';
import * as instrumentos from '../../../src/services/instrumentos';
import * as borradoresDao from '../../../src/db/borradoresDao';
import * as colaDao from '../../../src/db/colaDao';
import * as victimasOfflineDao from '../../../src/db/victimasOfflineDao';
import { calcularVisibles, motivoOcultaPregunta, type ContextoVictima } from '../../../src/services/skipLogic';
import { cargarMiembrosHogar } from '../../../src/services/miembrosHogar';
import { useSyncStore } from '../../../src/stores/syncStore';
import { useIAStore } from '../../../src/stores/iaStore';
import { useCaracterizacionStore } from '../../../src/stores/caracterizacionStore';
import { encuestasApi } from '../../../src/api/encuestas';
import { AudioRecorder } from '../../../src/components/AudioRecorder';
import { SugerenciaIA } from '../../../src/components/SugerenciaIA';
import { GovHeader } from '../../../src/components/GovHeader';
import { GovButton } from '../../../src/components/GovButton';
import { SelectorMunicipio } from '../../../src/components/SelectorMunicipio';
import { SelectorFecha } from '../../../src/components/SelectorFecha';
import { GOV, SPACING, RADIUS, SHADOW, FONT } from '../../../src/theme/govTheme';
import type { PreguntaRow, OpcionRow, ReglaSkipLogicRow } from '../../../src/db/instrumentoDao';
import type { MiembroHogarResumen, VictimaResumenFuente } from '../../../src/types';

// Sprint 21 — clave compuesta para indexar respuestas por (pregunta, miembro).
// Miembro vacío = pregunta nivel HOGAR (única para toda la sesión).
function claveResp(preguntaId: string, miembroId: string | null | undefined): string {
  return `${preguntaId}|${miembroId ?? ''}`;
}

/** Edad en años cumplidos a hoy, derivada de una fecha ISO 'YYYY-MM-DD'. */
function calcularEdad(fechaISO: string): string {
  if (!fechaISO) return '';
  const nac = new Date(fechaISO);
  if (isNaN(nac.getTime())) return '';
  const hoy = new Date();
  let edad = hoy.getFullYear() - nac.getFullYear();
  const m = hoy.getMonth() - nac.getMonth();
  if (m < 0 || (m === 0 && hoy.getDate() < nac.getDate())) edad--;
  return edad >= 0 && edad < 130 ? String(edad) : '';
}

/**
 * Grupo etario (pregunta B10) derivado de la edad, según los rangos del
 * instrumento (B10_GRUPO_ETARIO). Se autocompleta desde la fecha de nacimiento
 * que ya tiene la víctima → ahorra tramitología, no se vuelve a preguntar.
 *   0-5: Primera infancia · 6-11: Niñez · 12-17: Adolescencia
 *   18-28: Jóvenes · 29-59: Adulto · 60+: Persona mayor
 */
/**
 * Mapea la pertenencia étnica de la víctima al grupo que usa el skip-logic
 * (indigena · negro_afro · rom · ninguno). Heurística por palabra clave.
 */
function mapearEtnia(pertenencia?: string): string {
  const p = (pertenencia ?? '').toLowerCase();
  if (!p) return 'ninguno';
  if (p.includes('ind') || p.includes('resguardo')) return 'indigena';
  if (p.includes('negr') || p.includes('afro') || p.includes('palenq') || p.includes('raizal')) return 'negro_afro';
  if (p.includes('rom') || p.includes('gitan') || p.includes('kumpa')) return 'rom';
  return 'ninguno';
}

function edadAGrupoEtario(edad: number): string {
  if (!Number.isFinite(edad) || edad < 0) return '';
  if (edad <= 5) return '1';
  if (edad <= 11) return '2';
  if (edad <= 17) return '3';
  if (edad <= 28) return '4';
  if (edad <= 59) return '5';
  return '6';
}

/**
 * Traducción del tipo de documento de la víctima (códigos del RUV/Oracle) al
 * valor de la opción A3 del instrumento (LISTA con códigos numéricos). Sin esto,
 * sembrar 'CC' nunca coincidía con la opción '1' y el dato se descartaba en silencio.
 */
const MAP_TIPO_DOC_A3: Record<string, string> = {
  CC: '1',   // Cédula de Ciudadanía
  CE: '2',   // Cédula de Extranjería
  TI: '3',   // Tarjeta de Identidad
  RC: '4',   // Registro Civil/NUIP
  PEP: '9',  // Permiso especial de permanencia
  PTP: '10', PPT: '10', // Permiso temporal de permanencia
  PA: '11',  PAS: '11', PASAPORTE: '11', // Pasaporte
};

/**
 * Traducción del género de la víctima (M/F/NB/ND) al valor de la opción A8 "Sexo"
 * del instrumento (1=Hombre, 2=Mujer, 3=Intersexual, 4=Indeterminado). NB/ND no
 * tienen equivalente directo en SEXO biológico → no se siembran (se capturan a mano).
 */
const MAP_GENERO_A8: Record<string, string> = {
  M: '1', // Hombre
  F: '2', // Mujer
};

/**
 * Mapa codigo_externo → valor para PRE-LLENAR "Datos básicos" del AUTORIZADO con
 * lo ya capturado de la víctima (instrumento territorial/estándar). La EDAD se
 * deriva de la fecha de nacimiento. Los apellidos NO se incluyen porque el
 * instrumento no tiene esa pregunta (decisión de instrumento/UARIV). Los códigos
 * de tipo LISTA (A3 doc, A8 sexo) se traducen al código de opción del instrumento
 * y solo se siembran si coinciden con una opción real (validado en runtime).
 */
function construirPrefillVictima(v: VictimaResumenFuente): Record<string, string> {
  // Códigos del instrumento Territorial reconstruido desde el diccionario oficial.
  const m: Record<string, string> = {};
  if (v.primer_nombre)    m.NOMBRE_1 = v.primer_nombre;
  if (v.segundo_nombre)   m.NOMBRE_2 = v.segundo_nombre;
  if (v.primer_apellido)  m.APELLIDO_1 = v.primer_apellido;
  if (v.segundo_apellido) m.APELLIDO_2 = v.segundo_apellido;
  if (v.fecha_nacimiento) {
    m.A6 = v.fecha_nacimiento;              // fecha de nacimiento (FECHA)
    const edad = calcularEdad(v.fecha_nacimiento);
    if (edad) {
      m.B9 = edad;                          // años cumplidos (NUMERICO)
      // Grupo etario (B10) derivado de la edad — se autocompleta desde la data
      // que ya tiene la víctima (valida la opción en runtime).
      const grupo = edadAGrupoEtario(Number(edad));
      if (grupo) m.B10 = grupo;
    }
  }
  if (v.numero_documento) m.A5 = v.numero_documento;  // número de documento (TEXTO)
  // Tipo de documento y sexo son LISTA con códigos numéricos: traducir desde el
  // código del RUV (CC/CE…, M/F) al valor de la opción del instrumento.
  const docA3 = v.tipo_documento ? MAP_TIPO_DOC_A3[v.tipo_documento.toUpperCase()] : undefined;
  if (docA3) m.A3 = docA3;                            // tipo de documento (LISTA)
  const sexoA8 = v.genero ? MAP_GENERO_A8[v.genero.toUpperCase()] : undefined;
  if (sexoA8) m.A8 = sexoA8;                          // sexo (LISTA)
  // Hecho victimizante: NO se pregunta (el RUV ya lo tiene). Se prellena desde el
  // hecho principal y se MUESTRA en modo solo-lectura (PREGUNTAS_RUV_READONLY) para
  // que el encuestador lo confirme. H_V = hecho · Ocur_HV = fecha de ocurrencia.
  const hecho = v.hechos_victimizantes?.[0];
  if (hecho) {
    if (hecho.codigo || hecho.nombre) m.H_V = hecho.nombre || hecho.codigo;
    if (hecho.fecha_hecho)            m.Ocur_HV = hecho.fecha_hecho;
  }
  return m;
}

/**
 * Preguntas que el RUV ya tiene (hecho victimizante y su fecha de ocurrencia). NO
 * se le preguntan al encuestador: se prellenan desde el RUV y se muestran en modo
 * SOLO LECTURA, para que el encuestador VEA el dato que vino del RUV (confirmación
 * visual) sin poder editarlo. La caracterización es posterior a la victimización →
 * el hecho ya se conoce; capturarlo de nuevo introduciría inconsistencias.
 */
const PREGUNTAS_RUV_READONLY = new Set(['H_V', 'Ocur_HV']);

interface ItemLista {
  // 'pregunta'         → HOGAR: respuesta única para todo el hogar.
  // 'pregunta-persona' → PERSONA: una fila por miembro dentro de la tarjeta.
  type: 'header-hogar' | 'header-miembro' | 'pregunta' | 'pregunta-persona';
  /** preguntas tipo 'pregunta' / 'pregunta-persona' */
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
  const victimaFuente = useCaracterizacionStore((s) => s.victimaFuente);
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
  const flatRef = useRef<FlatList | null>(null);
  // Prellenado: guarda las claves (borrador|capítulo) ya sembradas. ANTES era solo
  // el borrador, lo que causaba que tras precargar el capítulo 1 NO se precargara
  // ningún otro capítulo (mismo borrador → se saltaba). Ahora es por capítulo.
  const prefillRef = useRef<Set<string>>(new Set());
  // Evita repetir la alerta de "no hay borrador" en cada tecla.
  const alertaBorradorRef = useRef(false);

  // ── Cargar datos del capítulo + borradores previos ──────────────────────────
  useEffect(() => {
    if (!temaId) return;

    (async () => {
      console.log('[cap useEffect] params:', { temaId, borradorIdParam, sesionServerId, instrumentoId, hogarId });

      // Sprint 18 F1B: TODO viene de memoria (bundle), no SQLite.
      const caps = instrumentos.getCapitulos();
      const cap = caps.find((c) => c.id === temaId);
      setCapituloNombre(cap?.nombre ?? '');

      const pgs = instrumentos.getPreguntas(temaId);
      setPreguntas(pgs);
      if (pgs.length > 0) {
        setOpciones(instrumentos.getOpcionesBatch(pgs.map((p) => p.id)));
      }

      // Skip-logic: cargar TODAS las reglas del instrumento (no solo las del
      // capítulo). Las HABILITAR/DESHABILITAR/OBLIGAR cuelgan de pregunta_afectada
      // (capitulo_afectado=null) y getReglasPorCapitulo las filtraba fuera → el
      // formulario quedaba sin skip-logic ("como un libro"). calcularVisibles ya
      // filtra por pregunta y maneja FINALIZAR de capítulo con todas las reglas.
      setReglas(instrumentos.getReglas());

      // ── Resolver borrador ─────────────────────────────────────────────────
      const meta = instrumentos.getMeta();
      const instrId = instrumentoId ?? meta?.instrumento_id ?? '';
      console.log('[cap useEffect] meta:', { meta_codigo: meta?.perfil_codigo, instrId });

      if (borradorIdParam) {
        // Ya tenemos un borrador local — cargar sus respuestas (clave compuesta)
        console.log('[cap useEffect] usando borradorIdParam:', borradorIdParam);
        setRespuestasState(await borradoresDao.getRespuestaMapCompuesto(borradorIdParam));
        setBorradorId(borradorIdParam);

      } else if (sesionServerId) {
        // Buscar si ya existe un borrador vinculado a esta sesión
        const existente = await borradoresDao.findBySesionId(sesionServerId);
        console.log('[cap useEffect] findBySesionId:', { sesionServerId, existente: existente ? existente.id : null });

        if (existente) {
          setBorradorId(existente.id);
          setRespuestasState(await borradoresDao.getRespuestaMapCompuesto(existente.id));
        } else {
          // Crear nuevo borrador y vincularlo
          let nuevoBorradorId: string | null = null;
          try {
            const nuevo = await borradoresDao.crearBorrador(instrId, hogarId);
            console.log('[cap useEffect] crearBorrador OK:', { id: nuevo.id, instrId, hogarId });
            await borradoresDao.vincularSesionServidor(nuevo.id, sesionServerId);
            console.log('[cap useEffect] vincularSesionServidor OK:', { borrador: nuevo.id, sesion: sesionServerId });
            setBorradorId(nuevo.id);
            nuevoBorradorId = nuevo.id;
          } catch (e) {
            console.error('[cap useEffect] FALLO al crear/vincular borrador:', e);
          }

          // Si hay conexión, descargar respuestas previas del servidor
          if (estaOnline && nuevoBorradorId) {
            try {
              const { data: previas } = await encuestasApi.getRespuestas(sesionServerId);
              for (const r of previas) {
                if (r.valor) {
                  // Sprint 21: r.miembro puede venir del backend; usar para indexar
                  const mid = (r as any).miembro ?? null;
                  await borradoresDao.upsertRespuesta(nuevoBorradorId, r.pregunta, r.valor, mid);
                }
              }
              setRespuestasState(await borradoresDao.getRespuestaMapCompuesto(nuevoBorradorId));
            } catch { /* sin red — empieza en blanco */ }
          }
        }

      } else {
        // Sesión sin id de servidor (OFFLINE). Reutilizar el borrador único de
        // este (hogar, instrumento) para que TODOS los capítulos compartan el
        // mismo. Solo crear (y encolar CREAR_SESION) si aún no existe ninguno.
        let borrador =
          hogarId && instrId
            ? await borradoresDao.findBorradorOfflinePorHogarInstrumento(hogarId, instrId)
            : null;

        if (borrador) {
          setBorradorId(borrador.id);
          setRespuestasState(await borradoresDao.getRespuestaMapCompuesto(borrador.id));
        } else {
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
      }

      setCargando(false);
    })().catch(() => setCargando(false));
  }, [temaId]);

  // ── Sprint 21 — cargar miembros del hogar ──────────────────────────────────
  // Tolerante a red (fix #4/#38): online → caché; offline-local →
  // construirMiembrosOffline; online caído → caché del servidor. Sin esto las
  // preguntas PERSONA NO se renderizaban sin red y se perdía media caracterización.
  useEffect(() => {
    if (!hogarId) return;
    let activo = true;
    cargarMiembrosHogar(hogarId)
      .then((ms) => { if (activo) setMiembros(ms); })
      .catch(() => { /* queda en [] (degradación a solo HOGAR) */ });
    return () => { activo = false; };
  }, [hogarId]);

  // ── Prellenado de "Datos básicos" del autorizado ────────────────────────────
  // Siembra UNA sola vez por borrador las respuestas que ya conocemos de la
  // víctima (nombres, documento, fecha de nacimiento, EDAD derivada, sexo), solo
  // en celdas VACÍAS (nunca pisa lo capturado). Encola cada valor para que
  // sincronice igual que una respuesta normal. Si el capítulo no tiene preguntas
  // mapeables, no hace nada.
  useEffect(() => {
    const bid = borradorId ?? borradorIdParam;
    if (!bid || preguntas.length === 0) return;
    const claveCap = `${bid}|${temaId}`; // por capítulo, no por borrador
    if (prefillRef.current.has(claveCap)) return;

    // Las preguntas de datos básicos son PERSONA → se siembran contra el miembro
    // autorizado. `miembros` ya viene ordenado con el autorizado primero
    // (ordenarMiembros), así que si ninguno trae el flag es_autorizado marcado
    // (p.ej. el backend no lo seteó), caemos al primero como autorizado de facto
    // en vez de bloquear TODO el prellenado.
    const autorizado = miembros.find((m) => m.es_autorizado) ?? miembros[0] ?? null;

    let cancelado = false;
    (async () => {
      try {
        // Fuente de datos del prellenado. `victimaFuente` vive solo en memoria
        // (store volátil) y se pierde al reabrir la caracterización, cerrar la
        // app o re-enfocar la búsqueda. Cuando no esté (o llegue incompleta), la
        // recuperamos PERSISTIDA desde victimas_offline por el id del autorizado
        // (que offline ES el id_local de la víctima). Así la precarga sobrevive.
        let fuente = victimaFuente;
        if ((!fuente || !fuente.fecha_nacimiento) && autorizado?.id) {
          try {
            const row = await victimasOfflineDao.obtenerPorIdLocal(autorizado.id);
            if (row) {
              const persistida = JSON.parse(row.payload_json) as VictimaResumenFuente;
              if (persistida?.fecha_nacimiento || !fuente) fuente = persistida;
            }
          } catch { /* sin víctima persistida: seguimos con lo que haya */ }
        }
        if (cancelado) return;
        if (!fuente) return; // ni store ni SQLite → esperar (re-corre si llega)

        const map = construirPrefillVictima(fuente);
        if (Object.keys(map).length === 0) { prefillRef.current.add(claveCap); return; }

        const hayPersonaMapeable = preguntas.some(
          (p) => map[p.codigo_externo] && p.nivel === 'PERSONA',
        );
        // Si hay preguntas PERSONA por sembrar pero aún no hay miembro, esperar
        // (el effect re-corre cuando lleguen los miembros).
        if (hayPersonaMapeable && !autorizado) return;

        const existentes = await borradoresDao.getRespuestaMapCompuesto(bid);
        const borrador = await borradoresDao.getBorrador(bid);
        const nuevos: Record<string, string> = {};
        for (const p of preguntas) {
          const valor = map[p.codigo_externo];
          if (!valor) continue;
          const miembroId = p.nivel === 'PERSONA' ? (autorizado?.id ?? null) : null;
          if (p.nivel === 'PERSONA' && !miembroId) continue;
          const clave = claveResp(p.id, miembroId);
          if (existentes[clave]?.trim()) continue; // no pisar lo ya capturado
          // Tipos de opción: solo sembrar si el valor coincide con una opción real.
          const esOpcion = p.tipo === 'LISTA' || p.tipo === 'RADIO'
            || p.tipo === 'BOOLEAN' || p.tipo === 'LISTA_MULTIPLE';
          if (esOpcion) {
            const ops = opciones[p.id] ?? [];
            if (!ops.some((o) => o.valor === valor)) continue;
          }
          await borradoresDao.upsertRespuesta(bid, p.id, valor, miembroId);
          await colaDao.encolar('RESPONDER_PREGUNTA', bid, {
            borrador_id: bid,
            sesion_id: borrador?.sesion_id ?? null,
            pregunta_id: p.id,
            miembro_id: miembroId,
            valor,
          });
          nuevos[clave] = valor;
        }
        if (cancelado) return;
        prefillRef.current.add(claveCap);
        if (Object.keys(nuevos).length > 0) {
          setRespuestasState((prev) => ({ ...prev, ...nuevos }));
          await refrescarContadores();
        }
      } catch { /* prellenado best-effort: si falla, el usuario captura a mano */ }
    })();
    return () => { cancelado = true; };
  }, [borradorId, borradorIdParam, temaId, victimaFuente, preguntas, miembros, opciones, refrescarContadores]);

  // ── Skip logic — captura AGRUPADA (una pregunta, fila por miembro) ───────────
  // Cada pregunta PERSONA se evalúa POR CADA MIEMBRO con SU propio contexto
  // (edad/sexo/etnia/RUV de ese miembro) y SUS propias respuestas. Una pregunta
  // aplica a un miembro M si queda visible al evaluar con el contexto/respuestas
  // de M. Si no aplica, se muestra la fila en gris con el motivo derivado de la
  // regla que la oculta. Las HOGAR usan una única respuesta para todo el hogar.
  //
  // Todas las preguntas del instrumento (todos los capítulos) — para que el
  // skip-logic CROSS-CAPÍTULO funcione (ej. H3 rehabilitación depende de B16
  // discapacidad, que está en otro capítulo). `respuestas` ya trae todo el borrador.
  const todasPreguntasInstrumento = useMemo(
    () => instrumentos.getCapitulos().flatMap((c) => instrumentos.getPreguntas(c.id)),
    [temaId],
  );

  // Construye el mapa de respuestas (codigo_externo → valor) para evaluar
  // skip-logic desde la óptica de UN miembro: PERSONA usa la respuesta de ESE
  // miembro; HOGAR usa su respuesta única.
  const construirRespuestasMiembro = useCallback(
    (miembro: MiembroHogarResumen | null): Record<string, string> => {
      const m: Record<string, string> = {};
      for (const p of todasPreguntasInstrumento) {
        if (p.nivel === 'PERSONA') {
          m[p.codigo_externo] = miembro ? (respuestas[claveResp(p.id, miembro.id)] ?? '') : '';
        } else {
          m[p.codigo_externo] = respuestas[claveResp(p.id, null)] ?? '';
        }
      }
      return m;
    },
    [todasPreguntasInstrumento, respuestas],
  );

  // Contexto demográfico/étnico de UN miembro (edad/sexo/etnia/RUV) para evaluar
  // condiciones offline. Prioriza lo capturado por ESE miembro (A6 fecha, B9 edad,
  // A8 sexo); cae a los datos del propio miembro (genero, fecha_nacimiento,
  // incluido_ruv). Para etnia no hay dato por-miembro: se usa el de la víctima
  // fuente SOLO para el autorizado (a quien pertenece esa fuente); el resto cae a
  // 'ninguno' salvo que el miembro la haya capturado. (Riesgo documentado.)
  const construirContextoMiembro = useCallback(
    (miembro: MiembroHogarResumen | null, respMiembro: Record<string, string>): ContextoVictima => {
      const esAutorizado = !!miembro?.es_autorizado;
      const fuente = esAutorizado ? victimaFuente : null;
      const fechaNac = respMiembro.A6 || miembro?.fecha_nacimiento || fuente?.fecha_nacimiento || '';
      const edadResp = respMiembro.B9 ? Number(respMiembro.B9) : NaN;
      const edad = Number.isFinite(edadResp) ? edadResp : Number(calcularEdad(fechaNac));
      // sexo: A8 captura '1'=Hombre/'2'=Mujer; cae al genero del miembro (M/F),
      // y para el autorizado al genero de la víctima fuente.
      let sexo = respMiembro.A8 || '';
      const genero = miembro?.genero || fuente?.genero || '';
      if (!sexo && genero) sexo = genero === 'M' ? '1' : genero === 'F' ? '2' : '';
      // etnia: solo la víctima fuente (autorizado) la tiene fiable. El resto
      // 'ninguno' por defecto (no hay dato por-miembro persistido).
      const etnia = esAutorizado ? mapearEtnia(fuente?.pertenencia_etnica) : 'ninguno';
      // RUV: del propio miembro; para el autorizado cae a la víctima fuente.
      const ruvIncluido = miembro?.incluido_ruv ?? (fuente?.estado_ruv === 'INCLUIDO');
      return {
        edad: Number.isFinite(edad) ? edad : undefined,
        sexo: sexo || undefined,
        etnia,
        ruvIncluido,
      };
    },
    [victimaFuente],
  );

  // ── Visibilidad HOGAR (una sola evaluación, contexto del autorizado) ─────────
  // Las preguntas HOGAR no dependen de un miembro; se evalúan con el contexto del
  // autorizado (o primer miembro) por compatibilidad con reglas demográficas.
  const visiblesHogar = useMemo(() => {
    const autorizado = miembros.find((m) => m.es_autorizado) ?? miembros[0] ?? null;
    const respMiembro = construirRespuestasMiembro(autorizado);
    const ctx = construirContextoMiembro(autorizado, respMiembro);
    const { visibles } = calcularVisibles(preguntas, reglas, respMiembro, ctx);
    // es_precargada: datos del RUV/sesión (dirección territorial, nombres RUV, hecho
    // victimizante, estado…) — ya capturados antes; NO se vuelven a preguntar.
    return preguntas.filter((p) => p.nivel === 'HOGAR' && !p.es_precargada && visibles.has(p.codigo_externo));
  }, [preguntas, reglas, miembros, construirRespuestasMiembro, construirContextoMiembro]);

  // ── Visibilidad PERSONA por miembro ──────────────────────────────────────────
  // Para CADA miembro: evalúa skip-logic con su contexto/respuestas y guarda, por
  // pregunta PERSONA, si aplica (visible) y, si no, el motivo. Resultado indexado
  // por id de miembro. Una pregunta PERSONA se muestra en el capítulo si está
  // visible para AL MENOS un miembro (si no la ve nadie, no se lista).
  type AplicabilidadMiembro = { aplica: boolean; motivo?: string };
  const personaPorMiembro = useMemo(() => {
    const mapa = new Map<string, Map<string, AplicabilidadMiembro>>(); // miembroId → (codigo → {aplica,motivo})
    for (const miembro of miembros) {
      const respMiembro = construirRespuestasMiembro(miembro);
      const ctx = construirContextoMiembro(miembro, respMiembro);
      const { visibles } = calcularVisibles(preguntas, reglas, respMiembro, ctx);
      const porPregunta = new Map<string, AplicabilidadMiembro>();
      for (const p of preguntas) {
        if (p.nivel !== 'PERSONA') continue;
        const aplica = visibles.has(p.codigo_externo);
        if (aplica) {
          porPregunta.set(p.codigo_externo, { aplica: true });
        } else {
          const motivo = motivoOcultaPregunta(p, reglas, respMiembro, ctx);
          porPregunta.set(p.codigo_externo, { aplica: false, motivo });
        }
      }
      mapa.set(miembro.id, porPregunta);
    }
    return mapa;
  }, [preguntas, reglas, miembros, construirRespuestasMiembro, construirContextoMiembro]);

  // Preguntas PERSONA a listar: las que aplican a AL MENOS un miembro. Si no hay
  // miembros resueltos, se listan todas las PERSONA del capítulo (degradación:
  // el motor mostrará el aviso de "no se cargaron miembros").
  const visiblesPersona = useMemo(() => {
    const personaTodas = preguntas.filter((p) => p.nivel === 'PERSONA' && !p.es_precargada);
    if (miembros.length === 0) return personaTodas;
    return personaTodas.filter((p) =>
      miembros.some((m) => personaPorMiembro.get(m.id)?.get(p.codigo_externo)?.aplica),
    );
  }, [preguntas, miembros, personaPorMiembro]);

  // Helper de render: aplicabilidad de una pregunta para un miembro concreto.
  const aplicabilidad = useCallback(
    (codigoExterno: string, miembroId: string): AplicabilidadMiembro =>
      personaPorMiembro.get(miembroId)?.get(codigoExterno) ?? { aplica: false, motivo: 'no aplica' },
    [personaPorMiembro],
  );

  // ── Construcción de la lista (agrupada) ──────────────────────────────────────
  // HOGAR: header + una tarjeta por pregunta (respuesta única).
  // PERSONA: header + una tarjeta por pregunta; dentro, una fila por miembro.
  const items = useMemo<ItemLista[]>(() => {
    const out: ItemLista[] = [];
    let idx = 0;
    // Render en el ORDEN del manual (campo `orden`), intercalando HOGAR y PERSONA.
    // Antes se separaba en bloque HOGAR + bloque PERSONA, lo que mandaba las
    // preguntas PERSONA (ej. autorreconocimiento A4, celular A11) al final, fuera
    // de orden. Cada PERSONA sigue siendo una tarjeta agrupada (fila por miembro).
    const todasVis = [...visiblesHogar, ...visiblesPersona].sort((a, b) => a.orden - b.orden);
    const totalGlobal = todasVis.length;
    for (const p of todasVis) {
      out.push(
        p.nivel === 'PERSONA'
          ? { type: 'pregunta-persona', pregunta: p, miembro: null, indexGlobal: idx++, totalGlobal, key: `qp-${p.id}` }
          : { type: 'pregunta', pregunta: p, miembro: null, indexGlobal: idx++, totalGlobal, key: `q-${p.id}-` },
      );
    }
    return out;
  }, [visiblesHogar, visiblesPersona, miembros]);

  // ── Progreso del capítulo ───────────────────────────────────────────────────
  // Las obligatorias PERSONA solo cuentan para los miembros A QUIENES APLICA la
  // pregunta (skip-logic por miembro). Antes contaba PERSONA × TODOS los miembros,
  // lo que inflaba el denominador con celdas que nunca se pueden responder.
  const { totalOblig, respondidoOblig } = useMemo(() => {
    const obligHogar = visiblesHogar.filter((p) => p.obligatoria === 1);
    const obligPersona = visiblesPersona.filter((p) => p.obligatoria === 1);

    let totalOblig = obligHogar.length;
    let respondidoOblig = 0;
    for (const p of obligHogar) {
      if (respuestas[claveResp(p.id, null)]?.trim()) respondidoOblig++;
    }
    for (const p of obligPersona) {
      for (const m of miembros) {
        if (!aplicabilidad(p.codigo_externo, m.id).aplica) continue;
        totalOblig++;
        if (respuestas[claveResp(p.id, m.id)]?.trim()) respondidoOblig++;
      }
    }
    return { totalOblig, respondidoOblig };
  }, [visiblesHogar, visiblesPersona, miembros, respuestas, aplicabilidad]);

  const progresoCap = totalOblig > 0 ? respondidoOblig / totalOblig : 0;

  // ── Guardar respuesta en SQLite + encolar (con debounce 500 ms) ─────────────
  // - El estado React se actualiza inmediato (UI fluida).
  // - SQLite + cola se escriben 500 ms después del último cambio por clave
  //   pregunta+miembro. Esto evita un job por keystroke en preguntas tipo TEXTO.
  // - flushPendientes() fuerza la persistencia inmediata (lo usa "Guardar capítulo").
  type Pendiente = { preguntaId: string; valor: string; miembroId: string | null };
  const debounceTimers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());
  const pendientes = useRef<Map<string, Pendiente>>(new Map());

  const persistirRespuesta = useCallback(async (bid: string, p: Pendiente) => {
    try {
      await borradoresDao.upsertRespuesta(bid, p.preguntaId, p.valor, p.miembroId);
      console.log('[setRespuesta] guardada:', { bid, preguntaId: p.preguntaId, miembroId: p.miembroId });
      const borrador = await borradoresDao.getBorrador(bid);
      if (borrador) {
        await colaDao.encolar('RESPONDER_PREGUNTA', bid, {
          borrador_id: bid,
          sesion_id: borrador.sesion_id ?? null,
          pregunta_id: p.preguntaId,
          miembro_id: p.miembroId,
          valor: p.valor,
        });
        await refrescarContadores();
      }
    } catch (e) {
      console.error('[setRespuesta] ERROR upsertRespuesta:', e);
    }
  }, []);

  // Al desmontar: persistir cualquier pendiente para no perderlo si el usuario
  // sale del capítulo sin tocar "Guardar".
  useEffect(() => {
    const timers = debounceTimers.current;
    const pend = pendientes.current;
    return () => {
      timers.forEach((t) => clearTimeout(t));
      timers.clear();
      const bid = borradorId ?? borradorIdParam;
      if (!bid) { pend.clear(); return; }
      const items = Array.from(pend.values());
      pend.clear();
      // Persistencia fire-and-forget — el cleanup no puede ser async.
      for (const p of items) void persistirRespuesta(bid, p);
    };
  }, [borradorId, borradorIdParam, persistirRespuesta]);

  const flushPendientes = useCallback(async () => {
    const bid = borradorId ?? borradorIdParam;
    if (!bid) return;
    const timers = debounceTimers.current;
    const items = Array.from(pendientes.current.values());
    timers.forEach((t) => clearTimeout(t));
    timers.clear();
    pendientes.current.clear();
    for (const p of items) {
      await persistirRespuesta(bid, p);
    }
  }, [borradorId, borradorIdParam, persistirRespuesta]);

  const setRespuesta = useCallback((
    preguntaId: string,
    valor: string,
    miembroId: string | null = null,
  ) => {
    const clave = claveResp(preguntaId, miembroId);
    // 1) UI: estado React inmediato
    setRespuestasState((prev) => ({ ...prev, [clave]: valor }));

    const bid = borradorId ?? borradorIdParam;
    if (!bid) {
      // Sin borrador NO se puede persistir: avisar de forma visible (una vez) en
      // lugar de descartar en silencio. Evita capturar "a ciegas" y perder todo.
      if (!alertaBorradorRef.current) {
        alertaBorradorRef.current = true;
        Alert.alert(
          'No se pudo guardar',
          'No se preparó el borrador de esta caracterización. Vuelve atrás y entra de nuevo al capítulo; si continúa, reinicia la app.',
        );
      }
      return;
    }

    // 2) Guardar valor pendiente + reprogramar timer de persistencia
    pendientes.current.set(clave, { preguntaId, valor, miembroId });
    const timers = debounceTimers.current;
    const prev = timers.get(clave);
    if (prev) clearTimeout(prev);
    const timer = setTimeout(() => {
      timers.delete(clave);
      const p = pendientes.current.get(clave);
      if (!p) return;
      pendientes.current.delete(clave);
      void persistirRespuesta(bid, p);
    }, 500);
    timers.set(clave, timer);
  }, [borradorId, borradorIdParam, persistirRespuesta]);

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

  // ── Autollenar correspondencia = residencia cuando Z11 = "Sí" (mismo lugar) ───
  // Las preguntas de correspondencia quedan OCULTAS por skip-logic cuando el lugar
  // es el mismo, pero el registro debe llevar el dato (igual al de residencia).
  // Pares residencia→correspondencia del cap A (Identificación). En otros capítulos
  // los códigos no existen → no-op. Solo escribe si difiere (evita re-render loop).
  useEffect(() => {
    const byCodigo = new Map(preguntas.map((p) => [p.codigo_externo, p]));
    const z11 = byCodigo.get('Z11');
    if (!z11) return;
    if ((respuestas[claveResp(z11.id, null)] ?? '') !== 'true') return;
    const pares: [string, string][] = [
      ['Z5A', 'Z15'], ['Z6', 'Z16'], ['Z7', 'Z17'], ['VEREDA', 'Z18'], ['Z8', 'Z12'],
    ];
    for (const [resCod, corCod] of pares) {
      const res = byCodigo.get(resCod), cor = byCodigo.get(corCod);
      if (!res || !cor) continue;
      const valRes = respuestas[claveResp(res.id, null)] ?? '';
      const valCor = respuestas[claveResp(cor.id, null)] ?? '';
      if (valRes && valRes !== valCor) setRespuesta(cor.id, valRes, null);
    }
  }, [preguntas, respuestas, setRespuesta]);

  // ── Guardar capítulo: bulk sync (online) o encolar (offline) → volver ─────────
  async function guardarYVolver() {
    const bid = borradorId ?? borradorIdParam;

    // Persistir cualquier respuesta debounceada que aún esté en el aire ANTES
    // de leer SQLite para el bulk.
    await flushPendientes();

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
          let enviado = false;
          if (estaOnline) {
            try {
              await encuestasApi.responderBulk(sesionServerId, arr);
              enviado = true;
            } catch { /* el envío directo falló — cae al encolado de abajo */ }
          }
          if (!enviado) {
            // Sin red (o bulk online fallido): encolar para que la cola lo
            // reintente cuando vuelva la conexión. Sin este fallback, un 500
            // o timeout dejaba las respuestas solo en SQLite sin reintento.
            await colaDao.encolar('RESPONDER_BULK', bid, {
              sesion_id: sesionServerId,
              borrador_id: bid,
              respuestas: arr,
            });
          }
        }
      } catch { /* lectura de SQLite falló — las respuestas siguen en el borrador */ }
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
    } else if (borradorId || borradorIdParam || (hogarId && instrumentoId)) {
      // OFFLINE: volver a la LISTA de capítulos local (índice del formulario),
      // que es 100% offline-friendly. NUNCA al hub del servidor
      // (hogares/[hogarId]/caracterizaciones hace hogaresApi.detalle y, con un
      // id de hogar local + sin red, revienta el flujo). Mantenemos el MISMO
      // borrador para que el progreso y las respuestas se conserven.
      router.replace({
        pathname: '/(main)/formulario',
        params: {
          ...(borradorId ?? borradorIdParam
            ? { borradorId: (borradorId ?? borradorIdParam) as string }
            : {}),
          ...(instrumentoId ? { instrumentoId } : {}),
          ...(hogarId ? { hogarId } : {}),
        },
      });
    } else {
      router.back();
    }
  }

  async function finalizarCapitulo() {
    // Preguntas obligatorias sin respuesta: HOGAR (1 por pregunta) y PERSONA
    // (1 por pregunta × miembro AL QUE APLICA, según skip-logic por miembro).
    let faltantes = 0;
    for (const p of visiblesHogar) {
      if (p.obligatoria !== 1) continue;
      if (!respuestas[claveResp(p.id, null)]?.trim()) faltantes++;
    }
    for (const p of visiblesPersona) {
      if (p.obligatoria !== 1) continue;
      for (const m of miembros) {
        if (!aplicabilidad(p.codigo_externo, m.id).aplica) continue;
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

  // Guarda #6 — sin borrador resuelto NO se puede persistir nada. Bloquear la
  // captura con un estado de error en vez de pintar el formulario y descartar
  // cada respuesta en silencio (pérdida total a ciegas).
  if (!(borradorId ?? borradorIdParam)) {
    return (
      <View style={styles.root}>
        <GovHeader title={capituloNombre || 'Capítulo'} onBack={volverAListaCapitulos} />
        <View style={styles.centrado}>
          <MaterialCommunityIcons name="alert-circle-outline" size={44} color={GOV.rojo} />
          <Text style={{ ...FONT.body, color: GOV.textoP, textAlign: 'center', marginTop: SPACING.sm, marginBottom: SPACING.md }}>
            No se pudo preparar el borrador de esta caracterización. No es posible
            capturar respuestas en este capítulo.
          </Text>
          <GovButton label="Volver a capítulos" variant="secondary" onPress={volverAListaCapitulos} />
        </View>
      </View>
    );
  }

  // Captura agrupada: cada pregunta se muestra UNA vez (las PERSONA con una fila
  // por miembro dentro de la misma tarjeta), así que el conteo es 1 por pregunta.
  const totalVisible = visiblesHogar.length + visiblesPersona.length;
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

      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
      <FlatList
        ref={flatRef}
        data={items}
        keyExtractor={(it) => it.key}
        keyboardShouldPersistTaps="handled"
        removeClippedSubviews
        initialNumToRender={6}
        maxToRenderPerBatch={8}
        windowSize={7}
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
            if (miembros.length === 0) {
              return (
                <View style={styles.seccionHeaderWarning}>
                  <MaterialCommunityIcons name="alert-circle-outline" size={18} color={GOV.naranja} />
                  <Text style={styles.seccionTituloWarning}>
                    Este capítulo tiene preguntas por persona, pero no se pudieron cargar los miembros del hogar.
                  </Text>
                </View>
              );
            }
            // Captura agrupada: una sola cabecera "Datos por persona" — cada
            // pregunta lista a TODOS los miembros en filas dentro de su tarjeta.
            return (
              <View style={styles.seccionHeader}>
                <MaterialCommunityIcons name="account-group" size={18} color={GOV.azul} />
                <Text style={styles.seccionTitulo}>
                  Datos por persona ({miembros.length} miembro{miembros.length !== 1 ? 's' : ''})
                </Text>
              </View>
            );
          }

          if (item.type === 'pregunta-persona') {
            // Pregunta PERSONA: una tarjeta con una fila por miembro. Cada miembro
            // responde su propio valor; si no aplica, fila en gris con el motivo.
            const p = item.pregunta!;
            return (
              <PreguntaPersonaItem
                pregunta={p}
                index={item.indexGlobal ?? 0}
                total={item.totalGlobal ?? 0}
                opciones={opciones[p.id] ?? []}
                miembros={miembros}
                respuestas={respuestas}
                soloLectura={PREGUNTAS_RUV_READONLY.has(p.codigo_externo)}
                aplicabilidad={aplicabilidad}
                onChange={setRespuesta}
              />
            );
          }

          // type === 'pregunta' (HOGAR — respuesta única)
          const p = item.pregunta!;
          const clave = claveResp(p.id, null);
          const valor = respuestas[clave] ?? '';
          // IA: solo se asocia con HOGAR por ahora (clave preguntaId solo)
          return (
            <PreguntaItem
              pregunta={p}
              index={item.indexGlobal ?? 0}
              total={item.totalGlobal ?? 0}
              opciones={opciones[p.id] ?? []}
              valor={valor}
              soloLectura={PREGUNTAS_RUV_READONLY.has(p.codigo_externo)}
              onChange={(v) => setRespuesta(p.id, v, null)}
              iaActivo={iaActivo}
              onTextoIA={(texto) => handleTextoTranscrito(p.id, texto)}
              sugerenciaActiva={
                sugerencia && preguntaActivaId === p.id && estadoIA === 'sugerida'
                  ? sugerencia
                  : null
              }
              onAceptarIA={() => handleAceptarSugerencia(p.id)}
              onRechazarIA={rechazarSugerencia}
            />
          );
        }}
        contentContainerStyle={styles.lista}
        ListEmptyComponent={
          <Text style={styles.sinPreguntas}>No hay preguntas en este capítulo.</Text>
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
      </KeyboardAvoidingView>
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

// ─────────────────────────────────────────────────────────────────────────────
// Control de entrada por tipo — reutilizable por HOGAR (1 control) y por cada
// fila de miembro en las preguntas PERSONA. Centraliza TODOS los tipos de input
// (TEXTO/NUMERICO/FECHA/RADIO/LISTA/BOOLEAN/LISTA_MULTIPLE/COMBO_DINAMICO) y sus
// validaciones, para que cada miembro pueda responder su propio valor con la
// MISMA lógica (incluida la selección múltiple). `compacto` reduce los labels de
// los selectores cuando el control vive dentro de una fila de miembro.
// ─────────────────────────────────────────────────────────────────────────────
function ControlInput({
  pregunta,
  opciones,
  valor,
  onChange,
  compacto,
}: {
  pregunta: PreguntaRow;
  opciones: OpcionRow[];
  valor: string;
  onChange: (v: string) => void;
  compacto?: boolean;
}) {
  const esTexto    = pregunta.tipo === 'TEXTO' || pregunta.tipo === 'TEXTO_LARGO';
  const esNumerico = pregunta.tipo === 'NUMERICO';
  const validaciones = useMemo<{ longitud_exacta?: number; max_length?: number; solo_numerico?: boolean }>(() => {
    try { return JSON.parse(pregunta.validaciones || '{}'); } catch { return {}; }
  }, [pregunta.validaciones]);
  const maxLen = validaciones.longitud_exacta ?? validaciones.max_length;
  const onChangeValidado = (t: string) => {
    let v = validaciones.solo_numerico ? t.replace(/[^0-9]/g, '') : t;
    if (maxLen) v = v.slice(0, maxLen);
    onChange(v);
  };
  const esFecha    = pregunta.tipo === 'FECHA';
  // Sprint 20: COMBO_DINAMICO ya no se trata como LISTA — SelectorMunicipio.
  const esRadio    = pregunta.tipo === 'RADIO' || pregunta.tipo === 'LISTA';
  const esCombo    = pregunta.tipo === 'COMBO_DINAMICO';
  const esMultiple = pregunta.tipo === 'LISTA_MULTIPLE';
  const esBoolean  = pregunta.tipo === 'BOOLEAN';

  return (
    <>
      {(esTexto || esNumerico) && (
        <TextInput
          mode="outlined"
          value={valor}
          onChangeText={onChangeValidado}
          keyboardType={esNumerico ? 'numeric' : 'default'}
          maxLength={maxLen}
          multiline={pregunta.tipo === 'TEXTO_LARGO'}
          numberOfLines={pregunta.tipo === 'TEXTO_LARGO' ? 4 : 1}
          placeholder={esNumerico ? 'Escribe el número' : 'Escribe la respuesta'}
          outlineColor={GOV.borde}
          activeOutlineColor={GOV.azul}
          dense={compacto}
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

      {/* Sprint 20: COMBO_DINAMICO = municipio. */}
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
    </>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Fila de un miembro dentro de una pregunta PERSONA. Si la pregunta aplica al
// miembro, muestra su control de entrada; si no, una fila gris con el motivo.
// ─────────────────────────────────────────────────────────────────────────────
function FilaMiembroBase({
  miembro,
  pregunta,
  opciones,
  valor,
  aplica,
  motivo,
  soloLectura,
  onChange,
}: {
  miembro: MiembroHogarResumen;
  pregunta: PreguntaRow;
  opciones: OpcionRow[];
  valor: string;
  aplica: boolean;
  motivo?: string;
  soloLectura?: boolean;
  onChange: (v: string) => void;
}) {
  const rolPrefijo = miembro.es_autorizado ? 'Autorizado' : 'Miembro';
  const nombre = (miembro.nombre_completo ?? '').trim();
  const titulo = nombre || miembro.rol_display || rolPrefijo;
  const tieneRespuesta = !!valor?.trim();

  // No aplica → fila gris con el motivo, sin control habilitado.
  if (!aplica) {
    return (
      <View style={styles.filaMiembro}>
        <View style={styles.filaMiembroHeader}>
          <MaterialCommunityIcons
            name={miembro.es_autorizado ? 'account-star-outline' : 'account-outline'}
            size={16}
            color={GOV.textoT}
          />
          <Text style={styles.filaMiembroNombreInactivo} numberOfLines={1}>{titulo}</Text>
        </View>
        <View style={styles.noAplicaBox}>
          <MaterialCommunityIcons name="minus-circle-outline" size={14} color={GOV.textoT} />
          <Text style={styles.noAplicaTxt}>
            No aplica{motivo ? ` · ${motivo}` : ''}
          </Text>
        </View>
      </View>
    );
  }

  // Solo lectura (RUV) — muestra el valor sin control editable.
  if (soloLectura) {
    const esOpcion = pregunta.tipo === 'RADIO' || pregunta.tipo === 'LISTA'
      || pregunta.tipo === 'BOOLEAN' || pregunta.tipo === 'LISTA_MULTIPLE';
    const etiqueta = esOpcion
      ? (opciones.find((o) => o.valor === valor)?.etiqueta ?? valor)
      : valor;
    return (
      <View style={styles.filaMiembro}>
        <View style={styles.filaMiembroHeader}>
          <MaterialCommunityIcons name="lock-outline" size={15} color={GOV.textoS} />
          <Text style={styles.filaMiembroNombre} numberOfLines={1}>{titulo}</Text>
        </View>
        <Text style={styles.ruvValorTxt}>
          {etiqueta?.trim() ? etiqueta : 'Sin dato registrado'}
        </Text>
      </View>
    );
  }

  return (
    <View style={[styles.filaMiembro, tieneRespuesta && styles.filaMiembroOk]}>
      <View style={styles.filaMiembroHeader}>
        <MaterialCommunityIcons
          name={miembro.es_autorizado ? 'account-star' : 'account'}
          size={16}
          color={tieneRespuesta ? GOV.verde : GOV.azul}
        />
        <Text style={styles.filaMiembroNombre} numberOfLines={1}>{titulo}</Text>
        {tieneRespuesta && (
          <MaterialCommunityIcons name="check-circle" size={15} color={GOV.verde} />
        )}
      </View>
      <ControlInput pregunta={pregunta} opciones={opciones} valor={valor} onChange={onChange} compacto />
    </View>
  );
}

const FilaMiembro = memo(FilaMiembroBase, (prev, next) =>
  prev.pregunta === next.pregunta &&
  prev.miembro === next.miembro &&
  prev.valor === next.valor &&
  prev.aplica === next.aplica &&
  prev.motivo === next.motivo &&
  prev.opciones === next.opciones &&
  prev.soloLectura === next.soloLectura,
);

// ─────────────────────────────────────────────────────────────────────────────
// Tarjeta de una pregunta PERSONA — encabezado de la pregunta + una fila por
// miembro del hogar (agrupado). Reemplaza el wizard "un miembro a la vez".
// ─────────────────────────────────────────────────────────────────────────────
function PreguntaPersonaItemBase({
  pregunta,
  index,
  total,
  opciones,
  miembros,
  respuestas,
  soloLectura,
  aplicabilidad,
  onChange,
}: {
  pregunta: PreguntaRow;
  index: number;
  total: number;
  opciones: OpcionRow[];
  miembros: MiembroHogarResumen[];
  respuestas: Record<string, string>;
  soloLectura?: boolean;
  aplicabilidad: (codigoExterno: string, miembroId: string) => { aplica: boolean; motivo?: string };
  onChange: (preguntaId: string, valor: string, miembroId: string | null) => void;
}) {
  const esObligatoria = pregunta.obligatoria === 1;
  // Cuántos miembros a quienes APLICA ya tienen respuesta (progreso de la tarjeta).
  const aplicables = miembros.filter((m) => aplicabilidad(pregunta.codigo_externo, m.id).aplica);
  const respondidos = aplicables.filter(
    (m) => respuestas[claveResp(pregunta.id, m.id)]?.trim(),
  ).length;
  const completa = aplicables.length > 0 && respondidos === aplicables.length;

  return (
    <View style={[
      styles.preguntaCard,
      esObligatoria && !completa && styles.preguntaCardPendiente,
      completa && styles.preguntaCardRespondida,
    ]}>
      <View style={styles.preguntaHeader}>
        <View style={[styles.numBadge, completa && styles.numBadgeOk]}>
          {completa
            ? <MaterialCommunityIcons name="check" size={13} color="#FFFFFF" />
            : <Text style={styles.numBadgeTxt}>{index + 1}</Text>
          }
        </View>
        <Text style={styles.numTotal}>de {total}</Text>
        {esObligatoria && (
          <View style={[styles.requeridoChip, completa && styles.requeridoChipOk]}>
            <Text style={[styles.requeridoTxt, completa && styles.requeridoTxtOk]}>
              {completa ? 'Completa' : 'Requerida'}
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

      {aplicables.length > 0 && (
        <Text style={styles.personaProgreso}>
          {respondidos} de {aplicables.length} {aplicables.length === 1 ? 'persona' : 'personas'} respondida{respondidos !== 1 ? 's' : ''}
        </Text>
      )}

      {/* Una fila por miembro */}
      <View style={styles.filasWrap}>
        {miembros.map((m) => {
          const ap = aplicabilidad(pregunta.codigo_externo, m.id);
          const valor = respuestas[claveResp(pregunta.id, m.id)] ?? '';
          return (
            <FilaMiembro
              key={m.id}
              miembro={m}
              pregunta={pregunta}
              opciones={opciones}
              valor={valor}
              aplica={ap.aplica}
              motivo={ap.motivo}
              soloLectura={soloLectura}
              onChange={(v) => onChange(pregunta.id, v, m.id)}
            />
          );
        })}
      </View>
    </View>
  );
}

const PreguntaPersonaItem = memo(PreguntaPersonaItemBase, (prev, next) =>
  prev.pregunta === next.pregunta &&
  prev.index === next.index &&
  prev.total === next.total &&
  prev.opciones === next.opciones &&
  prev.miembros === next.miembros &&
  prev.respuestas === next.respuestas &&
  prev.soloLectura === next.soloLectura &&
  prev.aplicabilidad === next.aplicabilidad,
);

function PreguntaItemBase({
  pregunta,
  index,
  total,
  opciones,
  valor,
  soloLectura,
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
  soloLectura?: boolean;
  onChange: (v: string) => void;
  iaActivo?: boolean;
  onTextoIA?: (texto: string) => void;
  sugerenciaActiva?: import('../../../src/api/ia').MapearAudioResponse | null;
  onAceptarIA?: () => void;
  onRechazarIA?: () => void;
}) {
  const tieneRespuesta = !!valor?.trim();
  const esObligatoria  = pregunta.obligatoria === 1;

  // Modo SOLO LECTURA — datos del RUV (hecho victimizante). Se muestra el valor
  // precargado, sin controles editables ni asistente de voz. Si el RUV no trajo
  // el dato, se indica explícitamente en vez de mostrar un campo vacío.
  if (soloLectura) {
    const esOpcion = pregunta.tipo === 'RADIO' || pregunta.tipo === 'LISTA'
      || pregunta.tipo === 'BOOLEAN' || pregunta.tipo === 'LISTA_MULTIPLE';
    const etiqueta = esOpcion
      ? (opciones.find((o) => o.valor === valor)?.etiqueta ?? valor)
      : valor;
    return (
      <View style={[styles.preguntaCard, styles.preguntaCardRuv]}>
        <View style={styles.preguntaHeader}>
          <MaterialCommunityIcons name="shield-check" size={16} color={GOV.azul} />
          <Text style={styles.ruvBadgeTxt}>Dato del RUV</Text>
          {pregunta.no_pregunta ? (
            <Text style={styles.codigoTxt}>{pregunta.no_pregunta}</Text>
          ) : null}
        </View>
        <Text style={styles.textoPregunta}>{pregunta.texto}</Text>
        <View style={styles.ruvValorBox}>
          <MaterialCommunityIcons name="lock-outline" size={15} color={GOV.textoS} />
          <Text style={styles.ruvValorTxt}>
            {etiqueta?.trim() ? etiqueta : 'Sin dato registrado en el RUV'}
          </Text>
        </View>
      </View>
    );
  }

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

      {/* Controles por tipo — delega en ControlInput (compartido con las filas
          por miembro de las preguntas PERSONA). */}
      <ControlInput pregunta={pregunta} opciones={opciones} valor={valor} onChange={onChange} />
    </View>
  );
}

// #23/#34 — memoizar evita re-renderizar TODAS las tarjetas en cada pulsación de
// tecla (setRespuestasState re-renderiza el padre). Las callbacks envoltorio
// cambian de identidad cada render pero solo reenvían a useCallbacks estables
// (setRespuesta, handleAceptarSugerencia…), así que se comparan solo las props
// de DATOS. La presencia (no la identidad) de las callbacks IA sí importa.
const PreguntaItem = memo(PreguntaItemBase, (prev, next) =>
  prev.pregunta === next.pregunta &&
  prev.valor === next.valor &&
  prev.soloLectura === next.soloLectura &&
  prev.index === next.index &&
  prev.total === next.total &&
  prev.opciones === next.opciones &&
  prev.iaActivo === next.iaActivo &&
  prev.sugerenciaActiva === next.sugerenciaActiva &&
  !!prev.onTextoIA === !!next.onTextoIA &&
  !!prev.onAceptarIA === !!next.onAceptarIA,
);

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
  sinPreguntas: { textAlign: 'center', ...FONT.body, color: GOV.textoT, marginTop: SPACING.xl },

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

  // Captura agrupada — progreso por persona dentro de una pregunta PERSONA
  personaProgreso: {
    ...FONT.caption,
    color: GOV.textoS,
    marginBottom: SPACING.sm,
    fontStyle: 'italic',
  },

  // Captura agrupada — contenedor de las filas por miembro
  filasWrap: { gap: SPACING.sm, marginTop: 2 },
  filaMiembro: {
    backgroundColor: GOV.fondoApp,
    borderRadius: RADIUS.sm,
    padding: SPACING.sm,
    borderWidth: 1,
    borderColor: GOV.borde,
    borderLeftWidth: 3,
    borderLeftColor: GOV.borde,
    gap: SPACING.xs,
  },
  filaMiembroOk: { borderLeftColor: GOV.verde },
  filaMiembroHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.xs,
  },
  filaMiembroNombre: { ...FONT.label, color: GOV.textoP, flex: 1, fontWeight: '700' },
  filaMiembroNombreInactivo: { ...FONT.label, color: GOV.textoT, flex: 1 },
  noAplicaBox: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.xs,
    paddingVertical: 2,
  },
  noAplicaTxt: { ...FONT.caption, color: GOV.textoT, flex: 1, fontStyle: 'italic' },

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
  // Tarjeta de pregunta en modo solo-lectura (dato precargado del RUV).
  preguntaCardRuv: {
    borderLeftColor: GOV.azul,
    backgroundColor: GOV.azulTenue,
  },
  ruvBadgeTxt: { ...FONT.label, color: GOV.azulOscuro },
  ruvValorBox: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.xs,
    backgroundColor: GOV.superficie,
    borderWidth: 1,
    borderColor: GOV.borde,
    borderRadius: RADIUS.sm,
    paddingHorizontal: SPACING.sm,
    paddingVertical: 10,
    marginTop: 2,
  },
  ruvValorTxt: { ...FONT.body, fontWeight: '600', color: GOV.textoP, flex: 1 },
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
