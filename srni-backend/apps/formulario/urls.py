from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    PerfilViewSet, InstrumentoVersionViewSet, CapituloViewSet,
    PreguntaViewSet, InstrumentoCompletoView, EvaluarSkipLogicView,
)

router = DefaultRouter()
router.register(r"perfiles", PerfilViewSet, basename="perfil")
router.register(r"versiones", InstrumentoVersionViewSet, basename="instrumento-version")
router.register(r"capitulos", CapituloViewSet, basename="capitulo")
router.register(r"preguntas", PreguntaViewSet, basename="pregunta")

urlpatterns = router.urls + [
    path("instrumento/<str:perfil_codigo>/", InstrumentoCompletoView.as_view(), name="instrumento-completo"),
    path("evaluar-skip-logic/", EvaluarSkipLogicView.as_view(), name="evaluar-skip-logic"),
]
