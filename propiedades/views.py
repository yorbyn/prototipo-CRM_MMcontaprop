from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Max, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from actividades.forms import ActividadForm, ProgramarForm
from actividades.models import Actividad
from captacion.models import SolicitudCaptacion, fotos_solicitud_pendientes, publicar_fotos_solicitud
from comercial.cruce import interesados_para
from comercial.models import Operacion
from core.permisos import crm_requerido
from documentos.forms import DocumentoForm

from .forms import CambioEstadoForm, FiltroPropiedadesForm, FotoForm, PropiedadForm, TipoPropiedadForm
from .models import FotoPropiedad, Propiedad, TipoPropiedad


# ---------------------------------------------------------------------------
# Propiedades
# ---------------------------------------------------------------------------

@crm_requerido
def propiedad_lista(request):
    filtros = FiltroPropiedadesForm(request.GET or None)
    propiedades = Propiedad.objects.select_related("propietario", "tipo").prefetch_related("fotos")
    if filtros.is_valid():
        datos = filtros.cleaned_data
        if datos["q"]:
            q = datos["q"]
            propiedades = propiedades.filter(
                Q(codigo__icontains=q) | Q(titulo__icontains=q) | Q(comuna__icontains=q)
                | Q(propietario__nombre__icontains=q) | Q(direccion_exacta__icontains=q)
            )
        for campo in ("estado", "operacion", "tipo", "zona"):
            if datos[campo]:
                propiedades = propiedades.filter(**{campo: datos[campo]})
        # El precio solo se compara en una moneda (no se convierte UF a pesos).
        if datos["precio_min"] is not None or datos["precio_max"] is not None:
            propiedades = propiedades.filter(moneda=datos["moneda"] or Propiedad.Moneda.CLP)
            if datos["precio_min"] is not None:
                propiedades = propiedades.filter(precio__gte=datos["precio_min"])
            if datos["precio_max"] is not None:
                propiedades = propiedades.filter(precio__lte=datos["precio_max"])
    pagina = Paginator(propiedades, 20).get_page(request.GET.get("page"))
    return render(request, "propiedades/propiedad_lista.html", {
        "filtros": filtros if request.GET else FiltroPropiedadesForm(),
        "pagina": pagina,
        "total": pagina.paginator.count,
    })


@crm_requerido
def propiedad_crear(request):
    # ?propietario=<id> deja elegido al propietario (botón «Nueva propiedad» de su ficha).
    form = PropiedadForm(request.POST or None, initial={"propietario": request.GET.get("propietario")})
    if request.method == "POST" and form.is_valid():
        propiedad = form.save()
        Actividad.registrar_sistema("Propiedad creada en estado Borrador.", request.user, propiedad=propiedad)
        messages.success(request, f"Propiedad {propiedad.codigo} creada como borrador. Ahora puedes subir fotografías.")
        return redirect(propiedad)
    return render(request, "propiedades/propiedad_form.html", {"form": form, "titulo": "Nueva propiedad"})


@crm_requerido
def propiedad_editar(request, pk):
    propiedad = get_object_or_404(Propiedad, pk=pk)
    form = PropiedadForm(request.POST or None, instance=propiedad)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Propiedad actualizada.")
        return redirect(propiedad)
    return render(request, "propiedades/propiedad_form.html", {
        "form": form, "titulo": f"Editar {propiedad.codigo}", "propiedad": propiedad,
    })


@crm_requerido
def propiedad_detalle(request, pk):
    propiedad = get_object_or_404(Propiedad, pk=pk)
    return render(request, "propiedades/propiedad_detalle.html", {
        "propiedad": propiedad,
        "fotos": propiedad.fotos.all(),
        "form_estado": CambioEstadoForm(initial={"estado": propiedad.estado}),
        "errores_publicar": propiedad.errores_para_publicar(),
        "encargos": propiedad.encargos.all(),
        "fotos_privadas": fotos_solicitud_pendientes(propiedad),
        "solicitud": SolicitudCaptacion.objects.filter(propiedad=propiedad).first(),
        "oportunidades": propiedad.oportunidades.select_related("contacto"),
        "interesados": interesados_para(propiedad),
        # Para los parciales de documentos y de historial:
        "objeto": propiedad,
        "destino": "propiedad",
        "documentos": propiedad.documentos.all(),
        "form_documento": DocumentoForm(),
        "actividades": propiedad.actividades.select_related("contacto")[:80],
        "form_actividad": ActividadForm(),
        "form_programar": ProgramarForm(fijo="propiedad"),
    })


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

    vigente = propiedad.operaciones.filter(estado=Operacion.Estado.VIGENTE).first()
    if vigente:
        messages.error(request, f"La propiedad tiene una operación vigente (oportunidad #{vigente.oportunidad_id}). "
                                "Para cambiar su estado, anule primero la operación.")
        return redirect(propiedad)
    if nuevo == Propiedad.Estado.DISPONIBLE:
        errores = propiedad.errores_para_publicar()
        if errores:
            for error in errores:
                messages.error(request, error)
            return redirect(propiedad)

    anterior = propiedad.get_estado_display()
    copiadas = 0
    with transaction.atomic():
        if nuevo == Propiedad.Estado.DISPONIBLE:
            # Las fotos privadas de la solicitud de captación pasan a la galería pública recién ahora.
            copiadas = publicar_fotos_solicitud(propiedad)
        propiedad.estado = nuevo
        propiedad.save()
    if copiadas:
        Actividad.registrar_sistema(f"{copiadas} foto(s) enviadas por el propietario pasaron a la galería pública.",
                                    request.user, propiedad=propiedad)
    Actividad.registrar_sistema(f"Estado cambiado de «{anterior}» a «{propiedad.get_estado_display()}».",
                                request.user, propiedad=propiedad)
    if propiedad.publicada:
        messages.success(request, "La propiedad ahora está publicada en el portal.")
    else:
        messages.success(request, f"Estado actualizado a «{propiedad.get_estado_display()}». "
                                  "No aparece en el portal público.")
    return redirect(propiedad)


# ---------------------------------------------------------------------------
# Fotografías
# ---------------------------------------------------------------------------

@crm_requerido
@require_POST
def subir_fotos(request, pk):
    propiedad = get_object_or_404(Propiedad, pk=pk)
    archivos = request.FILES.getlist("imagenes")  # el input permite elegir varias a la vez
    if not archivos:
        messages.error(request, "Selecciona al menos una fotografía.")
        return redirect(propiedad.get_absolute_url() + "#fotos")

    # Primero se validan todas: si una falla, no se guarda ninguna.
    forms = []
    for archivo in archivos:
        form = FotoForm(files={"imagen": archivo})
        if not form.is_valid():
            for error in form.errors["imagen"]:
                messages.error(request, f"{archivo.name}: {error}")
            return redirect(propiedad.get_absolute_url() + "#fotos")
        forms.append(form)

    siguiente = (propiedad.fotos.aggregate(m=Max("orden"))["m"] or 0) + 1
    sin_principal = not propiedad.fotos.filter(es_principal=True).exists()
    for i, form in enumerate(forms):
        foto = form.save(commit=False)
        foto.propiedad = propiedad
        foto.orden = siguiente + i
        foto.es_principal = sin_principal and i == 0  # la primera queda de portada si no había
        foto.save()
    messages.success(request, f"{len(forms)} fotografía(s) subida(s).")
    return redirect(propiedad.get_absolute_url() + "#fotos")


@crm_requerido
@require_POST
def foto_principal(request, foto_id):
    foto = get_object_or_404(FotoPropiedad, pk=foto_id)
    foto.propiedad.fotos.update(es_principal=False)
    foto.es_principal = True
    foto.save()
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
    foto.imagen.delete(save=False)  # borra el archivo del disco
    foto.delete()                   # borra el registro de la base de datos
    if era_principal:
        primera = propiedad.fotos.order_by("orden", "id").first()
        if primera:
            primera.es_principal = True
            primera.save()
    messages.success(request, "Fotografía eliminada.")
    return redirect(propiedad.get_absolute_url() + "#fotos")


# ---------------------------------------------------------------------------
# Tipos de propiedad
# ---------------------------------------------------------------------------

@crm_requerido
def tipos(request):
    lista = TipoPropiedad.objects.annotate(n_propiedades=Count("propiedades")).order_by("nombre")
    return render(request, "propiedades/tipo_lista.html", {"tipos": lista})


@crm_requerido
def tipo_editar(request, clave=None):
    """Crea un tipo (sin clave) o edita uno existente."""
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
    tipo.save()
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
