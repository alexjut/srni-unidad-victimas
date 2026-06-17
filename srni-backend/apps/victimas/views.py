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
from apps.autenticacion.throttles import BusquedaRNIThrottle
from apps.auditoria.models import LogAcceso
from .models import Victima
from .serializers import (
    VictimaListSerializer, VictimaDetalleSerializer, BusquedaDocumentoSerializer,
    ConsultarFuenteInputSerializer, ResultadoBusquedaSerializer,
    RegistrarDesdeFuenteSerializer,
)
from .fields import sha256_hash
from .repository import get_repository


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
    throttle_classes = [BusquedaRNIThrottle]   # 30 búsquedas/hora por usuario

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

        # Incluir info del hogar activo si ya existe — el cliente decide
        # si mostrar "Continuar caracterización" o "Crear hogar".
        from apps.hogares.models import Hogar

        # Solo adjuntamos como hogar_activo uno que el usuario PUEDA abrir.
        # Para no-admin filtramos por creado_por: un hogar de otro encuestador
        # daría 404 al intentar abrirlo (get_queryset filtra creado_por), así
        # que no lo exponemos aquí como si fuera navegable.
        hogares_qs = (
            Hogar.objects
            .filter(autorizado=victima)
            .exclude(estado='ARCHIVADO')
        )
        if not request.user.puede('administrar'):
            hogares_qs = hogares_qs.filter(creado_por=request.user)

        hogar_activo = hogares_qs.order_by('-created_at').first()

        data = VictimaListSerializer(victima).data
        data['hogar_activo'] = (
            {
                'id': str(hogar_activo.id),
                'estado': hogar_activo.estado,
                'total_miembros': hogar_activo.miembros.count(),
                'total_sesiones': hogar_activo.sesiones.count(),
            }
            if hogar_activo else None
        )
        return Response(data)


@extend_schema(
    summary='Consultar víctima en fuente externa (RUV / Oracle)',
    description=(
        'Busca a la persona en el repositorio externo (RUV, Oracle SNARIV o Mock). '
        'Retorna habilitado_para_caracterizacion y, si corresponde, los hechos victimizantes '
        'y datos para conformar el hogar. '
        'Este endpoint NO consulta la DB local SRNI — usa el VictimaRepository configurado '
        'en settings.VICTIMA_REPOSITORY.'
    ),
    tags=['Víctimas'],
    request=ConsultarFuenteInputSerializer,
    responses={200: ResultadoBusquedaSerializer},
)
class ConsultarFuenteView(APIView):
    """
    POST /api/victimas/consultar-fuente/

    Requiere permiso puede_buscar_rni.
    Toda consulta queda registrada en LogAcceso.
    """
    permission_classes = [IsAuthenticated, PuedeBuscarRNI]

    def post(self, request):
        serializer = ConsultarFuenteInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tipo = serializer.validated_data['tipo_documento']
        numero = serializer.validated_data['numero_documento']
        ip = _ip_de_request(request)
        ua = request.META.get('HTTP_USER_AGENT', '')

        repo = get_repository()
        resultado = repo.buscar_por_documento(tipo, numero)

        LogAcceso.registrar(
            usuario=request.user,
            accion='CONSULTA_FUENTE_EXTERNA',
            recurso='VictimaRepository',
            recurso_id=None,
            ip=ip,
            user_agent=ua,
            resultado='EXITO',
            detalle={
                'encontrado': resultado.encontrado,
                'fuente': resultado.fuente,
                'tipo_documento': tipo,
                'habilitado': (
                    resultado.victima.habilitado_para_caracterizacion
                    if resultado.victima else None
                ),
            },
        )

        return Response(ResultadoBusquedaSerializer(resultado).data)


@extend_schema(
    summary='Obtener grupo familiar desde fuente externa',
    description=(
        'Retorna los integrantes del grupo familiar registrados en el RUV/Oracle '
        'para el consecutivo Oracle indicado (cons_persona). '
        'Requiere que la búsqueda previa haya retornado cons_persona.'
    ),
    tags=['Víctimas'],
    responses={200: ResultadoBusquedaSerializer(many=True)},
)
class GrupoFamiliarView(APIView):
    """
    GET /api/victimas/grupo-familiar/{cons_persona}/

    Requiere permiso puede_caracterizar.
    """
    permission_classes = [IsAuthenticated, PuedeCaracterizar]

    def get(self, request, cons_persona: int):
        repo = get_repository()
        miembros = repo.obtener_grupo_familiar(cons_persona)

        from .serializers import VictimaResumenSerializer
        return Response(VictimaResumenSerializer(miembros, many=True).data)


@extend_schema(
    summary='Registrar o actualizar víctima desde fuente externa',
    description=(
        'Recibe los datos de una VictimaResumen DTO proveniente del repositorio externo '
        '(RUV / Oracle / Mock) y realiza un upsert en la tabla local Victima. '
        'Busca por hash SHA-256 del número de documento + tipo de documento. '
        'Retorna el UUID local del registro y si fue creado (created=true) o actualizado.'
    ),
    tags=['Víctimas'],
    request=RegistrarDesdeFuenteSerializer,
    responses={
        200: {'type': 'object', 'properties': {
            'victima_id': {'type': 'string', 'format': 'uuid'},
            'created': {'type': 'boolean'},
        }},
    },
)
class RegistrarDesdeFuenteView(APIView):
    """
    POST /api/victimas/registrar-desde-fuente/

    Hace upsert de Victima usando (numero_documento_hash, tipo_documento) como clave.
    Requiere permiso puede_buscar_rni.
    Toda operación queda registrada en LogAcceso.
    """
    permission_classes = [IsAuthenticated, PuedeBuscarRNI]

    def post(self, request):
        serializer = RegistrarDesdeFuenteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        ip = _ip_de_request(request)
        ua = request.META.get('HTTP_USER_AGENT', '')

        # 1. Resolver TipoDocumento
        from apps.parametricas.models import TipoDocumento, Municipio
        try:
            tipo_doc = TipoDocumento.objects.get(codigo=data['tipo_documento'])
        except TipoDocumento.DoesNotExist:
            return Response(
                {'detail': f"Tipo de documento '{data['tipo_documento']}' no existe en el catálogo."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 2. Calcular hash del número de documento
        hash_doc = sha256_hash(data['numero_documento'])

        # 3. Buscar registro existente o preparar uno nuevo
        try:
            victima = Victima.objects.get(
                numero_documento_hash=hash_doc,
                tipo_documento=tipo_doc,
            )
            created = False
        except Victima.DoesNotExist:
            victima = Victima(
                tipo_documento=tipo_doc,
                numero_documento=data['numero_documento'],
                creado_por=request.user,
            )
            created = True

        # 4. Actualizar campos (tanto en creación como en actualización)
        victima.cons_persona = data.get('cons_persona')
        victima.primer_nombre = data['primer_nombre']
        victima.segundo_nombre = data.get('segundo_nombre', '')
        victima.primer_apellido = data['primer_apellido']
        victima.segundo_apellido = data.get('segundo_apellido', '')
        # fecha_nacimiento viene como objeto date; EncryptedField almacena texto
        victima.fecha_nacimiento = str(data['fecha_nacimiento'])
        victima.genero = data['genero']
        victima.estado_ruv = data['estado_ruv']
        victima.habilitado_para_caracterizacion = data['habilitado_para_caracterizacion']
        victima.pertenencia_etnica = data.get('pertenencia_etnica', 'NINGUNA')
        victima.pueblo_indigena = data.get('pueblo_indigena', '')
        victima.discapacidad = data.get('discapacidad', False)
        victima.tipo_discapacidad = data.get('tipo_discapacidad', '')
        victima.fuente_origen = data.get('fuente_origen', 'RUV')

        # 5. Resolver municipio de residencia (no es error si no existe)
        codigo_mun = data.get('municipio_residencia_codigo')
        if codigo_mun:
            try:
                victima.municipio_residencia = Municipio.objects.get(codigo_dane=codigo_mun)
            except Municipio.DoesNotExist:
                victima.municipio_residencia = None
        else:
            victima.municipio_residencia = None

        victima.save()

        # 6. Auditoría
        LogAcceso.registrar(
            usuario=request.user,
            accion='REGISTRAR_VICTIMA_FUENTE_EXTERNA',
            recurso='Victima',
            recurso_id=str(victima.id),
            ip=ip,
            user_agent=ua,
            resultado='EXITO',
            detalle={
                'created': created,
                'tipo_documento': data['tipo_documento'],
                'fuente_origen': victima.fuente_origen,
            },
        )

        return Response(
            {'victima_id': str(victima.id), 'created': created},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )
