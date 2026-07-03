"""
Admin de Víctimas — NUNCA mostrar PII descifrado en el panel.
El admin muestra solo el hash del documento para identificación interna.
"""
from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.decorators import display
from .models import Victima


@admin.register(Victima)
class VictimaAdmin(ModelAdmin):
    # Solo campos que no revelan PII (estado/género/etnia como badges de color)
    list_display = (
        'hash_corto', 'tipo_documento', 'genero_badge',
        'etnia_badge', 'estado_ruv_badge',
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

    # ── Badges de color (presentación; los filtros usan el campo real) ──────────
    @display(description='Estado RUV', ordering='estado_ruv', label={
        'Incluido en RUV': 'success',
        'En proceso de valoración': 'info',
        'No incluido en RUV': 'warning',
        'Excluido del RUV': 'danger',
    })
    def estado_ruv_badge(self, obj):
        return obj.get_estado_ruv_display()

    @display(description='Género', ordering='genero', label={
        'Masculino': 'info',
        'Femenino': 'warning',
    })
    def genero_badge(self, obj):
        return obj.get_genero_display()

    @display(description='Pertenencia étnica', ordering='pertenencia_etnica', label={
        # 'Ninguna' se omite a propósito → badge neutro (gris).
        'Indígena': 'info',
        'Afrocolombiano / Afrodescendiente': 'info',
        'Pueblo Rom / Gitano': 'info',
        'Raizal del Archipiélago': 'info',
        'Palenquero de San Basilio': 'info',
    })
    def etnia_badge(self, obj):
        return obj.get_pertenencia_etnica_display()

    def has_add_permission(self, request):
        # Víctimas solo se crean via API, nunca desde el admin
        return False
