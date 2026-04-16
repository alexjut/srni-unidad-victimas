from django.contrib import admin
from .models import Hogar, MiembroHogar


class MiembroHogarInline(admin.TabularInline):
    model = MiembroHogar
    extra = 0
    fields = ('parentesco', 'genero', 'edad', 'discapacidad', 'victima', 'tipo_documento')
    raw_id_fields = ('victima', 'tipo_documento')
    readonly_fields = ('created_at',)


@admin.register(Hogar)
class HogarAdmin(admin.ModelAdmin):
    list_display = ('id_corto', 'estado', 'municipio', 'numero_personas', 'creado_por', 'created_at')
    list_filter = ('estado', 'tipo_vivienda', 'condicion_ocupacion')
    search_fields = ('id',)
    ordering = ('-created_at',)
    readonly_fields = ('id', 'created_at', 'updated_at')
    raw_id_fields = ('jefe_hogar', 'municipio', 'creado_por')
    inlines = [MiembroHogarInline]

    @admin.display(description='ID (corto)')
    def id_corto(self, obj):
        return str(obj.id)[:8] + '…'


@admin.register(MiembroHogar)
class MiembroHogarAdmin(admin.ModelAdmin):
    list_display = ('id', 'hogar', 'parentesco', 'genero', 'edad', 'discapacidad')
    list_filter = ('parentesco', 'genero', 'discapacidad')
    raw_id_fields = ('hogar', 'victima', 'tipo_documento', 'creado_por')
    readonly_fields = ('id', 'created_at')
