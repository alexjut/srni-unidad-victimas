from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .serializers import LoginSerializer, UsuarioMeSerializer, CambiarPasswordSerializer


class LoginView(TokenObtainPairView):
    """
    POST /api/auth/login/
    Body: { "codigo_usuario": "...", "password": "..." }
    Response: { "access": "...", "refresh": "..." }
    """
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid()
            if hasattr(serializer, 'user') and serializer.user:
                serializer.user.fecha_ultimo_login = timezone.now()
                serializer.user.save(update_fields=['fecha_ultimo_login'])
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
