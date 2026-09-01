from django.contrib import admin

from .models import IntentoPrueba, PreguntaPrueba, Prueba


class PreguntaInline(admin.TabularInline):
    model = PreguntaPrueba
    extra = 0
    fields = ('orden', 'enunciado', 'correcta')


@admin.register(Prueba)
class PruebaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'codigo', 'momento', 'pareja', 'abierta', 'total_preguntas')
    list_filter = ('momento', 'abierta')
    search_fields = ('codigo', 'titulo')
    inlines = [PreguntaInline]


@admin.register(IntentoPrueba)
class IntentoAdmin(admin.ModelAdmin):
    list_display = ('correo', 'nombre', 'territorial', 'prueba', 'puntaje', 'total', 'creado_en')
    list_filter = ('prueba__momento', 'prueba__codigo', 'territorial')
    search_fields = ('correo', 'nombre')
    readonly_fields = ('correo_normalizado', 'respuestas', 'ip', 'creado_en')
