"""
Views de Víctimas — búsqueda segura por hash SHA-256 del documento.

Seguridad:
- El número de documento NUNCA viaja en query params (evita logs de Nginx/proxy).
- La búsqueda se hace via POST con body cifrado en tránsito (HTTPS).
- Toda búsqueda queda registrada en LogAcceso (auditoría inmutable).
- Los listados usan VictimaListSerializer (sin PII).
- El detalle usa VictimaDetalleSerializer solo con permiso puede_caracterizar.
"""
from rest_framework import mixins, viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, extend_schema_view

from apps.autenticacion.permissions import PuedeBuscarRNI, PuedeCaracterizar
from apps.auditoria.models import LogAcceso
from .models import Victima
from .serializers import (
    VictimaListSerializer, VictimaDetalleSerializer, BusquedaDocumentoSerializer,
)
from .fields import sha256_hash


def _ip_de_request(request) -> str:
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


@extend_schema_view(
    retrieve=extend_schema(
        summary='Detalle de víctima (requiere permiso caracterizar)',
        tags=['Víctimas'],
    ),
)
class VictimaViewSet(
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    Solo expone detalle por UUID — nunca listado global.
    Requiere permiso puede_caracterizar.
    """
    permission_classes = [IsAuthenticated, PuedeCaracterizar]
    serializer_class = VictimaDetalleSerializer

    def get_queryset(self):
        return Victima.objects.select_related(
            'tipo_documento',
            'municipio_residencia__departamento',
            'creado_por',
        ).all()

    def retrieve(self, request, *args, **kwargs):
        victima = self.get_object()
        LogAcceso.registrar(
            usuario=request.user,
            accion='VER_VICTIMA',
            recurso='Victima',
            recurso_id=str(victima.id),
            ip=_ip_de_request(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            resultado='EXITO',
        )
        serializer = self.get_serializer(victima)
        return Response(serializer.data)


@extend_schema(
    summary='Buscar víctima por documento',
    description=(
        'Recibe tipo y número de documento en el body (HTTPS). '
        'El backend calcula el hash SHA-256 y consulta el índice — '
        'el número de documento nunca se almacena en logs.'
    ),
    tags=['Víctimas'],
    request=BusquedaDocumentoSerializer,
    responses={
        200: VictimaListSerializer,
        404: {'description': 'Víctima no encontrada en el sistema'},
    },
)
class BuscarVictimaView(APIView):
    """
    Búsqueda segura por número de documento.
    Requiere permiso puede_buscar_rni.
    """
    permission_classes = [IsAuthenticated, PuedeBuscarRNI]

    def post(self, request):
        serializer = BusquedaDocumentoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tipo_codigo = serializer.validated_data['tipo_documento_codigo']
        numero = serializer.validated_data['numero_documento']
        hash_doc = sha256_hash(numero)

        ip = _ip_de_request(request)
        ua = request.META.get('HTTP_USER_AGENT', '')

        try:
            victima = Victima.objects.select_related(
                'tipo_documento',
                'municipio_residencia__departamento',
            ).get(
                numero_documento_hash=hash_doc,
                tipo_documento__codigo=tipo_codigo,
            )
        except Victima.DoesNotExist:
            LogAcceso.registrar(
                usuario=request.user,
                accion='BUSQUEDA_RNI',
                recurso='Victima',
                recurso_id=None,
                ip=ip,
                user_agent=ua,
                resultado='EXITO',
                detalle={'encontrado': False, 'tipo_documento': tipo_codigo},
            )
            return Response(
                {'detail': 'No se encontró ninguna víctima con ese documento.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        LogAcceso.registrar(
            usuario=request.user,
            accion='BUSQUEDA_RNI',
            recurso='Victima',
            recurso_id=str(victima.id),
            ip=ip,
            user_agent=ua,
            resultado='EXITO',
            detalle={'encontrado': True, 'tipo_documento': tipo_codigo},
        )
        return Response(VictimaListSerializer(victima).data)
