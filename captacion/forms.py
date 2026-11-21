from django import forms
from django.db.models import Q

from core.forms import BootstrapMixin
from core.validators import normalizar_rut
from propiedades.models import TipoPropiedad 

from .models import Encargo, SolicitudCaptacion

# Campos que puede completar el propietario. El formulario público del portal
# usa exactamente esta lista (nunca estado, origen, observaciones ni relaciones).
CAMPOS_SOLICITUD_PUBLICOS = [
    "nombre", "rut", "email", "telefono",
    "tipo", "operacion", "modalidad_arriendo", "zona", "comuna", "direccion",
    "dormitorios", "banos", "superficie_util", "superficie_total",
    "precio_esperado", "moneda", "comentarios",
]


class SolicitudBaseForm(BootstrapMixin, forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["modalidad_arriendo"].choices = [("", "—")] + list(self.fields["modalidad_arriendo"].choices)[1:]
        actual = self.instance.tipo_id if self.instance.pk else None
        self.fields["tipo"].queryset = TipoPropiedad.objects.filter(Q(activo=True) | Q(pk=actual))
        self.fields["tipo"].empty_label = "Elige un tipo"

    def clean_rut(self):
        return normalizar_rut(self.cleaned_data.get("rut"))

    def clean_email(self):
        return (self.cleaned_data.get("email") or "").strip().lower()

    def clean_comuna(self):
        return " ".join(self.cleaned_data["comuna"].split())


class SolicitudForm(SolicitudBaseForm):
    """Ingreso manual o edición de una solicitud desde el CRM."""

    class Meta:
        model = SolicitudCaptacion
        fields = CAMPOS_SOLICITUD_PUBLICOS + ["observaciones"]
        widgets = {
            "comentarios": forms.Textarea(attrs={"rows": 3}),
            "observaciones": forms.Textarea(attrs={"rows": 3}),
        }


class EncargoForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Encargo
        fields = ["comision_pct", "exclusividad", "fecha_inicio", "fecha_vencimiento"]
        widgets = {
            "fecha_inicio": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "fecha_vencimiento": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "comision_pct": forms.NumberInput(attrs={"step": "0.01", "min": "0.01", "max": "100"}),
        }
