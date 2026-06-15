"""
Módulo de administración de usuarios (panel web — solo administradores).

CRUD de usuarios + acciones (resetear contraseña, activar/desactivar) y
listado de perfiles para los formularios.
"""
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Perfil, Usuario
from .permissions import PuedeAdministrar
from .serializers_admin import (
    PerfilSerializer,
    UsuarioAdminSerializer,
    UsuarioCrearSerializer,
)


class UsuarioAdminViewSet(viewsets.ModelViewSet):
    """
    /api/usuarios/                 GET (lista) · POST (crear)
    /api/usuarios/{id}/            GET · PATCH (editar) · DELETE (desactiva, no borra)
    /api/usuarios/{id}/reset_password/   POST {password}
    /api/usuarios/{id}/activar/          POST
    /api/usuarios/{id}/desactivar/       POST
    /api/usuarios/perfiles/              GET (perfiles para el dropdown)
    """
    queryset = Usuario.objects.select_related("perfil").order_by("codigo_usuario")
    permission_classes = [PuedeAdministrar]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["codigo_usuario", "nombre_completo", "email"]
    filterset_fields = ["activo", "perfil__codigo"]
    ordering_fields = ["codigo_usuario", "nombre_completo", "created_at"]

    def get_serializer_class(self):
        if self.action == "create":
            return UsuarioCrearSerializer
        return UsuarioAdminSerializer

    def destroy(self, request, *args, **kwargs):
        """No se borra físicamente: se desactiva (preserva integridad y auditoría)."""
        usuario = self.get_object()
        usuario.activo = False
        usuario.save(update_fields=["activo"])
        return Response(
            {"detail": "Usuario desactivado."}, status=status.HTTP_200_OK
        )

    @action(detail=True, methods=["post"])
    def reset_password(self, request, pk=None):
        usuario = self.get_object()
        password = request.data.get("password", "")
        if len(password) < 8:
            return Response(
                {"detail": "La contraseña debe tener al menos 8 caracteres."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        usuario.set_password(password)
        usuario.save(update_fields=["password"])
        return Response({"detail": "Contraseña actualizada."})

    @action(detail=True, methods=["post"])
    def activar(self, request, pk=None):
        usuario = self.get_object()
        usuario.activo = True
        usuario.save(update_fields=["activo"])
        return Response({"detail": "Usuario activado."})

    @action(detail=True, methods=["post"])
    def desactivar(self, request, pk=None):
        usuario = self.get_object()
        usuario.activo = False
        usuario.save(update_fields=["activo"])
        return Response({"detail": "Usuario desactivado."})

    @action(detail=False, methods=["get"])
    def perfiles(self, request):
        perfiles = Perfil.objects.filter(activo=True).order_by("nombre")
        return Response(PerfilSerializer(perfiles, many=True).data)
