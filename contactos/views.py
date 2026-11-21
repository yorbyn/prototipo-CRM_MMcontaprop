from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render, redirect
from core.permisos import crm_requerido
from django.contrib import messages

from .forms import ContactoForm, PreferenciaForm
from documentos.forms import DocumentoForm
from .models import Contacto, PreferenciaBusqueda

ROLES = {
    "propietario": "es_propietario",
    "arrendatario": "es_arrendatario",
    "interesado": "es_interesado",
}

@crm_requerido
def lista_contacto(request):
    q = request.GET.get("q", "").strip()
    rol = request.GET.get("rol", "")
    # annotate(Count) agrupa y Django descarta Meta.ordering: se fija el orden explícito
    # para que la paginación sea estable.
    contactos = Contacto.objects.annotate(n_propiedades=Count("propiedades")).order_by("nombre", "pk")
    if q:
        q_rut = q.replace(".", "").replace(" ", "").upper()
        contactos = contactos.filter(Q(nombre__icontains=q) | Q(rut__icontains=q_rut))
    if rol in ROLES:
        contactos = contactos.filter(**{ROLES[rol]: True})
    pagina = Paginator(contactos, 25).get_page(request.GET.get("page"))
    return render(request, "contactos/lista_contacto.html", {
        "pagina": pagina, "q": q, "rol": rol, "total": pagina.paginator.count,
    })

@crm_requerido
def detalle_contacto(request, pk):
    contacto = get_object_or_404(Contacto, pk=pk)
    return render(request, "contactos/detalle_contacto.html", {
        "contacto": contacto,
        "propiedades": contacto.propiedades.all(),
        "arriendos": contacto.arriendos.all(),
        "preferencias": contacto.preferencias.all(),
        "form_preferencia": PreferenciaForm(),
        "objeto": contacto,
        "destino": "contacto",
        "documentos": contacto.documentos.all(),
        "form_documento": DocumentoForm(),
    })

@crm_requerido
def crear_contacto(request):
    inicial = {}
    if request.GET.get("rol") in ROLES:
        inicial[ROLES[request.GET["rol"]]] = True
    form = ContactoForm(request.POST or None, initial=inicial)
    if request.method == "POST" and form.is_valid():
        contacto = form.save(commit=False)
        contacto.guardar_por(request.user)
        messages.success(request, f"Contacto «{contacto}» registrado.")
        return redirect(contacto)
    return render(request, "contactos/form_contacto.html", {"form": form, "titulo": "Nuevo contacto"})

@crm_requerido
def editar_contacto(request, pk):
    contacto = get_object_or_404(Contacto, pk=pk)
    form = ContactoForm(request.POST or None, instance=contacto)
    if request.method == "POST" and form.is_valid():
        form.save(commit=False).guardar_por(request.user)
        messages.success(request, "Datos actualizados.")
        return redirect(contacto)
    return render(request, "contactos/form_contacto.html", {
        "form": form, "titulo": f"Editar: {contacto}", "contacto": contacto,
    })

@crm_requerido
def crear_preferencia(request, pk):
    contacto = get_object_or_404(Contacto, pk=pk)
    if not contacto.es_interesado:
        messages.error(request, "Las preferencias de búsqueda se registran para contactos con el rol de interesado.")
        return redirect(contacto)
    # El contacto se fija en el servidor, nunca desde datos del navegador.
    form = PreferenciaForm(request.POST, instance=PreferenciaBusqueda(contacto=contacto))
    if form.is_valid():
        form.save(commit=False).guardar_por(request.user)
        messages.success(request, "Preferencia de búsqueda registrada.")
    else:
        for errores in form.errors.values():
            for e in errores:
                messages.error(request, e)
    return redirect(contacto.get_absolute_url() + "#preferencias")

@crm_requerido
def editar_preferencia(request, pk):
    preferencia = get_object_or_404(PreferenciaBusqueda.objects.select_related("contacto"), pk=pk)
    contacto = preferencia.contacto
    form = PreferenciaForm(request.POST or None, instance=preferencia)
    if request.method == "POST" and form.is_valid():
        form.save(commit=False).guardar_por(request.user)
        messages.success(request, "Preferencia actualizada.")
        return redirect(contacto.get_absolute_url() + "#preferencias")
    return render(request, "contactos/preferencia_form.html", {"form": form, "contacto": contacto})

@crm_requerido
def eliminar_preferencia(request, pk):
    preferencia = get_object_or_404(PreferenciaBusqueda, pk=pk)
    contacto = preferencia.contacto
    preferencia.delete()
    messages.success(request, "Preferencia eliminada.")
    return redirect(contacto.get_absolute_url() + "#preferencias")