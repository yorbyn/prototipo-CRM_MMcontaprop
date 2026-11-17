import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

SECRET_KEY = "django-insecure-^up)h3n^s34ohx_a0mcnor(y_9%0j_38f5ivh97^v*!$20-)**"

DEBUG = True

ALLOWED_HOSTS = []

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
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

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "es-cl"

TIME_ZONE = "America/Santiago"

USE_I18N = True

USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "core:login"
LOGIN_REDIRECT_URL = "core:dashboard"
LOGOUT_REDIRECT_URL = "core:login"

MESSAGE_TAGS = {40: "danger"}

PRIVATE_MEDIA_ROOT = BASE_DIR / "private_media"

GMAIL_USUARIO = os.getenv("GMAIL_USUARIO", "")
EMAIL_HOST_PASSWORD = os.getenv("GMAIL_CONTRASENA_APLICACION", "").replace(" ", "")
if GMAIL_USUARIO and EMAIL_HOST_PASSWORD:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = GMAIL_USUARIO
DEFAULT_FROM_EMAIL = f"MMCONTAPROP SPA <{GMAIL_USUARIO}>" if GMAIL_USUARIO else "webmaster@localhost"
CORREO_RESPONDER_A = GMAIL_USUARIO
CORREO_COPIA_OCULTA = False
CORREO_LIMITE_DIARIO = 500

EMPRESA = {
    "nombre": "MMCONTAPROP SPA",
    "lema": "Servicios Contables - Corretaje de Propiedades",
    "telefono": os.getenv("EMPRESA_TELEFONO", ""),
    "email": os.getenv("EMPRESA_EMAIL", ""),
}

MAX_FOTO_MB = 5
MAX_DOCUMENTO_MB = 10
GRUPO_CRM = "Administración CRM"
PORTAL_MAX_ENVIOS = 5
PORTAL_VENTANA_SEGUNDOS = 60 * 60
PROXIES_CONFIABLES = []
CSP_ACTIVA = False

LOGIN_MAX_INTENTOS = 5
LOGIN_BLOQUEO_SEGUNDOS = 15 * 60