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
import { calcularVisibles } from './skipLogic';

export interface ProgresoCapitulo {
  obligVisibles: number; // obligatorias visibles (denominador real)
  obligRespondidas: number; // de esas, respondidas (numerador)
  estado: 'pendiente' | 'en_progreso' | 'completado';
}

export interface MiembroRef {
  id: string;
}

export interface ProgresoGlobal {
  porCapitulo: Record<string, ProgresoCapitulo>;
  obligVisibles: number;
  obligRespondidas: number;
  capsCompletados: number;
  capsConObligatorias: number;
  progreso: number; // 0..1
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

    // HOGAR: la visibilidad no depende del miembro → una sola evaluación.
    const visH = calcularVisibles(
      preguntas,
      reglas,
      mapaParaMiembro(preguntas, respuestasCompuesto, efectivos[0].id),
    );
    const obligHogar = preguntas.filter(
      (p) => p.nivel === 'HOGAR' && p.obligatoria === 1 && visH.visibles.has(p.codigo_externo),
    );

    let obligVisibles = obligHogar.length;
    let obligRespondidas = 0;
    for (const p of obligHogar) {
      if (respuestasCompuesto[`${p.id}|`]?.trim()) obligRespondidas++;
    }

    // PERSONA: la visibilidad depende de las respuestas de cada miembro.
    for (const miembro of efectivos) {
      const visP = calcularVisibles(
        preguntas,
        reglas,
        mapaParaMiembro(preguntas, respuestasCompuesto, miembro.id),
      );
      const obligPersona = preguntas.filter(
        (p) => p.nivel === 'PERSONA' && p.obligatoria === 1 && visP.visibles.has(p.codigo_externo),
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
