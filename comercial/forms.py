from django import forms
from django.db.models import Q

from contactos.models import Contacto
from propiedades.models import Propiedad

from .models import ESTADOS_NO_OFRECIBLES, Oferta, Operacion, Oportunidad


def propiedades_ofrecibles():
    """Propiedades que todavía se pueden ofrecer a un interesado."""
    return Propiedad.objects.exclude(estado__in=ESTADOS_NO_OFRECIBLES).order_by("codigo")


def filtro_texto(oportunidades, q):
    """Búsqueda de la lista: por interesado (nombre o correo) o propiedad (código o título)."""
    return oportunidades.filter(Q(contacto__nombre__icontains=q) | Q(contacto__email__icontains=q)
                                | Q(propiedad__codigo__icontains=q) | Q(propiedad__titulo__icontains=q))


class OportunidadForm(forms.ModelForm):
    """Ingreso manual de una oportunidad."""

    class Meta:
        model = Oportunidad
        fields = ["contacto", "propiedad", "mensaje"]
        widgets = {"mensaje": forms.Textarea(attrs={"rows": 3, "placeholder": "Qué busca o cómo llegó (opcional)"})}
        labels = {"mensaje": "Notas iniciales"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["contacto"].queryset = Contacto.objects.filter(es_interesado=True).order_by("nombre")
        self.fields["contacto"].help_text = "Solo contactos con rol de interesado."
        self.fields["propiedad"].queryset = propiedades_ofrecibles()

    def clean(self):
        datos = super().clean()
        contacto, propiedad = datos.get("contacto"), datos.get("propiedad")
        if contacto and propiedad:
            if propiedad.propietario_id == contacto.pk:
                raise forms.ValidationError("El interesado es el propietario de esa propiedad.")
            if Oportunidad.objects.filter(contacto=contacto, propiedad=propiedad, etapa__in=Oportunidad.ABIERTAS).exists():
                raise forms.ValidationError("Ya existe una oportunidad abierta para este interesado y esta propiedad.")
        return datos


# --- Formularios pequeños de la ficha de la oportunidad (se dibujan campo por campo,
#     por eso cada widget trae su clase de Bootstrap) ---

class EtapaForm(forms.Form):
    etapa = forms.ChoiceField(choices=[(e.value, e.label) for e in Oportunidad.ABIERTAS],
                              widget=forms.Select(attrs={"class": "form-select"}))


class PerdidaForm(forms.Form):
    motivo = forms.CharField(label="Motivo", max_length=500, widget=forms.Textarea(attrs={
        "class": "form-control", "rows": 2, "placeholder": "Ej.: compró otra propiedad, precio fuera de presupuesto"}))


class AsignarPropiedadForm(forms.Form):
    propiedad = forms.ModelChoiceField(queryset=Propiedad.objects.none(), label="Propiedad",
                                       widget=forms.Select(attrs={"class": "form-select"}))

    def __init__(self, *args, oportunidad=None, **kwargs):
        super().__init__(*args, **kwargs)
        propiedades = propiedades_ofrecibles()
        if oportunidad is not None:
            # El interesado no puede ser el propietario.
            propiedades = propiedades.exclude(propietario_id=oportunidad.contacto_id)
        self.fields["propiedad"].queryset = propiedades


class FiltroOportunidadesForm(forms.Form):
    """Filtros de la lista (el HTML de los campos está escrito en el template)."""
    q = forms.CharField(required=False)
    origen = forms.ChoiceField(required=False, choices=[("", "Todos los orígenes")] + Oportunidad.Origen.choices)


class OfertaForm(forms.ModelForm):
    class Meta:
        model = Oferta
        fields = ["tipo", "monto", "moneda", "fecha"]
        widgets = {
            "tipo": forms.Select(attrs={"class": "form-select"}),
            "monto": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "1"}),
            "moneda": forms.Select(attrs={"class": "form-select"}),
            "fecha": forms.DateInput(attrs={"class": "form-control", "type": "date"}, format="%Y-%m-%d"),
        }


class RespuestaOfertaForm(forms.Form):
    respuesta = forms.ChoiceField(choices=[(Oferta.Respuesta.ACEPTADA, "Aceptar"), (Oferta.Respuesta.RECHAZADA, "Rechazar")])


class OperacionForm(forms.ModelForm):
    """Cierre (o edición) de la operación. Muestra las fechas según sea venta o arriendo."""

    class Meta:
        model = Operacion
        fields = ["precio_final", "moneda", "comision_monto", "comision_moneda",
                  "fecha_promesa", "fecha_escritura", "fecha_firma_contrato",
                  "comision_pagada", "fecha_pago_comision"]
        widgets = {campo: forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")
                   for campo in ("fecha_promesa", "fecha_escritura", "fecha_firma_contrato", "fecha_pago_comision")}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.tipo == Propiedad.Operacion.VENTA:
            del self.fields["fecha_firma_contrato"]
        else:
            del self.fields["fecha_promesa"]
            del self.fields["fecha_escritura"]
            self.fields["fecha_firma_contrato"].required = True
            self.fields["precio_final"].label = "Canon de arriendo pactado"


class PeriodoForm(forms.Form):
    """Período de los indicadores. Se dibuja campo por campo."""
    desde = forms.DateField(widget=forms.DateInput(
        attrs={"class": "form-control", "type": "date", "min": "2000-01-01", "max": "2100-12-31"}, format="%Y-%m-%d"))
    hasta = forms.DateField(widget=forms.DateInput(
        attrs={"class": "form-control", "type": "date", "min": "2000-01-01", "max": "2100-12-31"}, format="%Y-%m-%d"))

    def clean(self):
        datos = super().clean()
        for campo in ("desde", "hasta"):
            fecha = datos.get(campo)
            if fecha and not (2000 <= fecha.year <= 2100):
                raise forms.ValidationError("Use fechas entre los años 2000 y 2100.")
        if datos.get("desde") and datos.get("hasta") and datos["desde"] > datos["hasta"]:
            raise forms.ValidationError("La fecha «desde» debe ser anterior a «hasta».")
        return datos
