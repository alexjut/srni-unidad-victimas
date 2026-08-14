"""
Views de Hogares SRNI.
Requieren permiso puede_caracterizar para todas las operaciones.
"""
from django.db import IntegrityError, transaction
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
    CambiarAutorizadoSerializer,
)


def _ip(request) -> str:
    # Ver apps/auditoria/red.py: el WAF manda `IP:puerto` y sin limpiarlo el
    # INSERT de auditoría falla y la petición responde 500.
    return ip_de_request(request)


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
            'miembros',
            'sesiones__instrumento',
            'sesiones__encuestador',
        )

        # Admin y supervisión (ver_reportes) ven todos los hogares; el
        # encuestador de campo solo los que él creó.
        if not (user.puede('administrar') or user.puede('ver_reportes')):
            qs = qs.filter(creado_por=user)
        return qs

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
            - No-admin: solo si es propio (creado_por = request.user). Si NO hay
              propio pero SÍ existe uno ajeno, devuelve el ajeno marcado para que
              el caller responda 409 en lugar de exponer un id inaccesible.

            Retorna (hogar, es_propio).
            """
            base = _no_archivados()
            if es_admin:
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
        summary='Corregir o quitar un integrante agregado por error',
        description=(
            'PATCH corrige los datos del integrante; DELETE lo quita del hogar. '
            'Solo mientras el hogar NO tenga una caracterización completada.'
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

        ─── Quitar es BORRAR, y solo acá ────────────────────────────────────
        Se borra la fila en vez de marcarla con un estado, porque esto atiende
        un caso muy concreto: **el integrante nunca debió existir**. Es distinto
        de «esta persona ya no vive en el hogar», que sí es un hecho histórico y
        pide una novedad hacia el legado — eso queda pendiente de definir, y por
        eso la operación está acotada.

        La guarda es esa acotación: si el hogar ya tiene una encuesta
        COMPLETADA, el integrante forma parte de algo que ya se reportó y
        borrarlo cambiaría un dato entregado. Ahí se responde 409.

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

        if hogar.sesiones.filter(estado='COMPLETADA').exists():
            return Response(
                {'detail': 'Este hogar ya tiene una caracterización completada. '
                           'No se pueden quitar ni corregir integrantes de un dato '
                           'ya reportado; solicite el ajuste a su coordinación.'},
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
