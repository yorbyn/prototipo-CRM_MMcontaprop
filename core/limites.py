"""Límite de envíos por IP para los formularios públicos (usa la caché de Django,
sin dependencias nuevas). Con varios procesos en producción, la caché debe ser
compartida (base de datos o Redis) para que el límite sea común a todos."""
import ipaddress

from django.conf import settings
from django.core.cache import cache


def _ip_valida(valor):
    try:
        return str(ipaddress.ip_address((valor or "").strip()))
    except ValueError:
        return ""


def ip_cliente(request):
    """IP del visitante.

    Detrás de Nginx, REMOTE_ADDR es la del propio Nginx (127.0.0.1): todos los
    visitantes parecerían uno solo. Por eso, SOLO cuando la petición llega desde
    un proxy de confianza (DJANGO_PROXIES_CONFIABLES), se usa la cabecera
    X-Real-IP, que Nginx reemplaza siempre con la IP real. Si alguien envía esa
    cabecera directamente al servidor, se ignora."""
    remota = request.META.get("REMOTE_ADDR", "")
    if remota in settings.PROXIES_CONFIABLES:
        real = _ip_valida(request.META.get("HTTP_X_REAL_IP"))
        if real:
            return real
    return remota


def _clave(request, ambito):
    return f"envios:{ambito}:{ip_cliente(request)}"


def envios_excedidos(request, ambito):
    return cache.get(_clave(request, ambito), 0) >= settings.PORTAL_MAX_ENVIOS


def registrar_envio(request, ambito):
    clave = _clave(request, ambito)
    cache.add(clave, 0, settings.PORTAL_VENTANA_SEGUNDOS)
    try:
        cache.incr(clave)
    except ValueError:
        cache.set(clave, 1, settings.PORTAL_VENTANA_SEGUNDOS)
