from rest_framework.permissions import BasePermission


class PuedeAdministrar(BasePermission):
    """Solo usuarios con perfil.puede_administrar=True."""
    message = 'Se requiere perfil de administrador.'

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.puede('administrar')
        )


class PuedeBuscarRNI(BasePermission):
    """Solo usuarios con perfil.puede_buscar_rni=True."""
    message = 'Se requiere permiso de búsqueda en el RNI.'

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.puede('buscar_rni')
        )


class PuedeCaracterizar(BasePermission):
    """Solo usuarios con perfil.puede_caracterizar=True."""
    message = 'Se requiere permiso de caracterización.'

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.puede('caracterizar')
        )


class PuedeVerReportes(BasePermission):
    """Solo usuarios con perfil.puede_ver_reportes=True."""
    message = 'Se requiere permiso de acceso a reportes.'

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.puede('ver_reportes')
        )
