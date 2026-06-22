from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import ConsentimientoIA, SesionIA


@admin.register(ConsentimientoIA)
class ConsentimientoIAAdmin(ModelAdmin):
    list_display = ['id', 'sesion_encuesta', 'encuestador', 'acepto', 'creado_en']
    list_filter = ['acepto', 'creado_en']
    search_fields = ['encuestador__codigo_usuario', 'sesion_encuesta__id']
    readonly_fields = ['id', 'firma_digital', 'creado_en']


@admin.register(SesionIA)
class SesionIAAdmin(ModelAdmin):
    list_display = ['id', 'sesion_encuesta', 'inicio', 'fin', 'total_llamadas']
    list_filter = ['inicio']
    search_fields = ['sesion_encuesta__id']
    readonly_fields = ['id', 'inicio', 'total_llamadas', 'transcripcion_hash']
