from django.urls import path

from . import views

app_name = "actividades"

urlpatterns = [
    path("", views.agenda, name="agenda"),
    path("programar/", views.programar, name="programar"),
    path("programar/<str:destino>/<int:pk>/", views.programar_en, name="programar_en"),
    path("registrar/<str:destino>/<int:pk>/", views.registrar, name="registrar"),
    path("<int:pk>/completar/", views.completar, name="completar"),
]
