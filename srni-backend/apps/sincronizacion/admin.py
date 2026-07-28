"""Admin de auditoría — el ledger de escritura a Oracle es SOLO LECTURA."""
from django.contrib import admin

from .models import RegistroEscrituraOracle


@admin.register(RegistroEscrituraOracle)
class RegistroEscrituraOracleAdmin(admin.ModelAdmin):
    list_display = ("hogar", "paso", "origen_id", "estado", "destino_hog_codigo",
                    "destino_per_idpersona", "destino_entorno", "intento", "actualizado_en")
    list_filter = ("paso", "estado", "destino_entorno")
    search_fields = ("hogar__codigo_hogar", "destino_hog_codigo", "origen_id")
    readonly_fields = [f.name for f in RegistroEscrituraOracle._meta.fields]
    ordering = ("-actualizado_en",)

    def has_add_permission(self, request):
        return False  # el ledger solo lo escribe el escritor, nunca a mano.

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
