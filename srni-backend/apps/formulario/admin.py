from django.contrib import admin
from .models import Instrumento, Tema, Pregunta, OpcionRespuesta, PreguntaDerivada


class TemaInline(admin.TabularInline):
    model = Tema
    fields = ('codigo', 'nombre', 'orden', 'activo')
    extra = 0
    ordering = ('orden',)


@admin.register(Instrumento)
class InstrumentoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'version', 'vigente', 'created_at')
    list_filter = ('vigente',)
    search_fields = ('codigo', 'nombre')
    inlines = [TemaInline]


class OpcionRespuestaInline(admin.TabularInline):
    model = OpcionRespuesta
    fields = ('codigo', 'texto', 'orden', 'activa')
    extra = 0
    ordering = ('orden',)


class PreguntaDerivadaHijaInline(admin.TabularInline):
    model = PreguntaDerivada
    fk_name = 'pregunta_padre'
    fields = ('pregunta_hija', 'operador', 'valor_condicion')
    extra = 0
    verbose_name = 'Derivación (habilita pregunta hija)'
    verbose_name_plural = 'Derivaciones (skip logic)'
    raw_id_fields = ('pregunta_hija',)


@admin.register(Tema)
class TemaAdmin(admin.ModelAdmin):
    list_display = ('orden', 'codigo', 'nombre', 'instrumento', 'activo')
    list_filter = ('instrumento', 'activo')
    search_fields = ('codigo', 'nombre')
    ordering = ('instrumento', 'orden')
    raw_id_fields = ('instrumento',)


@admin.register(Pregunta)
class PreguntaAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'texto_corto', 'tema', 'tipo_respuesta', 'requerida', 'activa')
    list_filter = ('tema__instrumento', 'tipo_respuesta', 'requerida', 'activa')
    search_fields = ('codigo', 'texto')
    ordering = ('tema__orden', 'orden')
    raw_id_fields = ('tema',)
    inlines = [OpcionRespuestaInline, PreguntaDerivadaHijaInline]

    @admin.display(description='Texto')
    def texto_corto(self, obj):
        return obj.texto[:80]


@admin.register(PreguntaDerivada)
class PreguntaDerivadaAdmin(admin.ModelAdmin):
    list_display = ('pregunta_padre', 'operador', 'valor_condicion', 'pregunta_hija')
    list_filter = ('operador',)
    raw_id_fields = ('pregunta_padre', 'pregunta_hija')
    search_fields = ('pregunta_padre__codigo', 'pregunta_hija__codigo')
