from django.urls import path

from . import views

app_name = "propiedades"

urlpatterns = [
    path("", views.propiedad_lista, name="propiedad_lista"),
    path("nueva/", views.propiedad_crear, name="propiedad_crear"),
    path("<int:pk>/", views.propiedad_detalle, name="propiedad_detalle"),
    path("<int:pk>/editar/", views.propiedad_editar, name="propiedad_editar"),
    path("<int:pk>/estado/", views.cambiar_estado, name="cambiar_estado"),

    path("<int:pk>/fotos/", views.subir_fotos, name="subir_fotos"),
    path("fotos/<int:foto_id>/principal/", views.foto_principal, name="foto_principal"),
    path("fotos/<int:foto_id>/eliminar/", views.eliminar_foto, name="eliminar_foto"),

    path("<int:pk>/comprobantes/subir/", views.comprobante_subir, name="comprobante_subir"),
    path("comprobantes/<int:pk>/ver/", views.comprobante_ver, name="comprobante_ver"),
    path("comprobantes/<int:pk>/descargar/", views.comprobante_descargar, name="comprobante_descargar"),
    path("comprobantes/<int:pk>/eliminar/", views.comprobante_eliminar, name="comprobante_eliminar"),

    path("tipos/", views.tipos, name="tipos"),
    path("tipos/nuevo/", views.tipo_editar, name="tipo_crear"),
    path("tipos/<slug:clave>/editar/", views.tipo_editar, name="tipo_editar"),
    path("tipos/<slug:clave>/estado/", views.tipo_activar, name="tipo_activar"),
    path("tipos/<slug:clave>/eliminar/", views.tipo_eliminar, name="tipo_eliminar"),
]
