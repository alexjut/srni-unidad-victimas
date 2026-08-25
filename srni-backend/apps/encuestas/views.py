"""
Views de Encuestas SRNI.

Flujo de uso:
  1. POST /api/encuestas/          → crea SesionEncuesta (estado=INICIADA)
  2. POST /api/encuestas/{id}/responder/   → guarda/actualiza respuesta individual
  3. GET  /api/encuestas/{id}/             → detalle con todas las respuestas
  4. POST /api/encuestas/{id}/finalizar/   → cierra la sesión (COMPLETADA)
"""
import logging

from django.utils import timezone
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from drf_spectacular.utils import extend_schema, extend_schema_view

from apps.autenticacion.permissions import PuedeConsultarOperacion
from apps.auditoria.models import LogAcceso
from apps.auditoria.red import ip_de_request
from apps.formulario.models import Pregunta
from apps.hogares.models import MiembroHogar
from apps.sincronizacion.tasks import encolar_hogar
from srni.pagination import DefaultPageNumberPagination
from .models import SesionEncuesta, RespuestaEncuesta
from .filters import SesionEncuestaFilterSet

logger = logging.getLogger(__name__)


def _resolver_miembro(sesion, pregunta, miembro_id):
    """
    Sprint 21 — valida coherencia de nivel pregunta/miembro y devuelve la
    instancia MiembroHogar (o None si la pregunta es HOGAR).

    Reglas:
      - pregunta.nivel == 'HOGAR':   miembro_id debe ser None.
      - pregunta.nivel == 'PERSONA': miembro_id requerido y debe pertenecer
                                     al hogar de la sesión.

    Devuelve (miembro, error_dict). Si error_dict es no-None, la vista debe
    responder 400 con ese dict.
    """
    if pregunta.nivel == 'HOGAR':
        if miembro_id is not None:
            return None, {
                'miembro_id': f"La pregunta '{pregunta.codigo_externo}' es de nivel HOGAR; "
                              f'no admite miembro_id.',
            }
        return None, None

    # nivel == PERSONA
    if miembro_id is None:
        return None, {
            'miembro_id': f"La pregunta '{pregunta.codigo_externo}' es de nivel PERSONA; "
                          f'requiere miembro_id.',
        }
    try:
        miembro = MiembroHogar.objects.get(pk=miembro_id, hogar=sesion.hogar_id)
    except MiembroHogar.DoesNotExist:
        return None, {
            'miembro_id': f'El miembro {miembro_id} no pertenece al hogar de esta sesión.',
        }
    return miembro, None
from .serializers import (
    SesionEncuestaListSerializer, SesionEncuestaDetalleSerializer,
    RespuestaEncuestaSerializer,
    ResponderPreguntaSerializer, ResponderBulkSerializer, FinalizarSesionSerializer,
)


def _ip(request) -> str:
    # Ver apps/auditoria/red.py: el WAF manda `IP:puerto` y sin limpiarlo el
    # INSERT de auditoría falla y la petición responde 500.
    return ip_de_request(request)


@extend_schema_view(
    list=extend_schema(summary='Listar sesiones del encuestador', tags=['Encuestas']),
    retrieve=extend_schema(summary='Detalle de sesión con respuestas', tags=['Encuestas']),
    create=extend_schema(summary='Iniciar nueva sesión de encuesta', tags=['Encuestas']),
)
class SesionEncuestaViewSet(viewsets.ModelViewSet):
    """
    Gestión de sesiones de encuesta.
    Solo los encuestadores con puede_caracterizar pueden operar este endpoint.
    """
    permission_classes = [IsAuthenticated, PuedeConsultarOperacion]
    # Paginación por número de página, no por cursor. El panel de supervisión
    # está escrito para eso —manda ?page= y lee `count` para mostrar «página N
    # de M»— y el cursor no devuelve `count`: por eso el listado mostraba
    # «undefined sesión(es)» y «Página 1 de NaN» (H-010/H-011), y además el
    # botón «siguiente» nunca avanzaba porque el cursor ignora ?page=. La APK
    # solo lee `results`, así que no le afecta.
    pagination_class = DefaultPageNumberPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = SesionEncuestaFilterSet
    ordering_fields = [
        'created_at', 'updated_at',
        'porcentaje_completado',
        'fecha_inicio', 'fecha_fin',
    ]
    ordering = ['-created_at']
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_queryset(self):
        user = self.request.user
        qs = SesionEncuesta.objects.select_related(
            'hogar', 'instrumento', 'encuestador',
            'direccion_territorial', 'departamento_atencion',
            'municipio_atencion', 'punto_atencion',
        ).prefetch_related('respuestas')
        # Admin y supervisión (ver_reportes) ven todas las sesiones; el
        # encuestador de campo solo las suyas.
        if not (user.puede('administrar') or user.puede('ver_reportes')):
            qs = qs.filter(encuestador=user)
        return qs

    def get_serializer_class(self):
        if self.action == 'list':
            return SesionEncuestaListSerializer
        return SesionEncuestaDetalleSerializer

    def create(self, request, *args, **kwargs):
        """
        Regla universal: 1 víctima → 1 hogar → 1 caracterización activa.

        Si el hogar ya tiene una sesión activa (no COMPLETADA), devolver esa
        en lugar de crear una duplicada. Para probar otro instrumento sobre
        la misma víctima, completar la sesión actual y archivar el hogar.
        """
        hogar_id = request.data.get('hogar')
        if hogar_id:
            es_admin = request.user.puede('administrar')
            base = SesionEncuesta.objects.filter(
                hogar_id=hogar_id,
            ).exclude(estado='COMPLETADA').order_by('-created_at')

            if es_admin:
                sesion_activa = base.first()
            else:
                # Para no-admin la idempotencia debe filtrar encuestador: una
                # sesión activa de OTRO encuestador no es navegable (get_queryset
                # filtra encuestador=user → 404 en responder/finalizar). En ese
                # caso respondemos 409 en lugar de exponer un id inaccesible.
                sesion_activa = base.filter(encuestador=request.user).first()
                if not sesion_activa and base.exists():
                    return Response(
                        {'detail': (
                            'Este hogar ya tiene una sesión de encuesta activa '
                            'iniciada por otro encuestador. Solicita su '
                            'reasignación al supervisor.'
                        )},
                        status=status.HTTP_409_CONFLICT,
                    )

            if sesion_activa:
                from .serializers import SesionEncuestaDetalleSerializer
                detalle = SesionEncuestaDetalleSerializer(
                    sesion_activa, context={'request': request}
                )
                return Response(detalle.data, status=status.HTTP_200_OK)

        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        sesion = serializer.save(encuestador=self.request.user, estado='INICIADA')
        LogAcceso.registrar(
            usuario=self.request.user,
            accion='RESPONDER_PREGUNTA',
            recurso='SesionEncuesta',
            recurso_id=str(sesion.id),
            ip=_ip(self.request),
            user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
            resultado='EXITO',
            detalle={'accion': 'CREAR_SESION', 'hogar_id': str(sesion.hogar_id)},
        )

    @extend_schema(
        summary='Guardar o actualizar una respuesta',
        description=(
            'Upsert: si la pregunta ya tiene respuesta en esta sesión, la actualiza. '
            'Si no, la crea. Actualiza automáticamente el porcentaje de completado.'
        ),
        tags=['Encuestas'],
        request=ResponderPreguntaSerializer,
        responses={200: RespuestaEncuestaSerializer},
    )
    @action(detail=True, methods=['post'], url_path='responder')
    def responder(self, request, pk=None):
        sesion = self.get_object()

        if sesion.estado == 'COMPLETADA':
            return Response(
                {'detail': 'La sesión ya está completada. No se pueden modificar respuestas.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ResponderPreguntaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        pregunta_id = serializer.validated_data['pregunta_id']
        miembro_id = serializer.validated_data.get('miembro_id')
        valor = serializer.validated_data['valor']

        # Verificar que la pregunta pertenece al instrumento de la sesión
        try:
            pregunta = Pregunta.objects.get(
                pk=pregunta_id,
                capitulo__instrumento=sesion.instrumento,
            )
        except Pregunta.DoesNotExist:
            return Response(
                {'detail': f'La pregunta {pregunta_id} no pertenece al instrumento de esta sesión.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Sprint 21 — resolver miembro según nivel de la pregunta
        miembro, err = _resolver_miembro(sesion, pregunta, miembro_id)
        if err:
            return Response(err, status=status.HTTP_400_BAD_REQUEST)

        # Upsert de la respuesta — uniqueness por (sesion, pregunta, miembro)
        respuesta, created = RespuestaEncuesta.objects.update_or_create(
            sesion=sesion,
            pregunta=pregunta,
            miembro=miembro,
            defaults={'valor': valor},
        )

        # Actualizar estado y porcentaje
        nuevo_pct = sesion.recalcular_porcentaje()
        SesionEncuesta.objects.filter(pk=sesion.pk).update(
            porcentaje_completado=nuevo_pct,
            estado='EN_PROGRESO',
        )

        LogAcceso.registrar(
            usuario=request.user,
            accion='RESPONDER_PREGUNTA',
            recurso='RespuestaEncuesta',
            recurso_id=str(respuesta.id),
            ip=_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            resultado='EXITO',
            detalle={
                'sesion_id': str(sesion.id),
                'pregunta_codigo': pregunta.codigo_externo,
                'creada': created,
            },
        )

        return Response(
            RespuestaEncuestaSerializer(respuesta).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @extend_schema(
        summary='Finalizar sesión de encuesta',
        description='Marca la sesión como COMPLETADA. Solo se puede hacer una vez.',
        tags=['Encuestas'],
        request=FinalizarSesionSerializer,
        responses={200: SesionEncuestaDetalleSerializer},
    )
    @action(detail=True, methods=['post'], url_path='finalizar')
    def finalizar(self, request, pk=None):
        sesion = self.get_object()

        if sesion.estado == 'COMPLETADA':
            return Response(
                {'detail': 'La sesión ya está completada.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = FinalizarSesionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        observaciones = serializer.validated_data.get('observaciones', '')

        pct_final = sesion.recalcular_porcentaje()
        sesion.estado = 'COMPLETADA'
        sesion.fecha_fin = timezone.now()
        sesion.porcentaje_completado = pct_final
        if observaciones:
            sesion.observaciones = observaciones
        sesion.save(update_fields=[
            'estado', 'fecha_fin', 'porcentaje_completado', 'observaciones'
        ])

        # La caracterización que acabamos de hacer cuenta como caracterización.
        #
        # Parece obvio y no lo estaba: `fecha_ult_caracterizacion` solo la escribía
        # `cargar_fechas_caracterizacion` leyendo el Oracle legacy, así que una
        # persona caracterizada en SICAV seguía figurando como "nunca caracterizada"
        # y volvía a aparecer habilitada en la búsqueda siguiente — el encuestador
        # podía caracterizarla otra vez el mismo día sin que nada lo avisara.
        #
        # Se marca a TODOS los miembros del hogar, no solo al autorizado: la
        # caracterización cuelga del hogar, que es el mismo criterio con el que el
        # legacy calcula la fecha (MAX de GIC_HOGAR por miembro).
        marcados = self._marcar_caracterizadas(sesion)
        habilitaciones_usadas = self._consumir_habilitaciones(sesion)

        LogAcceso.registrar(
            usuario=request.user,
            accion='FINALIZAR_ENCUESTA',
            recurso='SesionEncuesta',
            recurso_id=str(sesion.id),
            ip=_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            resultado='EXITO',
            detalle={'porcentaje_completado': pct_final, 'hogar_id': str(sesion.hogar_id),
                     'victimas_marcadas': marcados,
                     'habilitaciones_usadas': habilitaciones_usadas},
        )

        # Cerrar la encuesta es lo que dispara la escritura hacia el Oracle legacy.
        #
        # Va en `on_commit` a propósito: encolar dentro de la transacción dejaría al
        # worker leyendo un hogar que la base todavía no expone —o que desaparece si
        # la transacción revierte—. Y `encolar_hogar` no propaga excepciones: que el
        # broker esté caído no puede impedir que un encuestador cierre su encuesta;
        # el hogar queda en PostgreSQL y se reprocesa con `escribir_a_oracle`.
        #
        # Si ORACLE_SYNC.AUTOMATICA está apagado (el default), la tarea corre y se
        # marca omitida sin tocar Oracle.
        transaction.on_commit(lambda: encolar_hogar(sesion.hogar_id))

        return Response(SesionEncuestaDetalleSerializer(sesion).data)

    @staticmethod
    def _marcar_caracterizadas(sesion) -> int:
        """
        Deja constancia en el padrón de que estas personas ya fueron caracterizadas.

        Devuelve cuántas víctimas se marcaron. No falla la finalización si algo sale
        mal: la encuesta ya está guardada y cerrar es lo que el encuestador necesita;
        una fecha que no se pudo escribir se recupera con la sincronización.
        """
        from apps.hogares.models import MiembroHogar
        from apps.victimas.models import Victima

        try:
            ids = set(
                MiembroHogar.objects
                .filter(hogar_id=sesion.hogar_id, victima_id__isnull=False)
                .values_list('victima_id', flat=True)
            )
            autorizado_id = getattr(sesion.hogar, 'autorizado_id', None)
            if autorizado_id:
                ids.add(autorizado_id)
            if not ids:
                return 0
            return Victima.objects.filter(id__in=ids).update(
                fecha_ult_caracterizacion=sesion.fecha_fin,
                # La regla de 2 años: recién caracterizada, deja de estar disponible.
                habilitado_para_caracterizacion=False,
            )
        except Exception:                                      # noqa: BLE001
            logger.exception(
                'No se pudo marcar la fecha de caracterización de la sesión %s',
                sesion.id)
            return 0

    @staticmethod
    def _consumir_habilitaciones(sesion) -> int:
        """
        Consume las habilitaciones de excepción que esta caracterización usó.

        Una habilitación es de un solo uso: si quedara vigente después de
        usarse, esa persona tendría permiso permanente para saltarse la regla de
        los dos años, que es justo lo que la regla existe para impedir.

        Se consumen las de todo el hogar y no solo la del autorizado, por el
        mismo criterio con el que se marcan las fechas: la caracterización
        cuelga del hogar.

        No falla la finalización si algo sale mal — la encuesta ya está
        guardada—, pero sí queda en el log: una habilitación que no se consumió
        es un permiso abierto, y alguien tiene que poder encontrarlo.
        """
        from django.utils import timezone

        from apps.hogares.models import MiembroHogar

        from .models import ExcepcionVigencia

        try:
            ids = set(
                MiembroHogar.objects
                .filter(hogar_id=sesion.hogar_id, victima_id__isnull=False)
                .values_list('victima_id', flat=True)
            )
            autorizado_id = getattr(sesion.hogar, 'autorizado_id', None)
            if autorizado_id:
                ids.add(autorizado_id)
            if not ids:
                return 0
            return (ExcepcionVigencia.objects
                    .filter(victima_id__in=ids, estado=ExcepcionVigencia.VIGENTE)
                    .update(estado=ExcepcionVigencia.USADA,
                            usada_en_sesion=sesion,
                            usada_at=timezone.now()))
        except Exception:                                      # noqa: BLE001
            logger.exception(
                'No se pudieron consumir las habilitaciones de la sesión %s — '
                'quedan VIGENTES y hay que revisarlas a mano', sesion.id)
            return 0

    @extend_schema(
        summary='Guardar múltiples respuestas en una sola transacción',
        description=(
            'Recibe una lista de {pregunta_id, valor} y hace upsert de todas en una '
            'transacción atómica. Recalcula el porcentaje una sola vez al final. '
            'Más eficiente que llamar /responder/ N veces desde el móvil.'
        ),
        tags=['Encuestas'],
        request=ResponderBulkSerializer,
    )
    @action(detail=True, methods=['post'], url_path='responder-bulk')
    def responder_bulk(self, request, pk=None):
        sesion = self.get_object()

        if sesion.estado == 'COMPLETADA':
            return Response(
                {'detail': 'La sesión ya está completada. No se pueden modificar respuestas.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ResponderBulkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        items = serializer.validated_data['respuestas']

        ids = [str(i['pregunta_id']) for i in items]
        preguntas_qs = Pregunta.objects.filter(
            pk__in=ids,
            capitulo__instrumento=sesion.instrumento,
        )
        pregunta_map = {str(p.pk): p for p in preguntas_qs}

        invalidas = [pid for pid in ids if pid not in pregunta_map]
        if invalidas:
            return Response(
                {'detail': f'Preguntas no pertenecen al instrumento de esta sesión: {invalidas[:3]}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Sprint 21 — pre-cachear miembros del hogar (1 query) para validar
        # cada item sin N+1.
        miembros_map = {
            str(m.pk): m for m in MiembroHogar.objects.filter(hogar=sesion.hogar_id)
        }

        creadas, actualizadas = 0, 0
        errores_nivel = []
        with transaction.atomic():
            for item in items:
                pid = str(item['pregunta_id'])
                pregunta = pregunta_map[pid]
                miembro_id = item.get('miembro_id')
                miembro_id_str = str(miembro_id) if miembro_id else None

                # Validación HOGAR vs PERSONA (sin querying — usa el cache)
                if pregunta.nivel == 'HOGAR':
                    if miembro_id_str:
                        errores_nivel.append(
                            f'{pregunta.codigo_externo} es HOGAR pero trae miembro_id'
                        )
                        continue
                    miembro = None
                else:  # PERSONA
                    if not miembro_id_str:
                        errores_nivel.append(
                            f'{pregunta.codigo_externo} es PERSONA pero falta miembro_id'
                        )
                        continue
                    miembro = miembros_map.get(miembro_id_str)
                    if miembro is None:
                        errores_nivel.append(
                            f'miembro {miembro_id_str} no pertenece al hogar'
                        )
                        continue

                _, created = RespuestaEncuesta.objects.update_or_create(
                    sesion=sesion,
                    pregunta=pregunta,
                    miembro=miembro,
                    defaults={'valor': item['valor']},
                )
                if created:
                    creadas += 1
                else:
                    actualizadas += 1

            if errores_nivel:
                # Si hubo cualquier inconsistencia, abortar todo el bulk
                transaction.set_rollback(True)
                return Response(
                    {'detail': 'Errores de nivel HOGAR/PERSONA', 'errores': errores_nivel[:10]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            nuevo_pct = sesion.recalcular_porcentaje()
            SesionEncuesta.objects.filter(pk=sesion.pk).update(
                porcentaje_completado=nuevo_pct,
                estado='EN_PROGRESO',
            )

        LogAcceso.registrar(
            usuario=request.user,
            accion='RESPONDER_PREGUNTA',
            recurso='SesionEncuesta',
            recurso_id=str(sesion.id),
            ip=_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            resultado='EXITO',
            detalle={'accion': 'BULK', 'creadas': creadas, 'actualizadas': actualizadas, 'porcentaje': nuevo_pct},
        )

        return Response({
            'porcentaje_completado': nuevo_pct,
            'creadas': creadas,
            'actualizadas': actualizadas,
        })

    @extend_schema(
        summary='Listar todas las respuestas guardadas de la sesión',
        description='Devuelve {pregunta (UUID), valor} para restaurar borradores en el cliente.',
        tags=['Encuestas'],
        responses={200: RespuestaEncuestaSerializer(many=True)},
    )
    @action(detail=True, methods=['get'], url_path='respuestas')
    def listar_respuestas(self, request, pk=None):
        sesion = self.get_object()
        respuestas = (
            sesion.respuestas
            .select_related('pregunta')
            .order_by('pregunta__orden')
        )
        return Response(RespuestaEncuestaSerializer(respuestas, many=True).data)

    @action(detail=True, methods=['post'], url_path='excepcion-vigencia',
            parser_classes=[MultiPartParser, FormParser])
    def excepcion_vigencia(self, request, pk=None):
        """
        **Retirado el 14-ago-2026.** La excepción ya no se registra desde campo.

        Hasta esa fecha el encuestador elegía la ruta y adjuntaba una foto del
        soporte desde el celular. La operación indicó que el caracterizador no
        debe tener ese documento —le llega al nivel central por canal
        institucional—, así que la autorización se mudó al front web:

            POST /api/habilitaciones/     (perfil con puede_autorizar_excepciones)

        Responde 410 y no 404 a propósito: una APK anterior a la v1.2.0 que
        siga instalada en un celular tiene que poder decirle al encuestador qué
        cambió. Un 404 se lee como "falló la red" y manda a buscar señal.

        (Este endpoint además estaba roto: escribía la auditoría con
        `LogAcceso.objects.create(..., ip=...)`, y ese campo se llama
        `ip_origen` mientras `detalle` es un JSONField. Toda llamada terminaba
        en 500 antes de responder. No se detectó porque ninguna encuestadora
        había entrado todavía.)
        """
        return Response(
            {'detail': 'La excepción de vigencia ya no se registra desde la '
                       'aplicación móvil. Solicítela a su coordinación: se '
                       'autoriza desde la plataforma web y usted la verá '
                       'habilitada al sincronizar.',
             'flujo_actual': 'POST /api/habilitaciones/'},
            status=status.HTTP_410_GONE)
