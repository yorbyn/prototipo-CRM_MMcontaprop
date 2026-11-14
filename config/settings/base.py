"""
Configuración COMÚN a desarrollo y producción.

Aquí no hay nada relacionado con HTTPS, proxies ni servidores: eso vive en
produccion.py. Las variables de entorno se leen del archivo .env (opcional).
"""
import os
from pathlib import Path

# config/settings/base.py -> la carpeta del proyecto (donde está manage.py)
BASE_DIR = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# Lectura del archivo .env (sin dependencias externas)
# ---------------------------------------------------------------------------

def cargar_env(ruta):
    """Lee un archivo .env simple (CLAVE=valor). Si no existe, no pasa nada.
    Las variables ya definidas en el sistema tienen prioridad."""
    if not ruta.exists():
        return
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))


def env_bool(nombre, defecto=False):
    """true/True/TRUE/1/si/sí/yes -> True. Ignora espacios. Vacío -> valor por defecto."""
    valor = os.environ.get(nombre, "").strip().lower()
    if not valor:
        return defecto
    return valor in ("1", "true", "si", "sí", "yes")


def env_lista(nombre, defecto=""):
    return [v.strip() for v in os.environ.get(nombre, defecto).split(",") if v.strip()]


# DJANGO_ARCHIVO_ENV permite indicar otro archivo (lo usan las pruebas).
cargar_env(Path(os.environ.get("DJANGO_ARCHIVO_ENV", BASE_DIR / ".env")))

# Interruptor único entre desarrollo y producción (ver __init__.py).
# Por defecto TRUE: sin .env, o si falta la variable, el proyecto arranca en
# modo desarrollo. Producción exige escribir DJANGO_DEBUG=false a propósito.
DEBUG = env_bool("DJANGO_DEBUG", True)


# ---------------------------------------------------------------------------
# Aplicaciones
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    # Aplicaciones del proyecto
    "core",
    "contactos",
    "propiedades",
    "actividades",
    "documentos",
    "captacion",
    "comercial",
    "correo",
    "portal",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # Política de contenido (CSP): activa solo en producción (CSP_ACTIVA).
    "core.middleware.CabecerasSeguridadMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.empresa",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# ---------------------------------------------------------------------------
# Base de datos
# ---------------------------------------------------------------------------
# SQLite: un archivo db.sqlite3 en la carpeta del proyecto. No requiere instalar
# nada. Es la base de datos del proyecto en desarrollo y en la evaluación.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# OPCIONAL / FUTURO: PostgreSQL (también sirve para Supabase). Solo se activa si
# alguien escribe DB_ENGINE=postgresql en .env, y requiere instalar psycopg
# (despliegue/requirements-produccion.txt). No es necesario para la evaluación.
if os.environ.get("DB_ENGINE", "").strip().lower() == "postgresql":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("DB_NAME", "mmcontaprop"),
            "USER": os.environ.get("DB_USER", ""),
            "PASSWORD": os.environ.get("DB_PASSWORD", ""),
            "HOST": os.environ.get("DB_HOST", "localhost"),
            "PORT": os.environ.get("DB_PORT", "5432"),
            # Reutiliza conexiones entre peticiones y verifica que sigan vivas.
            "CONN_MAX_AGE": int(os.environ.get("DB_CONN_MAX_AGE", "60")),
            "CONN_HEALTH_CHECKS": True,
            # Supabase u otra base remota: DB_SSLMODE=require
            "OPTIONS": {"connect_timeout": 10,
                        **({"sslmode": os.environ["DB_SSLMODE"]} if os.environ.get("DB_SSLMODE") else {})},
        }
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ---------------------------------------------------------------------------
# Contraseñas, idioma y zona horaria
# ---------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-cl"
TIME_ZONE = "America/Santiago"
USE_I18N = True
USE_TZ = True
# Los precios se formatean con el filtro {{ valor|precio:moneda }} (core/templatetags).


# ---------------------------------------------------------------------------
# Archivos
# ---------------------------------------------------------------------------

# Estáticos (CSS, JS, logos, Bootstrap, íconos y fuentes en static/vendor/).
# Con runserver en desarrollo se sirven solos; no hace falta collectstatic.
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"   # solo para «collectstatic» en producción

# Archivos públicos: solo fotografías de propiedades.
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Archivos privados: documentos y fotos de solicitudes. NO se sirven por URL
# pública; solo mediante una vista que exige sesión iniciada.
PRIVATE_MEDIA_ROOT = BASE_DIR / "private_media"

# Límites de carga
MAX_FOTO_MB = 5
MAX_DOCUMENTO_MB = 10


# ---------------------------------------------------------------------------
# Reglas del CRM (iguales en desarrollo y producción)
# ---------------------------------------------------------------------------

# Para entrar al CRM el usuario debe estar activo, ser staff y pertenecer a este
# grupo (los superusuarios siempre tienen acceso).
GRUPO_CRM = "Administración CRM"
LOGIN_MAX_INTENTOS = 5
LOGIN_BLOQUEO_SEGUNDOS = 15 * 60

# Formularios públicos (consulta, «Contacto» y «Ofrecer mi propiedad»): envíos por
# IP y ventana. Desarrollo usa un límite más alto (ver desarrollo.py).
PORTAL_MAX_ENVIOS = 5
PORTAL_VENTANA_SEGUNDOS = 60 * 60

LOGIN_URL = "core:login"
LOGIN_REDIRECT_URL = "core:dashboard"
LOGOUT_REDIRECT_URL = "core:login"

# Sesiones y cookies (las opciones «secure», solo para HTTPS, están en produccion.py)
SESSION_COOKIE_AGE = 60 * 60 * 8  # 8 horas
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"

# Los avisos («Correo enviado a …») se guardan en la sesión, no en una cookie legible.
MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"
MESSAGE_TAGS = {40: "danger"}  # messages.ERROR -> clase Bootstrap "danger"

# IP real del visitante detrás de un proxy (Nginx). Vacío = sin proxy, que es el
# caso de desarrollo. Solo produccion.py lo lee del entorno.
PROXIES_CONFIABLES = []

# Política de contenido (CSP). Desactivada en desarrollo; activa en producción.
CSP_ACTIVA = False

# Registro de errores en la consola (la terminal de runserver, o el diario del
# sistema en producción). Nunca se registran contraseñas ni formularios.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"simple": {"format": "{asctime} {levelname} {name}: {message}", "style": "{"}},
    "handlers": {"consola": {"class": "logging.StreamHandler", "formatter": "simple"}},
    "root": {"handlers": ["consola"], "level": "WARNING"},
    "loggers": {
        # Un solo destino para los mensajes de Django (evita líneas duplicadas en runserver).
        "django": {"handlers": ["consola"], "level": "INFO", "propagate": False},
        "django.security": {"handlers": ["consola"], "level": "WARNING", "propagate": False},
        "mmcontaprop": {"handlers": ["consola"], "level": "INFO", "propagate": False},
    },
}

# Respaldos (python manage.py respaldar): carpeta de destino y cuántos conservar.
RESPALDO_DIR = Path(os.environ.get("RESPALDO_DIR", BASE_DIR / "respaldos"))
RESPALDO_CONSERVAR = int(os.environ.get("RESPALDO_CONSERVAR", "14"))


# ---------------------------------------------------------------------------
# Correo (Gmail personal con contraseña de aplicación)
# ---------------------------------------------------------------------------
# La contraseña se lee SOLO desde .env o el entorno, nunca del código.
# Si no se configura, desarrollo muestra los correos en la terminal (desarrollo.py).
GMAIL_USUARIO = os.environ.get("GMAIL_USUARIO", "").strip()
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_TIMEOUT = 20
EMAIL_HOST_USER = GMAIL_USUARIO
EMAIL_HOST_PASSWORD = os.environ.get("GMAIL_CONTRASENA_APLICACION", "").replace(" ", "")
DEFAULT_FROM_EMAIL = f"MMCONTAPROP SPA <{GMAIL_USUARIO}>" if GMAIL_USUARIO else "webmaster@localhost"
# Las respuestas llegan a esta dirección (por defecto, la misma cuenta de Gmail).
CORREO_RESPONDER_A = os.environ.get("CORREO_RESPONDER_A", GMAIL_USUARIO)
# Copia oculta de cada envío a CORREO_RESPONDER_A.
CORREO_COPIA_OCULTA = env_bool("CORREO_COPIA_OCULTA", False)
# Límite de Gmail para cuentas personales: 500 destinatarios al día.
CORREO_LIMITE_DIARIO = 500


# ---------------------------------------------------------------------------
# Datos públicos de la empresa (se muestran en el portal)
# ---------------------------------------------------------------------------

EMPRESA = {
    "nombre": "MMCONTAPROP SPA",
    "lema": "Servicios Contables - Corretaje de Propiedades",
    "telefono": os.environ.get("EMPRESA_TELEFONO", ""),
    "email": os.environ.get("EMPRESA_EMAIL", ""),
}
