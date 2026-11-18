from django import forms
from django.db.models import Q

from contactos.models import Contacto
from core.forms import BootstrapMixin
from propiedades.models import Propiedad

from .models import Oferta, Operacion, Oportunidad

ESTADOS_NO_OFRECIBLES = ("anulada", "vendida", "arrendada")


def propiedades_ofrecibles():
    return Propiedad.objects.exclude(estado__in=ESTADOS_NO_OFRECIBLES).order_by("codigo")


class OportunidadForm(BootstrapMixin, forms.ModelForm):
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
        c, p = datos.get("contacto"), datos.get("propiedad")
        if c and p:
            if p.propietario_id == c.pk:
                raise forms.ValidationError("El interesado es el propietario de esa propiedad.")
            if Oportunidad.objects.filter(contacto=c, propiedad=p, etapa__in=Oportunidad.ABIERTAS).exists():
                raise forms.ValidationError("Ya existe una oportunidad abierta para este interesado y esta propiedad.")
        return datos


class EtapaForm(BootstrapMixin, forms.Form):
    etapa = forms.ChoiceField(choices=[(e.value, e.label) for e in Oportunidad.ABIERTAS])


class PerdidaForm(BootstrapMixin, forms.Form):
    motivo = forms.CharField(label="Motivo", max_length=500,
                             widget=forms.Textarea(attrs={"rows": 2, "placeholder": "Ej.: compró otra propiedad, precio fuera de presupuesto"}))


class AsignarPropiedadForm(BootstrapMixin, forms.Form):
    propiedad = forms.ModelChoiceField(queryset=Propiedad.objects.none(), label="Propiedad")

    def __init__(self, *args, oportunidad=None, **kwargs):
        super().__init__(*args, **kwargs)
        qs = propiedades_ofrecibles()
        if oportunidad is not None:
            qs = qs.exclude(propietario_id=oportunidad.contacto_id)
        self.fields["propiedad"].queryset = qs


class FiltroOportunidadesForm(forms.Form):
    q = forms.CharField(required=False)
    origen = forms.ChoiceField(required=False, choices=[("", "Todos los orígenes")] + Oportunidad.Origen.choices)


def filtro_texto(qs, q):
    return qs.filter(Q(contacto__nombre__icontains=q) | Q(contacto__email__icontains=q)
                     | Q(propiedad__codigo__icontains=q) | Q(propiedad__titulo__icontains=q))


class OfertaForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Oferta
        fields = ["tipo", "monto", "moneda", "fecha"]
        widgets = {"fecha": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
                   "monto": forms.NumberInput(attrs={"step": "0.01", "min": "1"})}


class RespuestaOfertaForm(forms.Form):
    respuesta = forms.ChoiceField(choices=[(Oferta.Respuesta.ACEPTADA, "Aceptar"), (Oferta.Respuesta.RECHAZADA, "Rechazar")])


class OperacionForm(BootstrapMixin, forms.ModelForm):
    """Cierre (o edición) de la operación. Muestra las fechas según sea venta o arriendo."""

    class Meta:
        model = Operacion
        fields = ["precio_final", "moneda", "comision_monto", "comision_moneda",
                  "fecha_promesa", "fecha_escritura", "fecha_firma_contrato",
                  "comision_pagada", "fecha_pago_comision"]
        widgets = {f: forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")
                   for f in ("fecha_promesa", "fecha_escritura", "fecha_firma_contrato", "fecha_pago_comision")}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.tipo == "venta":
            del self.fields["fecha_firma_contrato"]
        else:
            del self.fields["fecha_promesa"]
            del self.fields["fecha_escritura"]
            self.fields["fecha_firma_contrato"].required = True
            self.fields["precio_final"].label = "Canon de arriendo pactado"


class PeriodoForm(BootstrapMixin, forms.Form):
    desde = forms.DateField(widget=forms.DateInput(attrs={"type": "date", "min": "2000-01-01", "max": "2100-12-31"},
                                                   format="%Y-%m-%d"))
    hasta = forms.DateField(widget=forms.DateInput(attrs={"type": "date", "min": "2000-01-01", "max": "2100-12-31"},
                                                   format="%Y-%m-%d"))

    def clean(self):
        datos = super().clean()
        for campo in ("desde", "hasta"):
            fecha = datos.get(campo)
            if fecha and not (2000 <= fecha.year <= 2100):
                raise forms.ValidationError("Use fechas entre los años 2000 y 2100.")
        if datos.get("desde") and datos.get("hasta") and datos["desde"] > datos["hasta"]:
            raise forms.ValidationError("La fecha «desde» debe ser anterior a «hasta».")
        return datos
