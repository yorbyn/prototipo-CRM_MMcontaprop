from django.urls import path

from . import views

app_name = "documentos"

urlpatterns = [
    path("subir/<str:destino>/<int:pk>/", views.subir, name="subir"),
    path("<int:pk>/descargar/", views.descargar, name="descargar"),
    path("<int:pk>/eliminar/", views.eliminar, name="eliminar"),
]