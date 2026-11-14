"""Cabeceras de seguridad que Django no agrega por sí solo.

La política de contenido (CSP) se envía solo si settings.CSP_ACTIVA es True
(producción). En desarrollo queda apagada para no bloquear recursos que se
agreguen en clases o pruebas."""
from django.conf import settings

# Todo (estilos, scripts, fuentes, íconos) se sirve desde el propio sitio.
# 'unsafe-inline' solo para estilos: algunas plantillas usan atributos style=.
POLITICA_CONTENIDO = "; ".join([
    "default-src 'self'",
    "img-src 'self' data:",
    "style-src 'self' 'unsafe-inline'",
    "script-src 'self'",
    "font-src 'self'",
    "connect-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
])
PERMISOS = "camera=(), microphone=(), geolocation=(), payment=(), usb=()"


class CabecerasSeguridadMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        respuesta = self.get_response(request)
        if getattr(settings, "CSP_ACTIVA", False):
            respuesta.headers.setdefault("Content-Security-Policy", POLITICA_CONTENIDO)
        respuesta.headers.setdefault("Permissions-Policy", PERMISOS)
        return respuesta
