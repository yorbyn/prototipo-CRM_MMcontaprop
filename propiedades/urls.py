from django.urls import path

from . import views

app_name = "propiedades"

urlpatterns = [
    path("", views.lista_propiedad, name="lista-propiedad"),
    path("nueva/", views.crear_propiedad, name="crear-propiedad"),
    path("<int:pk>/", views.detalle_propiedad, name="detalle-propiedad"),
    path("<int:pk>/editar/", views.editar_propiedad, name="actualizar-propiedad"),
    path("<int:pk>/estado/", views.cambiar_estado, name="cambiar_estado"),

    path("tipos/", views.tipos, name="tipos"),
    path("tipos/nuevo/", views.tipo_editar, name="tipo_crear"),
    path("tipos/<slug:clave>/editar/", views.tipo_editar, name="tipo_editar"),
    path("tipos/<slug:clave>/estado/", views.tipo_activar, name="tipo_activar"),
    path("tipos/<slug:clave>/eliminar/", views.tipo_eliminar, name="tipo_eliminar"),
    
    path("<int:pk>/fotos/", views.subir_fotos, name="subir_fotos"),
    path("fotos/<int:foto_id>/principal/", views.foto_principal, name="foto_principal"),
    path("fotos/<int:foto_id>/eliminar/", views.eliminar_foto, name="eliminar_foto"),
]