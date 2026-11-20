from django.urls import path

from . import views

app_name = "propiedades"

urlpatterns = [
    path("", views.lista_propiedad, name="lista-propiedad"),
    path("nueva/", views.crear_propiedad, name="crear-propiedad"),
    path("<int:pk>/", views.detalle_propiedad, name="detalle-propiedad"),
    path("<int:pk>/editar/", views.editar_propiedad, name="actualizar-propiedad"),
]