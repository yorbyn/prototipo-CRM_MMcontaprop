from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from actividades.forms import ActividadForm, ProgramarForm
from comercial.cruce import propiedades_para
from core.permisos import crm_requerido
from documentos.forms import DocumentoForm

from .forms import ContactoForm, PreferenciaForm
from .models import Contacto, PreferenciaBusqueda

# Valor del filtro ?rol= -> campo del modelo.
ROLES = {
    "propietario": "es_propietario",
    "arrendatario": "es_arrendatario",
    "interesado": "es_interesado",
}


@crm_requerido
def contacto_lista(request):
    q = request.GET.get("q", "").strip()
    rol = request.GET.get("rol", "")
    # Con annotate() Django ignora el orden de Meta: se indica aquí para que la paginación sea estable.
    contactos = Contacto.objects.annotate(n_propiedades=Count("propiedades")).order_by("nombre", "pk")
    if q:
        q_rut = q.replace(".", "").replace(" ", "").upper()
        contactos = contactos.filter(Q(nombre__icontains=q) | Q(rut__icontains=q_rut))
    if rol in ROLES:
        contactos = contactos.filter(**{ROLES[rol]: True})
    pagina = Paginator(contactos, 25).get_page(request.GET.get("page"))
    return render(request, "contactos/contacto_lista.html", {
        "pagina": pagina, "q": q, "rol": rol, "total": pagina.paginator.count,
    })


@crm_requerido
def contacto_detalle(request, pk):
    contacto = get_object_or_404(Contacto, pk=pk)
    return render(request, "contactos/contacto_detalle.html", {
        "contacto": contacto,
        "propiedades": contacto.propiedades.all(),
        "arriendos": contacto.arriendos.all(),
        "preferencias": contacto.preferencias.all(),
        "form_preferencia": PreferenciaForm(),
        "oportunidades": contacto.oportunidades.select_related("propiedad"),
        "calces": propiedades_para(contacto),
        # Para los parciales de documentos y de historial:
        "objeto": contacto,
        "destino": "contacto",
        "documentos": contacto.documentos.all(),
        "form_documento": DocumentoForm(),
        "actividades": contacto.actividades.select_related("propiedad")[:80],
        "form_actividad": ActividadForm(),
        "form_programar": ProgramarForm(fijo="contacto"),
    })


@crm_requerido
def contacto_crear(request):
    # ?rol=propietario deja ese rol marcado de entrada.
    inicial = {ROLES[request.GET["rol"]]: True} if request.GET.get("rol") in ROLES else {}
    form = ContactoForm(request.POST or None, initial=inicial)
    if request.method == "POST" and form.is_valid():
        contacto = form.save()
        messages.success(request, f"Contacto «{contacto}» registrado.")
        return redirect(contacto)
    return render(request, "contactos/contacto_form.html", {"form": form, "titulo": "Nuevo contacto"})


@crm_requerido
def contacto_editar(request, pk):
    contacto = get_object_or_404(Contacto, pk=pk)
    form = ContactoForm(request.POST or None, instance=contacto)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Datos actualizados.")
        return redirect(contacto)
    return render(request, "contactos/contacto_form.html", {
        "form": form, "titulo": f"Editar: {contacto}", "contacto": contacto,
    })


@crm_requerido
@require_POST
def preferencia_crear(request, pk):
    contacto = get_object_or_404(Contacto, pk=pk)
    if not contacto.es_interesado:
        messages.error(request, "Las preferencias de búsqueda se registran para contactos con el rol de interesado.")
        return redirect(contacto)
    # El contacto se fija aquí, nunca desde los datos que envía el navegador.
    form = PreferenciaForm(request.POST, instance=PreferenciaBusqueda(contacto=contacto))
    if form.is_valid():
        form.save()
        messages.success(request, "Preferencia de búsqueda registrada.")
    else:
        for errores in form.errors.values():
            for error in errores:
                messages.error(request, error)
    return redirect(contacto.get_absolute_url() + "#preferencias")


@crm_requerido
def preferencia_editar(request, pk):
    preferencia = get_object_or_404(PreferenciaBusqueda, pk=pk)
    contacto = preferencia.contacto
    form = PreferenciaForm(request.POST or None, instance=preferencia)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Preferencia actualizada.")
        return redirect(contacto.get_absolute_url() + "#preferencias")
    return render(request, "contactos/preferencia_form.html", {"form": form, "contacto": contacto})


@crm_requerido
@require_POST
def preferencia_eliminar(request, pk):
    preferencia = get_object_or_404(PreferenciaBusqueda, pk=pk)
    contacto = preferencia.contacto
    preferencia.delete()
    messages.success(request, "Preferencia eliminada.")
    return redirect(contacto.get_absolute_url() + "#preferencias")
