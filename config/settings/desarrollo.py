"""
DESARROLLO ACADÉMICO / LOCAL.

Se usa con DJANGO_DEBUG=true (o cuando no existe .env). Pensado para:

    python manage.py migrate
    python manage.py createsuperuser
    python manage.py runserver

runserver solo entiende HTTP (http://127.0.0.1:8000). Por eso aquí se APAGAN
de forma explícita todas las opciones que obligan a usar HTTPS o que suponen un
servidor real delante (Nginx). Aunque el .env traiga valores de producción por
error, en este modo NO se aplican.
"""
import os

from .base import env_lista

# Clave solo para desarrollo. Si el .env trae una, se usa esa.
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "").strip() or "clave-solo-para-desarrollo-local-no-usar-en-produccion"

# Cualquier nombre de equipo: localhost, 127.0.0.1, la IP de la red local (para
# probar desde el celular con «runserver 0.0.0.0:8000») o un entorno en la nube
# como GitHub Codespaces. En producción la lista es obligatoria y cerrada.
ALLOWED_HOSTS = env_lista("DJANGO_ALLOWED_HOSTS") or ["*"]

# Solo si se trabaja detrás de un dominio con https (ej.: Codespaces):
# DJANGO_CSRF_TRUSTED_ORIGINS=https://*.app.github.dev
CSRF_TRUSTED_ORIGINS = env_lista("DJANGO_CSRF_TRUSTED_ORIGINS")

# --- HTTPS: TODO APAGADO en desarrollo -----------------------------------
SECURE_SSL_REDIRECT = False          # no redirigir http:// -> https://
SECURE_HSTS_SECONDS = 0              # sin HSTS (el navegador no «recuerda» HTTPS)
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SESSION_COOKIE_SECURE = False        # la cookie de sesión funciona con http://
CSRF_COOKIE_SECURE = False           # la cookie CSRF funciona con http://

# --- Proxies: TODO APAGADO en desarrollo -----------------------------------
SECURE_PROXY_SSL_HEADER = None       # no se confía en cabeceras X-Forwarded-*
USE_X_FORWARDED_HOST = False
USE_X_FORWARDED_PORT = False
PROXIES_CONFIABLES = []              # la IP del visitante es REMOTE_ADDR, sin más

# --- Política de contenido (CSP): apagada ------------------------------------
# Así, si alguien agrega un script o estilo externo en una plantilla durante
# una clase, funciona sin bloqueos «misteriosos». Producción la activa.
CSP_ACTIVA = False

# --- Caché en memoria: no requiere «createcachetable» ------------------------
# (El bloqueo de inicio de sesión se borra al reiniciar runserver.)
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

# --- Formularios públicos: límite más holgado para poder probarlos -----------
PORTAL_MAX_ENVIOS = 50

# --- Correo: sin Gmail configurado, los correos se muestran en la terminal ----
# Así se puede probar «Enviar correo» sin cuentas ni contraseñas. Si el .env trae
# GMAIL_USUARIO y GMAIL_CONTRASENA_APLICACION, se envían de verdad.
if not (os.environ.get("GMAIL_USUARIO", "").strip() and os.environ.get("GMAIL_CONTRASENA_APLICACION", "").strip()):
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
