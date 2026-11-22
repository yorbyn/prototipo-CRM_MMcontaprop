from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from comercial.models import Oportunidad
from contactos.models import Contacto
from core.permisos import crm_requerido
from propiedades.models import Propiedad

from .envio import correo_en_consola, enviados_hoy, enviar
from .forms import PlantillaForm, RedactarForm
from .models import VARIABLES, Mensaje, PlantillaCorreo, reemplazar, valores_para


def _contexto_envio(datos):
    """Contacto, propiedad y oportunidad del correo, leídos de ?contacto=, ?propiedad= u ?oportunidad=.
    Si viene una oportunidad, el contacto y la propiedad son los de ella."""
    def obtener(modelo, clave):
        valor = datos.get(clave, "")
        return get_object_or_404(modelo, pk=valor) if str(valor).isdigit() else None

    oportunidad = obtener(Oportunidad, "oportunidad")
    if oportunidad is not None:
        return oportunidad.contacto, oportunidad.propiedad, oportunidad
    return obtener(Contacto, "contacto"), obtener(Propiedad, "propiedad"), None


@crm_requerido
def redactar(request):
    datos = request.POST if request.method == "POST" else request.GET
    contacto, propiedad, oportunidad = _contexto_envio(datos)
    plantilla = PlantillaCorreo.objects.filter(clave=datos.get("plantilla", "")).first()

    if request.method == "POST":
        form = RedactarForm(request.POST, contacto_fijo=contacto)
        if form.is_valid():
            destinatario = contacto or form.cleaned_data["contacto"]
            valores = valores_para(destinatario, propiedad, request)
            try:
                mensaje = enviar(contacto=destinatario, propiedad=propiedad, oportunidad=oportunidad,
                                 plantilla=plantilla,
                                 asunto=reemplazar(form.cleaned_data["asunto"], valores),
                                 cuerpo=reemplazar(form.cleaned_data["cuerpo"], valores))
            except ValidationError as e:
                for error in e.messages:
                    messages.error(request, error)
            else:
                if mensaje.estado == Mensaje.Estado.ENVIADO:
                    messages.success(request, f"Correo enviado a {mensaje.para}. Quedó en el historial.")
                    # Se vuelve a la ficha desde la que se escribió.
                    if oportunidad:
                        ficha = oportunidad
                    elif propiedad and datos.get("volver") == "propiedad":
                        ficha = propiedad
                    else:
                        ficha = destinatario
                    return redirect(ficha.get_absolute_url() + "#historial")
                messages.error(request, "No se pudo enviar el correo. Revise la configuración de Gmail "
                                        "y la conexión. El detalle quedó en «Correos enviados».")
    else:
        # Al elegir una plantilla, el asunto y el cuerpo se llenan con sus variables ya reemplazadas.
        inicial = {}
        if plantilla is not None:
            valores = valores_para(contacto, propiedad, request) if contacto else {}
            inicial = {"asunto": reemplazar(plantilla.asunto, valores), "cuerpo": reemplazar(plantilla.cuerpo, valores)}
        form = RedactarForm(initial=inicial, contacto_fijo=contacto)

    return render(request, "correo/redactar.html", {
        "form": form, "contacto": contacto, "propiedad": propiedad, "oportunidad": oportunidad,
        "plantilla": plantilla, "plantillas": PlantillaCorreo.objects.all(), "variables": VARIABLES,
        "volver": datos.get("volver", ""), "en_consola": correo_en_consola(),
    })


@crm_requerido
def enviados(request):
    pagina = Paginator(Mensaje.objects.select_related("contacto", "propiedad"), 30).get_page(request.GET.get("page"))
    return render(request, "correo/mensaje_lista.html", {
        "pagina": pagina, "hoy": enviados_hoy(), "en_consola": correo_en_consola(),
    })


@crm_requerido
def plantillas(request):
    return render(request, "correo/plantilla_lista.html", {
        "plantillas": PlantillaCorreo.objects.all(), "variables": VARIABLES,
    })


@crm_requerido
def plantilla_editar(request, pk=None):
    """Crea una plantilla (sin pk) o edita una existente."""
    plantilla = get_object_or_404(PlantillaCorreo, pk=pk) if pk else PlantillaCorreo()
    form = PlantillaForm(request.POST or None, instance=plantilla)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Plantilla guardada.")
        return redirect("correo:plantillas")
    return render(request, "correo/plantilla_form.html", {"form": form, "plantilla": plantilla, "variables": VARIABLES})
