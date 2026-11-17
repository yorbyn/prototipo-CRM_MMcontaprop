from django.shortcuts import get_object_or_404, render

from .models import Propiedad
# Create your views here.

def lista_propiedad(request):
    propiedades = Propiedad.objects.select_related("propietario")
    return render(request, "propiedades/lista_propiedad.html", {
        "propiedades": propiedades, "total": propiedades.count(),
    })

def detalle_propiedad(request, pk):
    propiedad = get_object_or_404(Propiedad, pk=pk)
    return render(request, "propiedades/detalle_propiedad.html", {
        "propiedad": propiedad, "fotos": propiedad.fotos.all(),
    })
