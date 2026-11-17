from django.urls import path

from . import views

app_name = "propiedades"

urlpatterns = [
    path("", views.lista_propiedad, name="lista-propiedad"),
    path("<int:pk>/", views.detalle_propiedad, name="detalle-propiedad"),
]