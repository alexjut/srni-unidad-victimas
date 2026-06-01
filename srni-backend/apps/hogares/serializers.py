"""
Serializers de Hogares SRNI.

HogarListSerializer     — listado sin PII de miembros.
HogarDetalleSerializer  — hogar completo con miembros anidados.
MiembroHogarSerializer  — miembro con campos PII opcionales (cifrados en modelo).
"""
from rest_framework import serializers
from apps.parametricas.serializers import MunicipioSerializer, TipoDocumentoSerializer
from apps.victimas.serializers import VictimaListSerializer
from apps.encuestas.serializers import SesionEncuestaListSerializer
from .models import Hogar, MiembroHogar


class MiembroHogarSerializer(serializers.ModelSerializer):
    rol_display = serializers.CharField(
        source='get_rol_display', read_only=True
    )
    parentesco_display = serializers.CharField(
        source='get_parentesco_display', read_only=True
    )
    genero_display = serializers.CharField(
        source='get_genero_display', read_only=True
    )
    estado_inclusion_display = serializers.CharField(
        source='get_estado_inclusion_display', read_only=True
    )
    victima_hash = serializers.CharField(
        source='victima.numero_documento_hash', read_only=True, default=None
    )

    class Meta:
        model = MiembroHogar
        fields = [
            'id', 'hogar',
            'victima', 'victima_hash',
            # Datos cifrados — solo se exponen al crear/editar
            'nombre_completo', 'tipo_documento', 'numero_documento',
            'parentesco', 'parentesco_display',
            'genero', 'genero_display',
            'fecha_nacimiento',
            # Campos principales del nuevo modelo
            'rol', 'rol_display',
            'es_autorizado',
            'estado_inclusion', 'estado_inclusion_display',
            # Compatibilidad Oracle (calculado en save())
            'tipo_persona',
            # Auxiliares
            'incluido_ruv',
            'tiene_discapacidad', 'tipo_discapacidad', 'tiene_enfermedad_ruinosa',
            'created_at',
        ]
        read_only_fields = [
            'id', 'created_at',
            'rol_display', 'parentesco_display', 'genero_display',
            'estado_inclusion_display', 'victima_hash',
            'tipo_persona', 'incluido_ruv',  # calculados en save()
        ]
        extra_kwargs = {
            'numero_documento': {'write_only': True},
            'hogar': {'required': False},
        }


class MiembroHogarListSerializer(serializers.ModelSerializer):
    """Versión reducida para listados — sin datos PII directos."""
    rol_display = serializers.CharField(
        source='get_rol_display', read_only=True
    )
    parentesco_display = serializers.CharField(
        source='get_parentesco_display', read_only=True
    )
    estado_inclusion_display = serializers.CharField(
        source='get_estado_inclusion_display', read_only=True
    )
    victima_hash = serializers.CharField(
        source='victima.numero_documento_hash', read_only=True, default=None
    )

    # Sprint 21 — nombre_completo derivado: si el miembro tiene nombre propio
    # úsalo; si no, combina los nombres/apellidos de la víctima RNI vinculada
    # (típicamente el autorizado). Si ambos vacíos, queda ''.
    nombre_completo = serializers.SerializerMethodField()

    def get_nombre_completo(self, obj):
        propio = (obj.nombre_completo or '').strip()
        if propio:
            return propio
        v = obj.victima
        if v is None:
            return ''
        partes = [
            (v.primer_nombre or '').strip(),
            (v.segundo_nombre or '').strip(),
            (v.primer_apellido or '').strip(),
            (v.segundo_apellido or '').strip(),
        ]
        return ' '.join(p for p in partes if p)

    class Meta:
        model = MiembroHogar
        fields = [
            'id',
            # Sprint 21 — nombre_completo visible para el encuestador.
            # El endpoint /api/hogares/{id}/ requiere puede_caracterizar,
            # así que solo el encuestador que está activo en la entrevista
            # ve este campo. NUNCA se persiste en SQLite local del dispositivo.
            'nombre_completo',
            'parentesco', 'parentesco_display',
            'genero', 'fecha_nacimiento',
            'rol', 'rol_display',
            'es_autorizado',
            'estado_inclusion', 'estado_inclusion_display',
            'tipo_persona',
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
    autorizado_hash = serializers.CharField(
        source='autorizado.numero_documento_hash', read_only=True
    )
    encuestador_nombre = serializers.CharField(
        source='creado_por.nombre_completo', read_only=True, default=None
    )

    class Meta:
        model = Hogar
        fields = [
            'id', 'codigo_hogar',
            'estado', 'estado_display',
            'autorizado', 'autorizado_hash',
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
    municipio_nombre = serializers.CharField(
        source='municipio.nombre', read_only=True, default=None
    )
    municipio_detalle = MunicipioSerializer(source='municipio', read_only=True)
    miembros = MiembroHogarListSerializer(many=True, read_only=True)
    sesiones = SesionEncuestaListSerializer(many=True, read_only=True)
    total_miembros = serializers.IntegerField(source='miembros.count', read_only=True)
    total_sesiones = serializers.IntegerField(source='sesiones.count', read_only=True)
    autorizado_hash = serializers.CharField(
        source='autorizado.numero_documento_hash', read_only=True
    )
    encuestador_nombre = serializers.CharField(
        source='creado_por.nombre_completo', read_only=True, default=None
    )

    class Meta:
        model = Hogar
        fields = [
            'id', 'codigo_hogar',
            'autorizado', 'autorizado_hash',
            'municipio', 'municipio_nombre', 'municipio_detalle',
            'tipo_vivienda', 'tipo_vivienda_display',
            'condicion_ocupacion', 'condicion_ocupacion_display',
            'estrato', 'numero_cuartos', 'numero_personas',
            'estado', 'estado_display',
            'observaciones',
            'miembros', 'total_miembros',
            'sesiones', 'total_sesiones',
            'creado_por', 'encuestador_nombre',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at',
            'estado_display', 'tipo_vivienda_display',
            'condicion_ocupacion_display', 'municipio_nombre', 'municipio_detalle',
            'miembros', 'total_miembros',
            'sesiones', 'total_sesiones',
            'autorizado_hash', 'encuestador_nombre',
        ]


class AgregarMiembroSerializer(serializers.ModelSerializer):
    """Serializer de entrada para la action agregar_miembro."""

    class Meta:
        model = MiembroHogar
        fields = [
            'victima', 'nombre_completo', 'tipo_documento', 'numero_documento',
            'parentesco', 'genero', 'fecha_nacimiento',
            'rol', 'estado_inclusion',
            'tiene_discapacidad', 'tipo_discapacidad', 'tiene_enfermedad_ruinosa',
        ]

    def validate(self, attrs):
        # es_autorizado solo lo asigna el backend en perform_create del hogar
        attrs.pop('es_autorizado', None)
        return attrs


class CambiarAutorizadoSerializer(serializers.Serializer):
    """Serializer de entrada para PATCH /hogares/{id}/cambiar-autorizado/"""
    victima_id = serializers.UUIDField(
        help_text='UUID de la Victima que pasará a ser el nuevo autorizado del hogar.'
    )
