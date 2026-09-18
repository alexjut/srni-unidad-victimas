"""Serializers de la jerarquía de equipos (coordinador → supervisor → encuestadores)."""
from django.utils import timezone
from rest_framework import serializers

from .models import Equipo, MiembroEquipo, Usuario

# Quién puede estar al frente de un equipo. Un encuestador no supervisa: si lo
# hiciera, el «alcance de equipo» le abriría las entrevistas de sus compañeros.
PERFILES_SUPERVISORES = ('SUPERVISOR', 'COORDINADOR', 'ADMINISTRADOR')


class UsuarioDeEquipoSerializer(serializers.ModelSerializer):
    """Lo mínimo para listar gente dentro de un equipo."""
    perfil_codigo = serializers.CharField(source='perfil.codigo', read_only=True, default=None)

    class Meta:
        model = Usuario
        fields = ['id', 'codigo_usuario', 'nombre_completo', 'email', 'perfil_codigo', 'activo']


class EquipoSerializer(serializers.ModelSerializer):
    supervisor_codigo = serializers.CharField(
        source='supervisor.codigo_usuario', read_only=True)
    supervisor_nombre = serializers.CharField(
        source='supervisor.nombre_completo', read_only=True)
    direccion_territorial_nombre = serializers.CharField(
        source='direccion_territorial.nombre', read_only=True, default=None)
    total_encuestadores = serializers.SerializerMethodField()

    class Meta:
        model = Equipo
        fields = [
            'id', 'nombre',
            'supervisor', 'supervisor_codigo', 'supervisor_nombre',
            'direccion_territorial', 'direccion_territorial_nombre',
            'activo', 'total_encuestadores', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_total_encuestadores(self, equipo) -> int:
        return equipo.pertenencias.filter(hasta__isnull=True).count()

    def validate_supervisor(self, usuario):
        perfil = getattr(usuario.perfil, 'codigo', None)
        if perfil not in PERFILES_SUPERVISORES:
            raise serializers.ValidationError(
                f'{usuario.codigo_usuario} tiene perfil {perfil or "sin perfil"}: '
                'un equipo lo encabeza un supervisor, un coordinador o un administrador.'
            )
        if not usuario.activo:
            raise serializers.ValidationError(
                f'{usuario.codigo_usuario} está inactivo y no puede quedar a cargo de un equipo.'
            )
        return usuario


class EquipoDetalleSerializer(EquipoSerializer):
    encuestadores = serializers.SerializerMethodField()

    class Meta(EquipoSerializer.Meta):
        fields = EquipoSerializer.Meta.fields + ['encuestadores']

    def get_encuestadores(self, equipo):
        usuarios = Usuario.objects.filter(
            pertenencias_equipo__equipo=equipo,
            pertenencias_equipo__hasta__isnull=True,
        ).select_related('perfil').order_by('nombre_completo')
        return UsuarioDeEquipoSerializer(usuarios, many=True).data


class AsignarMiembrosSerializer(serializers.Serializer):
    """Agregar varios encuestadores de una vez: es como se arma un equipo en la práctica."""
    usuarios = serializers.ListField(
        child=serializers.UUIDField(), allow_empty=False, max_length=200,
    )

    def validate_usuarios(self, ids):
        encontrados = Usuario.objects.filter(id__in=ids)
        if encontrados.count() != len(set(ids)):
            raise serializers.ValidationError('Alguno de los usuarios no existe.')
        return ids

    def asignar(self, equipo, ids, por):
        """
        Mueve a cada persona a este equipo.

        Si ya pertenecía a otro, se le cierra esa pertenencia con fecha de hoy en vez
        de borrarla: el reporte del mes pasado tiene que seguir sabiendo de quién era.
        Nadie queda en dos equipos a la vez — la base lo impide, pero el trabajo de
        cerrar la anterior es de acá, no de la restricción.
        """
        hoy = timezone.localdate()
        agregados, movidos = [], []

        for usuario in Usuario.objects.filter(id__in=ids).select_related('perfil'):
            if usuario == equipo.supervisor:
                raise serializers.ValidationError(
                    f'{usuario.codigo_usuario} es el supervisor del equipo: no puede '
                    'supervisarse a sí mismo.'
                )

            activa = MiembroEquipo.objects.filter(
                usuario=usuario, hasta__isnull=True,
            ).select_related('equipo').first()

            if activa and activa.equipo_id == equipo.id:
                continue  # ya está acá: no se duplica ni se reescribe la fecha

            if activa:
                activa.hasta = hoy
                activa.save(update_fields=['hasta'])
                movidos.append(usuario.codigo_usuario)
            else:
                agregados.append(usuario.codigo_usuario)

            MiembroEquipo.objects.create(
                equipo=equipo, usuario=usuario, asignado_por=por,
            )

        return {'agregados': agregados, 'movidos_de_otro_equipo': movidos}
