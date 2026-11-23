from datetime import datetime, time, timedelta

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from comercial.models import Oportunidad
from contactos.models import Contacto
from core.permisos import crm_requerido
from propiedades.models import Propiedad

from .forms import ActividadForm, ProgramarForm
from .models import Actividad

# Fichas desde las que se registran o programan actividades.
DESTINOS = {"contacto": Contacto, "propiedad": Propiedad, "oportunidad": Oportunidad}


def _nueva_actividad(destino, objeto):
    """Actividad asociada a la ficha. La relación la fija el servidor, nunca el formulario.
    Si es una oportunidad, también queda en el historial de su contacto y su propiedad."""
    if destino == "oportunidad":
        return Actividad(oportunidad=objeto, contacto=objeto.contacto, propiedad=objeto.propiedad)
    return Actividad(**{destino: objeto})


def _mostrar_errores(request, form):
    for errores in form.errors.values():
        for e in errores:
            messages.error(request, e)


def _contexto_agenda(request, form):
    tipo = request.GET.get("tipo", "")
    pendientes = Actividad.objects.agenda().select_related("contacto", "propiedad")
    if tipo in Actividad.TIPOS_AGENDA:
        pendientes = pendientes.filter(tipo=tipo)
    ahora = timezone.now()
    fin_del_dia = timezone.make_aware(datetime.combine(timezone.localdate(), time.max))
    proximas = pendientes.filter(fecha__gt=fin_del_dia).order_by("fecha")
    return {
        "tipo": tipo,
        "form": form,
        "vencidas": pendientes.filter(fecha__lt=ahora).order_by("fecha"),
        "hoy": pendientes.filter(fecha__gte=ahora, fecha__lte=fin_del_dia).order_by("fecha"),
        "proximas": proximas[:100],
        "n_proximas": proximas.count(),
        "realizadas": (Actividad.objects.filter(tipo__in=Actividad.TIPOS_AGENDA, estado=Actividad.Estado.REALIZADA,
                                                fecha__gte=ahora - timedelta(days=7))
                       .select_related("contacto", "propiedad").order_by("-fecha")[:10]),
    }


@crm_requerido
def agenda(request):
    return render(request, "actividades/agenda.html", _contexto_agenda(request, ProgramarForm()))


@crm_requerido
@require_POST
def programar(request):
    """Programa una visita o tarea desde la agenda."""
    form = ProgramarForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, "Actividad programada.")
        return redirect("actividades:agenda")
    return render(request, "actividades/agenda.html", _contexto_agenda(request, form))


@crm_requerido
@require_POST
def programar_en(request, destino, pk):
    """Programa una visita o tarea desde la ficha de un contacto, propiedad u oportunidad."""
    modelo = DESTINOS.get(destino)
    if modelo is None:
        return redirect("actividades:agenda")
    objeto = get_object_or_404(modelo, pk=pk)
    form = ProgramarForm(request.POST, fijo=destino, instance=_nueva_actividad(destino, objeto))
    if form.is_valid():
        form.save()
        messages.success(request, "Actividad programada. Aparece en la agenda.")
    else:
        _mostrar_errores(request, form)
    return redirect(objeto.get_absolute_url() + "#historial")


@crm_requerido
@require_POST
def registrar(request, destino, pk):
    """Registra una nota, llamada, reunión, etc. en el historial de una ficha."""
    modelo = DESTINOS.get(destino)
    if modelo is None:
        return redirect("actividades:agenda")
    objeto = get_object_or_404(modelo, pk=pk)
    form = ActividadForm(request.POST, instance=_nueva_actividad(destino, objeto))
    if form.is_valid():
        form.save()
        messages.success(request, "Actividad registrada.")
    else:
        _mostrar_errores(request, form)
    return redirect(objeto.get_absolute_url() + "#historial")


@crm_requerido
@require_POST
def completar(request, pk):
    """Marca como realizada una visita o tarea programada."""
    actividad = get_object_or_404(Actividad, pk=pk)
    if actividad.en_agenda:
        actividad.estado = Actividad.Estado.REALIZADA
        actividad.save()
        messages.success(request, f"{actividad.get_tipo_display()} marcada como realizada.")
    # Solo se vuelve a una página de este mismo sitio.
    destino = request.POST.get("next", "")
    if url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()}):
        return redirect(destino)
    return redirect("actividades:agenda")
