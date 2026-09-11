"""
`/api/recaracterizaciones/` — el punto de control del retiro de la vigencia.

─── Por qué existe ──────────────────────────────────────────────────────────
El 11-sep-2026 se retiró el bloqueo por ficha vigente. Lo único que se conservó
fue el **dato**: `RecaracterizacionVigente` anota, al cerrar cada encuesta, toda
caracterización hecha sobre una persona que todavía tenía ficha vigente.

Este módulo es la otra mitad del trabajo, y sin ella la primera no sirve de nada:
**un registro que nadie consulta equivale a no tenerlo.** Acá está la consulta.

─── Qué responde, sin que nadie tenga que pedirlo ──────────────────────────
    · cuántas recaracterizaciones se hicieron sobre ficha vigente;
    · quién las hizo, y cuántas cada uno;
    · en qué territorial y en qué municipio;
    · **cuántas veces se recaracterizó a cada persona** — la cifra que hace
      visible el caso de la misma ficha reescrita cuatro veces en dos meses;
    · con cuánta anticipación: los días que le faltaban a la ficha por vencer,
      que es lo que separa «la actualizaron a los 22 meses» de «a los 3 días».

Es exactamente el informe que va a pedir control interno o la Contraloría el día
que lo pidan, y hasta ahora la entidad no tendría con qué responderlo.

─── No detiene a nadie, y eso es deliberado ────────────────────────────────
Es un libro de registro, no una puerta. El encuestador no se entera de que se
escribe, no hay nada que autorizar y nada que esperar. Lo que este módulo agrega
es que alguien pueda **mirar** el libro.

Quién puede mirarlo: `administrar` o `ver_reportes` —supervisión—. No el
encuestador de campo: el propósito es supervisar la operación, y un instrumento
de supervisión en manos del supervisado no supervisa nada.
"""
import logging

import django_filters as df
from django.db.models import Count, Max, Min, OuterRef, Subquery
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import permissions, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from .models import RecaracterizacionVigente

logger = logging.getLogger(__name__)


class PuedeVerRecaracterizaciones(permissions.BasePermission):
    """
    Supervisión, no campo.

    Mismo criterio que la auditoría de accesos: un instrumento para mirar cómo
    opera el equipo no se le entrega al equipo que se está mirando.
    """

    message = ('Se requiere perfil administrador o supervisor para consultar las '
               'recaracterizaciones.')

    def has_permission(self, request, view):
        u = request.user
        if not (u and u.is_authenticated):
            return False
        return u.puede('administrar') or u.puede('ver_reportes')


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------

class RecaracterizacionSerializer(serializers.ModelSerializer):
    """
    Una fila del libro, con lo que el panel necesita para mostrarla sin ir a
    buscar nada más.

    El documento de la persona viaja **hasheado**, no en claro: para contar,
    agrupar y detectar a la misma persona repetida el hash alcanza, y esta
    consulta la usa supervisión sobre volúmenes grandes. Quien necesite la
    identidad de un caso concreto la pide por la ficha, donde el acceso queda
    registrado en la auditoría.
    """

    documento_hash = serializers.CharField(
        source='victima.numero_documento_hash', read_only=True, default='')
    realizada_por_codigo = serializers.CharField(
        source='realizada_por.codigo_usuario', read_only=True, default='')
    realizada_por_nombre = serializers.CharField(
        source='realizada_por.nombre_completo', read_only=True, default='')
    ruta_display = serializers.CharField(source='get_ruta_display', read_only=True)
    municipio_nombre = serializers.CharField(
        source='hogar.municipio.nombre', read_only=True, default='')
    departamento_nombre = serializers.CharField(
        source='hogar.municipio.departamento.nombre', read_only=True, default='')
    codigo_hogar = serializers.CharField(
        source='hogar.codigo_hogar', read_only=True, default='')
    #: Cuántas veces se ha recaracterizado a ESTA persona, contando esta vez. Lo
    #: anota el queryset; sin él habría una consulta por fila.
    veces_esta_persona = serializers.IntegerField(read_only=True, default=1)

    class Meta:
        model = RecaracterizacionVigente
        fields = [
            'id', 'victima', 'documento_hash', 'veces_esta_persona',
            'realizada_por', 'realizada_por_codigo', 'realizada_por_nombre',
            'realizada_at', 'ruta', 'ruta_display',
            'fecha_ult_caracterizacion', 'vigente_hasta', 'dias_restantes',
            'sesion', 'hogar', 'codigo_hogar',
            'municipio_nombre', 'departamento_nombre',
            'created_at',
        ]
        read_only_fields = fields


class PersonaRecaracterizadaSerializer(serializers.Serializer):
    """
    Una persona y **cuántas veces** se la recaracterizó.

    Es la vista que hace visible el caso que importa: la misma ficha reescrita
    varias veces en pocas semanas. Una lista cronológica de eventos lo esconde
    —quedan repartidos entre miles de filas—; agrupado por persona salta a la
    vista en la primera pantalla.
    """

    victima = serializers.UUIDField()
    documento_hash = serializers.CharField()
    veces = serializers.IntegerField()
    primera = serializers.DateTimeField()
    ultima = serializers.DateTimeField()
    #: La menor anticipación de todas sus recaracterizaciones: si una se hizo a
    #: los tres días de la anterior, este número lo delata.
    menor_dias_restantes = serializers.IntegerField(allow_null=True)
    autores = serializers.IntegerField(
        help_text='Cuántos encuestadores distintos la recaracterizaron.')


# ---------------------------------------------------------------------------
# Filtros
# ---------------------------------------------------------------------------

class RecaracterizacionFilterSet(df.FilterSet):
    fecha_desde = df.DateFilter(field_name='realizada_at', lookup_expr='date__gte')
    fecha_hasta = df.DateFilter(field_name='realizada_at', lookup_expr='date__lte')
    codigo_usuario = df.CharFilter(
        field_name='realizada_por__codigo_usuario', lookup_expr='iexact')
    ruta = df.CharFilter(field_name='ruta', lookup_expr='iexact')
    municipio = df.CharFilter(field_name='hogar__municipio__codigo_dane')
    departamento = df.CharFilter(
        field_name='hogar__municipio__departamento__codigo_dane')
    #: El filtro que se va a usar de verdad: «muéstrame las que se hicieron con
    #: la ficha más fresca», que son las que hay que mirar primero.
    dias_restantes_min = df.NumberFilter(
        field_name='dias_restantes', lookup_expr='gte')
    documento_hash = df.CharFilter(field_name='victima__numero_documento_hash')

    class Meta:
        model = RecaracterizacionVigente
        fields = ['fecha_desde', 'fecha_hasta', 'codigo_usuario', 'ruta',
                  'municipio', 'departamento', 'dias_restantes_min',
                  'documento_hash']


# ---------------------------------------------------------------------------
# ViewSet
# ---------------------------------------------------------------------------

@extend_schema_view(
    list=extend_schema(
        summary='Recaracterizaciones hechas sobre ficha vigente',
        description=(
            'El libro de registro del retiro del control de vigencia. Una fila por '
            'caracterización hecha sobre una persona que todavía tenía ficha '
            'vigente, escrita por el sistema al cerrar la encuesta.\n\n'
            'Solo supervisión (`administrar` o `ver_reportes`).\n\n'
            '**Filtros:** `fecha_desde`, `fecha_hasta`, `codigo_usuario`, `ruta`, '
            '`municipio`, `departamento`, `dias_restantes_min`, `documento_hash`.\n\n'
            '**Orden:** por defecto la más reciente primero. `ordering=dias_restantes` '
            'las pone por gravedad — las hechas con la ficha más fresca arriba.'
        ),
        tags=['Recaracterizaciones'],
        parameters=[
            OpenApiParameter('fecha_desde', str, description='YYYY-MM-DD'),
            OpenApiParameter('fecha_hasta', str, description='YYYY-MM-DD'),
            OpenApiParameter('codigo_usuario', str, description='Quién la hizo'),
            OpenApiParameter('dias_restantes_min', int,
                             description='Solo las que se hicieron con al menos '
                                         'estos días de anticipación'),
        ],
    ),
    retrieve=extend_schema(tags=['Recaracterizaciones']),
)
class RecaracterizacionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Solo lectura, y no por prudencia sino por definición: estas filas las escribe
    el sistema al cerrar una encuesta. Una que se pudiera editar desde el panel no
    serviría como constancia de nada.
    """

    serializer_class = RecaracterizacionSerializer
    permission_classes = [PuedeVerRecaracterizaciones]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = RecaracterizacionFilterSet
    ordering_fields = ['realizada_at', 'dias_restantes', 'fecha_ult_caracterizacion']
    ordering = ['-realizada_at']

    def get_queryset(self):
        # Cuántas veces se ha recaracterizado a ESTA persona, en la misma fila.
        #
        # Va como subconsulta y no contando después: el panel muestra 50 filas por
        # página y preguntarlo una por una son 50 viajes más a la base. Y va en la
        # fila —no solo en `personas/`— porque es el dato que permite ver, mirando
        # el listado corriente, que la que se está leyendo es la cuarta vez sobre
        # la misma persona. Sin él hay que ir a otra pantalla a sospecharlo.
        veces = (RecaracterizacionVigente.objects
                 .filter(victima=OuterRef('victima'))
                 .values('victima')
                 .annotate(c=Count('id'))
                 .values('c')[:1])

        # `select_related` no es cosmético: el serializer lee el código del
        # usuario, el municipio, su departamento y el código del hogar. Sin esto,
        # una página de 50 filas dispara 200 consultas.
        return (RecaracterizacionVigente.objects
                .select_related('realizada_por', 'victima',
                                'hogar__municipio__departamento')
                .annotate(veces_esta_persona=Subquery(veces))
                .all())

    @extend_schema(
        summary='Resumen para el informe de control',
        description=(
            'Los totales que responden «cuántas, quién y con cuánta anticipación», '
            'sin traer las filas. Acepta los mismos filtros que el listado.'
        ),
        tags=['Recaracterizaciones'],
    )
    @action(detail=False, methods=['get'], url_path='resumen')
    def resumen(self, request):
        """
        Lo que va en la primera pantalla del panel y en el informe.

        Se calcula en la base y no en Python: sobre cientos de miles de filas,
        traerlas para contarlas agota la memoria del proceso y el tiempo de espera
        del panel.
        """
        qs = self.filter_queryset(self.get_queryset())

        total = qs.count()
        personas = qs.values('victima').distinct().count()

        por_autor = list(
            qs.values('realizada_por__codigo_usuario',
                      'realizada_por__nombre_completo')
              .annotate(veces=Count('id'))
              .order_by('-veces')[:100]
        )
        por_territorial = list(
            qs.values('hogar__municipio__departamento__nombre')
              .annotate(veces=Count('id'))
              .order_by('-veces')[:50]
        )
        por_ruta = list(
            qs.values('ruta').annotate(veces=Count('id')).order_by('-veces')
        )

        # Franjas de anticipación. Son el orden de gravedad: recaracterizar a los
        # tres días de la entrevista anterior no es lo mismo que hacerlo a los 22
        # meses, y un promedio mezcla las dos cosas hasta volverlas invisibles.
        franjas = {
            'hasta_7_dias': qs.filter(dias_restantes__gte=718).count(),
            'hasta_30_dias': qs.filter(dias_restantes__gte=700,
                                       dias_restantes__lt=718).count(),
            'hasta_6_meses': qs.filter(dias_restantes__gte=548,
                                       dias_restantes__lt=700).count(),
            'mas_de_6_meses': qs.filter(dias_restantes__lt=548).count(),
            'sin_dato': qs.filter(dias_restantes__isnull=True).count(),
        }

        return Response({
            'total': total,
            'personas_distintas': personas,
            # Si este número es mayor que 1, hay personas recaracterizadas más de
            # una vez, y `personas/` dice cuáles.
            'promedio_por_persona': round(total / personas, 2) if personas else 0,
            'por_autor': [
                {'codigo_usuario': f['realizada_por__codigo_usuario'] or '',
                 'nombre': f['realizada_por__nombre_completo'] or '',
                 'veces': f['veces']}
                for f in por_autor
            ],
            'por_territorial': [
                {'departamento': f['hogar__municipio__departamento__nombre'] or 'Sin dato',
                 'veces': f['veces']}
                for f in por_territorial
            ],
            'por_ruta': [{'ruta': f['ruta'] or '', 'veces': f['veces']}
                         for f in por_ruta],
            'anticipacion': franjas,
        })

    @extend_schema(
        summary='Cuántas veces se recaracterizó a cada persona',
        description=(
            'Agrupado por persona y ordenado de más a menos veces. Es la vista que '
            'hace visible la misma ficha reescrita varias veces en pocas semanas: '
            'en el listado cronológico esos casos quedan repartidos entre miles de '
            'filas.\n\n'
            'Acepta los mismos filtros que el listado, más `veces_min` (por defecto '
            '2: solo las personas con más de una).'
        ),
        tags=['Recaracterizaciones'],
        parameters=[
            OpenApiParameter('veces_min', int,
                             description='Mínimo de recaracterizaciones (default 2)'),
        ],
    )
    @action(detail=False, methods=['get'], url_path='personas')
    def personas(self, request):
        """
        El default es `veces_min=2` a propósito.

        Con 1 la respuesta es el padrón entero de recaracterizados y no dice nada:
        toda persona que aparece en el libro tiene al menos una. Lo que hay que
        mirar son las que tienen más, y esas son pocas. Poner el umbral en el
        default es lo que hace que la primera pantalla ya muestre el problema en
        vez de obligar a buscarlo.
        """
        try:
            veces_min = max(1, int(request.query_params.get('veces_min', 2)))
        except (TypeError, ValueError):
            veces_min = 2

        qs = self.filter_queryset(self.get_queryset())
        filas = (qs.values('victima', 'victima__numero_documento_hash')
                   .annotate(veces=Count('id'),
                             primera=Min('realizada_at'),
                             ultima=Max('realizada_at'),
                             menor_dias_restantes=Max('dias_restantes'),
                             autores=Count('realizada_por', distinct=True))
                   .filter(veces__gte=veces_min)
                   .order_by('-veces', '-ultima'))

        pagina = self.paginate_queryset(list(filas))
        datos = [
            {
                'victima': f['victima'],
                'documento_hash': f['victima__numero_documento_hash'] or '',
                'veces': f['veces'],
                'primera': f['primera'],
                'ultima': f['ultima'],
                # ⚠️ `dias_restantes` cuenta lo que le FALTABA por vencer, así que
                # el número más ALTO es la recaracterización más temprana — la más
                # grave. Tomar el mínimo dejaría fuera justo el caso que se busca.
                'menor_dias_restantes': f['menor_dias_restantes'],
                'autores': f['autores'],
            }
            for f in (pagina if pagina is not None else filas)
        ]
        serializer = PersonaRecaracterizadaSerializer(datos, many=True)
        if pagina is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)
