from django.contrib import admin
from .models import (
    Departamento, Municipio, Vereda,
    TipoDocumento, ComunidadNegra, ResguardoIndigena,
    DireccionTerritorial, PuntoAtencion,
)


@admin.register(Departamento)
class DepartamentoAdmin(admin.ModelAdmin):
    list_display = ('codigo_dane', 'nombre', 'activo')
    list_filter = ('activo',)
    search_fields = ('codigo_dane', 'nombre')
    ordering = ('nombre',)


@admin.register(Municipio)
class MunicipioAdmin(admin.ModelAdmin):
    list_display = ('codigo_dane', 'nombre', 'departamento', 'activo')
    list_filter = ('activo', 'departamento')
    search_fields = ('codigo_dane', 'nombre')
    ordering = ('departamento__nombre', 'nombre')
    raw_id_fields = ('departamento',)


@admin.register(Vereda)
class VeredaAdmin(admin.ModelAdmin):
    list_display = ('codigo_dane', 'nombre', 'municipio', 'activo')
    list_filter = ('activo',)
    search_fields = ('codigo_dane', 'nombre')
    raw_id_fields = ('municipio',)


@admin.register(TipoDocumento)
class TipoDocumentoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'aplica_nacionales', 'aplica_extranjeros', 'activo')
    list_filter = ('activo', 'aplica_nacionales', 'aplica_extranjeros')
    search_fields = ('codigo', 'nombre')
    ordering = ('nombre',)


@admin.register(ComunidadNegra)
class ComunidadNegraAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'municipio', 'activo')
    list_filter = ('activo',)
    search_fields = ('codigo', 'nombre')
    raw_id_fields = ('municipio',)


@admin.register(ResguardoIndigena)
class ResguardoIndigenaAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'pueblo', 'municipio', 'activo')
    list_filter = ('activo',)
    search_fields = ('codigo', 'nombre', 'pueblo')
    raw_id_fields = ('municipio',)


@admin.register(DireccionTerritorial)
class DireccionTerritorialAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'activo')
    list_filter = ('activo',)
    search_fields = ('codigo', 'nombre')
    filter_horizontal = ('departamentos',)


@admin.register(PuntoAtencion)
class PuntoAtencionAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'direccion_territorial', 'municipio', 'activo')
    list_filter = ('activo', 'direccion_territorial')
    search_fields = ('codigo', 'nombre')
    raw_id_fields = ('direccion_territorial', 'municipio')
