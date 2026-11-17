from django.conf import settings
from django.contrib.auth.views import LoginView
from django.core.cache import cache
from django.shortcuts import render
from .limites import ip_cliente
from .permisos import crm_requerido, tiene_acceso_crm

"""Guía del equipo: etapa 2 viendo las plantillas primero
Page 6 of 11"""

class LoginProtegidoView(LoginView):
    template_name = "core/login.html"
    redirect_authenticated_user = True

    def _clave(self):
        return f"login-fallos:{ip_cliente(self.request)}"

    def _bloqueado(self):
        return cache.get(self._clave(), 0) >= settings.LOGIN_MAX_INTENTOS

    def _registrar_fallo(self):
        clave = self._clave()
        cache.add(clave, 0, settings.LOGIN_BLOQUEO_SEGUNDOS)
        try:
            cache.incr(clave)
        except ValueError:
            cache.set(clave, 1, settings.LOGIN_BLOQUEO_SEGUNDOS)

    def post(self, request, *args, **kwargs):
        if self._bloqueado():
            return self.render_to_response(self.get_context_data(form=self.get_form_class()(request), bloqueado=True))
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        if not tiene_acceso_crm(form.get_user()):
            form.add_error(None, "Este usuario no tiene acceso al CRM.")
            return self.form_invalid(form)
        cache.delete(self._clave())
        return super().form_valid(form)
    
    def form_invalid(self, form):
        self._registrar_fallo()
        return super().form_invalid(form)

@crm_requerido
def dashboard(request):
    return render(request, "core/dashboard.html")
