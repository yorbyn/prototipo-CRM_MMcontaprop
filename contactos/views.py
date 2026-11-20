from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render, redirect
from core.permisos import crm_requerido
from django.contrib import messages

from .forms import ContactoForm
from .models import Contacto

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