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
    qs = SolicitudCaptacion.objects.select_related("propiedad", "contacto")
    if estado in FILTROS:
        qs = qs.filter(estado=FILTROS[estado])
    if q:
        qs = qs.filter(Q(nombre__icontains=q) | Q(comuna__icontains=q) | Q(email__icontains=q)
                       | Q(rut__icontains=q.replace(".", "").upper()))
    pagina = Paginator(qs.order_by("-creado", "-pk"), 25).get_page(request.GET.get("page"))
    return render(request, "captacion/lista.html", {
        "pagina": pagina, "estado": estado, "q": q,
        "n_pendientes": SolicitudCaptacion.objects.filter(estado=SolicitudCaptacion.Estado.PENDIENTE).count(),
    })


@crm_requerido
def crear(request):
    form = SolicitudForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        solicitud = form.save(commit=False)
        solicitud.origen = SolicitudCaptacion.Origen.MANUAL
        solicitud.guardar_por(request.user)
        messages.success(request, f"Solicitud #{solicitud.pk} registrada. Evalúela para crear la propiedad.")
        return redirect(solicitud)
    return render(request, "captacion/form.html", {"form": form, "titulo": "Nueva solicitud de captación"})


@crm_requerido
def detalle(request, pk):
    solicitud = get_object_or_404(SolicitudCaptacion.objects.select_related("contacto", "propiedad"), pk=pk)
    coincidencia, conflicto = (None, None)
    if solicitud.pendiente:
        coincidencia, conflicto = solicitud.buscar_contacto()
    return render(request, "captacion/detalle.html", {
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
        form.save(commit=False).guardar_por(request.user)
        messages.success(request, "Solicitud actualizada.")
        return redirect(solicitud)
    return render(request, "captacion/form.html", {
        "form": form, "titulo": f"Editar solicitud #{solicitud.pk}", "solicitud": solicitud,
    })


@crm_requerido
@require_POST
def aceptar(request, pk):
    solicitud = get_object_or_404(SolicitudCaptacion, pk=pk)
    try:
        propiedad = solicitud.aceptar(request.user)
    except ValidationError as e:
        for m in e.messages:
            messages.error(request, m)
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
        solicitud.rechazar(request.user)
    except ValidationError as e:
        messages.error(request, " ".join(e.messages))
    else:
        messages.success(request, f"Solicitud #{solicitud.pk} rechazada.")
    return redirect(solicitud)


# ---------------------------------------------------------------------------
# Encargos de corretaje
# ---------------------------------------------------------------------------

@crm_requerido
def encargo_crear(request, propiedad_id):
    propiedad = get_object_or_404(Propiedad, pk=propiedad_id)
    # La propiedad se fija en el servidor, nunca desde datos del navegador.
    form = EncargoForm(request.POST or None, instance=Encargo(propiedad=propiedad))
    if request.method == "POST" and form.is_valid():
        encargo = form.save(commit=False)
        encargo.guardar_por(request.user)
        Actividad.registrar_sistema(f"Encargo de corretaje registrado: {encargo.resumen()}.",
                                    request.user, propiedad=propiedad)
        messages.success(request, "Encargo de corretaje registrado.")
        return redirect(propiedad.get_absolute_url() + "#encargos")
    return render(request, "captacion/encargo_form.html", {
        "form": form, "propiedad": propiedad, "titulo": f"Nuevo encargo · {propiedad.codigo}",
    })


@crm_requerido
def encargo_editar(request, pk):
    encargo = get_object_or_404(Encargo.objects.select_related("propiedad"), pk=pk)
    propiedad = encargo.propiedad
    anterior = encargo.resumen()
    form = EncargoForm(request.POST or None, instance=encargo)
    if request.method == "POST" and form.is_valid():
        encargo = form.save(commit=False)
        encargo.guardar_por(request.user)
        if encargo.resumen() != anterior:
            Actividad.registrar_sistema(f"Encargo de corretaje modificado: antes {anterior}; "
                                        f"ahora {encargo.resumen()}.", request.user, propiedad=propiedad)
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
    f = get_object_or_404(FotoSolicitud, pk=pk)
    if not f.imagen or not f.imagen.storage.exists(f.imagen.name):
        raise Http404("La foto no existe.")
    tipo = "image/png" if f.imagen.name.lower().endswith(".png") else "image/jpeg"
    respuesta = FileResponse(f.imagen.open("rb"), content_type=tipo)
    respuesta["Cache-Control"] = "private, no-store"
    respuesta["X-Content-Type-Options"] = "nosniff"
    return respuesta


@crm_requerido
@require_POST
def foto_eliminar(request, pk):
    f = get_object_or_404(FotoSolicitud.objects.select_related("solicitud__propiedad"), pk=pk)
    solicitud = f.solicitud
    if f.copiada_a_id:
        messages.error(request, "Esta foto ya está en la galería pública; elimínela desde la propiedad.")
    else:
        f.delete()
        messages.success(request, "Foto eliminada. No se publicará.")
    destino = request.POST.get("volver")
    if destino == "propiedad" and solicitud.propiedad:
        return redirect(solicitud.propiedad.get_absolute_url() + "#fotos")
    return redirect(solicitud)
