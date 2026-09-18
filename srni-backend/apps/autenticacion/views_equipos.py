"""
Equipos: quién supervisa a quién.

La visibilidad del sistema era binaria —o ves lo tuyo, o ves todo el país—, así que un
supervisor no podía mirar a los suyos sin ver a los 1.157 encuestadores. Acá vive el
tercer alcance, «lo de mi equipo», y el helper `usuarios_visibles_para` que las demás
vistas van a usar para recortar sus consultas.
"""
from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.auditoria.models import LogAcceso

from .models import Equipo, MiembroEquipo, Usuario
from .serializers_equipos import (
    AsignarMiembrosSerializer, EquipoDetalleSerializer, EquipoSerializer,
    UsuarioDeEquipoSerializer,
)


def _ip(request):
    adelante = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if adelante:
        # El WAF manda la IP con el puerto; quedarse con el host.
        return adelante.split(',')[0].strip().rsplit(':', 1)[0] if adelante.count(':') == 1 \
            else adelante.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def equipos_visibles_para(usuario):
    """
    Qué equipos puede ver quien pregunta.

    · Administrador: todos.
    · Coordinador (ve reportes): los de su área si la tiene, si no, todos —hoy los
      usuarios no tienen área propia, y recortar por una que no existe dejaría al
      coordinador sin ver nada.
    · Supervisor: el suyo.
    · Encuestador: ninguno. No es un castigo: la jerarquía es para organizar y
      seguir, y él no organiza a nadie.
    """
    qs = Equipo.objects.select_related('supervisor', 'direccion_territorial')
    if usuario.puede('administrar'):
        return qs
    if usuario.puede('ver_reportes'):
        return qs
    return qs.filter(supervisor=usuario)


def usuarios_visibles_para(usuario):
    """
    Las personas cuyo trabajo puede mirar quien pregunta. El tercer alcance.

    Devuelve un queryset de usuarios para recortar consultas de sesiones, hogares y
    reportes. El administrador ve a todos; el supervisor, a su equipo y a sí mismo;
    el resto, solo a sí mismo.
    """
    if usuario.puede('administrar'):
        return Usuario.objects.all()

    equipos = Equipo.objects.filter(supervisor=usuario, activo=True)
    if not equipos.exists():
        return Usuario.objects.filter(pk=usuario.pk)

    del_equipo = Q(
        pertenencias_equipo__equipo__in=equipos,
        pertenencias_equipo__hasta__isnull=True,
    )
    return Usuario.objects.filter(Q(pk=usuario.pk) | del_equipo).distinct()


class EquipoViewSet(viewsets.ModelViewSet):
    """CRUD de equipos y asignación de encuestadores."""
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        qs = equipos_visibles_para(self.request.user)
        dt = self.request.query_params.get('direccion_territorial')
        if dt:
            qs = qs.filter(direccion_territorial_id=dt)
        return qs.order_by('nombre')

    def get_serializer_class(self):
        if self.action in ('retrieve', 'mio'):
            return EquipoDetalleSerializer
        return EquipoSerializer

    def _solo_gestores(self):
        """Crear, cambiar o borrar equipos es de quien organiza, no de quien captura."""
        u = self.request.user
        return u.puede('administrar') or u.puede('ver_reportes')

    def create(self, request, *args, **kwargs):
        if not self._solo_gestores():
            return Response(
                {'detail': 'No tiene permiso para crear equipos.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if not self._solo_gestores():
            return Response(
                {'detail': 'No tiene permiso para modificar equipos.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """
        Un equipo no se borra: se desactiva.

        Borrarlo se llevaría por delante la historia de quién supervisaba a quién, que
        es justo lo que esta tabla existe para conservar.
        """
        if not self._solo_gestores():
            return Response(
                {'detail': 'No tiene permiso para desactivar equipos.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        equipo = self.get_object()
        equipo.activo = False
        equipo.save(update_fields=['activo', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        summary='El equipo del supervisor que consulta',
        tags=['Equipos'],
        responses={200: EquipoDetalleSerializer},
    )
    @action(detail=False, methods=['get'], url_path='mio')
    def mio(self, request):
        equipo = (
            Equipo.objects.filter(supervisor=request.user, activo=True)
            .select_related('supervisor', 'direccion_territorial')
            .first()
        )
        if not equipo:
            return Response(
                {'detail': 'Usted no tiene un equipo a cargo.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(EquipoDetalleSerializer(equipo).data)

    @extend_schema(
        summary='Agregar encuestadores al equipo (varios a la vez)',
        tags=['Equipos'],
        request=AsignarMiembrosSerializer,
        responses={200: EquipoDetalleSerializer},
    )
    @action(detail=True, methods=['post'], url_path='miembros')
    def agregar_miembros(self, request, pk=None):
        equipo = self.get_object()
        if not (self._solo_gestores() or equipo.supervisor_id == request.user.id):
            return Response(
                {'detail': 'Solo el supervisor del equipo o la coordinación pueden asignar.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = AsignarMiembrosSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        resultado = serializer.asignar(equipo, serializer.validated_data['usuarios'], request.user)

        LogAcceso.registrar(
            usuario=request.user,
            accion='CAMBIO_USUARIO',
            recurso='Equipo',
            recurso_id=str(equipo.id),
            ip=_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            resultado='EXITO',
            detalle={'operacion': 'asignar_a_equipo', **resultado},
        )
        return Response(EquipoDetalleSerializer(equipo).data)

    @extend_schema(
        summary='Sacar a un encuestador del equipo',
        tags=['Equipos'],
        responses={200: EquipoDetalleSerializer},
    )
    @action(detail=True, methods=['delete'], url_path=r'miembros/(?P<usuario_id>[^/.]+)')
    def quitar_miembro(self, request, pk=None, usuario_id=None):
        equipo = self.get_object()
        if not (self._solo_gestores() or equipo.supervisor_id == request.user.id):
            return Response(
                {'detail': 'Solo el supervisor del equipo o la coordinación pueden quitar.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        pertenencia = MiembroEquipo.objects.filter(
            equipo=equipo, usuario_id=usuario_id, hasta__isnull=True,
        ).first()
        if not pertenencia:
            return Response(
                {'detail': 'Esa persona no pertenece hoy a este equipo.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Se cierra, no se borra: quién supervisaba a quién en agosto es una pregunta
        # que se va a hacer.
        pertenencia.hasta = timezone.localdate()
        pertenencia.save(update_fields=['hasta'])

        LogAcceso.registrar(
            usuario=request.user,
            accion='CAMBIO_USUARIO',
            recurso='Equipo',
            recurso_id=str(equipo.id),
            ip=_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            resultado='EXITO',
            detalle={'operacion': 'quitar_de_equipo', 'usuario_id': str(usuario_id)},
        )
        return Response(EquipoDetalleSerializer(equipo).data)

    @extend_schema(
        summary='Encuestadores sin equipo (para armar uno)',
        tags=['Equipos'],
        responses={200: UsuarioDeEquipoSerializer(many=True)},
    )
    @action(detail=False, methods=['get'], url_path='sin-equipo')
    def sin_equipo(self, request):
        # Subconsulta y no `.exclude(pertenencias_equipo__hasta__isnull=True)`: con una
        # relación inversa, ese exclude arma un LEFT JOIN y a quien NO tiene ninguna
        # pertenencia le deja `hasta` en NULL, así que lo excluía también. Resultado:
        # la lista de «sin equipo» salía vacía, que es justo al revés.
        con_equipo = MiembroEquipo.objects.filter(
            hasta__isnull=True).values('usuario_id')
        usuarios = (
            Usuario.objects.filter(activo=True, perfil__codigo='ENCUESTADOR')
            .exclude(pk__in=con_equipo)
            .select_related('perfil')
            .order_by('nombre_completo')
        )
        busqueda = request.query_params.get('busqueda', '').strip()
        if busqueda:
            usuarios = usuarios.filter(
                Q(codigo_usuario__icontains=busqueda) | Q(nombre_completo__icontains=busqueda)
            )
        return Response(UsuarioDeEquipoSerializer(usuarios[:200], many=True).data)
