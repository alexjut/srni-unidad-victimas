"""
Bloque 5 — Guardado de respuesta con limpieza de derivadas fuera de flujo.

PORT de GIC_N_CARACTERIZACION.SP_SET_RESPUESTAS_DE_ENCUESTA (package body líneas 4-73):

    IF FN_VERIFICARRESPUESTA(...) = FALSE OR pOrden = 1 THEN   -- la respuesta cambió
        IF pbANDera = 1 THEN
            SP_BORRADORESPUESTAS(pregunta_padre => pper_idPreguntaPadre, ...);  -- borra derivadas
        END IF;
        INSERT INTO GIC_N_RESPUESTASENCUESTA (...);            -- guarda la respuesta
    END IF;
    IF pbANDera = 1 THEN
        SP_BORRADOVALIDADORES(pregunta_padre => ...);          -- borra validadores del padre
    END IF;
    IF pValidador <> 0 THEN
        INSERT INTO GIC_N_VALIDADORESXPERSONA (...);           -- resuelve validador de la respuesta
    END IF;

MAPEO A DJANGO:
- "La respuesta cambió" (FN_VERIFICARRESPUESTA) → comparamos el valor nuevo contra
  el guardado; solo si cambia (o es la primera) recalculamos derivadas.
- Upsert de RespuestaEncuesta (unique por sesion+pregunta+miembro) = el INSERT.
- SP_BORRADORESPUESTAS (borrar respuestas derivadas de la pregunta que cambió) se
  porta reevaluando el skip-logic: si una pregunta afectada por reglas cuya ORIGEN
  es la pregunta que cambió queda OCULTA con el nuevo valor, se borra su respuesta
  (quedaría fuera de flujo). Reutiliza el motor declarativo ReglaSkipLogic ya
  existente (misma lógica que EvaluarSkipLogicView._regla_activa).

DIVERGENCIA CONSCIENTE (ver reporte de paridad):
- La rama de "validadores" (GIC_N_VALIDADORESXPERSONA / SP_BORRADOVALIDADORES) NO
  tiene modelo Django equivalente: en este backend la obligatoriedad/validación se
  computa on-read por el motor skip-logic (acción OBLIGAR) y no se materializa por
  persona. Por eso NO se porta esa rama en esta fase (pertenece a la fase de
  escritura a Oracle). Se documenta explícitamente, no es un olvido.
- La limpieza se hace UN nivel (hijos directos de la pregunta que cambió), igual que
  el proc opera sobre `pper_idPreguntaPadre`.
"""
from dataclasses import dataclass, field


@dataclass
class ResultadoGuardarRespuesta:
    respuesta: "object"
    creada: bool
    cambio: bool
    limpiadas: list = field(default_factory=list)  # códigos de preguntas cuya respuesta se borró


def _trigger_se_cumple(regla, valor: str) -> bool:
    """
    Mirror de EvaluarSkipLogicView._regla_activa para el caso de origen por
    respuesta directa (soporta selección única y múltiple).
    """
    from apps.formulario.views import _valores_seleccionados

    if regla.pregunta_origen_id is None:
        return False  # reglas por expresión de contexto no las gatilla este cambio
    if not regla.valor_trigger:
        return bool(valor)
    seleccionados = _valores_seleccionados(valor)
    triggers = [v.strip() for v in regla.valor_trigger.split(",")]
    return any(t in seleccionados for t in triggers)


def _afectada_queda_oculta(regla, valor: str) -> bool:
    """
    Con el nuevo `valor` de la pregunta origen, ¿la pregunta afectada por esta
    regla queda oculta (y por tanto su respuesta debe borrarse)?

    - HABILITAR que YA NO se cumple  → afectada oculta.
    - DESHABILITAR que ahora se cumple → afectada oculta.
    """
    from apps.formulario.models import AccionSkipChoices

    if regla.pregunta_afectada_id is None:
        return False
    activa = _trigger_se_cumple(regla, valor)
    if regla.accion == AccionSkipChoices.HABILITAR and not activa:
        return True
    if regla.accion == AccionSkipChoices.DESHABILITAR and activa:
        return True
    return False


def guardar_respuesta(*, sesion, pregunta, valor: str, miembro=None) -> ResultadoGuardarRespuesta:
    """
    Upsert de una respuesta + limpieza de derivadas fuera de flujo.

    Devuelve ResultadoGuardarRespuesta con la respuesta, si se creó/cambió y la
    lista de códigos de preguntas cuyas respuestas se borraron por quedar fuera
    de flujo.
    """
    from apps.formulario.models import ReglaSkipLogic
    from apps.encuestas.models import RespuestaEncuesta

    # ¿Cambió el valor? (FN_VERIFICARRESPUESTA)
    existente = RespuestaEncuesta.objects.filter(
        sesion=sesion, pregunta=pregunta, miembro=miembro
    ).first()
    cambio = existente is None or existente.valor != valor

    if existente is None:
        respuesta = RespuestaEncuesta.objects.create(
            sesion=sesion, pregunta=pregunta, miembro=miembro, valor=valor
        )
        creada = True
    else:
        creada = False
        if cambio:
            existente.valor = valor
            existente.save(update_fields=["valor", "updated_at"])
        respuesta = existente

    limpiadas = []
    if cambio:
        # SP_BORRADORESPUESTAS: borra respuestas de preguntas que dependen de ésta
        # y que quedan fuera de flujo con el nuevo valor.
        reglas = ReglaSkipLogic.objects.filter(
            instrumento=sesion.instrumento, pregunta_origen=pregunta
        ).select_related("pregunta_afectada")
        for regla in reglas:
            if _afectada_queda_oculta(regla, valor):
                afectada = regla.pregunta_afectada
                qs = RespuestaEncuesta.objects.filter(sesion=sesion, pregunta=afectada)
                # Respuestas PERSONA: acotar al mismo miembro; HOGAR: miembro NULL.
                if miembro is not None:
                    qs = qs.filter(miembro=miembro)
                n, _ = qs.delete()
                if n:
                    limpiadas.append(afectada.codigo_externo)

    return ResultadoGuardarRespuesta(
        respuesta=respuesta, creada=creada, cambio=cambio, limpiadas=limpiadas
    )
