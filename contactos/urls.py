from django.urls import path

from . import views

app_name = "contactos"

urlpatterns = [
    path("", views.lista_contacto, name="lista-contacto"),
    path("nueva/", views.crear_contacto, name="crear-contacto"),
    path("<int:pk>/", views.detalle_contacto, name="detalle-contacto"),
    path("<int:pk>/editar/", views.editar_contacto, name="actualizar-contacto"),
]
