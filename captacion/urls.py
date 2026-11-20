from django.urls import path
from . import views

app_name = "captacion"

urlpatterns = [
    path("", views.lista, name="lista"),
    path("nueva/", views.crear, name="crear"),
    path("<int:pk>/", views.detalle, name="detalle"),
    path("<int:pk>/editar/", views.editar, name="editar"),
    path("<int:pk>/aceptar/", views.aceptar, name="aceptar"),
    path("<int:pk>/rechazar/", views.rechazar, name="rechazar"),
    path("fotos/<int:pk>/", views.foto, name="foto"),
    path("fotos/<int:pk>/eliminar/", views.foto_eliminar, name="foto_eliminar"),
    path("encargos/nuevo/<int:propiedad_id>/", views.encargo_crear, name="encargo_crear"),
    path("encargos/<int:pk>/editar/", views.encargo_editar, name="encargo_editar"),
]
