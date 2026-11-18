from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render

from .models import Contacto

ROLES = {
    "propietario": "es_propietario",
    "arrendatario": "es_arrendatario",
    "interesado": "es_interesado",
}

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


def detalle_contacto(request, pk):
    contacto = get_object_or_404(Contacto, pk=pk)
    return render(request, "contactos/detalle_contacto.html", {
        "contacto": contacto,
        "propiedades": contacto.propiedades.all(),
        "arriendos": contacto.arriendos.all(),
        "preferencias": contacto.preferencias.all(),
    })