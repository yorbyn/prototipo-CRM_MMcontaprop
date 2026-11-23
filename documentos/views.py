import os

from django.contrib import messages
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from comercial.models import Operacion
from contactos.models import Contacto
from core.permisos import crm_requerido
from propiedades.models import Propiedad

from .forms import DocumentoForm
from .models import Documento

# Fichas a las que se puede adjuntar un documento (el valor <destino> de la URL).
DESTINOS = {"contacto": Contacto, "propiedad": Propiedad, "operacion": Operacion}


@crm_requerido
@require_POST
def subir(request, destino, pk):
    modelo = DESTINOS.get(destino)
    if modelo is None:
        return redirect("core:dashboard")
    objeto = get_object_or_404(modelo, pk=pk)
    # La ficha dueña se fija aquí (por ejemplo Documento(contacto=objeto)), nunca desde el navegador.
    form = DocumentoForm(request.POST, request.FILES, instance=Documento(**{destino: objeto}))
    if form.is_valid():
        form.save()
        messages.success(request, "Documento adjuntado.")
    else:
        for errores in form.errors.values():
            for error in errores:
                messages.error(request, error)
    return redirect(objeto.get_absolute_url() + "#documentos")


@crm_requerido
def descargar(request, pk):
    """Los documentos están fuera de media/ y no tienen URL pública: solo se descargan
    desde aquí, con sesión del CRM. FileResponse envía el archivo al navegador."""
    documento = get_object_or_404(Documento, pk=pk)
    archivo = documento.archivo
    if not archivo.storage.exists(archivo.name):
        raise Http404("El archivo no existe.")
    extension = os.path.splitext(archivo.name)[1]
    return FileResponse(archivo.open("rb"), as_attachment=True, filename=f"{documento.nombre}{extension}")


@crm_requerido
@require_POST
def eliminar(request, pk):
    documento = get_object_or_404(Documento, pk=pk)
    ficha = documento.duenio  # contacto, propiedad u operación a la que pertenece
    documento.archivo.delete(save=False)  # borra el archivo del disco
    documento.delete()                    # borra el registro de la base de datos
    messages.success(request, "Documento eliminado.")
    return redirect(ficha.get_absolute_url() + "#documentos")
