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

    # Sin este campo el DTO traía los otros registros con el mismo documento y el
    # serializer los tiraba: la respuesta decía "Hay 2 registros con este documento,
    # CONFIRME cuál corresponde" y no mandaba con qué confirmar. Verificado contra
    # prod el 2-ago con un documento duplicado real (mensaje correcto, candidatos 0).
    candidatos = VictimaResumenSerializer(many=True, required=False)

    # true = el número es un valor de relleno y no identifica a nadie. La app tiene
    # que decir eso, no "no está en el padrón": son cosas distintas.
    no_identificante = serializers.BooleanField(required=False, default=False)

    # El porqué, en código. Sin esto la app solo podía pintar `mensaje` y no
    # sabía qué acción ofrecer, así que un bloqueo previsto se leía en campo
    # como una falla del sistema. Ver `MotivoNoElegible` en repository/base.py.
    motivo = serializers.CharField(required=False, allow_blank=True, default='')

    # Cuándo vuelve a estar disponible (fecha de la última caracterización + los
    # años de vigencia). Permite decir "vuelva a intentar el …" sin que la app
    # tenga que conocer la regla.
    disponible_desde = serializers.DateField(required=False, allow_null=True)


class ConsultarFuenteInputSerializer(serializers.Serializer):
    """
    Input para POST /api/victimas/consultar-fuente/
    Igual que BusquedaDocumentoSerializer pero semánticamente diferente:
    esta búsqueda va al RUV/Oracle (repositorio externo), no a la DB local.
    """
    tipo_documento = serializers.CharField(max_length=10)
    numero_documento = serializers.CharField(max_length=20, trim_whitespace=True)

    # La ruta viaja junto al documento porque el Manual §5.1.1 (pág. 22) las pide
    # en el mismo paso: «Diligenciar el número de documento con el cual iniciarán
    # la conformación del hogar y establecer la ruta respectiva».
    #
    # Opcional a propósito: sin ruta se responde el estado real de la persona,
    # que es lo que corresponde en la primera búsqueda. El encuestador elige una
    # ruta de excepción recién DESPUÉS de ver que hay ficha vigente.
    ruta_entrevista = serializers.CharField(
        max_length=30, required=False, allow_blank=True, default='',
        help_text=('Ruta de entrevista. ACCIONES_CONSTITUCIONALES, '
                   'MODIFICACION_NUCLEO y ESPECIAL omiten la regla de vigencia '
                   '(Manual §5.1.1); GENERAL la respeta.'),
    )

    def validate_numero_documento(self, value):
        return value.strip().upper()

    def validate_tipo_documento(self, value):
        return value.strip().upper()

    def validate_ruta_entrevista(self, value):
        return (value or '').strip().upper()


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
    # Default 'NO_VERIFICADO', no 'NO_INCLUIDO': si el cliente no manda el estado
    # es porque no lo resolvió contra el padrón — y "no lo sé" no es "no está".
    estado_ruv = serializers.CharField(max_length=15, default='NO_VERIFICADO')
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

    # Valores que mandan APKs ya desplegadas y que NO existen en el dominio del
    # modelo. Se aceptan y se traducen en vez de rechazarse con 400: en campo hay
    # dispositivos con la versión anterior y un 400 aquí les rompe el alta manual.
    _FUENTE_ORIGEN_LEGACY = {
        'NO_INCLUIDA': 'MANUAL',   # alta manual desde búsqueda; nunca fue un choice
        'OFFLINE': 'RUV',          # salió del padrón descargado: la fuente es el RUV,
                                   # 'OFFLINE' era el canal, no el origen del dato
        'ENCUESTADOR': 'MANUAL',   # nombre del dominio de MiembroHogar, no del de Victima
    }

    def validate_tipo_documento(self, value):
        return value.strip().upper()

    def validate_numero_documento(self, value):
        return value.strip().upper()

    def validate_estado_ruv(self, value):
        # Antes era un CharField suelto: cualquier cadena entraba a la BD.
        valor = (value or '').strip().upper()
        validos = {c for c, _ in Victima.ESTADO_RUV}
        if valor not in validos:
            raise serializers.ValidationError(
                f'Estado RUV no reconocido: {value!r}. Válidos: {sorted(validos)}.'
            )
        return valor

    def validate_fuente_origen(self, value):
        valor = (value or '').strip().upper()
        valor = self._FUENTE_ORIGEN_LEGACY.get(valor, valor)
        validos = {c for c, _ in Victima.FUENTE_ORIGEN}
        if valor not in validos:
            raise serializers.ValidationError(
                f'Fuente de origen no reconocida: {value!r}. Válidas: {sorted(validos)}.'
            )
        return valor


# ---------------------------------------------------------------------------
# Serializers para la precarga offline (GET /api/victimas/precarga/)
# ---------------------------------------------------------------------------

class PadronItemSerializer(serializers.Serializer):
    """
    Resumen mínimo de una víctima para el padrón offline.
    NO incluye el detalle de los hechos — solo la cantidad. Esto reduce el
    tamaño de la descarga y limita la PII en reposo en el dispositivo.
    """
    tipo_documento = serializers.CharField()
    documento = serializers.CharField()
    nombre = serializers.CharField()
    ubicacion = serializers.CharField(allow_null=True, allow_blank=True)
    cantidad_hechos = serializers.IntegerField()
    en_ruv = serializers.BooleanField()
    habilitada = serializers.BooleanField()
    ya_caracterizada = serializers.BooleanField()
    cons_persona = serializers.IntegerField(allow_null=True)
    # null = documento limpio; 'AMBIGUO' = varias personas lo comparten y hay que
    # preguntar; 'NO_IDENTIFICANTE' = valor de relleno que no identifica a nadie.
    # Sin esto, en campo y sin señal no hay forma de saber que la persona que se
    # está mostrando podría no ser la que está enfrente.
    clase_colision = serializers.CharField(allow_null=True, required=False)
