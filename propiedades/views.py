from django.shortcuts import get_object_or_404, render, redirect
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages
from core.permisos import crm_requerido

from actividades.models import Actividad

from .models import Propiedad
from .forms import FiltroPropiedadesForm, PropiedadForm
# Create your views here.

@crm_requerido
def lista_propiedad(request):
    filtros = FiltroPropiedadesForm(request.GET or None)
    propiedades = Propiedad.objects.select_related("propietario").prefetch_related("fotos")
    if filtros.is_valid():
        d = filtros.cleaned_data
        if d["q"]:
            q = d["q"]
            propiedades = propiedades.filter(
                Q(codigo__icontains=q) | Q(titulo__icontains=q) | Q(comuna__icontains=q)
                | Q(propietario__nombre__icontains=q) | Q(direccion_exacta__icontains=q)
            )
        for campo in ("estado", "operacion", "tipo", "zona"):
            if d[campo]:
                propiedades = propiedades.filter(**{campo: d[campo]})
        if d["precio_min"] is not None or d["precio_max"] is not None:
            propiedades = propiedades.filter(moneda=d["moneda"] or "CLP")
            if d["precio_min"] is not None:
                propiedades = propiedades.filter(precio__gte=d["precio_min"])
            if d["precio_max"] is not None:
                propiedades = propiedades.filter(precio__lte=d["precio_max"])
    pagina = Paginator(propiedades, 20).get_page(request.GET.get("page"))
    return render(request, "propiedades/lista_propiedad.html", {
        "filtros": filtros if request.GET else FiltroPropiedadesForm(),
        "pagina": pagina,
        "total": pagina.paginator.count,
    })

@crm_requerido
def crear_propiedad(request):
    inicial = {}
    if request.GET.get("propietario"):
        inicial["propietario"] = request.GET["propietario"]
    form = PropiedadForm(request.POST or None, initial=inicial)
    if request.method == "POST" and form.is_valid():
        propiedad = form.save(commit=False)
        propiedad.guardar_por(request.user)
        Actividad.registrar_sistema("Propiedad creada en estado Borrador.", request.user, propiedad=propiedad)
        messages.success(request, f"Propiedad {propiedad.codigo} creada como borrador. Ahora puedes subir fotografías.")
        return redirect(propiedad)
    return render(request, "propiedades/form_propiedad.html", {"form": form, "titulo": "Nueva propiedad"})

@crm_requerido
def editar_propiedad(request, pk):
    propiedad = get_object_or_404(Propiedad, pk=pk)
    form = PropiedadForm(request.POST or None, instance=propiedad)
    if request.method == "POST" and form.is_valid():
        form.save(commit=False).guardar_por(request.user)
        messages.success(request, "Propiedad actualizada.")
        return redirect(propiedad)
    return render(request, "propiedades/form_propiedad.html", {
        "form": form, "titulo": f"Editar {propiedad.codigo}", "propiedad": propiedad,
    })

@crm_requerido
def detalle_propiedad(request, pk):
    propiedad = get_object_or_404(Propiedad, pk=pk)
    return render(request, "propiedades/detalle_propiedad.html", {
        "propiedad": propiedad, "fotos": propiedad.fotos.all(),
    })
