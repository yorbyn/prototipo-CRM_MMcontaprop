"""
Portal público. Estas vistas no exigen sesión y SOLO muestran los datos que entrega
portal/publico.py (una lista cerrada de campos: nunca la dirección exacta ni el propietario).
"""
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.http import Http404
from django.shortcuts import redirect, render

from captacion.models import MAX_FOTOS_SOLICITUD, SolicitudCaptacion
from comercial.models import Oportunidad
from propiedades.models import Propiedad

from .forms import BusquedaForm, ConsultaForm, FotoSolicitudForm, OfrecerPropiedadForm
from .publico import ficha_publica, propiedades_publicas


def catalogo(request):
    form = BusquedaForm(request.GET or None)
    propiedades = propiedades_publicas()
    if form.is_valid():
        datos = form.cleaned_data
        for campo in ("operacion", "tipo", "zona"):
            if datos[campo]:
                propiedades = propiedades.filter(**{campo: datos[campo]})
        if datos["dormitorios"]:
            propiedades = propiedades.filter(dormitorios__gte=int(datos["dormitorios"]))
        # El precio solo se compara en una moneda (no se convierte UF a pesos).
        if datos["precio_min"] is not None or datos["precio_max"] is not None:
            propiedades = propiedades.filter(moneda=datos["moneda"] or Propiedad.Moneda.CLP)
            if datos["precio_min"] is not None:
                propiedades = propiedades.filter(precio__gte=datos["precio_min"])
            if datos["precio_max"] is not None:
                propiedades = propiedades.filter(precio__lte=datos["precio_max"])
    pagina = Paginator(propiedades.order_by("-actualizado"), 12).get_page(request.GET.get("page"))
    return render(request, "portal/catalogo.html", {
        "form": form if request.GET else BusquedaForm(),
        "pagina": pagina,
        "propiedades": [ficha_publica(p) for p in pagina],
        "total": pagina.paginator.count,
    })


def ficha(request, codigo):
    propiedad = propiedades_publicas().filter(codigo=codigo).first()
    if propiedad is None:
        # Borrador, vendida, arrendada o anulada: para el público no existe.
        raise Http404("Propiedad no disponible.")
    form = ConsultaForm(request.POST or None, initial={
        "mensaje": f"Hola, me interesa la propiedad {propiedad.codigo}. ¿Podrían enviarme más información?",
    })
    if request.method == "POST" and form.is_valid():
        Oportunidad.desde_portal(**form.cleaned_data, propiedad=propiedad, origen=Oportunidad.Origen.PORTAL)
        messages.success(request, "¡Gracias! Recibimos tu consulta y te contactaremos a la brevedad.")
        return redirect("portal:ficha", codigo=codigo)
    return render(request, "portal/ficha.html", {"p": ficha_publica(propiedad), "form": form})


def ofrecer(request):
    """«Ofrecer mi propiedad»: crea solo una solicitud por evaluar. No crea contactos ni
    propiedades: eso ocurre cuando la administradora la acepta en el CRM."""
    form = OfrecerPropiedadForm(request.POST or None)
    errores_fotos = []
    if request.method == "POST":
        # Las fotos son opcionales; cada una se valida por separado con FotoSolicitudForm.
        archivos = request.FILES.getlist("fotos")
        fotos = []
        if len(archivos) > MAX_FOTOS_SOLICITUD:
            errores_fotos.append(f"Puedes enviar como máximo {MAX_FOTOS_SOLICITUD} fotos.")
        else:
            for archivo in archivos:
                foto_form = FotoSolicitudForm(files={"imagen": archivo})
                if foto_form.is_valid():
                    fotos.append(foto_form)
                else:
                    errores_fotos += [f"{archivo.name}: {error}" for error in foto_form.errors["imagen"]]

        if form.is_valid() and not errores_fotos:
            with transaction.atomic():  # la solicitud y sus fotos se guardan juntas
                solicitud = form.save(commit=False)
                solicitud.origen = SolicitudCaptacion.Origen.WEB
                solicitud.save()
                for foto_form in fotos:
                    foto = foto_form.save(commit=False)
                    foto.solicitud = solicitud
                    foto.save()
            messages.success(request, "¡Gracias! Recibimos los datos de tu propiedad. "
                                      "Te contactaremos para coordinar una evaluación.")
            return redirect("portal:ofrecer")
    return render(request, "portal/ofrecer.html", {
        "form": form, "errores_fotos": errores_fotos, "max_fotos": MAX_FOTOS_SOLICITUD,
    })


def contacto(request):
    """Mensaje general a la corredora. Abre una oportunidad nueva sin propiedad."""
    form = ConsultaForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        Oportunidad.desde_portal(**form.cleaned_data, origen=Oportunidad.Origen.CONTACTO)
        messages.success(request, "¡Gracias! Recibimos tu mensaje y te responderemos a la brevedad.")
        return redirect("portal:contacto")
    return render(request, "portal/contacto.html", {"form": form})
