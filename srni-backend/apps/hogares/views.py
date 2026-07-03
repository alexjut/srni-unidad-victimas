"""
Views de Hogares SRNI.
Requieren permiso puede_caracterizar para todas las operaciones.
"""
from django.db import IntegrityError, transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema, extend_schema_view

from apps.autenticacion.permissions import PuedeCaracterizar
from apps.auditoria.models import LogAcceso
from .models import Hogar, MiembroHogar
from .filters import HogarFilterSet
from .serializers import (
    HogarListSerializer, HogarDetalleSerializer,
    AgregarMiembroSerializer, MiembroHogarSerializer,
    CambiarAutorizadoSerializer,
)


def _ip(request) -> str:
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    return xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR', '')


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
    permission_classes = [IsAuthenticated, PuedeCaracterizar]
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

        if not (user.puede('administrar')):
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
