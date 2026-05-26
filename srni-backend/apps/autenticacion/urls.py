from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import LoginView, LogoutView, MeView, CambiarPasswordView

urlpatterns = [
    # Endpoints "oficiales" usados por el mobile (Sprint 1+)
    path('login/', LoginView.as_view(), name='auth-login'),
    path('refresh/', TokenRefreshView.as_view(), name='auth-refresh'),
    path('logout/', LogoutView.as_view(), name='auth-logout'),
    path('me/', MeView.as_view(), name='auth-me'),
    path('cambiar-password/', CambiarPasswordView.as_view(), name='auth-cambiar-password'),

    # Sprint 20 — aliases para el panel web (srni-frontend) que usa nombres
    # más estándar de SimpleJWT. Apuntan a las MISMAS views — no duplican lógica.
    path('token/',         LoginView.as_view(),        name='auth-token'),
    path('token/refresh/', TokenRefreshView.as_view(), name='auth-token-refresh'),
    path('perfil/',        MeView.as_view(),           name='auth-perfil'),
]
