"""
Portal público. Estas vistas no exigen sesión y SOLO trabajan con los
diccionarios que entrega propiedades.publico (lista cerrada de campos).
"""
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.http import Http404
from django.shortcuts import redirect, render

from captacion.models import FotoSolicitud, SolicitudCaptacion
from comercial.models import Oportunidad
from core.limites import envios_excedidos, registrar_envio
from propiedades.models import Propiedad
from propiedades.publico import ficha_publica, propiedades_publicas

from .forms import BusquedaForm, ConsultaForm, OfrecerPropiedadForm

MENSAJE_LIMITE = ("Recibimos varios envíos desde tu conexión en poco tiempo. "
                  "Inténtalo nuevamente en una hora o contáctanos por teléfono.")


def catalogo(request):
    form = BusquedaForm(request.GET or None)
    qs = propiedades_publicas()
    if form.is_valid():
        d = form.cleaned_data
        for campo in ("operacion", "tipo", "zona"):
            if d[campo]:
                qs = qs.filter(**{campo: d[campo]})
        if d["dormitorios"]:
            qs = qs.filter(dormitorios__gte=int(d["dormitorios"]))
        if d["precio_min"] is not None or d["precio_max"] is not None:
            qs = qs.filter(moneda=d["moneda"] or Propiedad.Moneda.CLP)
            if d["precio_min"] is not None:
                qs = qs.filter(precio__gte=d["precio_min"])
            if d["precio_max"] is not None:
                qs = qs.filter(precio__lte=d["precio_max"])
    qs = qs.order_by("-actualizado")
    pagina = Paginator(qs, 12).get_page(request.GET.get("page"))
    return render(request, "portal/catalogo.html", {
        "form": form if request.GET else BusquedaForm(),
        "pagina": pagina,
        "propiedades": [ficha_publica(p) for p in pagina],
        "total": pagina.paginator.count,
    })


def ficha(request, codigo):
    p = propiedades_publicas().filter(codigo=codigo).first()
    if p is None:
        # No disponible, vendida, arrendada, anulada o en borrador: no existe para el público.
        raise Http404("Propiedad no disponible.")

    form = ConsultaForm(request.POST or None, initial={
        "mensaje": f"Hola, me interesa la propiedad {p.codigo}. ¿Podrían enviarme más información?",
    })
    if request.method == "POST" and envios_excedidos(request, "consulta"):
        form.add_error(None, MENSAJE_LIMITE)
    elif request.method == "POST" and form.is_valid():
        registrar_envio(request, "consulta")
        Oportunidad.desde_portal(**form.cleaned_data_sin_trampa(), propiedad=p,
                                 origen=Oportunidad.Origen.PORTAL)
        messages.success(request, "¡Gracias! Recibimos tu consulta y te contactaremos a la brevedad.")
        return redirect("portal:ficha", codigo=codigo)

    return render(request, "portal/ficha.html", {"p": ficha_publica(p), "form": form})


def ofrecer(request):
    """«Ofrecer mi propiedad»: crea solo una solicitud por evaluar. No crea contactos
    ni propiedades: eso ocurre cuando la administradora la acepta en el CRM."""
    form = OfrecerPropiedadForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and envios_excedidos(request, "ofrecer"):
        form.add_error(None, MENSAJE_LIMITE)
    elif request.method == "POST" and form.is_valid():
        registrar_envio(request, "ofrecer")
        solicitud = form.save(commit=False)
        solicitud.origen = SolicitudCaptacion.Origen.WEB
        with transaction.atomic():
            solicitud.save()
            for imagen in form.cleaned_data["fotos"]:
                FotoSolicitud.objects.create(solicitud=solicitud, imagen=imagen)
        messages.success(request, "¡Gracias! Recibimos los datos de tu propiedad. "
                                  "Te contactaremos para coordinar una evaluación.")
        return redirect("portal:ofrecer")
    return render(request, "portal/ofrecer.html", {"form": form})


def contacto(request):
    """Mensaje general a la corredora. Abre una oportunidad nueva sin propiedad."""
    form = ConsultaForm(request.POST or None)
    if request.method == "POST" and envios_excedidos(request, "consulta"):
        form.add_error(None, MENSAJE_LIMITE)
    elif request.method == "POST" and form.is_valid():
        registrar_envio(request, "consulta")
        Oportunidad.desde_portal(**form.cleaned_data_sin_trampa(), origen=Oportunidad.Origen.CONTACTO)
        messages.success(request, "¡Gracias! Recibimos tu mensaje y te responderemos a la brevedad.")
        return redirect("portal:contacto")
    return render(request, "portal/contacto.html", {"form": form})
