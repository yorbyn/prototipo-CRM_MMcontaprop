"""Roles del CRM. Se guardan como grupos de Django (no se necesita un modelo nuevo).

- Administrador: usa todo el CRM y además crea y edita usuarios.
- Trabajador: usa el CRM, pero no la pantalla de usuarios.
"""
from django.conf import settings

ADMINISTRADOR = "administrador"
TRABAJADOR = "trabajador"

ROLES = [
    (ADMINISTRADOR, "Administrador"),
    (TRABAJADOR, "Trabajador"),
]


def grupo_de(rol):
    """Nombre del grupo de Django que corresponde a cada rol."""
    return settings.GRUPO_CRM if rol == ADMINISTRADOR else settings.GRUPO_TRABAJADORES


def es_admin_crm(usuario):
    if not (usuario and usuario.is_authenticated and usuario.is_active):
        return False
    return usuario.is_superuser or usuario.groups.filter(name=settings.GRUPO_CRM).exists()


def rol_de(usuario):
    if es_admin_crm(usuario):
        return ADMINISTRADOR
    if usuario.groups.filter(name=settings.GRUPO_TRABAJADORES).exists():
        return TRABAJADOR
    return ""
