from rest_framework.permissions import BasePermission, SAFE_METHODS


def _puede_cualquiera(user, *acciones) -> bool:
    """True si el usuario autenticado tiene AL MENOS uno de los permisos dados."""
    return bool(
        user and
        user.is_authenticated and
        any(user.puede(accion) for accion in acciones)
    )


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
    """
    Acceso al módulo de reportes.

    Lo satisface tanto ``puede_ver_reportes`` como ``puede_administrar``:
    administrar implica poder consultar los reportes agregados. Esto evita
    que un ADMINISTRADOR quede fuera si su perfil aún no tiene marcado el
    flag de reportes (Bug 2 — supervisión/series vacías para el admin).
    """
    message = 'Se requiere permiso de acceso a reportes.'

    def has_permission(self, request, view):
        return _puede_cualquiera(request.user, 'ver_reportes', 'administrar')


class PuedeConsultarOperacion(BasePermission):
    """
    Permiso de datos operativos (hogares, sesiones, producción por encuestador).

    - **Lectura** (GET/HEAD/OPTIONS): cualquier rol operativo — campo
      (``caracterizar``), supervisión (``ver_reportes``) o administración
      (``administrar``). Así el Supervisor puede consultar en solo lectura
      sin tener permiso de caracterización (Bug 3).
    - **Escritura** (POST/PUT/PATCH/DELETE): exclusiva de quien puede
      caracterizar. La supervisión nunca modifica datos de campo.
    """
    message = 'Se requiere permiso de caracterización (escritura) o de consulta (supervisión/reportes).'

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return _puede_cualquiera(user, 'caracterizar', 'ver_reportes', 'administrar')
        return user.puede('caracterizar')
