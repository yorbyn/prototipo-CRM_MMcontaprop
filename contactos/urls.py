from django.urls import path

from . import views

app_name = "contactos"

urlpatterns = [
    path("", views.lista_contacto, name="lista_contacto"),
    path("<int:pk>/", views.detalle_contacto, name="detalle_contacto"),
]