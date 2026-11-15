from django.urls import path
from . import views

app_name = "portal"

urlpatterns = [
    path("", views.catalogo, name="catalogo"),
    path("propiedad/<str:codigo>/", views.ficha, name="ficha"),
    path("ofrecer-mi-propiedad/", views.ofrecer, name="ofrecer"),
    path("contacto/", views.contacto, name="contacto"),
]
