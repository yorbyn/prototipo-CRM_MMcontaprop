"""Control de acceso al CRM privado. Tener sesión iniciada NO basta."""
from functools import wraps

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied


def tiene_acceso_crm(usuario):
    if not (usuario and usuario.is_authenticated and usuario.is_active):
        return False
    if usuario.is_superuser:
        return True
    return usuario.is_staff and usuario.groups.filter(
    name__in=[settings.GRUPO_CRM, settings.GRUPO_TRABAJADORES]).exists()


def crm_requerido(vista):
    """Decorador obligatorio para TODAS las vistas del CRM."""
    @wraps(vista)
    def envoltura(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not tiene_acceso_crm(request.user):
            raise PermissionDenied("Su usuario no tiene acceso al CRM.")
        return vista(request, *args, **kwargs)
    return envoltura
