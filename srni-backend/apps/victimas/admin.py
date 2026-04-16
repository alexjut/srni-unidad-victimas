"""
Admin de Víctimas — NUNCA mostrar PII descifrado en el panel.
El admin muestra solo el hash del documento para identificación interna.
"""
from django.contrib import admin
from .models import Victima


@admin.register(Victima)
class VictimaAdmin(admin.ModelAdmin):
    # Solo campos que no revelan PII
    list_display = (
        'hash_corto', 'tipo_documento', 'genero',
        'pertenencia_etnica', 'estado_ruv',
        'municipio_residencia', 'created_at',
    )
    list_filter = (
        'estado_ruv', 'genero', 'pertenencia_etnica',
        'discapacidad', 'tipo_documento',
    )
    # Búsqueda solo por hash — nunca por nombre o documento
    search_fields = ('numero_documento_hash',)
    ordering = ('-created_at',)
    readonly_fields = (
        'id', 'numero_documento_hash',
        'created_at', 'updated_at',
    )
    # Excluir campos PII del formulario de edición en el admin
    exclude = (
        'numero_documento',
        'primer_nombre', 'segundo_nombre',
        'primer_apellido', 'segundo_apellido',
        'fecha_nacimiento',
    )

    @admin.display(description='Hash doc (8 chars)')
    def hash_corto(self, obj):
        return obj.numero_documento_hash[:8] + '…'

    def has_add_permission(self, request):
        # Víctimas solo se crean via API, nunca desde el admin
        return False
