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
    motivo_retiro_display = serializers.CharField(
        source='get_motivo_retiro_display', read_only=True, default=''
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
            # Constancia tutor/cuidador (se sube por la acción subir-constancia)
            'constancia', 'constancia_nombre', 'constancia_subida_en',
            # Retiro del hogar — la novedad. Va en los dos serializers de salida
            # porque la aplicación decide con esto a quién le pregunta en la
            # entrevista: un integrante retirado se muestra, pero no se interroga.
            'retirado_en', 'motivo_retiro', 'motivo_retiro_display',
            'observacion_retiro', 'retirado_at',
            'created_at',
        ]
        read_only_fields = [
            'id', 'created_at',
            'rol_display', 'parentesco_display', 'genero_display',
            'estado_inclusion_display', 'victima_hash',
            # El retiro se registra por su acción dedicada, nunca por escritura
            # directa: exige motivo y fecha, y deja quién y cuándo lo registró.
            'retirado_en', 'motivo_retiro', 'motivo_retiro_display',
            'observacion_retiro', 'retirado_at',
            'tipo_persona', 'incluido_ruv',  # calculados en save()
            # El archivo se gestiona por la acción dedicada, no por escritura directa
            'constancia', 'constancia_nombre', 'constancia_subida_en',
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
    motivo_retiro_display = serializers.CharField(
        source='get_motivo_retiro_display', read_only=True, default=''
    )

    # Sprint 21 — nombre_completo derivado: si el miembro tiene nombre propio
    # úsalo; si no, combina los nombres/apellidos de la víctima RNI vinculada
    # (típicamente el autorizado). Si ambos vacíos, queda ''.
    nombre_completo = serializers.SerializerMethodField()

    # ── Las partes del nombre, y el documento, por separado ─────────────────
    #
    # Hasta el 11-sep-2026 este serializer entregaba el nombre **solo** como una
    # cadena concatenada y el documento no lo entregaba en absoluto
    # (`numero_documento` es `write_only` en el serializer hermano). El efecto en
    # campo: al conformar un hogar, el autorizado salía completo y **los demás
    # integrantes llegaban con el primer nombre y nada más** —sin segundo
    # nombre, sin apellidos y sin cédula—, porque la aplicación no tenía de
    # dónde sacarlos y partía la cadena quedándose con el primer pedazo.
    #
    # Partir la cadena en el cliente no es el arreglo: «José Luis Vargas Mora» y
    # «José Vargas Mora» no se distinguen sin saber cuántos nombres tiene la
    # persona, y adivinarlo le escribe a alguien un apellido que no es el suyo.
    # Acá sí se sabe, porque la víctima vinculada trae los cuatro campos
    # separados desde el padrón.
    #
    # No abre PII nueva: el endpoint ya exige `puede_caracterizar` y ya venía
    # devolviendo el nombre completo en claro por esta misma vía.
    primer_nombre = serializers.SerializerMethodField()
    segundo_nombre = serializers.SerializerMethodField()
    primer_apellido = serializers.SerializerMethodField()
    segundo_apellido = serializers.SerializerMethodField()
    numero_documento = serializers.SerializerMethodField()
    tipo_documento_codigo = serializers.SerializerMethodField()

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

    def _partes(self, obj):
        """
        Los cuatro campos del nombre, de la mejor fuente disponible.

        La víctima vinculada manda cuando existe: ahí los cuatro vienen
        separados desde el padrón y no hay nada que deducir. Solo cuando el
        miembro no está en el RNI —el alta manual en campo, que es donde el
        único dato es lo que tecleó el encuestador— se reparte la cadena con la
        convención española: dos apellidos al final.
        """
        v = obj.victima
        if v is not None and (v.primer_nombre or v.primer_apellido):
            return ((v.primer_nombre or '').strip(), (v.segundo_nombre or '').strip(),
                    (v.primer_apellido or '').strip(), (v.segundo_apellido or '').strip())

        tokens = (obj.nombre_completo or '').split()
        if len(tokens) >= 4:
            return tokens[0], ' '.join(tokens[1:-2]), tokens[-2], tokens[-1]
        if len(tokens) == 3:
            return tokens[0], '', tokens[1], tokens[2]
        if len(tokens) == 2:
            return tokens[0], '', tokens[1], ''
        if len(tokens) == 1:
            return tokens[0], '', '', ''
        return '', '', '', ''

    def get_primer_nombre(self, obj) -> str:
        return self._partes(obj)[0]

    def get_segundo_nombre(self, obj) -> str:
        return self._partes(obj)[1]

    def get_primer_apellido(self, obj) -> str:
        return self._partes(obj)[2]

    def get_segundo_apellido(self, obj) -> str:
        return self._partes(obj)[3]

    def get_numero_documento(self, obj) -> str:
        """
        El del miembro si lo tiene; si no, el de la víctima vinculada.

        Ese orden y no el inverso: cuando el encuestador corrige el documento en
        campo, lo escribe en el miembro, y el del padrón es el que se está
        corrigiendo.
        """
        propio = (obj.numero_documento or '').strip()
        if propio:
            return propio
        v = obj.victima
        return (v.numero_documento or '').strip() if v is not None else ''

    def get_tipo_documento_codigo(self, obj) -> str:
        if obj.tipo_documento_id:
            return obj.tipo_documento.codigo
        v = obj.victima
        if v is not None and v.tipo_documento_id:
            return v.tipo_documento.codigo
        return ''

    class Meta:
        model = MiembroHogar
        fields = [
            'id',
            # Sprint 21 — nombre_completo visible para el encuestador.
            # El endpoint /api/hogares/{id}/ requiere puede_caracterizar,
            # así que solo el encuestador que está activo en la entrevista
            # ve este campo. NUNCA se persiste en SQLite local del dispositivo.
            'nombre_completo',
            # Las mismas garantías de acceso que `nombre_completo`, que ya
            # viajaba en claro por este endpoint. Sin estos seis campos el
            # integrante que no es el autorizado llega a la encuesta con el
            # primer nombre y nada más.
            'primer_nombre', 'segundo_nombre', 'primer_apellido', 'segundo_apellido',
            'numero_documento', 'tipo_documento_codigo',
            'parentesco', 'parentesco_display',
            'genero', 'fecha_nacimiento',
            'rol', 'rol_display',
            'es_autorizado',
            'estado_inclusion', 'estado_inclusion_display',
            'tipo_persona',
            'incluido_ruv', 'tiene_discapacidad',
            'victima', 'victima_hash',
            # El retiro viaja también acá, y es lo que la APK usa para decidir a
            # quién le pregunta: un integrante retirado se sigue viendo —para que
            # nadie crea que se perdió— pero sus filas de preguntas quedan
            # inactivas con el motivo a la vista.
            'retirado_en', 'motivo_retiro', 'motivo_retiro_display',
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


class RetirarMiembroSerializer(serializers.Serializer):
    """
    Entrada de POST /hogares/{id}/miembros/{mid}/retirar/

    Registra que una persona dejó de pertenecer al hogar. **No borra nada.**

    ─── Por qué el motivo y la fecha son obligatorios ────────────────────────
    Sin motivo, «se retiró» no se distingue de «lo borraron por error», y esa
    diferencia es la que se va a necesitar el día que alguien revise por qué un
    hogar pasó de cinco a tres personas. Sin fecha no se puede saber si la
    persona pertenecía al hogar en la caracterización anterior, que es
    justamente lo que permite que esa entrevista siga siendo válida.

    La fecha es la del HECHO, no la de hoy. Una familia informa en septiembre un
    fallecimiento de marzo, y ese es el caso corriente.
    """

    motivo = serializers.ChoiceField(choices=MiembroHogar.RETIRO)
    fecha = serializers.DateField(
        help_text='Fecha desde la cual la persona ya no pertenece al hogar. '
                  'Es la del hecho, no la de hoy.',
    )
    observacion = serializers.CharField(
        max_length=2_000, required=False, allow_blank=True, default='',
    )

    def validate_fecha(self, value):
        from django.utils import timezone

        hoy = timezone.localdate()
        if value > hoy:
            raise serializers.ValidationError(
                'La fecha no puede ser futura: se registra un hecho que ya ocurrió.'
            )
        return value

    def validate(self, attrs):
        # 'OTRO' sin explicación no dice nada, y es el que más se va a usar.
        if attrs.get('motivo') == 'OTRO' and not (attrs.get('observacion') or '').strip():
            raise serializers.ValidationError({
                'observacion': 'Con el motivo "Otro" hay que explicar cuál es.',
            })
        return attrs
