"""
Views de Hogares SRNI.
Requieren permiso puede_caracterizar para todas las operaciones.
"""
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema, extend_schema_view

from apps.autenticacion.permissions import PuedeConsultarOperacion
from apps.auditoria.models import LogAcceso
from apps.auditoria.red import ip_de_request
from .models import Hogar, MiembroHogar
from .filters import HogarFilterSet
from .serializers import (
    HogarListSerializer, HogarDetalleSerializer,
    AgregarMiembroSerializer, MiembroHogarSerializer,
    CambiarAutorizadoSerializer, RetirarMiembroSerializer,
)


def _ip(request) -> str:
    # Ver apps/auditoria/red.py: el WAF manda `IP:puerto` y sin limpiarlo el
    # INSERT de auditoría falla y la petición responde 500.
    return ip_de_request(request)


def _bloqueo_vigencia_activo() -> bool:
    """
    ¿Sigue en pie la regla de los dos años? (`settings.VIGENCIA`).

    Acá importa por una razón indirecta pero decisiva: mientras el control esté
    activo, encontrarse el hogar de otro encuestador es un caso raro —la vigencia
    ya frenaba antes de llegar—. Retirado el control es el caso corriente, y el
    hogar pasa a ser el de la familia y no la propiedad de quien lo creó.

    Se delega en el repositorio de víctimas para que la condición viva en un solo
    lugar: dos lecturas del mismo interruptor terminarían divergiendo.
    """
    from apps.victimas.repository.base import _bloqueo_vigencia_activo as _fuente

    return _fuente()


@extend_schema_view(
    list=extend_schema(summary='Listar hogares del encuestador', tags=['Hogares']),
    retrieve=extend_schema(summary='Detalle de hogar con miembros', tags=['Hogares']),
    create=extend_schema(summary='Crear nuevo hogar', tags=['Hogares']),
    update=extend_schema(summary='Actualizar hogar', tags=['Hogares']),
    partial_update=extend_schema(summary='Actualizar hogar (parcial)', tags=['Hogares']),
)
class HogarViewSet(viewsets.ModelViewSet):
    """
    CRUD de hogares.
    Al crear un hogar, el autorizado queda registrado automáticamente
    como primer MiembroHogar (rol='MIEMBRO', es_autorizado=True, estado_inclusion='INCLUIDO').
    El listado muestra solo los hogares creados por el encuestador autenticado
    (o todos, si tiene perfil administrador).
    """
    permission_classes = [IsAuthenticated, PuedeConsultarOperacion]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = HogarFilterSet
    ordering_fields = ['created_at', 'updated_at', 'estado', 'numero_personas']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        qs = Hogar.objects.select_related(
            'autorizado', 'municipio__departamento', 'creado_por'
        ).prefetch_related(
            # `miembros__victima` y no solo `miembros`: el serializer de listado
            # lee los nombres y el documento de la víctima vinculada cuando el
            # miembro no los tiene propios. Sin traerla acá, un hogar de seis
            # integrantes dispara seis consultas extra, y el listado de hogares
            # las multiplica por cada fila de la página.
            'miembros__victima__tipo_documento',
            'miembros__tipo_documento',
            'sesiones__instrumento',
            'sesiones__encuestador',
        )

        # Admin y supervisión (ver_reportes) ven todos los hogares; el
        # encuestador de campo solo los suyos.
        if user.puede('administrar') or user.puede('ver_reportes'):
            return qs

        # «Suyos» son los que creó **y** aquellos sobre los que caracterizó. Lo
        # segundo se agregó con el retiro del control de vigencia: si el hogar lo
        # conformó un compañero, la entrevista sigue siendo de quien la hizo, y un
        # encuestador que no puede volver a abrir su propia entrevista no puede
        # corregir nada de lo que capturó.
        propios = Q(creado_por=user) | Q(sesiones__encuestador=user)

        if self.action == 'list':
            # El listado NO se abre. Ver un hogar por estar trabajándolo no es lo
            # mismo que poder navegar los hogares de todo el país: son 2,5 millones
            # de fichas con datos personales de víctimas.
            return qs.filter(propios).distinct()

        # Acceso por id (abrir, agregar integrante, crear la sesión). Con el
        # control de vigencia retirado, el encuestador tiene que poder continuar
        # sobre el hogar que ya existe, sea de quien sea: es el hogar de la persona
        # que tiene enfrente. Filtrarlo por dueño devolvería 404 justo después de
        # que `create` le entregó el id, y el flujo moriría sin explicación —el
        # bloqueo nuevo que el retiro de la vigencia vino a evitar—.
        #
        # Sigue siendo acceso por identificador conocido, no exploración: ese id
        # solo se obtiene conformando el hogar de la persona atendida.
        if not _bloqueo_vigencia_activo():
            return qs.exclude(estado='ARCHIVADO')

        return qs.filter(propios).distinct()

    def get_serializer_class(self):
        if self.action in ('list',):
            return HogarListSerializer
        return HogarDetalleSerializer

    def create(self, request, *args, **kwargs):
        """
        Sprint 21 — validación idempotente: una víctima solo puede ser autorizada
        en UN hogar a la vez (en estado BORRADOR o ACTIVO). Aplica a TODOS los
        usuarios sin excepción.

        Si se intenta crear un segundo hogar para la misma víctima, devolvemos
        el existente con HTTP 200 en lugar de crear duplicado. El cliente
        recibe el mismo flujo que si lo hubiera creado.

        Modelo correcto:
            1 víctima → 1 hogar → N caracterizaciones (1 por instrumento).
        Para probar los 8 instrumentos con una víctima, NO se crean 8 hogares
        sino 1 hogar con 8 sesiones de encuesta (una por instrumento).

        Solo bloquea contra hogares NO archivados — si el anterior está ARCHIVADO,
        sí se puede crear uno nuevo (caso de cambio definitivo de núcleo familiar).
        """
        autorizado_id = request.data.get('autorizado')
        es_admin = request.user.puede('administrar')

        # Mensaje cuando ya existe un hogar activo creado por OTRO encuestador.
        MSG_AJENO = (
            'Esta víctima ya tiene un hogar activo registrado por otro '
            'encuestador. Solicita su reasignación al supervisor.'
        )

        def _no_archivados():
            """Todos los hogares no archivados de esta víctima (de cualquier dueño)."""
            if not autorizado_id:
                return Hogar.objects.none()
            return Hogar.objects.filter(
                autorizado_id=autorizado_id,
            ).exclude(estado='ARCHIVADO').order_by('-created_at')

        def _existente_propio():
            """
            Hogar no archivado idempotente que el usuario PUEDE ver.

            - Admin: cualquier hogar no archivado de la víctima.
            - Con el control de vigencia retirado: cualquiera, de quien sea. **El
              hogar es la familia, no la entrevista**, y el encuestador que está
              parado frente a la persona tiene que poder continuar sobre el hogar
              que ya existe. No se le reasigna la propiedad: `creado_por` no se
              toca —quitárselo al primero le borraría de «mis encuestas» un trabajo
              que sí hizo— y la autoría de cada caracterización vive en su sesión,
              que es donde siempre debió estar.
            - Con el control activo (el default): solo si es propio. Si NO hay
              propio pero SÍ existe uno ajeno, devuelve el ajeno marcado para que
              el caller responda 409 en lugar de exponer un id inaccesible.

            Retorna (hogar, es_propio).
            """
            base = _no_archivados()
            if es_admin or not _bloqueo_vigencia_activo():
                return base.first(), True
            propio = base.filter(creado_por=request.user).first()
            if propio:
                return propio, True
            ajeno = base.first()
            return ajeno, False

        existente, es_propio = _existente_propio()
        if existente:
            if not es_propio:
                # Hogar activo de otro encuestador: el get_queryset le negaría
                # acceso (404 en cadena), así que respondemos 409 explícito.
                return Response({'detail': MSG_AJENO}, status=status.HTTP_409_CONFLICT)
            detalle = HogarDetalleSerializer(existente, context={'request': request})
            return Response(detalle.data, status=status.HTTP_200_OK)

        try:
            with transaction.atomic():
                return super().create(request, *args, **kwargs)
        except IntegrityError:
            # Carrera: otro request creó el hogar entre la verificación de arriba
            # y el INSERT. El constraint uniq_hogar_no_archivado_por_autorizado lo
            # rechazó. Devolvemos el hogar ganador si es accesible; si es ajeno
            # (no-admin), respondemos 409 con el mismo mensaje claro.
            existente, es_propio = _existente_propio()
            if existente:
                if not es_propio:
                    return Response({'detail': MSG_AJENO}, status=status.HTTP_409_CONFLICT)
                detalle = HogarDetalleSerializer(existente, context={'request': request})
                return Response(detalle.data, status=status.HTTP_200_OK)
            raise

    def perform_create(self, serializer):
        hogar = serializer.save(creado_por=self.request.user)

        # ── Auto-insertar el autorizado como primer MiembroHogar ──────────────
        # El autorizado siempre es víctima registrada (estado_inclusion='INCLUIDO').
        # Es el primer integrante: rol='MIEMBRO' + es_autorizado=True.
        MiembroHogar.objects.create(
            hogar=hogar,
            victima=hogar.autorizado,
            rol='MIEMBRO',
            es_autorizado=True,
            estado_inclusion='INCLUIDO',
            parentesco='',          # el autorizado no tiene parentesco relativo a sí mismo
            creado_por=self.request.user,
        )

        LogAcceso.registrar(
            usuario=self.request.user,
            accion='CREAR_HOGAR',
            recurso='Hogar',
            recurso_id=str(hogar.id),
            ip=_ip(self.request),
            user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
            resultado='EXITO',
        )

    @extend_schema(
        summary='Agregar miembro al hogar',
        tags=['Hogares'],
        request=AgregarMiembroSerializer,
        responses={201: MiembroHogarSerializer},
    )
    @action(detail=True, methods=['post'], url_path='agregar-miembro')
    def agregar_miembro(self, request, pk=None):
        hogar = self.get_object()
        serializer = AgregarMiembroSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Los integrantes adicionales nunca son el autorizado (es_autorizado=False por defecto)
        miembro = serializer.save(hogar=hogar, creado_por=request.user, es_autorizado=False)

        LogAcceso.registrar(
            usuario=request.user,
            accion='AGREGAR_MIEMBRO',
            recurso='MiembroHogar',
            recurso_id=str(miembro.id),
            ip=_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            resultado='EXITO',
            detalle={'hogar_id': str(hogar.id)},
        )
        return Response(
            MiembroHogarSerializer(miembro).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        summary='Listar miembros del hogar',
        tags=['Hogares'],
        responses={200: MiembroHogarSerializer(many=True)},
    )
    @action(detail=True, methods=['get'], url_path='miembros')
    def listar_miembros(self, request, pk=None):
        hogar = self.get_object()
        miembros = hogar.miembros.select_related('victima', 'tipo_documento').all()
        return Response(MiembroHogarSerializer(miembros, many=True).data)

    @extend_schema(
        summary='Corregir un integrante, o quitar uno agregado por error',
        description=(
            'PATCH corrige los datos del integrante. DELETE lo quita del hogar, y '
            'solo mientras NO haya una caracterización completada: después de eso, '
            'para registrar que la persona ya no pertenece al hogar se usa la '
            'acción "retirar", que no borra nada.'
        ),
        tags=['Hogares'],
        responses={200: MiembroHogarSerializer},
    )
    @action(detail=True, methods=['patch', 'delete'],
            url_path=r'miembros/(?P<miembro_id>[^/.]+)')
    def editar_miembro(self, request, pk=None, miembro_id=None):
        """
        APK-004 — hasta ahora se podía agregar un integrante pero no corregirlo
        ni quitarlo, ni en la app ni en la API. Quien se equivocaba al capturar
        quedaba con el error adentro del hogar para siempre.

        ─── Tres operaciones distintas, y conviene no confundirlas ──────────
        · **DELETE — «nunca debió existir».** Borra la fila. Solo mientras no
          haya caracterización completada: después, el integrante forma parte de
          algo ya reportado y borrarlo cambiaría un dato entregado.
        · **PATCH — «el dato está mal».** Corrige nombre, documento, parentesco.
          Se permite SIEMPRE, incluso después de una caracterización completada,
          y queda en auditoría. Bloquearlo dejaba el error adentro para siempre,
          y un apellido mal escrito no se arregla solo con el tiempo.
        · **`retirar` — «ya no pertenece al hogar».** Es un hecho histórico, no
          un error, y tiene su propia acción: no borra, registra la novedad con
          su fecha. Ver `retirar_miembro`.

        Hasta el 11-sep-2026 las tres caían en la misma guarda y el único camino
        que quedaba era «solicite el ajuste a su coordinación», que no existe
        como proceso. Con el control de vigencia retirado la recaracterización
        pasó a ser el caso corriente, y con ella las familias que cambiaron.

        Al autorizado no se le toca: es el titular del hogar y quitarlo dejaría
        un hogar sin dueño. Para cambiarlo existe `cambiar-autorizado`.
        """
        hogar = self.get_object()
        miembro = get_object_or_404(MiembroHogar, pk=miembro_id, hogar=hogar)

        if miembro.es_autorizado:
            return Response(
                {'detail': 'No se puede modificar ni quitar a la persona autorizada: '
                           'es el titular del hogar. Use "cambiar autorizado".'},
                status=status.HTTP_409_CONFLICT)

        # Solo el BORRADO queda acotado. Corregir un dato mal capturado se
        # permite siempre: el mensaje que estaba acá mandaba a un proceso que no
        # existe, y el error se quedaba adentro.
        if (request.method == 'DELETE'
                and hogar.sesiones.filter(estado='COMPLETADA').exists()):
            return Response(
                {'detail': 'Este hogar ya tiene una caracterización completada, así '
                           'que no se puede borrar a un integrante ya reportado. Si '
                           'la persona dejó de pertenecer al hogar, use "Retirar del '
                           'hogar": queda registrada la novedad con su fecha y no se '
                           'altera la caracterización anterior.'},
                status=status.HTTP_409_CONFLICT)

        if request.method == 'DELETE':
            datos = {'hogar_id': str(hogar.id),
                     'documento_hash': getattr(miembro, 'numero_documento_hash', '')}
            miembro.delete()
            LogAcceso.registrar(
                usuario=request.user,
                accion='QUITAR_MIEMBRO',
                recurso='MiembroHogar',
                recurso_id=str(miembro_id),
                ip=_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                resultado='EXITO',
                detalle=datos,
            )
            return Response(status=status.HTTP_204_NO_CONTENT)

        serializer = AgregarMiembroSerializer(miembro, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        miembro = serializer.save()

        LogAcceso.registrar(
            usuario=request.user,
            accion='EDITAR_MIEMBRO',
            recurso='MiembroHogar',
            recurso_id=str(miembro.id),
            ip=_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            resultado='EXITO',
            detalle={'hogar_id': str(hogar.id), 'campos': list(request.data.keys())},
        )
        return Response(MiembroHogarSerializer(miembro).data)

    @extend_schema(
        summary='Retirar un integrante del hogar (novedad, no borrado)',
        description=(
            'Registra que la persona dejó de pertenecer al hogar desde una fecha. '
            'NO borra la fila ni altera la caracterización anterior. Exige motivo y '
            'fecha del hecho.'
        ),
        tags=['Hogares'],
        request=RetirarMiembroSerializer,
        responses={200: MiembroHogarSerializer},
    )
    @action(detail=True, methods=['post'],
            url_path=r'miembros/(?P<miembro_id>[^/.]+)/retirar')
    def retirar_miembro(self, request, pk=None, miembro_id=None):
        """
        La familia cambió entre una caracterización y la siguiente.

        ─── Por qué no alcanzaba con borrar ─────────────────────────────────
        Borrar la fila haría dos daños a la vez: las respuestas de la
        caracterización anterior quedarían apuntando a un integrante que el
        sistema ya no conoce, y se perdería el hecho —cuándo y por qué se fue—
        que es justamente lo que la recaracterización viene a registrar.

        Acá la fila SE QUEDA. Lo que se agrega es la fecha desde la cual la
        persona ya no pertenece al hogar. Con eso, cada entrevista puede decir
        quiénes eran el hogar en SU momento: la anterior sigue siendo válida y la
        nueva no pregunta por quien ya no está.

        ─── Se permite con caracterizaciones completadas, y es el punto ──────
        Es exactamente el caso para el que existe. La guarda que sí se conserva
        es la del borrado, en `editar_miembro`.

        El autorizado no se retira: es el titular del hogar. Si es él quien dejó
        de pertenecer, lo que corresponde es cambiar el autorizado.
        """
        hogar = self.get_object()
        miembro = get_object_or_404(MiembroHogar, pk=miembro_id, hogar=hogar)

        if miembro.es_autorizado:
            return Response(
                {'detail': 'No se puede retirar a la persona autorizada: es el '
                           'titular del hogar. Si dejó de pertenecer, cambie primero '
                           'el autorizado y luego retírela.'},
                status=status.HTTP_409_CONFLICT)

        serializer = RetirarMiembroSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        datos = serializer.validated_data

        # `retirar` es idempotente: no pisa la fecha del primer retiro. La app
        # reintenta cuando la red se corta, así que esto llega dos veces con
        # normalidad y no puede quedar en error.
        cambio = miembro.retirar(
            usuario=request.user,
            motivo=datos['motivo'],
            fecha=datos['fecha'],
            observacion=datos.get('observacion', ''),
        )

        LogAcceso.registrar(
            usuario=request.user,
            accion='RETIRAR_MIEMBRO',
            recurso='MiembroHogar',
            recurso_id=str(miembro.id),
            ip=_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            resultado='EXITO',
            detalle={'hogar_id': str(hogar.id), 'motivo': datos['motivo'],
                     'fecha': str(datos['fecha']), 'ya_estaba_retirado': not cambio},
        )
        return Response(MiembroHogarSerializer(miembro).data)

    @extend_schema(
        summary='Deshacer el retiro de un integrante',
        description='Devuelve al integrante al hogar. Para un retiro registrado por error.',
        tags=['Hogares'],
        responses={200: MiembroHogarSerializer},
    )
    @action(detail=True, methods=['post'],
            url_path=r'miembros/(?P<miembro_id>[^/.]+)/reincorporar')
    def reincorporar_miembro(self, request, pk=None, miembro_id=None):
        """
        Deshace un retiro.

        Existe porque el encuestador se equivoca de fila, y un retiro registrado
        por error no puede quedar para siempre: sin esto la única salida sería
        pedir un ajuste a soporte, que es el callejón que este trabajo vino a
        cerrar. Queda en auditoría, con quién lo deshizo.
        """
        hogar = self.get_object()
        miembro = get_object_or_404(MiembroHogar, pk=miembro_id, hogar=hogar)

        retiro_previo = {'fecha': str(miembro.retirado_en or ''),
                         'motivo': miembro.motivo_retiro}
        cambio = miembro.reincorporar()

        LogAcceso.registrar(
            usuario=request.user,
            accion='REINCORPORAR_MIEMBRO',
            recurso='MiembroHogar',
            recurso_id=str(miembro.id),
            ip=_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            resultado='EXITO',
            detalle={'hogar_id': str(hogar.id), 'retiro_deshecho': retiro_previo,
                     'no_estaba_retirado': not cambio},
        )
        return Response(MiembroHogarSerializer(miembro).data)

    @extend_schema(
        summary='Subir constancia de tutor/cuidador de un miembro',
        description=(
            'Sube el documento que acredita el rol de TUTOR o CUIDADOR_PERMANENTE '
            '(Manual §5.1.2). multipart/form-data con `miembro_id` y `archivo`. '
            'Solo se acepta para miembros con esos roles.'
        ),
        tags=['Hogares'],
        responses={200: MiembroHogarSerializer},
    )
    @action(
        detail=True, methods=['post'], url_path='subir-constancia',
        parser_classes=[MultiPartParser, FormParser],
    )
    def subir_constancia(self, request, pk=None):
        hogar = self.get_object()
        miembro_id = request.data.get('miembro_id')
        archivo = request.FILES.get('archivo')

        if not miembro_id or not archivo:
            return Response(
                {'detail': 'Se requieren `miembro_id` y `archivo`.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            miembro = hogar.miembros.get(id=miembro_id)
        except MiembroHogar.DoesNotExist:
            return Response(
                {'detail': 'El miembro no pertenece a este hogar.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        if miembro.rol not in ('TUTOR', 'CUIDADOR_PERMANENTE'):
            return Response(
                {'detail': 'Solo los roles TUTOR o CUIDADOR_PERMANENTE requieren constancia.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Reemplaza la constancia previa si existía (evita huérfanos en disco).
        if miembro.constancia:
            miembro.constancia.delete(save=False)
        miembro.constancia = archivo
        miembro.constancia_nombre = archivo.name[:255]
        miembro.constancia_subida_en = timezone.now()
        miembro.save(update_fields=[
            'constancia', 'constancia_nombre', 'constancia_subida_en',
        ])

        LogAcceso.registrar(
            usuario=request.user,
            accion='SUBIR_CONSTANCIA',
            recurso='MiembroHogar',
            recurso_id=str(miembro.id),
            ip=_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            resultado='EXITO',
            detalle={'hogar_id': str(hogar.id), 'rol': miembro.rol},
        )
        return Response(MiembroHogarSerializer(miembro).data)

    @extend_schema(
        summary='Cambiar autorizado del hogar',
        description=(
            'Reemplaza el autorizado del hogar con otra Victima registrada en el sistema. '
            'Actualiza también la marca es_autorizado en la tabla MiembroHogar. '
            'El miembro anterior conserva su registro en el hogar (es_autorizado pasa a False).'
        ),
        tags=['Hogares'],
        request=CambiarAutorizadoSerializer,
        responses={200: HogarDetalleSerializer},
    )
    @action(detail=True, methods=['patch'], url_path='cambiar-autorizado')
    def cambiar_autorizado(self, request, pk=None):
        from apps.victimas.models import Victima
        hogar = self.get_object()
        serializer = CambiarAutorizadoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        victima_id = serializer.validated_data['victima_id']
        try:
            nueva_autorizada = Victima.objects.get(pk=victima_id)
        except Victima.DoesNotExist:
            return Response(
                {'detail': 'Víctima no encontrada.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        autorizado_anterior_id = str(hogar.autorizado_id)

        # Desmarcar autorizado anterior en MiembroHogar
        hogar.miembros.filter(es_autorizado=True).update(es_autorizado=False)

        # Actualizar el FK en Hogar
        hogar.autorizado = nueva_autorizada
        hogar.save(update_fields=['autorizado', 'updated_at'])

        # Marcar (o crear) el nuevo autorizado en MiembroHogar
        miembro, created = MiembroHogar.objects.get_or_create(
            hogar=hogar,
            victima=nueva_autorizada,
            defaults={
                'rol': 'MIEMBRO',
                'es_autorizado': True,
                'estado_inclusion': 'INCLUIDO',
                'creado_por': request.user,
            },
        )
        if not created:
            miembro.es_autorizado = True
            miembro.save(update_fields=['es_autorizado'])

        LogAcceso.registrar(
            usuario=request.user,
            accion='CAMBIAR_AUTORIZADO',
            recurso='Hogar',
            recurso_id=str(hogar.id),
            ip=_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            resultado='EXITO',
            detalle={
                'autorizado_anterior': autorizado_anterior_id,
                'autorizado_nuevo': str(victima_id),
            },
        )

        return Response(HogarDetalleSerializer(hogar).data)
