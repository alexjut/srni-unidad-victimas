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

#: El universo trae el género escrito ('Mujer', 'Hombre'), no el código del
#: dominio. Lo que no se reconoce queda 'ND' —no se adivina—, y el encuestador
#: lo captura en campo.
_GENERO_UNIVERSO = {
    'mujer': 'F', 'femenino': 'F', 'f': 'F',
    'hombre': 'M', 'masculino': 'M', 'm': 'M',
    'no binario': 'NB', 'intersexual': 'NB',
}

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

    # Uno de los dos, no los dos. `universo_id` es para quien está en el corte
    # del RUV pero todavía no tiene ficha en el padrón operativo: al autorizar
    # se le crea, con los datos del propio corte. Ver `_materializar_del_universo`.
    victima_id = serializers.UUIDField(required=False)
    universo_id = serializers.UUIDField(required=False)
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

    def validate(self, attrs):
        if not attrs.get('victima_id') and not attrs.get('universo_id'):
            raise serializers.ValidationError(
                'Indique a quién se autoriza: `victima_id` si ya tiene ficha en '
                'el padrón, o `universo_id` si viene del corte del RUV.'
            )
        return attrs


class CrearHabilitacionLoteSerializer(CrearHabilitacionSerializer):
    """
    Igual que la individual pero sobre varias personas, con el MISMO soporte.

    Hereda para que las reglas de radicado y motivo no se escriban dos veces: el
    día que cambie el mínimo del motivo, cambia en los dos caminos o en ninguno.
    """

    victima_id = None            # se reemplaza por la lista
    universo_id = None
    victima_ids = serializers.ListField(
        child=serializers.UUIDField(), max_length=200, required=False, default=list)
    universo_ids = serializers.ListField(
        child=serializers.UUIDField(), max_length=200, required=False, default=list)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop('victima_id', None)
        self.fields.pop('universo_id', None)

    def validate(self, attrs):
        if not attrs.get('victima_ids') and not attrs.get('universo_ids'):
            raise serializers.ValidationError(
                'Indique al menos una persona: `victima_ids`, `universo_ids`, o ambas.'
            )
        return attrs


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

        victima, problema = self._resolver_persona(datos, request)
        if problema is not None:
            return Response(problema, status=status.HTTP_404_NOT_FOUND)

        habilitacion, problema = self._autorizar_una(victima, datos, request)
        if problema is not None:
            return Response(problema, status=status.HTTP_409_CONFLICT)

        return Response(HabilitacionSerializer(habilitacion).data,
                        status=status.HTTP_201_CREATED)

    def _materializar_del_universo(self, universo_id, request):
        """Crea la ficha en el padrón a partir del corte del RUV.

        Devuelve `(victima, problema)`; uno de los dos siempre es `None`.

        **Por qué `estado_ruv='INCLUIDO'`.** `PersonaUniverso` ES el corte oficial
        del RUV: estar ahí es estar incluida. No se usa `NO_VERIFICADO` —el
        estado que existe para el alta manual— porque ahí el dato lo teclea un
        encuestador y no se comprobó contra nada; acá viene del snapshot de la
        Unidad. Decisión de Javier, 21-ago.

        **Por qué solo al autorizar.** Buscar no crea nada. Coordinación puede
        pegar 200 documentos de un oficio para ver la situación de cada uno, y
        eso no puede dejar 200 fichas nuevas en el padrón.
        """
        from apps.victimas.models import PersonaUniverso, Victima
        from apps.parametricas.models import TipoDocumento

        try:
            p = PersonaUniverso.objects.get(pk=universo_id)
        except PersonaUniverso.DoesNotExist:
            return None, {'detail': 'La persona indicada no existe en el corte del RUV.',
                          'motivo': 'NO_EXISTE_EN_UNIVERSO'}

        # Si ya se materializó antes —dos autorizaciones sobre la misma persona,
        # o el padrón se recargó— se reusa. Crear otra sería duplicarla.
        if p.victima_id:
            return Victima.objects.filter(pk=p.victima_id).first(), None
        ya = Victima.objects.filter(
            numero_documento_hash_sin_tipo=p.numero_documento_hash_sin_tipo).first()
        if ya is not None:
            PersonaUniverso.objects.filter(pk=p.pk).update(victima=ya)
            return ya, None

        tipo_doc = None
        if p.tipo_documento:
            tipo_doc = TipoDocumento.objects.filter(codigo=p.tipo_documento).first()

        with transaction.atomic():
            victima = Victima.objects.create(
                tipo_documento=tipo_doc,
                numero_documento=p.numero_documento,
                primer_nombre=p.primer_nombre or '',
                segundo_nombre=p.segundo_nombre or '',
                primer_apellido=p.primer_apellido or '',
                segundo_apellido=p.segundo_apellido or '',
                fecha_nacimiento=str(p.fecha_nacimiento) if p.fecha_nacimiento else '',
                genero=_GENERO_UNIVERSO.get((p.genero or '').strip().lower(), 'ND'),
                estado_ruv='INCLUIDO',
                fuente_origen='RUV',
                habilitado_para_caracterizacion=False,
                pertenencia_etnica='NINGUNA',
                discapacidad=bool(p.discapacidad),
                tipo_discapacidad=p.tipo_discapacidad or '',
                cons_persona=p.cons_persona_universo,
                fecha_ult_caracterizacion=p.fecha_ult_caracterizacion,
                creado_por=request.user,
            )
            PersonaUniverso.objects.filter(pk=p.pk).update(victima=victima)

            LogAcceso.registrar(
                accion='REGISTRAR_VICTIMA',
                usuario=request.user,
                ip=ip_de_request(request),
                recurso='Victima',
                recurso_id=victima.id,
                detalle={'origen': 'UNIVERSO', 'universo_id': str(p.id),
                         'motivo': 'materializada para autorizar excepcion'},
            )

        logger.info('victima %s materializada del universo %s por %s',
                    victima.id, p.id, request.user)
        return victima, None

    def _resolver_persona(self, datos, request):
        """La persona sobre la que se autoriza, venga del padrón o del universo."""
        from apps.victimas.models import Victima

        if datos.get('universo_id'):
            return self._materializar_del_universo(datos['universo_id'], request)
        victima = Victima.objects.filter(pk=datos['victima_id']).first()
        if victima is None:
            return None, {'detail': 'La víctima indicada no existe.',
                          'motivo': 'NO_EXISTE'}
        return victima, None

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
        # Los del universo llegan aparte: no tienen ficha todavía y se les crea
        # una por una al autorizar.
        ids_universo = list(dict.fromkeys(datos.get('universo_ids') or []))
        victimas = {v.id: v for v in Victima.objects.filter(pk__in=ids)}

        autorizadas, omitidas = [], []
        for uid in ids_universo:
            victima, problema = self._materializar_del_universo(uid, request)
            if problema is not None:
                omitidas.append(dict(problema, universo_id=str(uid)))
                continue
            habilitacion, problema = self._autorizar_una(victima, datos, request)
            if problema is not None:
                omitidas.append(dict(problema, universo_id=str(uid)))
            else:
                autorizadas.append(HabilitacionSerializer(habilitacion).data)

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

        **Respaldo por número sin tipo.** 1.126.615 víctimas (14,5 % del padrón)
        están cargadas SIN tipo de documento, y su hash de identidad se calculó
        con el tipo vacío. Buscarlas por «CC + número» no las encuentra. Esta
        pantalla decía «sin coincidencia» sobre personas que **sí** están en el
        padrón, y quien autoriza no tenía forma de saber que el sistema le estaba
        mintiendo. La búsqueda de la APK ya tenía este respaldo; acá faltaba.
        """
        from apps.victimas.models import Victima
        from apps.victimas.repository.base import (
            describir_elegibilidad, doc_hash, num_hash,
        )

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
        victimas = list(Victima.objects
                        .filter(numero_documento_hash__in=list(por_hash.keys()))
                        .select_related('tipo_documento'))

        # `documento` de cada fila hallada, para poder decir después cuáles
        # quedaron sin coincidencia.
        doc_de = {v.id: por_hash[v.numero_documento_hash] for v in victimas}

        # Respaldo por número SIN tipo, solo para los que no aparecieron. Las
        # 1.126.615 víctimas cargadas sin tipo tienen su hash calculado con el
        # tipo vacío: por «CC + número» no salen nunca. Se consulta en un solo
        # viaje más y únicamente si hace falta.
        faltantes = [d for d in documentos if d not in doc_de.values()]
        if faltantes:
            por_num = {num_hash(d): d for d in faltantes}
            respaldo = (Victima.objects
                        .filter(numero_documento_hash_sin_tipo__in=list(por_num.keys()))
                        .exclude(id__in=list(doc_de.keys()))
                        .select_related('tipo_documento'))
            for v in respaldo:
                doc_de[v.id] = por_num.get(v.numero_documento_hash_sin_tipo)
                victimas.append(v)

        # Colapsar los registros que son LA MISMA persona (H-025).
        #
        # El padrón tiene 768.096 documentos compartidos por más de una fila, y
        # el 92 % de esos son la misma persona cargada dos veces por el Oracle de
        # origen, no personas distintas. Sin esto, buscar ese documento devolvía
        # dos filas casi idénticas y el panel mostraba una «fila duplicada».
        #
        # Se reutiliza el mismo criterio que la búsqueda de víctimas
        # (`ColisionDocumento`, ya calculado): si el veredicto dice que son la
        # misma persona se deja la fila más completa; solo se mantienen separadas
        # las que de verdad son personas distintas (el ~7 %), porque ahí quien
        # autoriza SÍ tiene que elegir. La reducción vive en el repositorio para
        # que el panel y la APK decidan igual sobre la misma persona.
        from apps.victimas.repository import DjangoVictimaRepository
        victimas = DjangoVictimaRepository._resolver_colision(victimas)

        habilitaciones = self._habilitaciones_vigentes([v.id for v in victimas])

        resultados, encontrados = [], set()
        for v in victimas:
            encontrados.add(doc_de.get(v.id))
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
                # Se encontró por número pero el tipo registrado es otro (o no
                # tiene). Quien autoriza tiene que verlo antes de decidir: es el
                # mismo aviso que la APK le da al encuestador en campo.
                'coincide_solo_por_numero': (
                    v.numero_documento_hash != doc_hash(tipo, doc_de.get(v.id) or '')),
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

        # Lo que el padrón operativo no tiene, se busca en el corte del RUV.
        #
        # El padrón son 5,9 M de fichas; el universo, 12 M de personas. Una
        # víctima puede estar en el corte del RUV —con nombre, documento y fecha
        # de nacimiento— y no tener ficha, y hasta hoy la pantalla le decía a
        # coordinación «sin coincidencia»: la daba por no cubierta por el oficio
        # aunque la Unidad la reconozca como víctima.
        #
        # No se le crea la ficha por buscarla. Se le crea al AUTORIZAR, que es
        # cuando alguien decidió algo sobre ella. Buscar 200 documentos no puede
        # dejar 200 filas nuevas en el padrón.
        faltan = [d for d in documentos if d not in encontrados]
        del_universo = []
        if faltan:
            from apps.victimas.models import PersonaUniverso

            # SOLO por `numero_documento_hash_sin_tipo`, y no por el hash completo.
            #
            # PersonaUniverso tiene 12 M de filas. `numero_documento_hash` NO está
            # indexado (solo lo está el compuesto por hash-sin-tipo), así que
            # filtrar por él era un table scan de ~6 s medido en producción. Con
            # el timeout de 15 s del cliente + el WAF, la consulta se pasaba de
            # forma intermitente y el panel mostraba «No se pudo buscar»: es el
            # hallazgo H-024 del QA, y lo introdujo este mismo bloque.
            #
            # Buscar por número solo es además lo correcto: el universo puede
            # tener a la persona con un tipo de documento distinto —o sin tipo—,
            # y ese caso se avisa abajo con `coincide_solo_por_numero`. Es el
            # mismo criterio del respaldo por número de la búsqueda de víctimas.
            por_num_u = {num_hash(d): d for d in faltan}
            personas = PersonaUniverso.objects.filter(
                numero_documento_hash_sin_tipo__in=list(por_num_u.keys()))
            vistos_u = set()
            for p in personas:
                doc = por_num_u.get(p.numero_documento_hash_sin_tipo)
                # Una misma persona puede aparecer en varios cortes del universo:
                # nos quedamos con la primera y no la duplicamos.
                if doc in vistos_u:
                    continue
                vistos_u.add(doc)
                encontrados.add(doc)
                del_universo.append({
                    'id': None,
                    'universo_id': str(p.id),
                    'origen': 'UNIVERSO',
                    'nombre': ' '.join(x for x in [
                        p.primer_nombre, p.segundo_nombre,
                        p.primer_apellido, p.segundo_apellido] if x).strip(),
                    'tipo_documento': p.tipo_documento or '',
                    'numero_documento': p.numero_documento,
                    'fecha_nacimiento': p.fecha_nacimiento,
                    'estado_ruv': 'INCLUIDO',
                    'motivo': 'SIN_FICHA_EN_PADRON',
                    'mensaje': ('Está en el corte del RUV pero no tiene ficha en el '
                                'padrón. Al autorizar se le crea con estos datos.'),
                    'ficha_vigente_hasta': None,
                    'requiere_excepcion': True,
                    'habilitacion_vigente': None,
                    'coincide_solo_por_numero': (
                        p.numero_documento_hash != doc_hash(tipo, doc or '')),
                })

        for r in resultados:
            r.setdefault('origen', 'PADRON')
            r.setdefault('universo_id', None)

        todos = resultados + del_universo
        return Response({
            'total': len(todos),
            'resultados': todos,
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
