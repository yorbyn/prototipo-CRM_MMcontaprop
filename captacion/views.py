from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from actividades.models import Actividad
from core.permisos import crm_requerido
from propiedades.models import Propiedad

from .forms import EncargoForm, SolicitudForm
from .models import Encargo, FotoSolicitud, SolicitudCaptacion

# Pestañas de la lista (?estado=...) -> estado de la solicitud. «todas» no filtra.
FILTROS = {
    "pendientes": SolicitudCaptacion.Estado.PENDIENTE,
    "aceptadas": SolicitudCaptacion.Estado.ACEPTADA,
    "rechazadas": SolicitudCaptacion.Estado.RECHAZADA,
}


# ---------------------------------------------------------------------------
# Solicitudes
# ---------------------------------------------------------------------------

@crm_requerido
def lista(request):
    estado = request.GET.get("estado", "pendientes")
    q = request.GET.get("q", "").strip()
    solicitudes = SolicitudCaptacion.objects.select_related("propiedad", "tipo").order_by("-creado", "-pk")
    if estado in FILTROS:
        solicitudes = solicitudes.filter(estado=FILTROS[estado])
    if q:
        solicitudes = solicitudes.filter(Q(nombre__icontains=q) | Q(comuna__icontains=q) | Q(email__icontains=q)
                                         | Q(rut__icontains=q.replace(".", "").upper()))
    pagina = Paginator(solicitudes, 25).get_page(request.GET.get("page"))
    return render(request, "captacion/solicitud_lista.html", {
        "pagina": pagina, "estado": estado, "q": q,
        "n_pendientes": SolicitudCaptacion.objects.filter(estado=SolicitudCaptacion.Estado.PENDIENTE).count(),
    })


@crm_requerido
def crear(request):
    """Ingreso manual (el origen por defecto es «Ingreso manual»)."""
    form = SolicitudForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        solicitud = form.save()
        messages.success(request, f"Solicitud #{solicitud.pk} registrada. Evalúela para crear la propiedad.")
        return redirect(solicitud)
    return render(request, "captacion/solicitud_form.html", {"form": form, "titulo": "Nueva solicitud de captación"})


@crm_requerido
def detalle(request, pk):
    solicitud = get_object_or_404(SolicitudCaptacion, pk=pk)
    # Mientras está por evaluar, se avisa si el propietario ya existe como contacto.
    coincidencia, conflicto = solicitud.buscar_contacto() if solicitud.pendiente else (None, None)
    return render(request, "captacion/solicitud_detalle.html", {
        "solicitud": solicitud, "coincidencia": coincidencia, "conflicto": conflicto,
        "fotos_privadas": solicitud.fotos.all(),
    })


@crm_requerido
def editar(request, pk):
    solicitud = get_object_or_404(SolicitudCaptacion, pk=pk)
    if not solicitud.pendiente:
        messages.error(request, "Solo se pueden editar solicitudes por evaluar.")
        return redirect(solicitud)
    form = SolicitudForm(request.POST or None, instance=solicitud)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Solicitud actualizada.")
        return redirect(solicitud)
    return render(request, "captacion/solicitud_form.html", {
        "form": form, "titulo": f"Editar solicitud #{solicitud.pk}", "solicitud": solicitud,
    })


@crm_requerido
@require_POST
def aceptar(request, pk):
    solicitud = get_object_or_404(SolicitudCaptacion, pk=pk)
    try:
        propiedad = solicitud.aceptar()
    except ValidationError as e:
        for mensaje in e.messages:
            messages.error(request, mensaje)
        return redirect(solicitud)
    messages.success(request, f"Solicitud aceptada. Se creó la propiedad {propiedad.codigo} en borrador "
                              f"con «{propiedad.propietario}» como propietario. Complete la ficha y "
                              "registre el encargo de corretaje.")
    return redirect(propiedad)


@crm_requerido
@require_POST
def rechazar(request, pk):
    solicitud = get_object_or_404(SolicitudCaptacion, pk=pk)
    try:
        solicitud.rechazar()
        messages.success(request, f"Solicitud #{solicitud.pk} rechazada.")
    except ValidationError as e:
        messages.error(request, " ".join(e.messages))
    return redirect(solicitud)


# ---------------------------------------------------------------------------
# Encargos de corretaje
# ---------------------------------------------------------------------------

@crm_requerido
def encargo_crear(request, propiedad_id):
    propiedad = get_object_or_404(Propiedad, pk=propiedad_id)
    # La propiedad se fija aquí, nunca desde los datos que envía el navegador.
    form = EncargoForm(request.POST or None, instance=Encargo(propiedad=propiedad))
    if request.method == "POST" and form.is_valid():
        encargo = form.save()
        Actividad.registrar_sistema(f"Encargo de corretaje registrado: {encargo.resumen()}.",
                                    propiedad=propiedad)
        messages.success(request, "Encargo de corretaje registrado.")
        return redirect(propiedad.get_absolute_url() + "#encargos")
    return render(request, "captacion/encargo_form.html", {
        "form": form, "propiedad": propiedad, "titulo": f"Nuevo encargo · {propiedad.codigo}",
    })


@crm_requerido
def encargo_editar(request, pk):
    encargo = get_object_or_404(Encargo, pk=pk)
    propiedad = encargo.propiedad
    anterior = encargo.resumen()
    form = EncargoForm(request.POST or None, instance=encargo)
    if request.method == "POST" and form.is_valid():
        encargo = form.save()
        if encargo.resumen() != anterior:
            Actividad.registrar_sistema(f"Encargo de corretaje modificado: antes {anterior}; "
                                        f"ahora {encargo.resumen()}.", propiedad=propiedad)
        messages.success(request, "Encargo actualizado.")
        return redirect(propiedad.get_absolute_url() + "#encargos")
    return render(request, "captacion/encargo_form.html", {
        "form": form, "propiedad": propiedad, "encargo": encargo,
        "titulo": f"Editar encargo · {propiedad.codigo}",
    })


# ---------------------------------------------------------------------------
# Fotos privadas de la solicitud (solo CRM)
# ---------------------------------------------------------------------------

@crm_requerido
def foto(request, pk):
    """Muestra una foto privada. Están fuera de media/, así que solo se ven a través de esta vista."""
    foto = get_object_or_404(FotoSolicitud, pk=pk)
    if not foto.imagen.storage.exists(foto.imagen.name):
        raise Http404("La foto no existe.")
    return FileResponse(foto.imagen.open("rb"))


@crm_requerido
@require_POST
def foto_eliminar(request, pk):
    foto = get_object_or_404(FotoSolicitud, pk=pk)
    solicitud = foto.solicitud
    if foto.copiada_a_id:
        messages.error(request, "Esta foto ya está en la galería pública; elimínela desde la propiedad.")
    else:
        foto.imagen.delete(save=False)  # borra el archivo del disco
        foto.delete()                   # borra el registro de la base de datos
        messages.success(request, "Foto eliminada. No se publicará.")
    # Si se eliminó desde la ficha de la propiedad, se vuelve ahí.
    if request.POST.get("volver") == "propiedad" and solicitud.propiedad:
        return redirect(solicitud.propiedad.get_absolute_url() + "#fotos")
    return redirect(solicitud)
