"""Admin de auditoría de seguridad — vista de SOLO LECTURA del LogAcceso.

El LogAcceso es un registro inmutable (Ley 1581). Desde el admin se puede
consultar/filtrar/buscar la traza de seguridad (logins, accesos denegados,
bloqueos por intentos fallidos, búsquedas RNI, etc.), pero NO crear/editar/borrar.
"""
from django.contrib import admin

from .models import LogAcceso


@admin.register(LogAcceso)
class LogAccesoAdmin(admin.ModelAdmin):
    list_display = (
        'timestamp', 'codigo_usuario', 'accion', 'resultado',
        'ip_origen', 'recurso', 'recurso_id',
    )
    list_filter = ('accion', 'resultado', 'timestamp')
    search_fields = ('codigo_usuario', 'recurso', 'recurso_id', 'ip_origen')
    date_hierarchy = 'timestamp'
    ordering = ('-timestamp',)
    list_per_page = 50

    # ── Inmutable: solo lectura desde el admin ──────────────────────────────────
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]
