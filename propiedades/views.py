from django.shortcuts import get_object_or_404, render, redirect
from django.core.paginator import Paginator
from django.db.models import Max, Q, Count
from django.db import transaction
from django.contrib import messages
from django.views.decorators.http import require_POST
from core.permisos import crm_requerido

from actividades.models import Actividad
from actividades.forms import ActividadForm, ProgramarForm
from captacion.models import SolicitudCaptacion, fotos_solicitud_pendientes, publicar_fotos_solicitud
from comercial.cruce import interesados_para
from core.imagenes import limpiar_imagen

from .models import Propiedad, FotoPropiedad, TipoPropiedad
from .forms import FiltroPropiedadesForm, PropiedadForm, CambioEstadoForm, FotosForm, TipoPropiedadForm
from documentos.forms import DocumentoForm
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
        "form_estado": CambioEstadoForm(initial={"estado": propiedad.estado}),
        "form_fotos": FotosForm(),
        "errores_publicar": propiedad.errores_para_publicar(),
        
        "objeto": propiedad,
        "destino": "propiedad",
        "documentos": propiedad.documentos.all(),
        "form_documento": DocumentoForm(),
        "encargos": propiedad.encargos.all(),
        "fotos_privadas": fotos_solicitud_pendientes(propiedad),
        "solicitud": SolicitudCaptacion.objects.filter(propiedad=propiedad).first(),
        "oportunidades": propiedad.oportunidades.select_related("contacto"),
        "interesados": interesados_para(propiedad),
        "actividades": propiedad.actividades.select_related("contacto")[:80],
        "form_actividad": ActividadForm(),
        "form_programar": ProgramarForm(fijo="propiedad"),
    })

def _mostrar_errores(request, form):
    for errores in form.errors.values():
        for e in errores:
            messages.error(request, e)

@crm_requerido
@require_POST
def cambiar_estado(request, pk):
    propiedad = get_object_or_404(Propiedad, pk=pk)
    form = CambioEstadoForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Estado no válido.")
        return redirect(propiedad)
    nuevo = form.cleaned_data["estado"]
    if nuevo == propiedad.estado:
        return redirect(propiedad)
    vigente = propiedad.operaciones.filter(estado="vigente").select_related("oportunidad").first()
    if vigente:
        messages.error(request, f"La propiedad tiene una operación vigente (oportunidad #{vigente.oportunidad_id}). "
                                "Para cambiar su estado, anule primero la operación.")
        return redirect(propiedad)
    if nuevo == Propiedad.Estado.DISPONIBLE:
        errores = propiedad.errores_para_publicar()
        if errores:
            for e in errores:
                messages.error(request, e)
            return redirect(propiedad)
    anterior = propiedad.get_estado_display()
    with transaction.atomic():
        copiadas = 0
        if nuevo == Propiedad.Estado.DISPONIBLE:
            # Las fotos privadas de la solicitud pasan a la galería pública recién ahora.
            copiadas = publicar_fotos_solicitud(propiedad)
        propiedad.estado = nuevo
        propiedad.guardar_por(request.user, update_fields=["estado", "actualizado", "modificado_por"])
    if copiadas:
        Actividad.registrar_sistema(f"{copiadas} foto(s) enviadas por el propietario pasaron a la galería pública.",
                                    request.user, propiedad=propiedad)
    Actividad.registrar_sistema(
        f"Estado cambiado de «{anterior}» a «{propiedad.get_estado_display()}».",
        request.user, propiedad=propiedad,
    )
    if propiedad.publicada:
        messages.success(request, "La propiedad ahora está publicada en el portal.")
    else:
        messages.success(request, f"Estado actualizado a «{propiedad.get_estado_display()}». "
                                  "No aparece en el portal público.")
    return redirect(propiedad)


@crm_requerido
def tipos(request):
    lista = TipoPropiedad.objects.annotate(n_propiedades=Count("propiedades")).order_by("nombre")
    return render(request, "propiedades/tipos.html", {"tipos": lista})


@crm_requerido
@require_POST
def tipo_editar(request, clave=None):
    tipo = get_object_or_404(TipoPropiedad, clave=clave) if clave else None
    form = TipoPropiedadForm(request.POST or None, instance=tipo)
    if request.method == "POST" and form.is_valid():
        tipo = form.save()
        messages.success(request, f"Tipo «{tipo}» guardado.")
        return redirect("propiedades:tipos")
    return render(request, "propiedades/tipo_form.html", {"form": form, "tipo": tipo})


@crm_requerido
@require_POST
def tipo_activar(request, clave):
    tipo = get_object_or_404(TipoPropiedad, clave=clave)
    tipo.activo = not tipo.activo
    tipo.save(update_fields=["activo"])
    estado = "activado" if tipo.activo else "desactivado: ya no se ofrece en los formularios ni en el portal"
    messages.success(request, f"Tipo «{tipo}» {estado}.")
    return redirect("propiedades:tipos")


@crm_requerido
@require_POST
def tipo_eliminar(request, clave):
    tipo = get_object_or_404(TipoPropiedad, clave=clave)
    if tipo.en_uso:
        messages.error(request, f"«{tipo}» está en uso por propiedades, preferencias o solicitudes: "
                                "no se puede eliminar. Puedes desactivarlo.")
    else:
        tipo.delete()
        messages.success(request, f"Tipo «{tipo}» eliminado.")
    return redirect("propiedades:tipos")


@crm_requerido
@require_POST
def subir_fotos(request, pk):
    propiedad = get_object_or_404(Propiedad, pk=pk)
    form = FotosForm(request.POST, request.FILES)
    if form.is_valid():
        siguiente = (propiedad.fotos.aggregate(m=Max("orden"))["m"] or 0) + 1
        sin_principal = not propiedad.fotos.filter(es_principal=True).exists()
        with transaction.atomic():
            for i, imagen in enumerate(form.cleaned_data["imagenes"]):
                # Se publica una copia sin metadatos (EXIF/GPS) de cada foto.
                FotoPropiedad.objects.create(
                    propiedad=propiedad, imagen=limpiar_imagen(imagen), orden=siguiente + i,
                    es_principal=sin_principal and i == 0,
                )
        messages.success(request, f"{len(form.cleaned_data['imagenes'])} fotografía(s) subida(s).")
    else:
        _mostrar_errores(request, form)
    return redirect(propiedad.get_absolute_url() + "#fotos")


@crm_requerido
@require_POST
def foto_principal(request, foto_id):
    foto = get_object_or_404(FotoPropiedad, pk=foto_id)
    with transaction.atomic():
        foto.propiedad.fotos.update(es_principal=False)
        foto.es_principal = True
        foto.save(update_fields=["es_principal"])
    messages.success(request, "Foto principal actualizada.")
    return redirect(foto.propiedad.get_absolute_url() + "#fotos")


@crm_requerido
@require_POST
def eliminar_foto(request, foto_id):
    foto = get_object_or_404(FotoPropiedad, pk=foto_id)
    propiedad = foto.propiedad
    if propiedad.publicada and propiedad.fotos.count() == 1:
        messages.error(request, "Una propiedad publicada debe tener al menos una foto. "
                                "Suba otra antes de eliminar esta o cambie su estado.")
        return redirect(propiedad.get_absolute_url() + "#fotos")
    era_principal = foto.es_principal
    foto.delete()
    if era_principal:
        primera = propiedad.fotos.order_by("orden", "id").first()
        if primera:
            primera.es_principal = True
            primera.save(update_fields=["es_principal"])
    messages.success(request, "Fotografía eliminada.")
    return redirect(propiedad.get_absolute_url() + "#fotos")