from django.urls import path

from . import views

app_name = "correo"

urlpatterns = [
    path("redactar/", views.redactar, name="redactar"),
    path("enviados/", views.enviados, name="enviados"),
    path("plantillas/", views.plantillas, name="plantillas"),
    path("plantillas/nueva/", views.plantilla_editar, name="plantilla_crear"),
    path("plantillas/<int:pk>/", views.plantilla_editar, name="plantilla_editar"),
]