from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import Usuario, Perfil


class PerfilSerializer(serializers.ModelSerializer):
    class Meta:
        model = Perfil
        fields = [
            'codigo', 'nombre',
            'puede_buscar_rni', 'puede_caracterizar',
            'puede_ver_reportes', 'puede_administrar',
            # 14-ago-2026 — lo necesita el panel web para decidir si muestra
            # «Autorizaciones» en el menú. Sin exponerlo, el front tendría que
            # adivinar por el código del perfil, y ahí es donde se cuelan los
            # menús que aparecen para quien después recibe un 403.
            'puede_autorizar_excepciones',
        ]


class LoginSerializer(TokenObtainPairSerializer):
    """
    Serializer de login personalizado.
    - Usa 'codigo_usuario' en lugar de 'username'
    - Añade claims del perfil en el payload del JWT
    """
    username_field = Usuario.USERNAME_FIELD

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Claims adicionales embebidos en el JWT (no PII sensible)
        token['codigo'] = user.codigo_usuario
        token['nombre'] = user.nombre_completo
        token['perfil'] = user.perfil.codigo if user.perfil else None
        return token

    def validate(self, attrs):
        # Normalizar codigo_usuario a mayúsculas antes de validar
        attrs[self.username_field] = attrs.get(self.username_field, '').strip().upper()
        return super().validate(attrs)


class UsuarioMeSerializer(serializers.ModelSerializer):
    """Datos del usuario autenticado — sin exponer información sensible."""
    perfil = PerfilSerializer(read_only=True)

    class Meta:
        model = Usuario
        fields = [
            'id', 'codigo_usuario', 'nombre_completo', 'email',
            'perfil', 'fecha_ultimo_login',
        ]
        read_only_fields = fields


class CambiarPasswordSerializer(serializers.Serializer):
    password_actual = serializers.CharField(write_only=True)
    password_nuevo = serializers.CharField(write_only=True, min_length=10)
    password_nuevo_confirmacion = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['password_nuevo'] != data['password_nuevo_confirmacion']:
            raise serializers.ValidationError(
                {'password_nuevo_confirmacion': 'Las contraseñas nuevas no coinciden.'}
            )
        return data

    def validate_password_actual(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('La contraseña actual es incorrecta.')
        return value
