from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied

from .roles import es_admin_crm


def admin_requerido(vista):
    """Solo administradores del CRM (o superusuarios)."""
    @wraps(vista)
    def envoltura(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not es_admin_crm(request.user):
            raise PermissionDenied("Solo un administrador puede gestionar usuarios.")
        return vista(request, *args, **kwargs)
    return envoltura
