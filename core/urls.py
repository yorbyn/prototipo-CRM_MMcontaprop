from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("ingresar/", views.iniciar_sesion, name="login"),
    path("salir/", views.cerrar_sesion, name="logout"),
]
