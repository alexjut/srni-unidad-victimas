"""
Serializers de paramétricas — tablas de referencia de solo lectura.
"""
from rest_framework import serializers
from .models import (
    Departamento, Municipio, Vereda,
    TipoDocumento, ComunidadNegra, ResguardoIndigena,
    DireccionTerritorial, PuntoAtencion,
)


class DepartamentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Departamento
        fields = ['id', 'codigo_dane', 'nombre', 'activo']


class MunicipioSerializer(serializers.ModelSerializer):
    departamento_nombre = serializers.CharField(
        source='departamento.nombre', read_only=True
    )
    departamento_codigo = serializers.CharField(
        source='departamento.codigo_dane', read_only=True
    )

    class Meta:
        model = Municipio
        fields = [
            'id', 'codigo_dane', 'nombre',
            'departamento', 'departamento_codigo', 'departamento_nombre',
            'activo',
        ]


class VeredaSerializer(serializers.ModelSerializer):
    municipio_nombre = serializers.CharField(
        source='municipio.nombre', read_only=True
    )

    class Meta:
        model = Vereda
        fields = ['id', 'codigo_dane', 'nombre', 'municipio', 'municipio_nombre', 'activo']


class TipoDocumentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoDocumento
        fields = [
            'id', 'codigo', 'nombre',
            'aplica_nacionales', 'aplica_extranjeros', 'activo',
        ]


class ComunidadNegraSerializer(serializers.ModelSerializer):
    municipio_nombre = serializers.CharField(
        source='municipio.nombre', read_only=True
    )

    class Meta:
        model = ComunidadNegra
        fields = ['id', 'codigo', 'nombre', 'municipio', 'municipio_nombre', 'activo']


class ResguardoIndigenaSerializer(serializers.ModelSerializer):
    municipio_nombre = serializers.CharField(
        source='municipio.nombre', read_only=True
    )

    class Meta:
        model = ResguardoIndigena
        fields = [
            'id', 'codigo', 'nombre', 'pueblo',
            'municipio', 'municipio_nombre', 'activo',
        ]


class DireccionTerritorialSerializer(serializers.ModelSerializer):
    departamentos = DepartamentoSerializer(many=True, read_only=True)

    class Meta:
        model = DireccionTerritorial
        fields = ['id', 'codigo', 'nombre', 'departamentos', 'activo']


class PuntoAtencionSerializer(serializers.ModelSerializer):
    municipio_nombre = serializers.CharField(
        source='municipio.nombre', read_only=True
    )
    direccion_territorial_nombre = serializers.CharField(
        source='direccion_territorial.nombre', read_only=True
    )

    class Meta:
        model = PuntoAtencion
        fields = [
            'id', 'codigo', 'nombre',
            'direccion_territorial', 'direccion_territorial_nombre',
            'municipio', 'municipio_nombre',
            'direccion_fisica', 'activo',
        ]
