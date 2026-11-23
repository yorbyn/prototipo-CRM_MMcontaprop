from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .permisos import crm_requerido, tiene_acceso_crm


def iniciar_sesion(request):
    # "next" es la página del CRM que se quería abrir antes de iniciar sesión.
    siguiente = request.POST.get("next") or request.GET.get("next", "")
    if not url_has_allowed_host_and_scheme(siguiente, allowed_hosts={request.get_host()}):
        siguiente = ""  # solo se vuelve a páginas de este mismo sitio

    if request.user.is_authenticated and tiene_acceso_crm(request.user):
        return redirect(siguiente or "core:dashboard")

    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        usuario = form.get_user()
        if tiene_acceso_crm(usuario):
            login(request, usuario)
            return redirect(siguiente or "core:dashboard")
        form.add_error(None, "Este usuario no tiene acceso al CRM.")
    return render(request, "core/login.html", {"form": form, "next": siguiente})


@require_POST
def cerrar_sesion(request):
    logout(request)
    return redirect("core:login")


@crm_requerido
def dashboard(request):
    return render(request, "core/dashboard.html")
