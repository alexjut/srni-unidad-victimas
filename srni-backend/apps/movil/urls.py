from django.urls import path

from . import views

urlpatterns = [
    path("version/", views.version, name="movil-version"),
    path("descargar/", views.descargar, name="movil-descargar"),
]
