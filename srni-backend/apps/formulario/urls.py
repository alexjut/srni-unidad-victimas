from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    InstrumentoViewSet, TemaViewSet, PreguntaViewSet,
    EvaluarSkipLogicView,
)

router = DefaultRouter()
router.register(r'instrumentos', InstrumentoViewSet, basename='instrumento')
router.register(r'temas', TemaViewSet, basename='tema')
router.register(r'preguntas', PreguntaViewSet, basename='pregunta')

urlpatterns = router.urls + [
    path('evaluar-skip-logic/', EvaluarSkipLogicView.as_view(), name='evaluar-skip-logic'),
]
