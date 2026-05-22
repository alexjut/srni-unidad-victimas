from django.contrib import admin
from .models import Hogar, MiembroHogar


class MiembroHogarInline(admin.TabularInline):
    model = MiembroHogar
    extra = 0
    fields = (
        'rol', 'es_autorizado', 'estado_inclusion',
        'parentesco', 'genero', 'fecha_nacimiento',
        'tiene_discapacidad', 'incluido_ruv', 'victima', 'tipo_documento',
    )
    raw_id_fields = ('victima', 'tipo_documento')
    readonly_fields = ('created_at', 'tipo_persona', 'incluido_ruv')


@admin.register(Hogar)
class HogarAdmin(admin.ModelAdmin):
    list_display = ('id_corto', 'estado', 'municipio', 'numero_personas', 'creado_por', 'created_at')
    list_filter = ('estado', 'tipo_vivienda', 'condicion_ocupacion')
    search_fields = ('id',)
    ordering = ('-created_at',)
    readonly_fields = ('id', 'created_at', 'updated_at')
    raw_id_fields = ('autorizado', 'municipio', 'creado_por')
    inlines = [MiembroHogarInline]

    @admin.display(description='ID (corto)')
    def id_corto(self, obj):
        return str(obj.id)[:8] + '…'


@admin.register(MiembroHogar)
class MiembroHogarAdmin(admin.ModelAdmin):
    list_display = ('id', 'hogar', 'rol', 'es_autorizado', 'estado_inclusion', 'genero', 'tiene_discapacidad')
    list_filter = ('rol', 'es_autorizado', 'estado_inclusion', 'genero', 'tiene_discapacidad')
    raw_id_fields = ('hogar', 'victima', 'tipo_documento', 'creado_por')
    readonly_fields = ('id', 'created_at', 'tipo_persona', 'incluido_ruv')
