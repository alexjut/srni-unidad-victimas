"""
Serializers de Hogares SRNI.

HogarListSerializer   — listado sin PII de miembros.
HogarDetalleSerializer — hogar completo con miembros anidados.
MiembroHogarSerializer — miembro con campos PII opcionales (cifrados en modelo).
"""
from rest_framework import serializers
from apps.parametricas.serializers import MunicipioSerializer, TipoDocumentoSerializer
from apps.victimas.serializers import VictimaListSerializer
from .models import Hogar, MiembroHogar


class MiembroHogarSerializer(serializers.ModelSerializer):
    parentesco_display = serializers.CharField(
        source='get_parentesco_display', read_only=True
    )
    genero_display = serializers.CharField(
        source='get_genero_display', read_only=True
    )
    victima_hash = serializers.CharField(
        source='victima.numero_documento_hash', read_only=True, default=None
    )

    class Meta:
        model = MiembroHogar
        fields = [
            'id', 'hogar',
            'victima', 'victima_hash',
            # Datos cifrados — solo se exponen al crear/editar; en lectura solo para
            # usuarios con puede_caracterizar (validado en el ViewSet).
            'nombre_completo', 'tipo_documento', 'numero_documento',
            'parentesco', 'parentesco_display',
            'genero', 'genero_display',
            'fecha_nacimiento', 'tipo_persona', 'incluido_ruv',
            'tiene_discapacidad', 'tipo_discapacidad', 'tiene_enfermedad_ruinosa',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'parentesco_display', 'genero_display', 'victima_hash']
        extra_kwargs = {
            # numero_documento es write-only en la API: no se devuelve en lectura
            'numero_documento': {'write_only': True},
            'hogar': {'required': False},
        }


class MiembroHogarListSerializer(serializers.ModelSerializer):
    """Versión reducida para listados — sin datos PII directos."""
    parentesco_display = serializers.CharField(
        source='get_parentesco_display', read_only=True
    )
    victima_hash = serializers.CharField(
        source='victima.numero_documento_hash', read_only=True, default=None
    )

    class Meta:
        model = MiembroHogar
        fields = [
            'id', 'parentesco', 'parentesco_display',
            'genero', 'fecha_nacimiento', 'tipo_persona',
            'incluido_ruv', 'tiene_discapacidad',
            'victima', 'victima_hash',
        ]


class HogarListSerializer(serializers.ModelSerializer):
    """Listado de hogares — sin PII, con conteo de miembros."""
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    municipio_nombre = serializers.CharField(
        source='municipio.nombre', read_only=True, default=None
    )
    total_miembros = serializers.IntegerField(source='miembros.count', read_only=True)
    jefe_hogar_hash = serializers.CharField(
        source='jefe_hogar.numero_documento_hash', read_only=True
    )
    encuestador_nombre = serializers.CharField(
        source='creado_por.nombre_completo', read_only=True, default=None
    )

    class Meta:
        model = Hogar
        fields = [
            'id', 'estado', 'estado_display',
            'jefe_hogar', 'jefe_hogar_hash',
            'municipio', 'municipio_nombre',
            'total_miembros', 'numero_personas',
            'encuestador_nombre',
            'created_at', 'updated_at',
        ]


class HogarDetalleSerializer(serializers.ModelSerializer):
    """Hogar completo con miembros — requiere puede_caracterizar."""
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    tipo_vivienda_display = serializers.CharField(
        source='get_tipo_vivienda_display', read_only=True
    )
    condicion_ocupacion_display = serializers.CharField(
        source='get_condicion_ocupacion_display', read_only=True
    )
    municipio_detalle = MunicipioSerializer(source='municipio', read_only=True)
    miembros = MiembroHogarListSerializer(many=True, read_only=True)
    total_miembros = serializers.IntegerField(source='miembros.count', read_only=True)
    total_sesiones = serializers.IntegerField(source='sesiones.count', read_only=True)

    class Meta:
        model = Hogar
        fields = [
            'id',
            'jefe_hogar',
            'municipio', 'municipio_detalle',
            'tipo_vivienda', 'tipo_vivienda_display',
            'condicion_ocupacion', 'condicion_ocupacion_display',
            'estrato', 'numero_cuartos', 'numero_personas',
            'estado', 'estado_display',
            'observaciones',
            'miembros', 'total_miembros', 'total_sesiones',
            'creado_por',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at',
            'estado_display', 'tipo_vivienda_display',
            'condicion_ocupacion_display', 'municipio_detalle',
            'miembros', 'total_miembros', 'total_sesiones',
        ]


class AgregarMiembroSerializer(serializers.ModelSerializer):
    """Serializer de entrada para la action agregar_miembro."""
    class Meta:
        model = MiembroHogar
        fields = [
            'victima', 'nombre_completo', 'tipo_documento', 'numero_documento',
            'parentesco', 'genero', 'fecha_nacimiento', 'tipo_persona',
            'incluido_ruv', 'tiene_discapacidad', 'tipo_discapacidad', 'tiene_enfermedad_ruinosa',
        ]


class CambiarJefeSerializer(serializers.Serializer):
    """Serializer de entrada para PATCH /hogares/{id}/cambiar-jefe/"""
    victima_id = serializers.UUIDField(
        help_text='UUID de la Victima que pasará a ser jefe de hogar.'
    )
