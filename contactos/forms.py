from django import forms
from django.db.models import Q

from core.forms import BootstrapMixin
from core.validators import normalizar_rut
from propiedades.models import TipoPropiedad

from .models import Contacto, PreferenciaBusqueda


class ContactoForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Contacto
        fields = [
            "nombre", "rut", "telefono", "email", "informacion_adicional",
            "es_propietario", "es_arrendatario", "es_interesado",
        ]
        widgets = {"informacion_adicional": forms.Textarea(attrs={"rows": 3})}

    def clean_rut(self):
        # Se normaliza antes de la validación de unicidad para detectar
        # duplicados aunque se escriba con o sin puntos.
        return normalizar_rut(self.cleaned_data.get("rut")) or None

class PreferenciaForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = PreferenciaBusqueda
        fields = ["operacion", "tipo", "zona", "dormitorios_min", "moneda", "precio_min", "precio_max"]
        widgets = {
            "precio_min": forms.NumberInput(attrs={"placeholder": "Desde"}),
            "precio_max": forms.NumberInput(attrs={"placeholder": "Hasta"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Tipos activos, más el que ya tenía la preferencia.
        actual = self.instance.tipo_id if self.instance.pk else None
        self.fields["tipo"].queryset = TipoPropiedad.objects.filter(Q(activo=True) | Q(pk=actual))
        self.fields["tipo"].empty_label = "Cualquier tipo"
        self.fields["zona"].choices = [("", "Cualquier zona")] + list(self.fields["zona"].choices)[1:]
    