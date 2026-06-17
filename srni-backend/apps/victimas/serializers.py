"""
Serializers de Víctimas — cumple Ley 1581/2012.

Reglas de seguridad aplicadas:
- VictimaListSerializer: NUNCA expone PII (nombres, documento, fecha nacimiento).
- VictimaDetalleSerializer: expone PII solo para usuarios con permiso puede_caracterizar.
- BusquedaDocumentoSerializer: recibe documento en claro; el servidor hashea y busca.
- VictimaResumenSerializer / ResultadoBusquedaSerializer: serializan DTOs del repositorio
  (VictimaResumen / ResultadoBusqueda) — usados en ConsultarFuenteView.
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
    Input para POST /api/victimas/buscar/ (búsqueda en DB local SRNI).
    El frontend envía el documento en claro; el backend hashea server-side.
    NUNCA se almacena el número de documento sin cifrar en logs.
    """
    tipo_documento_codigo = serializers.CharField(max_length=10)
    numero_documento = serializers.CharField(max_length=20, trim_whitespace=True)

    def validate_numero_documento(self, value):
        return value.strip().upper()


# ---------------------------------------------------------------------------
# Serializers para DTOs del repositorio externo (VictimaRepository)
# ---------------------------------------------------------------------------

class HechoResumenSerializer(serializers.Serializer):
    """Serializa HechoResumen DTO — hecho victimizante de una búsqueda en RUV/Oracle."""
    codigo = serializers.CharField()
    nombre = serializers.CharField()
    fecha_hecho = serializers.DateField(allow_null=True)
    municipio_hecho = serializers.CharField(allow_null=True)


class VictimaResumenSerializer(serializers.Serializer):
    """
    Serializa VictimaResumen DTO — datos de la víctima retornados por el repositorio.
    Contiene PII; solo debe usarse en vistas con permiso puede_caracterizar.
    """
    cons_persona = serializers.IntegerField(allow_null=True)
    tipo_documento = serializers.CharField()
    numero_documento = serializers.CharField()
    primer_nombre = serializers.CharField()
    segundo_nombre = serializers.CharField()
    primer_apellido = serializers.CharField()
    segundo_apellido = serializers.CharField()
    fecha_nacimiento = serializers.DateField()
    genero = serializers.CharField()
    estado_ruv = serializers.CharField()
    habilitado_para_caracterizacion = serializers.BooleanField()
    fecha_ult_caracterizacion = serializers.DateTimeField(allow_null=True)
    pertenencia_etnica = serializers.CharField()
    pueblo_indigena = serializers.CharField()
    discapacidad = serializers.BooleanField()
    tipo_discapacidad = serializers.CharField()
    hechos_victimizantes = HechoResumenSerializer(many=True)
    municipio_residencia_codigo = serializers.CharField(allow_null=True)
    municipio_residencia_nombre = serializers.CharField(allow_null=True)
    fuente_origen = serializers.CharField()


class ResultadoBusquedaSerializer(serializers.Serializer):
    """
    Serializa ResultadoBusqueda DTO — respuesta de ConsultarFuenteView.
    Si encontrado=False, victima es null.
    """
    encontrado = serializers.BooleanField()
    victima = VictimaResumenSerializer(allow_null=True)
    fuente = serializers.CharField()
    mensaje = serializers.CharField(allow_blank=True)


class ConsultarFuenteInputSerializer(serializers.Serializer):
    """
    Input para POST /api/victimas/consultar-fuente/
    Igual que BusquedaDocumentoSerializer pero semánticamente diferente:
    esta búsqueda va al RUV/Oracle (repositorio externo), no a la DB local.
    """
    tipo_documento = serializers.CharField(max_length=10)
    numero_documento = serializers.CharField(max_length=20, trim_whitespace=True)

    def validate_numero_documento(self, value):
        return value.strip().upper()

    def validate_tipo_documento(self, value):
        return value.strip().upper()


# ---------------------------------------------------------------------------
# Serializer para upsert de víctima desde fuente externa
# ---------------------------------------------------------------------------

class RegistrarDesdeFuenteSerializer(serializers.Serializer):
    """
    Input: datos de VictimaResumen DTO provenientes del repositorio externo.
    Usado para crear/actualizar la Victima local antes de conformar el hogar.
    """
    cons_persona = serializers.IntegerField(allow_null=True, required=False)
    tipo_documento = serializers.CharField(max_length=10)
    numero_documento = serializers.CharField(max_length=20)
    primer_nombre = serializers.CharField(max_length=100)
    segundo_nombre = serializers.CharField(max_length=100, allow_blank=True, default='')
    primer_apellido = serializers.CharField(max_length=100)
    segundo_apellido = serializers.CharField(max_length=100, allow_blank=True, default='')
    fecha_nacimiento = serializers.DateField()
    genero = serializers.ChoiceField(choices=['M', 'F', 'NB', 'ND'], default='ND')
    estado_ruv = serializers.CharField(max_length=15, default='NO_INCLUIDO')
    habilitado_para_caracterizacion = serializers.BooleanField(default=True)
    pertenencia_etnica = serializers.CharField(max_length=20, default='NINGUNA')
    pueblo_indigena = serializers.CharField(max_length=150, allow_blank=True, default='')
    discapacidad = serializers.BooleanField(default=False)
    tipo_discapacidad = serializers.CharField(max_length=100, allow_blank=True, default='')
    municipio_residencia_codigo = serializers.CharField(
        max_length=10, allow_null=True, required=False,
        help_text='Código DIVIPOLA 5 dígitos del municipio de residencia.',
    )
    fuente_origen = serializers.CharField(max_length=20, default='RUV')

    def validate_tipo_documento(self, value):
        return value.strip().upper()

    def validate_numero_documento(self, value):
        return value.strip().upper()
