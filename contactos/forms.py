from django import forms
from django.db.models import Q

from propiedades.models import TipoPropiedad

from .models import Contacto, PreferenciaBusqueda


class ContactoForm(forms.ModelForm):
    class Meta:
        model = Contacto
        fields = [
            "nombre", "rut", "telefono", "email", "informacion_adicional",
            "es_propietario", "es_arrendatario", "es_interesado",
        ]
        widgets = {"informacion_adicional": forms.Textarea(attrs={"rows": 3})}


class PreferenciaForm(forms.ModelForm):
    class Meta:
        model = PreferenciaBusqueda
        fields = ["operacion", "tipo", "zona", "dormitorios_min", "moneda", "precio_min", "precio_max"]
        widgets = {
            "precio_min": forms.NumberInput(attrs={"placeholder": "Desde"}),
            "precio_max": forms.NumberInput(attrs={"placeholder": "Hasta"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Tipos activos, más el que ya tenía la preferencia (aunque después se haya desactivado).
        self.fields["tipo"].queryset = TipoPropiedad.objects.filter(Q(activo=True) | Q(pk=self.instance.tipo_id))
        self.fields["tipo"].empty_label = "Cualquier tipo"
        self.fields["zona"].choices = [("", "Cualquier zona")] + list(self.fields["zona"].choices)[1:]
