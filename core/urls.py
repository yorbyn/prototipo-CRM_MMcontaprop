from django.urls import path

from . import views

app_name = "core" # nombre de la app

urlpatterns = [
    path("", views.dashboard, name="dashboard") #Dashboard es el panel de control
]