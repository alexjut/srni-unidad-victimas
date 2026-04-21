"""
Serializers de Víctimas — cumple Ley 1581/2012.

Reglas de seguridad aplicadas:
- VictimaListSerializer: NUNCA expone PII (nombres, documento, fecha nacimiento).
- VictimaDetalleSerializer: expone PII solo para usuarios con permiso puede_caracterizar.
- BusquedaDocumentoSerializer: recibe documento en claro; el servidor hashea y busca.
"""
from rest_framework import serializers
from .models import Victima
from apps.parametricas.serializers import TipoDocumentoSerializer, MunicipioSerializer


class VictimaListSerializer(serializers.ModelSerializer):
    """
    Serializer seguro para listados — sin campos PII.
    Solo expone metadatos que no identifican a la víctima por sí solos.
    """
    tipo_documento_codigo = serializers.CharField(
        source='tipo_documento.codigo', read_only=True
    )
    municipio_residencia_nombre = serializers.CharField(
        source='municipio_residencia.nombre', read_only=True
    )
    departamento_nombre = serializers.CharField(
        source='municipio_residencia.departamento.nombre', read_only=True
    )

    class Meta:
        model = Victima
        fields = [
            'id',
            'tipo_documento_codigo',
            # hash del documento — útil para identificar el registro sin revelar el número
            'numero_documento_hash',
            'genero', 'estado_civil', 'pertenencia_etnica',
            'discapacidad', 'tipo_discapacidad',
            'estado_ruv',
            'municipio_residencia', 'municipio_residencia_nombre', 'departamento_nombre',
            'created_at',
        ]
        read_only_fields = fields


class VictimaDetalleSerializer(serializers.ModelSerializer):
    """
    Serializer completo con PII descifrado.
    Solo debe usarse en vistas que verifiquen permiso puede_caracterizar.
    El EncryptedField ya descifra automáticamente en from_db_value.
    """
    tipo_documento = TipoDocumentoSerializer(read_only=True)
    municipio_residencia = MunicipioSerializer(read_only=True)
    creado_por_nombre = serializers.CharField(
        source='creado_por.nombre_completo', read_only=True, default=None
    )

    class Meta:
        model = Victima
        fields = [
            'id',
            'tipo_documento',
            # numero_documento viene descifrado por EncryptedField.from_db_value
            'numero_documento',
            'primer_nombre', 'segundo_nombre',
            'primer_apellido', 'segundo_apellido',
            'fecha_nacimiento',
            'genero', 'estado_civil', 'pertenencia_etnica',
            'pueblo_indigena', 'discapacidad', 'tipo_discapacidad',
            'estado_ruv', 'hechos_victimizantes',
            'municipio_residencia',
            'creado_por', 'creado_por_nombre',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields


class BusquedaDocumentoSerializer(serializers.Serializer):
    """
    Input para POST /api/victimas/buscar/
    El frontend envía el documento en claro; el backend hashea server-side.
    NUNCA se almacena el número de documento sin cifrar en logs.
    """
    tipo_documento_codigo = serializers.CharField(max_length=10)
    numero_documento = serializers.CharField(max_length=20, trim_whitespace=True)

    def validate_numero_documento(self, value):
        return value.strip().upper()
