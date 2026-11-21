from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import Group, User
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import UsuarioCrearForm, UsuarioEditarForm
from .permisos import admin_requerido
from .roles import grupo_de, rol_de


def _asignar_rol(usuario, rol):
    """Deja al usuario en el grupo de su rol (y solo en ese) y con acceso al CRM."""
    grupos = Group.objects.filter(name__in=[settings.GRUPO_CRM, settings.GRUPO_TRABAJADORES])
    usuario.groups.remove(*grupos)
    usuario.groups.add(Group.objects.get_or_create(name=grupo_de(rol))[0])
    if not usuario.is_staff:
        usuario.is_staff = True
        usuario.save(update_fields=["is_staff"])


@admin_requerido
def usuario_lista(request):
    usuarios = (User.objects.filter(Q(is_superuser=True) | Q(groups__name__in=[
        settings.GRUPO_CRM, settings.GRUPO_TRABAJADORES])).distinct().order_by("-is_active", "first_name", "username"))
    filas = [(u, rol_de(u)) for u in usuarios]
    return render(request, "usuarios/usuario_lista.html", {"filas": filas})


@admin_requerido
def usuario_crear(request):
    form = UsuarioCrearForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            usuario = form.save()
            _asignar_rol(usuario, form.cleaned_data["rol"])
        messages.success(request, f"Usuario «{usuario.username}» creado.")
        return redirect("usuarios:usuario_lista")
    return render(request, "usuarios/usuario_form.html", {"form": form, "titulo": "Nuevo usuario"})


@admin_requerido
def usuario_editar(request, pk):
    usuario = get_object_or_404(User, pk=pk)
    form = UsuarioEditarForm(request.POST or None, instance=usuario, initial={"rol": rol_de(usuario)})
    if usuario.is_superuser:
        # El superusuario siempre es administrador: su rol no se edita aquí.
        form.fields["rol"].disabled = True
    if request.method == "POST" and form.is_valid():
        if usuario == request.user and form.cleaned_data["rol"] != "administrador":
            messages.error(request, "No puedes quitarte a ti mismo el rol de administrador.")
            return redirect("usuarios:usuario_editar", pk=usuario.pk)
        with transaction.atomic():
            form.save()
            if not usuario.is_superuser:
                _asignar_rol(usuario, form.cleaned_data["rol"])
        messages.success(request, f"Usuario «{usuario.username}» actualizado.")
        return redirect("usuarios:usuario_lista")
    return render(request, "usuarios/usuario_form.html", {
        "form": form, "titulo": f"Editar «{usuario.username}»", "usuario_editado": usuario,
    })


@admin_requerido
@require_POST
def usuario_activar(request, pk):
    """No se borran usuarios: se desactivan, así su historial queda a su nombre."""
    usuario = get_object_or_404(User, pk=pk)
    if usuario == request.user:
        messages.error(request, "No puedes desactivar tu propio usuario.")
        return redirect("usuarios:usuario_lista")
    usuario.is_active = not usuario.is_active
    usuario.save(update_fields=["is_active"])
    estado = "activado" if usuario.is_active else "desactivado: ya no puede entrar al CRM"
    messages.success(request, f"Usuario «{usuario.username}» {estado}.")
    return redirect("usuarios:usuario_lista")
