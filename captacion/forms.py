from django import forms
from django.db.models import Q

from propiedades.models import TipoPropiedad

from .models import Encargo, SolicitudCaptacion

# Campos que puede completar el propietario. El formulario público del portal usa
# exactamente esta lista (nunca estado, origen, observaciones ni relaciones).
CAMPOS_SOLICITUD_PUBLICOS = [
    "nombre", "rut", "email", "telefono",
    "tipo", "operacion", "modalidad_arriendo", "zona", "comuna", "direccion",
    "dormitorios", "banos", "superficie_util", "superficie_total",
    "precio_esperado", "moneda", "comentarios",
]


class SolicitudBaseForm(forms.ModelForm):
    """Base del formulario del CRM y del portal («Ofrecer mi propiedad»)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["modalidad_arriendo"].choices = [("", "—")] + list(self.fields["modalidad_arriendo"].choices)[1:]
        # Tipos activos, más el que ya tenía la solicitud.
        self.fields["tipo"].queryset = TipoPropiedad.objects.filter(Q(activo=True) | Q(pk=self.instance.tipo_id))
        self.fields["tipo"].empty_label = "Elige un tipo"


class SolicitudForm(SolicitudBaseForm):
    """Ingreso manual o edición de una solicitud desde el CRM."""

    class Meta:
        model = SolicitudCaptacion
        fields = CAMPOS_SOLICITUD_PUBLICOS + ["observaciones"]
        widgets = {
            "comentarios": forms.Textarea(attrs={"rows": 3}),
            "observaciones": forms.Textarea(attrs={"rows": 3}),
        }


class EncargoForm(forms.ModelForm):
    class Meta:
        model = Encargo
        fields = ["comision_pct", "exclusividad", "fecha_inicio", "fecha_vencimiento"]
        widgets = {
            "fecha_inicio": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "fecha_vencimiento": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "comision_pct": forms.NumberInput(attrs={"step": "0.01", "min": "0.01", "max": "100"}),
        }
