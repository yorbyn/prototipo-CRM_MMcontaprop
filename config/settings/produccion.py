"""
PRODUCCIÓN (servidor real). NO se necesita para la evaluación académica.

Se usa SOLO con DJANGO_DEBUG=false escrito a propósito en .env, en un servidor
con Nginx (HTTPS) delante de Gunicorn. Instrucciones completas: DESPLIEGUE.md.

Aquí viven todas las opciones que obligan a usar HTTPS, confían en el proxy o
necesitan pasos extra (createcachetable, collectstatic).
"""
import os
import sys

from django.core.exceptions import ImproperlyConfigured

from .base import env_bool, env_lista

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "").strip()
if not SECRET_KEY:
    raise ImproperlyConfigured(
        "DJANGO_DEBUG=false activa el modo PRODUCCIÓN, que exige DJANGO_SECRET_KEY en .env.\n"
        "¿Está trabajando en su computador? Escriba DJANGO_DEBUG=true en el archivo .env "
        "(o borre esa línea) y vuelva a ejecutar el comando."
    )

ALLOWED_HOSTS = env_lista("DJANGO_ALLOWED_HOSTS")
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("Producción: defina DJANGO_ALLOWED_HOSTS en .env (ej.: mmcontaprop.cl).")
CSRF_TRUSTED_ORIGINS = env_lista("DJANGO_CSRF_TRUSTED_ORIGINS")

# --- HTTPS -------------------------------------------------------------------
SECURE_SSL_REDIRECT = env_bool("DJANGO_SSL_REDIRECT", True)
SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_HSTS_SEGUNDOS", 60 * 60 * 24 * 30))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("DJANGO_HSTS_SUBDOMINIOS", False)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# --- Proxy (Nginx) -------------------------------------------------------------
# IP de Nginx (con Nginx en el mismo servidor: 127.0.0.1). Solo si la petición
# viene de ahí se cree la cabecera X-Real-IP con la IP real del visitante.
PROXIES_CONFIABLES = env_lista("DJANGO_PROXIES_CONFIABLES")
if PROXIES_CONFIABLES:
    # Nginx reemplaza siempre esta cabecera (despliegue/nginx.conf).
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# --- Política de contenido (CSP) ----------------------------------------------
CSP_ACTIVA = True

# --- Caché compartida entre procesos de Gunicorn ------------------------------
# Requiere una vez: python manage.py createcachetable
if env_bool("DJANGO_CACHE_BD", True):
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.db.DatabaseCache",
                          "LOCATION": "cache_mmcontaprop"}}

# Aviso amistoso si alguien corre runserver en modo producción por error.
if len(sys.argv) > 1 and sys.argv[1] == "runserver":
    sys.stderr.write(
        "\n*** ATENCIÓN: runserver está en modo PRODUCCIÓN (DJANGO_DEBUG=false).\n"
        "*** El navegador será redirigido a https:// y la página no cargará.\n"
        "*** Para trabajar en su computador use DJANGO_DEBUG=true en el archivo .env.\n\n"
    )
