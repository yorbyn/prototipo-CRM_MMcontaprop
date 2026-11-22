"""Control de acceso al CRM privado. Tener sesión iniciada NO basta."""
from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied

from usuarios.models import Perfil


def tiene_acceso_crm(usuario):
    """Entran el superusuario y los usuarios con perfil (Administrador o Trabajador)."""
    if not (usuario and usuario.is_authenticated and usuario.is_active):
        return False
    return usuario.is_superuser or Perfil.objects.filter(user=usuario).exists()


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
