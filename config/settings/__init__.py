"""
Configuración del CRM inmobiliario MMCONTAPROP SPA.

Se divide en tres archivos:

    base.py         Todo lo común: aplicaciones, base de datos SQLite, idioma,
                    archivos, reglas del CRM. No depende del entorno.
    desarrollo.py   DESARROLLO ACADÉMICO / LOCAL (lo que se usa con runserver).
                    Sin HTTPS, sin HSTS, sin cookies «secure», sin proxies.
    produccion.py   PRODUCCIÓN (servidor real con Nginx, HTTPS y Gunicorn).
                    Ver DESPLIEGUE.md. No se necesita para la evaluación.

Un solo interruptor elige cuál se usa: la variable DJANGO_DEBUG del archivo .env.

    DJANGO_DEBUG=true  (o si no existe .env, o si falta la variable) -> desarrollo
    DJANGO_DEBUG=false                                               -> producción

Así, un estudiante que ejecuta «python manage.py runserver» sin configurar nada
queda siempre en modo desarrollo. Producción hay que pedirla explícitamente.
"""
from .base import *  # noqa: F401,F403

if DEBUG:  # noqa: F405
    from .desarrollo import *  # noqa: F401,F403
else:
    from .produccion import *  # noqa: F401,F403
