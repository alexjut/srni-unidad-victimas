"""
Views de Víctimas — búsqueda segura por hash SHA-256 del documento.

Seguridad:
- El número de documento NUNCA viaja en query params (evita logs de Nginx/proxy).
- La búsqueda se hace via POST con body cifrado en tránsito (HTTPS).
- Toda búsqueda queda registrada en LogAcceso (auditoría inmutable).
- Los listados usan VictimaListSerializer (sin PII).
- El detalle usa VictimaDetalleSerializer solo con permiso puede_caracterizar.
"""
import json
import os

from django.conf import settings
from django.http import FileResponse, Http404
from django.utils import timezone
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
    RegistrarDesdeFuenteSerializer, VictimaResumenSerializer, PadronItemSerializer,
)
from .repository.base import doc_hash
from .repository import get_repository


def _ip_de_request(request) -> str:
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


# ---------------------------------------------------------------------------
# Padrón offline descargable (Fase B) — helpers
# ---------------------------------------------------------------------------
# El archivo y el manifiesto los genera el command `generar_padron`
# (apps/victimas/management/commands/generar_padron.py). Estas vistas solo
# LEEN ese resultado; no consultan el repositorio en cada request.

_PADRON_DIRNAME = 'padron'
_MANIFIESTO_NOMBRE = 'padron-latest.json'


def _padron_dir() -> str:
    return os.path.join(str(settings.MEDIA_ROOT), _PADRON_DIRNAME)


def _leer_manifiesto():
    """Lee padron-latest.json. Devuelve dict o None si aún no se ha generado."""
    ruta = os.path.join(_padron_dir(), _MANIFIESTO_NOMBRE)
    if not os.path.exists(ruta):
        return None
    try:
        with open(ruta, 'r', encoding='utf-8') as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None


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
        409: {'description': (
            'Documento ambiguo: varios registros lo comparten. El body trae '
            '`candidatos` (todos los registros) y `ambiguo: true`. La UI DEBE pedir '
            'confirmación en vez de asumir el primero.'
        )},
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
        # Una sola definición del hash, la de repository.base (ver Victima.save).
        # Además de unificar, `doc_hash` normaliza puntos, guiones y espacios: con la
        # fórmula anterior, "1.030.547.250" y "1030547250" eran personas distintas.
        hash_doc = doc_hash(tipo_codigo, numero)

        ip = _ip_de_request(request)
        ua = request.META.get('HTTP_USER_AGENT', '')

        coincidencias = list(Victima.objects.select_related(
            'tipo_documento',
            'municipio_residencia__departamento',
        ).filter(
            numero_documento_hash=hash_doc,
            tipo_documento__codigo=tipo_codigo,
        ))

        # Antes esto era un `.get()` y reventaba con 500 cuando el documento estaba
        # repetido: 768.096 documentos del padrón lo están (~15,6 % de las búsquedas
        # posibles), verificado contra prod el 2-ago. No se elige uno por regla —
        # pueden ser dos personas distintas, y mostrar a una como si fuera la única
        # es el riesgo de "datos de otra persona, en silencio". Se devuelven todos y
        # confirma el encuestador, que tiene a la persona enfrente.
        if len(coincidencias) > 1:
            LogAcceso.registrar(
                usuario=request.user,
                accion='BUSQUEDA_RNI',
                recurso='Victima',
                recurso_id=None,
                ip=ip,
                user_agent=ua,
                resultado='EXITO',
                detalle={
                    'encontrado': True,
                    'ambiguo': True,
                    'coincidencias': len(coincidencias),
                    'tipo_documento': tipo_codigo,
                },
            )
            return Response(
                {
                    'detail': (
                        f'Hay {len(coincidencias)} registros con este documento. '
                        f'CONFIRME cuál corresponde antes de caracterizar.'
                    ),
                    'ambiguo': True,
                    'candidatos': VictimaListSerializer(coincidencias, many=True).data,
                },
                status=status.HTTP_409_CONFLICT,
            )

        if coincidencias:
            victima = coincidencias[0]
        else:
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

        # 2. Calcular hash del número de documento (misma definición que la búsqueda:
        #    si el upsert hashea distinto que el buscador, se crean duplicados)
        hash_doc = doc_hash(data['tipo_documento'], data['numero_documento'])

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


def _nombre_completo(v) -> str:
    """Arma el nombre completo de un VictimaResumen omitiendo partes vacías."""
    partes = [v.primer_nombre, v.segundo_nombre, v.primer_apellido, v.segundo_apellido]
    return ' '.join(p for p in partes if p)


@extend_schema(
    summary='Precarga de datos para trabajo offline',
    description=(
        'Devuelve en UNA sola llamada todo lo que la APK necesita para operar sin '
        'conexión durante una jornada: el padrón resumido de víctimas, el detalle '
        'completo (resumen-fuente) de cada víctima para precargar el formulario, y '
        'las paramétricas (municipios, direcciones territoriales, puntos de atención). '
        'Fuente: VictimaRepository configurado (Mock en Fase 0). Requiere permiso de '
        'caracterización.'
    ),
    tags=['Víctimas'],
    responses={200: {'type': 'object', 'properties': {
        'version': {'type': 'string'},
        'padron': {'type': 'array', 'items': {'type': 'object'}},
        'jornada': {'type': 'array', 'items': {'type': 'object'}},
        'parametricas': {'type': 'object'},
    }}},
)
class PrecargaOfflineView(APIView):
    """
    GET /api/victimas/precarga/

    Habilitador del modo offline. Requiere permiso puede_caracterizar.

    ⚠️ El tope NO es negociable
    ---------------------------
    Esta vista nació contra el mock, donde `listar_todas()` devolvía 11 personas.
    Al activar el padrón real (1-ago-2026) esa misma llamada pasó a pedir
    **5.926.004** — serializarlas revienta la memoria del proceso y agota el
    timeout de 30 s de la APK sin devolver nada. El login quedaría colgado.

    Por eso siempre se pasa `LIMITE`. No es una optimización: es lo que hace que
    el endpoint responda.

    El padrón completo **no viaja por aquí**: se descarga como archivo SQLite
    prearmado desde `padron/download/` (ver `generar_padron`), que es el diseño
    offline-first de verdad. Este endpoint es el arranque rápido de la jornada.
    """
    permission_classes = [IsAuthenticated, PuedeCaracterizar]

    #: Techo de personas en la precarga. Sale de `settings` para poder subirlo o
    #: bajarlo sin desplegar, pero nunca debe quedar en `None`.
    LIMITE = getattr(settings, "PRECARGA_LIMITE_PERSONAS", 5000)

    def get(self, request):
        repo = get_repository()
        victimas = repo.listar_todas(limite=self.LIMITE)

        # --- padron: resumen mínimo, sin detalle de hechos ---
        padron = [
            {
                'tipo_documento': v.tipo_documento,
                'documento': v.numero_documento,
                'nombre': _nombre_completo(v),
                'ubicacion': v.municipio_residencia_nombre,
                'cantidad_hechos': len(v.hechos_victimizantes or []),
                'en_ruv': v.estado_ruv == 'INCLUIDO',
                'habilitada': v.habilitado_para_caracterizacion,
                # Fase 0: la caracterización no está en la fuente externa, así que no
                # podemos derivarla barato desde el repo. Se reporta False; la APK
                # tratará 'habilitada' como la señal operativa. Cuando exista Oracle se
                # poblará desde fecha_ult_caracterizacion.
                'ya_caracterizada': bool(v.fecha_ult_caracterizacion),
                'cons_persona': v.cons_persona,
            }
            for v in victimas
        ]

        padron = PadronItemSerializer(padron, many=True).data

        # --- jornada: resumen-fuente COMPLETO de cada víctima (mismo shape que .victima) ---
        jornada = VictimaResumenSerializer(victimas, many=True).data

        # --- parametricas: tablas de referencia desde la BD local ---
        from apps.parametricas.models import (
            Municipio, DireccionTerritorial, PuntoAtencion,
        )
        from apps.parametricas.serializers import (
            DireccionTerritorialSerializer, PuntoAtencionSerializer,
        )

        municipios = [
            {
                'codigo_dane': m.codigo_dane,
                'nombre': m.nombre,
                'departamento': m.departamento.nombre,
            }
            for m in Municipio.objects.select_related('departamento').filter(activo=True)
        ]
        direcciones = DireccionTerritorialSerializer(
            DireccionTerritorial.objects.prefetch_related('departamentos').filter(activo=True),
            many=True,
        ).data
        puntos = PuntoAtencionSerializer(
            PuntoAtencion.objects.select_related('municipio', 'direccion_territorial').filter(activo=True),
            many=True,
        ).data

        # Fase B: si ya existe un padrón-archivo generado (command generar_padron),
        # adjuntamos su referencia SIN quitar el `padron` inline. La app mobile
        # ACTUAL sigue usando el inline; en una fase posterior migrará a descargar
        # el archivo vía /padron/download/ usando esta referencia para decidir si
        # debe re-descargar (compara `version`/`checksum` con su copia local).
        manifiesto = _leer_manifiesto()
        padron_archivo = None
        if manifiesto:
            padron_archivo = {
                'version': manifiesto.get('version'),
                'checksum': manifiesto.get('checksum'),
                'total_registros': manifiesto.get('total_registros'),
                'formato': manifiesto.get('formato'),
                'url': request.build_absolute_uri('/api/victimas/padron/download/'),
            }

        payload = {
            # version: ISO con tz (no datetime.now sin tz). Sirve a la APK para saber
            # si su copia local está vigente frente al servidor.
            'version': timezone.now().isoformat(),
            'padron': padron,
            # Referencia al padrón descargable (Fase B). None si aún no se generó.
            'padron_archivo': padron_archivo,
            'jornada': jornada,
            'parametricas': {
                'municipios': municipios,
                'direcciones_territoriales': direcciones,
                'puntos_atencion': puntos,
            },
        }

        LogAcceso.registrar(
            usuario=request.user,
            accion='PRECARGA_OFFLINE',
            recurso='VictimaRepository',
            recurso_id=None,
            ip=_ip_de_request(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            resultado='EXITO',
            detalle={
                'total_padron': len(padron),
                'total_jornada': len(jornada),
                'total_municipios': len(municipios),
                'fuente': getattr(repo, 'FUENTE', 'DESCONOCIDA'),
            },
        )

        return Response(payload)


# ---------------------------------------------------------------------------
# Fase B — Padrón offline descargable, versionado y con ETag
# ---------------------------------------------------------------------------

@extend_schema(
    summary='Versión/manifiesto del padrón offline descargable',
    description=(
        'Devuelve el manifiesto del padrón offline generado por el command '
        '`generar_padron`: version, checksum (sha256 del archivo), total de '
        'registros, formato y URL de descarga. La APK lo consulta para decidir '
        'si debe re-descargar el archivo (compara version/checksum con su copia '
        'local). Requiere permiso de caracterización.'
    ),
    tags=['Víctimas'],
    responses={200: {'type': 'object', 'properties': {
        'version': {'type': 'string'},
        'checksum': {'type': 'string'},
        'total_registros': {'type': 'integer'},
        'generado_en': {'type': 'string', 'format': 'date-time'},
        'formato': {'type': 'string'},
        'archivo': {'type': 'string'},
        'url': {'type': 'string'},
    }}},
)
class PadronVersionView(APIView):
    """
    GET /api/victimas/padron/version/

    Lee el manifiesto generado por `generar_padron`. Si aún no se ha generado,
    responde 404 con un mensaje explicativo (no es un error de servidor).
    """
    permission_classes = [IsAuthenticated, PuedeCaracterizar]

    def get(self, request):
        manifiesto = _leer_manifiesto()
        if manifiesto is None:
            return Response(
                {'detail': 'El padrón offline aún no ha sido generado. '
                           'Ejecute el command generar_padron.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        data = dict(manifiesto)
        data['url'] = request.build_absolute_uri('/api/victimas/padron/download/')

        LogAcceso.registrar(
            usuario=request.user,
            accion='PRECARGA_OFFLINE',
            recurso='PadronOffline',
            recurso_id=manifiesto.get('version', ''),
            ip=_ip_de_request(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            resultado='EXITO',
            detalle={'operacion': 'version', 'checksum': manifiesto.get('checksum')},
        )
        return Response(data)


@extend_schema(
    summary='Descargar el archivo del padrón offline',
    description=(
        'Sirve el archivo del padrón offline (SQLite indexado por doc_hash). '
        'Soporta caché condicional vía ETag = checksum sha256 del archivo: si el '
        'cliente envía If-None-Match con el checksum actual, responde 304 sin '
        'cuerpo. Requiere permiso de caracterización.'
    ),
    tags=['Víctimas'],
    responses={
        200: {'description': 'Archivo del padrón (application/octet-stream).'},
        304: {'description': 'No modificado — el ETag coincide.'},
        404: {'description': 'El padrón aún no ha sido generado.'},
    },
)
class PadronDownloadView(APIView):
    """
    GET /api/victimas/padron/download/

    Entrega el archivo del padrón con ETag = checksum. Responde 304 si el
    If-None-Match del cliente coincide con el checksum actual.

    Nota despliegue: el archivo del mock es pequeño y se sirve con FileResponse.
    Para padrones grandes (Oracle) conviene delegar el envío del archivo a Nginx
    (X-Accel-Redirect) tras esta misma verificación de permisos/ETag — ver
    apps/movil/views.descargar como referencia del patrón de redirección.
    """
    permission_classes = [IsAuthenticated, PuedeCaracterizar]

    def get(self, request):
        manifiesto = _leer_manifiesto()
        if manifiesto is None:
            return Response(
                {'detail': 'El padrón offline aún no ha sido generado. '
                           'Ejecute el command generar_padron.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        checksum = manifiesto.get('checksum', '')
        archivo_nombre = manifiesto.get('archivo', '')
        archivo_path = os.path.join(_padron_dir(), archivo_nombre)

        if not archivo_nombre or not os.path.exists(archivo_path):
            return Response(
                {'detail': 'El archivo del padrón referenciado por el manifiesto no existe.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # ETag entre comillas (RFC 7232). Comparamos contra If-None-Match.
        etag = f'"{checksum}"'
        if_none_match = request.META.get('HTTP_IF_NONE_MATCH', '')
        # El cliente puede mandar varios ETags separados por coma; normalizamos.
        enviados = {t.strip() for t in if_none_match.split(',')} if if_none_match else set()
        no_modificado = etag in enviados or checksum in enviados

        ip = _ip_de_request(request)
        ua = request.META.get('HTTP_USER_AGENT', '')

        if no_modificado:
            LogAcceso.registrar(
                usuario=request.user,
                accion='PRECARGA_OFFLINE',
                recurso='PadronOffline',
                recurso_id=manifiesto.get('version', ''),
                ip=ip,
                user_agent=ua,
                resultado='EXITO',
                detalle={'operacion': 'download', 'status': 304, 'checksum': checksum},
            )
            resp = Response(status=status.HTTP_304_NOT_MODIFIED)
            resp['ETag'] = etag
            return resp

        LogAcceso.registrar(
            usuario=request.user,
            accion='PRECARGA_OFFLINE',
            recurso='PadronOffline',
            recurso_id=manifiesto.get('version', ''),
            ip=ip,
            user_agent=ua,
            resultado='EXITO',
            detalle={
                'operacion': 'download', 'status': 200,
                'checksum': checksum, 'total_registros': manifiesto.get('total_registros'),
            },
        )

        resp = FileResponse(
            open(archivo_path, 'rb'),
            content_type='application/octet-stream',
            as_attachment=True,
            filename=archivo_nombre,
        )
        resp['ETag'] = etag
        return resp
