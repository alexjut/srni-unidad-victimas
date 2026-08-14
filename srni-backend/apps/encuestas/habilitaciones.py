"""
Habilitaciones de excepción de vigencia — el recurso que consume el front web.

─── Qué resuelve ────────────────────────────────────────────────────────────
Una persona con ficha vigente no se puede recaracterizar (regla de los dos
años, Manual §5.1.1). Tres rutas la omiten, pero exigen un soporte: un fallo,
una tutela, un auto de seguimiento.

Hasta el 14-ago-2026 ese soporte se adjuntaba **como foto desde el celular**, y
la excepción la registraba el mismo encuestador que iba a usarla. La operación
indicó que el caracterizador no debe tener ese documento —le llega al nivel
central por canal institucional—, así que la autorización se mudó acá: se
otorga desde el front, por un perfil con `puede_autorizar_excepciones`, y el
celular solo la consume.

─── El flujo completo ───────────────────────────────────────────────────────
    1. El encuestador encuentra la ficha vigente y no puede continuar.
       La app le dice que solicite la excepción a su coordinación.
    2. Coordinación recibe el soporte por el canal institucional y crea la
       habilitación acá:  POST /api/habilitaciones/
    3. La persona queda habilitada. El celular lo ve en la precarga de la
       jornada siguiente, o en la búsqueda si tiene señal.
    4. Al finalizar la caracterización, la habilitación se consume
       (`estado='USADA'`). No queda un permiso abierto.

Anular una habilitación no la borra: `POST /api/habilitaciones/{id}/anular/`
la marca `ANULADA` con quién y por qué. Una autorización otorgada y retirada es
justamente lo que una auditoría necesita poder ver.
"""
import logging

from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.auditoria.models import LogAcceso
from apps.auditoria.red import ip_de_request
from apps.autenticacion.permissions import PuedeAutorizarExcepciones
from apps.victimas.homologacion import RUTAS_QUE_OMITEN_VIGENCIA

from .models import ExcepcionVigencia

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------

class HabilitacionSerializer(serializers.ModelSerializer):
    """Salida. Lo que el front necesita para listar y para confirmar."""

    ruta_display = serializers.CharField(source='get_ruta_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    victima_documento = serializers.CharField(
        source='victima.numero_documento', read_only=True)
    victima_nombre = serializers.SerializerMethodField()
    autorizada_por_codigo = serializers.CharField(
        source='autorizada_por.codigo_usuario', read_only=True, default='')

    class Meta:
        model = ExcepcionVigencia
        fields = [
            'id', 'victima', 'victima_documento', 'victima_nombre',
            'ruta', 'ruta_display', 'radicado', 'observacion',
            'estado', 'estado_display',
            'fecha_ult_caracterizacion', 'vigente_hasta',
            'soporte_nombre', 'autorizada_por', 'autorizada_por_codigo',
            'created_at', 'usada_at', 'anulada_at', 'motivo_anulacion',
        ]
        read_only_fields = fields

    def get_victima_nombre(self, obj) -> str:
        v = obj.victima
        partes = [getattr(v, 'primer_nombre', ''), getattr(v, 'primer_apellido', '')]
        return ' '.join(p for p in partes if p).strip()


class CrearHabilitacionSerializer(serializers.Serializer):
    """
    Entrada del front al autorizar.

    El archivo es opcional a propósito (decidido el 14-ago): quien autoriza
    suele tener el PDF, pero exigirlo dejaría fuera los casos que llegan por
    correo o por teléfono. Lo que **sí** es obligatorio es el par
    radicado + motivo: sin ellos, "hubo una tutela" no se puede verificar
    contra nada después.
    """

    victima_id = serializers.UUIDField()
    ruta = serializers.CharField(max_length=30)
    radicado = serializers.CharField(max_length=100)
    observacion = serializers.CharField(max_length=2_000)
    soporte = serializers.FileField(required=False, allow_null=True)

    def validate_ruta(self, value):
        ruta = (value or '').strip().upper()
        if ruta not in RUTAS_QUE_OMITEN_VIGENCIA:
            raise serializers.ValidationError(
                f"La ruta '{value}' no omite la regla de vigencia. Solo la omiten: "
                f"{', '.join(sorted(RUTAS_QUE_OMITEN_VIGENCIA))}. La ruta general la "
                f"respeta, así que no hay excepción que autorizar."
            )
        return ruta

    def validate_radicado(self, value):
        radicado = (value or '').strip()
        if not radicado:
            raise serializers.ValidationError(
                'El radicado del soporte es obligatorio: es lo que permite ir a '
                'buscar el documento después.'
            )
        return radicado

    def validate_observacion(self, value):
        motivo = (value or '').strip()
        if len(motivo) < 10:
            raise serializers.ValidationError(
                'Escriba el motivo de la excepción (mínimo 10 caracteres). Es lo '
                'que queda como justificación de haber levantado la regla.'
            )
        return motivo


class AnularHabilitacionSerializer(serializers.Serializer):
    motivo = serializers.CharField(max_length=2_000)

    def validate_motivo(self, value):
        motivo = (value or '').strip()
        if len(motivo) < 10:
            raise serializers.ValidationError(
                'Indique por qué se anula (mínimo 10 caracteres).'
            )
        return motivo


# ---------------------------------------------------------------------------
# ViewSet
# ---------------------------------------------------------------------------

@extend_schema_view(
    list=extend_schema(tags=['Habilitaciones'],
                       description='Habilitaciones de excepción de vigencia.'),
    retrieve=extend_schema(tags=['Habilitaciones']),
)
class HabilitacionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Habilitaciones para caracterizar sobre ficha vigente.

    Lectura para cualquier perfil autorizado; crear y anular exige
    `puede_autorizar_excepciones`. El encuestador **no** entra acá: su app solo
    ve el resultado, en la búsqueda y en la precarga.
    """

    serializer_class = HabilitacionSerializer
    permission_classes = [IsAuthenticated, PuedeAutorizarExcepciones]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['estado', 'ruta', 'victima']
    ordering_fields = ['created_at', 'estado']
    ordering = ['-created_at']

    def get_queryset(self):
        return (ExcepcionVigencia.objects
                .select_related('victima', 'autorizada_por')
                .all())

    @extend_schema(
        tags=['Habilitaciones'],
        request=CrearHabilitacionSerializer,
        responses={201: HabilitacionSerializer},
        description=(
            'Autoriza la actualización de una caracterización vigente. La '
            'persona queda habilitada hasta que se use o se anule.'
        ),
    )
    def create(self, request, *args, **kwargs):
        from apps.victimas.models import Victima
        from apps.victimas.repository.base import describir_elegibilidad

        serializer = CrearHabilitacionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        datos = serializer.validated_data

        try:
            victima = Victima.objects.get(pk=datos['victima_id'])
        except Victima.DoesNotExist:
            return Response({'detail': 'La víctima indicada no existe.'},
                            status=status.HTTP_404_NOT_FOUND)

        # Una excluida del RUV no se habilita por ninguna ruta: el manual prevé
        # la excepción para fichas vigentes, no para revertir una decisión del
        # RUV. Sin esta guarda, el front podría otorgar una habilitación que la
        # app después ignora, y nadie entendería por qué.
        if getattr(victima, 'estado_ruv', '') == 'EXCLUIDO':
            return Response(
                {'detail': 'Persona excluida del RUV — no elegible para '
                           'caracterización. Ninguna ruta de excepción habilita '
                           'este caso.'},
                status=status.HTTP_409_CONFLICT)

        # Se pasa `habilitacion=None` para preguntar por el estado REAL: si no,
        # una habilitación ya existente haría ver a la persona como elegible y
        # el bloque de abajo nunca detectaría la duplicada.
        veredicto = describir_elegibilidad(victima, habilitacion=None)

        vigente = ExcepcionVigencia.vigente_para(victima.id)
        if vigente is not None:
            return Response(
                {'detail': 'Esta persona ya tiene una habilitación vigente.',
                 'habilitacion': HabilitacionSerializer(vigente).data},
                status=status.HTTP_409_CONFLICT)

        with transaction.atomic():
            soporte = datos.get('soporte')
            habilitacion = ExcepcionVigencia.objects.create(
                victima=victima,
                ruta=datos['ruta'],
                radicado=datos['radicado'],
                observacion=datos['observacion'],
                # Se congela la situación al momento de autorizar. Si se
                # referenciara, al recaracterizar cambiaría la fecha de la
                # víctima y se perdería la razón por la que se autorizó.
                fecha_ult_caracterizacion=(
                    victima.fecha_ult_caracterizacion.date()
                    if getattr(victima.fecha_ult_caracterizacion, 'date', None)
                    else victima.fecha_ult_caracterizacion),
                vigente_hasta=veredicto.disponible_desde,
                soporte=soporte,
                soporte_nombre=getattr(soporte, 'name', '')[:255] if soporte else '',
                autorizada_por=request.user,
                estado=ExcepcionVigencia.VIGENTE,
            )

            LogAcceso.registrar(
                accion='HABILITAR_EXCEPCION',
                usuario=request.user,
                ip=ip_de_request(request),
                recurso='ExcepcionVigencia',
                recurso_id=habilitacion.id,
                detalle={
                    'victima_id': str(victima.id),
                    'ruta': habilitacion.ruta,
                    'radicado': habilitacion.radicado,
                    'ficha_vigente_hasta': str(veredicto.disponible_desde or ''),
                },
            )

        logger.info('habilitacion de excepcion %s creada por %s sobre victima %s',
                    habilitacion.id, request.user, victima.id)
        return Response(HabilitacionSerializer(habilitacion).data,
                        status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=['Habilitaciones'],
        request=AnularHabilitacionSerializer,
        responses={200: HabilitacionSerializer},
        description='Deja sin efecto una habilitación que todavía no se usó.',
    )
    @action(detail=True, methods=['post'])
    def anular(self, request, pk=None):
        habilitacion = self.get_object()
        serializer = AnularHabilitacionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not habilitacion.anular(request.user, serializer.validated_data['motivo']):
            return Response(
                {'detail': f'No se puede anular: la habilitación está '
                           f'{habilitacion.get_estado_display()}.'},
                status=status.HTTP_409_CONFLICT)

        LogAcceso.registrar(
            accion='ANULAR_EXCEPCION',
            usuario=request.user,
            ip=ip_de_request(request),
            recurso='ExcepcionVigencia',
            recurso_id=habilitacion.id,
            detalle={
                'victima_id': str(habilitacion.victima_id),
                'motivo': habilitacion.motivo_anulacion,
            },
        )
        return Response(HabilitacionSerializer(habilitacion).data)
