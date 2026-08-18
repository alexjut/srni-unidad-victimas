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
import re

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


class CrearHabilitacionLoteSerializer(CrearHabilitacionSerializer):
    """
    Igual que la individual pero sobre varias personas, con el MISMO soporte.

    Hereda para que las reglas de radicado y motivo no se escriban dos veces: el
    día que cambie el mínimo del motivo, cambia en los dos caminos o en ninguno.
    """

    victima_id = None            # se reemplaza por la lista
    victima_ids = serializers.ListField(
        child=serializers.UUIDField(), min_length=1, max_length=200)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop('victima_id', None)


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

    #: Tope de documentos por búsqueda. Existe para que un pegado accidental de
    #: media planilla no se lleve por delante la consulta ni la pantalla.
    MAX_DOCUMENTOS_BUSQUEDA = 200

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

        serializer = CrearHabilitacionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        datos = serializer.validated_data

        try:
            victima = Victima.objects.get(pk=datos['victima_id'])
        except Victima.DoesNotExist:
            return Response({'detail': 'La víctima indicada no existe.'},
                            status=status.HTTP_404_NOT_FOUND)

        habilitacion, problema = self._autorizar_una(victima, datos, request)
        if problema is not None:
            return Response(problema, status=status.HTTP_409_CONFLICT)

        return Response(HabilitacionSerializer(habilitacion).data,
                        status=status.HTTP_201_CREATED)

    def _autorizar_una(self, victima, datos, request):
        """
        Autoriza sobre UNA persona. Devuelve `(habilitacion, problema)`.

        Uno de los dos siempre es `None`. Está separado del `create` porque el
        lote necesita exactamente estas reglas, y tenerlas dos veces significa
        que el día que cambie una, el otro camino queda autorizando con las
        reglas viejas sin que nada falle.
        """
        from apps.victimas.repository.base import describir_elegibilidad

        # Una excluida del RUV no se habilita por ninguna ruta: el manual prevé
        # la excepción para fichas vigentes, no para revertir una decisión del
        # RUV. Sin esta guarda, el front podría otorgar una habilitación que la
        # app después ignora, y nadie entendería por qué.
        if getattr(victima, 'estado_ruv', '') == 'EXCLUIDO':
            return None, {
                'detail': 'Persona excluida del RUV — no elegible para '
                          'caracterización. Ninguna ruta de excepción habilita '
                          'este caso.',
                'motivo': 'EXCLUIDA_RUV',
            }

        vigente = ExcepcionVigencia.vigente_para(victima.id)
        if vigente is not None:
            return None, {
                'detail': 'Esta persona ya tiene una habilitación vigente.',
                'motivo': 'YA_HABILITADA',
                'habilitacion': HabilitacionSerializer(vigente).data,
            }

        # Se pasa `habilitacion=None` para preguntar por el estado REAL: si no,
        # una habilitación existente haría ver a la persona como elegible.
        veredicto = describir_elegibilidad(victima, habilitacion=None)

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
        return habilitacion, None

    @extend_schema(
        tags=['Habilitaciones'],
        request=CrearHabilitacionLoteSerializer,
        description=(
            'Autoriza la misma excepción sobre varias personas — un fallo que '
            'ampara a un hogar entero. Devuelve el resultado persona por '
            'persona: lo que no se pudo autorizar se informa, no se calla.'
        ),
    )
    @action(detail=False, methods=['post'])
    def lote(self, request):
        """
        Autoriza sobre varias personas con el mismo soporte.

        **No es atómico a propósito.** Si una persona del oficio está excluida
        del RUV o ya tenía habilitación, esa se salta y las demás se autorizan
        igual. Hacerlo todo-o-nada obligaría a coordinación a depurar la lista a
        mano hasta que pase entera, con la tutela vencida esperando.

        Lo que no se pudo hacer vuelve en `omitidas`, con el motivo de cada una.
        """
        from apps.victimas.models import Victima

        serializer = CrearHabilitacionLoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        datos = serializer.validated_data

        ids = list(dict.fromkeys(datos['victima_ids']))     # sin duplicados, en orden
        victimas = {v.id: v for v in Victima.objects.filter(pk__in=ids)}

        autorizadas, omitidas = [], []
        for vid in ids:
            victima = victimas.get(vid)
            if victima is None:
                omitidas.append({'victima_id': str(vid), 'motivo': 'NO_EXISTE',
                                 'detail': 'La víctima indicada no existe.'})
                continue
            habilitacion, problema = self._autorizar_una(victima, datos, request)
            if problema is not None:
                omitidas.append(dict(problema, victima_id=str(vid)))
            else:
                autorizadas.append(HabilitacionSerializer(habilitacion).data)

        # 201 solo si algo se creó. Con todas omitidas, un 201 le diría a quien
        # autoriza que quedó hecho cuando no se hizo nada.
        return Response(
            {'autorizadas': autorizadas, 'omitidas': omitidas,
             'total_autorizadas': len(autorizadas), 'total_omitidas': len(omitidas)},
            status=(status.HTTP_201_CREATED if autorizadas
                    else status.HTTP_409_CONFLICT))

    @extend_schema(
        tags=['Habilitaciones'],
        description=(
            'Busca por documento las personas sobre las que se puede autorizar '
            'una excepción, con su situación actual. Devuelve el `id` que pide '
            'el POST.'
        ),
    )
    @action(detail=False, methods=['get', 'post'])
    def buscar(self, request):
        """
        Documentos → personas, con la situación de cada una.

        Existe porque quien autoriza tiene el **documento** en el oficio, no un
        UUID interno, y ningún endpoint se lo daba: `/api/victimas/buscar/`
        devuelve el DTO del repositorio, que a propósito no expone el id, y
        `/api/victimas/{id}/` exige `puede_caracterizar` —permiso que el
        SUPERVISOR no tiene—.

        Acepta uno o varios documentos:

            GET  ?tipo_documento=CC&numero_documento=1115724047
            POST {"tipo_documento": "CC", "documentos": ["111...", "222..."]}

        La lista no es un lujo: una tutela ampara a un hogar, y un auto de
        seguimiento puede cubrir a varias personas. Pedirle a coordinación que
        busque de a una y repita el formulario veinte veces es cómo se terminan
        autorizando cosas a las apuradas.

        Devuelve **todas** las coincidencias de cada documento, no la primera. En
        el padrón hay 768.096 documentos compartidos por más de un registro y
        ~7 % son personas distintas: quedarse con una sola sería autorizar sobre
        quien no es, en silencio.

        Los documentos que no existen vuelven en `sin_coincidencia`, porque
        "no lo encontré" es justo lo que quien autoriza necesita saber para no
        dar por hecho que quedó cubierto por el oficio.
        """
        from apps.victimas.models import Victima
        from apps.victimas.repository.base import describir_elegibilidad, doc_hash

        if request.method == 'POST':
            tipo = (request.data.get('tipo_documento') or '').strip().upper()
            crudos = request.data.get('documentos') or []
            if isinstance(crudos, str):
                crudos = re.split(r'[\s,;]+', crudos)
        else:
            tipo = (request.query_params.get('tipo_documento') or '').strip().upper()
            crudos = [request.query_params.get('numero_documento') or '']

        # Se deduplica conservando el orden en que los pegaron: quien revisa la
        # lista contra el oficio la lee en ese orden.
        documentos, vistos = [], set()
        for d in crudos:
            d = (str(d) or '').strip()
            if d and d not in vistos:
                vistos.add(d)
                documentos.append(d)

        if not tipo or not documentos:
            return Response(
                {'detail': 'Indique el tipo y al menos un número de documento.'},
                status=status.HTTP_400_BAD_REQUEST)
        if len(documentos) > self.MAX_DOCUMENTOS_BUSQUEDA:
            return Response(
                {'detail': f'Máximo {self.MAX_DOCUMENTOS_BUSQUEDA} documentos por '
                           f'búsqueda. Llegaron {len(documentos)}.'},
                status=status.HTTP_400_BAD_REQUEST)

        # Una consulta para todos los documentos y no una por cada uno: con 50
        # cédulas serían 50 viajes a la base mientras alguien espera.
        por_hash = {doc_hash(tipo, d): d for d in documentos}
        victimas = (Victima.objects
                    .filter(numero_documento_hash__in=list(por_hash.keys()))
                    .select_related('tipo_documento'))

        habilitaciones = self._habilitaciones_vigentes([v.id for v in victimas])

        resultados, encontrados = [], set()
        for v in victimas:
            encontrados.add(por_hash.get(v.numero_documento_hash))
            vigente = habilitaciones.get(v.id)
            # `habilitacion=None` a propósito: se quiere la situación REAL. Si se
            # dejara consultar sola, una persona ya habilitada aparecería como
            # elegible y quien autoriza no vería que ya lo está.
            veredicto = describir_elegibilidad(v, habilitacion=None)
            resultados.append({
                'id': str(v.id),
                'nombre': ' '.join(p for p in [
                    v.primer_nombre, v.segundo_nombre,
                    v.primer_apellido, v.segundo_apellido] if p).strip(),
                'tipo_documento': (v.tipo_documento.codigo
                                   if v.tipo_documento_id else ''),
                'numero_documento': v.numero_documento,
                'fecha_nacimiento': v.fecha_nacimiento,
                'estado_ruv': v.estado_ruv,
                'motivo': veredicto.motivo,
                'mensaje': veredicto.mensaje,
                'ficha_vigente_hasta': veredicto.disponible_desde,
                'requiere_excepcion': veredicto.motivo == 'FICHA_VIGENTE',
                'habilitacion_vigente': (HabilitacionSerializer(vigente).data
                                         if vigente else None),
            })

        LogAcceso.registrar(
            accion='BUSQUEDA_RNI',
            usuario=request.user,
            ip=ip_de_request(request),
            recurso='ExcepcionVigencia.buscar',
            # Los números NO se registran: la auditoría guarda que se buscó, no a
            # quién se buscó. Misma regla que el resto de las búsquedas.
            detalle={'documentos': len(documentos), 'coincidencias': len(resultados)},
        )

        return Response({
            'total': len(resultados),
            'resultados': resultados,
            'sin_coincidencia': [d for d in documentos if d not in encontrados],
        })

    @staticmethod
    def _habilitaciones_vigentes(ids) -> dict:
        """`{victima_id: habilitación vigente}` en una sola consulta."""
        if not ids:
            return {}
        vigentes = (ExcepcionVigencia.objects
                    .filter(victima_id__in=list(ids),
                            estado=ExcepcionVigencia.VIGENTE)
                    .select_related('autorizada_por')
                    .order_by('victima_id', '-created_at'))
        resultado = {}
        for h in vigentes:
            resultado.setdefault(h.victima_id, h)
        return resultado

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
