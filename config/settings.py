import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Cargar las variables del archivo .env
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("SECRET_KEY")

DEBUG = os.getenv("DEBUG", "False") == "True"

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")

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
    "usuarios",
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
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-cl"
TIME_ZONE = "America/Santiago"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Archivos estáticos y subidos ---
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"                  # fotos públicas de las propiedades
PRIVATE_MEDIA_ROOT = BASE_DIR / "private_media"  # documentos y fotos de solicitudes (solo CRM)

MAX_FOTO_MB = 5
MAX_DOCUMENTO_MB = 10

# --- Inicio de sesión ---
LOGIN_URL = "core:login"
LOGIN_REDIRECT_URL = "core:dashboard"
LOGOUT_REDIRECT_URL = "core:login"

# El nivel "error" de messages se muestra con la clase "danger" de Bootstrap.
MESSAGE_TAGS = {40: "danger"}

# --- Correo (Gmail). Sin usuario ni contraseña, los correos se muestran en la terminal ---
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

# --- Datos de la empresa que se muestran en el portal ---
EMPRESA = {
    "nombre": "MMCONTAPROP SPA",
    "lema": "Servicios Contables - Corretaje de Propiedades",
    "telefono": os.getenv("EMPRESA_TELEFONO", ""),
    "email": os.getenv("EMPRESA_EMAIL", ""),
}

# --- Roles del CRM (grupos de Django). Se reemplazan por Rol y Perfil en el paso 3 ---
GRUPO_CRM = "Administración CRM"
GRUPO_TRABAJADORES = "Trabajadores CRM"

# --- Temporales: los usa el límite de envíos del portal, que se quita en el paso 9 ---
PORTAL_MAX_ENVIOS = 5
PORTAL_VENTANA_SEGUNDOS = 60 * 60
PROXIES_CONFIABLES = []
