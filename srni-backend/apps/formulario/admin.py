from django.contrib import admin
from .models import (
    Perfil, InstrumentoVersion, Capitulo, Pregunta, OpcionRespuesta, ReglaSkipLogic,
)


class CapituloInline(admin.TabularInline):
    model = Capitulo
    fields = ("codigo", "nombre", "orden", "poblacion_objetivo", "aplicabilidad")
    extra = 0
    ordering = ("orden",)


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "activo", "creado")
    list_filter = ("activo",)
    search_fields = ("codigo", "nombre")


@admin.register(InstrumentoVersion)
class InstrumentoVersionAdmin(admin.ModelAdmin):
    list_display = ("perfil", "numero", "vigente_desde", "vigente_hasta", "vigente")
    list_filter = ("perfil",)
    search_fields = ("numero", "fuente_documental")
    inlines = [CapituloInline]


@admin.register(Capitulo)
class CapituloAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "instrumento", "orden", "poblacion_objetivo")
    list_filter = ("instrumento__perfil", "poblacion_objetivo")
    search_fields = ("codigo", "nombre")
    ordering = ("instrumento", "orden")


class OpcionInline(admin.TabularInline):
    model = OpcionRespuesta
    extra = 0
    fields = ("orden", "valor", "etiqueta", "id_resp_vivanto", "finaliza_capitulo")


@admin.register(Pregunta)
class PreguntaAdmin(admin.ModelAdmin):
    list_display = (
        "codigo_externo", "capitulo", "texto_corto", "tipo", "nivel", "obligatoria", "activa"
    )
    list_filter = ("capitulo__instrumento", "capitulo", "tipo", "nivel", "obligatoria", "activa")
    search_fields = ("codigo_externo", "variable_bd", "texto")
    ordering = ("capitulo", "orden")
    inlines = [OpcionInline]

    @admin.display(description="Texto")
    def texto_corto(self, obj):
        return obj.texto[:80]


@admin.register(ReglaSkipLogic)
class ReglaSkipLogicAdmin(admin.ModelAdmin):
    list_display = (
        "pregunta_origen", "valor_trigger", "accion",
        "pregunta_afectada", "capitulo_afectado", "descripcion",
    )
    list_filter = ("accion", "instrumento")
    search_fields = (
        "descripcion",
        "pregunta_origen__codigo_externo",
        "pregunta_afectada__codigo_externo",
    )
