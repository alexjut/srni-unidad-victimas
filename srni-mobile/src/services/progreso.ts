/**
 * Progreso offline por capítulo — fix #8/#18 (auditoría APK 2026-06-21).
 *
 * El conteo ESTÁTICO de obligatorias (contarPreguntasPorCapitulo) incluye
 * preguntas obligatorias OCULTAS por skip-logic (reglas HABILITAR que aún no
 * se disparan). Esas obligatorias nunca pueden responderse → el denominador
 * queda inflado y el progreso NUNCA llega a 100%.
 *
 * Este módulo calcula el progreso REAL evaluando la visibilidad con
 * calcularVisibles() contra el estado actual de respuestas del borrador. Es el
 * mismo cálculo que hace la pantalla de capítulo ([temaId].tsx); centralizado
 * aquí para que el hub (formulario/index) y el capítulo coincidan EXACTAMENTE.
 *
 * Reglas de conteo (espejo de [temaId].tsx):
 *   - Denominador = obligatorias estáticas que están VISIBLES dado el estado.
 *   - HOGAR: la visibilidad no depende del miembro → una evaluación.
 *   - PERSONA: la visibilidad depende de las respuestas de CADA miembro →
 *     se evalúa por miembro y se suma.
 */
import type { CapituloRow, PreguntaRow, ReglaSkipLogicRow } from '../db/instrumentoDao';
import { calcularVisibles, type ContextoVictima } from './skipLogic';

export interface ProgresoCapitulo {
  obligVisibles: number; // obligatorias visibles (denominador real)
  obligRespondidas: number; // de esas, respondidas (numerador)
  estado: 'pendiente' | 'en_progreso' | 'completado';
}

export interface MiembroRef {
  id: string;
  /** Para evaluar las reglas por expresión (edad/sexo/RUV). Ver contextoDe(). */
  genero?: string;
  fecha_nacimiento?: string | null;
  incluido_ruv?: boolean;
  es_autorizado?: boolean;
}

export interface ProgresoGlobal {
  porCapitulo: Record<string, ProgresoCapitulo>;
  obligVisibles: number;
  obligRespondidas: number;
  capsCompletados: number;
  capsConObligatorias: number;
  progreso: number; // 0..1
}

/**
 * Contexto demográfico de un integrante — edad, sexo, etnia y RUV.
 *
 * Sin esto, las reglas por expresión (`sexo == '2' and edad >= 12`) no se
 * evaluaban nunca acá y el denominador salía mal: el bloque de gestación
 * desaparecía de la cuenta y la barra decía 100 % con la entrevista incompleta.
 *
 * Mismo criterio que la pantalla de captura (`construirContextoMiembro` en
 * formulario/[temaId].tsx) y que el backend (`contexto_para` en
 * SesionEncuesta.recalcular_porcentaje). Los tres tienen que decidir igual: si
 * el hub contara distinto de lo que el capítulo muestra, el encuestador vería
 * un progreso que no corresponde con lo que tiene delante.
 *
 * Lo que NO se hereda del padrón es deliberado: el género de allí acierta la
 * mitad de las veces (join roto, ver docs/oracle-legacy/) y la etnia se
 * pregunta, no se hereda. Sin dato, la variable queda `undefined` y la regla no
 * dispara — no afirma nada.
 */
function contextoDe(miembro: MiembroRef, respMiembro: Record<string, string>): ContextoVictima {
  const edadResp = respMiembro.B9 ? Number(respMiembro.B9) : NaN;
  let edad = Number.isFinite(edadResp) ? edadResp : NaN;
  if (!Number.isFinite(edad)) {
    const nac = respMiembro.A6 || miembro.fecha_nacimiento || '';
    const f = nac ? new Date(nac) : null;
    if (f && !Number.isNaN(f.getTime())) {
      const hoy = new Date();
      edad = hoy.getFullYear() - f.getFullYear();
      const m = hoy.getMonth() - f.getMonth();
      if (m < 0 || (m === 0 && hoy.getDate() < f.getDate())) edad--;
    }
  }

  let sexo = respMiembro.A8 || '';
  const genero = miembro.genero || '';
  if (!sexo && genero) sexo = genero === 'M' ? '1' : genero === 'F' ? '2' : '';

  return {
    edad: Number.isFinite(edad) && edad >= 0 && edad < 130 ? edad : undefined,
    sexo: sexo || undefined,
    etnia: 'ninguno',
    ruvIncluido: miembro.incluido_ruv ?? false,
  };
}

/** Construye codigo_externo→valor para evaluar skip-logic en el contexto de un miembro. */
function mapaParaMiembro(
  preguntas: Pick<PreguntaRow, 'id' | 'codigo_externo' | 'nivel'>[],
  respuestasCompuesto: Record<string, string>,
  miembroId: string,
): Record<string, string> {
  const m: Record<string, string> = {};
  for (const p of preguntas) {
    const clave = p.nivel === 'PERSONA' ? `${p.id}|${miembroId}` : `${p.id}|`;
    m[p.codigo_externo] = respuestasCompuesto[clave] ?? '';
  }
  return m;
}

/**
 * Calcula el progreso de TODO el instrumento a partir del borrador local.
 *
 * @param respuestasCompuesto mapa `pregunta_id|miembro_id` → valor
 *   (de borradoresDao.getRespuestaMapCompuesto). HOGAR usa `pregunta_id|`.
 */
export function calcularProgresoOffline(
  capitulos: CapituloRow[],
  getPreguntas: (capId: string) => PreguntaRow[],
  reglas: ReglaSkipLogicRow[],
  miembros: MiembroRef[],
  respuestasCompuesto: Record<string, string>,
): ProgresoGlobal {
  const porCapitulo: Record<string, ProgresoCapitulo> = {};
  // Al menos un "miembro fantasma" para que las preguntas PERSONA cuenten
  // aunque aún no se hayan capturado integrantes (espejo de Math.max(N, 1)).
  const efectivos: MiembroRef[] = miembros.length > 0 ? miembros : [{ id: '' }];

  let gVis = 0;
  let gResp = 0;
  let completados = 0;
  let conOblig = 0;

  for (const cap of capitulos) {
    const preguntas = getPreguntas(cap.id);

    // HOGAR: la visibilidad no depende del miembro, pero las reglas demográficas
    // sí necesitan a alguien. Se usa el AUTORIZADO —igual que la pantalla de
    // capítulo— y no «el primero de la lista»: si no, el mismo hogar daría dos
    // progresos distintos según el orden en que vinieran los integrantes.
    const refHogar = efectivos.find((m) => m.es_autorizado) ?? efectivos[0];
    const mapaHogar = mapaParaMiembro(preguntas, respuestasCompuesto, refHogar.id);
    const visH = calcularVisibles(preguntas, reglas, mapaHogar, contextoDe(refHogar, mapaHogar));
    const obligHogar = preguntas.filter(
      (p) => p.nivel === 'HOGAR' && p.obligatoria === 1 && !p.es_precargada && visH.visibles.has(p.codigo_externo),
    );

    let obligVisibles = obligHogar.length;
    let obligRespondidas = 0;
    for (const p of obligHogar) {
      if (respuestasCompuesto[`${p.id}|`]?.trim()) obligRespondidas++;
    }

    // PERSONA: la visibilidad depende de las respuestas de cada miembro.
    for (const miembro of efectivos) {
      const mapaM = mapaParaMiembro(preguntas, respuestasCompuesto, miembro.id);
      const visP = calcularVisibles(preguntas, reglas, mapaM, contextoDe(miembro, mapaM));
      const obligPersona = preguntas.filter(
        (p) => p.nivel === 'PERSONA' && p.obligatoria === 1 && !p.es_precargada && visP.visibles.has(p.codigo_externo),
      );
      obligVisibles += obligPersona.length;
      for (const p of obligPersona) {
        if (respuestasCompuesto[`${p.id}|${miembro.id}`]?.trim()) obligRespondidas++;
      }
    }

    let estado: ProgresoCapitulo['estado'] = 'pendiente';
    if (obligVisibles > 0 && obligRespondidas >= obligVisibles) estado = 'completado';
    else if (obligRespondidas > 0) estado = 'en_progreso';

    porCapitulo[cap.id] = { obligVisibles, obligRespondidas, estado };

    gVis += obligVisibles;
    gResp += Math.min(obligRespondidas, obligVisibles);
    if (obligVisibles > 0) {
      conOblig++;
      if (obligRespondidas >= obligVisibles) completados++;
    }
  }

  return {
    porCapitulo,
    obligVisibles: gVis,
    obligRespondidas: gResp,
    capsCompletados: completados,
    capsConObligatorias: conOblig,
    progreso: gVis > 0 ? gResp / gVis : 0,
  };
}
