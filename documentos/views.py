import os

from django.contrib import messages
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from contactos.models import Contacto
from core.permisos import crm_requerido
from propiedades.models import Propiedad

from .forms import DocumentoForm
from .models import Documento

from comercial.models import Operacion

DESTINOS = {"contacto": Contacto, "propiedad": Propiedad, "operacion": Operacion}


@crm_requerido
@require_POST
def subir(request, destino, pk):
    modelo = DESTINOS.get(destino)
    if modelo is None:
        return redirect("core:dashboard")
    objeto = get_object_or_404(modelo, pk=pk)
    form = DocumentoForm(request.POST, request.FILES, instance=Documento(**{destino: objeto}))
    if form.is_valid():
        form.instance.guardar_por(request.user)
        messages.success(request, "Documento adjuntado.")
    else:
        for errores in form.errors.values():
            for e in errores:
                messages.error(request, e)
    return redirect(objeto.get_absolute_url() + "#documentos")


@crm_requerido
def descargar(request, pk):
    doc = get_object_or_404(Documento, pk=pk)
    archivo = doc.archivo
    if not archivo or not archivo.storage.exists(archivo.name):
        raise Http404("El archivo no existe.")
    ext = os.path.splitext(archivo.name)[1]
    respuesta = FileResponse(archivo.open("rb"), as_attachment=True, filename=f"{doc.nombre}{ext}")
    respuesta["Cache-Control"] = "private, no-store"
    return respuesta


@crm_requerido
@require_POST
def eliminar(request, pk):
    doc = get_object_or_404(Documento, pk=pk)
    destino = doc.duenio
    doc.archivo.delete(save=False)  # borra el archivo del disco
    doc.delete()                    # borra el registro de la base de datos
    messages.success(request, "Documento eliminado.")
    return redirect(destino.get_absolute_url() + "#documentos") if destino else redirect("core:dashboard")