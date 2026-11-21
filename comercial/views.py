from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.http import Http404
from django.utils import timezone
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from actividades.forms import ActividadForm, ProgramarForm
from contactos.models import Contacto
from core.permisos import crm_requerido
from documentos.forms import DocumentoForm
from propiedades.models import Propiedad

from . import indicadores as ind
from .cruce import ESTADOS_NO_OFRECIBLES

from .forms import (
    AsignarPropiedadForm,
    EtapaForm,
    FiltroOportunidadesForm,
    OfertaForm,
    OperacionForm,
    OportunidadForm,
    PerdidaForm,
    PeriodoForm,
    RespuestaOfertaForm,
    filtro_texto,
)
from .models import Oferta, Operacion, Oportunidad

# Create your views here.

VISTAS = {
    "abiertas": Oportunidad.ABIERTAS,
    **{e.value: (e.value,) for e in Oportunidad.Etapa},
    "todas": tuple(Oportunidad.Etapa.values),
}


def _errores(request, e):
    for m in e.messages:
        messages.error(request, m)


@crm_requerido
def lista(request):
    vista = request.GET.get("etapa", "abiertas")
    if vista not in VISTAS:
        vista = "abiertas"
    filtros = FiltroOportunidadesForm(request.GET or None)
    qs = Oportunidad.objects.select_related("contacto", "propiedad").filter(etapa__in=VISTAS[vista])
    if filtros.is_valid():
        if filtros.cleaned_data["q"]:
            qs = filtro_texto(qs, filtros.cleaned_data["q"].strip())
        if filtros.cleaned_data["origen"]:
            qs = qs.filter(origen=filtros.cleaned_data["origen"])
    conteo = dict(Oportunidad.objects.order_by().values_list("etapa").annotate(n=Count("id")))
    pestanas = [{"clave": e.value, "nombre": e.label, "total": conteo.get(e.value, 0)} for e in Oportunidad.Etapa]
    pagina = Paginator(qs.order_by("-creado", "-id"), 25).get_page(request.GET.get("page"))
    return render(request, "comercial/lista.html", {
        "pagina": pagina, "vista": vista, "pestanas": pestanas,
        "n_abiertas": sum(conteo.get(e, 0) for e in Oportunidad.ABIERTAS),
        "q": request.GET.get("q", ""), "origen": request.GET.get("origen", ""),
        "origenes": Oportunidad.Origen.choices,
    })


@crm_requerido
def crear(request):
    inicial = {k: request.GET[k] for k in ("contacto", "propiedad") if request.GET.get(k, "").isdigit()}
    form = OportunidadForm(request.POST or None, initial=inicial)
    if request.method == "POST" and form.is_valid():
        op = form.save(commit=False)
        op.origen = Oportunidad.Origen.MANUAL
        op.guardar_por(request.user)
        op._registrar("Oportunidad creada manualmente.", request.user)
        messages.success(request, "Oportunidad creada.")
        return redirect(op)
    return render(request, "comercial/form.html", {"form": form, "titulo": "Nueva oportunidad"})


@crm_requerido
def detalle(request, pk):
    op = get_object_or_404(Oportunidad.objects.select_related("contacto", "propiedad", "propiedad__propietario"), pk=pk)
    contexto = {
        "op": op,
        "objeto": op, "destino": "oportunidad",
        # Pasos del embudo que se muestran en la ficha (la pérdida se muestra aparte).
        "pasos": [Oportunidad.Etapa.NUEVA, Oportunidad.Etapa.CONTACTADO, Oportunidad.Etapa.VISITA,
                  Oportunidad.Etapa.NEGOCIACION, Oportunidad.Etapa.GANADA],
        "actividades": op.actividades.select_related("contacto", "propiedad")[:80],
        "form_actividad": ActividadForm(),
        "form_programar": ProgramarForm(fijo="oportunidad"),
        "form_etapa": EtapaForm(initial={"etapa": op.etapa}),
        "form_perdida": PerdidaForm(),
        "form_propiedad": AsignarPropiedadForm(oportunidad=op),
        "otras_abiertas": (Oportunidad.objects.filter(propiedad=op.propiedad, etapa__in=Oportunidad.ABIERTAS)
                           .exclude(pk=op.pk).select_related("contacto") if op.propiedad_id else []),
    }
    contexto.update({
        "ofertas": op.ofertas.all(),
        "form_documento": DocumentoForm(),
        "form_oferta": OfertaForm(initial={"moneda": op.propiedad.moneda if op.propiedad_id else "CLP"}),
    })
    return render(request, "comercial/detalle.html", contexto)


@crm_requerido
@require_POST
def cambiar_etapa(request, pk):
    op = get_object_or_404(Oportunidad, pk=pk)
    form = EtapaForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Etapa no válida.")
        return redirect(op)
    try:
        if op.cambiar_etapa(form.cleaned_data["etapa"], request.user):
            messages.success(request, f"Etapa actualizada a «{op.get_etapa_display()}».")
    except ValidationError as e:
        _errores(request, e)
    return redirect(op)


@crm_requerido
@require_POST
def perder(request, pk):
    op = get_object_or_404(Oportunidad, pk=pk)
    motivo = request.POST.get("motivo", "").strip()
    if len(motivo) > 500:
        messages.error(request, "El motivo no puede superar los 500 caracteres.")
        return redirect(op)
    try:
        op.perder(motivo, request.user)
        messages.success(request, "Oportunidad marcada como perdida.")
    except ValidationError as e:
        _errores(request, e)
    return redirect(op)


@crm_requerido
@require_POST
def asignar_propiedad(request, pk):
    op = get_object_or_404(Oportunidad, pk=pk)
    form = AsignarPropiedadForm(request.POST, oportunidad=op)
    if not form.is_valid():
        messages.error(request, "Elija una propiedad válida.")
        return redirect(op)
    try:
        op.asignar_propiedad(form.cleaned_data["propiedad"], request.user)
        messages.success(request, "Propiedad asignada.")
    except ValidationError as e:
        _errores(request, e)
    return redirect(op)


# ---------------------------------------------------------------------------
# Ofertas y contraofertas
# ---------------------------------------------------------------------------

@crm_requerido
@require_POST
def oferta_registrar(request, pk):
    op = get_object_or_404(Oportunidad, pk=pk)
    # La oportunidad se fija en el servidor.
    form = OfertaForm(request.POST, instance=Oferta(oportunidad=op))
    if form.is_valid():
        try:
            form.instance.registrar(request.user)
            messages.success(request, f"{form.instance.get_tipo_display()} registrada.")
        except ValidationError as e:
            _errores(request, e)
    else:
        for errores in form.errors.values():
            for e in errores:
                messages.error(request, e)
    return redirect(op.get_absolute_url() + "#ofertas")


@crm_requerido
@require_POST
def oferta_responder(request, pk):
    oferta = get_object_or_404(Oferta.objects.select_related("oportunidad"), pk=pk)
    form = RespuestaOfertaForm(request.POST)
    try:
        if not form.is_valid():
            raise ValidationError("Respuesta no válida.")
        oferta.responder(form.cleaned_data["respuesta"], request.user)
        messages.success(request, f"Respuesta registrada: {oferta.get_respuesta_display().lower()}.")
    except ValidationError as e:
        _errores(request, e)
    return redirect(oferta.oportunidad.get_absolute_url() + "#ofertas")


# ---------------------------------------------------------------------------
# Cruce de propiedades
# ---------------------------------------------------------------------------

@crm_requerido
@require_POST
def crear_desde_cruce(request):
    """Abre una oportunidad (origen «cruce») entre un interesado y una propiedad."""
    contacto = get_object_or_404(Contacto, pk=request.POST.get("contacto") or 0)
    propiedad = get_object_or_404(Propiedad, pk=request.POST.get("propiedad") or 0)
    existente = Oportunidad.objects.filter(contacto=contacto, propiedad=propiedad,
                                           etapa__in=Oportunidad.ABIERTAS).first()
    if existente:
        messages.info(request, "Ya existe una oportunidad abierta entre ambos.")
        return redirect(existente)
    if not contacto.es_interesado or propiedad.estado in ESTADOS_NO_OFRECIBLES \
            or propiedad.propietario_id == contacto.pk:
        messages.error(request, "No se puede abrir una oportunidad entre este contacto y esta propiedad.")
        return redirect(request.POST.get("volver") == "propiedad" and propiedad or contacto)
    op = Oportunidad(contacto=contacto, propiedad=propiedad, origen=Oportunidad.Origen.CRUCE)
    op.guardar_por(request.user)
    op._registrar("Oportunidad creada desde el cruce de propiedades.", request.user)
    messages.success(request, f"Oportunidad creada con {contacto} por {propiedad.codigo}.")
    return redirect(op)


# ---------------------------------------------------------------------------
# Operaciones y cierre
# ---------------------------------------------------------------------------

@crm_requerido
def cerrar(request, pk):
    """Registrar el cierre: la oportunidad pasa a ganada y la propiedad, sola, a
    vendida o arrendada."""
    op = get_object_or_404(Oportunidad.objects.select_related("propiedad", "contacto"), pk=pk)
    if not op.abierta or not op.propiedad_id:
        messages.error(request, "Solo se cierra una oportunidad abierta y con propiedad.")
        return redirect(op)
    operacion = Operacion(oportunidad=op, propiedad=op.propiedad, tipo=op.propiedad.operacion)
    aceptada = op.ofertas.filter(respuesta=Oferta.Respuesta.ACEPTADA).order_by("-fecha", "-id").first()
    precio = aceptada.monto if aceptada else op.propiedad.precio
    moneda = aceptada.moneda if aceptada else op.propiedad.moneda
    sugerida, encargo = Operacion.comision_sugerida(op.propiedad, precio)
    form = OperacionForm(request.POST or None, instance=operacion, initial={
        "precio_final": precio, "moneda": moneda, "comision_monto": sugerida, "comision_moneda": moneda,
    })
    if request.method == "POST" and form.is_valid():
        try:
            form.instance.cerrar(request.user)
        except ValidationError as e:
            _errores(request, e)
            return redirect(op)
        otras = Oportunidad.objects.filter(propiedad=op.propiedad, etapa__in=Oportunidad.ABIERTAS).count()
        messages.success(request, f"¡Cierre registrado! {op.propiedad.codigo} quedó "
                                  f"{op.propiedad.get_estado_display().lower()} y se retiró del portal.")
        if otras:
            messages.warning(request, f"Hay {otras} oportunidad(es) abiertas por esta propiedad. Puede cerrarlas "
                                      "como perdidas con el botón «Cerrar las demás como perdidas».")
        return redirect(op)
    return render(request, "comercial/operacion_form.html", {
        "form": form, "op": op, "aceptada": aceptada, "encargo": encargo, "titulo": "Registrar cierre",
    })


@crm_requerido
def operacion_editar(request, pk):
    operacion = get_object_or_404(Operacion.objects.select_related("oportunidad", "propiedad"), pk=pk)
    op = operacion.oportunidad
    if operacion.estado != Operacion.Estado.VIGENTE:
        messages.error(request, "La operación está anulada.")
        return redirect(op)
    anterior = operacion.resumen()
    form = OperacionForm(request.POST or None, instance=operacion)
    if request.method == "POST" and form.is_valid():
        form.save(commit=False).guardar_por(request.user)
        if operacion.resumen() != anterior:
            op._registrar(f"Operación actualizada: {operacion.resumen()}.", request.user)
        messages.success(request, "Operación actualizada.")
        return redirect(op.get_absolute_url() + "#operacion")
    return render(request, "comercial/operacion_form.html", {
        "form": form, "op": op, "operacion": operacion, "titulo": "Editar operación",
    })


@crm_requerido
@require_POST
def operacion_anular(request, pk):
    operacion = get_object_or_404(Operacion.objects.select_related("oportunidad", "propiedad"), pk=pk)
    try:
        operacion.anular(request.POST.get("motivo", "")[:500], request.user)
        messages.success(request, "Operación anulada. La oportunidad volvió a negociación y la propiedad quedó "
                                  "en borrador: publíquela de nuevo cuando corresponda.")
    except ValidationError as e:
        _errores(request, e)
    return redirect(operacion.oportunidad)


# ---------------------------------------------------------------------------
# Indicadores y exportación CSV
# ---------------------------------------------------------------------------

def _periodo(request):
    hoy = timezone.localdate()
    defecto = {"desde": hoy.replace(month=1, day=1), "hasta": hoy}
    form = PeriodoForm(request.GET or None, initial=defecto)
    if request.GET and form.is_valid():
        return form, form.cleaned_data["desde"], form.cleaned_data["hasta"]
    if not request.GET:
        form = PeriodoForm(initial=defecto)
    return form, defecto["desde"], defecto["hasta"]


@crm_requerido
def indicadores(request):
    form, desde, hasta = _periodo(request)
    return render(request, "comercial/indicadores.html", {
        "form": form, "desde": desde, "hasta": hasta, "i": ind.calcular(desde, hasta),
    })


@crm_requerido
def exportar(request, tipo):
    _, desde, hasta = _periodo(request)
    sufijo = f"{desde:%Y%m%d}-{hasta:%Y%m%d}"
    if tipo == "oportunidades":
        encabezados, filas = ind.csv_oportunidades(desde, hasta)
    elif tipo == "operaciones":
        encabezados, filas = ind.csv_operaciones(desde, hasta)
    elif tipo == "propiedades":
        encabezados, filas = ind.csv_propiedades()
        sufijo = f"{timezone.localdate():%Y%m%d}"
    else:
        raise Http404("Exportación no disponible.")
    return ind.respuesta_csv(f"{tipo}_{sufijo}.csv", encabezados, filas)


@crm_requerido
@require_POST
def cerrar_otras(request, pk):
    """Cierra como perdidas las demás oportunidades abiertas por la propiedad de una
    operación vigente. Requiere confirmación explícita."""
    operacion = get_object_or_404(Operacion.objects.select_related("oportunidad", "propiedad"), pk=pk)
    if request.POST.get("confirmar") != "si":
        messages.error(request, "Debe confirmar la acción.")
        return redirect(operacion.oportunidad)
    try:
        n = operacion.cerrar_otras_como_perdidas(request.user)
        messages.success(request, f"{n} oportunidad(es) cerrada(s) como perdida(s)." if n
                         else "No había otras oportunidades abiertas.")
    except ValidationError as e:
        _errores(request, e)
    return redirect(operacion.oportunidad)
