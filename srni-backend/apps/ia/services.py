"""
Servicio de integración con Gemini API.

Reglas de seguridad:
- La clave API solo existe en el backend (nunca en la app móvil).
- El audio nunca llega aquí: el móvil envía texto ya transcrito.
- Toda llamada queda registrada en LogAcceso (acción LLAMADA_GEMINI).
- Timeout de 10 s — si falla, se propaga GeminiError y el formulario sigue funcionando.
"""
import hashlib
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

try:
    import google.generativeai as genai
except ImportError:
    genai = None  # type: ignore[assignment]


class GeminiError(Exception):
    """Error recuperable en la llamada a Gemini."""


# Tipos de campo que el backend conoce (espejo del instrumento)
_TIPOS_CAMPO = {
    'TEXTO', 'NUMERICO', 'FECHA', 'LISTA', 'LISTA_MULTIPLE',
    'RADIO', 'BOOLEAN', 'TEXTO_LARGO', 'COMBO_DINAMICO',
}

_SYSTEM_PROMPT = """Eres un asistente de caracterización de víctimas del conflicto armado colombiano,
parte del Sistema de Registro Nacional de Información (SRNI) de la Unidad para las Víctimas.

Tu única función es interpretar una respuesta oral transcrita y extraer el valor exacto
que debe guardarse en el campo del formulario PAARI.

Reglas estrictas:
1. Responde SOLO con el valor del campo, sin explicaciones, sin comillas, sin formato adicional.
2. Para campos de tipo LISTA o RADIO, devuelve exactamente una de las opciones válidas.
3. Para BOOLEAN, devuelve "true" o "false".
4. Para NUMERICO, devuelve solo dígitos (sin puntos, sin comas, sin unidades).
5. Para FECHA, devuelve en formato YYYY-MM-DD.
6. Para LISTA_MULTIPLE, devuelve los valores separados por comas.
7. Si no puedes extraer un valor con confianza, devuelve la cadena vacía "".
8. Nunca inventes datos ni completes información no mencionada explícitamente.
9. Respeta la privacidad: no repitas datos personales en tu respuesta.
"""


def mapear_texto_a_campo(
    *,
    texto_transcrito: str,
    tipo_campo: str,
    enunciado_pregunta: str,
    opciones: list[str] | None = None,
) -> dict:
    """
    Llama a Gemini para mapear el texto transcrito al valor del campo.

    Args:
        texto_transcrito: Lo que dijo el encuestado/encuestador, ya transcrito.
        tipo_campo: Tipo del campo del formulario (LISTA, NUMERICO, BOOLEAN, etc.).
        enunciado_pregunta: Texto de la pregunta en el instrumento.
        opciones: Lista de valores válidos (solo para LISTA, RADIO, LISTA_MULTIPLE).

    Returns:
        {'sugerencia': str, 'confianza': float, 'modelo': str}

    Raises:
        GeminiError: Si Gemini no responde o devuelve error.
    """
    if genai is None:
        raise GeminiError('google-generativeai no está instalado.')

    api_key = getattr(settings, 'GEMINI_API_KEY', None)
    if not api_key:
        raise GeminiError('GEMINI_API_KEY no configurado en settings.')

    genai.configure(api_key=api_key)

    # Construir el prompt de usuario
    partes = [
        f'Pregunta del formulario: {enunciado_pregunta}',
        f'Tipo de campo: {tipo_campo}',
    ]
    if opciones:
        partes.append(f'Opciones válidas: {", ".join(opciones)}')
    partes.append(f'Respuesta oral transcrita: {texto_transcrito}')
    partes.append('Valor a guardar en el campo:')

    prompt_usuario = '\n'.join(partes)

    try:
        model = genai.GenerativeModel(
            model_name='gemini-1.5-flash',
            system_instruction=_SYSTEM_PROMPT,
            generation_config={
                'temperature': 0.1,   # baja temperatura = más determinista
                'max_output_tokens': 200,
                'candidate_count': 1,
            },
        )
        respuesta = model.generate_content(
            prompt_usuario,
            request_options={'timeout': 10},
        )
        sugerencia = (respuesta.text or '').strip()

        # Calcular confianza heurística: si la sugerencia es una opción válida exacta → 1.0
        confianza = 1.0
        if opciones and sugerencia and sugerencia not in opciones:
            confianza = 0.6  # sugirió algo pero no es opción válida exacta

        return {
            'sugerencia': sugerencia,
            'confianza': confianza,
            'modelo': 'gemini-1.5-flash',
        }

    except Exception as exc:
        logger.error('Error llamando a Gemini: %s', exc, exc_info=True)
        raise GeminiError(f'Error en Gemini: {exc}') from exc


def hash_texto(texto: str) -> str:
    """SHA-256 del texto — para almacenar en SesionIA.transcripcion_hash."""
    return hashlib.sha256(texto.encode()).hexdigest()


# ─── Batch: procesar entrevista completa ──────────────────────────────────────

_BATCH_SYSTEM_PROMPT = """Eres un asistente de caracterización de víctimas del conflicto armado colombiano,
parte del Sistema de Registro Nacional de Información (SRNI) de la Unidad para las Víctimas.

Tu función es analizar una entrevista transcrita y extraer los valores exactos
que deben guardarse en cada campo del formulario PAARI.

Reglas estrictas:
1. Responde ÚNICAMENTE con un arreglo JSON válido, sin texto adicional, sin bloques de código.
2. Para campos LISTA, RADIO o COMBO_DINAMICO: devuelve el "valor" exacto de la opción (no el texto de la etiqueta).
3. Para BOOLEAN: devuelve "true" o "false".
4. Para NUMERICO: devuelve solo dígitos (sin puntos, sin comas, sin unidades).
5. Para FECHA: devuelve en formato YYYY-MM-DD.
6. Para LISTA_MULTIPLE: devuelve los valores separados por comas.
7. Para TEXTO o TEXTO_LARGO: devuelve el fragmento textual relevante de la entrevista.
8. Si no puedes extraer un valor con confianza para una pregunta, devuelve null en "sugerencia" y 0.0 en "confianza".
9. Nunca inventes datos ni completes información no mencionada explícitamente.
10. El campo "razonamiento" debe ser breve (máx. 30 palabras) y en español.
"""


def procesar_entrevista_batch(
    transcripcion: str,
    preguntas: list[dict],
) -> list[dict]:
    """
    Envía la transcripción completa + todas las preguntas de un capítulo a Gemini
    y obtiene sugerencias en bloque.

    Args:
        transcripcion: Texto completo de la entrevista transcrita.
        preguntas: Lista de dicts con claves:
            pregunta_id (str UUID), codigo_externo (str), texto (str),
            tipo (str), opciones (list[str] — valores válidos).

    Returns:
        Lista de dicts con claves:
            pregunta_id (str), codigo_externo (str), sugerencia (str|None),
            confianza (float), razonamiento (str).

    Raises:
        GeminiError: Si Gemini no responde, falla o devuelve JSON inválido.
    """
    if genai is None:
        raise GeminiError('google-generativeai no está instalado.')

    api_key = getattr(settings, 'GEMINI_API_KEY', None)
    if not api_key:
        raise GeminiError('GEMINI_API_KEY no configurado en settings.')

    genai.configure(api_key=api_key)

    # Construir la lista de preguntas para el prompt
    preguntas_txt_partes = []
    for p in preguntas:
        parte = (
            f'- pregunta_id: {p["pregunta_id"]}\n'
            f'  codigo: {p["codigo_externo"]}\n'
            f'  tipo: {p["tipo"]}\n'
            f'  texto: {p["texto"]}'
        )
        if p.get('opciones'):
            parte += f'\n  opciones_validas: {", ".join(p["opciones"])}'
        preguntas_txt_partes.append(parte)

    preguntas_bloque = '\n'.join(preguntas_txt_partes)

    prompt_usuario = (
        f'TRANSCRIPCIÓN DE ENTREVISTA:\n{transcripcion}\n\n'
        f'PREGUNTAS A RESPONDER:\n{preguntas_bloque}\n\n'
        'Devuelve un arreglo JSON con un objeto por cada pregunta, en el mismo orden, '
        'con estas claves: "pregunta_id", "codigo_externo", "sugerencia", "confianza", "razonamiento".'
    )

    try:
        model = genai.GenerativeModel(
            model_name='gemini-1.5-flash',
            system_instruction=_BATCH_SYSTEM_PROMPT,
            generation_config={
                'temperature': 0.1,
                'max_output_tokens': 8192,
                'candidate_count': 1,
                'response_mime_type': 'application/json',
            },
        )
        respuesta = model.generate_content(
            prompt_usuario,
            request_options={'timeout': 30},
        )
    except Exception as exc:
        logger.error('Error llamando a Gemini (batch): %s', exc, exc_info=True)
        raise GeminiError(f'Error en Gemini batch: {exc}') from exc

    # Parsear JSON de la respuesta
    import json  # noqa: PLC0415 — import local para no contaminar el módulo si json no se usa
    texto_respuesta = (respuesta.text or '').strip()
    try:
        resultados_raw = json.loads(texto_respuesta)
    except (json.JSONDecodeError, ValueError) as exc:
        logger.error('Gemini batch devolvió JSON inválido: %s', texto_respuesta[:500])
        raise GeminiError(f'Gemini devolvió respuesta no parseable: {exc}') from exc

    if not isinstance(resultados_raw, list):
        raise GeminiError('Gemini batch no devolvió una lista JSON.')

    # Construir mapa pregunta_id → pregunta para validar opciones
    mapa_opciones: dict[str, list[str]] = {
        str(p['pregunta_id']): p.get('opciones', []) for p in preguntas
    }
    mapa_codigos: dict[str, str] = {
        str(p['pregunta_id']): p['codigo_externo'] for p in preguntas
    }

    resultados: list[dict] = []
    for item in resultados_raw:
        pid = str(item.get('pregunta_id', ''))
        codigo = item.get('codigo_externo') or mapa_codigos.get(pid, '')
        sugerencia = item.get('sugerencia')
        if sugerencia is not None:
            sugerencia = str(sugerencia).strip() or None
        confianza = float(item.get('confianza', 0.0))
        razonamiento = str(item.get('razonamiento', '')).strip()

        # Ajustar confianza: si la opción sugerida no es válida para LISTA/RADIO → penalizar
        opciones_validas = mapa_opciones.get(pid, [])
        if opciones_validas and sugerencia and sugerencia not in opciones_validas:
            confianza = min(confianza, 0.4)

        resultados.append({
            'pregunta_id': pid,
            'codigo_externo': codigo,
            'sugerencia': sugerencia,
            'confianza': max(0.0, min(1.0, confianza)),
            'razonamiento': razonamiento,
        })

    return resultados
