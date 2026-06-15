"""Serializers para el módulo de administración de usuarios (panel web)."""
from rest_framework import serializers

from .models import Perfil, Usuario


class PerfilSerializer(serializers.ModelSerializer):
    class Meta:
        model = Perfil
        fields = [
            "id", "codigo", "nombre",
            "puede_buscar_rni", "puede_caracterizar",
            "puede_ver_reportes", "puede_administrar", "activo",
        ]


class UsuarioAdminSerializer(serializers.ModelSerializer):
    """Lectura/edición de usuarios (sin contraseña)."""
    perfil_codigo = serializers.CharField(source="perfil.codigo", read_only=True)
    perfil_nombre = serializers.CharField(source="perfil.nombre", read_only=True)

    class Meta:
        model = Usuario
        fields = [
            "id", "codigo_usuario", "nombre_completo", "email",
            "perfil", "perfil_codigo", "perfil_nombre",
            "activo", "es_admin", "fecha_ultimo_login", "created_at",
        ]
        read_only_fields = ["id", "fecha_ultimo_login", "created_at"]


class UsuarioCrearSerializer(serializers.ModelSerializer):
    """Creación de usuario con contraseña."""
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = Usuario
        fields = [
            "id", "codigo_usuario", "nombre_completo", "email",
            "perfil", "activo", "es_admin", "password",
        ]

    def validate_codigo_usuario(self, value):
        return value.strip().upper()

    def create(self, validated_data):
        password = validated_data.pop("password")
        es_admin = validated_data.pop("es_admin", False)
        usuario = Usuario.objects.create_user(password=password, **validated_data)
        if es_admin:
            usuario.es_admin = True
            usuario.is_superuser = True
            usuario.save(update_fields=["es_admin", "is_superuser"])
        return usuario
