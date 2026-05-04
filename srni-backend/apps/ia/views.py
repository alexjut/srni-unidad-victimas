"""
Views del módulo IA — Asistente de voz Gemini.

Endpoints:
  POST /api/ia/consentimiento/   → registrar consentimiento antes de activar IA
  GET  /api/ia/estado/           → consultar estado IA para una sesión
  POST /api/ia/mapear-audio/     → proxy hacia Gemini (texto → valor campo)

Seguridad:
  - Todos requieren PuedeCaracterizar.
  - mapear-audio exige consentimiento activo para esa sesión.
  - Toda llamada a Gemini queda en LogAcceso.
"""
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from apps.autenticacion.permissions import PuedeCaracterizar
from apps.auditoria.models import LogAcceso
from apps.encuestas.models import SesionEncuesta
from apps.formulario.models import Pregunta

from .models import ConsentimientoIA, SesionIA
from .serializers import (
    ConsentimientoIAInputSerializer,
    ConsentimientoIASerializer,
    MapearAudioInputSerializer,
    MapearAudioOutputSerializer,
    EstadoIASerializer,
)
from .services import mapear_texto_a_campo, hash_texto, GeminiError


def _ip(request) -> str:
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    return xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR', '')


class ConsentimientoIAView(APIView):
    """
    POST /api/ia/consentimiento/

    Registra el consentimiento del encuestador para usar la IA en una sesión.
    Solo se permite un consentimiento activo (acepto=True) por sesión.
    """
    permission_classes = [IsAuthenticated, PuedeCaracterizar]

    @extend_schema(
        request=ConsentimientoIAInputSerializer,
        responses={201: ConsentimientoIASerializer},
        summary='Registrar consentimiento IA',
        tags=['IA'],
    )
    def post(self, request):
        ser = ConsentimientoIAInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        sesion_id = ser.validated_data['sesion_encuesta_id']
        acepto = ser.validated_data['acepto']

        # Verificar que la sesión existe y pertenece al encuestador
        try:
            sesion = SesionEncuesta.objects.get(
                pk=sesion_id, encuestador=request.user
            )
        except SesionEncuesta.DoesNotExist:
            return Response(
                {'detail': 'Sesión no encontrada o no autorizada.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        consentimiento = ConsentimientoIA.objects.create(
            sesion_encuesta=sesion,
            encuestador=request.user,
            acepto=acepto,
        )

        LogAcceso.registrar(
            accion='CONSENTIMIENTO_IA',
            ip=_ip(request),
            usuario=request.user,
            recurso='SesionEncuesta',
            recurso_id=str(sesion_id),
            resultado='EXITO',
            detalle={'acepto': acepto},
        )

        return Response(
            ConsentimientoIASerializer(consentimiento).data,
            status=status.HTTP_201_CREATED,
        )


class EstadoIAView(APIView):
    """
    GET /api/ia/estado/?sesion_encuesta_id=<uuid>

    Devuelve si la IA está activa para la sesión indicada.
    """
    permission_classes = [IsAuthenticated, PuedeCaracterizar]

    @extend_schema(
        responses={200: EstadoIASerializer},
        summary='Estado IA para una sesión',
        tags=['IA'],
    )
    def get(self, request):
        sesion_id = request.query_params.get('sesion_encuesta_id')
        if not sesion_id:
            return Response(
                {'detail': 'Parámetro sesion_encuesta_id requerido.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        consentimiento = (
            ConsentimientoIA.objects.filter(
                sesion_encuesta_id=sesion_id,
                encuestador=request.user,
                acepto=True,
            )
            .order_by('-creado_en')
            .first()
        )

        sesion_ia = None
        total_llamadas = 0
        if consentimiento:
            try:
                sesion_ia = SesionIA.objects.get(sesion_encuesta_id=sesion_id)
                total_llamadas = sesion_ia.total_llamadas
            except SesionIA.DoesNotExist:
                pass

        data = {
            'activo': consentimiento is not None,
            'consentimiento_id': consentimiento.id if consentimiento else None,
            'sesion_ia_id': sesion_ia.id if sesion_ia else None,
            'total_llamadas': total_llamadas,
        }
        return Response(EstadoIASerializer(data).data)


class MapearAudioView(APIView):
    """
    POST /api/ia/mapear-audio/

    Recibe texto transcrito + contexto de la pregunta,
    llama a Gemini y devuelve el valor sugerido para el campo.

    Requiere consentimiento activo para esa sesión.
    """
    permission_classes = [IsAuthenticated, PuedeCaracterizar]

    @extend_schema(
        request=MapearAudioInputSerializer,
        responses={200: MapearAudioOutputSerializer},
        summary='Mapear audio transcrito → valor de campo (proxy Gemini)',
        tags=['IA'],
    )
    def post(self, request):
        ser = MapearAudioInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        sesion_id = ser.validated_data['sesion_encuesta_id']
        pregunta_id = ser.validated_data['pregunta_id']
        texto = ser.validated_data['texto_transcrito']

        # 1. Verificar consentimiento activo
        consentimiento_activo = ConsentimientoIA.objects.filter(
            sesion_encuesta_id=sesion_id,
            encuestador=request.user,
            acepto=True,
        ).exists()

        if not consentimiento_activo:
            return Response(
                {'detail': 'Se requiere consentimiento activo para usar la IA.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        # 2. Verificar que la sesión pertenece al encuestador
        try:
            SesionEncuesta.objects.get(pk=sesion_id, encuestador=request.user)
        except SesionEncuesta.DoesNotExist:
            return Response(
                {'detail': 'Sesión no encontrada o no autorizada.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 3. Obtener datos de la pregunta
        try:
            pregunta = Pregunta.objects.prefetch_related('opciones').get(pk=pregunta_id)
        except Pregunta.DoesNotExist:
            return Response(
                {'detail': 'Pregunta no encontrada.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        opciones = list(pregunta.opciones.values_list('valor', flat=True))

        # 4. Llamar a Gemini via servicio
        resultado_log = 'EXITO'
        detalle_log: dict = {'pregunta_id': str(pregunta_id), 'tipo': pregunta.tipo}

        try:
            resultado = mapear_texto_a_campo(
                texto_transcrito=texto,
                tipo_campo=pregunta.tipo,
                enunciado_pregunta=pregunta.texto,
                opciones=opciones if opciones else None,
            )
        except GeminiError as exc:
            resultado_log = 'ERROR'
            detalle_log['error'] = str(exc)
            LogAcceso.registrar(
                accion='LLAMADA_GEMINI',
                ip=_ip(request),
                usuario=request.user,
                recurso='Pregunta',
                recurso_id=str(pregunta_id),
                resultado=resultado_log,
                detalle=detalle_log,
            )
            return Response(
                {'detail': 'El servicio de IA no está disponible. Continúa de forma manual.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # 5. Actualizar SesionIA (crear si no existe) y LogAcceso
        sesion_ia, _ = SesionIA.objects.get_or_create(sesion_encuesta_id=sesion_id)
        SesionIA.objects.filter(pk=sesion_ia.pk).update(
            total_llamadas=sesion_ia.total_llamadas + 1,
            transcripcion_hash=hash_texto(
                (sesion_ia.transcripcion_hash or '') + texto
            ),
        )

        detalle_log['confianza'] = resultado['confianza']
        LogAcceso.registrar(
            accion='LLAMADA_GEMINI',
            ip=_ip(request),
            usuario=request.user,
            recurso='Pregunta',
            recurso_id=str(pregunta_id),
            resultado=resultado_log,
            detalle=detalle_log,
        )

        return Response(MapearAudioOutputSerializer(resultado).data)
