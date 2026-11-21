from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

urlpatterns = [
    path("crm/", include("core.urls")),
    path("crm/contactos/", include("contactos.urls")),
    path("crm/propiedades/", include("propiedades.urls")),
    path("crm/actividades/", include("actividades.urls")),
    path("crm/documentos/", include("documentos.urls")),
    path("crm/captacion/", include("captacion.urls")),
    path("crm/comercial/", include("comercial.urls")),
    path("crm/correo/", include("correo.urls")),
    path("crm/usuarios/", include("usuarios.urls")),
    path("", include("portal.urls")),
]

if settings.DEBUG:
    # Solo fotografías públicas. Los documentos privados nunca se exponen aquí.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
