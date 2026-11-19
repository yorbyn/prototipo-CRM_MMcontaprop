from django.urls import path

from . import views

app_name = "comercial"

urlpatterns = [
    # peschke seba mike aqui van las urls de la app 
    path("", views.lista, name="lista"),
    path("nueva/", views.crear, name="crear"),
    path("cruce/", views.crear_desde_cruce, name="crear_desde_cruce"),
    path("indicadores/", views.indicadores, name="indicadores"),
    path("indicadores/<str:tipo>.csv", views.exportar, name="exportar"),
    path("<int:pk>/", views.detalle, name="detalle"),
    path("<int:pk>/etapa/", views.cambiar_etapa, name="cambiar_etapa"),
    path("<int:pk>/perder/", views.perder, name="perder"),
    path("<int:pk>/propiedad/", views.asignar_propiedad, name="asignar_propiedad"),
    path("<int:pk>/ofertas/nueva/", views.oferta_registrar, name="oferta_registrar"),
    path("ofertas/<int:pk>/responder/", views.oferta_responder, name="oferta_responder"),
    path("<int:pk>/cierre/", views.cerrar, name="cerrar"),
    path("operaciones/<int:pk>/editar/", views.operacion_editar, name="operacion_editar"),
    path("operaciones/<int:pk>/anular/", views.operacion_anular, name="operacion_anular"),
    path("operaciones/<int:pk>/cerrar-otras/", views.cerrar_otras, name="cerrar_otras"),
]