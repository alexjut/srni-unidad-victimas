from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from unfold.admin import ModelAdmin as UnfoldModelAdmin
from .models import Usuario, Perfil


@admin.register(Perfil)
class PerfilAdmin(UnfoldModelAdmin):
    list_display = ['codigo', 'nombre', 'puede_buscar_rni', 'puede_caracterizar',
                    'puede_ver_reportes', 'puede_administrar', 'activo']
    list_filter = ['activo']
    search_fields = ['codigo', 'nombre']


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin, UnfoldModelAdmin):
    list_display = ['codigo_usuario', 'nombre_completo', 'email', 'perfil', 'activo', 'es_admin']
    list_filter = ['activo', 'es_admin', 'perfil']
    search_fields = ['codigo_usuario', 'nombre_completo', 'email']
    ordering = ['codigo_usuario']

    fieldsets = (
        (None, {'fields': ('codigo_usuario', 'password')}),
        ('Información personal', {'fields': ('nombre_completo', 'email')}),
        ('Permisos', {'fields': ('activo', 'es_admin', 'perfil', 'groups', 'user_permissions')}),
        ('Fechas', {'fields': ('fecha_ultimo_login', 'created_at', 'updated_at')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('codigo_usuario', 'email', 'nombre_completo', 'perfil', 'password1', 'password2'),
        }),
    )
    readonly_fields = ('created_at', 'updated_at', 'fecha_ultimo_login')
