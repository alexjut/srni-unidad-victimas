from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from drf_spectacular.utils import extend_schema, OpenApiResponse

from django.core.cache import cache

from .serializers import LoginSerializer, UsuarioMeSerializer, CambiarPasswordSerializer
from .throttles import LoginRateThrottle
from apps.auditoria.models import LogAcceso

# ─── Bloqueo de cuenta por intentos fallidos (anti-fuerza-bruta) ───────────────
# Complementa al throttle por-IP (5/min): tras N fallos del MISMO código de
# usuario, se bloquea por un tiempo. El contador vive en la caché Redis, así que
# es consistente entre workers de gunicorn y auto-expira.
LOGIN_MAX_INTENTOS = 5
LOGIN_VENTANA_SEG = 15 * 60      # ventana de conteo de fallos
LOGIN_BLOQUEO_SEG = 15 * 60      # duración del bloqueo
_KEY_INTENTOS = 'login_fallidos:%s'
_KEY_BLOQUEO = 'login_bloqueo:%s'


def _client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
    return xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR', '0.0.0.0')


def _registrar_intento_fallido(codigo, ip):
    """Incrementa (atómico) el contador de fallos y bloquea al superar el umbral.
    Tolerante a fallos de caché: nunca debe romper el flujo de login."""
    try:
        key = _KEY_INTENTOS % codigo
        try:
            intentos = cache.incr(key)
        except ValueError:
            cache.set(key, 1, LOGIN_VENTANA_SEG)
            intentos = 1
        if intentos and intentos >= LOGIN_MAX_INTENTOS:
            cache.set(_KEY_BLOQUEO % codigo, True, LOGIN_BLOQUEO_SEG)
            LogAcceso.registrar(
                accion='ACCESO_DENEGADO', resultado='DENEGADO', ip=ip,
                recurso='Login', recurso_id=codigo,
                detalle={'motivo': f'bloqueo por {intentos} intentos fallidos'},
            )
    except Exception:
        pass  # un fallo de caché/Redis no debe impedir registrar el login fallido


class LoginView(TokenObtainPairView):
    """
    POST /api/auth/login/
    Body: { "codigo_usuario": "...", "password": "..." }
    Response: { "access": "...", "refresh": "..." }
    """
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]   # 5 intentos/min por IP

    def post(self, request, *args, **kwargs):
        codigo = (request.data.get('codigo_usuario') or '').strip().upper()
        ip = _client_ip(request)

        # ¿Cuenta bloqueada por intentos fallidos previos?
        if codigo and cache.get(_KEY_BLOQUEO % codigo):
            return Response(
                {'detail': 'Cuenta bloqueada temporalmente por múltiples intentos '
                           'fallidos. Inténtalo de nuevo en unos minutos.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            if codigo:
                cache.delete(_KEY_INTENTOS % codigo)   # éxito → resetea el contador
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid()
            if hasattr(serializer, 'user') and serializer.user:
                serializer.user.fecha_ultimo_login = timezone.now()
                serializer.user.save(update_fields=['fecha_ultimo_login'])
        elif codigo and response.status_code in (400, 401):
            _registrar_intento_fallido(codigo, ip)

        return response


@extend_schema(
    request={'application/json': {'type': 'object', 'properties': {'refresh': {'type': 'string'}}, 'required': ['refresh']}},
    responses={200: OpenApiResponse(description='Sesión cerrada'), 400: OpenApiResponse(description='Token inválido')},
    summary='Cerrar sesión',
    description='Invalida el refresh token en la blacklist. El access token expira por TTL (15 min).',
    tags=['Autenticación'],
)
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response(
                {'error': 'Se requiere el refresh token.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'mensaje': 'Sesión cerrada correctamente.'})
        except TokenError:
            return Response(
                {'error': 'Token inválido o ya expirado.'},
                status=status.HTTP_400_BAD_REQUEST,
            )


@extend_schema(
    responses={200: UsuarioMeSerializer},
    summary='Perfil del usuario autenticado',
    description='Retorna datos del usuario y permisos de su perfil.',
    tags=['Autenticación'],
)
class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UsuarioMeSerializer(request.user)
        return Response(serializer.data)


@extend_schema(
    request=CambiarPasswordSerializer,
    responses={200: OpenApiResponse(description='Contraseña actualizada')},
    summary='Cambiar contraseña',
    description='Cambia la contraseña del usuario autenticado e invalida el refresh token activo.',
    tags=['Autenticación'],
)
class CambiarPasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CambiarPasswordSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)

        request.user.set_password(serializer.validated_data['password_nuevo'])
        request.user.save(update_fields=['password', 'updated_at'])

        refresh_token = request.data.get('refresh')
        if refresh_token:
            try:
                RefreshToken(refresh_token).blacklist()
            except TokenError:
                pass

        return Response({'mensaje': 'Contraseña actualizada. Inicia sesión nuevamente.'})
