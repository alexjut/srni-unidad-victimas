from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from .models import SesionEncuesta, RespuestaEncuesta


class RespuestaInline(TabularInline):
    model = RespuestaEncuesta
    extra = 0
    fields = ('pregunta', 'valor', 'updated_at')
    readonly_fields = ('updated_at',)
    raw_id_fields = ('pregunta',)


@admin.register(SesionEncuesta)
class SesionEncuestaAdmin(ModelAdmin):
    list_display = (
        'id_corto', 'hogar', 'instrumento', 'encuestador',
        'estado', 'porcentaje_completado', 'fecha_inicio',
    )
    list_filter = ('estado', 'instrumento')
    search_fields = ('id',)
    ordering = ('-created_at',)
    readonly_fields = ('id', 'porcentaje_completado', 'fecha_inicio', 'created_at', 'updated_at')
    raw_id_fields = ('hogar', 'instrumento', 'encuestador')
    inlines = [RespuestaInline]

    @admin.display(description='ID (corto)')
    def id_corto(self, obj):
        return str(obj.id)[:8] + '…'


@admin.register(RespuestaEncuesta)
class RespuestaEncuestaAdmin(ModelAdmin):
    list_display = ('id', 'sesion', 'pregunta', 'valor_corto', 'updated_at')
    raw_id_fields = ('sesion', 'pregunta')
    readonly_fields = ('created_at', 'updated_at')

    @admin.display(description='Valor')
    def valor_corto(self, obj):
        return obj.valor[:60]
